"""
行事曆 Pydantic Schemas
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# ── 事件類型 / 顏色 / 標籤常數 ────────────────────────────────────────────────
EVENT_TYPE_COLORS: Dict[str, str] = {
    "hotel_pm":   "#1B3A5C",   # 飯店保養 — 品牌主色（深藍）
    "mall_pm":    "#4BA8E8",   # 商場保養 — 品牌輔色（天藍）
    "security":   "#52c41a",   # 保全巡檢 — 綠
    "inspection": "#1677ff",   # 工務巡檢 — Ant Design 藍
    "approval":   "#fa8c16",   # 簽核管理 — 橙
    "memo":       "#722ed1",   # 公告牆   — 紫
    "custom":     "#13c2c2",   # 自訂事件 — 青
}

EVENT_TYPE_LABELS: Dict[str, str] = {
    "hotel_pm":   "飯店保養",
    "mall_pm":    "商場保養",
    "security":   "保全巡檢",
    "inspection": "工務巡檢",
    "approval":   "簽核管理",
    "memo":       "公告牆",
    "custom":     "自訂事件",
}


# ── 輸出：聚合事件 ─────────────────────────────────────────────────────────────
class CalendarEventOut(BaseModel):
    id:           str
    title:        str
    start:        str                       # ISO date "2026-04-15"
    end:          Optional[str] = None
    all_day:      bool = True
    event_type:   str                       # hotel_pm|mall_pm|security|inspection|approval|memo|custom
    module_label: str                       # 飯店保養|商場保養|...
    source_id:    str = ""                  # 原模組記錄 ID
    status:       str = ""                  # pending|completed|abnormal|overdue
    status_label: str = ""
    responsible:  str = ""                  # 負責人
    description:  str = ""                  # 補充說明
    deep_link:    str = ""                  # 跳轉路徑（前端 React Router 路徑）
    color:        str = ""                  # 顏色 hex

    class Config:
        from_attributes = True


class CalendarEventsResponse(BaseModel):
    events: List[CalendarEventOut]
    total:  int


# ── 輸出：今日摘要 KPI ─────────────────────────────────────────────────────────
class TodaySummary(BaseModel):
    today:            str
    total_events:     int
    pending_count:    int         # 待執行 / 未完成
    abnormal_count:   int         # 異常
    overdue_count:    int         # 逾期
    approval_pending: int         # 待簽核件數（全系統）
    high_risk_count:  int         # 高風險（異常 + 逾期）
    event_by_type:    Dict[str, int]


# ── 輸入：自訂事件新增 / 更新 ─────────────────────────────────────────────────
class CustomEventCreate(BaseModel):
    title:       str
    description: str = ""
    start_date:  str              # YYYY-MM-DD
    end_date:    str = ""         # YYYY-MM-DD（選填，空=同 start_date）
    all_day:     bool = True
    start_time:  str = ""         # HH:MM（all_day=False 時有效）
    end_time:    str = ""         # HH:MM
    color:       str = "#13c2c2"
    responsible: str = ""


class CustomEventUpdate(CustomEventCreate):
    pass


# ── 輸出：自訂事件 ─────────────────────────────────────────────────────────────
class CustomEventOut(BaseModel):
    id:           str
    title:        str
    description:  str
    start_date:   str
    end_date:     str
    all_day:      bool
    start_time:   str
    end_time:     str
    color:        str
    responsible:  str
    created_by:   str
    created_at:   Optional[Any] = None

    class Config:
        from_attributes = True
