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

2026-08-07（第四次調整，與 Samuel 確認）：
  - **系統自動關閉**：期別已過的請購單由系統自動關閉（`auto_close_expired_requests()`），
    寫入 is_closed=True、close_batch_no 蓋 `CPAUTO-YYYYMM`、closed_by_* 留空。
    與 Samuel 確認要**真的寫進 DB**（不是只做顯示層），因為彙整單只挑
    is_closed=True 的單 —— 若只做顯示層，過月沒人手動關的單會永遠彙整不到。
  - **人工／系統關閉的區分**：靠 close_batch_no 的前綴判斷（_AUTO_CLOSE_PREFIX），
    不新增欄位。close_kind 為衍生欄位（manual / auto / None），由
    _attach_display_fields() 掛上，前端據此顯示不同樣式的標籤。
  - **重新開啟後可編輯**：_check_editable() **拿掉「必須當月」的條件**，只看
    is_closed。原因：過月現在會自動關閉，月份檢查已由 is_closed 涵蓋；而重新
    開啟被視為「有權限的人明確授權補改」，若仍卡當月，重新開啟一張過月的單
    就完全沒有效果。
  - **自動關閉不會覆蓋人工重新開啟**：auto_close_expired_requests() 會跳過
    reopened_at IS NOT NULL 的單。沒有這個防護的話，今天重新開啟、明天排程
    又把它關回去，使用者會覺得系統在跟他作對。
  - **可見性**：沒有 cycle_purchase_close（也沒有 cycle_purchase_view /
    system_admin）的人，清單看不到已關閉的單、詳情直接 403（後端硬過濾，
    不是前端預設篩選）。

2026-08-09（第五次調整，與 Samuel 確認，「部門範圍」+「品類接線」——規格見
docs/SPEC_cycle_purchase_dept_scope.md，設計背景見 models/cycle_purchase_cycle.py）：
  - **`_applicable_departments()` 改寫為 `resolve_applicable_departments()`（B ∩ D）**：
        候選部門 = 啟用中部門
          ∩ company ∈ cycle.applicable_scope            （空／all＝不限）  ← B
          ∩ id ∈ cycle.applicable_department_ids        （空＝不限）       ← B
          ∩ 在 (該公司, 該部門) 有符合 cycle.applicable_categories 的啟用中料號 ← D
    回傳 `(included, excluded)` 兩份清單——**被排除的部門一定要帶原因回去**，
    不可靜默跳過。靜默跳過的話，買家只會看到「怎麼少了一張單」，然後以為系統壞了。
  - **`get_available_items()` 接上品類**：原本只按「公司＋部門」篩，不看週期，
    所以同一部門開幾個週期都拿到同一份料號清單（既有 bug）。改成再串
    `request.cycle_id → cycle.applicable_categories` 篩 `CyclePurchaseItem.category`。
    篩選條件與 D 層的 `_has_available_items()` **刻意保持一致**，否則會出現
    「產生了單、點進去卻沒有料號可選」這種更難解釋的狀況。
  - **`generate_requests_for_period()` 改回傳 `(created, excluded)`**，router 組成
    `{requests, skipped}` 回給前端顯示未產生原因。原本的 `list[Request]` 回傳型別
    改變，呼叫端只有 router 一處（已同步調整）。
  - **孤兒空白單清理**（`find_orphan_blank_requests()` / `delete_orphan_blank_requests()`）：
    週期範圍縮小後，之前已產生給「現在不適用部門」的空白單要清掉。判準是
    **明細 0 筆 + is_closed == False + is_summarized == False** 三者全部成立——
    有人填過一行的、已定案的、已進彙整的一律不動。觸發點在「儲存週期設定」，
    先預覽讓使用者確認再刪（見 routers/cycle_purchase_cycles.py）。
    不限月份：過月的單通常已被 auto_close 關閉，會被 is_closed 條件擋下，
    實務上刪到的多半只有當月。
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, or_ as sa_or

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


# 系統自動關閉專用的批次號前綴。人工關閉是 CPCLOSE-YYYYMM-NNN，兩者前綴不同，
# 靠這個前綴就能分辨一張單是「有人按了關閉」還是「月份過了系統自己關的」，
# 不需要為此在資料表多開一個欄位。
_AUTO_CLOSE_PREFIX = "CPAUTO-"


def _auto_close_batch_no(year_month: str) -> str:
    """系統自動關閉的批次號：同一個月份共用一個，重跑排程也不會產生新批次。"""
    return f"{_AUTO_CLOSE_PREFIX}{year_month.replace('-', '')}"


def close_kind_of(req: CyclePurchaseRequest) -> Optional[str]:
    """這張單是怎麼關的：'manual'（有人按關閉）／'auto'（期別已過，系統關的）／
    None（還開放中）。衍生值，不落地成欄位。"""
    if not req.is_closed:
        return None
    if (req.close_batch_no or "").startswith(_AUTO_CLOSE_PREFIX):
        return "auto"
    return "manual"


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

def _split_csv(raw: Optional[str]) -> set[str]:
    """把逗號分隔的自由文字欄位拆成集合（去空白、去空字串）。"""
    return {part.strip() for part in (raw or "").split(",") if part.strip()}


def _split_csv_ids(raw: Optional[str]) -> set[int]:
    """把逗號分隔的 id 字串拆成整數集合；非數字的碎片直接忽略（不讓髒資料炸掉整頁）。"""
    out: set[int] = set()
    for part in _split_csv(raw):
        try:
            out.add(int(part))
        except ValueError:
            continue
    return out


def cycle_categories(cycle: CyclePurchaseCycle) -> set[str]:
    """這個週期的適用品類集合；空集合代表「不限品類」。"""
    return _split_csv(cycle.applicable_categories)


def _company_in_scope(cycle: CyclePurchaseCycle, company: str) -> bool:
    """applicable_scope 空值或 'all' 代表不限公司。"""
    scope = (cycle.applicable_scope or "").strip()
    if not scope or scope.lower() == "all":
        return True
    companies = _split_csv(scope)
    if not companies:
        return True
    return company in companies


def _has_available_items(
    db: Session, company: str, department_id: int, categories: set[str]
) -> bool:
    """
    D 層判斷：這個「公司＋部門」在指定品類下，有沒有任何啟用中料號可以請購。

    篩選條件必須與 get_available_items() 一致，否則會產生「有單但點進去
    沒有料號可選」的狀況——那比「沒有產生單」更難跟使用者解釋。
    """
    query = (
        db.query(func.count(CyclePurchaseItemMapping.id))
        .join(CyclePurchaseItem, CyclePurchaseItemMapping.item_id == CyclePurchaseItem.id)
        .filter(
            CyclePurchaseItemMapping.company == company,
            CyclePurchaseItemMapping.department_id == department_id,
            CyclePurchaseItem.is_active == True,  # noqa: E712
        )
    )
    if categories:
        query = query.filter(CyclePurchaseItem.category.in_(categories))
    return (query.scalar() or 0) > 0


def resolve_applicable_departments(
    db: Session, cycle: CyclePurchaseCycle
) -> tuple[list[CyclePurchaseDepartment], list[dict]]:
    """
    解析這個週期實際適用哪些部門（2026-08-09 改寫，B ∩ D，見模組開頭說明）。

    回傳 (included, excluded)：
      - included：真正要產生請購單的部門物件清單
      - excluded：被排除的部門與**原因**，格式
        {"department_id": int, "department_name": str, "company": str|None, "reason": str}

    excluded 只收「使用者可能覺得意外」的排除：明確勾選了卻不能用的部門，
    以及品類下沒有料號的部門。單純因為不在適用公司範圍而落選的部門不列入
    （那是設定本來就想要的結果，列出來只會變成雜訊）。
    """
    categories = cycle_categories(cycle)
    selected_ids = _split_csv_ids(cycle.applicable_department_ids)
    excluded: list[dict] = []

    if selected_ids:
        # 明確勾選的情況：停用／不屬於適用公司／主檔已刪的部門也要撈出來講清楚，
        # 否則使用者只會看到「我明明勾了，怎麼沒產生」。
        selected = (
            db.query(CyclePurchaseDepartment)
            .filter(CyclePurchaseDepartment.id.in_(selected_ids))
            .all()
        )
        found_ids = {d.id for d in selected}
        for missing_id in sorted(selected_ids - found_ids):
            excluded.append({
                "department_id": missing_id,
                "department_name": f"部門 #{missing_id}",
                "company": None,
                "reason": "部門主檔已無此部門（請回週期設定重新勾選）",
            })

        candidates: list[CyclePurchaseDepartment] = []
        for dept in selected:
            if not dept.is_active:
                excluded.append({
                    "department_id": dept.id,
                    "department_name": dept.dept_name,
                    "company": dept.company,
                    "reason": "部門已停用",
                })
            elif not _company_in_scope(cycle, dept.company):
                excluded.append({
                    "department_id": dept.id,
                    "department_name": dept.dept_name,
                    "company": dept.company,
                    "reason": "不屬於此週期的適用公司",
                })
            else:
                candidates.append(dept)
    else:
        # 沒勾選 = 適用公司底下的全部啟用中部門（維持改版前的行為，舊資料相容）
        query = db.query(CyclePurchaseDepartment).filter(
            CyclePurchaseDepartment.is_active == True  # noqa: E712
        )
        scope = (cycle.applicable_scope or "").strip()
        companies = _split_csv(scope)
        if scope and scope.lower() != "all" and companies:
            query = query.filter(CyclePurchaseDepartment.company.in_(companies))
        candidates = query.all()

    # ── D 層：該公司＋部門在此品類下有沒有啟用中料號 ──────────────────────
    included: list[CyclePurchaseDepartment] = []
    for dept in candidates:
        if _has_available_items(db, dept.company, dept.id, categories):
            included.append(dept)
        else:
            if categories:
                reason = f"此週期品類「{'、'.join(sorted(categories))}」下沒有啟用中料號"
            else:
                reason = "此部門在這家公司底下沒有啟用中料號（此週期未限定品類）"
            excluded.append({
                "department_id": dept.id,
                "department_name": dept.dept_name,
                "company": dept.company,
                "reason": reason,
            })

    included.sort(key=lambda d: (d.company, d.dept_code))
    return included, excluded


def preview_applicable_departments(db: Session, cycle_id: int) -> dict:
    """給前端「產生本期請購單」Modal 的預覽用：先看會產生哪些部門、哪些不會。"""
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == cycle_id).first()
    if not cycle:
        raise RequestServiceError("週期設定不存在")
    included, excluded = resolve_applicable_departments(db, cycle)
    return {
        "cycle_id": cycle.id,
        "cycle_name": cycle.cycle_name,
        "period_label": _current_period_label(),
        "departments": [
            {
                "department_id": d.id,
                "department_name": d.dept_name,
                "company": d.company,
            }
            for d in included
        ],
        "skipped": excluded,
    }


def generate_requests_for_period(db: Session, cycle_id: int) -> tuple[list[CyclePurchaseRequest], list[dict]]:
    """
    「產生本期請購單」：為每個適用部門建立一張空白請購單。
    隨時可呼叫，沒有時間窗限制；同一 cycle_id+period_label 冪等
    （已經產生過的部門會直接回傳既有那張，不會重複建立）。
    period_label 一律是「現在」的月份，不接受呼叫端指定。

    2026-08-09：適用部門改由 resolve_applicable_departments() 解析（B ∩ D），
    回傳型別改成 (created, excluded)——excluded 是「為什麼某些部門沒產生」的
    說明，router 會一起回給前端顯示，不可丟掉。
    """
    period_label = _current_period_label()

    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == cycle_id).first()
    if not cycle:
        raise RequestServiceError("週期設定不存在")

    departments, excluded = resolve_applicable_departments(db, cycle)
    if not departments:
        if excluded:
            reasons = "；".join(
                f"{e['department_name']}：{e['reason']}" for e in excluded[:5]
            )
            more = f"（另有 {len(excluded) - 5} 個部門）" if len(excluded) > 5 else ""
            raise RequestServiceError(f"這個週期設定目前沒有任何可產生的部門 —— {reasons}{more}")
        raise RequestServiceError(
            "這個週期設定目前沒有任何適用的啟用中部門，請先確認「適用公司」「適用部門」與部門主檔"
        )

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
    return created, excluded


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
    # 2026-08-07：人工關閉 / 系統自動關閉的區分（衍生值，不落地成欄位）
    req.close_kind = close_kind_of(req)
    return req


def _attach_item_account_label(db: Session, item: CyclePurchaseRequestItem) -> CyclePurchaseRequestItem:
    item.account_code_label = None
    if item.account_code_id:
        ac = db.query(CyclePurchaseAccountCode).filter(CyclePurchaseAccountCode.id == item.account_code_id).first()
        if ac:
            item.account_code_label = f"{ac.code} {ac.name}"
    return item


# 「狀態」篩選的合法值。刻意不重用舊的 status 欄位（那是改版前的歷史殘留，
# 新資料一律是 draft，篩了沒有意義），改用實際有意義的三種狀態。
CLOSE_STATES = ("open", "closed_manual", "closed_auto")


def list_requests(
    db: Session,
    cycle_id: Optional[int] = None,
    period_label: Optional[str] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    can_see_closed: bool = True,
    close_state: Optional[str] = None,
):
    """
    can_see_closed=False 時，**完全不回傳已關閉的請購單**（不論人工關閉或系統
    自動關閉）。2026-08-07 與 Samuel 確認採後端硬過濾而非前端預設篩選——前端篩選
    只是畫面乾淨，使用者切個下拉就看得到，不算權限控制。

    close_state（2026-08-07 新增的「狀態」篩選，None＝全部）：
      - "open"          還開放中
      - "closed_manual" 有人按了關閉
      - "closed_auto"   期別已過、系統自動關閉

    ⚠️ 篩選條件必須與 close_kind_of() 的判斷邏輯一致（都看 close_batch_no 的
    CPAUTO- 前綴），否則畫面上的標籤與篩選結果會對不起來。2026-07-17 舊資料一次性
    轉換的 LEGACY-CONVERT-* 前綴不是 CPAUTO-，會被歸到 closed_manual，這是正確的
    ——那批單在改版前確實是有人核准過的。

    ⚠️ 沒有沿用既有的 status 參數：那個欄位是改版前的殘留（新資料一律 draft），
    拿它做「狀態篩選」會篩出使用者無法理解的結果。status 參數保留未動（CLAUDE.md
    §5 不移除既有介面），只是不再是「狀態」的正解。
    """
    if close_state is not None and close_state not in CLOSE_STATES:
        raise RequestServiceError(
            f"不支援的狀態篩選值「{close_state}」，可用值：{'、'.join(CLOSE_STATES)}"
        )

    query = db.query(CyclePurchaseRequest)
    if not can_see_closed:
        # 沒權限的人一律只看得到開放中的單；就算前端硬送 close_state=closed_auto
        # 也一樣（下面的條件會與這一條 AND 起來，結果必然是空集合，不會外洩）
        query = query.filter(CyclePurchaseRequest.is_closed == False)  # noqa: E712

    if close_state == "open":
        query = query.filter(CyclePurchaseRequest.is_closed == False)  # noqa: E712
    elif close_state == "closed_auto":
        query = query.filter(
            CyclePurchaseRequest.is_closed == True,  # noqa: E712
            CyclePurchaseRequest.close_batch_no.like(f"{_AUTO_CLOSE_PREFIX}%"),
        )
    elif close_state == "closed_manual":
        query = query.filter(
            CyclePurchaseRequest.is_closed == True,  # noqa: E712
            # close_batch_no 可能是 NULL（理論上不該發生，但舊資料難保），
            # NULL 在 SQL 的 NOT LIKE 會是 NULL 而不是 TRUE，會被濾掉，
            # 所以要明確把 NULL 也算進「人工關閉」
            sa_or(
                CyclePurchaseRequest.close_batch_no.is_(None),
                ~CyclePurchaseRequest.close_batch_no.like(f"{_AUTO_CLOSE_PREFIX}%"),
            ),
        )
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


class RequestForbiddenError(Exception):
    """看得到 id 但沒有權限看這張單（router 轉成 403）。與 404 分開，
    因為兩者語意不同：404 是不存在，403 是存在但你不能看。"""
    pass


def get_request(
    db: Session, request_id: int, can_see_closed: bool = True
) -> Optional[CyclePurchaseRequest]:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        return None
    if req.is_closed and not can_see_closed:
        # 直接開 URL 也要擋掉，否則清單過濾了但詳情打得開，等於沒過濾
        raise RequestForbiddenError("這張請購單已經關閉，你沒有檢視已關閉請購單的權限")
    _attach_display_fields(db, req)
    for it in req.items:
        _attach_item_account_label(db, it)
    return req


# ═══════════════════════════════════════════════════════════════════════════
# 複製上期請購單（2026-08-13 新增，見 models/cycle_purchase_request.py 開頭說明）
# ═══════════════════════════════════════════════════════════════════════════

def list_copy_source_candidates(
    db: Session, cycle_id: int, department_id: int, limit: int = 12
) -> list[dict]:
    """
    列出同一週期＋同一部門過去有填過品項的請購單，供「複製上期請購單」選擇
    來源。協理要求可以自由選任一過去期別，不只是最近一次，所以這裡回傳一份
    清單（依期別新到舊排序，最多 limit 張），不是只回傳一張。

    只列有明細的單（複製一張空白單沒有意義）；不限是否已關閉——理論上開放中
    的單也可能已經填了想要的品項組合，一併給選。
    """
    rows = (
        db.query(CyclePurchaseRequest)
        .filter(
            CyclePurchaseRequest.cycle_id == cycle_id,
            CyclePurchaseRequest.department_id == department_id,
        )
        .order_by(CyclePurchaseRequest.period_label.desc(), CyclePurchaseRequest.request_no.desc())
        .limit(limit * 3)  # 抓寬一點，篩掉空單之後再截斷到 limit
        .all()
    )
    candidates: list[dict] = []
    for r in rows:
        item_count = (
            db.query(func.count(CyclePurchaseRequestItem.id))
            .filter(CyclePurchaseRequestItem.request_id == r.id)
            .scalar()
            or 0
        )
        if item_count == 0:
            continue
        candidates.append({
            "id": r.id,
            "request_no": r.request_no,
            "period_label": r.period_label,
            "is_closed": r.is_closed,
            "item_count": item_count,
            "total_amount": r.total_amount,
        })
        if len(candidates) >= limit:
            break
    return candidates


def copy_request(db: Session, source_request_id: int, user) -> tuple[CyclePurchaseRequest, list[dict]]:
    """
    複製上期請購單：以某張過去的請購單為範本，建立一張全新的請購單。

    2026-08-13 與協理確認：一律新建，不是加註到現有單；就算本期已經有單
    也要能複製，因此刻意**不**做 create_request() 那種「同週期同期同部門
    已有單」的擋重檢查——這是唯一跳過那個檢查的路徑，其餘手動新增路徑
    （create_request／generate_requests_for_period）不受影響，行為不變。

    每一行明細都重新查「現在」的料號對照（公司＋部門），不是照抄來源單
    當初的快照，理由跟 add_request_item() 一致：單價/品名以下單當下為準。
    來源品項如果現在已經停用或不再屬於這個部門的可選清單，該行會被跳過並
    記進 skipped_items 回傳給呼叫端顯示，不能靜默漏掉（否則使用者會以為
    自己複製全了，實際少了幾行）。
    """
    source = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == source_request_id).first()
    if not source:
        raise RequestServiceError("來源請購單不存在")

    dept = db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.id == source.department_id).first()
    if not dept:
        raise RequestServiceError("來源請購單的部門已不存在，無法複製")

    source_items = (
        db.query(CyclePurchaseRequestItem)
        .filter(CyclePurchaseRequestItem.request_id == source.id)
        .all()
    )
    if not source_items:
        raise RequestServiceError("來源請購單沒有任何明細，無法複製")

    today = date.today()
    new_req = CyclePurchaseRequest(
        request_no=_next_request_no(db, today),
        cycle_id=source.cycle_id,
        period_label=_current_period_label(),
        department_id=source.department_id,
        company=dept.company,
        cost_center_id=source.cost_center_id,
        status="draft",
        total_amount=0,
        notes=f"複製自 {source.request_no}（{source.period_label}）",
    )
    db.add(new_req)
    db.flush()

    skipped: list[dict] = []
    for src_item in source_items:
        item = db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id == src_item.item_id).first()
        if not item or not item.is_active:
            skipped.append({
                "item_code": src_item.item_code, "item_name": src_item.item_name,
                "reason": "料號已停用或不存在",
            })
            continue
        mapping = (
            db.query(CyclePurchaseItemMapping)
            .filter(
                CyclePurchaseItemMapping.item_id == item.id,
                CyclePurchaseItemMapping.company == dept.company,
                CyclePurchaseItemMapping.department_id == dept.id,
            )
            .first()
        )
        if not mapping:
            skipped.append({
                "item_code": src_item.item_code, "item_name": src_item.item_name,
                "reason": f"此料號已不屬於「{dept.dept_name}」的可選清單",
            })
            continue

        row = CyclePurchaseRequestItem(
            request_id=new_req.id,
            item_id=item.id,
            item_mapping_id=mapping.id,
            account_code_id=src_item.account_code_id,
            item_code=item.item_code,
            item_name=item.item_name,
            unit=item.unit,
            unit_price=mapping.original_unit_price,
            request_qty=src_item.request_qty,
            subtotal=(mapping.original_unit_price or Decimal("0")) * src_item.request_qty,
            notes=src_item.notes,
        )
        db.add(row)

    db.flush()
    _recompute_total(db, new_req.id)
    db.flush()
    db.refresh(new_req)
    _attach_display_fields(db, new_req)
    for it in new_req.items:
        _attach_item_account_label(db, it)
    return new_req, skipped


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
    """能不能編輯，2026-08-07 起**只看 is_closed 一個條件**。

    改版前是「沒關閉 AND 還是當月」兩個條件。拿掉月份條件的理由有兩個：
      1. 期別已過的單現在會被 auto_close_expired_requests() 自動關閉，
         「過月」這件事已經由 is_closed 涵蓋，再檢查一次是重複的。
      2. 「重新開啟」的語意是「有 cycle_purchase_close 權限的人明確授權補改
         這張單」。若仍卡當月，重新開啟一張過月的單就完全沒有效果，
         等於這個功能對最需要它的情境（上個月漏填要補）失效。
    """
    if req.is_closed:
        if close_kind_of(req) == "auto":
            raise RequestServiceError(
                f"這張請購單屬於「{req.period_label}」，期別已過、已由系統自動關閉，"
                "不能再編輯（如需補改請找有關閉權限的人重新開啟）"
            )
        raise RequestServiceError("這張請購單已經關閉，不能再編輯（如需修改請先請買家重新開啟）")


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
    """重算請購總金額，並順手蓋上 updated_at。

    2026-08-08：`updated_at` 明確寫進 UPDATE，**不依賴 Column 的 onupdate**。
    原因是這裡用的是 `Query.update()`（bulk update，不經過 ORM instance 的 flush），
    onupdate 會不會被套用在不同 SQLAlchemy 版本間行為不一致。清單頁的「最後更新」
    欄位要能反映「最後一次存檔時間」，欄位不準比沒有這個欄位更糟，所以明確指定。

    所有會動到明細的路徑（新增／更新／刪除明細）最後都會呼叫這支函式，
    所以只要在這裡蓋章，就涵蓋了全部的編輯情境。請購單本身的欄位（成本中心／
    備註）是改 ORM instance，onupdate 正常生效，不需要另外處理。
    """
    total = (
        db.query(func.coalesce(func.sum(CyclePurchaseRequestItem.subtotal), 0))
        .filter(CyclePurchaseRequestItem.request_id == request_id)
        .scalar()
    )
    db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).update(
        {"total_amount": total, "updated_at": datetime.now()}
    )


def get_available_items(db: Session, request_id: int):
    """
    該請購單所屬「公司＋部門＋週期品類」，有對照表資料的啟用中料號清單
    （給選料號畫面用）。

    2026-07-11 新增部門篩選：逐列核對兩家公司的「設料號明細表.xlsx」後確認，
    分頁（工務用／清潔用品／文具&印刷／營業用品）對應真實的功能性部門，
    同一家公司內沒有任何料號橫跨兩個分頁。因此這裡不能只按公司篩，要同時
    按 department_id 篩，否則營業部的請購單會看到工務部的料號可以選。

    2026-08-09 新增品類篩選（**修既有 bug**）：改版前這裡完全不看週期，
    所以同一個部門不管開幾個週期，可選料號清單都一模一樣——週期設定上的
    applicable_categories 從建檔以來沒有任何程式讀過。現在依這張單所屬週期的
    applicable_categories 篩 CyclePurchaseItem.category（空值＝不限品類），
    篩選條件與 _has_available_items() 的 D 層判斷保持一致。
    """
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        raise RequestServiceError("請購單不存在")

    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == req.cycle_id).first()
    categories = cycle_categories(cycle) if cycle else set()

    query = (
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
    )
    if categories:
        query = query.filter(CyclePurchaseItem.category.in_(categories))
    rows = query.order_by(CyclePurchaseItem.item_code).all()
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


def auto_close_expired_requests(db: Session) -> list[CyclePurchaseRequest]:
    """系統自動關閉「期別已過」的請購單（2026-08-07 新增）。

    關閉條件三者皆須成立：
      1. 還沒關閉（is_closed == False）
      2. period_label 小於當月（字串比較即可，YYYY-MM 格式本身就是可排序的）
      3. **沒有被人工重新開啟過**（reopened_at IS NULL）

    第 3 點是關鍵防護：重新開啟的語意是「有權限的人明確授權補改這張單」，
    如果排程隔天又把它關回去，使用者會覺得系統在跟他作對，而且永遠補不了單。
    代價是這張單之後就不會再被自動關閉，需要人工關閉——這是刻意的取捨，
    因為「人明確做過的決定」應該勝過「系統的預設行為」。

    寫入的 closed_* 欄位刻意**不填 closed_by_user_id / closed_by_name**（留 NULL），
    因為關閉這件事沒有經手人；要分辨是不是系統關的請用 close_kind_of()
    （看 close_batch_no 前綴），不要用「closed_by_name 是不是空的」去判斷，
    那是實作細節不是契約。

    這支函式是**冪等**的：同月份共用同一個 CPAUTO 批次號，重跑不會產生新批次，
    也不會動到已經關閉的單。可以安全地在啟動時與每日排程各跑一次。
    """
    current = _current_period_label()
    rows = (
        db.query(CyclePurchaseRequest)
        .filter(
            CyclePurchaseRequest.is_closed == False,          # noqa: E712
            CyclePurchaseRequest.period_label < current,
            CyclePurchaseRequest.reopened_at.is_(None),
        )
        .all()
    )
    if not rows:
        return []

    now = datetime.now()
    for r in rows:
        r.is_closed = True
        r.closed_at = now
        r.close_batch_no = _auto_close_batch_no(r.period_label)
        # closed_by_user_id / closed_by_name 刻意留空：沒有經手人
    db.flush()
    for r in rows:
        _attach_display_fields(db, r)
    return rows


def reopen_requests(db: Session, request_ids: list[int], user) -> list[CyclePurchaseRequest]:
    """重新開啟已關閉的請購單，改回可編輯。closed_* 欄位保留當作歷史紀錄不清掉，
    另外蓋上 reopened_* 欄位記錄「最近一次是誰、什麼時候重新開啟」。

    2026-08-07 起這個動作有兩個副作用，都是刻意的：
      1. 重新開啟後**不再受「必須當月」限制**，過月的單也能實際改（見 _check_editable）
      2. 這張單**之後不會再被系統自動關閉**（auto_close_expired_requests() 會跳過
         reopened_at 有值的單），要再關閉需要人工關。理由是「人明確做過的決定」
         應該勝過「系統的預設行為」，否則排程隔天就把它關回去、永遠補不了單。
    """
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


# ═══════════════════════════════════════════════════════════════════════════
# 孤兒空白請購單清理（2026-08-09 新增）
#
# 週期設定的部門範圍縮小之後，之前已產生給「現在不適用部門」的空白單會留在
# 清單上變成雜訊。與 Samuel 確認：在「儲存週期設定」時彈確認框刪除，
# 先預覽會刪哪幾張、讓使用者確認再執行（因果關係最直接，不會事後莫名少單）。
#
# ⚠️ 判準三個條件**全部成立**才刪，缺一不可：
#     ① 明細 0 筆　② is_closed == False　③ is_summarized == False
#   有人填過一行的、已定案的、已進彙整的一律不動。
#   不限月份——過月的單通常已被 auto_close_expired_requests() 關閉，
#   會被條件 ② 擋下，實務上刪到的多半只有當月。
# ═══════════════════════════════════════════════════════════════════════════

def find_orphan_blank_requests(db: Session, cycle: CyclePurchaseCycle) -> tuple[list[dict], int]:
    """
    找出這個週期底下、部門已不再適用的空白請購單。

    回傳 (orphans, protected_count)：
      - orphans：可以安全刪除的空白單（dict，供預覽顯示）
      - protected_count：部門雖然不再適用，但因為有明細／已關閉／已彙整而
        **保留不刪**的張數。這個數字要讓使用者看到，否則他會以為系統漏刪。
    """
    included, _ = resolve_applicable_departments(db, cycle)
    keep_dept_ids = {d.id for d in included}

    candidates = (
        db.query(CyclePurchaseRequest)
        .filter(CyclePurchaseRequest.cycle_id == cycle.id)
        .all()
    )

    orphans: list[dict] = []
    protected = 0
    for req in candidates:
        if req.department_id in keep_dept_ids:
            continue
        item_count = (
            db.query(func.count(CyclePurchaseRequestItem.id))
            .filter(CyclePurchaseRequestItem.request_id == req.id)
            .scalar()
            or 0
        )
        if item_count > 0 or req.is_closed or req.is_summarized:
            protected += 1
            continue
        dept = (
            db.query(CyclePurchaseDepartment)
            .filter(CyclePurchaseDepartment.id == req.department_id)
            .first()
        )
        orphans.append({
            "id": req.id,
            "request_no": req.request_no,
            "period_label": req.period_label,
            "company": req.company,
            "department_id": req.department_id,
            "department_name": dept.dept_name if dept else None,
        })

    orphans.sort(key=lambda o: (o["period_label"], o["request_no"]))
    return orphans, protected


def delete_orphan_blank_requests(db: Session, cycle: CyclePurchaseCycle) -> int:
    """實際刪除孤兒空白單，回傳刪除筆數。判準與 find_orphan_blank_requests 相同
    ——刻意重算一次而不是吃呼叫端傳來的 id 清單，避免預覽與執行之間資料被別人
    改過（例如剛好有人在那幾秒內填了明細）而誤刪。"""
    orphans, _ = find_orphan_blank_requests(db, cycle)
    if not orphans:
        return 0
    ids = [o["id"] for o in orphans]
    (
        db.query(CyclePurchaseRequest)
        .filter(CyclePurchaseRequest.id.in_(ids))
        .delete(synchronize_session=False)
    )
    db.flush()
    return len(ids)
