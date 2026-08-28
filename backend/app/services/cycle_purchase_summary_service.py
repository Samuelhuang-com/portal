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

2026-08-09（第四次調整，與 Samuel 確認，「彙整單退回請購單」）：
起因是實務上會發生「已經彙整好了，但這一期要取消／這張單不該納入」，需要
把已彙整的請購單退回到未彙整狀態。新增兩支：

  - list_summarized_requests(cycle_id, company, year_month)：列出某週期＋
    公司＋期別下**已經被彙整過**（is_summarized=True）的請購單，是
    list_eligible_requests() 的鏡像清單，供退回畫面勾選。
  - unsummarize_request(request_id, reason, user)：把單一一張請購單退回。

**為什麼是「重算」不是「反向扣減」**：彙整列沒有記錄「這列的量是哪幾張
請購單貢獻的」（沒有 lineage 表），而且 generate_summary_from_requests()
是用累加的方式寫進去的，所以無法從彙整列反推要扣多少。退回的作法是：
把該請購單 is_summarized 改回 False 之後，用「同一個週期＋期別＋公司＋
部門，且仍為 is_summarized=True 的請購單」重新加總，覆寫受影響的
draft 彙整列 demand_qty。受影響範圍只限這張請購單自己有出現過的料號
（item_ids）＋這張請購單自己的部門，不會動到其他部門或其他料號的列。

**三個擋下條件**（與 Samuel 確認，任一成立就整筆退回動作失敗，不做部分退回）：
  1. 受影響的彙整列裡有 status != "draft" 或已回填 po_id 的 → 已轉採購單，
     退回會讓採購單對不上帳。
  2. 受影響的彙整列裡有 ragic_pushed=True 的 → 已拋轉 Ragic，退回會造成
     Portal 與 Ragic 不一致（Ragic 端目前是 stub，但欄位已在用）。
  3. 該請購單 is_closed=False（已重新開啟）→ 理論上不會發生（要先關閉才能
     彙整），純防呆。

**人工調整量的處理**（與 Samuel 確認）：重算只覆寫 demand_qty。若某列的
adjusted_qty 曾被人工改過（≠ 重算前的 demand_qty），保留該值與 adjust_reason
不動，只在回傳的 warnings 裡提醒買家複查；沒被改過的才跟著新的 demand_qty
一起走。重算後 demand_qty 歸零的列，**沒有人工調整過才刪除**；有人工調整過
的保留（demand_qty=0）並發警告，避免靜默丟掉買家已經做的決定。
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
from app.models.cycle_purchase_audit import CyclePurchaseAuditLog
from app.services.cycle_purchase_audit_service import record_audit


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
    （YYYY-MM）、還沒被彙整過（is_summarized=False）的請購單，供使用者勾選要納入
    這次彙整的範圍。
    2026-07-17：判斷條件從「status == approved」改成「is_closed == True」，
    月份篩選也從「approved_at 換算年月」改成直接比對 period_label（見本檔
    開頭第三次調整說明）。

    2026-08-09（Samuel 回報「退回後重新開啟請購單，產生彙整就看不到那張單了」）：
    **不再直接把未關閉的單濾掉**，改成一併列出並標記 `can_summarize=False` ＋
    `block_reason`。原本的空清單訊息（「這個範圍內沒有已關閉、尚未被彙整過的
    請購單」）完全沒告訴使用者「那張單就在那裡，只差一個關閉動作」，症狀與
    退回清單先前的問題一模一樣——**單子憑空消失，使用者以為系統壞了**。

    ⚠️ 規則本身沒有放寬：`generate_summary_from_requests()` 仍然只接受
    `is_closed=True` 的單。「關閉＝數量定案」是彙整的前提，若允許彙整開放中的
    單，之後有人再去改請購數量，彙整單的數字就默默錯了而且無從察覺。
    這裡改的只是**看不看得見**，不是能不能彙整。
    """
    year_month = (year_month or "").strip()
    if not year_month:
        raise SummaryServiceError("月份不能是空白")

    rows = (
        db.query(CyclePurchaseRequest)
        .filter(
            CyclePurchaseRequest.cycle_id == cycle_id,
            CyclePurchaseRequest.company == company,
            CyclePurchaseRequest.is_summarized == False,  # noqa: E712
            CyclePurchaseRequest.period_label == year_month,
        )
        # 可彙整的（已關閉）排前面，未關閉的排後面；同組內依關閉時間
        .order_by(CyclePurchaseRequest.is_closed.desc(), CyclePurchaseRequest.closed_at.nullslast())
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
            "is_closed": bool(r.is_closed),
            "can_summarize": bool(r.is_closed),
            "block_reason": None if r.is_closed else "尚未關閉（關閉後數量才算定案，才能彙整）",
            # 曾被退回過的軌跡：讓買家知道「這張是退回來的，內容可能被改過」
            "unsummarized_at": r.unsummarized_at,
            "unsummarize_reason": r.unsummarize_reason,
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

        # 2026-08-18：補上 department_id 條件。料號對照表的唯一鍵已放寬成
        # (item_id, company, department_id)（見 models/cycle_purchase_item.py），
        # 同一家公司底下同一個料號可以有多筆 mapping（春大直文具用品各部門
        # 各一筆）。只用 (item_id, company) 取 .first() 會隨機拿到其中一個
        # 部門的單價與供應商，彙整單金額會無聲地錯掉。
        # 這裡的 department_id 就是彙整 key 的第三段，本來就在手上。
        mapping = (
            db.query(CyclePurchaseItemMapping)
            .filter(
                CyclePurchaseItemMapping.item_id == item_id,
                CyclePurchaseItemMapping.company == company_,
                CyclePurchaseItemMapping.department_id == department_id,
            )
            .first()
        )
        if mapping is None:
            # 部門對不到就退回「同公司任一筆」，維持舊行為當保底——彙整單
            # 產不出來比單價抓錯更難處理，但這是次佳解，不是預期路徑。
            # 一定要 order_by：沒有排序時 SQLite 的回傳順序不保證，同一張單
            # 重跑兩次可能拿到不同部門的單價，事後對不出來源。
            mapping = (
                db.query(CyclePurchaseItemMapping)
                .filter(
                    CyclePurchaseItemMapping.item_id == item_id,
                    CyclePurchaseItemMapping.company == company_,
                )
                .order_by(CyclePurchaseItemMapping.id)
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
# 退回請購單（2026-08-09 第四次調整，見本檔開頭說明）
# ═══════════════════════════════════════════════════════════════════════════

def list_summarized_requests(db: Session, cycle_id: int, company: str, year_month: str):
    """「退回請購單」畫面用：列出某週期＋公司下，期別（period_label）等於
    year_month 的**已彙整**（is_summarized=True）請購單。是
    list_eligible_requests() 的鏡像清單（那邊列 is_summarized=False）。

    這裡刻意**不**先幫使用者過濾掉「已轉採購單／已拋轉 Ragic 所以退不了」的
    單，而是每一列都回一個 `can_unsummarize` + `block_reason`，讓使用者在畫面
    上看得到「這張為什麼退不了」，而不是單子憑空消失、以為是系統漏抓。"""
    year_month = (year_month or "").strip()
    if not year_month:
        raise SummaryServiceError("月份不能是空白")

    rows = (
        db.query(CyclePurchaseRequest)
        .filter(
            CyclePurchaseRequest.cycle_id == cycle_id,
            CyclePurchaseRequest.company == company,
            CyclePurchaseRequest.is_summarized == True,  # noqa: E712
            CyclePurchaseRequest.period_label == year_month,
        )
        .order_by(CyclePurchaseRequest.summarized_at.nullslast())
        .all()
    )

    result = []
    for r in rows:
        dept = db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.id == r.department_id).first()
        block_reason = _unsummarize_block_reason(db, r)
        result.append({
            "id": r.id,
            "request_no": r.request_no,
            "department_id": r.department_id,
            "department_name": dept.dept_name if dept else None,
            "submitted_by_name": r.submitted_by_name,
            "closed_by_name": r.closed_by_name,
            "closed_at": r.closed_at,
            "total_amount": r.total_amount,
            "summary_batch_no": r.summary_batch_no,
            "summarized_at": r.summarized_at,
            "can_unsummarize": block_reason is None,
            "block_reason": block_reason,
        })
    return result


def _request_item_ids(db: Session, request_id: int) -> set[int]:
    return {
        i.item_id
        for i in db.query(CyclePurchaseRequestItem)
                   .filter(CyclePurchaseRequestItem.request_id == request_id).all()
        if i.item_id
    }


def _affected_summary_rows(db: Session, req: CyclePurchaseRequest) -> list[CyclePurchaseSummary]:
    """這張請購單的量可能落在哪些彙整列上：同一週期＋期別＋公司＋**這張單的
    部門**，且料號出現在這張單明細裡的所有彙整列（含已鎖定的，擋下條件要看）。"""
    item_ids = _request_item_ids(db, req.id)
    if not item_ids:
        return []
    return (
        db.query(CyclePurchaseSummary)
        .filter(
            CyclePurchaseSummary.cycle_id == req.cycle_id,
            CyclePurchaseSummary.period_label == req.period_label,
            CyclePurchaseSummary.company == req.company,
            CyclePurchaseSummary.department_id == req.department_id,
            CyclePurchaseSummary.item_id.in_(item_ids),
        )
        .all()
    )


def _unsummarize_block_reason(db: Session, req: CyclePurchaseRequest) -> Optional[str]:
    """回傳這張請購單「不能退回」的原因（可以退就回 None）。三個擋下條件見
    本檔開頭第四次調整說明。清單顯示與實際執行共用同一支，避免兩邊判斷不一致。"""
    if not req.is_summarized:
        return "目前不是已彙整狀態"
    if not req.is_closed:
        return "請購單已重新開啟（未關閉），請先重新關閉再退回"

    affected = _affected_summary_rows(db, req)

    locked = [r for r in affected if r.status != "draft" or r.po_id]
    if locked:
        po_ids = {r.po_id for r in locked if r.po_id}
        po_nos = sorted({
            po.po_no
            for po in db.query(CyclePurchasePO).filter(CyclePurchasePO.id.in_(po_ids or [-1])).all()
        })
        codes = sorted({r.item_code for r in locked})
        return (
            f"已轉採購單（{'、'.join(po_nos) if po_nos else '單號未知'}），"
            f"涉及料號：{'、'.join(codes)}"
        )

    pushed = [r for r in affected if r.ragic_pushed]
    if pushed:
        batches = sorted({r.ragic_push_batch_no for r in pushed if r.ragic_push_batch_no})
        return f"彙整列已拋轉 Ragic（批次 {'、'.join(batches) or '—'}）"

    # 同一個 key（料號＋部門）理論上最多只會有一列 draft（見
    # generate_summary_from_requests 的累加邏輯），多於一列代表資料異常，
    # 這時重算會不知道該把量寫到哪一列，直接擋下請人工處理。
    draft_count: dict[int, int] = {}
    for r in affected:
        if r.status == "draft":
            draft_count[r.item_id] = draft_count.get(r.item_id, 0) + 1
    dup = [str(k) for k, v in draft_count.items() if v > 1]
    if dup:
        return f"資料異常：料號 id {'、'.join(dup)} 在本期同一部門有多筆草稿彙整列，請先人工處理"

    return None


def unsummarize_request(db: Session, request_id: int, reason: str, user) -> dict:
    """把單一一張已彙整的請購單退回到未彙整狀態，並重算受影響的 draft 彙整列。
    重算邏輯與擋下條件見本檔開頭第四次調整說明。整筆動作是 all-or-nothing：
    只要有一個擋下條件成立就直接拋錯，不會做「退一半」。"""
    reason = (reason or "").strip()
    if not reason:
        raise SummaryServiceError("請填寫退回原因")

    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        raise SummaryServiceError("請購單不存在")

    block = _unsummarize_block_reason(db, req)
    if block:
        raise SummaryServiceError(f"請購單 {req.request_no} 不能退回：{block}")

    affected = _affected_summary_rows(db, req)
    item_ids = _request_item_ids(db, req.id)
    old_batch_no = req.summary_batch_no

    # 先把這張單標記為未彙整，重算才會自動把它排除在外
    now = datetime.now()
    req.is_summarized = False
    req.summary_batch_no = None
    req.summarized_at = None
    req.unsummarized_by_user_id = getattr(user, "id", None)
    req.unsummarized_by_name = getattr(user, "full_name", None)
    req.unsummarized_at = now
    req.unsummarize_reason = reason
    db.flush()

    # 重算：同一週期＋期別＋公司＋部門，仍為 is_summarized=True 的請購單，
    # 依料號加總（這張單已經被改成 False，所以自然被排除）
    remaining_rows = (
        db.query(CyclePurchaseRequestItem.item_id, func.sum(CyclePurchaseRequestItem.request_qty))
        .join(CyclePurchaseRequest, CyclePurchaseRequest.id == CyclePurchaseRequestItem.request_id)
        .filter(
            CyclePurchaseRequest.cycle_id == req.cycle_id,
            CyclePurchaseRequest.period_label == req.period_label,
            CyclePurchaseRequest.company == req.company,
            CyclePurchaseRequest.department_id == req.department_id,
            CyclePurchaseRequest.is_summarized == True,  # noqa: E712
            CyclePurchaseRequestItem.item_id.in_(item_ids or [-1]),
        )
        .group_by(CyclePurchaseRequestItem.item_id)
        .all()
    )
    remaining_by_item = {item_id: int(qty or 0) for item_id, qty in remaining_rows}

    updated: list[CyclePurchaseSummary] = []
    deleted_ids: list[int] = []
    warnings: list[str] = []
    changes: list[str] = []

    for row in affected:
        if row.status != "draft":   # 已被擋下條件排除，這裡純防禦
            continue
        old_demand = row.demand_qty or 0
        new_demand = remaining_by_item.get(row.item_id, 0)
        if new_demand == old_demand:
            continue

        # 「人工調整過」＝調整量不等於重算前的需求量（與 generate_summary_from_requests
        # 判斷是否要跟著累加用的是同一個定義，兩邊保持一致）
        manually_adjusted = (row.adjusted_qty or 0) != old_demand

        if new_demand <= 0 and not manually_adjusted:
            deleted_ids.append(row.id)
            changes.append(f"{row.item_code} 需求量 {old_demand}→0（刪除彙整列）")
            db.delete(row)
            continue

        row.demand_qty = new_demand
        if manually_adjusted:
            warnings.append(
                f"{row.item_code} {row.item_name}：需求量已由 {old_demand} 重算為 {new_demand}，"
                f"但調整量 {row.adjusted_qty} 是人工設定過的，已保留未變動，請確認是否仍適用"
            )
        else:
            row.adjusted_qty = new_demand
        changes.append(f"{row.item_code} 需求量 {old_demand}→{new_demand}")
        updated.append(row)

    db.flush()

    record_audit(
        db,
        document_type="request",
        document_id=req.id,
        document_no=req.request_no,
        event_type="unsummarize",
        description=(
            f"從彙整單退回請購單（{req.period_label}／{req.company}）：{reason}"
            + (f"；受影響彙整列 {len(updated)} 筆更新、{len(deleted_ids)} 筆刪除" if (updated or deleted_ids)
               else "；沒有彙整列需要調整")
        ),
        operator_user_id=getattr(user, "id", None),
        operator_name=getattr(user, "full_name", None),
        old_value=f"is_summarized=True，彙整批次 {old_batch_no or '—'}",
        new_value="is_summarized=False；" + ("、".join(changes) if changes else "彙整列無異動"),
    )
    db.flush()

    for r in updated:
        _attach_summary_display_fields(db, r)

    return {
        "request_id": req.id,
        "request_no": req.request_no,
        "period_label": req.period_label,
        "company": req.company,
        "previous_summary_batch_no": old_batch_no,
        "updated_summaries": updated,
        "deleted_summary_ids": deleted_ids,
        "warnings": warnings,
        "message": (
            f"已將請購單 {req.request_no} 退回未彙整狀態"
            f"（彙整列更新 {len(updated)} 筆、刪除 {len(deleted_ids)} 筆）"
        ),
        # 2026-08-09：Samuel 退回後把請購單重新開啟去改內容，改完卻發現「產生彙整」
        # 看不到那張單——因為開放中的單不能彙整，要先關閉。流程本身沒錯，但沒有
        # 任何地方講過這件事，所以在退回成功的當下就把下一步講清楚。
        "next_step": (
            "這張單現在是「已關閉、未彙整」，可以直接在「產生彙整」重新勾選。\n"
            "若要先修改內容，請到請購單頁面「重新開啟」——"
            "改完記得再關閉一次，開放中的請購單不能彙整"
            "（未關閉的單仍會出現在「產生彙整」清單裡，可以直接按該列的「關閉並納入」）。"
        ),
    }


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

    # 2026-08-09：重複檢查**排除 cancelled**。搭配「採購單退回彙整單」——退回後
    # 舊採購單保留為 cancelled 當軌跡，同一組要能再轉出一張新單。DB 那層的唯一鍵
    # 也一併改成 partial unique index（`WHERE status != 'cancelled'`），只改這裡是
    # 不夠的（實測會撞 `UNIQUE constraint failed: cycle_purchase_pos.cycle_id,
    # period_label, company, vendor_id`），見 models/cycle_purchase_po.py 開頭說明
    # 與 apply_cycle_purchase_po_unique_migration.py。
    existing_po = (
        db.query(CyclePurchasePO)
        .filter(
            CyclePurchasePO.cycle_id == cycle_id,
            CyclePurchasePO.period_label == period_label,
            CyclePurchasePO.company == company,
            CyclePurchasePO.vendor_id == vendor_id,
            CyclePurchasePO.status != "cancelled",
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

    # 2026-08-18：同料號跨部門的彙整列，轉單時**合併成一行**（與 Samuel 確認）。
    #
    # 背景：彙整列的粒度是 (cycle, period, company, item_id, department_id)，
    # 而 cycle_purchase_po_items 有 UNIQUE(po_id, item_id)。料號對照表唯一鍵在
    # 同日放寬成含 department_id 之後，一支文具可以同時被四個部門請購、產生四列
    # 同料號的彙整列，逐列插入就會撞唯一鍵 → IntegrityError → 500，症狀是
    # 「文具的採購單永遠轉不出來」。在此之前一料號一公司只有一筆對照，
    # 只有一個部門請購得到，所以這個唯一鍵從來沒被觸發過。
    #
    # 選擇合併而非分行的理由：採購單是要給廠商的，同一支文具出現四行一模一樣的
    # 料號沒有意義（po_items 也沒有部門欄位可以區分）。部門別的拆分在彙整單的
    # 「部門別分析」看得到；請款分攤本來就是回頭查請購單算的
    # （見 payment_service._compute_suggested_allocation），不依賴採購明細的部門。
    #
    # 單價不一致時**直接擋下**，不自行挑一個：四筆對照的單價都來自同一列 Excel，
    # 正常情況必然相同；會不同只有人工改過其中一個部門的對照單價，那時候
    # 「系統默默挑一個」會產生一張金額對不起來的採購單，比報錯難處理得多。
    merged: dict[int, list] = {}
    for r in orderable:
        merged.setdefault(r.item_id, []).append(r)
    for item_id_, rows_ in merged.items():
        prices = {r.unit_price for r in rows_}
        if len(prices) > 1:
            raise SummaryServiceError(
                f"料號 {rows_[0].item_code}（{rows_[0].item_name}）有 {len(rows_)} 個部門的"
                f"彙整列要合併成同一行採購明細，但單價不一致（{'、'.join(str(p) for p in prices)}）。"
                f"請先到料號對照表把這幾個部門的單價改成一致，再轉採購單。"
            )

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

    for item_id_, rows_ in merged.items():
        head = rows_[0]
        qty = sum(r.adjusted_qty or 0 for r in rows_)
        po_item = CyclePurchasePOItem(
            po_id=po.id,
            # summary_id 是 NOT NULL 單一外鍵，合併後只能記其中一筆當代表列。
            # 目前所有讀 summary_id 的地方（請款分攤）只拿它回查
            # cycle/period/company/item_id，不看部門，代表列足夠。
            # 反向追溯完整清單靠 summary.po_id（退回採購單就是走這條）。
            summary_id=head.id,
            item_id=item_id_,
            item_code=head.item_code,
            item_name=head.item_name,
            unit=head.unit,
            unit_price=head.unit_price,
            ordered_qty=qty,
            subtotal=(head.unit_price or Decimal("0")) * qty,
        )
        db.add(po_item)
        for r in rows_:
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
    """產生拋轉批次號。

    ⚠️ 流水號**從稽核紀錄取，不是從彙整表取**（2026-08-09 修正）。
    原本是數 `cycle_purchase_summary.ragic_push_batch_no` 的相異值，但新增
    「取消拋轉」之後那個欄位會被清成 NULL，計數就退回 0，重推會拿到**跟上一次
    一模一樣的批次號**——稽核上兩次拋轉的 document_no 相同，完全分不出來
    （實測重現：CPSUM-202608-日曜天地-0001 → 取消 → 重推仍是 0001）。

    稽核紀錄是 append-only、永遠不會被清掉（見 models/cycle_purchase_audit.py），
    所以拿它當號碼來源才不會倒退。
    """
    prefix = f"CPSUM-{period_label.replace('-', '')}-{company}-"
    used = (
        db.query(func.count(func.distinct(CyclePurchaseAuditLog.document_no)))
        .filter(
            CyclePurchaseAuditLog.event_type == "ragic_push",
            CyclePurchaseAuditLog.document_no.like(f"{prefix}%"),
        )
        .scalar()
        or 0
    )
    # 防呆：萬一稽核被清過（理論上不會），仍不可與目前彙整表上還在用的號碼相撞
    in_use = (
        db.query(func.count(func.distinct(CyclePurchaseSummary.ragic_push_batch_no)))
        .filter(CyclePurchaseSummary.ragic_push_batch_no.like(f"{prefix}%"))
        .scalar()
        or 0
    )
    return f"{prefix}{max(used, in_use) + 1:04d}"


def push_summary_to_ragic(
    db: Session, cycle_id: int, period_label: str, company: str, user=None,
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

    # 2026-08-09：擋重複拋轉（與 Samuel 確認）。改版前沒有這個檢查，按兩次會在
    # Ragic 產生兩張內容不同的同期單據，而 Ragic 端無從判斷哪一張才算數。
    # 要重推請先「取消拋轉」（cancel_ragic_push）。
    already = [r for r in rows if r.ragic_pushed]
    if already:
        batches = sorted({r.ragic_push_batch_no for r in already if r.ragic_push_batch_no})
        raise SummaryServiceError(
            f"「{period_label}／{company}」已經拋轉過了"
            f"（批次 {'、'.join(batches) or '—'}，共 {len(already)} 筆彙整列）。"
            f"若要重新拋轉，請先執行「取消拋轉」。"
        )

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

    # ⚠️ 這裡用的是 utcnow()，與本模組其他所有時間欄位（closed_at／summarized_at／
    #    unsummarized_at 都用 datetime.now()）不一致，會差 8 小時。這是既有寫法，
    #    2026-08-09 發現後回報 Samuel，未經同意不自行修改（改動會影響既有資料的
    #    解讀方式）。修的話就是把這一行換成 datetime.now()。
    now = datetime.utcnow()
    for r in rows:
        r.ragic_push_batch_no = batch_no
        r.ragic_pushed = True
        r.ragic_record_id = push_result.get("ragic_record_id")
        r.ragic_pushed_at = now
        r.ragic_push_error = None
    db.flush()

    # 2026-08-09 新增：拋轉也寫稽核。原本只有欄位標記，沒有紀錄——搭配「取消拋轉」
    # 之後會出現 推 → 取消 → 再推 的來回，沒有紀錄就完全看不出經過。
    record_audit(
        db,
        document_type="summary",
        document_id=cycle_id,   # 彙整單沒有單一主鍵，真正的識別是 document_no（批次號）
        document_no=batch_no,
        event_type="ragic_push",
        description=(
            f"拋轉 Ragic 匯總請購單（{cycle.cycle_name}／{period_label}／{company}）："
            f"{len(rows)} 筆彙整列"
            + ("　⚠️ 目前是 stub，未真正寫入 Ragic" if push_result.get("is_stub", True) else "")
        ),
        operator_user_id=getattr(user, "id", None),
        operator_name=getattr(user, "full_name", None),
        old_value="未拋轉",
        new_value=f"已拋轉，Ragic 記錄 ID {push_result.get('ragic_record_id') or '—'}",
    )
    db.flush()

    return {
        "batch_no": batch_no,
        "pushed_count": len(rows),
        "ragic_record_id": push_result.get("ragic_record_id"),
        "is_stub": push_result.get("is_stub", True),
        "message": push_result.get("message", "已拋轉"),
    }


def cancel_ragic_push(
    db: Session, cycle_id: int, period_label: str, company: str, reason: str, user,
):
    """取消某週期＋期別＋公司範圍的 Ragic 拋轉標記，讓它可以重新拋轉。

    2026-08-09 與 Samuel 確認新增。動機有兩個：
      1. 搭配「擋重複拋轉」——擋下之後必須有路可以重來，否則等於一次定生死。
      2. **解掉「已拋轉就永遠退不回請購單」的死結**：`ragic_pushed=True` 是
         `unsummarize_request()` 的擋下條件之一，改版前一旦按了拋轉，那一期的
         請購單就再也退不回去了（而拋轉目前還只是 stub，等於被一個假動作鎖死）。

    做的事：把 5 個 `ragic_*` 欄位清空（`ragic_pushed=False`、批次號／記錄 ID／
    時間／錯誤訊息都清掉），並寫一筆稽核。**不動彙整列本身的 status／po_id**——
    取消的是「拋轉」這個標記，不是彙整結果。

    ⚠️ TODO（等 Ragic 端表單建好、真的會寫入之後必須回來處理）：
       現在是 stub，Ragic 端沒有東西，所以清掉標記就結束。真正串接之後，
       這裡要決定「Ragic 那筆記錄怎麼辦」——刪掉、標記作廢、還是留著讓 Ragic 端
       自己判斷。**在做出決定之前不要上線真實 API**，否則會出現 Portal 說沒拋轉、
       Ragic 卻有一張單的不一致。
    """
    reason = (reason or "").strip()
    if not reason:
        raise SummaryServiceError("請填寫取消拋轉的原因")

    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == cycle_id).first()
    if not cycle:
        raise SummaryServiceError("週期設定不存在")

    rows = (
        db.query(CyclePurchaseSummary)
        .filter(
            CyclePurchaseSummary.cycle_id == cycle_id,
            CyclePurchaseSummary.period_label == period_label,
            CyclePurchaseSummary.company == company,
            CyclePurchaseSummary.ragic_pushed == True,  # noqa: E712
        )
        .all()
    )
    if not rows:
        raise SummaryServiceError(
            f"「{period_label}／{company}」目前沒有已拋轉的彙整列，沒有東西可以取消"
        )

    batches = sorted({r.ragic_push_batch_no for r in rows if r.ragic_push_batch_no})
    record_ids = sorted({r.ragic_record_id for r in rows if r.ragic_record_id})
    was_stub = all((rid or "").startswith("STUB-") for rid in record_ids) if record_ids else True

    for r in rows:
        r.ragic_pushed = False
        r.ragic_push_batch_no = None
        r.ragic_record_id = None
        r.ragic_pushed_at = None
        r.ragic_push_error = None
    db.flush()

    record_audit(
        db,
        document_type="summary",
        document_id=cycle_id,
        document_no=(batches[0] if batches else f"{period_label}/{company}"),
        event_type="ragic_push_cancel",
        description=(
            f"取消 Ragic 拋轉（{cycle.cycle_name}／{period_label}／{company}）：{reason}"
            f"；清除 {len(rows)} 筆彙整列的拋轉標記"
        ),
        operator_user_id=getattr(user, "id", None),
        operator_name=getattr(user, "full_name", None),
        old_value=f"已拋轉，批次 {'、'.join(batches) or '—'}，Ragic 記錄 {'、'.join(record_ids) or '—'}",
        new_value="未拋轉（標記已清除，可重新拋轉，也可以退回請購單）",
    )
    db.flush()

    return {
        "cleared_count": len(rows),
        "previous_batch_no": batches[0] if batches else None,
        "message": (
            f"已取消「{period_label}／{company}」的拋轉標記（{len(rows)} 筆彙整列）"
        ),
        "next_step": (
            "這個範圍現在可以重新拋轉，被擋住的「退回請購單」也解開了。"
            + ("" if was_stub else
               "\n⚠️ 先前那次拋轉已真正寫入 Ragic，Portal 這邊的標記清掉了但 "
               "Ragic 那筆記錄還在，請自行到 Ragic 確認要不要作廢，避免兩邊對不起來。")
        ),
    }
