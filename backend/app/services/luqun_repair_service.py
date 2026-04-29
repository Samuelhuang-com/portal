"""
樂群工務報修 — 共用 Service Layer

功能：
  1. Ragic 資料抓取（春大直-報修清單總表）
  2. 欄位清洗與標準化（unified field mapping）
  3. 完成狀態判定（可集中配置）
  4. 報修類型標準化 mapping
  5. 客房房號解析
  6. 4.1 ~ 4.4 統計公式
  7. Dashboard 統計

資料來源：
  https://ap12.ragic.com/soutlet001/luqun-public-works-repair-reporting-system/6
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
    IMAGE_FIELD_LUQUN, invalidate,
)

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# 1. 可集中配置的常數
# ═════════════════════════════════════════════════════════════════════════════

# ── 1-A. 完成狀態集合（視為「已完成」的狀態值）───────────────────────────────
COMPLETED_STATUSES: set[str] = {
    "已驗收",
    "已結案",
    "結案",
    "完修",
    "已完成",
    "完成",
    "已辦驗",  # 2026-04-17 新增：Ragic 實際資料確認「已辦驗」為完成狀態（驗收欄=結案）
}
# 注意：以下視為未完成（程式用 not in COMPLETED_STATUSES 判定）
# "待維修", "處理中", "待驗收", "待協調", "待排除", "未處理", "待辦驗", "委外處理"

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
    "建築": "建築",
    "結構": "建築",
    "外牆": "建築",
    "玻璃": "建築",
    "門窗": "建築",
    "電梯": "建築",
    "手扶梯": "建築",
    "招牌": "建築",
    # 衛廁
    "衛廁": "衛廁",
    "廁所": "衛廁",
    "馬桶": "衛廁",
    "洗手": "衛廁",
    "洗手槽": "衛廁",
    "烘手機": "衛廁",
    "哺乳": "衛廁",
    # 消防
    "消防": "消防",
    "瓦斯": "消防",
    "偵煙": "消防",
    "灑水": "消防",
    "鐵捲門": "消防",
    "安全門": "消防",
    "緊急": "消防",
    # 空調
    "空調": "空調",
    "冷氣": "空調",
    "冷卻": "空調",
    "送風": "空調",
    "補風": "空調",
    "導流": "空調",
    "分離式": "空調",
    # 機電
    "機電": "機電",
    "機房": "機電",
    "發電機": "機電",
    "配電": "機電",
    # 給排水
    "給排水": "給排水",
    "漏水": "給排水",
    "水塔": "給排水",
    "污水": "給排水",
    "排水": "給排水",
    "給水": "給排水",
    # 排煙
    "排煙": "排煙",
    "靜電機": "排煙",
    "水洗機": "排煙",
    "截油槽": "排煙",
    "排煙管": "排煙",
    # 監控
    "監控": "監控",
    "cctv": "監控",
    "攝影": "監控",
    "監視": "監控",
    # 弱電
    "弱電": "弱電",
    "交換機": "弱電",
    "電話": "弱電",
    "網路": "弱電",
    # 照明
    "照明": "照明",
    "燈": "照明",
    "燈具": "照明",
    "路燈": "照明",
    # 停車
    "停車": "停車",
    "車牌": "停車",
    "繳費機": "停車",
    "柵欄": "停車",
    # 其他
    "人流": "其他",
    "入金機": "其他",
    # 專櫃
    "專櫃": "專櫃",
    "租戶": "專櫃",
    "承租": "專櫃",
    # 公區
    "公區": "公區",
    "公共": "公區",
    "lobby": "公區",
    "大廳": "公區",
    "廣場": "公區",
    "梯廳": "公區",
    "接待": "公區",
    "露台": "公區",
    # 後勤空間
    "後勤": "後勤空間",
    "辦公室": "後勤空間",
    "儲藏": "後勤空間",
    "員工餐": "後勤空間",
}

# 類型顯示順序
REPAIR_TYPE_ORDER = [
    "建築",
    "衛廁",
    "消防",
    "空調",
    "機電",
    "給排水",
    "排煙",
    "監控",
    "弱電",
    "照明",
    "停車",
    "其他",
    "專櫃",
    "凍&藏類設備",
    "內裝",
    "廚房&吧台設備",
    "會議設備",
    "瓦斯類設備",
    "公區",
    "後勤空間",
]

# 各類型的「MD內容」說明文字（依規格書 Markdown 表格）
REPAIR_TYPE_EXAMPLES: dict[str, str] = {
    "建築":       "連續壁 / 外觀玻璃 / 外觀門窗 / 電梯 / 手扶梯 / 招牌 / 植栽",
    "衛廁":       "馬桶 / 洗手槽 / 烘手機 / 哺給乳室 / 衛生紙架 / 淋浴間 / 浴簾 / 吹風機",
    "消防":       "偵煙感知器 / 灑水頭 / 鐵捲門 / 安全門 / 緊急廣播系統 / 煙霧偵測器 / R型受信總機 / 消防圖控 / 緊急消防加壓送水泵",
    "空調":       "主機 / 送風機 / 冷卻水塔 / 補風機 / 分離式冷氣 / 導流風機",
    "機電":       "機房 / 緊急發電機 / 不斷電系統 / 鍋爐",
    "給排水":     "漏水 / 水塔 / 污水處理 / 排水系統 / 截油槽",
    "排煙":       "靜電機 / 水洗機 / 截油槽 / 排煙管 / 排風扇",
    "監控":       "CCTV / 監控主機",
    "弱電":       "交換機 / 電話 / 網路 / 插座",
    "照明":       "建築外觀 / 燈具",
    "停車":       "車牌辨識 / 自動繳費機 / 柵欄機",
    "其他":       "人流計數器 / 入金機",
    "專櫃":       "",
    "凍&藏類設備": "冰箱（冷凍 & 藏）/ 凍庫 / 飲料機 / 製冰機",
    "內裝":       "天花板 / 牆壁 / 地板 / 門 / 窗簾 / 遮光簾 / 紗簾 / 家具 / 櫃子 / 地毯 / 保險箱",
    "廚房&吧台設備": "蒸烤爐 / 洗碗機 / 封口機 / 洗杯機 / 層架 / 捕蚊燈 / 熱水壺 / 咖啡機",
    "會議設備":   "宴會顯示器 / 投影機 / 電視 / 影音設備",
    "瓦斯類設備": "天然氣緊急遮斷系統 / 熱盤櫃 / 單口爐 / 雙口爐",
    "公區":       "電扶梯、商場、停車場 / 機廳 / 廚場、飯店、LOBBY / 4F接待區 / 4F餐台 / 各層梯廳",
    "後勤空間":   "辦公室 / 儲藏室 / 員工餐區 / 更衣室",
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


# ── 1-C. 客房類別欄位對應 ─────────────────────────────────────────────────────
ROOM_REPAIR_CATEGORIES = [
    "客房房門",
    "客房消防",
    "客房設備",
    "客房傢俱",
    "客房燈",
    "客房牆",
    "面盆/台面",
    "浴廁",
    "浴間",
    "天地壁",
    "配電盤",
    "環境",
]

# 客房判定關鍵字（出現在發生樓層或標題）
ROOM_FLOOR_KEYWORDS = [
    "5f",
    "6f",
    "7f",
    "8f",
    "9f",
    "10f",
    "5樓",
    "6樓",
    "7樓",
    "8樓",
    "9樓",
    "10樓",
    "客房",
]


# ── 1-D. 案件大小型分類邏輯（可後續改為依「核可層級」判斷）──────────────────
def is_large_repair(case: "RepairCase") -> bool:
    """
    判斷是否為中大型報修。
    初版邏輯：total_fee > 0 視為中大型，否則視為小型。
    後續可改此函式，畫面不需修改。
    """
    return case.total_fee > 10000


# ═════════════════════════════════════════════════════════════════════════════
# 2. Ragic 欄位名稱常數（命名依實際 Ragic 回傳中文 key）
# ─────────────────────────────────────────────────────────────────────────────
# ⚠️  若 Ragic 回傳的欄位名稱與下方不符，只需修改這裡，不需改業務邏輯。
# ⚠️  可用 /api/v1/luqun-repair/raw-fields 確認實際 key 名稱。
# ═════════════════════════════════════════════════════════════════════════════

# 主要欄位
RK_CASE_NO = "報修編號"  # 報修編號
RK_TITLE = "標題"  # 標題（同「報修名稱」）
RK_REPORTER = "報修人姓名"  # 報修人姓名
RK_REPAIR_TYPE = "報修類型"  # 報修類型
RK_FLOOR = "發生樓層"  # 發生樓層
RK_OCCURRED_AT = "發生時間"  # 發生時間（日期）
RK_RESPONSIBLE = "負責單位"  # 負責單位（Ragic 實際欄位：處理工務，優先讀此）
RK_WORK_HOURS = "花費工時"   # 工時主欄位（HR）；fallback：工務處理天數（天 ×24）
RK_STATUS = "處理狀況"  # 處理狀況
RK_OUTSOURCE_FEE = "委外費用"  # 委外費用
RK_MAINTENANCE_FEE = "維修費用"  # 維修費用
RK_ACCEPTOR = "驗收者"  # 驗收者
RK_ACCEPT_STATUS = "驗收"  # 驗收
RK_CLOSER = "結案人"  # 結案人
RK_DEDUCTION_ITEM = "扣款事項"  # 扣款事項
RK_DEDUCTION_FEE = "扣款費用"  # 扣款費用
RK_DEDUCTION_COUNTER = "扣款專櫃"  # 扣款專櫃（存放專櫃名稱，非金額；"多櫃"時看管理單位回應）
RK_MGMT_RESPONSE    = "管理單位回應"  # 管理單位回應（多櫃時包含各專櫃名稱）
RK_FINANCE_NOTE     = "財務備註"  # 財務備註（多櫃明細：店名+金額）
# 結案時間（若 Ragic 無此欄位，fallback 到「驗收日期」或「結案日期」）
RK_COMPLETED_AT = "結案時間"  # 結案時間（優先）
RK_CLOSE_DATE = "結案日期"  # 結案日期（備用）
RK_ACCEPT_DATE = "驗收日期"  # 驗收日期（再備用）

# 別名對應（Ragic 欄位名可能有多種寫法）
RK_ALIASES: dict[str, list[str]] = {
    RK_CASE_NO: ["報修編號", "編號", "案件編號"],
    RK_TITLE: ["標題", "報修名稱", "名稱"],
    RK_REPORTER: ["報修同仁", "報修人姓名", "報修人", "申報人"],  # 實測：報修同仁
    RK_REPAIR_TYPE: ["報修類型", "類型", "類別"],
    RK_FLOOR: ["發生樓層", "樓層", "位置"],
    RK_OCCURRED_AT: ["報修日期", "發生時間", "實際報修時間", "報修時間", "申報時間", "建立時間"],  # 報修日期優先，發生時間備用
    RK_RESPONSIBLE: ["處理工務", "負責單位", "負責人", "承辦單位", "交辦主管"],
    RK_WORK_HOURS: ["花費工時", "工時", "預估工時"],  # 主欄位；fallback 工務處理天數在 __init__ 手動處理
    RK_STATUS: ["處理狀況", "問題狀態", "狀態", "進度"],  # 實測：問題狀態/狀態
    RK_OUTSOURCE_FEE: ["委外費用", "外包費用"],
    RK_MAINTENANCE_FEE: ["維修費用", "費用"],
    RK_ACCEPTOR: ["驗收者", "驗收人"],
    RK_ACCEPT_STATUS: ["驗收回應", "驗收", "驗收結果", "驗收狀態"],  # 實測：驗收回應
    RK_CLOSER: ["結案人", "結案者"],
    RK_DEDUCTION_ITEM: ["扣款事項"],
    RK_DEDUCTION_FEE: ["扣款費用"],
    RK_DEDUCTION_COUNTER: ["扣款專櫃"],
    RK_MGMT_RESPONSE:    ["管理單位回應", "管理回應"],
    RK_FINANCE_NOTE:     ["財務備註", "備註"],
    RK_COMPLETED_AT: ["完工時間", "結案時間", "完成時間"],  # 實測：完工時間
    RK_CLOSE_DATE: ["結案日期", "完成日期"],
    RK_ACCEPT_DATE: ["驗收時間", "前端驗收時間", "驗收日期"],  # 實測：驗收時間
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
    """
    任意值轉字串，dict 取 value/label，list 用逗號連接。
    ⚠️ 不可用 `v.get("value") or ...`，因為 0 / 0.0 / False 是 falsy，
       會被誤判為「無值」。改用 `is not None` 判斷。
    """
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(_str(x) for x in v)
    if isinstance(v, dict):
        # 優先取 "value" key（即使值為 0 也要保留）
        if "value" in v and v["value"] is not None:
            return _str(v["value"])
        if "label" in v and v["label"] is not None:
            return _str(v["label"])
        return ""
    return str(v).strip()


_RAGIC_HTML_TAGS = re.compile(
    r'\[(/?)('
    r'br|p|b|i|u|s|em|strong|span|div|table|thead|tbody|tfoot|tr|th|td|ul|ol|li|a|img|hr'
    r')(\s[^\]]*)?(/?)\]',
    re.IGNORECASE,
)

def _ragic_html(text: str) -> str:
    """
    Ragic 將 HTML tag 以方括號儲存（如 [br]、[table]、[/td]），
    此函式將其還原為正常的 HTML 角括號格式供前端 dangerouslySetInnerHTML 渲染。
    """
    if not text:
        return text
    def _replace(m: re.Match) -> str:
        slash  = m.group(1)   # "/" or ""
        tag    = m.group(2)
        attrs  = m.group(3) or ""
        self_c = m.group(4)   # "/" or ""
        return f"<{slash}{tag}{attrs}{self_c}>"
    return _RAGIC_HTML_TAGS.sub(_replace, text)


def _float(v: Any) -> float:
    """
    字串/數字轉 float，失敗回傳 0.0。
    可處理 Ragic 常見格式：
      - 純數字：440509
      - 千分位：440,509 / 440，509
      - 貨幣前綴：$440,509 / NT$440,509 / TWD 440,509
      - 貨幣後綴：440,509元 / 440,509元整
      - 空 list/dict（欄位存在但無值）：[] / {}
    策略：用 regex 萃取第一段合法數字（含可選負號），再去除千分位符號。
    """
    try:
        s = _str(v)  # list/dict → ""，數字 → str(n)
        if not s:
            return 0.0
        # 萃取第一個合法數字段（支援負號、千分位、小數點）
        match = re.search(r"-?\d[\d,，.]*", s)
        if not match:
            return 0.0
        cleaned = re.sub(r"[,，]", "", match.group())
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def _parse_datetime(v: Any) -> Optional[datetime]:
    """解析各種日期格式，失敗回傳 None"""
    s = _str(v)
    if not s:
        return None
    formats = [
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
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
    logger.debug(f"[LuqunRepair] 無法解析日期: {s!r}")
    return None


def _parse_room_no(floor: str, title: str) -> tuple[str, str]:
    """
    從發生樓層或標題中解析「房號」與「樓層」。
    回傳 (room_no, floor_normalized)

    房號規則：3~4 位數字（e.g. 501, 1023）
    客房樓層：5F~10F
    """
    # 先嘗試從 floor 欄位解析
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
        "客房房門": ["房門", "門鎖", "門縫", "門框"],
        "客房消防": ["消防", "偵煙", "灑水", "火警"],
        "客房設備": ["設備", "電視", "冰箱", "電話", "保險箱", "電熱水器"],
        "客房傢俱": ["傢俱", "家具", "床", "椅", "桌", "衣櫃", "沙發"],
        "客房燈": ["燈", "電源", "插座", "開關"],
        "客房牆": ["牆", "壁紙", "油漆", "牆面"],
        "面盆/台面": ["面盆", "台面", "水龍頭", "鏡面"],
        "浴廁": ["浴廁", "馬桶", "洗手", "廁所"],
        "浴間": ["浴間", "浴缸", "淋浴", "蓮蓬頭"],
        "天地壁": ["天花板", "地板", "地磚", "天地壁"],
        "配電盤": ["配電盤", "電箱", "斷路器"],
        "環境": ["異味", "噪音", "蟲", "環境"],
    }
    for cat, keywords in category_keywords.items():
        for kw in keywords:
            if kw in combined:
                return cat
    return "客房設備"  # default fallback


# ═════════════════════════════════════════════════════════════════════════════
# 3-B. 扣款專櫃名稱解析輔助
# ─────────────────────────────────────────────────────────────────────────────

def _parse_counter_stores(counter_name: str, finance_note: str = "") -> list[str]:
    """
    解析扣款專櫃名稱，回傳專櫃名稱 list。
    - 一般單櫃：["牪肉舖"]
    - "多櫃"：從財務備註解析（格式：店名 金額_x000D_\\n店名 金額...）
    """
    import re
    name = counter_name.strip()
    if not name:
        return []
    if name != "多櫃":
        return [name]
    # 多櫃：從財務備註解析（_x000D_\n 為換行符）
    src = finance_note.strip()
    if not src:
        return ["多櫃"]
    stores: list[str] = []
    # 清除 Excel 換行符 _x000D_ 後按 \n 分行
    cleaned = re.sub(r"_x000D_", "", src)
    for line in re.split(r"[\n\r]+", cleaned):
        line = line.strip()
        if not line:
            continue
        # 格式 "店名 數字" → 去掉結尾數字/空白，取店名部分
        store = re.sub(r"\s+\d[\d,，.]+\s*$", "", line).strip()
        if store and len(store) >= 2:
            stores.append(store)
    return stores if stores else ["多櫃"]


# 4. RepairCase 資料類別（標準化後的案件）
# ═════════════════════════════════════════════════════════════════════════════


class RepairCase:
    """標準化後的單筆報修案件"""

    __slots__ = (
        "ragic_id",
        "case_no",
        "title",
        "reporter_name",
        "repair_type",
        "floor",
        "occurred_at",
        "responsible_unit",
        "work_hours",
        "status",
        "outsource_fee",
        "maintenance_fee",
        "acceptor",
        "accept_status",
        "closer",
        "deduction_item",
        "deduction_fee",
        "deduction_counter",      # 保持為 0（欄位實際存的是名稱）
        "deduction_counter_name", # 扣款專櫃名稱（字串）
        "counter_stores",         # 解析後的專櫃名稱列表
        "mgmt_response",          # 管理單位回應原文
        "finance_note",
        "total_fee",
        "is_completed_flag",
        "is_excluded_flag",
        "completed_at",
        "close_days",
        "year",
        "month",
        "occ_year",
        "occ_month",
        "is_room_case",
        "room_no",
        "floor_normalized",
        "room_category",
        "images",
        "_raw",
    )

    def __init__(self, ragic_id: str, raw: dict):
        self._raw = raw
        self.ragic_id = ragic_id

        # 基本欄位
        self.case_no = _str(_get_field(raw, RK_CASE_NO))
        self.title = _str(_get_field(raw, RK_TITLE))
        self.reporter_name = _str(_get_field(raw, RK_REPORTER))
        self.floor = _str(_get_field(raw, RK_FLOOR))
        self.occurred_at = _parse_datetime(_get_field(raw, RK_OCCURRED_AT))
        self.responsible_unit = _str(_get_field(raw, RK_RESPONSIBLE))
        # 工時：① 花費工時（HR，直接使用）→ ② 工務處理天數（天 ×24，上限 365 天防誤植年份）
        _work_hrs = _float(_get_field(raw, RK_WORK_HOURS))  # 花費工時
        if _work_hrs <= 0:
            _work_hrs = safe_work_days_to_hours(raw.get("工務處理天數", ""))
        self.work_hours = _work_hrs
        self.status = _str(_get_field(raw, RK_STATUS))
        self.outsource_fee = _float(_get_field(raw, RK_OUTSOURCE_FEE))
        self.maintenance_fee = _float(_get_field(raw, RK_MAINTENANCE_FEE))
        self.acceptor = _str(_get_field(raw, RK_ACCEPTOR))
        self.accept_status = _str(_get_field(raw, RK_ACCEPT_STATUS))
        self.closer = _str(_get_field(raw, RK_CLOSER))
        self.deduction_item = _str(_get_field(raw, RK_DEDUCTION_ITEM))
        self.deduction_fee = _float(_get_field(raw, RK_DEDUCTION_FEE))
        # 扣款專櫃：Ragic API 回傳 list（如 ["牪肉舖"]），不是字串
        counter_val = _get_field(raw, RK_DEDUCTION_COUNTER)
        if isinstance(counter_val, list):
            counter_raw = "、".join(str(v).strip() for v in counter_val if v)
        else:
            counter_raw = _str(counter_val)
        self.mgmt_response     = _ragic_html(_str(_get_field(raw, RK_MGMT_RESPONSE)))
        self.finance_note      = _str(_get_field(raw, RK_FINANCE_NOTE))
        self.deduction_counter_name = counter_raw
        # 多櫃 → 解析財務備註；一般 → 直接用店名
        self.counter_stores    = _parse_counter_stores(counter_raw, self.finance_note)
        self.deduction_counter = 0.0  # 維持介面相容，實際金額在 deduction_fee

        # 報修類型標準化
        raw_type = _str(_get_field(raw, RK_REPAIR_TYPE))
        self.repair_type = normalize_repair_type(raw_type, self.title, self.floor)

        # 衍生欄位
        self.total_fee = self.outsource_fee + self.maintenance_fee
        self.is_excluded_flag  = is_excluded(self.status)  # 取消等不計入統計

        # 結案時間：優先用 RK_COMPLETED_AT，再 RK_CLOSE_DATE，再 RK_ACCEPT_DATE
        completed_raw = (
            _get_field(raw, RK_COMPLETED_AT)
            or _get_field(raw, RK_CLOSE_DATE)
            or _get_field(raw, RK_ACCEPT_DATE)
        )
        self.completed_at = _parse_datetime(completed_raw)

        # 完工判定：只要有「完工時間」即視為已完工，無論處理狀況
        # 備用：狀態字串本身也可判定完工（如已辦驗、結案等）
        self.is_completed_flag = (self.completed_at is not None) or is_completed(self.status)

        # 結案天數
        if self.is_completed_flag and self.occurred_at and self.completed_at:
            delta = self.completed_at - self.occurred_at
            self.close_days = round(delta.total_seconds() / 86400, 2)
        else:
            self.close_days = None

        # 統計月份：結案案件以「結案月份」為準，未結案以「報修月份」為準
        if self.is_completed_flag and self.completed_at:
            self.year = self.completed_at.year
            self.month = self.completed_at.month
        elif self.occurred_at:
            self.year = self.occurred_at.year
            self.month = self.occurred_at.month
        else:
            self.year = None
            self.month = None

        # 報修月份（4.1 報修統計專用，永遠以 occurred_at 為準）
        if self.occurred_at:
            self.occ_year = self.occurred_at.year
            self.occ_month = self.occurred_at.month
        else:
            self.occ_year = None
            self.occ_month = None

        # 客房相關
        self.is_room_case = _is_room_case(self.floor, self.title, raw_type)
        self.room_no, self.floor_normalized = _parse_room_no(self.floor, self.title)
        self.room_category = (
            _classify_room_category(raw_type, self.title) if self.is_room_case else ""
        )

        # 圖片（Ragic 「維修照上傳」附件欄位，用 file.jsp API 取實際檔案）
        self.images = parse_images(
            raw.get(IMAGE_FIELD_LUQUN) or raw.get("上傳圖片") or raw.get("維修照"),
            server=settings.RAGIC_LUQUN_REPAIR_SERVER_URL,
            account=settings.RAGIC_LUQUN_REPAIR_ACCOUNT,
        )

    def to_dict(self) -> dict:
        """轉換為 API 回傳用 dict"""
        return {
            "ragic_id": self.ragic_id,
            "case_no": self.case_no,
            "title": self.title,
            "reporter_name": self.reporter_name,
            "repair_type": self.repair_type,
            "floor": self.floor,
            "floor_normalized": self.floor_normalized,
            "occurred_at": (
                self.occurred_at.strftime("%Y/%m/%d %H:%M") if self.occurred_at else ""
            ),
            "responsible_unit": self.responsible_unit,
            "work_hours": self.work_hours,
            "status": self.status,
            "outsource_fee": self.outsource_fee,
            "maintenance_fee": self.maintenance_fee,
            "total_fee": self.total_fee,
            "acceptor": self.acceptor,
            "accept_status": self.accept_status,
            "closer": self.closer,
            "deduction_item": self.deduction_item,
            "deduction_fee": self.deduction_fee,
            "deduction_counter":      self.deduction_counter,       # 保持 0，介面相容
            "deduction_counter_name": self.deduction_counter_name,   # 扣款專櫃名稱
            "counter_stores":         self.counter_stores,           # 解析後的專櫃列表
            "mgmt_response":          self.mgmt_response,            # 管理單位回應
            "finance_note":           self.finance_note,
            "is_completed": self.is_completed_flag,
            "is_excluded":  self.is_excluded_flag,
            "completed_at": (
                self.completed_at.strftime("%Y/%m/%d") if self.completed_at else ""
            ),
            "close_days": self.close_days,
            "pending_days": (
                round((datetime.now() - self.occurred_at).total_seconds() / 86400)
                if (self.completed_at is None and self.occurred_at)
                else None
            ),
            "year": self.year,
            "month": self.month,
            "is_room_case": self.is_room_case,
            "room_no": self.room_no,
            "room_category": self.room_category,
            "images": self.images,
        }


# ═════════════════════════════════════════════════════════════════════════════
# 5. Ragic 資料抓取
# ═════════════════════════════════════════════════════════════════════════════


def _get_adapter() -> RagicAdapter:
    return RagicAdapter(
        sheet_path=settings.RAGIC_LUQUN_REPAIR_PATH,
        api_key=settings.RAGIC_API_KEY,
        server_url=settings.RAGIC_LUQUN_REPAIR_SERVER_URL,
        account=settings.RAGIC_LUQUN_REPAIR_ACCOUNT,
    )


_CACHE_KEY = "luqun_repair"

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
    )

    cases: list[RepairCase] = []
    for record in records:
        rid = record.get("_ragic_id", "")
        try:
            cases.append(RepairCase(ragic_id=rid, raw=record))
        except Exception as exc:
            logger.warning(f"[LuqunRepair] 案件 {rid} 清洗失敗，跳過: {exc}")

    logger.info(f"[LuqunRepair] 共載入 {len(cases)} 筆案件")
    return cases


def invalidate_cache() -> None:
    """清除樂群報修 cache（sync 後呼叫）"""
    invalidate(_CACHE_KEY)


async def fetch_raw_fields() -> dict:
    """取得第一筆資料的 key 列表（供 debug / 欄位確認用）"""
    adapter = _get_adapter()
    try:
        raw_data = await adapter.fetch_all(limit=2)
        for rid, row in raw_data.items():
            return {"ragic_id": rid, "fields": list(row.keys()), "sample": row}
    except Exception as exc:
        logger.error(f"[LuqunRepair] fetch_raw_fields 失敗: {exc}")
    return {}


# ═════════════════════════════════════════════════════════════════════════════
# 6. 過濾輔助
# ═════════════════════════════════════════════════════════════════════════════


def _stat_year(c) -> Optional[int]:
    """統計年份：有完工時間 → 完工年；否則 → 儲存的 year（報修年）。
    直接讀 completed_at 避免 ORM 物件因舊資料導致 year 欄位不正確。"""
    at = getattr(c, 'completed_at', None)
    if at is not None:
        return at.year
    return getattr(c, 'year', None)


def _stat_month(c) -> Optional[int]:
    """統計月份：有完工時間 → 完工月；否則 → 儲存的 month（報修月）。"""
    at = getattr(c, 'completed_at', None)
    if at is not None:
        return at.month
    return getattr(c, 'month', None)


def filter_cases(
    cases: list[RepairCase],
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> list[RepairCase]:
    """依統計年/月過濾案件。
    統計月份直接從 completed_at 計算（不依賴儲存的 year/month 欄位），
    確保即使 SQLite 資料尚未重新同步，也能正確篩選跨月完工案件。"""
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
        c
        for c in cases
        if c.year is not None
        and (c.year < year or (c.year == year and c.month <= month))
    ]


def get_years(cases: list[RepairCase]) -> list[int]:
    """取得資料中所有年份（排序後）"""
    years = sorted({c.year for c in cases if c.year is not None}, reverse=True)
    return years if years else [datetime.now().year]


# ═════════════════════════════════════════════════════════════════════════════
# 7. Dashboard 統計
# ═════════════════════════════════════════════════════════════════════════════

def _db_completed_by(c: RepairCase, y: int, m: int) -> bool:
    """completed_at 是否在 y/m 月底（含）之前（供 compute_dashboard 使用）"""
    if c.completed_at is None:
        return False
    return c.completed_at.year < y or (c.completed_at.year == y and c.completed_at.month <= m)


def _db_completed_in(c: RepairCase, y: int, m: int) -> bool:
    """completed_at 是否恰好落在 y/m 月（供 compute_dashboard 使用）"""
    if c.completed_at is None:
        return False
    return c.completed_at.year == y and c.completed_at.month == m


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

    # ── 本月相關案件口徑：① 上月累計未完成 + ⑤ 本月報修 ──────────────────────
    # 與 4.1 報修統計 Tab 口徑對齊；全年檢視（month=0）沿用舊邏輯
    if month:
        _prev_y, _prev_m = _month_offset(year, month, -1)
        _cases_up_to_prev = [
            c for c in all_cases
            if c.occ_year is not None
            and (c.occ_year < _prev_y or (c.occ_year == _prev_y and c.occ_month <= _prev_m))
        ]
        _prev_uncompleted = [c for c in _cases_up_to_prev if not _db_completed_by(c, _prev_y, _prev_m)]
        _this_month_new   = [c for c in all_cases if c.occ_year == year and c.occ_month == month]
        this_month_cases  = _prev_uncompleted + _this_month_new
    else:
        this_month_cases = filter_cases(all_cases, year, None)

    # ── KPI ──────────────────────────────────────────────────────────────────
    total = len(this_month_cases)
    # 月份檢視：完成 = 本月有 completed_at；全年：is_completed_flag
    if month:
        completed = sum(1 for c in this_month_cases if _db_completed_in(c, year, month))
    else:
        completed = sum(1 for c in this_month_cases if c.is_completed_flag)
    uncompleted = total - completed
    room_cases = [c for c in this_month_cases if c.is_room_case]

    close_days_list = [
        c.close_days
        for c in this_month_cases
        if c.is_completed_flag and c.close_days is not None
    ]
    avg_close_days = (
        round(sum(close_days_list) / len(close_days_list), 2)
        if close_days_list
        else None
    )

    total_fee = sum(c.total_fee for c in this_month_cases)
    total_deduction_fee = sum(c.deduction_fee for c in this_month_cases)
    total_deduction_counter = sum(c.deduction_counter for c in this_month_cases)  # 保持 0
    # 本月有扣款專櫃的案件金額合計（deduction_counter_name 非空）
    total_counter_fee = round(sum(
        c.deduction_fee for c in this_month_cases
        if getattr(c, 'deduction_counter_name', '')
    ), 2)
    # 本月有扣款的專櫃：計算唯一專櫃家數（含多櫃解析）
    # getattr 保護：ORM 物件在舊 sync 前可能沒有 deduction_counter_name
    counter_cases = [c for c in this_month_cases
                     if c.deduction_fee > 0 and getattr(c, 'deduction_counter_name', '')]
    _counter_set: set[str] = set()
    for _c in counter_cases:
        _stores = getattr(_c, 'counter_stores', None) or [getattr(_c, 'deduction_counter_name', '')]
        for _s in _stores:
            if _s:
                _counter_set.add(_s)
    total_counter_stores = len(_counter_set)
    counter_store_names  = sorted(_counter_set)
    # 工時統計：直接加總「花費工時」（hr），單位一致，不混用結案天數
    # 花費工時 ≈ 工務處理天數 × 24，÷24 即可換算為天數
    total_work_hours = round(sum(c.work_hours for c in this_month_cases), 2)

    # ── 近 12 個月趨勢 ────────────────────────────────────────────────────────
    trend_12m = []
    for m_offset in range(11, -1, -1):
        y, m = _month_offset(year, month if month else datetime.now().month, -m_offset)
        # 近 12 月趨勢同樣以「報修月份」為準
        mc = [c for c in all_cases if c.occ_year == y and c.occ_month == m]
        trend_12m.append(
            {
                "label": f"{y}/{m:02d}",
                "year": y,
                "month": m,
                "total": len(mc),
                "completed": sum(1 for c in mc if c.is_completed_flag),
            }
        )

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
    # 範圍：all_cases 中 completed_at 為空的案件（不限月份，找出積壓最久的）
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

    # ── 當月費用（口徑與「金額統計」Tab 一致：c.year/c.month，結案以結案月份為準）
    fee_month_cases = filter_cases(all_cases, year, month if month else None)
    month_outsource_fee     = round(sum(c.outsource_fee     for c in fee_month_cases), 2)
    month_maintenance_fee   = round(sum(c.maintenance_fee   for c in fee_month_cases), 2)
    month_deduction_fee     = round(sum(c.deduction_fee     for c in fee_month_cases), 2)
    month_deduction_counter = round(sum(c.deduction_counter for c in fee_month_cases), 2)
    month_total_fee         = round(month_outsource_fee + month_maintenance_fee + month_deduction_fee + month_deduction_counter, 2)

    # ── 年度費用合計（全年，不限月份）─────────────────────────────────────────
    year_cases = filter_cases(all_cases, year, None)  # year only, no month filter

    annual_outsource = round(sum(c.outsource_fee for c in year_cases), 2)
    annual_maintenance = round(sum(c.maintenance_fee for c in year_cases), 2)
    annual_fee = round(annual_outsource + annual_maintenance, 2)
    annual_deduction_fee = round(sum(c.deduction_fee for c in year_cases), 2)
    annual_deduction_counter = round(sum(c.deduction_counter for c in year_cases), 2)

    # 年度費用明細 — 委外+維修 Top20（點擊卡片時顯示）
    annual_fee_records = sorted(
        [c for c in year_cases if c.total_fee > 0],
        key=lambda x: x.total_fee,
        reverse=True,
    )
    annual_fee_detail = [
        {
            **c.to_dict(),
            "outsource_fee": c.outsource_fee,
            "maintenance_fee": c.maintenance_fee,
        }
        for c in annual_fee_records[:20]
    ]

    # 年度扣款費用明細 Top20
    annual_deduction_records = sorted(
        [c for c in year_cases if c.deduction_fee > 0],
        key=lambda x: x.deduction_fee,
        reverse=True,
    )
    annual_deduction_detail = [c.to_dict() for c in annual_deduction_records[:20]]

    # 年度扣款專櫃明細（有扣款費用且有專櫃名稱）Top30
    annual_counter_records = sorted(
        [c for c in year_cases if c.deduction_fee > 0 and getattr(c, 'deduction_counter_name', '')],
        key=lambda x: x.deduction_fee,
        reverse=True,
    )
    annual_counter_detail = [c.to_dict() for c in annual_counter_records[:30]]

    # 本月扣款專櫃明細（點擊卡片時用）
    counter_cases_sorted = sorted(counter_cases, key=lambda x: x.deduction_fee, reverse=True)
    # 排序也要 getattr 安全

    # 年度有扣款的唯一專櫃集合
    _annual_counter_set: set[str] = set()
    for _c in annual_counter_records:
        _stores2 = getattr(_c, 'counter_stores', None) or [getattr(_c, 'deduction_counter_name', '')]
        for _s in _stores2:
            if _s:
                _annual_counter_set.add(_s)
    annual_deduction_counter   = len(_annual_counter_set)
    annual_counter_fee         = round(sum(c.deduction_fee for c in annual_counter_records), 2)
    annual_counter_store_names = sorted(_annual_counter_set)

    # KPI 明細（點擊卡片時用）
    if month:
        completed_cases   = [c for c in this_month_cases if _db_completed_in(c, year, month)]
        uncompleted_cases = [c for c in this_month_cases if not _db_completed_in(c, year, month)]
        close_days_cases  = [c for c in completed_cases if c.close_days is not None]
    else:
        completed_cases   = [c for c in this_month_cases if c.is_completed_flag]
        uncompleted_cases = [c for c in this_month_cases if not c.is_completed_flag]
        close_days_cases  = [c for c in this_month_cases if c.is_completed_flag and c.close_days is not None]
    work_hours_cases = sorted(
        [c for c in this_month_cases if c.work_hours > 0],
        key=lambda x: x.work_hours, reverse=True
    )

    return {
        "kpi": {
            "total": total,
            "completed": completed,
            "uncompleted": uncompleted,
            "avg_close_days": avg_close_days,
            "total_fee": total_fee,
            "total_deduction_fee": total_deduction_fee,
            "total_deduction_counter": total_deduction_counter,  # 保持 0，介面相容
            "total_counter_stores":    total_counter_stores,    # 本月有扣款的專櫃家數
            "total_counter_fee":       total_counter_fee,       # 本月扣款專櫃費用合計
            "counter_store_names":     counter_store_names,     # 本月專櫃名稱列表
            "total_work_hours": total_work_hours,
            "room_cases": len(room_cases),
            # 當月費用（依年+月篩選，月份=0 時為全年合計）
            "month_outsource_fee":     month_outsource_fee,
            "month_maintenance_fee":   month_maintenance_fee,
            "month_deduction_fee":     month_deduction_fee,
            "month_deduction_counter": month_deduction_counter,
            "month_total_fee":         month_total_fee,
            # 年度費用（費用 KPI 卡片用此值，不受月份篩選影響）
            "annual_fee": annual_fee,
            "annual_outsource_fee": annual_outsource,
            "annual_maintenance_fee": annual_maintenance,
            "annual_deduction_fee": annual_deduction_fee,
            "annual_deduction_counter":    annual_deduction_counter,
            # 全年扣款專櫃（與委外/扣款費用卡片對齊，皆為全年口徑）
            "annual_counter_stores":       annual_deduction_counter,
            "annual_counter_fee":          annual_counter_fee,
            "annual_counter_store_names":  annual_counter_store_names,
        },
        # KPI 明細清單
        "kpi_total_detail":      [c.to_dict() for c in sorted(this_month_cases, key=lambda x: x.occurred_at or datetime.min, reverse=True)],
        "kpi_completed_detail":  [c.to_dict() for c in sorted(completed_cases, key=lambda x: x.completed_at or datetime.min, reverse=True)],
        "kpi_uncompleted_detail":[c.to_dict() for c in sorted(uncompleted_cases, key=lambda x: x.occurred_at or datetime.min)],
        "kpi_close_days_detail": [c.to_dict() for c in sorted(close_days_cases, key=lambda x: x.close_days or 0, reverse=True)],
        "kpi_room_detail":       [c.to_dict() for c in sorted(room_cases, key=lambda x: x.occurred_at or datetime.min, reverse=True)],
        "kpi_hours_detail":          [c.to_dict() for c in work_hours_cases],
        "kpi_counter_stores_detail": [c.to_dict() for c in counter_cases_sorted],
        "trend_12m": trend_12m,
        "type_dist": [{"type": k, "count": v} for k, v in type_dist.items()],
        "floor_dist": [
            {"floor": k, "count": v}
            for k, v in sorted(floor_dist.items(), key=lambda x: -x[1])
        ],
        "status_dist": [{"status": k, "count": v} for k, v in status_dist.items()],
        "top_uncompleted": top_uncompleted,
        "top_fee": top_fee,
        "top_hours": top_hours,
        # 年度費用明細（點擊 KPI 卡片時用）
        "annual_fee_detail": annual_fee_detail,
        "annual_deduction_detail": annual_deduction_detail,
        "annual_counter_detail": annual_counter_detail,
    }


def _month_offset(year: int, month: int, offset: int) -> tuple[int, int]:
    """計算月份偏移（offset 為正數往後、負數往前）"""
    total = (year * 12 + month - 1) + offset
    return total // 12, total % 12 + 1


# ═════════════════════════════════════════════════════════════════════════════
# 8. 金額統計
# ═════════════════════════════════════════════════════════════════════════════

FEE_KEYS = ["outsource_fee", "maintenance_fee", "deduction_fee", "deduction_counter"]
FEE_LABELS = {
    "outsource_fee": "委外費用",
    "maintenance_fee": "維修費用",
    "deduction_fee": "扣款費用",
    "deduction_counter": "扣款專櫃",
}


def compute_fee_stats(all_cases: list[RepairCase], year: int) -> dict:
    """
    金額統計：4 項費用 × 12 個月的交叉表。
    回傳 monthly[月份][fee_key] = 金額合計，以及各維度小計。
    同時回傳每個非零格子的明細案件清單（供點擊展開）。
    """
    # 排除「取消」等不計入統計的案件
    all_cases = [c for c in all_cases if not c.is_excluded_flag]
    monthly_totals: dict[int, dict[str, float]] = {}
    monthly_detail: dict[str, list[dict]] = {}  # key = "{month}_{fee_key}"

    for m in range(1, 13):
        mc = filter_cases(all_cases, year, m)
        monthly_totals[m] = {}
        for fk in FEE_KEYS:
            if fk == "deduction_counter":
                # 扣款專櫃：計算當月有扣款的唯一專櫃家數（整數，非金額）
                _m_stores: set[str] = set()
                for _c in mc:
                    if _c.deduction_fee > 0 and getattr(_c, 'deduction_counter_name', ''):
                        _sl = getattr(_c, 'counter_stores', None) or [getattr(_c, 'deduction_counter_name', '')]
                        for _s in _sl:
                            if _s:
                                _m_stores.add(_s)
                monthly_totals[m][fk] = len(_m_stores)
            else:
                monthly_totals[m][fk] = round(sum(getattr(c, fk) for c in mc), 2)

        # 明細：每個費用類型 × 月份，只取有值的案件
        for fk in FEE_KEYS:
            if fk == "deduction_counter":
                cases_with_fee = sorted(
                    [c for c in mc if getattr(c, 'deduction_counter_name', '') and c.deduction_fee > 0],
                    key=lambda c: c.deduction_fee, reverse=True,
                )
            else:
                cases_with_fee = sorted(
                    [c for c in mc if getattr(c, fk) > 0],
                    key=lambda c: getattr(c, fk), reverse=True,
                )
            if cases_with_fee:
                monthly_detail[f"{m}_{fk}"] = [c.to_dict() for c in cases_with_fee]

    # 全年唯一扣款專櫃家數（跨月去重，不能直接加總各月）
    _annual_fee_stores: set[str] = set()
    _year_cases_all = filter_cases(all_cases, year, None)
    for _c in _year_cases_all:
        if _c.deduction_fee > 0 and getattr(_c, 'deduction_counter_name', ''):
            _sl2 = getattr(_c, 'counter_stores', None) or [getattr(_c, 'deduction_counter_name', '')]
            for _s in _sl2:
                if _s:
                    _annual_fee_stores.add(_s)

    # 全年小計（各費用類型）
    _MONEY_KEYS = [fk for fk in FEE_KEYS if fk != "deduction_counter"]
    fee_totals = {
        fk: round(sum(monthly_totals[m][fk] for m in range(1, 13)), 2)
        for fk in _MONEY_KEYS
    }
    fee_totals["deduction_counter"] = len(_annual_fee_stores)  # 整數，全年唯一家數

    # 月份小計（僅加金額類，排除家數欄位 deduction_counter）
    month_totals = {
        m: round(sum(monthly_totals[m][fk] for fk in _MONEY_KEYS), 2) for m in range(1, 13)
    }
    grand_total = round(sum(fee_totals[fk] for fk in _MONEY_KEYS), 2)

    return {
        "year": year,
        "monthly_totals": monthly_totals,  # {month: {fee_key: amount}}
        "fee_totals": fee_totals,  # {fee_key: annual_total}
        "month_totals": month_totals,  # {month: total_of_all_fees}
        "grand_total": grand_total,
        "monthly_detail": monthly_detail,  # {"{m}_{fk}": [case, ...]}
        "fee_labels": FEE_LABELS,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 9. 4.1 報修統計
# ═════════════════════════════════════════════════════════════════════════════


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
    5. 本月報修項目完成數（完工日期落在本月）
    6. 本月未完成數
    7. 本月報修項目完成率

    ⚠️ 時間規則：
    - 「完成」的定義 = completed_at（完工日期）落在指定的年/月內
    - 不使用 is_completed_flag（當前狀態），避免跨月完工被錯誤計入報修月
    - 例：3月報修、4月完工 → 3月的⑤=0，4月的②才計入
    """
    # 排除「取消」等不計入統計的案件（明細總表仍完整保留）
    all_cases = [c for c in all_cases if not c.is_excluded_flag]

    # ── 輔助函式（定義在迴圈外，避免 closure 問題）────────────────────────────

    def _completed_by(c: RepairCase, y: int, m: int) -> bool:
        """completed_at 是否在 y/m 月底（含）之前"""
        if c.completed_at is None:
            return False
        return c.completed_at.year < y or (c.completed_at.year == y and c.completed_at.month <= m)

    def _completed_in(c: RepairCase, y: int, m: int) -> bool:
        """completed_at 是否恰好落在 y/m 月"""
        if c.completed_at is None:
            return False
        return c.completed_at.year == y and c.completed_at.month == m

    months_data = {}

    for month in range(1, 13):
        prev_y, prev_m = _month_offset(year, month, -1)

        # ── 截至上月底，以「報修月份」occ_year/occ_month 為準 ─────────────────
        cases_up_to_prev = [
            c for c in all_cases
            if c.occ_year is not None
            and (c.occ_year < prev_y or (c.occ_year == prev_y and c.occ_month <= prev_m))
        ]

        # ① 上月累計未完成：報修在上月底以前，且「完工日期」尚未落在上月底以前
        prev_uncompleted = [c for c in cases_up_to_prev if not _completed_by(c, prev_y, prev_m)]
        prev_uncompleted_count = len(prev_uncompleted)

        # ② 上月未完成，本月結案數：從①中，完工日期落在本月的案件
        closed_from_prev_cases = [c for c in prev_uncompleted if _completed_in(c, year, month)]
        closed_this_month_from_prev = len(closed_from_prev_cases)

        # ②b 上月累計完成數 = ① - ② = 上月累計未完成中，本月後仍未結案的案件
        prev_remaining_cases = [c for c in prev_uncompleted if not _completed_in(c, year, month)]
        prev_remaining_count = prev_uncompleted_count - closed_this_month_from_prev

        # ③ 累計完成率：報修在本月底以前，且完工日期也在本月底以前
        cases_up_to_this = [
            c for c in all_cases
            if c.occ_year is not None
            and (c.occ_year < year or (c.occ_year == year and c.occ_month <= month))
        ]
        cum_total = len(cases_up_to_this)
        cum_completed = sum(1 for c in cases_up_to_this if _completed_by(c, year, month))
        cum_rate = round(cum_completed / cum_total * 100, 1) if cum_total > 0 else None

        # ④ 本月報修項目數（以報修月份為準）
        this_month_cases = [
            c for c in all_cases if c.occ_year == year and c.occ_month == month
        ]
        this_total = len(this_month_cases)

        # ⑤ 本月報修項目完成數：報修在本月 且 完工日期也在本月
        this_completed_cases = [c for c in this_month_cases if _completed_in(c, year, month)]
        this_completed = len(this_completed_cases)

        # ⑥ 本月未完成數
        this_uncompleted_cases = [c for c in this_month_cases if not _completed_in(c, year, month)]
        this_uncompleted = len(this_uncompleted_cases)

        # ⑦ 本月完成率
        this_rate = round(this_completed / this_total * 100, 1) if this_total > 0 else None

        months_data[month] = {
            "month": month,
            "prev_uncompleted": prev_uncompleted_count,
            "closed_from_prev": closed_this_month_from_prev,
            "prev_remaining":   prev_remaining_count,
            "cum_completion_rate": cum_rate,
            "this_month_total": this_total,
            "this_month_completed": this_completed,
            "this_month_uncompleted": this_uncompleted,
            "this_month_completion_rate": this_rate,
            # 明細（點擊展開用）
            "prev_uncompleted_detail": [c.to_dict() for c in prev_uncompleted],
            "closed_from_prev_detail": [c.to_dict() for c in closed_from_prev_cases],
            "prev_remaining_detail":   [c.to_dict() for c in prev_remaining_cases],
            "this_month_total_detail":       [c.to_dict() for c in this_month_cases],
            "this_month_completed_detail":   [c.to_dict() for c in this_completed_cases],
            "this_month_uncompleted_detail": [c.to_dict() for c in this_uncompleted_cases],
        }

    return {"year": year, "months": months_data}


# ═════════════════════════════════════════════════════════════════════════════
# 9. 4.2 結案時間統計
# ═════════════════════════════════════════════════════════════════════════════


def compute_closing_time(
    all_cases: list[RepairCase],
    year: int,
    month: Optional[int] = None,
) -> dict:
    """
    4.2 結案時間統計（小型 vs 中大型）

    分類邏輯：is_large_repair() 可集中修改

    ⚠️ 時間規則：
    - 「結案」的定義 = completed_at（完工日期）落在指定的年/月內
    - 不使用 is_completed_flag（當前狀態），確保跨月完工正確歸屬
    - 例：3月報修、4月完工 → 歸屬於 4月 的結案統計
    """
    # 排除「取消」等不計入統計的案件
    all_cases = [c for c in all_cases if not c.is_excluded_flag]

    def _closed_in(c: RepairCase, y: int, m: Optional[int]) -> bool:
        """completed_at 是否落在指定年份（+月份）內"""
        if c.completed_at is None or c.close_days is None:
            return False
        if c.completed_at.year != y:
            return False
        if m is not None and c.completed_at.month != m:
            return False
        return True

    def stats_block(cases: list[RepairCase]) -> dict:
        count = len(cases)
        total_days = sum(c.close_days for c in cases)  # type: ignore[arg-type]
        avg_days = round(total_days / count, 2) if count > 0 else None
        return {
            "closed_count": count,
            "total_days": round(total_days, 2),
            "avg_days": avg_days,
            "cases": [c.to_dict() for c in sorted(cases, key=lambda x: x.close_days or 0, reverse=True)],
        }

    # 本月／本年已結案案件（以 completed_at 年月為準）
    closed = [c for c in all_cases if _closed_in(c, year, month)]
    small_cases = [c for c in closed if not is_large_repair(c)]
    large_cases = [c for c in closed if is_large_repair(c)]

    # 月份詳細（全年模式，每月各自以 completed_at 月份篩選）
    monthly = {}
    for m in range(1, 13):
        mc_closed = [c for c in all_cases if _closed_in(c, year, m)]
        mc_small = [c for c in mc_closed if not is_large_repair(c)]
        mc_large = [c for c in mc_closed if is_large_repair(c)]
        monthly[m] = {
            "small": stats_block(mc_small),
            "large": stats_block(mc_large),
        }

    return {
        "year": year,
        "month": month,
        "small": stats_block(small_cases),
        "large": stats_block(large_cases),
        "monthly": monthly,
        "classification_note": "小型=total_fee=0；中大型=total_fee>10000（is_large_repair）",
    }


# ═════════════════════════════════════════════════════════════════════════════
# 10. 4.3 報修類型統計
# ═════════════════════════════════════════════════════════════════════════════


def compute_type_stats(
    all_cases: list[RepairCase],
    year: int,
    month: Optional[int] = None,
) -> dict:
    """
    4.3 報修類型統計：依類型 × 月份 二維統計。
    """
    # 排除「取消」等不計入統計的案件
    all_cases = [c for c in all_cases if not c.is_excluded_flag]
    # 篩選本年案件
    year_cases = filter_cases(all_cases, year)
    focus_month = month  # 查詢聚焦月份（用於高亮）

    # type → month → [cases]
    type_monthly_cases: dict[str, dict[int, list[RepairCase]]] = {t: {} for t in REPAIR_TYPE_ORDER}
    type_monthly: dict[str, dict[int, int]] = {t: {} for t in REPAIR_TYPE_ORDER}

    for case in year_cases:
        if case.month is None:
            continue
        rt = case.repair_type
        if rt not in type_monthly:
            type_monthly[rt] = {}
            type_monthly_cases[rt] = {}
        type_monthly[rt][case.month] = type_monthly[rt].get(case.month, 0) + 1
        type_monthly_cases[rt].setdefault(case.month, []).append(case)

    # 整理輸出
    rows = []
    year_total = 0
    for rt in REPAIR_TYPE_ORDER:
        monthly = type_monthly.get(rt, {})
        row_total = sum(monthly.values())
        year_total += row_total

        prev_m_val = (
            monthly.get(
                _month_offset(year, focus_month or datetime.now().month, -1)[1], 0
            )
            if focus_month
            else 0
        )
        this_m_val = monthly.get(focus_month, 0) if focus_month else 0

        # monthly_detail: {月份: [case_dict, ...]}（只含有資料的月份）
        monthly_detail = {
            m: [c.to_dict() for c in cs]
            for m, cs in type_monthly_cases.get(rt, {}).items()
        }

        rows.append(
            {
                "type": rt,
                "example": REPAIR_TYPE_EXAMPLES.get(rt, ""),
                "monthly": {m: monthly.get(m, 0) for m in range(1, 13)},
                "monthly_detail": monthly_detail,
                "row_total": row_total,
                "prev_month": prev_m_val,
                "this_month": this_m_val,
                "cum_pct": (
                    round(row_total / len(year_cases) * 100, 1) if year_cases else 0.0
                ),
            }
        )

    return {
        "year": year,
        "focus_month": focus_month,
        "rows": rows,
        "year_total": year_total,
        "type_order": REPAIR_TYPE_ORDER,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 11. 4.4 本月客房報修表
# ═════════════════════════════════════════════════════════════════════════════


def compute_room_repair_table(
    all_cases: list[RepairCase],
    year: int,
    month: int,
) -> dict:
    """
    4.4 本月客房報修表：房號 × 客房分類 交叉表。

    ⚠️ 時間規則：以「報修月份」(occ_year/occ_month) 為準，
    反映本月新增的客房報修，不受結案日影響。

    回傳結構（對應前端 RoomRepairTableData）：
    {
      year, month,
      categories: [...],             # ROOM_REPAIR_CATEGORIES 順序
      rows: [{ room_no, floor, categories: {cat: [{ragic_id, title, status}]} }],
      unknown_room_cases: [...],     # 判定為客房但無法解析房號的案件
      floors_with_data: [...],       # 有資料的樓層列表（排序後）
      total_room_cases: int,         # 本月客房案件總數（含無房號）
    }
    """
    # 本月客房報修案件（以報修月份為準）
    month_cases = [
        c for c in all_cases
        if c.occ_year == year and c.occ_month == month and c.is_room_case
    ]

    # 有房號 vs 無法識別房號
    known   = [c for c in month_cases if c.room_no]
    unknown = [c for c in month_cases if not c.room_no]

    # 有資料的樓層（依數字排序）
    floors_with_data: list[str] = sorted(
        {c.floor_normalized for c in known if c.floor_normalized},
        key=lambda f: int(f.rstrip("Ff")) if f.rstrip("Ff").isdigit() else 0,
    )

    # 房號 → { floor, categories: { cat: [entry, ...] } }
    room_data: dict[str, dict] = {}
    for c in known:
        rno = c.room_no
        if rno not in room_data:
            room_data[rno] = {
                "room_no": rno,
                "floor":   c.floor_normalized or c.floor,
                "categories": {},
            }
        cat = c.room_category or "客房設備"
        room_data[rno]["categories"].setdefault(cat, []).append({
            "ragic_id": c.ragic_id,
            "title":    c.title,
            "status":   c.status,
        })

    # 依房號數字排序
    rows = sorted(
        room_data.values(),
        key=lambda x: int(x["room_no"]) if x["room_no"].isdigit() else 0,
    )

    return {
        "year":               year,
        "month":              month,
        "categories":         ROOM_REPAIR_CATEGORIES,
        "rows":               rows,
        "unknown_room_cases": [c.to_dict() for c in unknown],
        "floors_with_data":   floors_with_data,
        "total_room_cases":   len(month_cases),
    }


# ═════════════════════════════════════════════════════════════════════════════
# 12. 過濾條件選項
# ═════════════════════════════════════════════════════════════════════════════

def get_filter_options(all_cases: list[RepairCase]) -> dict:
    """回傳過濾條件的所有可選值（類型、樓層、狀態）"""
    repair_types = sorted({c.repair_type for c in all_cases if c.repair_type})
    floors = sorted({
        (c.floor_normalized or c.floor)
        for c in all_cases
        if (c.floor_normalized or c.floor)
    })
    statuses = sorted({c.status for c in all_cases if c.status})
    return {
        "repair_types": repair_types,
        "floors": floors,
        "statuses": statuses,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 13. 明細清單（分頁 + 排序 + 搜尋）
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
    """
    明細清單：多條件過濾 → 排序 → 分頁。

    year/month 口徑與 Dashboard「本月相關案件」一致（stat 月份）：
      ✅ 已完工案件：以 completed_at 年月（完工月份）歸屬
      ✅ 未完工案件：以 occurred_at 年月（報修月份）歸屬
    → 總表筆數 = Dashboard KPI「本月相關案件」數字
    """
    cases = all_cases

    # ── 年/月過濾（stat 口徑：與 filter_cases / Dashboard 一致）─────────────
    if year is not None:
        cases = [c for c in cases if _stat_year(c) == year]
    if month is not None:
        cases = [c for c in cases if _stat_month(c) == month]
    if repair_type:
        cases = [c for c in cases if c.repair_type == repair_type]
    if floor:
        cases = [c for c in cases if (c.floor_normalized or c.floor) == floor]
    if status:
        cases = [c for c in cases if c.status == status]
    if keyword:
        kw = keyword.lower()
        cases = [
            c for c in cases
            if kw in c.title.lower()
            or kw in c.case_no.lower()
            or kw in c.reporter_name.lower()
            or kw in c.responsible_unit.lower()
            or kw in c.floor.lower()
        ]

    # ── 排序 ──────────────────────────────────────────────────────────────────
    _SORTABLE = {
        "occurred_at", "completed_at", "case_no", "repair_type",
        "floor_normalized", "status", "total_fee", "work_hours",
        "close_days", "responsible_unit",
    }
    if sort_by in _SORTABLE:
        try:
            cases = sorted(
                cases,
                key=lambda c: (getattr(c, sort_by) is None, getattr(c, sort_by) or ""),
                reverse=sort_desc,
            )
        except Exception:
            pass

    # ── 分頁 ──────────────────────────────────────────────────────────────────
    total = len(cases)
    start = (page - 1) * page_size
    page_cases = cases[start: start + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [c.to_dict() for c in page_cases],
    }
