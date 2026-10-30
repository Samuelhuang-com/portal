"""
整棟工務每日巡檢 — Ragic 來源登錄檔（RF / B1F / B2F / B4F / B1~B4）

一個樓層可以對應多張 Ragic Sheet（例如 B4F 拆為冰水／連續壁／汙廢水／下水塔四張）。
每一張 Sheet 就是一個「來源」（InspectionSource），以 sheet_key 識別。

ID 規則（與 sync_tool 既有的複合鍵慣例一致，見 ragic_verify_utils.fetch_ragic_url_map_multi）：
  batch ragic_id = "{sheet_key}_{Ragic Row ID}"    例：b4f_9_0
  item  ragic_id = "{batch ragic_id}_{seq_no}"      例：b4f_9_0_1
  sheet_key 另存一欄，方便依來源篩選。

封存來源（archived=True）：
  舊的 full-building-inspection/1～4 已轉址至 archive-old-data/19～22，
  因此直接指向封存路徑，資料保留為唯讀歷史來源。

新增 Sheet：只要在 SOURCES 加一筆即可，不需改同步程式碼。
"""
from dataclasses import dataclass

# Ragic 連線（與各模組既有預設一致）
SERVER_URL = "ap12.ragic.com"
ACCOUNT    = "soutlet001"


@dataclass(frozen=True)
class InspectionSource:
    sheet_key:  str    # 寫入 DB 的 sheet_key，也是 ragic_id 前綴
    floor:      str    # 樓層 key：rf / b1f / b2f / b4f / b1b4
    label:      str    # 介面顯示用（Ragic 題目或 TAB 名稱）
    sheet_path: str    # Ragic 路徑（不含帳號與主機）
    archived:   bool = False


SOURCES: list[InspectionSource] = [
    # ── RF ──────────────────────────────────────────────────────────────
    InspectionSource("rf_1",  "rf",   "RF 舊表（封存）",                 "archive-old-data/19", True),
    InspectionSource("rf_5",  "rf",   "冷卻水塔／上水塔",                 "full-building-inspection/5"),
    # ── B1F ─────────────────────────────────────────────────────────────
    InspectionSource("b1f_4", "b1f",  "B1F 舊表（封存）",                 "archive-old-data/22", True),
    InspectionSource("b1f_6", "b1f",  "發電機／高壓機房／電信設備／瓦斯設備", "full-building-inspection/6"),
    # ── B2F ─────────────────────────────────────────────────────────────
    InspectionSource("b2f_3", "b2f",  "B2F 舊表（封存）",                 "archive-old-data/21", True),
    InspectionSource("b2f_7", "b2f",  "油脂截流槽",                       "full-building-inspection/7"),
    # ── B4F ─────────────────────────────────────────────────────────────
    InspectionSource("b4f_2", "b4f",  "B4F 舊表（封存）",                 "archive-old-data/20", True),
    InspectionSource("b4f_9", "b4f",  "冰水主機／冰水泵／冷卻水泵",        "full-building-inspection/9"),
    InspectionSource("b4f_10","b4f",  "連續壁",                           "full-building-inspection/10"),
    InspectionSource("b4f_11","b4f",  "汙廢水",                           "full-building-inspection/11"),
    InspectionSource("b4f_12","b4f",  "下水塔",                           "full-building-inspection/12"),
    # ── B1~B4（新樓層）────────────────────────────────────────────────────
    InspectionSource("b1b4_8","b1b4", "抽排風設備",                       "full-building-inspection/8"),
]

_BY_KEY: dict[str, InspectionSource] = {s.sheet_key: s for s in SOURCES}


def sources_for(floor: str) -> list[InspectionSource]:
    """某樓層的所有來源（含封存），依登錄順序。"""
    return [s for s in SOURCES if s.floor == floor]


def source_by_key(sheet_key: str) -> InspectionSource | None:
    return _BY_KEY.get(sheet_key)


def make_batch_id(sheet_key: str, row_id: str | int) -> str:
    """組出全站唯一的場次 ID：{sheet_key}_{Ragic Row ID}。"""
    return f"{sheet_key}_{row_id}"


def record_url(sheet_path: str, row_id: str) -> str:
    """Ragic 記錄直連 URL（與 work_journal._ragic_url 的格式一致）。"""
    return f"https://{SERVER_URL}/{ACCOUNT}/{sheet_path}/{row_id}"


def numeric_id(batch_id: str) -> str:
    """場次 ID 取出 Ragic Row ID（最後一段）：'b4f_9_0' → '0'。"""
    return batch_id.rsplit("_", 1)[-1]


def path_for_batch_id(batch_id: str) -> str | None:
    """依場次 ID 找到來源 Sheet 路徑；找不到回 None。"""
    for sk, src in _BY_KEY.items():
        if batch_id.startswith(sk + "_"):
            return src.sheet_path
    return None
