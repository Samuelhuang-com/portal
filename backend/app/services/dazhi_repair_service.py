"""
大直工務部 — 共用 Service Layer

功能：
  1. Ragic 資料抓取（大直工務部主表）
  2. 欄位清洗與標準化（unified field mapping）
  3. 完成狀態判定（可集中配置）
  4. 報修類型標準化 mapping
  5. 客房房號解析
  6. 4.1 ~ 4.4 統計公式
  7. Dashboard 統計

資料來源：
  https://ap12.ragic.com/soutlet001/lequn-public-works/8?PAGEID=fV8

⚠️  欄位名稱對應說明：
    - 實際 Ragic 欄位名稱請用 /api/v1/dazhi-repair/raw-fields 確認
    - 若名稱不符，只需修改下方 RK_* 常數或 RK_ALIASES，業務邏輯不需改動
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, date
from typing import Any, Optional

from app.core.config import settings
from app.services.ragic_adapter import RagicAdapter
from app.services.ragic_data_service import (
    get_merged_records, parse_images, safe_work_days_to_hours,
    IMAGE_FIELD_DAZHI, invalidate,
)

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# 1. 可集中配置的常數
# ═════════════════════════════════════════════════════════════════════════════

# ── 1-A. 完成狀態集合（視為「已完成」的狀態值）───────────────────────────────
COMPLETED_STATUSES: set[str] = {
    # 大直工務部 Ragic 實際出現的狀態（2026-04-21 確認）
    "結案",
    "已辦驗",   # 已辦理驗收，視為完成（500 筆，21.5%）
    # 通用完成狀態（保留相容）
    "已驗收", "已結案", "完修", "已完成", "完成",
}
# 注意：以下視為未完成（程式用 not in COMPLETED_STATUSES 判定）
# "待修中", "待料中", "委外處理", "待辦驗", "辦驗未通過", "進行中", "待確認"

# ── 1-A-2. 排除狀態集合（不計入任何統計，明細總表仍可查閱）──────────────────
# 設計原因：「取消」案件既非「完成」也非「待辦」。
#   若歸入已完成 → 3月開單4月取消，3月完成率虛高；4月上月未完成少算
#   若歸入未完成 → 案件永遠殘留在待辦清單，污染未完成統計
#   正確做法   → 從統計中排除，視為「不計算」，只在明細總表保留記錄
EXCLUDED_STATUSES: set[str] = {
    "取消",
}


def is_completed(status: str) -> bool:
    """判斷案件是否已完成（集中配置，改此處即全部生效）"""
    return status.strip() in COMPLETED_STATUSES


def is_excluded(status: str) -> bool:
    """判斷案件是否排除於統計之外（取消等）"""
    return status.strip() in EXCLUDED_STATUSES


# ── 1-B. 報修類型標準化 mapping ───────────────────────────────────────────────
# key = 可能出現的原始值（小寫比對），value = 標準類型名稱
REPAIR_TYPE_MAPPING: dict[str, str] = {
    # 建築
    "建築": "建築", "結構": "建築", "外牆": "建築", "玻璃": "建築",
    "門窗": "建築", "電梯": "建築", "手扶梯": "建築", "招牌": "建築",
    # 衛廁
    "衛廁": "衛廁", "廁所": "衛廁", "馬桶": "衛廁", "洗手": "衛廁",
    "洗手槽": "衛廁", "烘手機": "衛廁", "哺乳": "衛廁",
    "蓮蓬頭": "衛廁", "浴缸": "衛廁", "花灑": "衛廁", "淋浴": "衛廁",
    "水龍頭": "衛廁", "洗臉": "衛廁", "面盆": "衛廁",
    # 消防
    "消防": "消防", "瓦斯": "消防", "偵煙": "消防", "灑水": "消防",
    "鐵捲門": "消防", "安全門": "消防", "緊急": "消防",
    # 空調
    "空調": "空調", "冷氣": "空調", "冷卻": "空調", "送風": "空調",
    "補風": "空調", "導流": "空調", "分離式": "空調",
    # 機電
    "機電": "機電", "機房": "機電", "發電機": "機電", "配電": "機電",
    # 給排水
    "給排水": "給排水", "漏水": "給排水", "水塔": "給排水",
    "污水": "給排水", "排水": "給排水", "給水": "給排水",
    # 排煙
    "排煙": "排煙", "靜電機": "排煙", "水洗機": "排煙",
    "截油槽": "排煙", "排煙管": "排煙",
    # 監控
    "監控": "監控", "cctv": "監控", "攝影": "監控", "監視": "監控",
    # 弱電
    "弱電": "弱電", "交換機": "弱電", "電話": "弱電", "網路": "弱電",
    # 照明
    "照明": "照明", "燈": "照明", "燈具": "照明", "路燈": "照明",
    # 停車
    "停車": "停車", "車牌": "停車", "繳費機": "停車", "柵欄": "停車",
    # 其他
    "人流": "其他", "入金機": "其他",
    # 專櫃
    "專櫃": "專櫃", "租戶": "專櫃", "承租": "專櫃",
    # 公區
    "公區": "公區", "公共": "公區", "lobby": "公區", "大廳": "公區",
    "廣場": "公區", "梯廳": "公區", "接待": "公區", "露台": "公區",
    # 後勤空間
    "後勤": "後勤空間", "辦公室": "後勤空間", "儲藏": "後勤空間",
    "員工餐": "後勤空間",
}

# 類型顯示順序（固定，不可隨意更改）
REPAIR_TYPE_ORDER = [
    "建築", "衛廁", "消防", "空調", "機電", "給排水",
    "排煙", "監控", "弱電", "照明", "停車", "其他",
    "專櫃", "公區", "後勤空間",
]

# 各類型的「內容舉例」說明文字（依規格書固定）
REPAIR_TYPE_EXAMPLES: dict[str, str] = {
    "建築": "連續壁 / 外觀玻璃 / 外觀門窗 / 電梯 / 手扶梯 / 招牌",
    "衛廁": "馬桶 / 洗手槽 / 烘手機 / 哺乳室",
    "消防": "瓦斯 / 偵煙感知器 / 灑水頭 / 鐵捲門 / 安全門",
    "空調": "主機 / 送風機 / 冷卻水塔 / 補風機 / 分離式冷氣 / 導流風機",
    "機電": "機房 / 發電機",
    "給排水": "漏水 / 水塔 / 污水處理",
    "排煙": "靜電機 / 水洗機 / 截油槽 / 排煙管",
    "監控": "CCTV / 監控主機",
    "弱電": "交換機 / 電話 / 網路",
    "照明": "建築外觀",
    "停車": "車牌辨識 / 自動繳費機 / 柵欄機",
    "其他": "人流計數器 / 入金機",
    "專櫃": "（可擴充）",
    "公區": "商場 / 停車場 / 梯廳 / 廣場；飯店：LOBBY / 4F接待區 / 4F露台 / 各層梯廳",
    "後勤空間": "辦公室 / 儲藏室 / 員工餐區",
}


def normalize_repair_type(raw_type: str, title: str = "", floor: str = "") -> str:
    """
    報修類型標準化。
    優先用 raw_type 欄位做 mapping；無法判定時再用 title / floor 關鍵字補判。
    最後歸到「其他」。
    """
    # 嘗試直接 mapping
    for keyword, std_type in REPAIR_TYPE_MAPPING.items():
        if keyword.lower() in raw_type.lower():
            return std_type

    # 嘗試標題關鍵字補判
    combined = (title + " " + floor).lower()
    for keyword, std_type in REPAIR_TYPE_MAPPING.items():
        if keyword.lower() in combined:
            return std_type

    # fallback
    return raw_type.strip() if raw_type.strip() else "其他"


# ── 1-C. 客房類別欄位對應（12 個標準分類）─────────────────────────────────────
ROOM_REPAIR_CATEGORIES = [
    "客房房門", "客房消防", "客房設備", "客房傢俱",
    "客房燈", "客房牆", "面盆/台面", "浴廁", "浴間",
    "天地壁", "配電盤", "環境",
]

# 客房判定關鍵字（出現在發生樓層或標題）
ROOM_FLOOR_KEYWORDS = [
    "5f", "6f", "7f", "8f", "9f", "10f",
    "5樓", "6樓", "7樓", "8樓", "9樓", "10樓", "客房",
]


# ── 1-D. 案件大小型分類邏輯（可後續改為依「核可層級」判斷）──────────────────
def is_large_repair(case: "RepairCase") -> bool:
    """
    判斷是否為中大型報修。
    初版邏輯：total_fee > 0 視為中大型，否則視為小型。
    後續可改此函式，畫面不需修改。
    """
    return case.total_fee > 0


# ═════════════════════════════════════════════════════════════════════════════
# 2. Ragic 欄位名稱常數（命名依實際 Ragic 回傳中文 key）
# ─────────────────────────────────────────────────────────────────────────────
# ⚠️  若 Ragic 回傳的欄位名稱與下方不符，只需修改這裡，不需改業務邏輯。
# ⚠️  可用 /api/v1/dazhi-repair/raw-fields 確認實際 key 名稱。
# ═════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# ⚠️  欄位名稱已依 /ping 端點回傳的實際 Ragic key 更新（2026-04-16）
#     實際資料範例 record #2315：
#       報修單編號 / 報修日期 / 報修人 / 反應單位 / 維修地點 / (備註/詳細說明)
#       類型(array) / 維修人員 / 維修日期 / 處理狀態 / 維修天數(天)
#       驗收人員 / 驗收日期 / 處理說明
# ─────────────────────────────────────────────────────────────────────────────

# 主要欄位
RK_CASE_NO         = "報修單編號"          # Ragic: 報修單編號
RK_TITLE           = "(備註/詳細說明)"     # Ragic: (備註/詳細說明) — 報修說明當作標題
RK_REPORTER        = "報修人"              # Ragic: 報修人
RK_REPAIR_TYPE     = "類型"               # Ragic: 類型（值為 JSON array，e.g. ["蓮蓬頭"]）
RK_FLOOR           = "維修地點"            # Ragic: 維修地點（值為房號，e.g. "526"）
RK_OCCURRED_AT     = "報修日期"            # Ragic: 報修日期（決定年月分組）
RK_RESPONSIBLE     = "反應單位"            # Ragic: 反應單位（e.g.房務部，部門）；人員統計用 RK_CLOSER（維修人員）
RK_WORK_HOURS      = "花費工時"            # 備用工時欄位；主欄位「維修天數」在 __init__ 直接讀取
RK_STATUS          = "處理狀態"            # Ragic: 處理狀態（e.g. "結案"）
RK_OUTSOURCE_FEE   = "委外費用"            # 此 Sheet 無此欄，回傳 0
RK_MAINTENANCE_FEE = "維修費用"            # 此 Sheet 無此欄，回傳 0
RK_ACCEPTOR        = "驗收人員"            # Ragic: 驗收人員
RK_ACCEPT_STATUS   = "驗收說明"            # Ragic: 驗收說明
RK_CLOSER          = "維修人員"            # Ragic: 維修人員（執行修繕的人）
RK_DEDUCTION_ITEM  = "扣款事項"            # 此 Sheet 無此欄
RK_DEDUCTION_FEE   = "扣款費用"            # 此 Sheet 無此欄，回傳 0
RK_FINANCE_NOTE    = "處理說明"            # Ragic: 處理說明
# 結案時間：優先用維修日期，再用驗收日期
RK_COMPLETED_AT    = "維修日期"            # Ragic: 維修日期（完修時間）
RK_CLOSE_DATE      = "驗收日期"            # Ragic: 驗收日期（備用）
RK_ACCEPT_DATE     = "驗收日期"            # Ragic: 驗收日期

# 別名對應（第一個 alias = Ragic 實際欄位名，後面為備用）
RK_ALIASES: dict[str, list[str]] = {
    RK_CASE_NO:         ["報修單編號", "報修編號", "編號", "案件編號"],
    RK_TITLE:           ["(備註/詳細說明)", "備註/詳細說明", "備註", "標題", "報修名稱"],
    RK_REPORTER:        ["報修人", "報修人姓名", "申報人"],
    RK_REPAIR_TYPE:     ["類型", "報修類型", "類別"],
    RK_FLOOR:           ["維修地點", "發生樓層", "樓層", "位置"],
    RK_OCCURRED_AT:     ["報修日期", "發生時間", "報修時間", "申報時間"],
    RK_RESPONSIBLE:     ["處理工務", "反應單位", "負責單位", "負責人", "承辦單位"],  # 2026-04-23: 處理工務優先
    RK_WORK_HOURS:      ["花費工時", "工時"],    # 主欄位；fallback 工務處理天數/維修天數在 __init__ 手動處理
    RK_STATUS:          ["處理狀態", "處理狀況", "狀態", "進度"],
    RK_OUTSOURCE_FEE:   ["委外費用", "外包費用"],
    RK_MAINTENANCE_FEE: ["維修費用", "費用"],
    RK_ACCEPTOR:        ["驗收人員", "驗收者", "驗收人"],
    RK_ACCEPT_STATUS:   ["驗收說明", "驗收", "驗收結果", "驗收狀態"],
    RK_CLOSER:          ["維修人員", "結案人", "結案者"],
    RK_DEDUCTION_ITEM:  ["扣款事項"],
    RK_DEDUCTION_FEE:   ["扣款費用"],
    RK_FINANCE_NOTE:    ["處理說明", "財務備註", "備註"],
    RK_COMPLETED_AT:    ["完工時間", "維修日期", "結案時間", "完成時間"],  # 實測：完工時間優先，維修日期備用
    RK_CLOSE_DATE:      ["驗收日期", "結案日期", "完成日期"],
    RK_ACCEPT_DATE:     ["驗收日期"],
}


def _get_field(raw: dict, canonical_key: str, fallback: str = "") -> Any:
    """
    從 Ragic 原始 dict 取值，支援多別名。
    找不到時回傳 fallback。
    """
    aliases = RK_ALIASES.get(canonical_key, [canonical_key])
    for alias in aliases:
        if alias in raw:
            return raw[alias]
    return fallback


# ═════════════════════════════════════════════════════════════════════════════
# 3. 資料清洗工具函式
# ═════════════════════════════════════════════════════════════════════════════

def _str(v: Any) -> str:
    """任意值轉字串，dict 取 value/label，list 用逗號連接"""
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(_str(x) for x in v)
    if isinstance(v, dict):
        val = v.get("value") or v.get("label") or ""
        return _str(val)
    return str(v).strip()


def _float(v: Any) -> float:
    """字串/數字轉 float，失敗回傳 0.0"""
    try:
        cleaned = re.sub(r"[,，$＄\s]", "", _str(v))
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        return 0.0


def _parse_datetime(v: Any) -> Optional[datetime]:
    """解析各種日期格式，失敗回傳 None"""
    s = _str(v)
    if not s:
        return None
    formats = [
        "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
        "%Y.%m.%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s.strip(), fmt)
        except (ValueError, TypeError):
            continue
    # 嘗試只取前 10 碼
    try:
        return datetime.strptime(s[:10], "%Y/%m/%d")
    except Exception:
        pass
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except Exception:
        pass
    logger.debug(f"[DazhiRepair] 無法解析日期: {s!r}")
    return None


def _parse_room_no(floor: str, title: str) -> tuple[str, str]:
    """
    從發生樓層或標題中解析「房號」與「樓層」。
    回傳 (room_no, floor_normalized)

    房號規則：3~4 位數字（e.g. 501, 1023）
    客房樓層：5F~10F
    """
    combined = f"{floor} {title}"
    # 尋找房號（3~4 位數字）
    room_match = re.search(r"\b([5-9]\d{2}|10\d{2})\b", combined)
    room_no = room_match.group(1) if room_match else ""

    # 標準化樓層
    floor_match = re.search(r"(\d+)[Ff樓]", combined)
    floor_num = floor_match.group(1) if floor_match else ""
    floor_normalized = f"{floor_num}F" if floor_num else floor.strip()

    return room_no, floor_normalized


def _is_room_case(floor: str, title: str, repair_type: str) -> bool:
    """判斷案件是否屬於客房報修"""
    combined = (floor + " " + title + " " + repair_type).lower()
    for kw in ROOM_FLOOR_KEYWORDS:
        if kw.lower() in combined:
            return True
    # 有解析出客房房號也算
    room_no, _ = _parse_room_no(floor, title)
    return bool(room_no)


def _classify_room_category(repair_type: str, title: str) -> str:
    """將案件歸類到客房報修的 12 個分類之一"""
    combined = (repair_type + " " + title).lower()
    category_keywords: dict[str, list[str]] = {
        "客房房門":  ["房門", "門鎖", "門縫", "門框"],
        "客房消防":  ["消防", "偵煙", "灑水", "火警"],
        "客房設備":  ["設備", "電視", "冰箱", "電話", "保險箱", "電熱水器"],
        "客房傢俱":  ["傢俱", "家具", "床", "椅", "桌", "衣櫃", "沙發"],
        "客房燈":    ["燈", "電源", "插座", "開關"],
        "客房牆":    ["牆", "壁紙", "油漆", "牆面"],
        "面盆/台面": ["面盆", "台面", "水龍頭", "鏡面"],
        "浴廁":      ["浴廁", "馬桶", "洗手", "廁所"],
        "浴間":      ["浴間", "浴缸", "淋浴", "蓮蓬頭"],
        "天地壁":    ["天花板", "地板", "地磚", "天地壁"],
        "配電盤":    ["配電盤", "電箱", "斷路器"],
        "環境":      ["異味", "噪音", "蟲", "環境"],
    }
    for cat, keywords in category_keywords.items():
        for kw in keywords:
            if kw in combined:
                return cat
    return "客房設備"  # default fallback


# ═════════════════════════════════════════════════════════════════════════════
# 4. RepairCase 資料類別（標準化後的案件）
# ═════════════════════════════════════════════════════════════════════════════

class RepairCase:
    """標準化後的單筆報修案件（大直工務部）"""
    __slots__ = (
        "ragic_id", "case_no", "title", "reporter_name", "repair_type",
        "floor", "occurred_at", "responsible_unit", "work_hours",
        "status", "outsource_fee", "maintenance_fee",
        "acceptor", "accept_status", "closer",
        "deduction_item", "deduction_fee", "finance_note",
        "total_fee", "is_completed_flag", "is_excluded_flag", "completed_at", "close_days",
        "pending_days",
        "year", "month",
        "is_room_case", "room_no", "floor_normalized", "room_category",
        "images",
        "_raw",
    )

    def __init__(self, ragic_id: str, raw: dict):
        self._raw = raw
        self.ragic_id = ragic_id

        # 基本欄位
        self.case_no          = _str(_get_field(raw, RK_CASE_NO))
        self.title            = _str(_get_field(raw, RK_TITLE))
        self.reporter_name    = _str(_get_field(raw, RK_REPORTER))
        self.floor            = _str(_get_field(raw, RK_FLOOR))
        self.occurred_at      = _parse_datetime(_get_field(raw, RK_OCCURRED_AT))
        self.responsible_unit = _str(_get_field(raw, RK_RESPONSIBLE))
        # 工時：① 維修天數（天 ×24，上限 365 天防誤植年份如 2026→48624hr）→ ② 花費工時
        _work_hrs = safe_work_days_to_hours(raw.get("維修天數", ""))
        if _work_hrs <= 0:
            _work_hrs = _float(_get_field(raw, RK_WORK_HOURS))  # 花費工時（備用）
        self.work_hours = _work_hrs
        self.status           = _str(_get_field(raw, RK_STATUS))
        self.outsource_fee    = _float(_get_field(raw, RK_OUTSOURCE_FEE))
        self.maintenance_fee  = _float(_get_field(raw, RK_MAINTENANCE_FEE))
        self.acceptor         = _str(_get_field(raw, RK_ACCEPTOR))
        self.accept_status    = _str(_get_field(raw, RK_ACCEPT_STATUS))
        self.closer           = _str(_get_field(raw, RK_CLOSER))
        self.deduction_item   = _str(_get_field(raw, RK_DEDUCTION_ITEM))
        self.deduction_fee    = _float(_get_field(raw, RK_DEDUCTION_FEE))
        self.finance_note     = _str(_get_field(raw, RK_FINANCE_NOTE))

        # 報修類型標準化
        raw_type = _str(_get_field(raw, RK_REPAIR_TYPE))
        self.repair_type = normalize_repair_type(raw_type, self.title, self.floor)

        # 衍生欄位
        self.total_fee        = self.outsource_fee + self.maintenance_fee
        self.is_excluded_flag = is_excluded(self.status)  # 取消等不計入統計

        # 結案時間：優先用 RK_COMPLETED_AT，再 RK_CLOSE_DATE，再 RK_ACCEPT_DATE
        completed_raw = (
            _get_field(raw, RK_COMPLETED_AT) or
            _get_field(raw, RK_CLOSE_DATE)   or
            _get_field(raw, RK_ACCEPT_DATE)
        )
        self.completed_at = _parse_datetime(completed_raw)

        # 完工判定：有「完工時間」即視為已完工，無論處理狀態
        self.is_completed_flag = (self.completed_at is not None) or is_completed(self.status)

        # 結案天數（close_days = completed_at - occurred_at）
        if self.is_completed_flag and self.occurred_at and self.completed_at:
            delta = self.completed_at - self.occurred_at
            self.close_days = round(delta.total_seconds() / 86400, 2)
        else:
            self.close_days = None

        # 未完成天數（pending_days = now - occurred_at，僅 completed_at 為空的案件）
        if self.completed_at is None and self.occurred_at:
            self.pending_days = round(
                (datetime.now() - self.occurred_at).total_seconds() / 86400
            )
        else:
            self.pending_days = None

        # 年月（以發生時間為準）
        if self.occurred_at:
            self.year  = self.occurred_at.year
            self.month = self.occurred_at.month
        else:
            self.year  = None
            self.month = None

        # 客房相關
        self.is_room_case     = _is_room_case(self.floor, self.title, raw_type)
        self.room_no, self.floor_normalized = _parse_room_no(self.floor, self.title)
        self.room_category    = _classify_room_category(raw_type, self.title) if self.is_room_case else ""

        # 圖片（Ragic 「上傳圖片」附件欄位，用 file.jsp API 取實際檔案）
        self.images = parse_images(
            raw.get(IMAGE_FIELD_DAZHI) or raw.get("上傳圖片.1") or raw.get("維修照上傳") or raw.get("維修照"),
            server=settings.RAGIC_DAZHI_REPAIR_SERVER_URL,
            account=settings.RAGIC_DAZHI_REPAIR_ACCOUNT,
        )

    def to_dict(self) -> dict:
        """轉換為 API 回傳用 dict"""
        return {
            "ragic_id":         self.ragic_id,
            "case_no":          self.case_no,
            "title":            self.title,
            "reporter_name":    self.reporter_name,
            "repair_type":      self.repair_type,
            "floor":            self.floor,
            "floor_normalized": self.floor_normalized,
            "occurred_at":      self.occurred_at.strftime("%Y/%m/%d %H:%M") if self.occurred_at else "",
            "responsible_unit": self.responsible_unit,
            "work_hours":       self.work_hours,
            "status":           self.status,
            "outsource_fee":    self.outsource_fee,
            "maintenance_fee":  self.maintenance_fee,
            "total_fee":        self.total_fee,
            "acceptor":         self.acceptor,
            "accept_status":    self.accept_status,
            "closer":           self.closer,
            "deduction_item":   self.deduction_item,
            "deduction_fee":    self.deduction_fee,
            "finance_note":     self.finance_note,
            "is_completed":     self.is_completed_flag,
            "is_excluded":      self.is_excluded_flag,
            "completed_at":     self.completed_at.strftime("%Y/%m/%d") if self.completed_at else "",
            "close_days":       self.close_days,
            "pending_days":     self.pending_days,
            "year":             self.year,
            "month":            self.month,
            "is_room_case":     self.is_room_case,
            "room_no":          self.room_no,
            "room_category":    self.room_category,
            "images":           self.images,
        }


# ═════════════════════════════════════════════════════════════════════════════
# 5. Ragic 資料抓取
# ═════════════════════════════════════════════════════════════════════════════

def _get_adapter() -> RagicAdapter:
    return RagicAdapter(
        sheet_path=settings.RAGIC_DAZHI_REPAIR_PATH,
        api_key=settings.RAGIC_API_KEY,
        server_url=settings.RAGIC_DAZHI_REPAIR_SERVER_URL,
        account=settings.RAGIC_DAZHI_REPAIR_ACCOUNT,
    )


_CACHE_KEY = "dazhi_repair"

async def fetch_all_cases() -> list[RepairCase]:
    """
    從 Ragic 抓取全部報修案件（主表 + detail merge），清洗後回傳 RepairCase list。
    採 stale-while-revalidate：首次回傳主表資料，背景完成 detail merge 後更新 cache。
    """
    adapter = _get_adapter()
    records = await get_merged_records(
        adapter=adapter,
        cache_key=_CACHE_KEY,
        limit=500,
        extra_params={"PAGEID": settings.RAGIC_DAZHI_REPAIR_PAGEID},
    )

    cases: list[RepairCase] = []
    for record in records:
        rid = record.get("_ragic_id", "")
        try:
            cases.append(RepairCase(ragic_id=rid, raw=record))
        except Exception as exc:
            logger.warning(f"[DazhiRepair] 案件 {rid} 清洗失敗，跳過: {exc}")

    logger.info(f"[DazhiRepair] 共載入 {len(cases)} 筆案件")
    return cases


def invalidate_cache() -> None:
    """清除大直報修 cache（sync 後呼叫）"""
    invalidate(_CACHE_KEY)


async def fetch_raw_fields() -> dict:
    """取得第一筆資料的 key 列表（供 debug / 欄位確認用）"""
    adapter = _get_adapter()
    try:
        raw_data = await adapter.fetch_all(
            limit=2,
            extra_params={"PAGEID": settings.RAGIC_DAZHI_REPAIR_PAGEID},
        )
        for rid, row in raw_data.items():
            return {"ragic_id": rid, "fields": list(row.keys()), "sample": row}
    except Exception as exc:
        logger.error(f"[DazhiRepair] fetch_raw_fields 失敗: {exc}")
    return {}


# ═════════════════════════════════════════════════════════════════════════════
# 6. 過濾輔助
# ═════════════════════════════════════════════════════════════════════════════

def _stat_year(c) -> Optional[int]:
    """統計年份：有完工時間 → 完工年；否則 → 報修年。
    直接讀 completed_at 避免 ORM 物件因舊資料 year 欄位不正確。"""
    at = getattr(c, 'completed_at', None)
    if at is not None:
        return at.year
    return getattr(c, 'year', None)


def _stat_month(c) -> Optional[int]:
    """統計月份：有完工時間 → 完工月；否則 → 報修月。"""
    at = getattr(c, 'completed_at', None)
    if at is not None:
        return at.month
    return getattr(c, 'month', None)


def filter_cases(
    cases: list[RepairCase],
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> list[RepairCase]:
    """依統計年/月過濾（直接從 completed_at 計算，不依賴儲存的 year/month）"""
    result = cases
    if year is not None:
        result = [c for c in result if _stat_year(c) == year]
    if month is not None:
        result = [c for c in result if _stat_month(c) == month]
    return result


def filter_cases_up_to(
    cases: list[RepairCase],
    year: int,
    month: int,
) -> list[RepairCase]:
    """回傳 occurred_at <= 指定年月底的所有案件"""
    return [
        c for c in cases
        if c.year is not None and (
            c.year < year or (c.year == year and c.month <= month)
        )
    ]


def get_years(cases: list[RepairCase]) -> list[int]:
    """取得資料中所有年份（排序後）"""
    years = sorted({c.year for c in cases if c.year is not None}, reverse=True)
    return years if years else [datetime.now().year]


# ═════════════════════════════════════════════════════════════════════════════
# 7. Dashboard 統計
# ═════════════════════════════════════════════════════════════════════════════

def compute_dashboard(
    all_cases: list[RepairCase],
    year: int,
    month: int,
) -> dict:
    """
    Dashboard KPI + 圖表資料。
    month 若為 0 表示顯示全年。
    """
    # 排除「取消」等不計入統計的案件（明細總表仍完整保留）
    all_cases = [c for c in all_cases if not c.is_excluded_flag]
    this_month_cases = filter_cases(all_cases, year, month if month else None)

    # ── KPI ──────────────────────────────────────────────────────────────────
    total       = len(this_month_cases)
    completed   = sum(1 for c in this_month_cases if c.is_completed_flag)
    uncompleted = total - completed
    room_cases  = [c for c in this_month_cases if c.is_room_case]

    close_days_list = [
        c.close_days for c in this_month_cases
        if c.is_completed_flag and c.close_days is not None
    ]
    avg_close_days = (
        round(sum(close_days_list) / len(close_days_list), 2)
        if close_days_list else None
    )

    total_fee        = sum(c.total_fee    for c in this_month_cases)
    total_work_hours = round(sum(c.work_hours for c in this_month_cases), 2)

    # ── 近 12 個月趨勢 ────────────────────────────────────────────────────────
    trend_12m = []
    for m_offset in range(11, -1, -1):
        y, m = _month_offset(year, month if month else datetime.now().month, -m_offset)
        mc = filter_cases(all_cases, y, m)
        trend_12m.append({
            "label":     f"{y}/{m:02d}",
            "year":      y,
            "month":     m,
            "total":     len(mc),
            "completed": sum(1 for c in mc if c.is_completed_flag),
        })

    # ── 類型分布 ──────────────────────────────────────────────────────────────
    type_dist: dict[str, int] = {}
    for c in this_month_cases:
        type_dist[c.repair_type] = type_dist.get(c.repair_type, 0) + 1

    # ── 樓層分布 ──────────────────────────────────────────────────────────────
    floor_dist: dict[str, int] = {}
    for c in this_month_cases:
        key = c.floor_normalized or c.floor or "未知"
        floor_dist[key] = floor_dist.get(key, 0) + 1

    # ── 狀態分布 ──────────────────────────────────────────────────────────────
    status_dist: dict[str, int] = {}
    for c in this_month_cases:
        status_dist[c.status] = status_dist.get(c.status, 0) + 1

    # ── 未完成 Top10（completed_at 為空 = 真正未完成，依等待天數降序）──────────
    all_uncompleted = [c for c in all_cases if c.completed_at is None and c.occurred_at]
    all_uncompleted.sort(
        key=lambda x: (datetime.now() - x.occurred_at).total_seconds(),
        reverse=True,
    )
    top_uncompleted = [c.to_dict() for c in all_uncompleted[:10]]

    # ── 高費用 Top10 ──────────────────────────────────────────────────────────
    fee_list = sorted(this_month_cases, key=lambda x: x.total_fee, reverse=True)
    top_fee = [c.to_dict() for c in fee_list[:10] if c.total_fee > 0]

    # ── 高工時 Top10 ──────────────────────────────────────────────────────────
    hours_list = sorted(this_month_cases, key=lambda x: x.work_hours, reverse=True)
    top_hours = [c.to_dict() for c in hours_list[:10] if c.work_hours > 0]

    # ── 當月費用（依篩選月份，月份=0 時為全年）────────────────────────────────
    month_outsource_fee     = round(sum(c.outsource_fee   for c in this_month_cases), 2)
    month_maintenance_fee   = round(sum(c.maintenance_fee for c in this_month_cases), 2)
    month_deduction_fee     = round(sum(c.deduction_fee   for c in this_month_cases), 2)
    month_deduction_counter = 0.0  # 大直無此欄位
    month_total_fee         = round(month_outsource_fee + month_maintenance_fee + month_deduction_fee, 2)

    # ── 年度費用合計（全年，不限月份）─────────────────────────────────────────
    year_cases = filter_cases(all_cases, year, None)
    annual_outsource    = round(sum(c.outsource_fee   for c in year_cases), 2)
    annual_maintenance  = round(sum(c.maintenance_fee for c in year_cases), 2)
    annual_fee          = round(annual_outsource + annual_maintenance, 2)
    annual_deduction    = round(sum(c.deduction_fee   for c in year_cases), 2)

    # 年度費用明細 — 委外+維修 Top20
    annual_fee_records = sorted(
        [c for c in year_cases if c.total_fee > 0],
        key=lambda x: x.total_fee, reverse=True,
    )
    annual_fee_detail = [
        {**c.to_dict(), "outsource_fee": c.outsource_fee, "maintenance_fee": c.maintenance_fee}
        for c in annual_fee_records[:20]
    ]

    # 年度扣款費用明細 Top20
    annual_deduction_detail = [
        c.to_dict() for c in sorted(
            [c for c in year_cases if c.deduction_fee > 0],
            key=lambda x: x.deduction_fee, reverse=True,
        )[:20]
    ]

    # ── KPI 明細（點擊卡片時用）──────────────────────────────────────────────
    completed_cases   = [c for c in this_month_cases if c.is_completed_flag]
    uncompleted_cases = [c for c in this_month_cases if not c.is_completed_flag]
    close_days_cases  = [c for c in this_month_cases if c.is_completed_flag and c.close_days is not None]
    work_hours_cases  = sorted([c for c in this_month_cases if c.work_hours > 0], key=lambda x: x.work_hours, reverse=True)

    return {
        "kpi": {
            "total":            total,
            "completed":        completed,
            "uncompleted":      uncompleted,
            "avg_close_days":   avg_close_days,
            "total_fee":        total_fee,
            "total_work_hours": total_work_hours,
            "room_cases":       len(room_cases),
            # 當月費用（依年+月篩選，月份=0 時為全年合計）
            "month_outsource_fee":     month_outsource_fee,
            "month_maintenance_fee":   month_maintenance_fee,
            "month_deduction_fee":     month_deduction_fee,
            "month_deduction_counter": month_deduction_counter,
            "month_total_fee":         month_total_fee,
            # 年度費用（費用 KPI 卡片用，不受月份篩選影響）
            "annual_fee":              annual_fee,
            "annual_outsource_fee":    annual_outsource,
            "annual_maintenance_fee":  annual_maintenance,
            "annual_deduction_fee":    annual_deduction,
        },
        # KPI 明細清單
        "kpi_total_detail":      [c.to_dict() for c in sorted(this_month_cases, key=lambda x: x.occurred_at or datetime.min, reverse=True)],
        "kpi_completed_detail":  [c.to_dict() for c in sorted(completed_cases,   key=lambda x: x.completed_at or datetime.min, reverse=True)],
        "kpi_uncompleted_detail":[c.to_dict() for c in sorted(uncompleted_cases, key=lambda x: x.occurred_at or datetime.min)],
        "kpi_close_days_detail": [c.to_dict() for c in sorted(close_days_cases,  key=lambda x: x.close_days or 0, reverse=True)],
        "kpi_room_detail":       [c.to_dict() for c in sorted(room_cases,        key=lambda x: x.occurred_at or datetime.min, reverse=True)],
        "kpi_hours_detail":      [c.to_dict() for c in work_hours_cases],
        "trend_12m":     trend_12m,
        "type_dist":     [{"type": k, "count": v} for k, v in type_dist.items()],
        "floor_dist":    [{"floor": k, "count": v} for k, v in sorted(floor_dist.items(), key=lambda x: -x[1])],
        "status_dist":   [{"status": k, "count": v} for k, v in status_dist.items()],
        "top_uncompleted": top_uncompleted,
        "top_fee":         top_fee,
        "top_hours":       top_hours,
        # 年度費用明細（點擊 KPI 卡片時用）
        "annual_fee_detail":        annual_fee_detail,
        "annual_deduction_detail":  annual_deduction_detail,
    }


def _month_offset(year: int, month: int, offset: int) -> tuple[int, int]:
    """計算月份偏移（offset 為正數往後、負數往前）"""
    total = (year * 12 + month - 1) + offset
    return total // 12, total % 12 + 1


# ═════════════════════════════════════════════════════════════════════════════
# 8. 4.1 報修統計
# ═════════════════════════════════════════════════════════════════════════════

def _completed_by(c: RepairCase, y: int, m: int) -> bool:
    """截至 (y, m) 月底已完成（completed_at 落在 <= 該月）"""
    if not c.completed_at:
        return False
    cy, cm = c.completed_at.year, c.completed_at.month
    return cy < y or (cy == y and cm <= m)


def _completed_in(c: RepairCase, y: int, m: int) -> bool:
    """completed_at 恰好落在 (y, m) 月"""
    if not c.completed_at:
        return False
    return c.completed_at.year == y and c.completed_at.month == m


def compute_repair_stats(
    all_cases: list[RepairCase],
    year: int,
) -> dict:
    """
    4.1 報修統計表：1月~12月 × 6項統計指標。

    統計項目：
    1. 上月累計未完成項目數
    2. 上月累計未完成項目，於本月結案數
    3. 累計項目完成率
    4. 本月報修項目數
    5. 本月報修項目完成數
    6. 本月報修項目完成率

    時間規則：「完成」以 completed_at 時間戳為準，不使用 is_completed_flag（當前狀態）。
    """
    # 排除「取消」等不計入統計的案件（明細總表仍完整保留）
    all_cases = [c for c in all_cases if not c.is_excluded_flag]
    months_data = {}

    for month in range(1, 13):
        # 截至上月底的累計案件（occurred_at <= 上月底）
        prev_y, prev_m = _month_offset(year, month, -1)
        cases_up_to_prev = [
            c for c in all_cases
            if c.year is not None and (
                c.year < prev_y or (c.year == prev_y and c.month <= prev_m)
            )
        ]
        # 1. 上月累計未完成（截至上月底尚未完成）
        prev_uncompleted = [c for c in cases_up_to_prev if not _completed_by(c, prev_y, prev_m)]
        prev_uncompleted_count = len(prev_uncompleted)

        # 2. 上月未完成，本月結案數（completed_at 落在本月）
        closed_from_prev_list = [c for c in prev_uncompleted if _completed_in(c, year, month)]
        closed_this_month_from_prev = len(closed_from_prev_list)

        # 3. 累計完成率（截至本月底，以 completed_at 為準）
        cases_up_to_this = [
            c for c in all_cases
            if c.year is not None and (
                c.year < year or (c.year == year and c.month <= month)
            )
        ]
        cum_total = len(cases_up_to_this)
        cum_completed = sum(1 for c in cases_up_to_this if _completed_by(c, year, month))
        cum_rate = round(cum_completed / cum_total * 100, 1) if cum_total > 0 else None

        # 4. 本月報修項目數
        this_month_cases = filter_cases(all_cases, year, month)
        this_total = len(this_month_cases)

        # 5. 本月報修項目完成數（completed_at 落在本月）
        this_completed_list = [c for c in this_month_cases if _completed_in(c, year, month)]
        this_completed = len(this_completed_list)

        # 6. 本月未完成數
        this_uncompleted = this_total - this_completed

        # 7. 本月完成率
        this_rate = round(this_completed / this_total * 100, 1) if this_total > 0 else None

        months_data[month] = {
            "month":                      month,
            "prev_uncompleted":           prev_uncompleted_count,
            "closed_from_prev":           closed_this_month_from_prev,
            "cum_completion_rate":        cum_rate,
            "this_month_total":           this_total,
            "this_month_completed":       this_completed,
            "this_month_uncompleted":     this_uncompleted,
            "this_month_completion_rate": this_rate,
            # 明細（可點擊展開）
            "prev_uncompleted_detail":     [c.to_dict() for c in prev_uncompleted],
            "closed_from_prev_detail":     [c.to_dict() for c in closed_from_prev_list],
            "this_month_total_detail":     [c.to_dict() for c in this_month_cases],
            "this_month_completed_detail": [c.to_dict() for c in this_completed_list],
        }

    return {"year": year, "months": months_data}


# ═════════════════════════════════════════════════════════════════════════════
# 9. 金額統計（費用類型 × 月份交叉表）
# ═════════════════════════════════════════════════════════════════════════════

FEE_KEYS = ["outsource_fee", "maintenance_fee", "deduction_fee"]
FEE_LABELS = {
    "outsource_fee":   "委外費用",
    "maintenance_fee": "維修費用",
    "deduction_fee":   "扣款費用",
}


def compute_fee_stats(all_cases: list, year: int) -> dict:
    """
    金額統計：3 項費用 × 12 個月交叉表。
    回傳 monthly[月份][fee_key] = 金額合計，以及各維度小計。
    同時回傳每個非零格子的明細案件清單（供點擊展開）。

    注意：大直工務部目前 Ragic 無「扣款專櫃」欄位，
    若 Ragic 日後補上，將 deduction_counter 加入 FEE_KEYS 即可。
    """
    # 排除「取消」等不計入統計的案件
    all_cases = [c for c in all_cases if not c.is_excluded_flag]
    monthly_totals: dict[int, dict[str, float]] = {}
    monthly_detail: dict[str, list[dict]] = {}

    for m in range(1, 13):
        mc = filter_cases(all_cases, year, m)
        monthly_totals[m] = {
            fk: round(sum(getattr(c, fk, 0) for c in mc), 2) for fk in FEE_KEYS
        }
        for fk in FEE_KEYS:
            cases_with_fee = [c for c in mc if getattr(c, fk, 0) > 0]
            cases_with_fee.sort(key=lambda c: getattr(c, fk, 0), reverse=True)
            if cases_with_fee:
                monthly_detail[f"{m}_{fk}"] = [c.to_dict() for c in cases_with_fee]

    fee_totals = {fk: round(sum(monthly_totals[m][fk] for m in range(1,13)), 2) for fk in FEE_KEYS}
    month_totals = {m: round(sum(monthly_totals[m][fk] for fk in FEE_KEYS), 2) for m in range(1,13)}
    grand_total = round(sum(fee_totals.values()), 2)
    return {"year": year, "monthly_totals": monthly_totals, "fee_totals": fee_totals, "month_totals": month_totals, "grand_total": grand_total, "monthly_detail": monthly_detail, "fee_labels": FEE_LABELS}


# ═════════════════════════════════════════════════════════════════════════════
# 9. 4.2 結案時間統計
# ═════════════════════════════════════════════════════════════════════════════

def _closed_in(c: RepairCase, y: int, m: int) -> bool:
    """completed_at 落在 (y, m) 月且有 close_days（用於結案時間統計）"""
    return _completed_in(c, y, m) and c.close_days is not None


def compute_closing_time(
    all_cases: list[RepairCase],
    year: int,
    month: Optional[int] = None,
) -> dict:
    """
    4.2 結案時間統計。
    時間規則：以 completed_at 落在哪個月為準，不使用 is_completed_flag。
    """
    all_cases = [c for c in all_cases if not c.is_excluded_flag]

    def block(cases):
        total_days = round(sum(c.close_days for c in cases), 2)
        return {
            "closed_count": len(cases),
            "total_days": total_days,
            "avg_days": round(total_days / len(cases), 2) if cases else None,
        }

    monthly: dict = {}
    for m in range(1, 13):
        mc_closed = [c for c in all_cases if _closed_in(c, year, m)]
        monthly[m] = {
            "small": block([c for c in mc_closed if not is_large_repair(c)]),
            "large": block([c for c in mc_closed if is_large_repair(c)]),
        }

    # 彙總列（month=None 時顯示全年；有指定月份時顯示該月）
    if month is not None:
        summary_closed = [c for c in all_cases if _closed_in(c, year, month)]
    else:
        summary_closed = [c for c in all_cases if _completed_by(c, year, 12) and c.close_days is not None
                          and c.completed_at and c.completed_at.year == year]
    small = [c for c in summary_closed if not is_large_repair(c)]
    large = [c for c in summary_closed if is_large_repair(c)]

    return {
        "year": year, "month": month,
        "small": block(small), "large": block(large),
        "monthly": monthly,
        "classification_note": "小型=total_fee=0；中大型=total_fee>0",
    }


# ═════════════════════════════════════════════════════════════════════════════
# 10. 4.3 報修類型統計
# ═════════════════════════════════════════════════════════════════════════════

def compute_type_stats(
    all_cases: list[RepairCase],
    year: int,
    month: Optional[int] = None,
) -> dict:
    all_cases = [c for c in all_cases if not c.is_excluded_flag]
    year_cases = filter_cases(all_cases, year)
    focus_month = month

    type_monthly: dict[str, dict[int, int]] = {t: {} for t in REPAIR_TYPE_ORDER}
    type_monthly_cases: dict[str, dict[int, list]] = {t: {} for t in REPAIR_TYPE_ORDER}

    for case in year_cases:
        m = _stat_month(case)
        if m is None:
            continue
        rt = case.repair_type
        if rt not in type_monthly:
            type_monthly[rt] = {}
            type_monthly_cases[rt] = {}
        type_monthly[rt][m] = type_monthly[rt].get(m, 0) + 1
        type_monthly_cases[rt].setdefault(m, []).append(case)

    rows = []
    year_total = 0
    for rt in REPAIR_TYPE_ORDER:
        monthly = type_monthly.get(rt, {})
        row_total = sum(monthly.values())
        year_total += row_total
        prev_m_val = monthly.get(_month_offset(year, focus_month or datetime.now().month, -1)[1], 0) if focus_month else 0
        this_m_val = monthly.get(focus_month, 0) if focus_month else 0
        monthly_detail = {
            m: [c.to_dict() for c in cs]
            for m, cs in type_monthly_cases.get(rt, {}).items()
        }
        rows.append({
            "type": rt,
            "example": REPAIR_TYPE_EXAMPLES.get(rt, ""),
            "monthly": {m: monthly.get(m, 0) for m in range(1, 13)},
            "monthly_detail": monthly_detail,
            "row_total": row_total,
            "prev_month": prev_m_val,
            "this_month": this_m_val,
            "cum_pct": round(row_total / len(year_cases) * 100, 1) if year_cases else 0.0,
        })

    return {
        "year": year, "focus_month": focus_month,
        "rows": rows, "year_total": year_total,
        "type_order": REPAIR_TYPE_ORDER,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 11. 4.4 客房報修表
# ═════════════════════════════════════════════════════════════════════════════

def compute_room_repair_table(
    all_cases: list[RepairCase],
    year: int,
    month: int,
) -> dict:
    all_cases = [c for c in all_cases if not c.is_excluded_flag]
    room_cases = [c for c in filter_cases(all_cases, year, month) if c.is_room_case]

    matrix: dict[str, dict[str, list]] = {}
    unknown_room: list = []

    for case in room_cases:
        rno = case.room_no
        cat = case.room_category or "客房設備"
        if not rno:
            unknown_room.append(case.to_dict())
            continue
        if rno not in matrix:
            matrix[rno] = {c: [] for c in ROOM_REPAIR_CATEGORIES}
        if cat not in matrix[rno]:
            matrix[rno][cat] = []
        matrix[rno][cat].append(case.to_dict())

    sorted_rooms = sorted(matrix.keys())
    floors_with_data: set[str] = set()
    for rno in sorted_rooms:
        if rno:
            try:
                floor_num = int(rno[0]) if len(rno) == 3 else int(rno[:2])
                floors_with_data.add(f"{floor_num}F")
            except (ValueError, IndexError):
                pass

    rows = [
        {
            "room_no": rno,
            "floor": f"{rno[0]}F" if len(rno) == 3 else (f"{rno[:2]}F" if len(rno) >= 2 else "?"),
            "categories": matrix[rno],
        }
        for rno in sorted_rooms
    ]

    return {
        "year": year, "month": month,
        "categories": ROOM_REPAIR_CATEGORIES,
        "rows": rows,
        "unknown_room_cases": unknown_room,
        "floors_with_data": sorted(floors_with_data),
        "total_room_cases": len(room_cases),
    }


# ═════════════════════════════════════════════════════════════════════════════
# 12. 明細查詢
# ═════════════════════════════════════════════════════════════════════════════

def query_detail(
    all_cases: list[RepairCase],
    year: Optional[int] = None,
    month: Optional[int] = None,
    repair_type: Optional[str] = None,
    floor: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "occurred_at",
    sort_desc: bool = True,
) -> dict:
    result = all_cases
    if year is not None:
        result = [c for c in result if _stat_year(c) == year]
    if month is not None:
        result = [c for c in result if _stat_month(c) == month]
    if repair_type:
        result = [c for c in result if c.repair_type == repair_type]
    if floor:
        result = [c for c in result if floor.lower() in (c.floor + " " + c.floor_normalized).lower()]
    if status:
        result = [c for c in result if c.status == status]
    if keyword:
        kw = keyword.lower()
        result = [c for c in result if kw in c.case_no.lower() or kw in c.title.lower()]

    sort_key_map = {
        "occurred_at": lambda c: c.occurred_at or datetime.min,
        "total_fee":   lambda c: c.total_fee,
        "work_hours":  lambda c: c.work_hours,
        "close_days":  lambda c: c.close_days or 0.0,
        "case_no":     lambda c: c.case_no,
    }
    result.sort(key=sort_key_map.get(sort_by, sort_key_map["occurred_at"]), reverse=sort_desc)

    total = len(result)
    start = (page - 1) * page_size
    return {
        "total": total, "page": page, "page_size": page_size,
        "items": [c.to_dict() for c in result[start:start + page_size]],
    }


def get_filter_options(all_cases: list[RepairCase]) -> dict:
    return {
        "repair_types": sorted({c.repair_type for c in all_cases if c.repair_type}),
        "floors":       sorted({(c.floor_normalized or c.floor) for c in all_cases if c.floor}),
        "statuses":     sorted({c.status for c in all_cases if c.status}),
    }
