"""
行事曆 Pydantic Schemas
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# ── 區域別常數 ────────────────────────────────────────────────────────────────
ZONE_VALUES  = ["飯店", "商場", "公區", "其它"]

ZONE_COLORS: Dict[str, str] = {
    "飯店": "#1B3A5C",   # 品牌主色（深藍）
    "商場": "#4BA8E8",   # 品牌輔色（天藍）
    "公區": "#389e0d",   # 公共區域（深綠）
    "其它": "#8c8c8c",   # 其他（灰）
}

ZONE_LABELS: Dict[str, str] = {
    "飯店": "飯店",
    "商場": "商場",
    "公區": "公區",
    "其它": "其它",
}

# ── 事件類型 / 顏色 / 標籤常數 ────────────────────────────────────────────────
EVENT_TYPE_COLORS: Dict[str, str] = {
    "hotel_pm":   "#1B3A5C",   # 飯店保養 — 品牌主色（深藍）
    "mall_pm":    "#4BA8E8",   # 商場保養 — 品牌輔色（天藍）
    "full_pm":    "#006d75",   # 全棟例行維護 — 暗青
    "pm_plan":    "#52c41a",   # 週期保養預排 — 綠（主管排定）
    "approval":   "#fa8c16",   # 簽核管理 — 橙
    "memo":       "#722ed1",   # 公告牆   — 紫
    "custom":     "#13c2c2",   # 自訂事件 — 青
}

EVENT_TYPE_LABELS: Dict[str, str] = {
    "hotel_pm":   "飯店保養",
    "mall_pm":    "商場保養",
    "full_pm":    "全棟維護",
    "pm_plan":    "週期預排",
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
    event_type:   str                       # hotel_pm|mall_pm|pm_plan|approval|memo|custom
    module_label: str                       # 飯店保養|商場保養|...
    source_id:    str = ""                  # 原模組記錄 ID
    status:       str = ""                  # pending|completed|abnormal|overdue
    status_label: str = ""
    responsible:  str = ""                  # 負責人
    description:  str = ""                  # 補充說明
    deep_link:    str = ""                  # 跳轉路徑（前端 React Router 路徑）
    color:        str = ""                  # 顏色 hex
    zone:         str = "其它"              # 區域別：飯店/商場/公區/其它
    ragic_url:    str = ""                  # Ragic 原始記錄連結（空=無連結）

    # ── 明細 Drawer 強制規範欄位（CLAUDE.md §7 / WORK_JOURNAL_SPEC.md §9，2026-07-13 補上）──
    detail:        Dict[str, str] = {}      # 明細欄位區（來源模組原始欄位，中文 key，見 §9.2）
    image_item_id: str = ""                 # 附圖查詢用項目 ragic_id（空=此事件無附圖可查）

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
    zone:        str = "其它"     # 區域別：飯店/商場/公區/其它
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
    zone:         str = "其它"
    responsible:  str
    created_by:   str
    created_at:   Optional[Any] = None

    class Config:
        from_attributes = True
