"""
週期採購 — 採購單 Service 層（查詢／編輯／狀態變更）

採購單本身由 cycle_purchase_summary_service.convert_to_po() 建立，這裡只處理
建立之後的查詢、編輯（預計到貨日／備註）、狀態變更（draft -> issued /
draft-or-issued -> cancelled）。

2026-07-11 提醒（尚未跟 Samuel 確認，先照最保守的方式實作，之後如需要再調整）：
取消（cancelled）一張採購單，目前「不會」自動把對應的彙整列狀態從 converted
改回 draft、也不會清空彙整列的 po_id——避免自動改動資料造成誤解。如果之後
需要「取消採購單後彙整列自動解鎖可以重轉」的行為，需要另外實作，目前這是
刻意先不做、之後要 Samuel 確認的地方。

2026-08-09（上面那個「之後要 Samuel 確認的地方」已確認，新增「退回彙整單」）：

**先講清楚「取消」原本是死路一條**（這次才發現，不是新做出來的問題）：
  1. `set_po_status(cancelled)` 完全不碰彙整列 → 彙整列仍是 converted、po_id
     還指著那張已取消的單；
  2. 採購單有 `UniqueConstraint(cycle_id, period_label, company, vendor_id)`，
     而 `convert_to_po()` 檢查「已經有一張採購單」時**沒有排除 cancelled**
     → 取消後**不能重新轉單**；
  3. 彙整列鎖在 converted → **也不能退回請購單**（會被「已轉採購單」擋下）。
  結論：取消一張採購單，那批彙整列就**永久死鎖**，只能改資料庫。

與 Samuel 確認後的處置（**兩個動作並存，語意分開**）：
  - **取消**：這批本期不買了，維持原本行為（彙整列保持鎖定）。
  - **退回彙整單**（本次新增 `revert_po_to_summary()`）：採購單作廢，且把對應的
    彙整列解鎖回 draft、清掉 po_id，讓買家重新調整調整量後再轉一張新的採購單。
  另外把 `convert_to_po()` 的重複檢查改成**排除 cancelled**，否則不管走哪一條
  都還是轉不出新單（死鎖的第 2 點）。

`revert_po_to_summary()` 的幾個決定：
  - **擋下條件只有「已有驗收單」**（與 Samuel 確認）。請款單、partial_received／
    received 不另外檢查，因為兩者都**必然先有驗收單**（`create_payment()` 明確
    要求「請至少選擇一張驗收單」，而 partial_received／received 是驗收單送出後
    系統算出來的），已被同一條擋掉，多寫一次只是重複。
  - **`issued`（已發出）也可以退回**（與 Samuel 確認），因為現實中發出去之後才
    發現要改是常態；退回原因必填，訊息會提醒記得通知廠商。
  - **`cancelled` 也可以退回**：這正是上面那批既有死鎖資料的解套路徑——採購單
    已經是取消狀態，退回只是把彙整列解鎖。
  - ⚠️ **採購明細（po_items）會被刪除**，不是保留。因為 `po_items.summary_id`
    的外鍵是 `ondelete="RESTRICT"` 且本資料庫 `PRAGMA foreign_keys=ON`，明細留著
    的話，之後那些彙整列一旦需要被刪除（例如再往上退回請購單、需求量歸零），
    會被外鍵擋住而拋 IntegrityError——一個很難追的延遲性錯誤。採購單表頭保留為
    cancelled（單號、廠商、金額、時間都在），明細內容則完整寫進稽核紀錄的
    old_value 作為軌跡。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.cycle_purchase_po import CyclePurchasePO, CyclePurchasePOItem
from app.models.cycle_purchase_cycle import CyclePurchaseCycle
from app.models.cycle_purchase_vendor import CyclePurchaseVendor
from app.models.cycle_purchase_summary import CyclePurchaseSummary
from app.models.cycle_purchase_receiving import CyclePurchaseReceiving
from app.services.cycle_purchase_audit_service import record_audit


class POServiceError(Exception):
    """給 router 轉成適當 HTTP 錯誤用的一般性例外。"""
    pass


def _attach_po_display_fields(db: Session, po: CyclePurchasePO) -> CyclePurchasePO:
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == po.cycle_id).first()
    po.cycle_name = cycle.cycle_name if cycle else None
    vendor = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == po.vendor_id).first()
    po.vendor_name = vendor.vendor_name if vendor else None
    return po


def list_pos(
    db: Session,
    cycle_id: Optional[int] = None,
    period_label: Optional[str] = None,
    company: Optional[str] = None,
    vendor_id: Optional[int] = None,
    status: Optional[str] = None,
):
    query = db.query(CyclePurchasePO)
    if cycle_id is not None:
        query = query.filter(CyclePurchasePO.cycle_id == cycle_id)
    if period_label:
        query = query.filter(CyclePurchasePO.period_label == period_label)
    if company:
        query = query.filter(CyclePurchasePO.company == company)
    if vendor_id is not None:
        query = query.filter(CyclePurchasePO.vendor_id == vendor_id)
    if status:
        query = query.filter(CyclePurchasePO.status == status)
    rows = query.order_by(CyclePurchasePO.po_no.desc()).all()
    for r in rows:
        _attach_po_display_fields(db, r)
    return rows


def get_po(db: Session, po_id: int) -> Optional[CyclePurchasePO]:
    po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == po_id).first()
    if po:
        _attach_po_display_fields(db, po)
    return po


def update_po(db: Session, po_id: int, payload) -> Optional[CyclePurchasePO]:
    po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == po_id).first()
    if not po:
        return None
    if po.status != "draft":
        raise POServiceError("只有草稿狀態的採購單可以編輯預計到貨日／備註")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(po, k, v)
    db.flush()
    return _attach_po_display_fields(db, po)


def set_po_status(db: Session, po_id: int, new_status: str) -> Optional[CyclePurchasePO]:
    po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == po_id).first()
    if not po:
        return None
    if new_status not in ("issued", "cancelled"):
        raise POServiceError("狀態只能是 issued 或 cancelled")
    if new_status == "issued":
        if po.status != "draft":
            raise POServiceError("只有草稿狀態的採購單可以發出")
        po.status = "issued"
    else:  # cancelled
        if po.status not in ("draft", "issued"):
            raise POServiceError("只有草稿或已發出狀態的採購單可以取消")
        po.status = "cancelled"
    db.flush()
    return _attach_po_display_fields(db, po)


# ═══════════════════════════════════════════════════════════════════════════
# 退回彙整單（2026-08-09，見本檔開頭說明）
# ═══════════════════════════════════════════════════════════════════════════

def revert_po_to_summary(db: Session, po_id: int, reason: str, user) -> dict:
    """把一張採購單退回彙整單：採購單作廢（cancelled）、明細刪除，對應的彙整列
    解鎖回 draft 並清掉 po_id，讓買家重新調整後再轉一張新的採購單。

    與「取消」的差別：取消只是把這張單標成 cancelled，彙整列**維持鎖定**
    （語意是「這批本期不買了」）；退回則會把彙整列放回可編輯狀態。
    擋下條件與各項決定見本檔開頭說明。"""
    reason = (reason or "").strip()
    if not reason:
        raise POServiceError("請填寫退回原因")

    po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == po_id).first()
    if not po:
        raise POServiceError("採購單不存在")

    # 唯一的擋下條件：已經有驗收單。請款單與 partial_received／received 都
    # 必然先有驗收單，已被這一條涵蓋（見本檔開頭說明）。
    receivings = (
        db.query(CyclePurchaseReceiving)
        .filter(CyclePurchaseReceiving.po_id == po.id)
        .all()
    )
    if receivings:
        nos = "、".join(r.receiving_no for r in receivings)
        raise POServiceError(
            f"採購單 {po.po_no} 已經有驗收單（{nos}），不能退回彙整單。"
            f"請先處理驗收（與後續請款）紀錄。"
        )

    summary_rows = (
        db.query(CyclePurchaseSummary)
        .filter(CyclePurchaseSummary.po_id == po.id)
        .all()
    )
    if not summary_rows and po.status == "cancelled":
        raise POServiceError(
            f"採購單 {po.po_no} 已經是取消狀態，而且沒有任何彙整列還鎖在這張單上，"
            f"沒有需要退回的東西。"
        )

    items = (
        db.query(CyclePurchasePOItem)
        .filter(CyclePurchasePOItem.po_id == po.id)
        .all()
    )
    # 明細內容先做成文字快照寫進稽核，再刪除（刪除原因見本檔開頭說明：
    # po_items.summary_id 是 RESTRICT 外鍵，留著會擋住之後彙整列的刪除）
    items_snapshot = "；".join(
        f"{i.item_code} {i.item_name} × {i.ordered_qty}（小計 {i.subtotal}）" for i in items
    ) or "（無明細）"
    old_status = po.status

    unlocked = []
    for row in summary_rows:
        row.status = "draft"
        row.po_id = None
        unlocked.append(row)

    for i in items:
        db.delete(i)

    po.status = "cancelled"
    po.total_amount = 0
    # 退回原因記在採購單備註上，讓從採購單清單點進來的人直接看得到
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    revert_note = f"[{stamp}] 退回彙整單（{getattr(user, 'full_name', None) or '—'}）：{reason}"
    po.notes = f"{po.notes}\n{revert_note}" if po.notes else revert_note
    db.flush()

    record_audit(
        db,
        document_type="po",
        document_id=po.id,
        document_no=po.po_no,
        event_type="revert_to_summary",
        description=(
            f"採購單退回彙整單（{po.period_label}／{po.company}）：{reason}"
            f"；解鎖彙整列 {len(unlocked)} 筆、刪除採購明細 {len(items)} 筆"
        ),
        operator_user_id=getattr(user, "id", None),
        operator_name=getattr(user, "full_name", None),
        old_value=f"狀態 {old_status}；明細：{items_snapshot}",
        new_value=f"狀態 cancelled；彙整列已解鎖回 draft（{len(unlocked)} 筆）",
    )
    db.flush()

    return {
        "po_id": po.id,
        "po_no": po.po_no,
        "period_label": po.period_label,
        "company": po.company,
        "vendor_id": po.vendor_id,
        "unlocked_summary_count": len(unlocked),
        "deleted_item_count": len(items),
        "message": (
            f"已將採購單 {po.po_no} 退回彙整單"
            f"（解鎖彙整列 {len(unlocked)} 筆、刪除採購明細 {len(items)} 筆）"
        ),
        "next_step": (
            "這批彙整列已回到「草稿」，可以重新調整調整量，再從彙整單頁「轉採購單」"
            "產生一張新的採購單（新單號，舊單保留為已取消供追溯）。"
            + ("\n⚠️ 這張採購單先前已經發出（issued），記得通知供應商作廢。"
               if old_status == "issued" else "")
        ),
    }
