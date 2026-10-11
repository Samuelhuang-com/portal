"""
KPO 稽核 — Pydantic Schemas
對應 app/models/audit_kpo.py、app/routers/audit_kpo.py
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ── 部門 ───────────────────────────────────────────────────────────────────
class KpoDeptCreate(BaseModel):
    """新增部門。2026-10-11 起公司別先隱藏：只填 name 即可（不連結部門主檔）；
    若同時給 company_id＋ref_department_id 則維持舊行為（名稱取自 settings/company-departments）。"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    company_id: Optional[int] = None
    ref_department_id: Optional[int] = None
    source_title: Optional[str] = Field(None, max_length=200)
    sort_order: Optional[int] = None


class KpoDeptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)   # 僅尚未連結部門主檔者可直接改名
    company_id: Optional[int] = None
    ref_department_id: Optional[int] = None
    source_title: Optional[str] = Field(None, max_length=200)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class KpoDeptOut(BaseModel):
    id: int
    name: str
    display_name: str = ""
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    ref_department_id: Optional[int] = None
    source_title: Optional[str] = None
    sort_order: int
    is_active: bool
    item_count: int = 0
    key_count: int = 0
    total_score: int = 0


# ── 主檔項目 ───────────────────────────────────────────────────────────────
class KpoItemCreate(BaseModel):
    department_id: int
    item_no: Optional[int] = Field(None, ge=0, le=999)
    is_key: bool = False
    name: str = Field(..., min_length=1)
    score: Optional[int] = Field(None, ge=0, le=100)   # 未填：★=10、其餘=5
    method: Optional[str] = None


class KpoItemUpdate(BaseModel):
    item_no: Optional[int] = Field(None, ge=0, le=999)
    is_key: Optional[bool] = None
    name: Optional[str] = Field(None, min_length=1)
    score: Optional[int] = Field(None, ge=0, le=100)
    method: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class KpoItemOut(BaseModel):
    id: int
    department_id: int
    item_no: Optional[int] = None
    is_key: bool
    name: str
    score: int
    method: Optional[str] = None
    sort_order: int
    is_active: bool
    in_use: bool = False        # 已被任一期選定（僅提示；刪除不影響歷史期別）


# ── 期別 ───────────────────────────────────────────────────────────────────
class KpoPeriodCreate(BaseModel):
    period: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    title: str = Field("財#1稽核系統建構", max_length=100)
    note: Optional[str] = None


class KpoPeriodUpdate(BaseModel):
    period: Optional[str] = Field(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    title: Optional[str] = Field(None, max_length=100)
    note: Optional[str] = None


class KpoSubtotal(BaseModel):
    """小計（部門或全部）。全部由系統計算，不可手改。"""
    item_count: int = 0       # 選定項數
    key_count: int = 0        # 其中 ★ 重點項數
    full_score: int = 0       # 滿分（選定項目分數合計）
    pass_count: int = 0       # 符合
    fail_count: int = 0       # 不符合
    pending_count: int = 0    # 尚未查核
    earned_score: int = 0     # 得分（符合項目的分數合計）
    rate: Optional[float] = None   # 得分 / 滿分；滿分 0 → None
    score100: Optional[int] = None  # 本期分數＝得分÷滿分×100，四捨五入取整數（不呈現 %）；滿分 0 → None


class KpoLineOut(BaseModel):
    id: int
    department_id: int
    source_item_id: Optional[int] = None
    item_no: Optional[int] = None
    is_key: bool
    name: str
    score: int
    method: Optional[str] = None
    result: Optional[str] = None
    remark: Optional[str] = None
    sort_order: int


class KpoDeptBlock(BaseModel):
    department_id: int
    department_name: str
    lines: List[KpoLineOut]
    subtotal: KpoSubtotal


class KpoSheetBrief(BaseModel):
    id: int
    company_id: int
    company_name: str
    dept_count: int = 0


class KpoSheetBlock(BaseModel):
    """公司別稽核單：公司 → 受稽部門 → 稽核項目。"""
    id: int
    company_id: int
    company_name: str
    departments: List[KpoDeptBlock]
    total: KpoSubtotal


class KpoPeriodSummary(BaseModel):
    id: int
    period: str
    title: str
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    sheets: List[KpoSheetBrief] = []
    dept_count: int = 0
    total: KpoSubtotal


class KpoPeriodDetail(BaseModel):
    id: int
    period: str
    title: str
    note: Optional[str] = None
    sheets: List[KpoSheetBlock]
    total: KpoSubtotal


class KpoHistoryPeriod(BaseModel):
    period_id: int
    period: str                      # YYYY-MM
    score100: Optional[int] = None   # 該期該部門的本期分數


class KpoHistoryMark(BaseModel):
    period_id: int
    period: str
    result: Optional[str] = None     # pass / fail / None＝未查核


class KpoDeptHistory(BaseModel):
    """選擇項目視窗用：同公司、同部門在「其他期別」的歷史（不含本期）。"""
    periods: List[KpoHistoryPeriod] = []
    period_count: int = 0
    score_sum: int = 0               # 各期本期分數加總
    score_avg: Optional[float] = None   # score_sum ÷ period_count，取到小數 1 位
    items: dict[int, List[KpoHistoryMark]] = {}   # 主檔項目 id → 曾被選定的期別與判定


class KpoDashPeriod(BaseModel):
    period_id: int
    period: str
    score100: Optional[int] = None


class KpoDashMonth(BaseModel):
    """某公司某部門某月：該月所有期別本期分數的平均（同月多期取平均）。"""
    avg: Optional[float] = None
    count: int = 0
    periods: List[KpoDashPeriod] = []


class KpoDashRow(BaseModel):
    department_id: int
    department_name: str
    months: dict[int, KpoDashMonth] = {}     # 1~12
    period_count: int = 0                    # 年度內有選定項目的期別數
    score_sum: int = 0
    avg: Optional[float] = None              # 年度平均＝各期本期分數 ÷ 期別數


class KpoDashCompany(BaseModel):
    company_id: int
    company_name: str
    rows: List[KpoDashRow]


class KpoDashboard(BaseModel):
    year: int
    years: List[int]
    companies: List[KpoDashCompany]


class KpoSheetCreate(BaseModel):
    """新增公司別稽核單：公司別＋受稽部門（來源＝現場營運稽核項目的部門，與公司別無連動）。"""
    company_id: int
    department_ids: List[int] = Field(..., min_length=1)


class KpoSheetDeptsUpdate(BaseModel):
    """整組替換稽核單的受稽部門（移除的部門其選定項目與判定一併刪除）。"""
    department_ids: List[int] = Field(..., min_length=1)


class KpoSelectionUpdate(BaseModel):
    """把某部門在本期的選定項目整組替換成 item_ids（新增者由主檔快照、取消者移除）。"""
    department_id: int
    item_ids: List[int]


class KpoDeptOrderUpdate(BaseModel):
    """本期部門顯示順序（由上而下的部門 id）。"""
    department_ids: List[int]


class KpoLineOrderUpdate(BaseModel):
    """某部門在本期的項目順序（由上而下的選定項目 id）。"""
    department_id: int
    line_ids: List[int]


class KpoLineUpdate(BaseModel):
    """本期單獨編輯（不影響主檔與其他期別）。result 傳空字串＝清除判定。"""
    name: Optional[str] = Field(None, min_length=1)
    score: Optional[int] = Field(None, ge=0, le=100)
    is_key: Optional[bool] = None
    method: Optional[str] = None
    result: Optional[str] = Field(None, pattern=r"^(pass|fail|)$")
    remark: Optional[str] = None
