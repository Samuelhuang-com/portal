"""
商場工務每日巡檢表標準模板

來源：2.2商場-每日巡檢表.xlsx
樓層：4F / 3F / 1F~3F / 1F / B1~B4（共 41 列）
欄位：floor | item | check_content | result_options | minutes | source_tab
      + rowSpan 計算欄位（item_first_row / floor_first_row / floor_row_count / item_row_count）

source_tab 對應 mall_fi_inspection_batch.sheet_key：
  4f       → 4F
  3f       → 3F
  1f-3f    → 1F~3F
  1f       → 1F
  b1f-b4f  → B1~B4

巡檢時間：
  早班：08:30 ~ 10:00
  晚班：18:30 ~ 20:00
"""
from __future__ import annotations
from typing import TypedDict


class MallDailyInspectionTemplateRow(TypedDict):
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


# ── 原始資料（floor, item, check_content, result_options, minutes, source_tab）─

_RAW: list[tuple[str, str, str, str, int, str]] = [
    # ── 4F ── 配電室（10 min）────────────────────────────────────────────────
    ("4F", "配電室",     "電器室門禁",                         "□正常□異常",                                 10, "4f"),
    ("4F", "配電室",     "室內溫度與濕度",                      "□_______室內度數□_________濕度",             0,  "4f"),
    ("4F", "配電室",     "配電盤、電氣設備是否有異常發熱",        "□正常□異常過熱",                              0,  "4f"),
    ("4F", "配電室",     "接地線是否牢固",                       "□正常□異常",                                 0,  "4f"),
    ("4F", "配電室",     "各電表抄表",                          "□_________度數",                             0,  "4f"),
    # ── 4F ── 預冷空調箱（3 min）─────────────────────────────────────────────
    ("4F", "預冷空調箱", "風機系統檢查",                        "□正常□異音",                                  3,  "4f"),
    ("4F", "預冷空調箱", "預冷盤管及水系統",                    "□正常□髒污□積水",                             0,  "4f"),
    ("4F", "預冷空調箱", "空氣過濾系統",                        "□乾淨□髒污",                                  0,  "4f"),
    ("4F", "預冷空調箱", "控制系統及感測",                       "□正常□鬆動□位移□接觸不良",                    0,  "4f"),
    ("4F", "預冷空調箱", "排水系統檢查",                        "□正常□異常積水",                              0,  "4f"),
    ("4F", "預冷空調箱", "皮帶檢查",                            "□正常□過緊□鬆弛",                             0,  "4f"),
    # ── 3F ── 靜電機（5 min）─────────────────────────────────────────────────
    ("3F", "靜電機",     "電源與運轉狀態",                      "□正常□異常",                                  5,  "3f"),
    ("3F", "靜電機",     "異常警報燈",                          "□正常□異常",                                  0,  "3f"),
    ("3F", "靜電機",     "集塵箱 / 濾網狀態",                   "□正常□髒污□集塵量高□集塵量低",                0,  "3f"),
    ("3F", "靜電機",     "排油管路",                            "□正常□異常□管路變形□滲漏",                    0,  "3f"),
    ("3F", "靜電機",     "靜電模組",                            "□正常□變形□損壞",                             0,  "3f"),
    ("3F", "靜電機",     "廠商年度保養",                        "□正常□異常□查修表",                            0,  "3f"),
    # ── 1F ~ 3F ── 櫃位（90 min）─────────────────────────────────────────────
    ("1F ~ 3F", "櫃位",  "各櫃位抄水電瓦斯表(25)",              "□_________度數*25",                          90, "1f-3f"),
    # ── 1F ~ 3F ── 空調箱（5 min）────────────────────────────────────────────
    ("1F ~ 3F", "空調箱", "基本外觀檢查",                       "□正常□破損",                                  5,  "1f-3f"),
    ("1F ~ 3F", "空調箱", "濾網檢查",                           "□正常□髒污",                                  0,  "1f-3f"),
    ("1F ~ 3F", "空調箱", "風機/馬達系統",                      "□正常□異常",                                  0,  "1f-3f"),
    ("1F ~ 3F", "空調箱", "冷/熱盤管",                          "□正常□異常",                                  0,  "1f-3f"),
    ("1F ~ 3F", "空調箱", "溫度與濕度控制",                     "□_______室內度數□_________濕度",               0,  "1f-3f"),
    ("1F ~ 3F", "空調箱", "控制系統",                           "□正常□異常□未連線",                            0,  "1f-3f"),
    # ── 1F ── 水洗機（3 min）─────────────────────────────────────────────────
    ("1F", "水洗機",     "電源狀態、控制面板",                   "□正常□異常",                                  3,  "1f"),
    ("1F", "水洗機",     "水源管路與接頭",                       "□正常□堵塞",                                  0,  "1f"),
    ("1F", "水洗機",     "洗劑加注器",                          "□正常□結垢",                                  0,  "1f"),
    ("1F", "水洗機",     "機體外觀、排水功能",                   "□正常□堵塞",                                  0,  "1f"),
    ("1F", "水洗機",     "傳動皮帶 / 軸承",                     "□正常□鬆脫□斷裂□磨損",                        0,  "1f"),
    ("1F", "水洗機",     "機體震動與噪音",                       "□正常□異常□鏽蝕",                             0,  "1f"),
    # ── B1 ~ B4 ── 抽排風設備（3 min）───────────────────────────────────────
    ("B1 ~ B4", "抽排風設備", "風機本體、風管系統檢查",          "□正常□異常□異音",                             3,  "b1f-b4f"),
    ("B1 ~ B4", "抽排風設備", "濾網與過濾系統",                  "□正常□異常□髒污",                             0,  "b1f-b4f"),
    ("B1 ~ B4", "抽排風設備", "控制系統檢查",                    "□正常□異常",                                  0,  "b1f-b4f"),
    ("B1 ~ B4", "抽排風設備", "安全與警報系統",                  "□正常□異常",                                  0,  "b1f-b4f"),
    ("B1 ~ B4", "抽排風設備", "現場環境",                        "□正常□異常",                                  0,  "b1f-b4f"),
    # ── B1 ~ B4 ── 電信設備（3 min）─────────────────────────────────────────
    ("B1 ~ B4", "電信設備", "外觀檢查、設備外殼、線纜接頭",       "□正常□異常□未鎖緊",                            3,  "b1f-b4f"),
    ("B1 ~ B4", "電信設備", "電源檢查、電源指示燈、UPS供電狀態",  "□正常□異常",                                  0,  "b1f-b4f"),
    ("B1 ~ B4", "電信設備", "網路狀態、網路連線狀況",             "□正常□異常",                                  0,  "b1f-b4f"),
    ("B1 ~ B4", "電信設備", "設備運作、溫度狀況",                 "□正常□異常",                                  0,  "b1f-b4f"),
    ("B1 ~ B4", "電信設備", "防塵清潔",                          "□正常□積塵",                                  0,  "b1f-b4f"),
]


def _build_template() -> list[MallDailyInspectionTemplateRow]:
    """計算 rowSpan 欄位並回傳完整模板列表。"""
    # 計算各 floor 的列數
    floor_counts: dict[str, int] = {}
    for floor, *_ in _RAW:
        floor_counts[floor] = floor_counts.get(floor, 0) + 1

    # 計算各 (floor, item) 的列數
    item_counts: dict[tuple[str, str], int] = {}
    for floor, item, *_ in _RAW:
        k = (floor, item)
        item_counts[k] = item_counts.get(k, 0) + 1

    rows: list[MallDailyInspectionTemplateRow] = []
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


MALL_DAILY_INSPECTION_TEMPLATE: list[MallDailyInspectionTemplateRow] = _build_template()
