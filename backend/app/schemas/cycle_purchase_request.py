"""週期採購 — 請購單 + 請購明細 Pydantic Schemas"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class RequestItemCreate(BaseModel):
    item_id: int
    request_qty: int = 0
    account_code_id: Optional[int] = None
    notes: Optional[str] = None


class RequestItemUpdate(BaseModel):
    request_qty: Optional[int] = None
    account_code_id: Optional[int] = None
    notes: Optional[str] = None


class RequestItemOut(BaseModel):
    id: int
    request_id: int
    item_id: int
    item_mapping_id: Optional[int] = None
    account_code_id: Optional[int] = None
    account_code_label: Optional[str] = None
    item_code: str
    item_name: str
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    request_qty: int
    subtotal: Decimal
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RequestCreate(BaseModel):
    """
    手動新增單一部門的請購單（備用路徑；一般情況下請購單由「產生本期請購單」
    一次幫所有適用部門建好）。2026-07-11 拿掉批次後，改成掛週期 + 期別。
    2026-07-17 起 period_label 不再由呼叫端指定，一律由後端在建立當下蓋章為
    現在的 YYYY-MM，因此這裡不再收 period_label 欄位。
    """
    cycle_id: int
    department_id: int
    cost_center_id: Optional[int] = None


class RequestUpdate(BaseModel):
    cost_center_id: Optional[int] = None
    notes: Optional[str] = None


class GenerateRequestsPayload(BaseModel):
    """「產生本期請購單」：依週期設定的適用範圍，一次幫所有適用部門建一張空白
    請購單（同 cycle_id+期別重複觸發是冪等的）。2026-07-17 起 period_label 一律是
    「現在」的月份，不再由呼叫端指定。2026-08-09 起適用範圍＝適用公司 ∩ 適用部門
    ∩「該品類下有啟用中料號」（見 models/cycle_purchase_cycle.py 開頭說明）。"""
    cycle_id: int


# ── 2026-08-09：適用部門解析結果（產生預覽 / 產生結果共用）────────────────
# 被排除的部門一定要帶原因回前端顯示，不可靜默跳過——靜默跳過的話買家只會
# 看到「怎麼少了一張單」，然後以為系統壞了。

class SkippedDepartmentOut(BaseModel):
    """某個部門沒有產生請購單的原因。"""
    department_id: int
    department_name: str
    company: Optional[str] = None
    reason: str


class ApplicableDepartmentOut(BaseModel):
    department_id: int
    department_name: str
    company: str


class GeneratePreviewResult(BaseModel):
    """GET /requests/generate-preview：按下「產生」之前先看會產生哪些部門。"""
    cycle_id: int
    cycle_name: str
    period_label: str
    departments: List[ApplicableDepartmentOut] = []
    skipped: List[SkippedDepartmentOut] = []


class GenerateRequestsResult(BaseModel):
    """POST /requests/generate 的回傳。

    2026-08-09 從原本的 `List[RequestOut]` 改成物件，才放得下 skipped。
    這是**回傳型別變更**（不是端點移除），呼叫端只有前端 Requests 頁一處，已同步調整。
    """
    requests: List["RequestOut"] = []
    skipped: List[SkippedDepartmentOut] = []


class CloseRequestsPayload(BaseModel):
    """關閉勾選的請購單。"""
    request_ids: List[int]


class CloseAllRequestsPayload(BaseModel):
    """「全部關閉」：關閉某週期＋公司＋月份目前開放中的全部請購單。
    company／year_month 不給時分別代表「不篩公司」／「當月」。"""
    cycle_id: int
    company: Optional[str] = None
    year_month: Optional[str] = None


class ReopenRequestsPayload(BaseModel):
    """重新開啟已關閉的請購單。"""
    request_ids: List[int]


class RequestOut(BaseModel):
    id: int
    request_no: str
    cycle_id: int
    cycle_name: Optional[str] = None
    period_label: str
    department_id: int
    department_name: Optional[str] = None
    company: str
    cost_center_id: Optional[int] = None
    cost_center_name: Optional[str] = None
    total_amount: Decimal
    status: str
    submitted_by_user_id: Optional[str] = None
    submitted_by_name: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_by_user_id: Optional[str] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    reject_reason: Optional[str] = None
    is_closed: bool = False
    closed_by_user_id: Optional[str] = None
    closed_by_name: Optional[str] = None
    closed_at: Optional[datetime] = None
    close_batch_no: Optional[str] = None
    # 2026-08-07：'manual'（有人按關閉）／'auto'（期別已過，系統自動關閉）／
    # None（還開放中）。衍生欄位，由 service 的 close_kind_of() 依 close_batch_no
    # 前綴推導，不落地成資料表欄位。前端據此顯示不同樣式的標籤。
    close_kind: Optional[str] = None
    reopened_by_user_id: Optional[str] = None
    reopened_by_name: Optional[str] = None
    reopened_at: Optional[datetime] = None
    # 2026-08-09：彙整狀態。改版前這些欄位存在於 model 但**從來沒有回傳給前端**，
    # 導致請購單清單分不出「已關閉且已彙整」「已關閉但還沒彙整」「彙整過又被退回」
    # 三種狀態——三者畫面上一模一樣都只顯示「已關閉」，但處置方式完全不同。
    # unsummarized_* 就算之後又重新彙整也不會清空（是「曾經被退回過」的歷史軌跡，
    # 不是目前狀態；目前狀態看 is_summarized），前端據此顯示永久的「曾退回」小標記。
    is_summarized: bool = False
    summary_batch_no: Optional[str] = None
    summarized_at: Optional[datetime] = None
    unsummarized_by_name: Optional[str] = None
    unsummarized_at: Optional[datetime] = None
    unsummarize_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RequestDetail(RequestOut):
    items: List[RequestItemOut] = []


# ── 2026-08-13：複製上期請購單 ──────────────────────────────────────────
# 協理要求可自由選任一過去期別（不只最近一次），所以是清單而非單一物件；
# 複製一律建立新單，跳過的品項一定要回傳給前端顯示，不能靜默漏掉。

class CopySourceCandidateOut(BaseModel):
    """複製來源清單一列（同一週期＋同一部門過去有填過品項的請購單）。"""
    id: int
    request_no: str
    period_label: str
    is_closed: bool
    item_count: int
    total_amount: Decimal


class CopySkippedItemOut(BaseModel):
    """複製時因為料號現在停用/已不屬於此部門而被跳過的品項。"""
    item_code: str
    item_name: str
    reason: str


class CopyRequestResult(BaseModel):
    request: RequestDetail
    skipped_items: List[CopySkippedItemOut] = []


class AvailableItemOut(BaseModel):
    """給填單頁面「選料號」用：只回傳該請購單所屬公司有對照的料號"""
    item_id: int
    item_mapping_id: int
    item_code: str
    item_name: str
    unit: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[Decimal] = None
    is_confirmed: bool


class TodoSummary(BaseModel):
    """Dashboard 待辦提醒：登入者自己部門這個月還沒關閉的、以及（若有關閉權限）
    全部這個月還沒關閉的請購單。2026-07-17 起拿掉送出/簽核狀態機，
    pending_approval 改名 pending_close。"""
    my_pending: List[RequestOut] = []
    pending_close_count: int = 0
    pending_close: List[RequestOut] = []


# GenerateRequestsResult 引用了後面才定義的 RequestOut，這裡補上前向參考解析。
GenerateRequestsResult.model_rebuild()
