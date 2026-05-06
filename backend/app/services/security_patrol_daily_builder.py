"""
保全巡檢每日巡檢表彙整 Service

build_security_patrol_daily_table(year, month, db, inspection_date=None)
  → 將 SECURITY_PATROL_DAILY_TEMPLATE 標準模板與 DB 實際巡檢資料比對，
    回傳完整每日巡檢表列（含巡檢人員、結果、異常說明等）。

  inspection_date（選填，格式 YYYY/MM/DD）：
    - 不填 → 取整月所有 batch，多筆合併
    - 填入 → 只取該日的 batch；若無資料，各列 matched=False

比對邏輯：
  1. 依 source_tab 取出對應 sheet_key 的 batch（依日期或月份）。
  2. 收集每個 batch 的所有 item（item_name → result_status, result_raw, ...）。
  3. 以 check_content == item_name 精確比對（後備：contains 模糊比對）。
  4. 若同月有多筆，合併顯示（inspector 逗號分隔，異常說明帶日期前綴）。
"""
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.security_patrol import SecurityPatrolBatch, SecurityPatrolItem
from app.services.security_patrol_daily_template import (
    SECURITY_PATROL_DAILY_TEMPLATE,
    SecurityPatrolDailyTemplateRow,
)

logger = logging.getLogger(__name__)


# ── 輔助函式 ──────────────────────────────────────────────────────────────────

def _load_sheet_data(
    sheet_key: str,
    year_month_prefix: str,
    db: Session,
    inspection_date: str | None = None,
) -> list[tuple[SecurityPatrolBatch, list[SecurityPatrolItem]]]:
    """
    回傳 [(batch, [items]), ...] 依日期升序。
    inspection_date 不為 None 時只取該日的 batch。
    """
    q = db.query(SecurityPatrolBatch).filter(SecurityPatrolBatch.sheet_key == sheet_key)
    if inspection_date:
        q = q.filter(SecurityPatrolBatch.inspection_date == inspection_date)
    else:
        q = q.filter(SecurityPatrolBatch.inspection_date.like(f"{year_month_prefix}%"))
    batches = q.order_by(SecurityPatrolBatch.inspection_date.asc()).all()

    result = []
    for b in batches:
        items = (
            db.query(SecurityPatrolItem)
            .filter(SecurityPatrolItem.batch_ragic_id == b.ragic_id)
            .order_by(SecurityPatrolItem.seq_no)
            .all()
        )
        result.append((b, items))
    return result


def _match_item(
    check_content: str,
    items: list[SecurityPatrolItem],
) -> SecurityPatrolItem | None:
    """精確比對 item_name == check_content；失敗則模糊包含比對。"""
    for it in items:
        if it.item_name.strip() == check_content.strip():
            return it
    for it in items:
        n = it.item_name.strip()
        c = check_content.strip()
        if n in c or c in n:
            return it
    return None


def _priority_status(statuses: list[str]) -> str:
    """從多筆狀態取優先值：abnormal > pending > normal > unchecked。"""
    for p in ("abnormal", "pending", "normal", "unchecked"):
        if p in statuses:
            return p
    return "unchecked"


# ── 主函式 ────────────────────────────────────────────────────────────────────

def build_security_patrol_daily_table(
    year: int,
    month: int,
    db: Session,
    inspection_date: str | None = None,
) -> list[dict[str, Any]]:
    """
    回傳保全巡檢每日巡檢表完整列（list of dict），依 SECURITY_PATROL_DAILY_TEMPLATE 順序。

    inspection_date（YYYY/MM/DD）：
      - None  → 整月彙整（多 batch 合併）
      - 有值  → 只取該日結果（無資料時 matched=False）
    """
    year_month_prefix = f"{year}/{month:02d}"

    # 取出所有出現的 source_tab（去重）
    unique_tabs = list(dict.fromkeys(r["source_tab"] for r in SECURITY_PATROL_DAILY_TEMPLATE))

    sheet_data: dict[str, list[tuple[SecurityPatrolBatch, list[SecurityPatrolItem]]]] = {}
    for tab in unique_tabs:
        sheet_data[tab] = _load_sheet_data(
            tab, year_month_prefix, db,
            inspection_date=inspection_date,
        )

    result: list[dict[str, Any]] = []

    for tmpl_row in SECURITY_PATROL_DAILY_TEMPLATE:
        tab          = tmpl_row["source_tab"]
        check_key    = tmpl_row["check_content"]
        batches_data = sheet_data.get(tab, [])

        inspectors:  list[str] = []
        result_raws: list[str] = []
        statuses:    list[str] = []
        abn_notes:   list[str] = []

        for batch, items in batches_data:
            non_note_items = [it for it in items if not it.is_note]
            matched_item = _match_item(check_key, non_note_items)
            if matched_item is None:
                continue

            inspector = (batch.inspector_name or "").strip()
            if inspector and inspector not in inspectors:
                inspectors.append(inspector)

            raw    = (matched_item.result_raw    or "").strip()
            status = (matched_item.result_status or "unchecked").strip()
            result_raws.append(raw)
            statuses.append(status)

            # 異常說明：找 is_note=True 的項目
            note_item = next((it for it in items if it.is_note), None)
            if note_item:
                note_text = (note_item.result_raw or "").strip()
                if note_text:
                    abn_notes.append(f"[{batch.inspection_date}] {note_text}")

        has_match     = len(statuses) > 0
        merged_status = _priority_status(statuses) if statuses else "unchecked"
        merged_raw    = "、".join(dict.fromkeys(r for r in result_raws if r)) if result_raws else ""
        merged_abn    = "\n".join(abn_notes) if abn_notes else ""
        merged_insp   = "、".join(inspectors) if inspectors else ""
        is_abnormal   = merged_status in ("abnormal", "pending")

        result.append({
            **tmpl_row,
            "inspector":     merged_insp,
            "result_text":   merged_raw if has_match else "",
            "result_status": merged_status,
            "abnormal_note": merged_abn,
            "matched":       has_match,
            "abnormal":      is_abnormal,
        })

    return result
