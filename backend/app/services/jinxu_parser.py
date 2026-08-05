"""
金旭 PMS xlsx 解析器（純函式，不碰資料庫）

規格書：docs/SPEC_jinxu_analytics.md §4、§5、§9.3、§9.4

本模組負責把金旭匯出的兩種 xlsx 轉成可寫入資料庫的結構，並在此階段完成
住客姓名遮罩——**原始姓名不會離開本模組**。

實測踩過的坑（改動前務必先看 docs/SPEC_jinxu_analytics.md §4、§5）：
  1. FCR02 是分組列印報表：52,310 列中只有 40,706 列是資料，混有 2,900 組
     重複表頭與 2,900 組分組小計。必須逐列分類，不可 pandas.read_excel。
  2. FCR02「日期」是營業日、「建檔時間」是系統時戳，實測 46.7% 兩者不同
     （夜稽跨日）。統計歸期一律用 business_date。
  3. 小計／總計列的金額在 B 欄且型別是字串 '-87,485.00'，資料列則在 H 欄且
     是 int。不可直接 float()。
  4. RV_detail「住宿資料」必須用 finditer 掃描，**不可 split(',')**——金額
     含千分位逗號，naive split 會把一段切成兩半。
  5. 「住宿資料」的 N 後綴不是必定存在（實測 14 段沒有），regex 要寫成選擇
     性群組，否則那 13 列整列解析失敗、夜次對帳差 14。
  6. 「住宿資料」括號內金額是「該段一晚的總額（房數×單價）」，不含晚數。
     段總額 = 金額 × 晚數。
  7. RV_detail 的 DATA 判定必須用狀態碼 regex，不可用「A 欄有值就是資料」，
     否則會把總計列與雜訊列吃進去。
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

from app.models.jinxu_ledger import (
    DEPOSIT_IN_CODES,
    DEPOSIT_OUT_CODES,
    FCR02_WIDTH,
    MEMO_ONLY_CODES,
    SHIFT_EXCLUDED_FROM_SHIFT_ANALYSIS,
    SIDE_REVENUE,
    classify_room_kind,
    split_subject,
    subject_side,
)
from app.models.jinxu_reservation import (
    RESV_WIDTH,
    STATUS_CANCEL,
    STATUS_DUMMY,
    STATUS_NO_SHOW,
    RESV_TYPE_GIT,
)

PARSER_VERSION = "1.0.0"

# ── 錯誤碼（規格書 §10）──────────────────────────────────────────────────────

ERR_MISSING_REQUIRED = "MISSING_REQUIRED"
ERR_BAD_DATE = "BAD_DATE"
ERR_DUPLICATE_KEY = "DUPLICATE_KEY"
ERR_UNKNOWN_ROW_TYPE = "UNKNOWN_ROW_TYPE"
WARN_ENTRY_UPDATED = "ENTRY_UPDATED"   # 業務鍵已存在且 row_hash 不同 → 覆蓋
# FCR02
ERR_BAD_CREATE_SEQ = "BAD_CREATE_SEQ"
ERR_BAD_AMOUNT = "BAD_AMOUNT"
ERR_SUBTOTAL_MISMATCH = "SUBTOTAL_MISMATCH"
ERR_GRANDTOTAL_MISMATCH = "GRANDTOTAL_MISMATCH"
WARN_UNKNOWN_SUBJECT = "UNKNOWN_SUBJECT"
INFO_DATE_MISMATCH = "DATE_MISMATCH"
INFO_REVENUE_NEGATIVE = "REVENUE_NEGATIVE"
WARN_SETTLEMENT_POSITIVE = "SETTLEMENT_POSITIVE"
WARN_UNKNOWN_ROOM_KIND = "UNKNOWN_ROOM_KIND"
INFO_LARGE_AMOUNT = "LARGE_AMOUNT"
# RESV_DETAIL
ERR_BAD_BOOKING_NO = "BAD_BOOKING_NO"
ERR_BAD_STATUS_CODE = "BAD_STATUS_CODE"
ERR_DEPARTURE_BEFORE_ARRIVAL = "DEPARTURE_BEFORE_ARRIVAL"
ERR_ROOM_NIGHTS_MISMATCH = "ROOM_NIGHTS_MISMATCH"
ERR_STAY_DETAIL_UNPARSABLE = "STAY_DETAIL_UNPARSABLE"
ERR_STAY_DETAIL_LEFTOVER = "STAY_DETAIL_LEFTOVER"
WARN_NIGHTS_MISMATCH = "NIGHTS_MISMATCH"       # J22：記錄不阻擋
WARN_STAY_DETAIL_EMPTY = "STAY_DETAIL_EMPTY"
INFO_MISSING_N_SUFFIX = "MISSING_N_SUFFIX"
WARN_UNKNOWN_ROOM_TYPE = "UNKNOWN_ROOM_TYPE"
WARN_UNKNOWN_STATUS_CODE = "UNKNOWN_STATUS_CODE"
WARN_MISSING_COMPANY = "MISSING_COMPANY"
INFO_DEPARTURE_OUT_OF_RANGE = "DEPARTURE_OUT_OF_RANGE"

SEVERITY_ERROR = "ERROR"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"


class JinxuParseError(Exception):
    """整批無法解析（如未知列類型、欄數不符）。"""


# ── 列類型 ────────────────────────────────────────────────────────────────────

ROW_DATA = "DATA"
ROW_HEADER = "HEADER"
ROW_FILTER = "FILTER"
ROW_TITLE = "TITLE"
ROW_PROPERTY = "PROPERTY"
ROW_SUBTOTAL = "SUBTOTAL"
ROW_GRANDTOTAL = "GRANDTOTAL"
ROW_BLANK = "BLANK"
ROW_SIGNATURE = "SIGNATURE"
ROW_NOISE = "NOISE"


# ── 共通正規化 ────────────────────────────────────────────────────────────────

def norm_text(value) -> str:
    """去頭尾空白 + 全形轉半形。None 一律回空字串。"""
    if value is None:
        return ""
    text = str(value)
    text = unicodedata.normalize("NFKC", text)
    return text.strip()


def to_iso_date(yyyymmdd: str) -> str:
    """'20260101' → '2026-01-01'。無法解析回空字串。"""
    text = norm_text(yyyymmdd)
    if len(text) != 8 or not text.isdigit():
        return ""
    try:
        date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    except ValueError:
        return ""
    return f"{text[:4]}-{text[4:6]}-{text[6:8]}"


def parse_amount(value) -> float | None:
    """資料列是 int；小計／總計列是字串 '-87,485.00'。無法解析回 None。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = norm_text(value).replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def row_hash(values: list[str]) -> str:
    """依欄位固定順序串接正規化值後取 SHA-256。"""
    joined = "\x1f".join(norm_text(v) for v in values)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


@dataclass
class ParseIssue:
    source_row_no: int
    field_name: str
    raw_value: str
    error_code: str
    error_message: str
    severity: str = SEVERITY_ERROR


# ══════════════════════════════════════════════════════════════════════════════
#  FCR02（客帳帳目明細表）
# ══════════════════════════════════════════════════════════════════════════════

FCR02_TITLE = "客帳帳目明細表"
_CREATE_SEQ_RE = re.compile(r"^\d{8}-\d{8}$")


def classify_fcr02_row(row: tuple) -> str:
    """FCR02 列類型判定（規格書 §4.1）。"""
    c0 = row[0] if len(row) > 0 else None
    c1 = row[1] if len(row) > 1 else None
    if c0 is None and all(x is None for x in row):
        return ROW_BLANK
    c0s = norm_text(c0)
    if c0s == FCR02_TITLE:
        return ROW_TITLE
    if c0s == "日期" and norm_text(c1) == "建檔時間":
        return ROW_HEADER
    if c0s == "日期":
        return ROW_FILTER
    if c0s == "合計":
        return ROW_SUBTOTAL
    if c0s == "總計":
        return ROW_GRANDTOTAL
    if c0s == "":
        # A 欄空但整列非空：報表尾端的「部門主管／單位主管／製表」簽核列
        return ROW_SIGNATURE
    return ROW_DATA


@dataclass
class LedgerRow:
    """一筆解析後的交易分錄。"""

    source_row_no: int
    raw_values: list[str]

    create_seq: str = ""
    row_hash: str = ""
    business_date: str = ""
    created_at_text: str = ""
    created_date: str = ""
    shift: str = ""
    is_manual_shift: int = 1
    operator_id: str = ""
    room_no: str = ""
    room_kind: str = ""
    folio_name: str = ""
    folio_seq: int | None = None
    folio_type: str = ""
    subject_code: str = ""
    subject_name: str = ""
    subject_side: str = SIDE_REVENUE
    amount: float = 0.0
    is_reversal: int = 0
    is_memo_only: int = 0
    booking_no: str = ""
    document_no: str = ""
    ar_code: str = ""
    transfer_no: str = ""
    remark: str = ""          # J17：儲存但全站不顯示


@dataclass
class Fcr02ParseResult:
    rows: list[LedgerRow] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)
    row_counts: dict[str, int] = field(default_factory=dict)
    subtotals: list[dict] = field(default_factory=list)
    grand_total: float | None = None
    computed_total: float = 0.0
    report_start_date: str = ""
    report_end_date: str = ""
    printed_at: str = ""
    total_source_rows: int = 0


_FOLIO_SEQ_RE = re.compile(r"^(\d+)\s*-")


def _parse_folio_seq(folio_name: str) -> int | None:
    m = _FOLIO_SEQ_RE.match(folio_name or "")
    return int(m.group(1)) if m else None


def parse_fcr02(rows: list[tuple], *, large_amount_threshold: float = 100000.0) -> Fcr02ParseResult:
    """解析 FCR02 客帳帳目明細表。

    rows 為 openpyxl read-only 逐列 iterate 的結果（1-based 列號 = index + 1）。
    """
    res = Fcr02ParseResult()
    res.total_source_rows = len(rows)
    counts: dict[str, int] = {}
    seen_seq: set[str] = set()

    # 目前分組的科目與累計金額（用來與「合計」列比對）
    group_subject = ""
    group_sum = 0.0
    group_rows = 0

    for idx, raw in enumerate(rows):
        row_no = idx + 1
        row = tuple(raw) + (None,) * max(0, FCR02_WIDTH - len(raw))
        kind = classify_fcr02_row(row)
        counts[kind] = counts.get(kind, 0) + 1

        if kind == ROW_TITLE:
            # ('客帳帳目明細表', '印表日期', '2026/08/05', ...)
            res.printed_at = f"{norm_text(row[1])} {norm_text(row[2])}".strip()
            continue

        if kind == ROW_FILTER:
            # ('日期','20260101','～','20260805', '科目',... ,'印表時間','09:02:01')
            res.report_start_date = to_iso_date(row[1])
            res.report_end_date = to_iso_date(row[3])
            for i in range(FCR02_WIDTH - 1):
                if norm_text(row[i]) == "印表時間":
                    res.printed_at = f"{res.printed_at} {norm_text(row[i + 1])}".strip()
                    break
            continue

        if kind == ROW_SUBTOTAL:
            amt = parse_amount(row[1])
            res.subtotals.append({
                "source_row_no": row_no,
                "subject_code": group_subject,
                "reported": amt,
                "computed": round(group_sum, 2),
                "row_count": group_rows,
                "matched": amt is not None and abs(amt - group_sum) < 0.01,
            })
            group_subject, group_sum, group_rows = "", 0.0, 0
            continue

        if kind == ROW_GRANDTOTAL:
            res.grand_total = parse_amount(row[1])
            continue

        if kind in (ROW_HEADER, ROW_BLANK, ROW_SIGNATURE):
            continue

        # ── DATA ──────────────────────────────────────────────────────────────
        values = [norm_text(row[i]) for i in range(FCR02_WIDTH)]
        item = LedgerRow(source_row_no=row_no, raw_values=values)
        item.row_hash = row_hash(values)

        # 建檔時間（業務唯一鍵）
        seq = values[1]
        if not _CREATE_SEQ_RE.match(seq):
            res.issues.append(ParseIssue(
                row_no, "建檔時間", seq, ERR_BAD_CREATE_SEQ,
                "建檔時間格式不符 YYYYMMDD-HHMMSSNN（8碼+8碼）", SEVERITY_ERROR))
            continue
        if seq in seen_seq:
            res.issues.append(ParseIssue(
                row_no, "建檔時間", seq, ERR_DUPLICATE_KEY,
                "同一檔案內建檔時間重複", SEVERITY_ERROR))
            continue
        seen_seq.add(seq)
        item.create_seq = seq
        item.created_at_text = seq
        item.created_date = to_iso_date(seq[:8])

        # 營業日（統計歸期唯一依據）
        item.business_date = to_iso_date(values[0])
        if not item.business_date:
            res.issues.append(ParseIssue(
                row_no, "日期", values[0], ERR_BAD_DATE, "日期無法解析", SEVERITY_ERROR))
            continue
        if item.business_date != item.created_date:
            res.issues.append(ParseIssue(
                row_no, "日期", f"{item.business_date} vs {item.created_date}",
                INFO_DATE_MISMATCH, "營業日與建檔日不同（夜稽跨日，正常現象）",
                SEVERITY_INFO))

        # 金額
        amt = parse_amount(row[7])
        if amt is None:
            res.issues.append(ParseIssue(
                row_no, "金額", values[7], ERR_BAD_AMOUNT, "金額無法解析", SEVERITY_ERROR))
            continue
        item.amount = amt

        # 科目
        item.subject_code, item.subject_name = split_subject(values[6])
        if not item.subject_code:
            res.issues.append(ParseIssue(
                row_no, "科目", values[6], ERR_MISSING_REQUIRED, "科目無法解析", SEVERITY_ERROR))
            continue
        item.subject_side = subject_side(item.subject_code)
        item.is_memo_only = 1 if item.subject_code in MEMO_ONLY_CODES else 0

        # 沖帳判定（§11.2）：收入類 + 負值。**不可只靠備註字串**
        item.is_reversal = 1 if (item.subject_side == SIDE_REVENUE and amt < 0) else 0
        if item.is_reversal:
            res.issues.append(ParseIssue(
                row_no, "金額", str(amt), INFO_REVENUE_NEGATIVE,
                "收入類科目金額為負（沖帳）", SEVERITY_INFO))
        if item.subject_side != SIDE_REVENUE and amt > 0:
            res.issues.append(ParseIssue(
                row_no, "金額", str(amt), WARN_SETTLEMENT_POSITIVE,
                "抵充類科目金額為正（可能是退款沖銷）", SEVERITY_WARNING))
        if abs(amt) > large_amount_threshold:
            res.issues.append(ParseIssue(
                row_no, "金額", str(amt), INFO_LARGE_AMOUNT, "大額交易", SEVERITY_INFO))

        # 班別（J16：只有 N 排除於班別分析；X/Y 是真實收入，金額統計全數保留）
        item.shift = values[2].upper()
        item.is_manual_shift = 0 if item.shift in SHIFT_EXCLUDED_FROM_SHIFT_ANALYSIS else 1

        # 操作員與房號（正規化：實測大小寫混用）
        item.operator_id = values[3].upper()
        item.room_no = values[4].upper()
        item.room_kind = classify_room_kind(item.room_no)
        if item.room_kind != "GUEST":
            res.issues.append(ParseIssue(
                row_no, "房號", item.room_no, WARN_UNKNOWN_ROOM_KIND,
                "非客房房號（J24：進 DB，客房統計排除）", SEVERITY_WARNING))

        item.folio_name = values[5]
        item.folio_seq = _parse_folio_seq(values[5])
        item.folio_type = values[13]
        item.document_no = values[8]
        item.ar_code = values[9]
        item.remark = values[10]      # J17：儲存但全站不顯示
        item.transfer_no = values[11]
        item.booking_no = values[12]

        res.rows.append(item)
        res.computed_total += amt

        if not group_subject:
            group_subject = item.subject_code
        group_sum += amt
        group_rows += 1

    res.row_counts = counts
    res.computed_total = round(res.computed_total, 2)
    return res


# ══════════════════════════════════════════════════════════════════════════════
#  RV_detail（訂房狀況表）
# ══════════════════════════════════════════════════════════════════════════════

RESV_TITLE = "訂房狀況表"
_STATUS_RE = re.compile(r"^[A-Z]{4}-[A-Z]{2}$")

# 住宿資料段：{房型} * {房數} * {晚數}({金額}[N])
# ⚠️ N 後綴是選擇性群組——實測 14 段沒有 N（規格書 §5.3 坑 2）
_STAY_SEG_RE = re.compile(
    r"([A-Z]+)\s*\*\s*(\d+)\s*\*\s*(\d+)\s*\(\s*([\d,]+)\s*(N?)\s*\)"
)

# 姓名遮罩：稱謂一律保留
_NAME_TITLES = {"MR", "MS", "MRS", "MISS", "DR", "PROF"}
_CJK_RE = re.compile(r"[一-鿿]")

# J14：非人名資料判定（排除於回訪分析，訂房統計仍計入）
_PLACEHOLDER_EXACT = {"OTHERS", "OTHER", "N/A", "NA", "UNKNOWN"}
_PLACEHOLDER_KEYWORDS = (
    "公司", "有限", "股份", "企業", "旅行社", "工作室", "商行", "事務所",
)
_PLACEHOLDER_PREFIXES = ("訂房",)


def is_placeholder_name(raw_name: str) -> bool:
    """判定登記名稱是否為非人名資料（J14）。

    實測命中：OTHERS(37)、源點科技股份有限公司、登峰國際旅行社股份有限公司、
    裕利公司、曦慕投資有限公司、英商奧雅納工程顧問有限公司台北分公司、
    訂房壓房(2)、訂房保留房(2)。
    """
    text = norm_text(raw_name)
    if not text:
        return True
    if text.upper() in _PLACEHOLDER_EXACT:
        return True
    if any(text.startswith(p) for p in _PLACEHOLDER_PREFIXES):
        return True
    return any(kw in text for kw in _PLACEHOLDER_KEYWORDS)


def mask_guest_name(raw_name: str) -> str:
    """遮罩住客姓名（規格書 §15.2）。

    規則：第一個 token（姓氏）與稱謂（MR/MS/MRS…）保留原文；其餘每個 token
    只留第一個字元，其後以 * 取代。中文 token 同規則（保留第一個字）。

        'CAI MS PEI JYUN'          → 'CAI MS P** J***'
        'CHANG MS WEN YING 張玟瑛'  → 'CHANG MS W** Y*** 張**'
        'CHENG/HSIN YU'            → 'CHENG/H*** Y*'

    ⚠️ 遮罩後不可還原。原文不得回傳、不得寫入任何欄位或 log。
    """
    text = norm_text(raw_name)
    if not text:
        return ""

    # 以空白與斜線切分，保留分隔符以便還原排版
    parts = re.split(r"([\s/]+)", text)
    out: list[str] = []
    token_index = 0
    for part in parts:
        if not part or re.fullmatch(r"[\s/]+", part):
            out.append(part)
            continue
        if token_index == 0 or part.upper() in _NAME_TITLES:
            out.append(part)
        else:
            out.append(part[0] + "*" * (len(part) - 1))
        token_index += 1
    return "".join(out)


def guest_identity_hash(raw_name: str, property_code: str = "") -> str:
    """住客識別鍵（J13，規格書 §15.2.1）。

    業主指定規則：**只做 .strip()，字串完全一致才視為同一人。**
    不轉大小寫、不去稱謂、不去中間名、不翻轉斜線格式、不分離中英。

    ⚠️ 開發端不得自行加任何正規化。改規則需重新匯入全部原始檔
       （Portal DB 內不存姓名原文，無法重算）。
    """
    text = (raw_name or "").strip()
    if not text:
        return ""
    return hashlib.sha256(f"{property_code}|{text}".encode("utf-8")).hexdigest()


def classify_resv_row(row: tuple) -> str:
    """RV_detail 列類型判定（規格書 §5.1）。

    ⚠️ DATA 必須用狀態碼 regex 判定，不可用「A 欄有值就是資料」。
    """
    c0 = row[0] if len(row) > 0 else None
    if c0 is None and all(x is None for x in row):
        return ROW_BLANK
    c0s = norm_text(c0)
    if c0s == RESV_TITLE:
        return ROW_TITLE
    if c0s == "日期":
        return ROW_FILTER
    if c0s == "訂房/登記狀況":
        return ROW_HEADER
    if c0s == "合計":
        return ROW_GRANDTOTAL
    if c0s == "":
        # 印表資訊列、房型統計殘片（規格書 §5.7：內容不完整，一律丟棄）
        return ROW_NOISE
    if _STATUS_RE.match(c0s):
        return ROW_DATA
    return ROW_PROPERTY   # 第 1 列的飯店名稱（如「瀚寓酒店」）


@dataclass
class StaySegment:
    seq_no: int
    room_type_code: str
    rooms: int
    nights: int
    amount_per_night: float
    unit_rate: float
    room_nights: int
    segment_amount: float
    has_n_suffix: int
    raw_segment: str


@dataclass
class ReservationRow:
    source_row_no: int
    raw_values: list[str]

    booking_no: str = ""
    row_hash: str = ""
    status_code: str = ""
    status_main: str = ""
    status_kind: str = ""
    is_cancelled: int = 0
    is_dummy: int = 0
    is_no_show: int = 0
    arrival_date: str = ""
    departure_date: str = ""
    nights: int = 0
    billable_nights: int = 0
    is_day_use: int = 0
    guest_name_masked: str = ""
    guest_identity_hash: str = ""
    guest_is_placeholder: int = 0
    guest_has_cjk: int = 0
    company_name: str = ""
    rate_code: str = ""
    source_name: str = ""
    resv_type: str = ""
    is_group: int = 0
    stay_segment_count: int = 0
    total_room_nights: int = 0
    total_quoted_amount: float = 0.0
    room_type_codes: str = ""
    has_nights_mismatch: int = 0
    segments: list[StaySegment] = field(default_factory=list)


@dataclass
class ResvParseResult:
    rows: list[ReservationRow] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)
    row_counts: dict[str, int] = field(default_factory=dict)
    reported_room_nights: int | None = None    # 合計列「夜次」
    reported_rooms_text: str = ""              # 合計列「間」（J11：不對帳、不顯示）
    computed_room_nights: int = 0
    segment_count: int = 0
    property_name: str = ""
    report_start_date: str = ""
    report_end_date: str = ""
    printed_at: str = ""
    total_source_rows: int = 0


_NIGHTS_TEXT_RE = re.compile(r"(\d+)")


def parse_stay_detail(text: str) -> tuple[list[StaySegment], str]:
    """拆解「住宿資料」打包欄位。

    回傳 (段列表, 殘餘字元)。殘餘非空代表有無法解析的內容。

    ⚠️ 必須用 finditer，不可 split(',')（金額含千分位逗號）。
    """
    raw = norm_text(text)
    if not raw:
        return [], ""

    segments: list[StaySegment] = []
    for i, m in enumerate(_STAY_SEG_RE.finditer(raw), start=1):
        code = m.group(1)
        rooms = int(m.group(2))
        nights = int(m.group(3))
        amount_per_night = float(m.group(4).replace(",", ""))
        has_n = 1 if m.group(5) else 0
        # 括號內金額 = 該段一晚的總額（房數 × 單價），不含晚數
        unit_rate = round(amount_per_night / rooms, 2) if rooms else 0.0
        segments.append(StaySegment(
            seq_no=i,
            room_type_code=code,
            rooms=rooms,
            nights=nights,
            amount_per_night=amount_per_night,
            unit_rate=unit_rate,
            room_nights=rooms * nights,
            segment_amount=round(amount_per_night * nights, 2),
            has_n_suffix=has_n,
            raw_segment=m.group(0),
        ))

    leftover = re.sub(r"[,\s]", "", _STAY_SEG_RE.sub("", raw))
    return segments, leftover


def parse_resv_detail(rows: list[tuple], *, property_code: str = "") -> ResvParseResult:
    """解析 RV_detail 訂房狀況表。"""
    res = ResvParseResult()
    res.total_source_rows = len(rows)
    counts: dict[str, int] = {}
    seen_booking: set[str] = set()

    for idx, raw in enumerate(rows):
        row_no = idx + 1
        row = tuple(raw) + (None,) * max(0, RESV_WIDTH - len(raw))
        kind = classify_resv_row(row)
        counts[kind] = counts.get(kind, 0) + 1

        if kind == ROW_PROPERTY:
            if not res.property_name:
                res.property_name = norm_text(row[0])
            continue

        if kind == ROW_FILTER:
            res.report_start_date = to_iso_date(row[1])
            res.report_end_date = to_iso_date(row[3])
            continue

        if kind == ROW_NOISE:
            for cell in row:
                s = norm_text(cell)
                if s.startswith("印表日期"):
                    res.printed_at = s
            continue

        if kind == ROW_GRANDTOTAL:
            # ('合計', '9484間', '26663夜次', ...)
            res.reported_rooms_text = norm_text(row[1])
            m = _NIGHTS_TEXT_RE.search(norm_text(row[2]))
            res.reported_room_nights = int(m.group(1)) if m else None
            continue

        if kind in (ROW_TITLE, ROW_HEADER, ROW_BLANK):
            continue

        if kind != ROW_DATA:
            raise JinxuParseError(f"第 {row_no} 列為未知列類型：{row[:3]!r}")

        # ── DATA ──────────────────────────────────────────────────────────────
        values = [norm_text(row[i]) for i in range(RESV_WIDTH)]
        item = ReservationRow(source_row_no=row_no, raw_values=list(values))

        booking_no = values[3]
        if not booking_no:
            res.issues.append(ParseIssue(
                row_no, "訂房號碼", booking_no, ERR_BAD_BOOKING_NO,
                "訂房號碼為空", SEVERITY_ERROR))
            continue
        if booking_no in seen_booking:
            res.issues.append(ParseIssue(
                row_no, "訂房號碼", booking_no, ERR_DUPLICATE_KEY,
                "同一檔案內訂房號碼重複", SEVERITY_ERROR))
            continue
        seen_booking.add(booking_no)
        item.booking_no = booking_no

        # 狀態
        status = values[0].upper()
        item.status_code = status
        item.status_main = status[:4]
        item.status_kind = status[5:] if len(status) > 5 else ""
        item.is_cancelled = 1 if item.status_main == STATUS_CANCEL else 0
        item.is_dummy = 1 if item.status_main == STATUS_DUMMY else 0
        item.is_no_show = 1 if item.status_main == STATUS_NO_SHOW else 0

        # 日期
        item.arrival_date = to_iso_date(values[1])
        item.departure_date = to_iso_date(values[2])
        if not item.arrival_date or not item.departure_date:
            res.issues.append(ParseIssue(
                row_no, "到達日期/退房日期", f"{values[1]}/{values[2]}",
                ERR_BAD_DATE, "日期無法解析", SEVERITY_ERROR))
            continue
        a = date.fromisoformat(item.arrival_date)
        d = date.fromisoformat(item.departure_date)
        if d < a:
            res.issues.append(ParseIssue(
                row_no, "退房日期", item.departure_date, ERR_DEPARTURE_BEFORE_ARRIVAL,
                "退房日早於到達日", SEVERITY_ERROR))
            continue
        item.nights = (d - a).days
        # J27：Day Use 的日期差為 0，但實際收一晚房租 → 另存可計費晚數
        item.billable_nights = max(item.nights, 1)
        item.is_day_use = 1 if item.nights == 0 else 0

        # ── 住客姓名（⚠️ 個資，遮罩在此完成，原文不離開本函式）─────────────
        guest_raw = values[4]
        item.guest_name_masked = mask_guest_name(guest_raw)
        item.guest_is_placeholder = 1 if is_placeholder_name(guest_raw) else 0
        item.guest_has_cjk = 1 if _CJK_RE.search(guest_raw) else 0
        # J14：非人名資料不產生識別鍵，避免 37 筆 OTHERS 被算成同一位常客
        item.guest_identity_hash = (
            "" if item.guest_is_placeholder
            else guest_identity_hash(guest_raw, property_code)
        )
        # raw_values 內的姓名同樣換成遮罩後版本（原始層不存原文）
        item.raw_values[4] = item.guest_name_masked
        del guest_raw

        # 通路（J18/J19：照原值，不合併、不特別處理 SiteMinder）
        item.company_name = values[5]
        item.rate_code = values[6]
        item.source_name = values[7]
        item.resv_type = values[8].upper()
        item.is_group = 1 if item.resv_type == RESV_TYPE_GIT else 0
        if not item.company_name:
            res.issues.append(ParseIssue(
                row_no, "合約/訂房公司", "", WARN_MISSING_COMPANY,
                "訂房公司為空，通路統計歸『未指定』", SEVERITY_WARNING))

        # ── 住宿資料拆段 ─────────────────────────────────────────────────────
        stay_text = values[9]
        segments, leftover = parse_stay_detail(stay_text)
        if stay_text and not segments:
            res.issues.append(ParseIssue(
                row_no, "住宿資料", stay_text[:200], ERR_STAY_DETAIL_UNPARSABLE,
                "住宿資料有值但無法解析出任何段", SEVERITY_ERROR))
            continue
        if leftover:
            res.issues.append(ParseIssue(
                row_no, "住宿資料", leftover[:200], ERR_STAY_DETAIL_LEFTOVER,
                f"住宿資料拆段後仍有殘餘字元：{leftover[:80]}", SEVERITY_ERROR))
            continue
        if not stay_text:
            res.issues.append(ParseIssue(
                row_no, "住宿資料", "", WARN_STAY_DETAIL_EMPTY,
                "住宿資料為空，彙總欄填 0", SEVERITY_WARNING))

        item.segments = segments
        item.stay_segment_count = len(segments)
        item.total_room_nights = sum(s.room_nights for s in segments)
        item.total_quoted_amount = round(sum(s.segment_amount for s in segments), 2)
        seen_codes: list[str] = []
        for s in segments:
            if s.room_type_code not in seen_codes:
                seen_codes.append(s.room_type_code)
            if not s.has_n_suffix:
                res.issues.append(ParseIssue(
                    row_no, "住宿資料", s.raw_segment, INFO_MISSING_N_SUFFIX,
                    "段缺少 N 後綴（不影響計算）", SEVERITY_INFO))
        item.room_type_codes = ",".join(seen_codes)

        # J22：段晚數加總 != 住宿天數 → 記錄但**不阻擋**（實測 241 筆／2.8%）
        if segments and item.nights > 0:
            seg_nights = sum(s.nights for s in segments)
            if seg_nights != item.nights:
                item.has_nights_mismatch = 1
                res.issues.append(ParseIssue(
                    row_no, "住宿資料", f"段晚數 {seg_nights} vs 住宿天數 {item.nights}",
                    WARN_NIGHTS_MISMATCH,
                    "段晚數加總與住宿天數不符（記錄不阻擋）", SEVERITY_WARNING))

        if res.report_end_date and item.departure_date > res.report_end_date:
            res.issues.append(ParseIssue(
                row_no, "退房日期", item.departure_date, INFO_DEPARTURE_OUT_OF_RANGE,
                "退房日超出報表區間（期間統計需切齊）", SEVERITY_INFO))

        item.row_hash = row_hash(item.raw_values)
        res.rows.append(item)
        res.computed_room_nights += item.total_room_nights
        res.segment_count += item.stay_segment_count

    res.row_counts = counts
    return res
