"""
IHG 客房保養 API Router
Prefix: /api/v1/ihg-room-maintenance

端點說明：
  GET  /matrix     — 年度矩陣表（房號 × 月份）
  GET  /stats      — KPI 統計卡
  GET  /records    — 原始記錄清單（含篩選）
  GET  /debug-raw  — Ragic 原始欄位結構（除錯用）
  GET  /{ragic_id} — 單筆明細（含子表格）
  POST /sync       — 觸發同步

矩陣表邏輯：
  - 以房號為行、月份（1-12）為欄
  - 每格顯示狀態、日期、人員
  - 狀態判斷：
      completed  → 已完成（green）
      overdue    → 逾期（red）    = 本月應保養但超過今日且未完成
      scheduled  → 本月應保養（yellow/blue）
      pending    → 未完成（grey）

統計卡：
  全年應保養數、已完成數、未完成數、逾期數、完成率
"""
import json
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.time import twnow
from app.models.ihg_room_maintenance import IHGRoomMaintenanceMaster, IHGRoomMaintenanceDetail
from app.services.ihg_room_maintenance_sync import sync_from_ragic

router = APIRouter()

# ── 保養檢查欄位：忽略清單 ────────────────────────────────────────────────────
# 明確不屬於保養檢查項目的欄位名稱（精確匹配）
_IGNORE_FIELD_NAMES: frozenset[str] = frozenset({
    # 使用者指定忽略
    "項目", "更換日期", "費用", "設備保養上傳照片", "設備",
    # 已知 metadata 欄位
    "保養月份", "保養人員", "保養時間起", "保養時間迄", "保養日期",
    "工時計算", "房號", "複核人員", "是否有陽台",
})

def _is_check_field(key: str, value: object) -> bool:
    """
    判斷是否為有效的保養檢查項目欄位。
    符合條件的欄位值：正常 / 當時維護完成 / 等待維護(待料中) / ""（未檢查）
    """
    if key in _IGNORE_FIELD_NAMES:
        return False
    if "上傳照片" in key:
        return False
    if isinstance(value, str) and value in ("正常", "當時維護完成", "等待維護(待料中)", ""):
        return True
    # None 視為未檢查
    if value is None:
        return True
    return False


# ── 輔助 ─────────────────────────────────────────────────────────────────────

def _cell_status(rec: IHGRoomMaintenanceMaster) -> str:
    """
    計算矩陣格基礎狀態（check 欄位結果會在 /matrix 再覆蓋）
    Ragic 無逾期概念，只區分：本月應保養 / 待排程
    最終有效狀態：completed / abnormal / scheduled / pending
    """
    today = twnow()
    try:
        if rec.maint_year and rec.maint_month:
            rec_year  = int(rec.maint_year)
            rec_month = int(rec.maint_month)
            if (rec_year, rec_month) == (today.year, today.month):
                return "scheduled"
    except (ValueError, TypeError):
        pass
    return "pending"


def _room_sort_key(room_no: str) -> tuple:
    """房號排序：先依樓層數字、再依房間序號"""
    digits = "".join(c for c in room_no if c.isdigit())
    try:
        n = int(digits)
        floor = n // 100
        seq   = n % 100
        return (floor, seq)
    except ValueError:
        return (999, 0)


# ── GET /debug-raw ────────────────────────────────────────────────────────────

@router.get("/debug-raw", summary="[除錯] 查看 Ragic IHG Sheet 4 原始欄位結構")
async def debug_raw():
    """
    直接回傳 Ragic Sheet 4 第一筆記錄的原始 key/value，
    用於確認欄位 ID 與中文 label。
    ⚠️ 建議同步後刪除或加 auth 保護。
    """
    from app.services.ragic_adapter import RagicAdapter
    from app.services.ihg_room_maintenance_sync import IHG_SERVER_URL, IHG_ACCOUNT, IHG_SHEET_PATH

    adapter = RagicAdapter(
        sheet_path=IHG_SHEET_PATH,
        server_url=IHG_SERVER_URL,
        account=IHG_ACCOUNT,
    )
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ragic 拉取失敗：{exc}")

    total = len(raw_data)
    first_id, first_rec = next(iter(raw_data.items()), (None, {}))

    # 取第一筆完整記錄（含子表格）
    detail_structure = {}
    if first_id:
        try:
            full = await adapter.fetch_one(str(first_id))
            if str(first_id) in full and len(full) == 1:
                full = full[str(first_id)]
            detail_structure = {
                k: repr(v)[:120] for k, v in full.items()
            }
        except Exception as exc:
            detail_structure = {"error": str(exc)}

    return {
        "sheet_path": IHG_SHEET_PATH,
        "server_url": IHG_SERVER_URL,
        "account": IHG_ACCOUNT,
        "total_records": total,
        "first_ragic_id": first_id,
        "master_keys": {k: repr(v)[:80] for k, v in first_rec.items()},
        "full_record_keys": detail_structure,
    }


# ── POST /sync ────────────────────────────────────────────────────────────────

@router.post("/sync", summary="從 Ragic 同步 IHG 客房保養資料（背景執行）")
async def sync_records(background_tasks: BackgroundTasks):
    """觸發背景同步：Ragic Sheet 4 → ihg_rm_master + ihg_rm_detail"""
    background_tasks.add_task(sync_from_ragic)
    return {"success": True, "message": "IHG 客房保養同步已在背景啟動"}


# ── GET /stats ────────────────────────────────────────────────────────────────

@router.get("/stats", summary="IHG 客房保養 KPI 統計")
async def get_stats(
    year: Optional[str] = Query(None, description="篩選年度，如 2026；空白=當年"),
    db: Session = Depends(get_db),
):
    """
    回傳統計卡：
      total_scheduled  — 全年應保養數
      completed        — 已完成數
      pending          — 未完成數（不含逾期）
      overdue          — 逾期數
      completion_rate  — 完成率（%）
    """
    if not year:
        year = str(twnow().year)

    q = db.query(IHGRoomMaintenanceMaster).filter(
        IHGRoomMaintenanceMaster.maint_year == year
    )
    all_recs = q.all()

    total = len(all_recs)

    # 以 raw_json check 欄位計算各狀態（與 /matrix 邏輯一致）
    completed_count = 0
    abnormal_count  = 0
    pending_count   = 0

    for r in all_recs:
        normal_c = done_c = maint_c = unchecked_c = 0
        try:
            raw_data = json.loads(r.raw_json or "{}")
            for k, v in raw_data.items():
                if not _is_check_field(k, v):
                    continue
                val = v if isinstance(v, str) else ""
                if val == "正常":
                    normal_c += 1
                elif val == "當時維護完成":
                    done_c += 1
                elif val == "等待維護(待料中)":
                    maint_c += 1
                else:
                    unchecked_c += 1
        except Exception:
            pass

        if maint_c > 0:
            abnormal_count += 1
        elif normal_c + done_c > 0 and unchecked_c == 0:
            completed_count += 1
        else:
            pending_count += 1

    rate = round(completed_count / total * 100, 1) if total else 0.0

    return {
        "year": year,
        "total_scheduled": total,
        "completed": completed_count,
        "abnormal": abnormal_count,
        "pending": pending_count,
        "completion_rate": rate,
        "synced_at": (
            db.query(func.max(IHGRoomMaintenanceMaster.synced_at)).scalar() or ""
        ),
    }


# ── GET /matrix ───────────────────────────────────────────────────────────────

@router.get("/matrix", summary="IHG 客房保養年度矩陣表")
async def get_matrix(
    year:    Optional[str] = Query(None, description="年度，如 2026；空白=當年"),
    room_no: Optional[str] = Query(None, description="房號篩選，支援前綴匹配"),
    floor:   Optional[str] = Query(None, description="樓層篩選，如 5F"),
    cell_status: Optional[str] = Query(None, description="狀態篩選：completed/pending/overdue/scheduled"),
    db: Session = Depends(get_db),
):
    """
    回傳年度矩陣表，格式：
    {
      "year": "2026",
      "months": [1..12],
      "rooms": [
        {
          "room_no": "501",
          "floor": "5F",
          "cells": {
            "1": {"ragic_id": "...", "status": "completed", "date": "...", "assignee": "..."},
            "4": {"ragic_id": "...", "status": "pending", ...},
            ...  (只有有記錄的月份才有 key)
          }
        }
      ]
    }
    """
    if not year:
        year = str(twnow().year)

    q = db.query(IHGRoomMaintenanceMaster).filter(
        IHGRoomMaintenanceMaster.maint_year == year
    )
    if room_no:
        q = q.filter(IHGRoomMaintenanceMaster.room_no.ilike(f"{room_no}%"))
    if floor:
        q = q.filter(IHGRoomMaintenanceMaster.floor == floor)

    all_recs = q.all()

    # 按房號分組，建立矩陣
    room_map: dict[str, dict] = {}           # room_no → {floor, cells}
    month_minutes: dict[str, float] = {}     # month_key → 分鐘加總
    for rec in all_recs:
        rno = rec.room_no or "??"
        if rno not in room_map:
            room_map[rno] = {"room_no": rno, "floor": rec.floor, "cells": {}}
        month_key = str(int(rec.maint_month)) if rec.maint_month else "?"
        cell_stat = _cell_status(rec)

        # ── 解析 raw_json 統計保養項目結果 + 工時計算 ──────────────────────
        normal_count = done_count = maint_count = unchecked_count = 0
        work_minutes: float = 0.0
        try:
            raw_data = json.loads(rec.raw_json or "{}")
            for k, v in raw_data.items():
                # 單筆工時（分鐘）— 先獨立抽取，不受 _is_check_field 影響
                if k == "工時計算" and v not in (None, "", "None"):
                    try:
                        work_minutes = float(v)
                        month_minutes[month_key] = (
                            month_minutes.get(month_key, 0.0) + work_minutes
                        )
                    except (ValueError, TypeError):
                        pass

                # 保養檢查項目計數
                if not _is_check_field(k, v):
                    continue
                val = v if isinstance(v, str) else ""
                if val == "正常":
                    normal_count += 1
                elif val == "當時維護完成":
                    done_count += 1
                elif val == "等待維護(待料中)":
                    maint_count += 1
                else:                    # "" 或 None → 未檢查
                    unchecked_count += 1
        except Exception:
            pass

        # ── 以 check 欄位結果決定狀態（優先於日期邏輯）────────────────────
        if maint_count > 0:
            # 有「等待維護(待料中)」→ 異常
            cell_stat = "abnormal"
        elif normal_count + done_count > 0 and unchecked_count == 0:
            # 有 check 資料且全部正常/完成（無未檢查）→ 已完成
            cell_stat = "completed"
        # 否則（有未檢查 or 無 check 資料）→ 保持日期邏輯（scheduled / pending）

        # 狀態篩選（後端過濾）
        if cell_status and cell_stat != cell_status:
            continue

        room_map[rno]["cells"][month_key] = {
            "ragic_id":     rec.ragic_id,
            "status":       cell_stat,
            "date":         rec.maint_date,
            "assignee":     rec.assignee_name,
            "completion_date": rec.completion_date,
            "maint_type":   rec.maint_type,
            "notes":        rec.notes,
            "normal_count":    normal_count,
            "done_count":      done_count,
            "maint_count":     maint_count,
            "unchecked_count": unchecked_count,
            "work_minutes":    int(work_minutes) if work_minutes else None,
        }

    # 依樓層排序
    sorted_rooms = sorted(room_map.values(), key=lambda r: _room_sort_key(r["room_no"]))

    # 取所有已出現的樓層清單（供前端篩選）
    floors = sorted(
        set(r["floor"] for r in sorted_rooms if r["floor"]),
        key=lambda f: _room_sort_key(f.replace("F", "00"))
    )

    # 分鐘 → 小時（小數點後 2 位），key 轉 int
    month_hours = {
        int(mk): round(mins / 60, 2)
        for mk, mins in month_minutes.items()
        if mk.lstrip("-").isdigit()
    }

    return {
        "year": year,
        "months": list(range(1, 13)),
        "floors": floors,
        "rooms": sorted_rooms,
        "month_hours": month_hours,   # {1: 12.50, 4: 10.33, ...} 只含有資料的月份
    }


# ── GET /records ──────────────────────────────────────────────────────────────

@router.get("/records", summary="IHG 客房保養記錄清單（帶篩選）")
async def list_records(
    year:    Optional[str] = Query(None, description="年度"),
    month:   Optional[str] = Query(None, description="月份（不補零，如 4）"),
    room_no: Optional[str] = Query(None, description="房號（前綴匹配）"),
    floor:   Optional[str] = Query(None, description="樓層，如 5F"),
    rec_status: Optional[str] = Query(None, alias="status", description="狀態"),
    page:    int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """原始清單，支援多維篩選與分頁"""
    q = db.query(IHGRoomMaintenanceMaster)
    if year:
        q = q.filter(IHGRoomMaintenanceMaster.maint_year == year)
    if month:
        q = q.filter(IHGRoomMaintenanceMaster.maint_month == month.zfill(2))
    if room_no:
        q = q.filter(IHGRoomMaintenanceMaster.room_no.ilike(f"{room_no}%"))
    if floor:
        q = q.filter(IHGRoomMaintenanceMaster.floor == floor)
    if rec_status:
        if rec_status == "completed":
            q = q.filter(IHGRoomMaintenanceMaster.is_completed == True)
        else:
            q = q.filter(IHGRoomMaintenanceMaster.status == rec_status)

    total = q.count()
    recs  = (
        q.order_by(IHGRoomMaintenanceMaster.room_no, IHGRoomMaintenanceMaster.maint_month)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "data": [
            {
                "ragic_id":       r.ragic_id,
                "room_no":        r.room_no,
                "floor":          r.floor,
                "maint_year":     r.maint_year,
                "maint_month":    r.maint_month,
                "maint_date":     r.maint_date,
                "status":         _cell_status(r),
                "is_completed":   r.is_completed,
                "assignee_name":  r.assignee_name,
                "checker_name":   r.checker_name,
                "completion_date": r.completion_date,
                "maint_type":     r.maint_type,
                "notes":          r.notes,
                "synced_at":      r.synced_at.isoformat() if r.synced_at else None,
            }
            for r in recs
        ],
    }


# ── GET /{ragic_id} ────────────────────────────────────────────────────────────

@router.get("/{ragic_id}", summary="IHG 客房保養單筆明細（含子表格）")
async def get_record(ragic_id: str, db: Session = Depends(get_db)):
    """回傳主表單筆 + 所有子表格明細"""
    master = db.get(IHGRoomMaintenanceMaster, ragic_id)
    if not master:
        raise HTTPException(status_code=404, detail=f"找不到記錄 ragic_id={ragic_id}")

    details = (
        db.query(IHGRoomMaintenanceDetail)
        .filter(IHGRoomMaintenanceDetail.master_ragic_id == ragic_id)
        .order_by(IHGRoomMaintenanceDetail.seq_no)
        .all()
    )

    # 嘗試解析 raw_json 回傳完整欄位（方便前端 debug 欄位 mapping）
    try:
        raw_fields = json.loads(master.raw_json or "{}")
    except Exception:
        raw_fields = {}

    return {
        "ragic_id":       master.ragic_id,
        "room_no":        master.room_no,
        "floor":          master.floor,
        "maint_year":     master.maint_year,
        "maint_month":    master.maint_month,
        "maint_date":     master.maint_date,
        "status":         _cell_status(master),
        "is_completed":   master.is_completed,
        "assignee_name":  master.assignee_name,
        "checker_name":   master.checker_name,
        "completion_date": master.completion_date,
        "maint_type":     master.maint_type,
        "notes":          master.notes,
        "ragic_created_at": master.ragic_created_at,
        "ragic_updated_at": master.ragic_updated_at,
        "synced_at":      master.synced_at.isoformat() if master.synced_at else None,
        "raw_fields":     raw_fields,
        "details": [
            {
                "ragic_id":  d.ragic_id,
                "seq_no":    d.seq_no,
                "task_name": d.task_name,
                "result":    d.result,
                "is_ok":     d.is_ok,
                "notes":     d.notes,
            }
            for d in details
        ],
    }
