"""
商場工務巡檢 — Ragic 來源登錄檔（2026-10-30）

頁籤（tab，即 MallFIBatch.sheet_key）對應一或多張 Ragic Sheet：
  - 新 Sheet：本次新增（26、27、28、29、30）與既有的 B1F~B4F（7，已封存於 archive-old-data/27）。
  - 封存來源：舊 Sheet 2～5 已轉址至 archive-old-data/23～26，保留為唯讀歷史。

場次 ID（MallFIBatch.ragic_id）＝ "{source_key}_{Ragic Row ID}"，source_key 形如 "4f_27"、"4f_2"。
sheet_key（tab）另存一欄，供頁籤查詢；source_key 決定 Ragic 連結與來源。

⚠️ 不同 Sheet 的 Row ID 各自編號，必須加上 source_key 前綴，否則會互相覆蓋。
"""
from __future__ import annotations

from dataclasses import dataclass

SERVER_URL = "ap12.ragic.com"
ACCOUNT    = "soutlet001"


@dataclass(frozen=True)
class MallFISource:
    source_key: str     # 場次 ID 前綴：{tab}_{Sheet 編號}
    tab:        str     # 頁籤（sheet_key）
    label:      str     # 介面顯示
    sheet_path: str     # Ragic 路徑（不含主機與帳號）
    archived:   bool = False


SOURCES: list[MallFISource] = [
    MallFISource("1-4f_26",   "1-4f",    "1-4F",                    "mall-facility-inspection/26"),
    MallFISource("4f_27",     "4f",      "4F",                      "mall-facility-inspection/27"),
    MallFISource("4f_2",      "4f",      "4F 舊表（封存）",          "archive-old-data/23", True),
    MallFISource("3f_28",     "3f",      "3F",                      "mall-facility-inspection/28"),
    MallFISource("3f_3",      "3f",      "3F 舊表（封存）",          "archive-old-data/24", True),
    MallFISource("1f-3f_29",  "1f-3f",   "1F~3F",                   "mall-facility-inspection/29"),
    MallFISource("1f-3f_4",   "1f-3f",   "1F~3F 舊表（封存）",        "archive-old-data/25", True),
    MallFISource("1f_30",     "1f",      "1F",                      "mall-facility-inspection/30"),
    MallFISource("1f_5",      "1f",      "1F 舊表（封存）",           "archive-old-data/26", True),
    MallFISource("b1f-b4f_7", "b1f-b4f", "B1F~B4F（封存）",           "archive-old-data/27", True),
    MallFISource("b1f-b4f_arc28", "b1f-b4f", "B1F~B4F 封存（28）",      "archive-old-data/28", True),
    MallFISource("b1f-b4f_arc29", "b1f-b4f", "B1F~B4F 封存（29）",      "archive-old-data/29", True),
    MallFISource("b1f-b4f_arc30", "b1f-b4f", "B1F~B4F 封存（30）",      "archive-old-data/30", True),
]

_BY_KEY = {s.source_key: s for s in SOURCES}
TABS: list[str] = list(dict.fromkeys(s.tab for s in SOURCES))


def sources_for(tab: str) -> list[MallFISource]:
    return [s for s in SOURCES if s.tab == tab]


def live_source(tab: str) -> MallFISource | None:
    """頁籤的第一個現行（非封存）來源；沒有則回 None。"""
    return next((s for s in sources_for(tab) if not s.archived), None)


def batch_source(batch_id: str) -> MallFISource | None:
    """依場次 ID 找來源：'4f_27_12' → source '4f_27'（以最長前綴比對）。"""
    best = None
    for key, src in _BY_KEY.items():
        if batch_id.startswith(key + "_") and (best is None or len(key) > len(best.source_key)):
            best = src
    return best


def numeric_id(batch_id: str) -> str:
    """場次 ID 的 Ragic Row ID（最後一段）。"""
    return batch_id.rsplit("_", 1)[-1]


def record_url(batch_id: str) -> str:
    """場次 ID → Ragic 單筆紀錄網址（找不到來源回空字串）。"""
    src = batch_source(batch_id)
    if src is None:
        return ""
    return f"https://{SERVER_URL}/{ACCOUNT}/{src.sheet_path}/{numeric_id(batch_id)}"
