"""
整棟工務每日巡檢 - B2F  API Router【寬表格 Pivot 架構】
Prefix: /api/v1/mall/b2f-inspection

端點：
  POST /sync
  GET  /batches
  GET  /batches/{batch_id}
  GET  /batches/{batch_id}/kpi
  GET  /items
  GET  /stats
  GET  /items/item-history
  GET  /debug/ragic-raw
"""
from collections import Counter
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.b2f_inspection import B2FInspectionBatch, B2FInspectionItem
from app.schemas.b2f_inspection import (
    B2FInspectionBatchOut, B2FInspectionItemOut, B2FInspectionBatchKPI,
    B2FInspectionBatchDetail, StatusDistItem, B2FInspectionStats,
)
from app.services.b2f_inspection_sync import (
    sync_from_ragic, B2F_SERVER_URL, B2F_ACCOUNT, B2F_SHEET_PATH,
)
from app.services.ragic_adapter import RagicAdapter
from app.services.ragic_verify_utils import (
    read_portal_count_and_last_sync, read_portal_ragic_ids,
    fetch_ragic_count, fetch_ragic_url_map_single,
    build_verify_count_response, build_verify_diff_response,
)

router = APIRouter(dependencies=[Depends(get_current_user)])

STATUS_LABELS = {
    "normal":    "正常",
    "abnormal":  "異常",
    "pending":   "待處理",
    "unchecked": "未填寫",
    "measure":   "記錄值",
}
STATUS_COLORS = {
    "normal":    "#52C41A",
    "abnormal":  "#FF4D4F",
    "pending":   "#FAAD14",
    "unchecked": "#999999",
    "measure":   "#4BA8E8",
}


def _batch_to_out(b: B2FInspectionBatch, item_count: int = 0) -> B2FInspectionBatchOut:
    return B2FInspectionBatchOut(
        ragic_id        = b.ragic_id,
        inspection_date = b.inspection_date,
        inspector_name  = b.inspector_name,
        start_time      = b.start_time,
        end_time        = b.end_time,
        work_hours      = b.work_hours,
        item_count      = item_count,
        synced_at       = b.synced_at,
    )


def _item_to_out(it: B2FInspectionItem) -> B2FInspectionItemOut:
    return B2FInspectionItemOut(
        ragic_id       = it.ragic_id,
        batch_ragic_id = it.batch_ragic_id,
        seq_no         = it.seq_no,
        item_name      = it.item_name,
        result_raw     = it.result_raw,
        result_status  = it.result_status,
        abnormal_flag  = bool(it.abnormal_flag),
        synced_at      = it.synced_at,
    )


# ── KPI 只算「真正的設備項目」（2026-08-24）────────────────────────────────────
#
# 動態欄位偵測會把「拍照」「拍照2」「異常說明」「建立日期」「建立年份」「月份」
# 也收成 item，而 _normalize_result_status() 對「非空但不在對照表裡」的值一律
# 判成 abnormal —— 檔名與日期因此被算成異常，四個樓層合計虛報 488 筆。
#
# 判定規則集中在 app/services/inspection_field_rules.py，四個樓層與前端共用。
# ⚠️ 任何新增的「數異常」或「算完成率」的程式碼都必須先過這一層，
#    否則同一個模組會出現兩套數字。

def _equipment_items(items: list) -> list:
    """濾掉附件欄位與附註/系統欄位，只留下真正的設備巡檢項目。"""
    from app.services.inspection_field_rules import is_equipment_field
    return [it for it in items if is_equipment_field(it.item_name, it.result_raw)]


def _abnormal_count_for_batches(db, batches) -> int:
    """一批場次裡「異常 + 待處理」的設備項目數。"""
    total = 0
    for b in batches:
        items = db.query(B2FInspectionItem).filter(
            B2FInspectionItem.batch_ragic_id == b.ragic_id
        ).all()
        total += sum(
            1 for it in _equipment_items(items)
            if it.result_status in ("abnormal", "pending")
        )
    return total


def _calc_kpi(items: list[B2FInspectionItem]) -> B2FInspectionBatchKPI:
    items     = _equipment_items(items)
    total     = len(items)
    normal    = sum(1 for it in items if it.result_status == "normal")
    abnormal  = sum(1 for it in items if it.result_status == "abnormal")
    pending   = sum(1 for it in items if it.result_status == "pending")
    unchecked = sum(1 for it in items if it.result_status == "unchecked")
    # 量測/程度型（高/中/低、電壓範圍…）：有填就是已巡檢，但不是 pass/fail 判定
    measure   = sum(1 for it in items if it.result_status == "measure")
    checked   = normal + abnormal + pending + measure
    # ⚠️ normal_rate 的分母刻意**不含 measure** —— 「水位＝高」不是「合格」，
    #    把它算進合格率會讓數字虛高且無法解釋。
    judged    = normal + abnormal + pending
    return B2FInspectionBatchKPI(
        total           = total,
        normal          = normal,
        abnormal        = abnormal,
        pending         = pending,
        unchecked       = unchecked,
        measure         = measure,
        completion_rate = round(checked / total * 100, 1) if total > 0 else 0.0,
        normal_rate     = round(normal / judged * 100, 1) if judged > 0 else 0.0,
    )


@router.post("/sync", summary="從 Ragic 同步 B2F 巡檢資料（背景執行）", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def sync_b2f_inspection(background_tasks: BackgroundTasks):
    """觸發背景同步：Ragic → SQLite，立即回傳，不阻塞畫面"""
    background_tasks.add_task(sync_from_ragic)
    return {"status": "ok", "message": "同步已在背景啟動"}


# ── /verify-count／/verify-diff ─────────────────────────────────────────────────

@router.get("/verify-count", summary="與 Ragic 數量比對（管理員）",
            dependencies=[Depends(require_roles("system_admin"))])
async def verify_count(db: Session = Depends(get_db)):
    portal_count, last_synced_at = await read_portal_count_and_last_sync(
        db, B2FInspectionBatch, "B2F巡檢"
    )
    try:
        ragic_count = await fetch_ragic_count(B2F_SHEET_PATH, B2F_SERVER_URL, B2F_ACCOUNT)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ragic 連線失敗：{exc}")
    return build_verify_count_response("B2F巡檢", portal_count, ragic_count, last_synced_at)


@router.get("/verify-diff", summary="與 Ragic 明細差集比對（管理員）",
            dependencies=[Depends(require_roles("system_admin"))])
async def verify_diff(db: Session = Depends(get_db)):
    try:
        ragic_url_map = await fetch_ragic_url_map_single(B2F_SHEET_PATH, B2F_SERVER_URL, B2F_ACCOUNT)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ragic 連線失敗：{exc}")
    portal_ids = await read_portal_ragic_ids(db, B2FInspectionBatch)
    return build_verify_diff_response(ragic_url_map, portal_ids)


# ══════════════════════════════════════════════════════════════════════════════
# GET /db-images/{batch_ragic_id}  — 場次附圖（CLAUDE.md §7 附圖模組規範）
# ══════════════════════════════════════════════════════════════════════════════
#
# Ragic 的「拍照」欄在同步時被動態欄位偵測收成一般 item，`result_raw` 存的就是
# 檔名（如 "LMHiosXMzp@IMG_20260807_085440.jpg"）。因此這支端點**不需要打 Ragic、
# 也不需要新增 images_json 欄位**，直接把已同步的檔名交給 parse_images 組出
# Ragic 下載連結即可。
#
# ⚠️ 判定規則集中在 app/services/inspection_field_rules.py，四個樓層共用；
#    前端 FloorInspectionList.tsx 有一份等價規則，兩邊必須一起改，
#    否則會出現「明細列表把檔名當成異常狀態顯示成紅色 Tag」或「附圖區空白」。
#
# ⚠️ 不可改回寫死的欄位名清單（如 ("拍照",)）：Ragic 上的附件欄位命名沒有統一
#    （拍照 / 拍照1 / 拍照2 / 照片 / 附件…），Sheet 新增一個「拍照3」就會靜默漏掉，
#    而症狀只是「多一個紅色異常 Tag」，沒有人會發現。


class InspectionImageOut(BaseModel):
    url:      str
    filename: str


@router.get(
    "/db-images/{batch_ragic_id}",
    response_model=List[InspectionImageOut],
    summary="取得場次附圖（由已同步的附件欄位值組出 Ragic 下載連結，不打 Ragic）",
)
def get_batch_db_images(batch_ragic_id: str, db: Session = Depends(get_db)):
    from app.services.inspection_field_rules import (
        is_image_field, split_attachment_value,
    )
    from app.services.ragic_data_service import parse_images

    # 名稱規則之外還有值規則（副檔名），無法用 SQL 表達，故取回該場次全部 item
    # 再在 Python 端判定。單一場次至多數十筆，成本可忽略。
    items = (
        db.query(B2FInspectionItem)
        .filter(B2FInspectionItem.batch_ragic_id == batch_ragic_id)
        .order_by(B2FInspectionItem.seq_no)
        .all()
    )

    # ⚠️ 一個附件欄位可能同時有多張圖，sync 的 _stringify() 是用**空白**把它們
    #    串起來的（'a@1.jpg b@2.jpg'），而 parse_images 只認換行／逗號／分號。
    #    直接整串丟進去會組出一個含兩個檔名的壞連結 —— 兩張圖變一張破圖。
    images: list[dict] = []
    for it in items:
        if not is_image_field(it.item_name, it.result_raw):
            continue
        for token in split_attachment_value(it.result_raw):
            images.extend(parse_images(
                token, server=B2F_SERVER_URL, account=B2F_ACCOUNT,
            ))
    return images


@router.get("/batches", summary="取得巡檢場次清單")
def list_batches(
    year_month: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date:   Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(B2FInspectionBatch)
    if year_month:
        q = q.filter(B2FInspectionBatch.inspection_date.like(f"{year_month}%"))
    if start_date:
        q = q.filter(B2FInspectionBatch.inspection_date >= start_date)
    if end_date:
        q = q.filter(B2FInspectionBatch.inspection_date <= end_date)

    batches = q.order_by(B2FInspectionBatch.inspection_date.desc()).all()
    result = []
    for b in batches:
        items = db.query(B2FInspectionItem).filter(
            B2FInspectionItem.batch_ragic_id == b.ragic_id
        ).all()
        result.append({
            "batch": _batch_to_out(b, len(_equipment_items(items))).model_dump(),
            "kpi":   _calc_kpi(items).model_dump(),
        })
    return result


@router.get("/batches/{batch_id}", summary="取得單一場次完整資料")
def get_batch_detail(
    batch_id:      str,
    result_status: Optional[str] = Query(None, alias="status"),
    search:        Optional[str] = Query(None),
    db:            Session = Depends(get_db),
):
    batch = db.get(B2FInspectionBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"找不到場次：{batch_id}")

    items = db.query(B2FInspectionItem).filter(
        B2FInspectionItem.batch_ragic_id == batch_id
    ).order_by(B2FInspectionItem.seq_no).all()

    kpi = _calc_kpi(items)
    filtered = []
    for it in items:
        if result_status:
            if result_status == "abnormal_all":
                if it.result_status not in ("abnormal", "pending"):
                    continue
            elif it.result_status != result_status:
                continue
        if search and search.lower() not in it.item_name.lower():
            continue
        filtered.append(_item_to_out(it))

    return B2FInspectionBatchDetail(
        batch = _batch_to_out(batch, len(_equipment_items(items))),
        kpi   = kpi,
        items = filtered,
    )


@router.get("/batches/{batch_id}/kpi", summary="取得場次 KPI")
def get_batch_kpi(batch_id: str, db: Session = Depends(get_db)):
    batch = db.get(B2FInspectionBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"找不到場次：{batch_id}")
    items = db.query(B2FInspectionItem).filter(
        B2FInspectionItem.batch_ragic_id == batch_id
    ).all()
    return _calc_kpi(items)


@router.get("/items", summary="跨場次查詢設備巡檢項目")
def list_items(
    batch_id:      Optional[str] = Query(None),
    result_status: Optional[str] = Query(None, alias="status"),
    search:        Optional[str] = Query(None),
    db:            Session = Depends(get_db),
):
    q = db.query(B2FInspectionItem)
    if batch_id:
        q = q.filter(B2FInspectionItem.batch_ragic_id == batch_id)
    items = q.order_by(B2FInspectionItem.batch_ragic_id, B2FInspectionItem.seq_no).all()
    result = []
    for it in items:
        if result_status and it.result_status != result_status:
            continue
        if search and search.lower() not in it.item_name.lower():
            continue
        result.append(_item_to_out(it))
    return result


@router.get("/stats", summary="全站統計", response_model=B2FInspectionStats)
def get_stats(db: Session = Depends(get_db)):
    today     = date.today()

    latest_batch = db.query(B2FInspectionBatch).order_by(
        B2FInspectionBatch.inspection_date.desc()
    ).first()

    latest_batch_out = None
    latest_kpi       = None
    recent_abnormal: list[B2FInspectionItemOut] = []
    recent_pending:  list[B2FInspectionItemOut] = []
    status_dist:     list[StatusDistItem]       = []

    if latest_batch:
        items = db.query(B2FInspectionItem).filter(
            B2FInspectionItem.batch_ragic_id == latest_batch.ragic_id
        ).order_by(B2FInspectionItem.seq_no).all()

        latest_batch_out = _batch_to_out(latest_batch, len(_equipment_items(items)))
        latest_kpi       = _calc_kpi(items)

        eq_items = _equipment_items(items)
        status_counts = Counter(it.result_status for it in eq_items)
        for s, cnt in status_counts.items():
            if cnt > 0:
                status_dist.append(StatusDistItem(
                    status = s,
                    label  = STATUS_LABELS.get(s, s),
                    count  = cnt,
                    color  = STATUS_COLORS.get(s, "#666666"),
                ))

        recent_abnormal = [
            _item_to_out(it) for it in eq_items
            if it.result_status in ("abnormal", "pending")
        ][:10]
        recent_pending = [
            _item_to_out(it) for it in eq_items
            if it.result_status == "pending"
        ][:10]

    abnormal_trend: list[dict] = []
    for i in range(6, -1, -1):
        d     = today - timedelta(days=i)
        d_str = d.strftime("%Y/%m/%d")
        day_batches = db.query(B2FInspectionBatch).filter(
            B2FInspectionBatch.inspection_date == d_str
        ).all()
        abn_count = _abnormal_count_for_batches(db, day_batches)
        abnormal_trend.append({
            "date":           d_str,
            "abnormal_count": abn_count,
            "has_record":     len(day_batches) > 0,
        })

    week_ago = (today - timedelta(days=7)).strftime("%Y/%m/%d")
    total_batches_7d = db.query(B2FInspectionBatch).filter(
        B2FInspectionBatch.inspection_date >= week_ago
    ).count()

    return B2FInspectionStats(
        latest_batch        = latest_batch_out,
        latest_kpi          = latest_kpi,
        recent_abnormal     = recent_abnormal,
        recent_pending      = recent_pending,
        status_distribution = status_dist,
        total_batches_7d    = total_batches_7d,
        abnormal_trend      = abnormal_trend,
    )


@router.get("/items/item-history", summary="依設備名稱查詢近 N 日執行歷史")
def get_item_history(
    item_name: str = Query(...),
    days:      int = Query(30, ge=1, le=90),
    db:        Session = Depends(get_db),
):
    today = date.today()
    rows = (
        db.query(B2FInspectionItem, B2FInspectionBatch)
        .join(B2FInspectionBatch, B2FInspectionItem.batch_ragic_id == B2FInspectionBatch.ragic_id)
        .filter(B2FInspectionItem.item_name == item_name)
        .order_by(B2FInspectionBatch.inspection_date.desc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"找不到設備記錄：{item_name}")

    date_map: dict[str, tuple] = {}
    for item, batch in rows:
        if batch.inspection_date not in date_map:
            date_map[batch.inspection_date] = (item, batch)

    daily_summary = []
    for i in range(days - 1, -1, -1):
        d     = today - timedelta(days=i)
        d_str = d.strftime("%Y/%m/%d")
        if d_str in date_map:
            it, b = date_map[d_str]
            daily_summary.append({
                "inspection_date": d_str,
                "inspector_name":  b.inspector_name or "",
                "start_time":      b.start_time or "",
                "result_status":   it.result_status,
                "result_raw":      it.result_raw or "",
                "abnormal_flag":   bool(it.abnormal_flag),
                "has_record":      True,
                "is_today":        (d == today),
            })
        else:
            daily_summary.append({
                "inspection_date": d_str,
                "inspector_name":  "",
                "start_time":      "",
                "result_status":   "no_record",
                "result_raw":      "",
                "abnormal_flag":   False,
                "has_record":      False,
                "is_today":        (d == today),
            })

    normal_days   = sum(1 for ds in daily_summary if ds["result_status"] == "normal")
    abnormal_days = sum(1 for ds in daily_summary if ds["result_status"] in ("abnormal", "pending"))

    return {
        "item_name":     item_name,
        "daily_summary": daily_summary,
        "stats": {
            "total_days":    days,
            "normal_days":   normal_days,
            "abnormal_days": abnormal_days,
        },
    }


@router.get("/debug/ragic-raw", summary="[除錯] 顯示 Ragic Sheet 3 原始欄位", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def debug_ragic_raw():
    from app.services.b2f_inspection_sync import (
        B2F_SERVER_URL, B2F_ACCOUNT, B2F_SHEET_PATH,
        SESSION_FIELDS, _extract_check_items,
    )
    adapter = RagicAdapter(
        sheet_path=B2F_SHEET_PATH,
        server_url=B2F_SERVER_URL,
        account=B2F_ACCOUNT,
    )
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        return {"error": str(exc)}

    record_ids = list(raw_data.keys())
    if not record_ids:
        return {"error": "無資料", "record_count": 0}

    first_id    = record_ids[0]
    first_rec   = raw_data[first_id]
    check_items = _extract_check_items(first_rec)

    return {
        "record_count":         len(raw_data),
        "first_record_id":      first_id,
        "all_fields":           list(first_rec.keys()),
        "session_fields":       list(SESSION_FIELDS),
        "check_items_detected": check_items,
        "check_items_count":    len(check_items),
        "first_record_values":  {
            k: str(v)[:100]
            for k, v in first_rec.items()
            if k in check_items
        },
    }
