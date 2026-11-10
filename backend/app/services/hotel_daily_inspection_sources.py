"""
飯店每日巡檢 — Ragic 來源登錄檔（2026-11-10，比照 mall_facility_sources.py）

2026-11-10 Samuel 裁示：
  - 新表：main-project-inspection/17、28～33，共 7 個頁籤（依樓層）。
  - 舊表已封存至 archive-old-data，新舊連結必須同時存在；舊資料掛在最接近的新頁籤下。
      舊 18（4F~10F）→ archive-old-data/31   → 頁籤 5f-10f
      舊 19（4F）    → archive-old-data/32   → 頁籤 4f
      舊 20（2F）    → archive-old-data/33   → 頁籤 4f（無 2F 頁籤，掛最接近的公區頁籤）
      舊 21（1F）    → archive-old-data/34   → 頁籤 4f（同上）
      archive-old-data/35（4F）              → 頁籤 4f（Portal 以前未同步，這次一起接）
      archive-old-data/36～40（5F～9F）       → 頁籤 5f-10f（同上）
  - 舊 RF（17）：Ragic 封存區找不到，只存在 Portal DB；表號 17 已改為新 RF 表。
    舊場次改寫為 rf_legacy_{Row ID}（migration hdi1），不同步、無 Ragic 連結。

場次 ID（HotelDIBatch.ragic_id）＝ "{source_key}_{Ragic Row ID}"；sheet_key 另存頁籤。
⚠️ 不同 Sheet 的 Row ID 各自從 0 編號，必須加 source_key 前綴，否則會互相覆蓋。
"""
from __future__ import annotations

from dataclasses import dataclass

SERVER_URL = "ap12.ragic.com"
ACCOUNT    = "soutlet001"


@dataclass(frozen=True)
class HotelDISource:
    source_key: str     # 場次 ID 前綴
    tab:        str     # 頁籤（sheet_key）
    label:      str     # 介面顯示
    sheet_path: str     # Ragic 路徑（不含主機與帳號）；空字串＝已無 Ragic 表（不同步、無連結）
    archived:   bool = False


# 頁籤順序與顯示名稱（Ragic 表單名稱去掉「飯店工務每日巡檢 -」前綴）
TAB_LABELS: dict[str, str] = {
    "rf":         "RF 樓層 早班巡檢",
    "5f-10f":     "5-10F 客房公共區域",
    "4f":         "4F BAR-D公區",
    "b1f-hv":     "B1F 高壓機房",
    "b1f-office": "B1F 晚班巡檢 辦公室公區 廚房瓦斯設備",
    "b4f-water":  "B4F 早班巡檢 下水塔",
    "b4f-ac":     "B4F 晚班巡檢 空調機房",
}

SOURCES: list[HotelDISource] = [
    HotelDISource("rf_17",         "rf",         "RF 樓層 早班巡檢",               "main-project-inspection/17"),
    HotelDISource("rf_legacy",     "rf",         "RF 舊表（Ragic 已無此表）",       "", True),
    HotelDISource("5f-10f_28",     "5f-10f",     "5-10F 客房公共區域",              "main-project-inspection/28"),
    HotelDISource("5f-10f_a31",    "5f-10f",     "4F~10F 舊表（封存）",             "archive-old-data/31", True),
    HotelDISource("5f-10f_a36",    "5f-10f",     "5F 舊表（封存）",                 "archive-old-data/36", True),
    HotelDISource("5f-10f_a37",    "5f-10f",     "6F 舊表（封存）",                 "archive-old-data/37", True),
    HotelDISource("5f-10f_a38",    "5f-10f",     "7F 舊表（封存）",                 "archive-old-data/38", True),
    HotelDISource("5f-10f_a39",    "5f-10f",     "8F 舊表（封存）",                 "archive-old-data/39", True),
    HotelDISource("5f-10f_a40",    "5f-10f",     "9F 舊表（封存）",                 "archive-old-data/40", True),
    HotelDISource("4f_29",         "4f",         "4F BAR-D公區",                    "main-project-inspection/29"),
    HotelDISource("4f_a32",        "4f",         "4F 戶外廣場與宴會廳 舊表（封存）",  "archive-old-data/32", True),
    HotelDISource("4f_a35",        "4f",         "4F 舊表（封存）",                 "archive-old-data/35", True),
    HotelDISource("4f_a33",        "4f",         "2F 舊表（封存）",                 "archive-old-data/33", True),
    HotelDISource("4f_a34",        "4f",         "1F 舊表（封存）",                 "archive-old-data/34", True),
    HotelDISource("b1f-hv_30",     "b1f-hv",     "B1F 高壓機房",                    "main-project-inspection/30"),
    HotelDISource("b1f-office_31", "b1f-office", "B1F 晚班巡檢 辦公室公區、廚房瓦斯設備", "main-project-inspection/31"),
    HotelDISource("b4f-water_32",  "b4f-water",  "B4F 早班巡檢 下水塔",              "main-project-inspection/32"),
    HotelDISource("b4f-ac_33",     "b4f-ac",     "B4F 晚班巡檢 空調機房",            "main-project-inspection/33"),
]

_BY_KEY = {s.source_key: s for s in SOURCES}
TABS: list[str] = list(TAB_LABELS.keys())


def sources_for(tab: str) -> list[HotelDISource]:
    return [s for s in SOURCES if s.tab == tab]


def syncable_sources(tab: str) -> list[HotelDISource]:
    """有 Ragic 表的來源（rf_legacy 沒有 Ragic 表，不同步）。"""
    return [s for s in sources_for(tab) if s.sheet_path]


def live_source(tab: str) -> HotelDISource | None:
    """頁籤的現行（非封存）來源；沒有則回 None。"""
    return next((s for s in sources_for(tab) if not s.archived), None)


def batch_source(batch_id: str) -> HotelDISource | None:
    """依場次 ID 找來源：'4f_a32_12' → source '4f_a32'（以最長前綴比對）。"""
    best = None
    for key, src in _BY_KEY.items():
        if batch_id.startswith(key + "_") and (best is None or len(key) > len(best.source_key)):
            best = src
    return best


def is_live_batch(batch_id: str) -> bool:
    """場次是否來自現行（新）表 —— 每日巡檢表、樓層巡檢圖只看新表。"""
    src = batch_source(batch_id)
    return bool(src and not src.archived)


def numeric_id(batch_id: str) -> str:
    """場次 ID 的 Ragic Row ID（最後一段）。"""
    return batch_id.rsplit("_", 1)[-1]


def sheet_url(src: HotelDISource) -> str:
    return f"https://{SERVER_URL}/{ACCOUNT}/{src.sheet_path}" if src.sheet_path else ""


def record_url(batch_id: str) -> str:
    """場次 ID → Ragic 單筆紀錄網址（找不到來源或來源已無 Ragic 表回空字串）。"""
    src = batch_source(batch_id)
    if src is None or not src.sheet_path:
        return ""
    return f"https://{SERVER_URL}/{ACCOUNT}/{src.sheet_path}/{numeric_id(batch_id)}"
