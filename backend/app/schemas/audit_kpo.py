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
    """新增部門：一律從 settings/company-departments 選公司別＋部門別，名稱取自部門主檔。"""
    company_id: int
    ref_department_id: int
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


class KpoPeriodSummary(BaseModel):
    id: int
    period: str
    title: str
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    dept_count: int = 0
    total: KpoSubtotal


class KpoPeriodDetail(BaseModel):
    id: int
    period: str
    title: str
    note: Optional[str] = None
    dept_order: List[int] = []     # 本期自訂的部門順序（空＝依主檔）
    departments: List[KpoDeptBlock]
    total: KpoSubtotal


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
