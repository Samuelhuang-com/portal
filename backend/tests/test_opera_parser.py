"""
OPERA TXT 解析器單元測試（規格書 §16.1）

執行：
    cd backend && python -m pytest tests/test_opera_parser.py -v

以真實 OPERA 匯出檔做的端到端對帳測試，需把兩份 TXT 放在
`backend/tests/fixtures/` 底下才會執行（無檔案時自動 skip）：
    departure_all.txt
    history_forecast.txt
"""
from __future__ import annotations

import pathlib

import pytest

from app.services import opera_parser as P

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
DEPARTURE_FILE = FIXTURES / "departure_all.txt"
HF_FILE = FIXTURES / "history_forecast.txt"


# ══════════════════════════════════════════════════════════════════════════════
# 日期解析（規格書 §3.7）
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("raw,expected", [
    ("01-JAN-26",     "2026-01-01"),   # DEPARTURE / CONSIDERED_DATE 格式
    ("05-FEB-24",     "2024-02-05"),
    ("29-12-23",      "2023-12-29"),   # ARRIVAL 是 DD-MM-YY，不是 DD-MON-YY
    ("01-01-26 Thu",  "2026-01-01"),   # CHAR_CONSIDERED_DATE 帶星期後綴
    ("31-DEC-99",     "1999-12-31"),   # 兩位年份 pivot = 70
    ("2026-01-01",    None),
    ("abc",           None),
    ("",              None),
])
def test_parse_opera_date(raw, expected):
    assert P.parse_opera_date(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("12:03", 723),
    ("00:00", 0),
    ("23:59", 1439),
    ("25:00", None),
    ("",      None),
])
def test_parse_time_minutes(raw, expected):
    assert P.parse_time_minutes(raw) == expected


# ══════════════════════════════════════════════════════════════════════════════
# 住客姓名遮罩（規格書 §13.2）
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("raw,expected", [
    ("LIN,YU CHENG,Mr.",   "LIN,Y* C****,Mr."),
    ("TAN,CHEE SIANG,Mr.", "TAN,C*** S****,Mr."),
    ("王小明",              "王*明"),
    ("陳明",                "陳*"),
    ("歐陽小明",            "歐**明"),
    ("Purged-Individual",  P.PURGED_LABEL),
    ("*Purged-Individual", P.PURGED_LABEL),
    ("",                   P.EMPTY_LABEL),
])
def test_mask_guest_name(raw, expected):
    assert P.mask_guest_name(raw) == expected


def test_mask_never_leaks_given_name():
    """遮罩後不得殘留完整名字。"""
    masked = P.mask_guest_name("LIN,YU CHENG,Mr.")
    assert "YU" not in masked
    assert "CHENG" not in masked
    assert masked.startswith("LIN,")


@pytest.mark.parametrize("raw", ["Purged-Individual", "*Purged-Individual", ""])
def test_purged_guest_has_no_identity_hash(raw):
    assert P.compute_guest_identity_hash("SUMMER", raw, "12345") is None


def test_identity_hash_is_stable_and_irreversible():
    h1 = P.compute_guest_identity_hash("SUMMER", "LIN,YU CHENG,Mr.", "999")
    h2 = P.compute_guest_identity_hash("SUMMER", "lin,yu  cheng,mr.", "999")
    assert h1 == h2                      # 大小寫／多餘空白不影響
    assert h1 is not None and len(h1) == 64
    assert "LIN" not in h1


def test_invalid_guest_name_id_is_normalized():
    """OPERA 對已清除住客填 -100，不得當作有效識別碼。"""
    assert P.clean_guest_name_id("-100") is None
    assert P.clean_guest_name_id("0") is None
    assert P.clean_guest_name_id("") is None
    assert P.clean_guest_name_id("69756859") == "69756859"


# ══════════════════════════════════════════════════════════════════════════════
# Departure 續行合併（規格書 §3.2）
# ══════════════════════════════════════════════════════════════════════════════

def _dep_line(**over) -> str:
    """組一列 45 欄的 Departure 資料。"""
    cells = [""] * 45
    cells[0]  = over.get("DEPARTURE", "01-JAN-24")
    cells[10] = over.get("RESORT1", "SUMMER")
    cells[11] = "N"
    cells[12] = over.get("ROOM", "0408")
    cells[13] = over.get("NIGHTS", "3")
    cells[14] = over.get("ARRIVAL", "29-12-23")
    cells[15] = over.get("NO_OF_ROOMS", "1")
    cells[17] = "CHECKED OUT"
    cells[18] = "12:03"
    cells[20] = over.get("GUEST_NAME", "Purged-Individual")
    cells[21] = over.get("ADULTS", "2")
    cells[22] = over.get("CHILDREN", "0")
    cells[25] = over.get("ROOM_CATEGORY_LABEL", "SK")
    cells[27] = over.get("TRAVEL_AGENT_NAME", "")
    cells[32] = over.get("RESV_NAME_ID", "30860050")
    cells[33] = over.get("GUEST_NAME_ID", "-100")
    cells[35] = over.get("RATE_CODE", "OPEN")
    cells[42] = over.get("PROF_ATTACHED", "")
    cells[43] = "0"
    cells[44] = "0"
    return "\t".join(cells)


def _build_departure_txt(data_lines: list[str], footer_rooms: int, footer_persons: int) -> bytes:
    from app.models.opera_departure import DEPARTURE_COLUMNS
    header = "\t".join(DEPARTURE_COLUMNS)
    footer = (
        "SUMBALANCEPERREPORT\tSUMNO_OF_ROOMSPERREPORT\tSUMPERSONSPERREPORT\tLOGO\n"
        f"0\t{footer_rooms}\t{footer_persons}\t"
    )
    return ("\n".join([header, *data_lines, footer]) + "\n").encode("utf-8")


def test_departure_normal_row():
    content = _build_departure_txt([_dep_line()], footer_rooms=1, footer_persons=2)
    r = P.parse_departure(content)
    assert r.row_count_rejected == 0
    assert len(r.records) == 1
    fact = r.records[0].fact
    assert fact["departure_date"] == "2024-01-01"
    assert fact["arrival_date"] == "2023-12-29"
    assert fact["room_nights"] == 3
    assert fact["property_code"] == "SUMMER"
    assert fact["guest_identity_hash"] is None      # Purged
    assert fact["is_purged"] == 1
    assert P.reconcile_departure(r)["ok"] is True


def test_departure_continuation_merge():
    """43 欄 + 3 欄 → 合併成 45 欄，PROF_ATTACHED 含換行。"""
    full = _dep_line(PROF_ATTACHED="T- D-edge").split("\t")
    truncated = "\t".join(full[:43])                       # 尾端 PROF_COUNT/RES_COUNT 被換行切掉
    continuation = "G- 385368408 KO, CHIA LING\t0\t0"
    content = _build_departure_txt([truncated, continuation], footer_rooms=1, footer_persons=2)

    r = P.parse_departure(content)
    assert r.merged_pairs == 1
    assert len(r.records) == 1
    rec = r.records[0]
    assert rec.raw["PROF_ATTACHED"] == "T- D-edge\nG- 385368408 KO, CHIA LING"
    assert rec.raw["PROF_COUNT"] == "0"
    assert rec.raw["RES_COUNT"] == "0"
    assert rec.source_row_no_end == rec.source_row_no + 1  # raw 層保留列號關係


def test_departure_header_52_vs_row_45():
    """表頭 52 欄、資料列 45 欄時，尾端 7 欄回傳空字串且不得報錯。"""
    from app.models.opera_departure import DEPARTURE_COLUMNS
    content = _build_departure_txt([_dep_line()], footer_rooms=1, footer_persons=2)
    r = P.parse_departure(content)
    raw = r.records[0].raw
    assert len(raw) == len(DEPARTURE_COLUMNS) == 52
    for col in ("RESV_NAME_ID1", "RESORT", "MEMBERSHIP_TYPE", "MEMBERSHIP_LEVEL"):
        assert raw[col] == ""


def test_departure_membership_card_never_persisted():
    """會員卡號一律不落地（規格書 §13.1）。"""
    cells = _dep_line().split("\t")
    cells += [""] * 3 + ["VISA", "4111111111111111", "GOLD"]   # 補到含 MEMBERSHIP_CARD_NO
    content = _build_departure_txt(["\t".join(cells)], footer_rooms=0, footer_persons=0)
    r = P.parse_departure(content)
    for rec in r.records:
        assert rec.raw["MEMBERSHIP_CARD_NO"] == ""
        assert "4111111111111111" not in "".join(rec.raw.values())


def test_departure_missing_required_is_rejected():
    content = _build_departure_txt([_dep_line(ROOM="", NIGHTS="")], footer_rooms=0, footer_persons=0)
    r = P.parse_departure(content)
    assert r.row_count_rejected == 1
    assert len(r.records) == 0
    assert any(i.error_code == P.ERR_MISSING_REQUIRED for i in r.issues)


def test_departure_zero_room_row_is_kept_with_warning():
    """NO_OF_ROOMS=0 的列照常寫入，只發警示（規格書 §7.3）。"""
    content = _build_departure_txt(
        [_dep_line(), _dep_line(ROOM="0409", RESV_NAME_ID="30860051", NO_OF_ROOMS="0", ADULTS="0")],
        footer_rooms=1, footer_persons=2,
    )
    r = P.parse_departure(content)
    assert len(r.records) == 2
    assert r.stats["zero_room_rows"] == 1
    assert r.stats["sum_no_of_rooms"] == 1
    assert any(i.error_code == P.WARN_ZERO_ROOM and i.severity == "WARNING" for i in r.issues)


def test_departure_footer_not_in_records():
    content = _build_departure_txt([_dep_line()], footer_rooms=1, footer_persons=2)
    r = P.parse_departure(content)
    assert r.footer["SUMNO_OF_ROOMSPERREPORT"] == "1"
    assert all(rec.raw["DEPARTURE"] != "SUMBALANCEPERREPORT" for rec in r.records)


def test_departure_record_key_and_weak_key():
    content = _build_departure_txt([_dep_line(RESV_NAME_ID="")], footer_rooms=1, footer_persons=2)
    r = P.parse_departure(content)
    rec = r.records[0]
    assert rec.weak_key is True
    assert rec.record_key == rec.row_hash          # 缺 RESV_NAME_ID 改用 row_hash


# ══════════════════════════════════════════════════════════════════════════════
# History and Forecast
# ══════════════════════════════════════════════════════════════════════════════

def _hf_line(rec_type_desc="History", date="01-JAN-26", revenue="177939.05",
             no_rooms="51", inventory="69", ooo="0", calc_inv="69") -> str:
    from app.models.opera_revenue import HF_COLUMNS
    cells = [""] * len(HF_COLUMNS)
    idx = {c: i for i, c in enumerate(HF_COLUMNS)}
    cells[idx["REC_TYPE"]] = "A_STAT" if rec_type_desc == "History" else "B_FORE"
    cells[idx["REC_TYPE_DESC"]] = rec_type_desc
    cells[idx["REVENUE"]] = revenue
    cells[idx["NO_ROOMS"]] = no_rooms
    cells[idx["INVENTORY_ROOMS"]] = inventory
    cells[idx["CONSIDERED_DATE"]] = date
    cells[idx["CF_OOO_ROOMS"]] = ooo
    cells[idx["CF_CALC_INV_ROOMS"]] = calc_inv
    return "\t".join(cells)


def _build_hf_txt(data_lines: list[str], footer: dict[str, str]) -> bytes:
    from app.models.opera_revenue import HF_COLUMNS
    header = "\t".join(HF_COLUMNS)
    footer_block = "\t".join(footer.keys()) + "\n" + "\t".join(footer.values())
    return ("\n".join([header, *data_lines, footer_block]) + "\n").encode("utf-8")


def test_hf_history_and_forecast_are_separated():
    content = _build_hf_txt(
        [_hf_line("History"), _hf_line("Forecast", date="02-JAN-26", revenue="100", no_rooms="2", calc_inv="69")],
        footer={"SUMNO_ROOMSPERREPORT": "53", "SUMREVENUEPERREPORT": "178039.05",
                "SUMCALC_INVROOMSPERREPORT": "138", "SUMINVENTORY_ROOMSPERREPORT": "138"},
    )
    r = P.parse_history_forecast(content, property_code="SUMMER")
    assert r.stats["history_rows"] == 1
    assert r.stats["forecast_rows"] == 1
    # footer 是整份報表（History + Forecast）合計
    assert r.stats["sum_sold_rooms_all"] == 53
    assert r.stats["sum_sold_rooms"] == 51          # 分析只取 History
    assert P.reconcile_history_forecast(r)["ok"] is True


def test_hf_available_rooms_uses_calc_inv_not_inventory():
    """可售房晚必須用 CF_CALC_INV_ROOMS（= 實體 − OOO）。"""
    content = _build_hf_txt(
        [_hf_line(inventory="69", ooo="6", calc_inv="63")],
        footer={"SUMNO_ROOMSPERREPORT": "51", "SUMREVENUEPERREPORT": "177939.05",
                "SUMCALC_INVROOMSPERREPORT": "63", "SUMINVENTORY_ROOMSPERREPORT": "69"},
    )
    r = P.parse_history_forecast(content, property_code="SUMMER")
    fact = r.records[0].fact
    assert fact["available_rooms"] == 63
    assert fact["inventory_rooms"] == 69
    assert fact["ooo_rooms"] == 6


def test_hf_duplicate_same_type_same_date_is_error():
    """同批次同類型同日期重複必須報錯，不得靜默加總（規格書 §7.4）。"""
    content = _build_hf_txt(
        [_hf_line(), _hf_line()],
        footer={"SUMNO_ROOMSPERREPORT": "102"},
    )
    r = P.parse_history_forecast(content, property_code="SUMMER")
    assert len(r.records) == 1
    assert r.row_count_rejected == 1
    assert any(i.error_code == P.ERR_DUPLICATE_KEY for i in r.issues)


def test_hf_invalid_record_type_is_skipped():
    content = _build_hf_txt(
        [_hf_line(rec_type_desc="Budget")],
        footer={"SUMNO_ROOMSPERREPORT": "0"},
    )
    r = P.parse_history_forecast(content, property_code="SUMMER")
    assert len(r.records) == 0
    assert any(i.error_code == P.ERR_BAD_RECORD_TYPE for i in r.issues)


def test_hf_date_gap_warning():
    content = _build_hf_txt(
        [_hf_line(date="01-JAN-26"), _hf_line(date="04-JAN-26")],
        footer={"SUMNO_ROOMSPERREPORT": "102"},
    )
    r = P.parse_history_forecast(content, property_code="SUMMER")
    assert r.stats["date_gaps"] == 2                     # 01-02、01-03
    assert any(i.error_code == P.WARN_DATE_GAP for i in r.issues)


# ══════════════════════════════════════════════════════════════════════════════
# 真實檔案端到端對帳（規格書 §16.3）
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.skipif(not DEPARTURE_FILE.exists(), reason="缺少 fixtures/departure_all.txt")
def test_real_departure_reconciliation():
    r = P.parse_departure(DEPARTURE_FILE.read_bytes())
    assert len(r.records) == 35_334
    assert r.merged_pairs == 2_614
    assert r.row_count_rejected == 0
    assert r.property_code == "SUMMER"
    assert r.stats["sum_no_of_rooms"] == 22_411
    assert r.stats["sum_adults"] == 39_396
    assert r.stats["sum_nights"] == 67_838
    assert r.stats["sum_room_nights"] == 45_165
    assert r.stats["zero_room_rows"] == 12_923
    assert r.report_start_date == "2024-01-01"
    assert r.report_end_date == "2026-08-03"
    assert P.reconcile_departure(r)["ok"] is True


@pytest.mark.skipif(not HF_FILE.exists(), reason="缺少 fixtures/history_forecast.txt")
def test_real_history_forecast_reconciliation():
    r = P.parse_history_forecast(HF_FILE.read_bytes(), property_code="SUMMER")
    assert len(r.records) == 216
    assert r.stats["history_rows"] == 215
    assert r.stats["forecast_rows"] == 1
    assert r.stats["sum_sold_rooms_all"] == 10_059
    assert r.stats["sum_available_rooms_all"] == 14_891
    assert round(r.stats["sum_revenue_all"], 2) == 27_621_725.71
    assert P.reconcile_history_forecast(r)["ok"] is True
    # 整份報表 ADR / 住房率須與 OPERA footer 的 CF_* 欄位一致
    adr = r.stats["sum_revenue_all"] / r.stats["sum_sold_rooms_all"]
    occ = r.stats["sum_sold_rooms_all"] / r.stats["sum_available_rooms_all"]
    assert abs(adr - 2_745.97) < 0.01
    assert abs(occ * 100 - 67.55) < 0.01
