"""
週期採購 — 彙整單 Service 層（第三期：彙整＋轉採購單）

2026-07-11（與 Samuel 確認之設計，見 models/cycle_purchase_summary.py 開頭說明）：
  - 「產生彙整」只彙總 status == approved 的請購單明細（草稿／已送出／已退回
    一律不算）。同一 cycle_id+period_label+company+item_id 冪等：已經存在的
    彙整列不會被覆寫，只會新增這次才第一次出現的組合。
  - 彙整列的供應商一律來自料號對照表（cycle_purchase_item_mappings）的
    vendor_id，不是料號主檔的 default_vendor_id（見 models/cycle_purchase_item.py
    開頭說明，兩公司合併料號的 default_vendor_id 只會記到單一公司）。
  - 「轉採購單」＝一個公司＋一個供應商（同一週期＋期別內）合成一張採購單。
    只有 status=="draft" 的彙整列才能被轉單；調整量 > 0 的列變成採購明細，
    調整量 == 0 的列（代表「本期決定不訂這個料號」）一併鎖定為 converted、
    回填 po_id，但不會出現在採購明細裡。若這個公司＋供應商在本期完全沒有
    調整量 > 0 的列，不建立採購單（避免產生空的採購單）。
    轉單前會先驗證好所有條件（是否已經轉過、是否有可訂購的列）才動手，
    不會先建立採購單再中途失敗留下半殘資料。

2026-07-16（與 Samuel 確認，「匯總請購單」改版，見 models/cycle_purchase_summary.py
開頭說明）：
  - 彙整粒度從「公司＋料號」改成「公司＋料號＋部門」，group by 的 key 多一個
    department_id（來自請購單本身的 department_id，不是另外讓使用者填）。
  - 新增 list_department_breakdown()：把同一料號底下的多筆部門彙整列，還原成
    「部門別＋部門小計」的畫面（比照 0715 會議「匯總請購單」設計方向）。
  - 新增 push_summary_to_ragic()：把某週期＋期別＋公司範圍內的彙整列，組成一份
    「匯總請購單」文件，呼叫 cycle_purchase_ragic_push（目前是 stub，Ragic 端
    新表單尚未建立）推送出去，成功後在該範圍所有彙整列打上同一個
    ragic_push_batch_no／ragic_pushed／ragic_record_id／ragic_pushed_at。
  - convert_to_po() 本身不需要改動：彙整粒度變細後，同一料號可能對應多筆
    （不同部門）彙整列，會各自變成一筆 PO 明細（不會合併），這是刻意的
    設計——讓部門別的歸屬一路帶到採購單，不需要另外設計「費用分攤」反推。

2026-07-16（第二次調整，與 Samuel 確認，「彙整單產生方式」改版——起因是
「週期＋期別」完全字串比對，期別是自由文字欄位，一旦打字不一致就會查到
0 筆，誤判成「沒有已核准的請購單」）：
  - 拿掉舊版 generate_summary(cycle_id, period_label)：不再靠使用者輸入的
    期別字串去抓已核准請購明細，整條「輸入週期＋期別」的產生路徑已移除，
    不保留備用選項。
  - 新增 list_eligible_requests(cycle_id, company, year_month)：依「週期＋
    公司＋核准月份（approved_at 的年月）」列出所有已核准、尚未被彙整過
    （is_summarized=False）的請購單，供前端畫成勾選清單。
  - 新增 generate_summary_from_requests(request_ids)：只彙總「使用者勾選的
    這些請購單」的明細（不再整批自動撈），period_label 由系統從這些請購單
    本身的 approved_at 推導出「YYYY-MM」（不是「產生當下」的日期，避免
    「7 月的核准單、8 月才有空來彙整」時蓋成 8 月反而失真；使用者不能
    手動輸入）。彙整列若已存在（同一
    cycle_id+period_label+company+item_id+department_id 且狀態仍是
    draft），會把這次的 demand_qty／adjusted_qty 累加上去（支援「這個月
    分好幾批核准、分好幾次彙整」的情境）；若已存在的列狀態不是 draft
    （已經轉單鎖定），則另外新增一筆同 key 的新列承接這次的量，不動
    已鎖定的列（見 models/cycle_purchase_summary.py 關於 UniqueConstraint
    在 SQLite 沒有物理重建、只靠 service 層把關冪等性的說明，這裡是
    刻意利用這個彈性）。
  - 每一張被納入的請購單會標記 is_summarized=True／summary_batch_no／
    summarized_at，之後就不會再出現在可彙整清單裡，避免同一張單被
    重複勾選彙整。

2026-07-17（第三次調整，配合請購單流程大改版——拿掉送出／核准，改成
「關閉」，見 models/cycle_purchase_request.py 與
services/cycle_purchase_request_service.py 開頭說明）：
  - list_eligible_requests()／generate_summary_from_requests() 的判斷條件從
    「status == approved」改成「is_closed == True」：新流程沒有核准這個動作
    了，「關閉」才是「這張單的內容已經定案，可以拿去彙整」的訊號。
  - 月份篩選從「approved_at 的年月」改成直接比對請購單自己的 period_label
    ——因為 period_label 現在是建立當下就系統蓋章的建立月份，不會再有
    「approved_at 落在下個月」這種需要另外用 strftime 換算的情況，直接
    字串相等比對即可，也更貼近使用者「選某個月份」的直覺。
  - period_label 的推導（_period_label_from_requests）也跟著從
    「approved_at.strftime」改成直接讀 requests 自己的 period_label 欄位
    （理論上勾選清單本來就是用同一個 year_month 篩出來的，這裡維持一致性
    檢查是防呆，避免呼叫端繞過清單直接傳入跨月份的 request_ids）。
  - 顯示欄位的 approved_by_name／approved_at 改成 closed_by_name／
    closed_at（沿用 submitted_by_name 顯示原始填單人）。
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.cycle_purchase_summary import CyclePurchaseSummary
from app.models.cycle_purchase_po import CyclePurchasePO, CyclePurchasePOItem
from app.models.cycle_purchase_cycle import CyclePurchaseCycle
from app.models.cycle_purchase_vendor import CyclePurchaseVendor
from app.models.cycle_purchase_item import CyclePurchaseItem, CyclePurchaseItemMapping
from app.models.cycle_purchase_request import CyclePurchaseRequest, CyclePurchaseRequestItem
from app.models.cycle_purchase_reference import CyclePurchaseDepartment
from app.services import cycle_purchase_ragic_push


class SummaryServiceError(Exception):
    """給 router 轉成適當 HTTP 錯誤用的一般性例外。"""
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 顯示欄位
# ═══════════════════════════════════════════════════════════════════════════

def _attach_summary_display_fields(db: Session, row: CyclePurchaseSummary) -> CyclePurchaseSummary:
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == row.cycle_id).first()
    row.cycle_name = cycle.cycle_name if cycle else None

    row.department_name = None
    if row.department_id:
        dept = db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.id == row.department_id).first()
        if dept:
            row.department_name = dept.dept_name

    row.vendor_name = None
    if row.vendor_id:
        vendor = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == row.vendor_id).first()
        if vendor:
            row.vendor_name = vendor.vendor_name

    row.po_no = None
    if row.po_id:
        po = db.query(CyclePurchasePO).filter(CyclePurchasePO.id == row.po_id).first()
        if po:
            row.po_no = po.po_no
    return row


# ═══════════════════════════════════════════════════════════════════════════
# 產生彙整（2026-07-16 第二版：勾選請購單產生，見本檔開頭說明）
# ═══════════════════════════════════════════════════════════════════════════

def _period_label_from_requests(requests: list[CyclePurchaseRequest]) -> str:
    """彙整單的期別一律由系統從勾選的請購單本身的 period_label 讀出來
    （格式 YYYY-MM，該欄位是請購單建立當下就系統蓋章的建立月份），不是自由
    文字、也不需要另外換算。勾選的請購單如果 period_label 不一致（理論上
    不會發生，因為前端的可彙整清單本來就是用同一個 year_month 篩出來的，
    這裡是防呆，避免呼叫端繞過清單直接傳入跨月份的 request_ids），直接擋掉。"""
    labels = {r.period_label for r in requests if r.period_label}
    if not labels:
        raise SummaryServiceError("勾選的請購單缺少期別標籤，無法判斷期別")
    if len(labels) > 1:
        raise SummaryServiceError(f"勾選的請購單期別不一致（{sorted(labels)}），請分開彙整")
    return labels.pop()


def _next_summary_generate_batch_no(db: Session, cycle_id: int, company: str, year_month: str) -> str:
    """產生這次「勾選請購單→產生彙整」動作的批次號，蓋章到被納入的請購單上
    （summary_batch_no），跟彙整列本身的 ragic_push_batch_no 是不同用途的批次號。"""
    prefix = f"CPGEN-{year_month.replace('-', '')}-{company}-"
    count = (
        db.query(func.count(func.distinct(CyclePurchaseRequest.summary_batch_no)))
        .filter(CyclePurchaseRequest.summary_batch_no.like(f"{prefix}%"))
        .scalar()
        or 0
    )
    return f"{prefix}{count + 1:03d}"


def list_eligible_requests(db: Session, cycle_id: int, company: str, year_month: str):
    """「彙整單」畫面用：列出某週期＋公司下，期別（period_label）等於 year_month
    （YYYY-MM）、已經關閉（is_closed=True）、且還沒被彙整過（is_summarized=False）
    的請購單，供使用者勾選要納入這次彙整的範圍。
    2026-07-17：判斷條件從「status == approved」改成「is_closed == True」，
    月份篩選也從「approved_at 換算年月」改成直接比對 period_label（見本檔
    開頭第三次調整說明）。"""
    year_month = (year_month or "").strip()
    if not year_month:
        raise SummaryServiceError("月份不能是空白")

    rows = (
        db.query(CyclePurchaseRequest)
        .filter(
            CyclePurchaseRequest.cycle_id == cycle_id,
            CyclePurchaseRequest.company == company,
            CyclePurchaseRequest.is_closed == True,  # noqa: E712
            CyclePurchaseRequest.is_summarized == False,  # noqa: E712
            CyclePurchaseRequest.period_label == year_month,
        )
        .order_by(CyclePurchaseRequest.closed_at)
        .all()
    )

    result = []
    for r in rows:
        dept = db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.id == r.department_id).first()
        result.append({
            "id": r.id,
            "request_no": r.request_no,
            "department_id": r.department_id,
            "department_name": dept.dept_name if dept else None,
            "submitted_by_name": r.submitted_by_name,
            "closed_by_name": r.closed_by_name,
            "closed_at": r.closed_at,
            "total_amount": r.total_amount,
        })
    return result


def generate_summary_from_requests(db: Session, request_ids: list[int]) -> list[CyclePurchaseSummary]:
    """把使用者勾選的這些請購單（必須都已關閉 is_closed=True 且尚未被彙整過）
    彙整成彙整列。period_label 由系統從這些請購單本身的 period_label 讀出來
    （YYYY-MM），不是「產生當下」的日期。"""
    request_ids = list(dict.fromkeys(request_ids or []))  # 去重，保留順序
    if not request_ids:
        raise SummaryServiceError("請至少勾選一張請購單")

    requests = (
        db.query(CyclePurchaseRequest)
        .filter(CyclePurchaseRequest.id.in_(request_ids))
        .all()
    )
    found_ids = {r.id for r in requests}
    missing = set(request_ids) - found_ids
    if missing:
        raise SummaryServiceError(f"找不到請購單：{sorted(missing)}")

    not_closed = [r.request_no for r in requests if not r.is_closed]
    if not_closed:
        raise SummaryServiceError(f"這些請購單還沒關閉，不能彙整：{', '.join(not_closed)}")

    already_summarized = [r.request_no for r in requests if r.is_summarized]
    if already_summarized:
        raise SummaryServiceError(
            f"這些請購單已經被彙整過，不能重複勾選（避免重複計入數量）：{', '.join(already_summarized)}"
        )

    cycle_ids = {r.cycle_id for r in requests}
    companies = {r.company for r in requests}
    if len(cycle_ids) > 1 or len(companies) > 1:
        raise SummaryServiceError("勾選的請購單必須屬於同一個週期＋同一家公司，不能混選")
    cycle_id = cycle_ids.pop()
    company = companies.pop()

    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == cycle_id).first()
    if not cycle:
        raise SummaryServiceError("週期設定不存在")

    period_label = _period_label_from_requests(requests)

    items = (
        db.query(CyclePurchaseRequestItem)
        .filter(CyclePurchaseRequestItem.request_id.in_(request_ids))
        .all()
    )
    request_by_id = {r.id: r for r in requests}

    # 分組 key：公司＋料號＋部門（部門來自請購單本身）。
    demand_by_key: dict[tuple[str, int, Optional[int]], int] = {}
    for item in items:
        req = request_by_id[item.request_id]
        key = (req.company, item.item_id, req.department_id)
        demand_by_key[key] = demand_by_key.get(key, 0) + (item.request_qty or 0)

    result = []
    for (company_, item_id, department_id), demand_qty in demand_by_key.items():
        if demand_qty <= 0:
            continue

        # 只找狀態還是 draft 的既有列來累加；已經轉單鎖定（converted）的列
        # 不能再動，這種情況另外新增一筆同 key 的新列承接這次新增的量
        # （見本檔開頭 2026-07-16 第二次調整說明）。
        existing = (
            db.query(CyclePurchaseSummary)
            .filter(
                CyclePurchaseSummary.cycle_id == cycle_id,
                CyclePurchaseSummary.period_label == period_label,
                CyclePurchaseSummary.company == company_,
                CyclePurchaseSummary.item_id == item_id,
                CyclePurchaseSummary.department_id == department_id,
                CyclePurchaseSummary.status == "draft",
            )
            .first()
        )
        if existing:
            existing.demand_qty = (existing.demand_qty or 0) + demand_qty
            # 調整量若還沒被人工改過（等於舊的需求量），跟著累加；
            # 若已經被人工調整過（不等於舊需求量），保留人工調整的結果，
            # 不覆蓋掉買家已經做的決定。
            if existing.adjusted_qty == (existing.demand_qty - demand_qty):
                existing.adjusted_qty = existing.demand_qty
            db.flush()
            result.append(existing)
            continue

        item_obj = db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id == item_id).first()
        if not item_obj:
            continue

        mapping = (
            db.query(CyclePurchaseItemMapping)
            .filter(
                CyclePurchaseItemMapping.item_id == item_id,
                CyclePurchaseItemMapping.company == company_,
            )
            .first()
        )

        summary = CyclePurchaseSummary(
            cycle_id=cycle_id,
            period_label=period_label,
            company=company_,
            item_id=item_id,
            department_id=department_id,
            item_mapping_id=mapping.id if mapping else None,
            vendor_id=mapping.vendor_id if mapping else None,
            item_code=item_obj.item_code,
            item_name=item_obj.item_name,
            unit=item_obj.unit,
            unit_price=mapping.original_unit_price if mapping else item_obj.unit_price,
            demand_qty=demand_qty,
            adjusted_qty=demand_qty,
            adjust_reason=None,
            status="draft",
        )
        db.add(summary)
        db.flush()
        result.append(summary)

    batch_no = _next_summary_generate_batch_no(db, cycle_id, company, period_label)
    now = datetime.now()
    for req in requests:
        req.is_summarized = True
        req.summary_batch_no = batch_no
        req.summarized_at = now
    db.flush()

    for r in result:
        _attach_summary_display_fields(db, r)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# 彙整單查詢 / 調整
# ═══════════════════════════════════════════════════════════════════════════

def list_summary(
    db: Session,
    cycle_id: Optional[int] = None,
    period_label: Optional[str] = None,
    company: Optional[str] = None,
    vendor_id: Optional[int] = None,
    status: Optional[str] = None,
    department_id: Optional[int] = None,
):
    query = db.query(CyclePurchaseSummary)
    if cycle_id is not None:
        query = query.filter(CyclePurchaseSummary.cycle_id == cycle_id)
    if period_label:
        query = query.filter(CyclePurchaseSummary.period_label == period_label)
    if company:
        query = query.filter(CyclePurchaseSummary.company == company)
    if vendor_id is not None:
        query = query.filter(CyclePurchaseSummary.vendor_id == vendor_id)
    if status:
        query = query.filter(CyclePurchaseSummary.status == status)
    if department_id is not None:
        query = query.filter(CyclePurchaseSummary.department_id == department_id)
    rows = query.order_by(CyclePurchaseSummary.company, CyclePurchaseSummary.item_code).all()
    for r in rows:
        _attach_summary_display_fields(db, r)
    return rows


def get_summary(db: Session, summary_id: int) -> Optional[CyclePurchaseSummary]:
    row = db.query(CyclePurchaseSummary).filter(CyclePurchaseSummary.id == summary_id).first()
    if row:
        _attach_summary_display_fields(db, row)
    return row


def update_summary_item(db: Session, summary_id: int, payload) -> Optional[CyclePurchaseSummary]:
    row = db.query(CyclePurchaseSummary).filter(CyclePurchaseSummary.id == summary_id).first()
    if not row:
        return None
    if row.status != "draft":
        raise SummaryServiceError("只有草稿狀態的彙整列可以調整（已轉採購單的列不能再改）")

    data = payload.model_dump(exclude_unset=True)
    new_adjusted = data.get("adjusted_qty", row.adjusted_qty)
    new_reason = data.get("adjust_reason", row.adjust_reason)
    if (new_adjusted or 0) != row.demand_qty and not (new_reason and new_reason.strip()):
        raise SummaryServiceError("調整量與需求總量不同時，必須填寫調整原因")

    if "adjusted_qty" in data:
        row.adjusted_qty = data["adjusted_qty"] or 0
    if "adjust_reason" in data:
        row.adjust_reason = data["adjust_reason"]
    db.flush()
    return _attach_summary_display_fields(db, row)


def list_vendor_groups(db: Session, cycle_id: int, period_label: str, company: Optional[str] = None):
    """給「轉採購單」畫面用：某週期＋期別下還沒轉單（draft）的彙整列，依公司＋供應商分組統計。"""
    query = db.query(CyclePurchaseSummary).filter(
        CyclePurchaseSummary.cycle_id == cycle_id,
        CyclePurchaseSummary.period_label == period_label,
        CyclePurchaseSummary.status == "draft",
    )
    if company:
        query = query.filter(CyclePurchaseSummary.company == company)
    rows = query.all()

    groups: dict[tuple[str, Optional[int]], dict] = {}
    for r in rows:
        key = (r.company, r.vendor_id)
        g = groups.setdefault(
            key,
            {
                "company": r.company,
                "vendor_id": r.vendor_id,
                "vendor_name": None,
                "item_count": 0,
                "total_amount": Decimal("0"),
                "has_missing_vendor": r.vendor_id is None,
            },
        )
        g["item_count"] += 1
        g["total_amount"] += (r.unit_price or Decimal("0")) * (r.adjusted_qty or 0)

    result = []
    for (company_, vendor_id_), g in groups.items():
        if vendor_id_:
            vendor = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == vendor_id_).first()
            g["vendor_name"] = vendor.vendor_name if vendor else None
        result.append(g)
    result.sort(key=lambda g: (g["company"], g["vendor_name"] or ""))
    return result


# ═══════════════════════════════════════════════════════════════════════════
# 轉採購單
# ═══════════════════════════════════════════════════════════════════════════

def _next_po_no(db: Session, on_date: date) -> str:
    prefix = f"PO-{on_date.strftime('%Y%m')}-"
    count = (
        db.query(func.count(CyclePurchasePO.id))
        .filter(CyclePurchasePO.po_no.like(f"{prefix}%"))
        .scalar()
        or 0
    )
    return f"{prefix}{count + 1:04d}"


def convert_to_po(
    db: Session, cycle_id: int, period_label: str, company: str, vendor_id: int, user
) -> CyclePurchasePO:
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == cycle_id).first()
    if not cycle:
        raise SummaryServiceError("週期設定不存在")
    vendor = db.query(CyclePurchaseVendor).filter(CyclePurchaseVendor.id == vendor_id).first()
    if not vendor:
        raise SummaryServiceError("供應商不存在")

    existing_po = (
        db.query(CyclePurchasePO)
        .filter(
            CyclePurchasePO.cycle_id == cycle_id,
            CyclePurchasePO.period_label == period_label,
            CyclePurchasePO.company == company,
            CyclePurchasePO.vendor_id == vendor_id,
        )
        .first()
    )
    if existing_po:
        raise SummaryServiceError(
            f"「{cycle.cycle_name}／{period_label}／{company}／{vendor.vendor_name}」"
            f"已經有一張採購單（{existing_po.po_no}），不能重複轉單"
        )

    matched = (
        db.query(CyclePurchaseSummary)
        .filter(
            CyclePurchaseSummary.cycle_id == cycle_id,
            CyclePurchaseSummary.period_label == period_label,
            CyclePurchaseSummary.company == company,
            CyclePurchaseSummary.vendor_id == vendor_id,
            CyclePurchaseSummary.status == "draft",
        )
        .all()
    )
    if not matched:
        raise SummaryServiceError(
            "沒有符合條件、狀態為草稿的彙整列可以轉單，"
            "請確認週期／期別／公司／供應商是否正確，或是否已經轉過單"
        )

    orderable = [r for r in matched if (r.adjusted_qty or 0) > 0]
    zero_rows = [r for r in matched if not (r.adjusted_qty or 0) > 0]
    if not orderable:
        raise SummaryServiceError("此供應商本期沒有調整量大於 0 的彙整列，不需要轉採購單")

    total_amount = sum((r.unit_price or Decimal("0")) * r.adjusted_qty for r in orderable)

    po = CyclePurchasePO(
        po_no=_next_po_no(db, date.today()),
        cycle_id=cycle_id,
        period_label=period_label,
        company=company,
        vendor_id=vendor_id,
        buyer_user_id=user.id,
        buyer_name=user.full_name,
        total_amount=total_amount,
        status="draft",
    )
    db.add(po)
    db.flush()

    for r in orderable:
        po_item = CyclePurchasePOItem(
            po_id=po.id,
            summary_id=r.id,
            item_id=r.item_id,
            item_code=r.item_code,
            item_name=r.item_name,
            unit=r.unit,
            unit_price=r.unit_price,
            ordered_qty=r.adjusted_qty,
            subtotal=(r.unit_price or Decimal("0")) * r.adjusted_qty,
        )
        db.add(po_item)
        r.status = "converted"
        r.po_id = po.id

    for r in zero_rows:
        r.status = "converted"
        r.po_id = po.id

    db.flush()
    return po


# ═══════════════════════════════════════════════════════════════════════════
# 2026-07-16 新增：部門別＋小計 拆解畫面
# ═══════════════════════════════════════════════════════════════════════════

def list_department_breakdown(
    db: Session, cycle_id: int, period_label: str, company: Optional[str] = None,
):
    """匯總請購單畫面用：依「公司＋料號」分組，展開底下各部門別＋小計。
    比照 0715 會議「匯總請購單」設計方向——一張單橫跨多部門，用子表列部門別＋
    部門小計，而不是像舊版一樣把所有部門合併成一行看不出來源。"""
    query = db.query(CyclePurchaseSummary).filter(
        CyclePurchaseSummary.cycle_id == cycle_id,
        CyclePurchaseSummary.period_label == period_label,
    )
    if company:
        query = query.filter(CyclePurchaseSummary.company == company)
    rows = query.order_by(CyclePurchaseSummary.company, CyclePurchaseSummary.item_code).all()
    for r in rows:
        _attach_summary_display_fields(db, r)

    groups: dict[tuple[str, int], dict] = {}
    for r in rows:
        key = (r.company, r.item_id)
        g = groups.setdefault(
            key,
            {
                "company": r.company,
                "item_id": r.item_id,
                "item_code": r.item_code,
                "item_name": r.item_name,
                "unit": r.unit,
                "vendor_id": r.vendor_id,
                "vendor_name": r.vendor_name,
                "unit_price": r.unit_price,
                "departments": [],
                "total_adjusted_qty": 0,
                "total_amount": Decimal("0"),
                "has_missing_vendor": r.vendor_id is None,
            },
        )
        subtotal = (r.unit_price or Decimal("0")) * (r.adjusted_qty or 0)
        g["departments"].append({
            "summary_id": r.id,
            "department_id": r.department_id,
            "department_name": r.department_name or "（歷史資料，未拆分部門）",
            "demand_qty": r.demand_qty,
            "adjusted_qty": r.adjusted_qty,
            "subtotal": subtotal,
            "status": r.status,
        })
        g["total_adjusted_qty"] += (r.adjusted_qty or 0)
        g["total_amount"] += subtotal

    result = list(groups.values())
    result.sort(key=lambda g: (g["company"], g["item_code"]))
    return result


# ═══════════════════════════════════════════════════════════════════════════
# 2026-07-16 新增：拋轉 Ragic「匯總請購單」
# ═══════════════════════════════════════════════════════════════════════════

def _next_ragic_push_batch_no(db: Session, company: str, period_label: str) -> str:
    prefix = f"CPSUM-{period_label.replace('-', '')}-{company}-"
    count = (
        db.query(func.count(func.distinct(CyclePurchaseSummary.ragic_push_batch_no)))
        .filter(CyclePurchaseSummary.ragic_push_batch_no.like(f"{prefix}%"))
        .scalar()
        or 0
    )
    return f"{prefix}{count + 1:04d}"


def push_summary_to_ragic(
    db: Session, cycle_id: int, period_label: str, company: str,
):
    """把某週期＋期別＋公司範圍內的彙整列，組成一份「匯總請購單」文件推送到 Ragic。

    ⚠️ 現況（2026-07-16）：Ragic 端「匯總請購單」表單尚未建立（與 Samuel 確認，
    先做 Portal 端＋預留串接），這裡呼叫的 cycle_purchase_ragic_push.push_summary_document()
    目前是 stub，不會真的打 Ragic API，只會回傳模擬成功結果。等 Ragic 端表單建好、
    拿到真正的 ragic_path 之後，只需要改 cycle_purchase_ragic_push.py 內部實作，
    這裡的呼叫介面不需要變動。
    """
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == cycle_id).first()
    if not cycle:
        raise SummaryServiceError("週期設定不存在")

    rows = (
        db.query(CyclePurchaseSummary)
        .filter(
            CyclePurchaseSummary.cycle_id == cycle_id,
            CyclePurchaseSummary.period_label == period_label,
            CyclePurchaseSummary.company == company,
        )
        .all()
    )
    if not rows:
        raise SummaryServiceError("這個週期＋期別＋公司範圍內沒有彙整列，沒有東西可以拋轉")

    for r in rows:
        _attach_summary_display_fields(db, r)

    breakdown = list_department_breakdown(db, cycle_id, period_label, company)

    batch_no = _next_ragic_push_batch_no(db, company, period_label)
    document = {
        "batch_no": batch_no,
        "cycle_name": cycle.cycle_name,
        "period_label": period_label,
        "company": company,
        "items": breakdown,
        # 週期採購已在料號對照表指定單一廠商，不比價，所以這裡不會有
        # 廠商(一)/(二)/(三) 這種多廠商比價欄位，見 cycle_purchase_ragic_push.py
        # 開頭說明。
    }

    try:
        push_result = cycle_purchase_ragic_push.push_summary_document(document)
    except Exception as e:  # noqa: BLE001 — 對外一律轉成 SummaryServiceError
        for r in rows:
            r.ragic_push_error = str(e)
        db.flush()
        raise SummaryServiceError(f"拋轉 Ragic 失敗：{e}")

    now = datetime.utcnow()
    for r in rows:
        r.ragic_push_batch_no = batch_no
        r.ragic_pushed = True
        r.ragic_record_id = push_result.get("ragic_record_id")
        r.ragic_pushed_at = now
        r.ragic_push_error = None
    db.flush()

    return {
        "batch_no": batch_no,
        "pushed_count": len(rows),
        "ragic_record_id": push_result.get("ragic_record_id"),
        "is_stub": push_result.get("is_stub", True),
        "message": push_result.get("message", "已拋轉"),
    }
