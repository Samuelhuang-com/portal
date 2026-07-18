"""
週期採購 — 請購單 Service 層

2026-07-11（與 Samuel 討論後拿掉「批次」）：
  - 請購單不再掛 batch_id，改掛 cycle_id + period_label（期別標籤，如
    「2026-07」）。「產生本期請購單」（generate_requests_for_period）取代
    原本的 generate_requests_for_batch，隨時可觸發，不需要先手動開批次，
    也沒有固定時間窗限制 —— 這是 Samuel 的核心訴求：週採的範圍界線是
    「料號主檔」，不是時間窗。
  - 同一週期＋同一期別＋同一部門只能有一張請購單（冪等）。

2026-07-11 與 Samuel 確認之設計（第一次，仍然有效）：
  - 請購明細單價＝該公司在 cycle_purchase_item_mappings 的
    original_unit_price（不是 item.unit_price）。
  - 會計科目由填單人在明細逐行手動選（不做自動帶入）。

2026-07-17（第三次調整，與 Samuel 確認，「請購單流程」大改版，詳見
models/cycle_purchase_request.py 開頭說明）：
  - **拿掉送出／核准**：submit_request／approve_request／reject_request 三個
    函式已整個移除，不再保留備用路徑。請購單建立後由填單人自行編輯，不需要
    送出給誰核准。
  - **當期格式**：`_next_request_no()` 改成 `PR-YYYY-MM-NNN`（3 位流水號，
    每月重新起算）；`period_label` 不再是呼叫端傳入的自由文字，改由
    `_current_period_label()` 在建立當下自動算出建立月份的「YYYY-MM」。
    `generate_requests_for_period()`／`create_request()` 都不再接受
    `period_label` 參數。
  - **編輯期限**：新增 `_check_editable(req)`，同時檢查「還沒被關閉」與
    「現在還是這張單建立的那個月份」，取代原本檢查
    `status in ("draft", "rejected")` 的邏輯，套用到 `update_request()`、
    `add_request_item()`、`update_request_item()`、`delete_request_item()`。
  - **關閉／重新開啟**：新增 `list_open_requests_for_close()`（列出某週期＋
    公司＋月份範圍內還開放中的請購單，供勾選）、`close_requests()`（關閉
    勾選的請購單，"全部關閉"是先撈出全部開放中的 id 再呼叫這支函式）、
    `reopen_requests()`（重新開啟，改回可編輯）。
  - **Dashboard 待辦提醒**：原本「待簽核」（依 cycle_purchase_approve 權限）
    已經沒有意義（沒有簽核這個動作了），改成「本月待關閉」（依
    cycle_purchase_close 權限，回傳這個月還開放中、尚未關閉的請購單數量與
    清單），提醒買家記得關閉。
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.cycle_purchase_request import CyclePurchaseRequest, CyclePurchaseRequestItem
from app.models.cycle_purchase_cycle import CyclePurchaseCycle
from app.models.cycle_purchase_reference import (
    CyclePurchaseDepartment, CyclePurchaseCostCenter, CyclePurchaseAccountCode,
)
from app.models.cycle_purchase_item import CyclePurchaseItem, CyclePurchaseItemMapping


class RequestServiceError(Exception):
    """給 router 轉成適當 HTTP 錯誤用的一般性例外。"""
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 請購單號 / 當期
# ═══════════════════════════════════════════════════════════════════════════

def _next_request_no(db: Session, on_date: date) -> str:
    """2026-07-17 起格式為 PR-YYYY-MM-NNN（3 位流水號，每月重新起算）。"""
    prefix = f"PR-{on_date.strftime('%Y-%m')}-"
    count = (
        db.query(func.count(CyclePurchaseRequest.id))
        .filter(CyclePurchaseRequest.request_no.like(f"{prefix}%"))
        .scalar()
        or 0
    )
    return f"{prefix}{count + 1:03d}"


def _current_period_label() -> str:
    """期別標籤一律由系統蓋章為「現在」的 YYYY-MM，使用者不能手動輸入。"""
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


def _next_close_batch_no(db: Session, year_month: str) -> str:
    prefix = f"CPCLOSE-{year_month.replace('-', '')}-"
    count = (
        db.query(func.count(func.distinct(CyclePurchaseRequest.close_batch_no)))
        .filter(CyclePurchaseRequest.close_batch_no.like(f"{prefix}%"))
        .scalar()
        or 0
    )
    return f"{prefix}{count + 1:03d}"


# ═══════════════════════════════════════════════════════════════════════════
# 產生本期請購單（取代原本的批次開放觸發）
# ═══════════════════════════════════════════════════════════════════════════

def _applicable_departments(db: Session, cycle: CyclePurchaseCycle):
    """依 cycle.applicable_scope（逗號分隔的公司名稱，或 'all'）找出適用的啟用中部門。"""
    scope = (cycle.applicable_scope or "").strip()
    query = db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.is_active == True)  # noqa: E712

    if not scope or scope.lower() == "all":
        return query.all()

    companies = {s.strip() for s in scope.split(",") if s.strip()}
    if not companies:
        return query.all()
    return query.filter(CyclePurchaseDepartment.company.in_(companies)).all()


def generate_requests_for_period(db: Session, cycle_id: int) -> list[CyclePurchaseRequest]:
    """
    「產生本期請購單」：為每個適用部門建立一張空白請購單。
    隨時可呼叫，沒有時間窗限制；同一 cycle_id+period_label 冪等
    （已經產生過的部門會直接回傳既有那張，不會重複建立）。
    period_label 一律是「現在」的月份，不接受呼叫端指定。
    """
    period_label = _current_period_label()

    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == cycle_id).first()
    if not cycle:
        raise RequestServiceError("週期設定不存在")

    departments = _applicable_departments(db, cycle)
    if not departments:
        raise RequestServiceError("這個週期設定目前沒有任何適用的啟用中部門，請先確認 applicable_scope 與部門主檔")

    today = date.today()
    created = []
    for dept in departments:
        exists = (
            db.query(CyclePurchaseRequest)
            .filter(
                CyclePurchaseRequest.cycle_id == cycle_id,
                CyclePurchaseRequest.period_label == period_label,
                CyclePurchaseRequest.department_id == dept.id,
            )
            .first()
        )
        if exists:
            created.append(exists)
            continue
        req = CyclePurchaseRequest(
            request_no=_next_request_no(db, today),
            cycle_id=cycle_id,
            period_label=period_label,
            department_id=dept.id,
            company=dept.company,
            status="draft",
            total_amount=0,
        )
        db.add(req)
        db.flush()
        created.append(req)

    for r in created:
        _attach_display_fields(db, r)
    return created


# ═══════════════════════════════════════════════════════════════════════════
# 請購單 CRUD / 查詢
# ═══════════════════════════════════════════════════════════════════════════

def _attach_display_fields(db: Session, req: CyclePurchaseRequest) -> CyclePurchaseRequest:
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == req.cycle_id).first()
    req.cycle_name = cycle.cycle_name if cycle else None
    dept = db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.id == req.department_id).first()
    req.department_name = dept.dept_name if dept else None
    req.cost_center_name = None
    if req.cost_center_id:
        cc = db.query(CyclePurchaseCostCenter).filter(CyclePurchaseCostCenter.id == req.cost_center_id).first()
        req.cost_center_name = cc.cc_name if cc else None
    return req


def _attach_item_account_label(db: Session, item: CyclePurchaseRequestItem) -> CyclePurchaseRequestItem:
    item.account_code_label = None
    if item.account_code_id:
        ac = db.query(CyclePurchaseAccountCode).filter(CyclePurchaseAccountCode.id == item.account_code_id).first()
        if ac:
            item.account_code_label = f"{ac.code} {ac.name}"
    return item


def list_requests(
    db: Session,
    cycle_id: Optional[int] = None,
    period_label: Optional[str] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
):
    query = db.query(CyclePurchaseRequest)
    if cycle_id is not None:
        query = query.filter(CyclePurchaseRequest.cycle_id == cycle_id)
    if period_label:
        query = query.filter(CyclePurchaseRequest.period_label == period_label)
    if department_id is not None:
        query = query.filter(CyclePurchaseRequest.department_id == department_id)
    if status:
        query = query.filter(CyclePurchaseRequest.status == status)
    rows = query.order_by(CyclePurchaseRequest.request_no.desc()).all()
    for r in rows:
        _attach_display_fields(db, r)
    return rows


def get_request(db: Session, request_id: int) -> Optional[CyclePurchaseRequest]:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        return None
    _attach_display_fields(db, req)
    for it in req.items:
        _attach_item_account_label(db, it)
    return req


def create_request(db: Session, payload) -> CyclePurchaseRequest:
    """手動建立單一部門的請購單（備用路徑；一般由 generate_requests_for_period 一次幫全部部門建立）。
    period_label 一律是「現在」的月份，不接受呼叫端指定。"""
    dept = db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.id == payload.department_id).first()
    if not dept:
        raise RequestServiceError("部門不存在")
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == payload.cycle_id).first()
    if not cycle:
        raise RequestServiceError("週期設定不存在")

    period_label = _current_period_label()

    # 防呆：cycle_purchase_requests 有 (cycle_id, period_label, department_id) 唯一鍵限制，
    # 若不先檢查，重複建立會在 flush 時丟出未攔截的 IntegrityError（500），
    # 這裡改成清楚的訊息。
    existing = (
        db.query(CyclePurchaseRequest)
        .filter(
            CyclePurchaseRequest.cycle_id == payload.cycle_id,
            CyclePurchaseRequest.period_label == period_label,
            CyclePurchaseRequest.department_id == payload.department_id,
        )
        .first()
    )
    if existing:
        raise RequestServiceError(
            f"「{cycle.cycle_name}／{period_label}」的「{dept.dept_name}」已經有一張請購單"
            f"（{existing.request_no}），不能重複建立"
        )

    req = CyclePurchaseRequest(
        request_no=_next_request_no(db, date.today()),
        cycle_id=payload.cycle_id,
        period_label=period_label,
        department_id=payload.department_id,
        company=dept.company,
        cost_center_id=payload.cost_center_id,
        status="draft",
        total_amount=0,
    )
    db.add(req)
    db.flush()
    return _attach_display_fields(db, req)


def _check_editable(req: CyclePurchaseRequest) -> None:
    """2026-07-17：編輯權限不再看 status，改看「有沒有被關閉」+「還是不是當月」。
    兩個條件都要成立（沒關閉、還是當月）才能編輯，任一條件不成立就擋掉，
    訊息分開講清楚是哪一種情況，方便使用者理解。"""
    if req.is_closed:
        raise RequestServiceError("這張請購單已經關閉，不能再編輯（如需修改請先請買家重新開啟）")
    if req.period_label != _current_period_label():
        raise RequestServiceError(
            f"這張請購單屬於「{req.period_label}」，已經過了可以編輯的月份，不能再編輯"
        )


def update_request(db: Session, request_id: int, payload) -> Optional[CyclePurchaseRequest]:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        return None
    _check_editable(req)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(req, k, v)
    db.flush()
    return _attach_display_fields(db, req)


# ═══════════════════════════════════════════════════════════════════════════
# 請購明細
# ═══════════════════════════════════════════════════════════════════════════

def _recompute_total(db: Session, request_id: int):
    total = (
        db.query(func.coalesce(func.sum(CyclePurchaseRequestItem.subtotal), 0))
        .filter(CyclePurchaseRequestItem.request_id == request_id)
        .scalar()
    )
    db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).update(
        {"total_amount": total}
    )


def get_available_items(db: Session, request_id: int):
    """
    該請購單所屬「公司＋部門」，有對照表資料的啟用中料號清單（給選料號畫面用）。

    2026-07-11 新增部門篩選：逐列核對兩家公司的「設料號明細表.xlsx」後確認，
    分頁（工務用／清潔用品／文具&印刷／營業用品）對應真實的功能性部門，
    同一家公司內沒有任何料號橫跨兩個分頁。因此這裡不能只按公司篩，要同時
    按 department_id 篩，否則營業部的請購單會看到工務部的料號可以選。
    """
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        raise RequestServiceError("請購單不存在")

    rows = (
        db.query(CyclePurchaseItem, CyclePurchaseItemMapping)
        .join(
            CyclePurchaseItemMapping,
            CyclePurchaseItemMapping.item_id == CyclePurchaseItem.id,
        )
        .filter(
            CyclePurchaseItemMapping.company == req.company,
            CyclePurchaseItemMapping.department_id == req.department_id,
            CyclePurchaseItem.is_active == True,  # noqa: E712
        )
        .order_by(CyclePurchaseItem.item_code)
        .all()
    )
    result = []
    for item, mapping in rows:
        result.append(
            {
                "item_id": item.id,
                "item_mapping_id": mapping.id,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "unit": item.unit,
                "category": item.category,
                "unit_price": mapping.original_unit_price,
                "is_confirmed": mapping.is_confirmed,
            }
        )
    return result


def add_request_item(db: Session, request_id: int, payload) -> CyclePurchaseRequestItem:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        raise RequestServiceError("請購單不存在")
    _check_editable(req)

    item = db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id == payload.item_id).first()
    if not item:
        raise RequestServiceError("料號不存在")

    # 2026-07-11：新增部門篩選，跟 get_available_items() 的可選清單邏輯保持一致。
    # 不能只擋在前端「可選料號」清單上，這裡也要擋，否則直接呼叫 API 可以繞過
    # 部門邊界（例如營業部的請購單加進工務部的料號）。
    mapping = (
        db.query(CyclePurchaseItemMapping)
        .filter(
            CyclePurchaseItemMapping.item_id == payload.item_id,
            CyclePurchaseItemMapping.company == req.company,
            CyclePurchaseItemMapping.department_id == req.department_id,
        )
        .first()
    )
    if not mapping:
        raise RequestServiceError(f"此料號不屬於「{req.company}」這個部門的可選清單，無法加入本請購單")

    existing = (
        db.query(CyclePurchaseRequestItem)
        .filter(
            CyclePurchaseRequestItem.request_id == request_id,
            CyclePurchaseRequestItem.item_id == payload.item_id,
        )
        .first()
    )
    if existing:
        raise RequestServiceError("此料號已經在明細中，請直接修改數量")

    row = CyclePurchaseRequestItem(
        request_id=request_id,
        item_id=item.id,
        item_mapping_id=mapping.id,
        account_code_id=payload.account_code_id,
        item_code=item.item_code,
        item_name=item.item_name,
        unit=item.unit,
        unit_price=mapping.original_unit_price,
        request_qty=payload.request_qty or 0,
        subtotal=(mapping.original_unit_price or Decimal("0")) * (payload.request_qty or 0),
        notes=payload.notes,
    )
    db.add(row)
    db.flush()
    _recompute_total(db, request_id)
    db.flush()
    return _attach_item_account_label(db, row)


def update_request_item(db: Session, request_id: int, item_row_id: int, payload) -> Optional[CyclePurchaseRequestItem]:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        return None
    _check_editable(req)

    row = (
        db.query(CyclePurchaseRequestItem)
        .filter(
            CyclePurchaseRequestItem.id == item_row_id,
            CyclePurchaseRequestItem.request_id == request_id,
        )
        .first()
    )
    if not row:
        return None

    data = payload.model_dump(exclude_unset=True)
    if "request_qty" in data:
        row.request_qty = data["request_qty"] or 0
        row.subtotal = (row.unit_price or Decimal("0")) * row.request_qty
    if "account_code_id" in data:
        row.account_code_id = data["account_code_id"]
    if "notes" in data:
        row.notes = data["notes"]

    db.flush()
    _recompute_total(db, request_id)
    db.flush()
    return _attach_item_account_label(db, row)


def delete_request_item(db: Session, request_id: int, item_row_id: int) -> bool:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        return False
    _check_editable(req)

    row = (
        db.query(CyclePurchaseRequestItem)
        .filter(
            CyclePurchaseRequestItem.id == item_row_id,
            CyclePurchaseRequestItem.request_id == request_id,
        )
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.flush()
    _recompute_total(db, request_id)
    db.flush()
    return True


# ═══════════════════════════════════════════════════════════════════════════
# 關閉 / 重新開啟
# ═══════════════════════════════════════════════════════════════════════════

def list_open_requests_for_close(
    db: Session,
    cycle_id: int,
    company: Optional[str] = None,
    year_month: Optional[str] = None,
) -> list[CyclePurchaseRequest]:
    """列出某週期（可選：某公司、某月份）目前還「開放中」（尚未關閉）的請購單，供勾選關閉用。
    year_month 不給時預設當月（因為「全部關閉」通常就是要關當月）。"""
    query = db.query(CyclePurchaseRequest).filter(
        CyclePurchaseRequest.cycle_id == cycle_id,
        CyclePurchaseRequest.is_closed == False,  # noqa: E712
    )
    if company:
        query = query.filter(CyclePurchaseRequest.company == company)
    query = query.filter(CyclePurchaseRequest.period_label == (year_month or _current_period_label()))
    rows = query.order_by(CyclePurchaseRequest.request_no.asc()).all()
    for r in rows:
        _attach_display_fields(db, r)
    return rows


def close_requests(db: Session, request_ids: list[int], user) -> list[CyclePurchaseRequest]:
    """關閉勾選的請購單。關閉後不能再新增/編輯明細，也不能再修改請購單本身
    （見 _check_editable）。「全部關閉」是先呼叫 list_open_requests_for_close()
    撈出全部開放中的 id，再呼叫這支函式，不是另一支獨立邏輯。"""
    if not request_ids:
        raise RequestServiceError("沒有選擇任何請購單")

    rows = (
        db.query(CyclePurchaseRequest)
        .filter(CyclePurchaseRequest.id.in_(request_ids))
        .all()
    )
    found_ids = {r.id for r in rows}
    missing = set(request_ids) - found_ids
    if missing:
        raise RequestServiceError(f"有請購單不存在：{sorted(missing)}")

    already_closed = [r.request_no for r in rows if r.is_closed]
    if already_closed:
        raise RequestServiceError(f"以下請購單已經是關閉狀態，不能重複關閉：{'、'.join(already_closed)}")

    year_month = rows[0].period_label
    batch_no = _next_close_batch_no(db, year_month)
    now = datetime.now()
    for r in rows:
        r.is_closed = True
        r.closed_by_user_id = user.id
        r.closed_by_name = user.full_name
        r.closed_at = now
        r.close_batch_no = batch_no
    db.flush()
    for r in rows:
        _attach_display_fields(db, r)
    return rows


def close_all_requests(
    db: Session,
    cycle_id: int,
    company: Optional[str],
    year_month: Optional[str],
    user,
) -> list[CyclePurchaseRequest]:
    """「全部關閉」：撈出這個週期＋公司＋月份目前開放中的全部請購單，一次關閉。"""
    open_rows = list_open_requests_for_close(db, cycle_id, company, year_month)
    if not open_rows:
        raise RequestServiceError("目前沒有開放中的請購單可以關閉")
    return close_requests(db, [r.id for r in open_rows], user)


def reopen_requests(db: Session, request_ids: list[int], user) -> list[CyclePurchaseRequest]:
    """重新開啟已關閉的請購單，改回可編輯。closed_* 欄位保留當作歷史紀錄不清掉，
    另外蓋上 reopened_* 欄位記錄「最近一次是誰、什麼時候重新開啟」。"""
    if not request_ids:
        raise RequestServiceError("沒有選擇任何請購單")

    rows = (
        db.query(CyclePurchaseRequest)
        .filter(CyclePurchaseRequest.id.in_(request_ids))
        .all()
    )
    found_ids = {r.id for r in rows}
    missing = set(request_ids) - found_ids
    if missing:
        raise RequestServiceError(f"有請購單不存在：{sorted(missing)}")

    not_closed = [r.request_no for r in rows if not r.is_closed]
    if not_closed:
        raise RequestServiceError(f"以下請購單本來就不是關閉狀態，不能重新開啟：{'、'.join(not_closed)}")

    now = datetime.now()
    for r in rows:
        r.is_closed = False
        r.reopened_by_user_id = user.id
        r.reopened_by_name = user.full_name
        r.reopened_at = now
    db.flush()
    for r in rows:
        _attach_display_fields(db, r)
    return rows


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard 待辦提醒
# ═══════════════════════════════════════════════════════════════════════════

def get_dashboard_todos(db: Session, user, is_closer: bool):
    """
    待辦提醒：
      - my_pending：登入者是 owner_user_id 的部門，當月（period_label 為現在月份）
        且還沒關閉的請購單（這些是「我自己部門這個月還沒關閉、還可以填」的單，
        取代改版前依 status in (draft, rejected) 判斷的邏輯 —— 新流程沒有送出/
        核准狀態機了，「還沒關閉」才是真正代表「還需要我處理」的狀態）。
      - pending_close：若登入者有 cycle_purchase_close 權限，回傳全部「當月且尚未
        關閉」的請購單（關閉目前是全域功能，不分部門，所以不用篩選 owner），
        提醒買家記得在月底前關閉。
    """
    my_dept_ids = [
        d.id
        for d in db.query(CyclePurchaseDepartment.id)
        .filter(CyclePurchaseDepartment.owner_user_id == user.id)
        .all()
    ]

    current_month = _current_period_label()

    my_pending = []
    if my_dept_ids:
        my_pending = (
            db.query(CyclePurchaseRequest)
            .filter(
                CyclePurchaseRequest.department_id.in_(my_dept_ids),
                CyclePurchaseRequest.period_label == current_month,
                CyclePurchaseRequest.is_closed == False,  # noqa: E712
            )
            .order_by(CyclePurchaseRequest.request_no.desc())
            .all()
        )
        for r in my_pending:
            _attach_display_fields(db, r)

    pending_close = []
    if is_closer:
        pending_close = (
            db.query(CyclePurchaseRequest)
            .filter(
                CyclePurchaseRequest.period_label == current_month,
                CyclePurchaseRequest.is_closed == False,  # noqa: E712
            )
            .order_by(CyclePurchaseRequest.request_no.desc())
            .all()
        )
        for r in pending_close:
            _attach_display_fields(db, r)

    return {
        "my_pending": my_pending,
        "pending_close_count": len(pending_close),
        "pending_close": pending_close,
    }
