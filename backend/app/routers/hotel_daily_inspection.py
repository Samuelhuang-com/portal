"""
飯店每日巡檢 API Router
Prefix: /api/v1/hotel-daily-inspection

2026-11-10 改版：照抄 mall_facility_inspection router（Samuel 裁示：完全照商場模組的程式與架構）。
頁籤（sheet_key）與 Ragic 來源見 app/services/hotel_daily_inspection_sources.py：
  rf / 5f-10f / 4f / b1f-hv / b1f-office / b4f-water / b4f-ac（各含現行表＋封存表）。
判定一律用 app/services/hotel_daily_inspection_sheet（與每日巡檢表 Drawer、月曆格、樓層巡檢圖同一套）。

端點：
  GET  /sheets、POST /sync/all、POST /{sheet_key}/sync、GET /verify-count、GET /verify-diff
  GET  /{sheet_key}/stats、/{sheet_key}/batches、/{sheet_key}/batches/{batch_id}
  GET  /dashboard/summary、/dashboard/monthly-summary、/daily-sheet、/daily-calendar
  GET  /daily-form（舊版型；前端「每日巡檢表」TAB 比照商場隱藏，端點保留不移除）
"""
from collections import Counter
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission, require_roles
from app.models.hotel_daily_inspection import HotelDIBatch, HotelDIItem
from app.services.hotel_daily_inspection_sync import HDI_SERVER_URL, HDI_ACCOUNT, SHEET_CONFIGS
from app.services.ragic_verify_utils import (
    read_portal_count_and_last_sync, read_portal_ragic_ids,
    fetch_ragic_count_multi, fetch_ragic_url_map_multi,
    build_verify_count_response, build_verify_diff_response,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


# ── Schema ────────────────────────────────────────────────────────────────────

class InspectionSheetConfig(BaseModel):
    key:         str
    floor:       str
    title:       str
    ragic_url:   str
    description: str


# ── 頁籤設定（由 hotel_daily_inspection_sources 產生；ragic_url 指向現行表）──────

def _build_sheet_configs() -> List[InspectionSheetConfig]:
    from app.services.hotel_daily_inspection_sources import TAB_LABELS, TABS, live_source, sheet_url
    from app.services.hotel_daily_inspection_sheet import EXCEL_FLOOR_LABEL
    out = []
    for tab in TABS:
        src = live_source(tab)
        out.append(InspectionSheetConfig(
            key=tab,
            floor=EXCEL_FLOOR_LABEL[tab],
            title=f"飯店每日巡檢 - {TAB_LABELS[tab]}",
            ragic_url=sheet_url(src) if src else "",
            description=f"英迪格飯店工務每日巡檢：{TAB_LABELS[tab]}",
        ))
    return out


SHEET_CONFIGS: List[InspectionSheetConfig] = _build_sheet_configs()

VALID_KEYS = {c.key for c in SHEET_CONFIGS}


def _src_label(batch_id: str) -> str:
    """場次所屬來源名稱（新表／各封存表）；新舊連結同時存在（2026-11-10 裁示）。"""
    from app.services.hotel_daily_inspection_sources import batch_source
    src = batch_source(batch_id)
    return src.label if src else ""


def is_live_batch(batch_id: str) -> bool:
    from app.services.hotel_daily_inspection_sources import is_live_batch as _f
    return _f(batch_id)


# ── 頁籤名稱（2026-11-10：可在頁面上修改，套用到整個頁面）────────────────────────
TAB_MODULE = "hotel_daily_inspection"
TAB_LABEL_PERMISSION = "hotel_daily_inspection_tab_label_edit"


def _labels(db: Session) -> dict[str, str]:
    from app.services.hotel_daily_inspection_sources import TAB_LABELS
    from app.services.module_tab_labels import get_labels
    return get_labels(db, TAB_MODULE, TAB_LABELS)


def _relabel_sheet(data: dict, labels: dict[str, str]) -> dict:
    """每日巡檢表（build_daily_sheet 結果）的樓層／頁籤名稱換成目前名稱。"""
    for f in data.get("floors", []):
        if f.get("key") in labels:
            f["floor"] = f["title"] = labels[f["key"]]
    for r in data.get("rows", []):
        if r.get("source_tab") in labels:
            r["floor"] = labels[r["source_tab"]]
    for x in data.get("extra_issues", []):
        if x.get("source_tab") in labels:
            x["floor"] = labels[x["source_tab"]] + ("（舊表）" if x.get("legacy") else "")
    return data


class TabLabelsIn(BaseModel):
    labels: dict[str, Optional[str]]


@router.get("/tab-labels", summary="取得頁籤名稱（含預設值）", tags=["飯店每日巡檢"])
def get_tab_labels(db: Session = Depends(get_db)):
    from app.services.hotel_daily_inspection_sources import TAB_LABELS, TABS
    return {"order": TABS, "defaults": TAB_LABELS, "labels": _labels(db),
            "edit_permission": TAB_LABEL_PERMISSION}


@router.put("/tab-labels", summary="修改頁籤名稱（空白＝回到預設）", tags=["飯店每日巡檢"])
def put_tab_labels(
    body: TabLabelsIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission(TAB_LABEL_PERMISSION)),
):
    from app.services.hotel_daily_inspection_sources import TAB_LABELS
    from app.services.module_tab_labels import save_labels
    user = getattr(current_user, "email", None) or str(getattr(current_user, "id", ""))
    return {"labels": save_labels(db, TAB_MODULE, TAB_LABELS, body.labels, user)}


# ── 業務邏輯輔助 ───────────────────────────────────────────────────────────────

def _calc_kpi(items: list[HotelDIItem]) -> dict:
    """計算一組巡檢項目的 KPI 統計（排除 is_note 項目）"""
    # 飯店：附註欄（note）不計；填數字欄（measure）算已填（2026-11-10）
    scored = [it for it in items if not it.is_note and it.result_status != "note"]
    total     = len(scored)
    normal    = sum(1 for it in scored if it.result_status == "normal")
    abnormal  = sum(1 for it in scored if it.result_status == "abnormal")
    pending   = sum(1 for it in scored if it.result_status == "pending")
    unchecked = sum(1 for it in scored if it.result_status == "unchecked")
    measure   = sum(1 for it in scored if it.result_status == "measure")
    checked   = normal + abnormal + pending + measure

    completion_rate = round(checked / total * 100, 1) if total > 0 else 0.0
    return {
        "total":           total,
        "normal":          normal,
        "abnormal":        abnormal,
        "pending":         pending,
        "unchecked":       unchecked,
        "checked":         checked,
        "completion_rate": completion_rate,
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /sheets
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/sheets",
    summary="取得工務巡檢 Sheet 設定清單",
    response_model=List[InspectionSheetConfig],
    tags=["飯店每日巡檢"],
)
def get_sheets():
    """
    回傳飯店每日巡檢各樓層 Sheet 設定，
    包含 Ragic URL 供前端導頁或顯示摘要使用。
    """
    return SHEET_CONFIGS


# ══════════════════════════════════════════════════════════════════════════════
# POST /sync/all  ← 必須在 /{sheet_key}/sync 之前定義，避免 "all" 被解析為 sheet_key
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/sync/all",
    summary="從 Ragic 同步全部頁籤（背景執行）",
    tags=["飯店每日巡檢"],
)
async def sync_all_sheets(background_tasks: BackgroundTasks):
    """觸發背景同步：全部頁籤，立即回傳，不阻塞畫面"""
    from app.services.hotel_daily_inspection_sync import sync_all
    background_tasks.add_task(sync_all)
    return {"status": "ok", "message": "全部頁籤 同步已在背景啟動"}


# ── /verify-count／/verify-diff ─────────────────────────────────────────────────
# 全部頁籤 都 pivot 進同一張 HotelDIBatch（sheet_key 區分），做法同飯店每日巡檢。

def _hdi_sheets() -> list[dict]:
    """所有 Ragic 來源（現行＋封存），供 verify 多 Sheet 比對；key 為 source_key（場次 ID 前綴）。"""
    from app.services.hotel_daily_inspection_sources import SOURCES
    return [
        {"sheet_key": src.source_key, "sheet_path": src.sheet_path, "server_url": HDI_SERVER_URL, "account": HDI_ACCOUNT}
        for src in SOURCES
        if src.sheet_path          # rf_legacy 已無 Ragic 表，不比對
    ]


@router.get("/verify-count", summary="與 Ragic 數量比對（管理員，全部來源加總）",
            dependencies=[Depends(require_roles("system_admin"))])
async def verify_count(db: Session = Depends(get_db)):
    portal_count, last_synced_at = await read_portal_count_and_last_sync(
        db, HotelDIBatch, "飯店每日巡檢"
    )
    try:
        ragic_count = await fetch_ragic_count_multi(_hdi_sheets())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ragic 連線失敗：{exc}")
    return build_verify_count_response("飯店每日巡檢", portal_count, ragic_count, last_synced_at)


@router.get("/verify-diff", summary="與 Ragic 明細差集比對（管理員，全部來源加總）",
            dependencies=[Depends(require_roles("system_admin"))])
async def verify_diff(db: Session = Depends(get_db)):
    try:
        ragic_url_map = await fetch_ragic_url_map_multi(_hdi_sheets())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ragic 連線失敗：{exc}")
    portal_ids = await read_portal_ragic_ids(db, HotelDIBatch)
    return build_verify_diff_response(ragic_url_map, portal_ids)


# ══════════════════════════════════════════════════════════════════════════════
# POST /{sheet_key}/sync
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{sheet_key}/sync",
    summary="從 Ragic 同步指定樓層（背景執行）",
    tags=["飯店每日巡檢"],
)
async def sync_sheet(sheet_key: str, background_tasks: BackgroundTasks):
    """觸發背景同步：指定 sheet_key，立即回傳，不阻塞畫面"""
    if sheet_key not in VALID_KEYS:
        raise HTTPException(
            status_code=404,
            detail=f"未知的 sheet_key: {sheet_key}，有效值：{sorted(VALID_KEYS)}",
        )
    from app.services.hotel_daily_inspection_sync import sync_sheet as _sync
    background_tasks.add_task(_sync, sheet_key)
    return {"status": "ok", "message": f"{sheet_key} 同步已在背景啟動"}


# ══════════════════════════════════════════════════════════════════════════════
# GET /{sheet_key}/stats
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{sheet_key}/stats",
    summary="取得指定樓層 Dashboard 統計",
    tags=["飯店每日巡檢"],
)
def get_sheet_stats(
    sheet_key: str,
    target_date: Optional[str] = Query(
        None,
        description="查詢日期 YYYY/MM/DD，不填則取最新場次"
    ),
    db: Session = Depends(get_db),
):
    if sheet_key not in VALID_KEYS:
        raise HTTPException(status_code=404, detail=f"未知的 sheet_key: {sheet_key}")

    today = date.today()

    # ── 取最新（或指定日期）場次 ─────────────────────────────────────────────
    q = db.query(HotelDIBatch).filter(HotelDIBatch.sheet_key == sheet_key)
    if target_date:
        q = q.filter(HotelDIBatch.inspection_date == target_date)

    latest_batch = q.order_by(HotelDIBatch.inspection_date.desc()).first()

    latest_kpi   = None
    latest_batch_info = None
    recent_abnormal: list[dict] = []

    if latest_batch:
        items = (
            db.query(HotelDIItem)
            .filter(HotelDIItem.batch_ragic_id == latest_batch.ragic_id)
            .order_by(HotelDIItem.seq_no)
            .all()
        )
        latest_kpi = _calc_kpi(items)
        latest_batch_info = {
            "ragic_id":       latest_batch.ragic_id,
            "inspection_date": latest_batch.inspection_date,
            "inspector_name": latest_batch.inspector_name,
            "start_time":     latest_batch.start_time,
            "end_time":       latest_batch.end_time,
            "work_hours":     latest_batch.work_hours,
        }
        recent_abnormal = [
            {
                "item_name":     it.item_name,
                "result_raw":    it.result_raw,
                "result_status": it.result_status,
            }
            for it in items
            if it.result_status in ("abnormal", "pending") and not it.is_note
        ][:20]

    # ── 近 7 日場次數 ─────────────────────────────────────────────────────────
    week_ago = (today - timedelta(days=7)).strftime("%Y/%m/%d")
    batches_7d = (
        db.query(HotelDIBatch)
        .filter(
            HotelDIBatch.sheet_key == sheet_key,
            HotelDIBatch.inspection_date >= week_ago,
        )
        .count()
    )

    # ── 近 7 日異常趨勢 ───────────────────────────────────────────────────────
    abnormal_trend = []
    for i in range(6, -1, -1):
        d     = today - timedelta(days=i)
        d_str = d.strftime("%Y/%m/%d")

        day_batches = (
            db.query(HotelDIBatch)
            .filter(
                HotelDIBatch.sheet_key == sheet_key,
                HotelDIBatch.inspection_date == d_str,
            )
            .all()
        )

        abn_count = 0
        for b in day_batches:
            abn_count += (
                db.query(HotelDIItem)
                .filter(
                    HotelDIItem.batch_ragic_id == b.ragic_id,
                    HotelDIItem.result_status.in_(["abnormal", "pending"]),
                    HotelDIItem.is_note == False,
                )
                .count()
            )

        abnormal_trend.append({
            "date":           d_str,
            "abnormal_count": abn_count,
            "has_record":     len(day_batches) > 0,
        })

    return {
        "sheet_key":       sheet_key,
        "latest_batch":    latest_batch_info,
        "latest_kpi":      latest_kpi,
        "recent_abnormal": recent_abnormal,
        "total_batches_7d": batches_7d,
        "abnormal_trend":  abnormal_trend,
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /{sheet_key}/batches
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/{sheet_key}/batches",
    summary="取得指定樓層巡檢場次清單",
    tags=["飯店每日巡檢"],
)
def list_batches(
    sheet_key:  str,
    year_month: Optional[str] = Query(None, description="篩選年月，如 2026/04"),
    db: Session = Depends(get_db),
):
    if sheet_key not in VALID_KEYS:
        raise HTTPException(status_code=404, detail=f"未知的 sheet_key: {sheet_key}")

    q = db.query(HotelDIBatch).filter(HotelDIBatch.sheet_key == sheet_key)
    if year_month:
        q = q.filter(HotelDIBatch.inspection_date.like(f"{year_month}%"))

    batches = q.order_by(HotelDIBatch.inspection_date.desc()).all()

    # 2026-10-05：異常／待處理改用與每日巡檢表 Drawer 相同的判定（item_kpi）——
    #   原本 _calc_kpi 沿用同步時的 result_status，溫度、度數被算成異常，清單每天「有異常」。
    #   item 一次查完，不再每個場次查一次。
    from app.services.hotel_daily_inspection_sheet import item_kpi
    from app.services.hotel_daily_inspection_sources import record_url as ragic_record_url

    items_by_batch: dict[str, list[HotelDIItem]] = {b.ragic_id: [] for b in batches}
    ids = list(items_by_batch.keys())
    for i in range(0, len(ids), 500):
        for it in db.query(HotelDIItem).filter(HotelDIItem.batch_ragic_id.in_(ids[i:i + 500])).all():
            items_by_batch.setdefault(it.batch_ragic_id, []).append(it)

    result = []
    for b in batches:
        kpi = item_kpi(sheet_key, items_by_batch.get(b.ragic_id, []))
        result.append({
            "id":              b.ragic_id,
            "inspection_date": b.inspection_date,
            "inspector_name":  b.inspector_name,
            "start_time":      b.start_time,
            "end_time":        b.end_time,
            "work_hours":      b.work_hours,
            "estimated_minutes": b.estimated_minutes,
            "ragic_url":       ragic_record_url(b.ragic_id),
            "source_label":    _src_label(b.ragic_id),
            "archived":        not is_live_batch(b.ragic_id),
            "total":           kpi["total"],
            "checked":         kpi["checked"],
            "abnormal":        kpi["abnormal"],
            "pending":         kpi["pending"],
            "unchecked":       kpi["unchecked"],
            "measure":         kpi["measure"],
            "completion_rate": kpi["completion_rate"],
        })
    return result


# ── GET /{sheet_key}/batches/{batch_id}  — 場次明細（樓層 TAB 點列開 Drawer）────
# 2026-10-05 新增：比照整棟巡檢 FloorInspectionList 的明細 Drawer。
# 每個欄位的 status 用 item_status（與每日巡檢表 Drawer、月曆格同一套判定）。
# 附圖：sync 不收「拍照」欄位（_extract_check_items 排除），DB 沒有檔名，這裡不回附圖。

@router.get(
    "/{sheet_key}/batches/{batch_id}",
    summary="取得指定樓層單一巡檢場次明細",
    tags=["飯店每日巡檢"],
)
def get_batch_detail(
    sheet_key: str,
    batch_id:  str,
    db: Session = Depends(get_db),
):
    from app.services.hotel_daily_inspection_sheet import item_kpi, item_status
    from app.services.hotel_daily_inspection_sources import record_url as ragic_record_url

    if sheet_key not in VALID_KEYS:
        raise HTTPException(status_code=404, detail=f"未知的 sheet_key: {sheet_key}")
    b = (
        db.query(HotelDIBatch)
        .filter(HotelDIBatch.sheet_key == sheet_key, HotelDIBatch.ragic_id == batch_id)
        .first()
    )
    if not b:
        raise HTTPException(status_code=404, detail=f"找不到場次：{batch_id}")
    items = (
        db.query(HotelDIItem)
        .filter(HotelDIItem.batch_ragic_id == b.ragic_id)
        .order_by(HotelDIItem.seq_no)
        .all()
    )
    return {
        "batch": {
            "ragic_id":        b.ragic_id,
            "sheet_key":       b.sheet_key,
            "inspection_date": b.inspection_date,
            "inspector_name":  b.inspector_name,
            "start_time":      b.start_time,
            "end_time":        b.end_time,
            "work_hours":      b.work_hours,
            "estimated_minutes": b.estimated_minutes,
            "ragic_url":       ragic_record_url(b.ragic_id),
            "source_label":    _src_label(b.ragic_id),
            "archived":        not is_live_batch(b.ragic_id),
            "tab_label":       _labels(db).get(b.sheet_key, b.sheet_key),
        },
        "kpi":   item_kpi(sheet_key, items),
        "items": [
            {
                "ragic_id":    it.ragic_id,
                "seq_no":      it.seq_no,
                "item_name":   it.item_name,
                "result_raw":  it.result_raw,
                "status":      item_status(sheet_key, it.item_name, it.result_raw, bool(it.is_note)),
            }
            for it in items
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
# ── 工時解析輔助函式 ─────────────────────────────────────────────────────────────

def _parse_minutes(start: str, end: str) -> int:
    """解析 HH:MM 格式的開始/結束時間，回傳分鐘數差值；格式無效時回傳 0。"""
    import re
    def to_min(t: str):
        m = re.match(r'^(\d{1,2}):(\d{2})$', t.strip())
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))
        return None
    s, e = to_min(start), to_min(end)
    if s is None or e is None:
        return 0
    diff = e - s
    return diff + 24 * 60 if diff < 0 else diff


# GET /dashboard/summary  — 跨 Sheet 統計（index.tsx Dashboard 用）
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/dashboard/summary",
    summary="取得全體飯店每日巡檢 Dashboard 統計（跨 Sheet）",
    tags=["飯店每日巡檢"],
)
def get_dashboard_summary(
    target_date: Optional[str] = Query(
        None,
        description="查詢日期 YYYY/MM/DD，不填則取今日"
    ),
    db: Session = Depends(get_db),
):
    labels = _labels(db)
    if not target_date:
        target_date = date.today().strftime("%Y/%m/%d")

    results = []
    for cfg in SHEET_CONFIGS:
        key = cfg.key

        # 指定日期的所有場次
        day_batches = (
            db.query(HotelDIBatch)
            .filter(
                HotelDIBatch.sheet_key == key,
                HotelDIBatch.inspection_date == target_date,
            )
            .all()
        )

        total_batches   = len(day_batches)
        total_items     = 0
        checked_items   = 0
        abnormal_items  = 0
        pending_items   = 0
        unchecked_items = 0
        total_minutes   = 0

        for b in day_batches:
            items = (
                db.query(HotelDIItem)
                .filter(
                    HotelDIItem.batch_ragic_id == b.ragic_id,
                    HotelDIItem.is_note == False,
                )
                .all()
            )
            kpi = _calc_kpi(items)
            total_items     += kpi["total"]
            checked_items   += kpi["checked"]
            abnormal_items  += kpi["abnormal"]
            pending_items   += kpi["pending"]
            unchecked_items += kpi["unchecked"]
            total_minutes   += _parse_minutes(b.start_time or "", b.end_time or "")

        completion_rate = (
            round(checked_items / total_items * 100, 1) if total_items > 0 else 0.0
        )

        results.append({
            "key":             key,
            "floor":           labels.get(cfg.key, cfg.floor),
            "title":           labels.get(cfg.key, cfg.title),
            "total_batches":   total_batches,
            "total_items":     total_items,
            "checked_items":   checked_items,
            "abnormal_items":  abnormal_items,
            "pending_items":   pending_items,
            "unchecked_items": unchecked_items,
            "completion_rate": completion_rate,
            "has_data":        total_batches > 0,
            "total_minutes":   total_minutes,
        })

    return {"target_date": target_date, "sheets": results}


# ══════════════════════════════════════════════════════════════════════════════
# GET /dashboard/monthly-summary  — 跨 Sheet 月份統計（Dashboard 查詢月份用）
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/dashboard/monthly-summary",
    summary="取得飯店每日巡檢 Dashboard 月份統計（跨頁籤）",
    tags=["飯店每日巡檢"],
)
def get_dashboard_monthly_summary(
    year:  Optional[int] = Query(None, ge=2020, le=2030, description="年份（舊呼叫方式：year + month=1~12）"),
    month: Optional[str] = Query(None, description="YYYY-MM（商場同款呼叫方式）；或搭配 year 傳 1~12"),
    db: Session = Depends(get_db),
):
    """
    兩種呼叫方式（2026-11-10 改版後相容）：
      1. ?month=YYYY-MM（本模組 Dashboard，照商場）
      2. ?year=2026&month=4（飯店管理 Dashboard、決策駕駛艙既有呼叫，回傳格式不變）
    每個頁籤同時回傳：
      商場同款欄位 — month_count、missing_count、missing_days、latest_batch_date、has_today、
                     is_current_month、trend_7d、has_data
      舊有欄位     — total_batches、total_items、checked_items、abnormal_items、pending_items、
                     unchecked_items、completion_rate、total_minutes
    """
    labels = _labels(db)
    from app.core.date_utils import get_month_range, to_ragic_year_month

    legacy_call = year is not None
    today = date.today()
    if legacy_call:
        try:
            mm = int(month or today.month)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"month 格式錯誤：{month}")
        if not 1 <= mm <= 12:
            raise HTTPException(status_code=422, detail=f"month 必須 1~12：{month}")
        month_str = f"{year}-{mm:02d}"
    else:
        month_str = month or today.strftime("%Y-%m")

    start_date, end_date = get_month_range(month_str)
    year_month   = to_ragic_year_month(month_str)        # "2026/05"
    is_current   = (start_date.year == today.year and start_date.month == today.month)
    missing_end  = today if is_current else end_date
    trend_ref    = today if is_current else end_date
    ref_date_str = today.strftime("%Y/%m/%d") if is_current else end_date.strftime("%Y/%m/%d")

    month_batches_all = (
        db.query(HotelDIBatch)
        .filter(HotelDIBatch.inspection_date.like(f"{year_month}%"))
        .all()
    )
    items_by_batch: dict[str, list[HotelDIItem]] = {b.ragic_id: [] for b in month_batches_all}
    ids = list(items_by_batch.keys())
    for i in range(0, len(ids), 500):
        for it in db.query(HotelDIItem).filter(HotelDIItem.batch_ragic_id.in_(ids[i:i + 500])).all():
            items_by_batch.setdefault(it.batch_ragic_id, []).append(it)

    results = []
    for cfg in SHEET_CONFIGS:
        key = cfg.key
        month_batches = [b for b in month_batches_all if b.sheet_key == key]
        month_count = len(month_batches)
        latest_batch_date = max((b.inspection_date for b in month_batches), default="")
        inspected_days = {b.inspection_date for b in month_batches}
        has_today = ref_date_str in inspected_days

        missing_days: list[str] = []
        current = start_date
        while current <= missing_end:
            d_str = current.strftime("%Y/%m/%d")
            if d_str not in inspected_days:
                missing_days.append(d_str)
            current += timedelta(days=1)

        trend_7d = []
        for i in range(6, -1, -1):
            d_str = (trend_ref - timedelta(days=i)).strftime("%Y/%m/%d")
            trend_7d.append({"date": d_str, "has_record": d_str in inspected_days})

        tot = chk = abn = pen = unc = mins = 0
        for b in month_batches:
            kpi = _calc_kpi(items_by_batch.get(b.ragic_id, []))
            tot += kpi["total"]; chk += kpi["checked"]; abn += kpi["abnormal"]
            pen += kpi["pending"]; unc += kpi["unchecked"]
            mins += _parse_minutes(b.start_time or "", b.end_time or "")

        results.append({
            "key":               key,
            "floor":             labels.get(cfg.key, cfg.floor),
            "title":             labels.get(cfg.key, cfg.title),
            "month_count":       month_count,
            "missing_count":     len(missing_days),
            "missing_days":      missing_days,
            "latest_batch_date": latest_batch_date,
            "has_today":         has_today,
            "is_current_month":  is_current,
            "trend_7d":          trend_7d,
            "has_data":          month_count > 0,
            # 舊有欄位（飯店管理 Dashboard／決策駕駛艙）
            "total_batches":     month_count,
            "total_items":       tot,
            "checked_items":     chk,
            "abnormal_items":    abn,
            "pending_items":     pen,
            "unchecked_items":   unc,
            "completion_rate":   round(chk / tot * 100, 1) if tot else 0.0,
            "total_minutes":     mins,
        })

    t_items = sum(s["total_items"] for s in results)
    t_chk   = sum(s["checked_items"] for s in results)
    return {
        "year":            start_date.year,
        "month":           start_date.month if legacy_call else month_str,
        "year_month":      year_month,
        "total_items":     t_items,
        "checked_items":   t_chk,
        "abnormal_items":  sum(s["abnormal_items"] for s in results),
        "total_minutes":   sum(s["total_minutes"] for s in results),
        "completion_rate": round(t_chk / t_items * 100, 1) if t_items else 0.0,
        "sheets":          results,
    }


# ── GET /daily-sheet ──────────────────────────────────────────────────────────
# 2026-10-04 新增：Dashboard 月曆格的下一層 —— 指定日期，以 Excel「(飯店)每日設備巡檢表_1029」
# 原版型呈現 全部頁籤 的實際巡檢結果。對應邏輯見 services/hotel_daily_inspection_sheet.py。

@router.get(
    "/daily-sheet",
    summary="取得指定日期的飯店每日巡檢表（Excel 版型）",
    tags=["飯店每日巡檢"],
)
def get_daily_sheet(
    date: str = Query(..., description="巡檢日期 YYYY-MM-DD 或 YYYY/MM/DD"),
    db: Session = Depends(get_db),
):
    from app.services.hotel_daily_inspection_sheet import build_daily_sheet, normalize_date

    insp_date = normalize_date(date)
    if not insp_date:
        raise HTTPException(status_code=422, detail=f"日期格式錯誤：{date}")

    batches = (
        db.query(HotelDIBatch)
        .filter(HotelDIBatch.inspection_date == insp_date)
        .all()
    )
    items_by_batch: dict[str, list[HotelDIItem]] = {b.ragic_id: [] for b in batches}
    if batches:
        for it in (
            db.query(HotelDIItem)
            .filter(HotelDIItem.batch_ragic_id.in_(list(items_by_batch.keys())))
            .all()
        ):
            items_by_batch.setdefault(it.batch_ragic_id, []).append(it)

    data = _relabel_sheet(build_daily_sheet(batches, items_by_batch), _labels(db))
    return {"date": insp_date, **data}


# ── GET /daily-form ───────────────────────────────────────────────────────────

@router.get(
    "/daily-form",
    summary="取得每日巡檢表彙整（依標準模板與各 Sheet 比對）",
    tags=["飯店每日巡檢"],
)
def get_daily_form(
    year:            int           = Query(...,  ge=2020, le=2030, description="年份"),
    month:           int           = Query(...,  ge=1,    le=12,   description="月份（1–12）"),
    inspection_date: Optional[str] = Query(None, description="指定日期 YYYY/MM/DD；不填則取整月彙整"),
    db: Session = Depends(get_db),
):
    """
    依標準模板（(飯店)每日設備巡檢表_1029.xlsx）與各樓層 Sheet 實際巡檢資料比對。

    inspection_date 不填 → 整月所有 batch 彙整。
    inspection_date 填入 → 只取該日 batch；無資料時所有列 matched=False。
    """
    from app.services.daily_inspection_builder import build_daily_inspection_table
    rows = build_daily_inspection_table(
        year=year, month=month, db=db,
        inspection_date=inspection_date,
    )
    has_data_today = any(r["matched"] for r in rows) if inspection_date else None
    return {
        "year":            year,
        "month":           month,
        "inspection_date": inspection_date,
        "has_data_today":  has_data_today,
        "rows":            rows,
    }


# ── 月曆格共用建表（2026-10-05）──────────────────────────────────────────────
# ⚠ 異常／待處理的判定改用 services/hotel_daily_inspection_sheet（與 Drawer 同一套）：
#   原本直接加總同步時的 result_status，溫度、濕度、電表度數這類「填數字」欄位一律被當成異常，
#   造成 4F、1F~3F 幾乎每天 ⚠、點進 Drawer 卻找不到異常項目。
# 完成率維持原口徑（已填項目 ÷ 全部項目）。
# 每格附 issues（哪一項異常），供月曆格 Tooltip 直接顯示。

def _build_daily_calendar(year: int, month: int, db: Session) -> dict:
    labels = _labels(db)
    import calendar as cal_mod
    from app.services.hotel_daily_inspection_sheet import build_daily_sheet, day_issues

    max_day           = cal_mod.monthrange(year, month)[1]
    year_month_prefix = f"{year}/{month:02d}/"

    month_batches = (
        db.query(HotelDIBatch)
        .filter(HotelDIBatch.inspection_date.like(f"{year_month_prefix}%"))
        .all()
    )
    items_by_batch: dict[str, list[HotelDIItem]] = {b.ragic_id: [] for b in month_batches}
    ids = list(items_by_batch.keys())
    for i in range(0, len(ids), 500):
        for it in db.query(HotelDIItem).filter(HotelDIItem.batch_ragic_id.in_(ids[i:i + 500])).all():
            items_by_batch.setdefault(it.batch_ragic_id, []).append(it)

    by_date: dict[int, list[HotelDIBatch]] = {}
    for b in month_batches:
        try:
            day = int(b.inspection_date.split("/")[2])
        except (IndexError, ValueError):
            continue
        by_date.setdefault(day, []).append(b)

    issues_by_day: dict[int, dict[str, list[dict]]] = {}
    for day, bl in by_date.items():
        sheet = build_daily_sheet(bl, {b.ragic_id: items_by_batch.get(b.ragic_id, []) for b in bl})
        issues_by_day[day] = day_issues(_relabel_sheet(sheet, labels))

    sheets_out = []
    for cfg in SHEET_CONFIGS:
        key   = cfg.key
        daily: dict[str, dict] = {}
        for day in range(1, max_day + 1):
            day_batches = [b for b in by_date.get(day, []) if b.sheet_key == key]
            if not day_batches:
                daily[str(day)] = {
                    "has_record":      False,
                    "completion_rate": 0,
                    "abnormal_count":  0,
                    "pending_count":   0,
                    "issues":          [],
                }
                continue

            total_items = checked_items = 0
            for b in day_batches:
                kpi = _calc_kpi(items_by_batch.get(b.ragic_id, []))
                total_items   += kpi["total"]
                checked_items += kpi["checked"]

            issues = issues_by_day.get(day, {}).get(key, [])
            daily[str(day)] = {
                "has_record":      True,
                "completion_rate": round(checked_items / total_items * 100) if total_items > 0 else 0,
                "abnormal_count":  sum(1 for x in issues if x["status"] == "abnormal"),
                "pending_count":   sum(1 for x in issues if x["status"] == "pending"),
                "issues":          issues,
            }

        sheets_out.append({
            "key":   key,
            "floor": labels.get(cfg.key, cfg.floor),
            "title": labels.get(cfg.key, cfg.title),
            "daily": daily,
        })

    return {
        "year":    year,
        "month":   month,
        "max_day": max_day,
        "sheets":  sheets_out,
    }


# ── GET /daily-calendar ───────────────────────────────────────────────────────

@router.get(
    "/daily-calendar",
    summary="取得指定月份每日巡檢狀況（各樓層 × 各日，Dashboard 月曆格用）",
    tags=["飯店每日巡檢"],
)
def get_daily_calendar(
    year:  int = Query(..., ge=2020, le=2030, description="年份"),
    month: int = Query(..., ge=1,    le=12,   description="月份（1–12）"),
    db: Session = Depends(get_db),
):
    """
    回傳當月每日 × 每個 Sheet（樓層）的巡檢狀態，供 Dashboard 月曆格使用。
    回傳：
      max_day   — 當月天數
      sheets[]  — 各樓層，含 daily{day_str: {has_record, completion_rate, abnormal_count, pending_count, issues[]}}
    """
    # 2026-10-05：改用與每日巡檢表 Drawer 相同的判定（_build_daily_calendar）
    return _build_daily_calendar(year, month, db)
