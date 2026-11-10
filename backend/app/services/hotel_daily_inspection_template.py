"""
飯店每日巡檢表標準模板（2026-11-10，比照 mall_daily_inspection_template.py）

來源：myDoc/巡檢表_1110/(飯店)每日設備巡檢表_1029(飯店定案版).xlsx
2026-11-10 Samuel 裁示：以 Excel 提供的 Ragic 連結為準，顏色標記忽略；
「每日巡檢表」只顯示新項目 —— 這裡只收新 Ragic 表（main-project-inspection/17、28～33）
上實際存在的檢查欄位（2026-11-10 以瀏覽器讀 Ragic 列表欄位確認）。

floor：Drawer 的樓層格，每個頁籤一組（B1F、B4F 各有兩張表，分開顯示各自的 Ragic 連結）
欄位：floor | item | check_content | result_options | minutes | source_tab
      + rowSpan 計算欄位（item_first_row / floor_first_row / floor_row_count / item_row_count）
minutes：Excel E 欄（時間/分），空白＝0。

source_tab 對應 hotel_di_inspection_batch.sheet_key（見 hotel_daily_inspection_sources.TAB_LABELS）。
早班／晚班不寫進 Portal（2026-11-10 裁示）。
"""
from __future__ import annotations

from typing import TypedDict


class HotelDailyInspectionTemplateRow(TypedDict):
    floor:           str
    item:            str
    check_content:   str
    result_options:  str
    minutes:         int
    source_tab:      str
    item_first_row:  bool
    floor_first_row: bool
    floor_row_count: int
    item_row_count:  int


_N  = "□正常□異常"
_LMH = "□低□中□高"

# (floor, item, check_content, result_options, minutes, source_tab)
_RAW: list[tuple[str, str, str, str, int, str]] = [
    # ── RF（main-project-inspection/17）──────────────────────────────────────
    ("RF", "冷卻水塔",   "水位檢查",                 _LMH,                               5,  "rf"),
    ("RF", "冷卻水塔",   "水泵運作狀態",             "□正常□異常□懸浮物",               5,  "rf"),
    ("RF", "上水塔",     "水位狀態",                 _LMH,                               10, "rf"),
    ("RF", "上水塔",     "水質觀察",                 "□正常□異常□懸浮物□低□中□高",     0,  "rf"),
    ("RF", "上水塔",     "膨脹水箱水位",             _LMH,                               0,  "rf"),
    ("RF", "熱水系統",   "3-6F客房熱水回水泵",       "A泵□正常□異常　B泵□正常□異常",   15, "rf"),
    ("RF", "熱水系統",   "11-12F客房熱水回水泵",     "A泵□正常□異常　B泵□正常□異常",   0,  "rf"),
    ("RF", "鍋爐設備",   "鍋爐電源",                 "#1 □開□關，#2 □開□關",            0,  "rf"),
    ("RF", "鍋爐設備",   "熱水儲存桶溫度",           _N,                                 0,  "rf"),
    ("RF", "鍋爐設備",   "熱水儲存桶加熱泵浦開關",   "□開啟□關閉□異常",                 0,  "rf"),
    ("RF", "鍋爐設備",   "變頻加壓泵浦壓力值",       _N,                                 0,  "rf"),
    ("RF", "RF瓦斯",     "外觀與結構",               _N,                                 0,  "rf"),
    ("RF", "RF瓦斯",     "是否有洩漏狀況",           _N,                                 0,  "rf"),
    # ── 5-10F（main-project-inspection/28）───────────────────────────────────
    ("5-10F", "客房公共區域", "5樓客房走道空調箱",  _N, 30, "5f-10f"),
    ("5-10F", "客房公共區域", "6樓客房走道空調箱",  _N, 0,  "5f-10f"),
    ("5-10F", "客房公共區域", "7樓客房走道空調箱",  _N, 0,  "5f-10f"),
    ("5-10F", "客房公共區域", "8樓客房走道空調箱",  _N, 0,  "5f-10f"),
    ("5-10F", "客房公共區域", "9樓客房走道空調箱",  _N, 0,  "5f-10f"),
    ("5-10F", "客房公共區域", "10樓客房走道空調箱", _N, 0,  "5f-10f"),
    # ── 4F（main-project-inspection/29）──────────────────────────────────────
    ("4F", "BAR-D公區", "空調箱啟動",            _N, 10, "4f"),
    ("4F", "BAR-D公區", "BAR-D 飲水機、製冰機", _N, 0,  "4f"),
    ("4F", "BAR-D公區", "燈光視覺檢查",          _N, 0,  "4f"),
    # ── B1F 高壓機房（main-project-inspection/30）────────────────────────────
    ("B1F 高壓機房", "高壓機房", "室內照明正常",              _N,               20, "b1f-hv"),
    ("B1F 高壓機房", "高壓機房", "地面乾燥、無積水",          _N,               0,  "b1f-hv"),
    ("B1F 高壓機房", "高壓機房", "消防器材擺放明顯",          "□正常□異常□短缺", 0, "b1f-hv"),
    ("B1F 高壓機房", "高壓機房", "配電盤面板清潔",            "□正常□異常□積塵", 0, "b1f-hv"),
    ("B1F 高壓機房", "高壓機房", "開關設備運作正常",          _N,               0,  "b1f-hv"),
    ("B1F 高壓機房", "高壓機房", "指示燈號顯示正確",          _N,               0,  "b1f-hv"),
    ("B1F 高壓機房", "高壓機房", "保險絲與斷路器完整",        _N,               0,  "b1f-hv"),
    ("B1F 高壓機房", "高壓機房", "無異常聲音",                _N,               0,  "b1f-hv"),
    ("B1F 高壓機房", "高壓機房", "UPS 電源正常供電",          _N,               0,  "b1f-hv"),
    ("B1F 高壓機房", "高壓機房", "ATS（自動切換）功能正常",   _N,               0,  "b1f-hv"),
    ("B1F 高壓機房", "高壓機房", "遠端監控系統無異常",        _N,               0,  "b1f-hv"),
    # ── B1F 晚班：辦公室公區、廚房瓦斯設備（main-project-inspection/31）───────
    ("B1F 辦公室公區、廚房瓦斯", "辦公室公區",   "燈光視覺檢查",   _N, 20, "b1f-office"),
    ("B1F 辦公室公區、廚房瓦斯", "辦公室公區",   "空調送風機",     _N, 0,  "b1f-office"),
    ("B1F 辦公室公區、廚房瓦斯", "廚房瓦斯設備", "外觀與結構",     _N, 15, "b1f-office"),
    ("B1F 辦公室公區、廚房瓦斯", "廚房瓦斯設備", "電壓是否正常",   _N, 0,  "b1f-office"),
    ("B1F 辦公室公區、廚房瓦斯", "廚房瓦斯設備", "是否有洩漏狀況", _N, 0,  "b1f-office"),
    # ── B4F 早班：下水塔（main-project-inspection/32）────────────────────────
    ("B4F 下水塔", "下水塔", "水塔結構完整無裂縫",     "□正常□異常□破損",       15, "b4f-water"),
    ("B4F 下水塔", "下水塔", "液位、浮球感測器正常",   "□正常□高水位□低水位",   0,  "b4f-water"),
    ("B4F 下水塔", "下水塔", "幫浦啟停控制正常",       _N,                       0,  "b4f-water"),
    ("B4F 下水塔", "下水塔", "止回閥與電磁閥功能良好", _N,                       0,  "b4f-water"),
    ("B4F 下水塔", "下水塔", "無懸浮物漂浮",           _N,                       0,  "b4f-water"),
    ("B4F 下水塔", "下水塔", "進水/出水管無滲漏",      _N,                       0,  "b4f-water"),
    ("B4F 下水塔", "下水塔", "接頭與法蘭固定良好",     _N,                       0,  "b4f-water"),
    # ── B4F 晚班：空調機房（main-project-inspection/33）──────────────────────
    ("B4F 空調機房", "空調機房", "冰水主機基本運轉狀態", _N,                        45, "b4f-ac"),
    ("B4F 空調機房", "空調機房", "電機運轉電流",         "□正常□異常□短缺",         0,  "b4f-ac"),
    ("B4F 空調機房", "空調機房", "電壓是否正常",         "□正常□異常□積塵",         0,  "b4f-ac"),
    ("B4F 空調機房", "空調機房", "蒸發器壓力",           _N,                         0,  "b4f-ac"),
    ("B4F 空調機房", "空調機房", "冷凝器壓力",           _N,                         0,  "b4f-ac"),
    ("B4F 空調機房", "空調機房", "冷媒液位",             _N,                         0,  "b4f-ac"),
    ("B4F 空調機房", "空調機房", "冰水進水溫度",         "□正常□異常□_____度數",    0,  "b4f-ac"),
    ("B4F 空調機房", "空調機房", "冰水出水溫度",         "□正常□異常□_____度數",    0,  "b4f-ac"),
    ("B4F 空調機房", "空調機房", "冰水進出溫差",         "□正常□異常□_____度數",    0,  "b4f-ac"),
    ("B4F 空調機房", "空調機房", "流量 / 壓力值",        "□正常□異常□_____Kg2",     0,  "b4f-ac"),
    ("B4F 空調機房", "空調機房", "管路、閥件有無滲漏",   _N,                         0,  "b4f-ac"),
    ("B4F 空調機房", "空調機房", "隔熱材是否完好",       "□正常□異常□查修表",       0,  "b4f-ac"),
    ("B4F 空調機房", "空調機房", "設備地面有無積水",     _N,                         0,  "b4f-ac"),
]


def _build_template() -> list[HotelDailyInspectionTemplateRow]:
    floor_counts: dict[str, int] = {}
    for floor, *_ in _RAW:
        floor_counts[floor] = floor_counts.get(floor, 0) + 1

    item_counts: dict[tuple[str, str], int] = {}
    for floor, item, *_ in _RAW:
        k = (floor, item)
        item_counts[k] = item_counts.get(k, 0) + 1

    rows: list[HotelDailyInspectionTemplateRow] = []
    seen_floors: set[str] = set()
    seen_items:  set[tuple[str, str]] = set()
    for floor, item, check_content, result_options, minutes, source_tab in _RAW:
        item_key = (floor, item)
        rows.append({
            "floor":           floor,
            "item":            item,
            "check_content":   check_content,
            "result_options":  result_options,
            "minutes":         minutes,
            "source_tab":      source_tab,
            "item_first_row":  item_key not in seen_items,
            "floor_first_row": floor not in seen_floors,
            "floor_row_count": floor_counts[floor],
            "item_row_count":  item_counts[item_key],
        })
        seen_floors.add(floor)
        seen_items.add(item_key)
    return rows


HOTEL_DAILY_INSPECTION_TEMPLATE: list[HotelDailyInspectionTemplateRow] = _build_template()
