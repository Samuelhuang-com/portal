"""
OPERA TXT 解析器（純函式，不碰資料庫）

規格書：docs/SPEC_opera_analytics.md §3、§7.3、§7.4、§13.2

本模組負責把 OPERA 匯出的兩種 TXT 轉成可寫入資料庫的結構，並在此階段完成
住客姓名遮罩——原始姓名與會員卡號**不會**離開本模組。

實測踩過的坑（改動前務必先看 docs/SPEC_opera_analytics.md §3）：
  1. Departure 表頭 52 欄，資料列只有 45 欄 → 一律以「位置」取值，超出長度回傳 ""。
  2. PROF_ATTACHED 內含換行 → 43 欄列 + 3 欄列必須合併成 45 欄。
  3. 兩種檔案的 footer 都是「欄名列 + 數值列」兩行，不得寫入事實表。
  4. 日期格式 DD-MON-YY 用自建月份對照表解析，**不使用 strptime('%b')**，
     因為 %b 在中文 Windows 上會依 locale 失敗。
  5. 可售房晚一律取 CF_CALC_INV_ROOMS，不可用 INVENTORY_ROOMS。
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

from app.models.opera_departure import (
    DEPARTURE_COLUMNS,
    DEPARTURE_FOOTER_KEYS,
    DEPARTURE_MERGED_WIDTH,
    DEPARTURE_SENSITIVE_COLUMNS,
)
from app.models.opera_revenue import (
    HF_COLUMNS,
    HF_FOOTER_KEYS,
    HF_VALID_RECORD_TYPES,
    HF_WIDTH,
    RECORD_TYPE_HISTORY,
)

PARSER_VERSION = "1.0.0"

# ── 錯誤碼 ────────────────────────────────────────────────────────────────────
ERR_MISSING_REQUIRED = "MISSING_REQUIRED"
ERR_BAD_DATE = "BAD_DATE"
ERR_BAD_WIDTH = "BAD_WIDTH"
ERR_BAD_RECORD_TYPE = "BAD_RECORD_TYPE"
ERR_DUPLICATE_KEY = "DUPLICATE_KEY"
WARN_ZERO_ROOM = "ZERO_ROOM"
WARN_OVERSOLD = "OVERSOLD"
WARN_NEGATIVE_REVENUE = "NEGATIVE_REVENUE"
WARN_NEGATIVE_ROOMS = "NEGATIVE_ROOMS"
WARN_DATE_GAP = "DATE_GAP"

_MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}
_DATE_MON_RE = re.compile(r"^(\d{1,2})-([A-Za-z]{3})-(\d{2}|\d{4})$")   # 01-JAN-26
_DATE_NUM_RE = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{2}|\d{4})")        # 29-12-23（可帶後綴星期）
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})")
_CJK_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
_PURGED_RE = re.compile(r"^\*?\s*purged", re.IGNORECASE)

# guest_name_id 的「無效值」——OPERA 對已清除住客填 -100
_INVALID_GUEST_IDS = {"", "-100", "0"}


# ══════════════════════════════════════════════════════════════════════════════
# 基礎工具
# ══════════════════════════════════════════════════════════════════════════════

def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def detect_encoding(content: bytes) -> tuple[str, str]:
    """回傳 (decoded_text, encoding_name)。OPERA 匯出實測為 ASCII/UTF-8。"""
    for enc in ("utf-8-sig", "utf-8", "cp950", "big5", "latin-1"):
        try:
            return content.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace"), "utf-8(replace)"


def normalize_cell(value: str) -> str:
    """欄位正規化：NFKC（全形→半形）+ 去頭尾空白 + 壓縮連續空白。"""
    if not value:
        return ""
    v = unicodedata.normalize("NFKC", value).strip()
    return re.sub(r"[ \t]+", " ", v)


def parse_opera_date(value: str) -> str | None:
    """OPERA 日期 → ISO `YYYY-MM-DD`。無法解析回傳 None。

    OPERA 同一份報表混用兩種格式（實測確認，規格書 §3.7）：
      * `DD-MON-YY`：DEPARTURE、CONSIDERED_DATE          例：`01-JAN-26`
      * `DD-MM-YY` ：ARRIVAL、CHAR_DEPDATE、CHAR_ARRIVAL 例：`29-12-23`
    兩種都必須支援，否則 ARRIVAL 會被整批判為錯誤。
    （驗證：(DEPARTURE − ARRIVAL) == NIGHTS 於實測資料 100% 成立。）

    刻意不使用 datetime.strptime('%d-%b-%y')：%b 依賴 locale，
    在中文 Windows 上會直接拋 ValueError。
    """
    if not value:
        return None
    v = value.strip()

    m = _DATE_MON_RE.match(v)
    if m:
        day, mon, year = m.group(1), m.group(2).upper(), m.group(3)
        month = _MONTHS.get(mon)
        if not month:
            return None
        return _build_iso(day, month, year)

    m = _DATE_NUM_RE.match(v)
    if m:
        day, mon, year = m.group(1), m.group(2), m.group(3)
        return _build_iso(day, int(mon), year)

    return None


def _build_iso(day: str, month: int, year: str) -> str | None:
    y = int(year)
    if len(year) == 2:
        y = 2000 + y if y < 70 else 1900 + y
    try:
        d = int(day)
    except ValueError:
        return None
    if not (1 <= d <= 31 and 1 <= month <= 12):
        return None
    return f"{y:04d}-{month:02d}-{d:02d}"


def parse_time_minutes(value: str) -> int | None:
    """`12:03` → 723。"""
    if not value:
        return None
    m = _TIME_RE.match(value.strip())
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return None
    return h * 60 + mi


def to_int(value: str, default: int = 0) -> int:
    if value is None:
        return default
    v = value.strip().replace(",", "")
    if not v:
        return default
    try:
        return int(float(v))
    except ValueError:
        return default


def to_float(value: str, default: float = 0.0) -> float:
    if value is None:
        return default
    v = value.strip().replace(",", "")
    if not v:
        return default
    try:
        return float(v)
    except ValueError:
        return default


def compute_row_hash(columns: list[str], values: dict[str, str]) -> str:
    """依欄位固定順序串接正規化值後取 SHA-256（規格書 §6.2）。"""
    parts = [f"{c}={normalize_cell(values.get(c, ''))}" for c in columns]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════
# 住客姓名遮罩與識別 hash（規格書 §13.2）
# ══════════════════════════════════════════════════════════════════════════════

PURGED_LABEL = "（已清除）"
EMPTY_LABEL = "—"


def is_purged_guest(raw_name: str) -> bool:
    return bool(_PURGED_RE.match((raw_name or "").strip()))


def _mask_token(token: str) -> str:
    """英文單字：保留首字母，其餘以 * 取代。"""
    if len(token) <= 1:
        return token
    return token[0] + "*" * (len(token) - 1)


def mask_guest_name(raw_name: str) -> str:
    """把住客姓名轉成可安全落地的遮罩版本。

    中文 2 字   ：陳明             → 陳*
    中文 3 字以上：王小明           → 王*明 / 歐陽小明 → 歐**明
    OPERA 英文  ：LIN,YU CHENG,Mr. → LIN,Y* C****,Mr.（姓氏與稱謂保留）
    已清除      ：Purged-Individual→ （已清除）
    空值        ：                 → —
    """
    name = (raw_name or "").strip()
    if not name:
        return EMPTY_LABEL
    if is_purged_guest(name):
        return PURGED_LABEL

    if _CJK_RE.search(name):
        chars = name.replace(" ", "")
        if len(chars) <= 1:
            return chars
        if len(chars) == 2:
            return chars[0] + "*"
        return chars[0] + "*" * (len(chars) - 2) + chars[-1]

    if "," in name:
        parts = [p.strip() for p in name.split(",")]
        surname = parts[0]
        masked = [surname]
        # 中間段（名字）遮罩；最後一段若像稱謂（Mr./Ms./Dr. 等）則保留
        for idx, part in enumerate(parts[1:], start=1):
            is_last = idx == len(parts) - 1
            if is_last and len(part) <= 5 and part.endswith("."):
                masked.append(part)
            else:
                masked.append(" ".join(_mask_token(t) for t in part.split()))
        return ",".join(masked)

    return " ".join(_mask_token(t) for t in name.split())


def compute_guest_identity_hash(
    property_code: str, raw_name: str, guest_name_id: str
) -> str | None:
    """住客識別 hash；已清除住客一律回傳 None（規格書 §5.5）。"""
    name = (raw_name or "").strip()
    if not name or is_purged_guest(name):
        return None
    gid = (guest_name_id or "").strip()
    if gid in _INVALID_GUEST_IDS:
        gid = ""
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", name)).upper().strip()
    payload = f"{property_code}|{normalized}|{gid}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def clean_guest_name_id(value: str) -> str | None:
    v = (value or "").strip()
    return None if v in _INVALID_GUEST_IDS else v


# ══════════════════════════════════════════════════════════════════════════════
# 解析結果容器
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ParseIssue:
    source_row_no: int
    field_name: str
    raw_value: str
    error_code: str
    error_message: str
    severity: str = "ERROR"

    def as_dict(self) -> dict:
        return {
            "source_row_no": self.source_row_no,
            "field_name": self.field_name,
            "raw_value": self.raw_value[:500],
            "error_code": self.error_code,
            "error_message": self.error_message,
            "severity": self.severity,
        }


@dataclass
class ParsedRecord:
    """單筆解析結果：raw（原始欄名→值）+ fact（標準化欄位）"""
    source_row_no: int
    source_row_no_end: int
    raw: dict[str, str]
    fact: dict
    row_hash: str
    record_key: str
    weak_key: bool = False


@dataclass
class ParseResult:
    source_type: str
    property_code: str = ""
    records: list[ParsedRecord] = field(default_factory=list)
    footer: dict[str, str] = field(default_factory=dict)
    issues: list[ParseIssue] = field(default_factory=list)
    row_count_source: int = 0
    row_count_rejected: int = 0
    merged_pairs: int = 0
    report_start_date: str = ""
    report_end_date: str = ""
    stats: dict = field(default_factory=dict)

    @property
    def has_fatal(self) -> bool:
        return any(i.severity == "ERROR" for i in self.issues)


# ══════════════════════════════════════════════════════════════════════════════
# 共用：切行、取 footer
# ══════════════════════════════════════════════════════════════════════════════

def _split_lines(text: str) -> list[str]:
    return [ln.rstrip("\r") for ln in text.split("\n")]


def _extract_footer(
    body: list[tuple[int, str]], first_footer_key: str, footer_keys: list[str]
) -> tuple[list[tuple[int, str]], dict[str, str]]:
    """從尾端切出「欄名列 + 數值列」的兩行 footer（規格書 §3.3）。

    body 為 (實體列號, 行內容) 的序列。回傳 (資料列, footer dict)。
    """
    for idx in range(len(body) - 1, -1, -1):
        cells = body[idx][1].split("\t")
        if cells and cells[0].strip() == first_footer_key:
            keys = [c.strip() for c in cells]
            values: list[str] = []
            if idx + 1 < len(body):
                values = [c.strip() for c in body[idx + 1][1].split("\t")]
            footer = {
                k: (values[i] if i < len(values) else "")
                for i, k in enumerate(keys)
                if k
            }
            return body[:idx], footer
    # 找不到 footer → 用已知欄名再掃一次（防欄位順序變動）
    for idx in range(len(body) - 1, -1, -1):
        cells = [c.strip() for c in body[idx][1].split("\t")]
        if cells and set(cells) & set(footer_keys):
            values = [c.strip() for c in body[idx + 1][1].split("\t")] if idx + 1 < len(body) else []
            footer = {k: (values[i] if i < len(values) else "") for i, k in enumerate(cells) if k}
            return body[:idx], footer
    return body, {}


# ══════════════════════════════════════════════════════════════════════════════
# Departure All
# ══════════════════════════════════════════════════════════════════════════════

_DEP_REQUIRED = ["DEPARTURE", "ARRIVAL", "NIGHTS", "ROOM"]


def _merge_departure_continuations(
    body: list[tuple[int, str]]
) -> tuple[list[tuple[int, int, list[str]]], int]:
    """合併 PROF_ATTACHED 換行造成的續行列（規格書 §3.2）。

    43 欄列 + 緊接的 3 欄列 → 45 欄列。
    回傳 [(起始列號, 結束列號, cells)] 與合併對數。
    """
    merged: list[tuple[int, int, list[str]]] = []
    pairs = 0
    i = 0
    while i < len(body):
        row_no, line = body[i]
        cells = line.split("\t")
        end_no = row_no
        if len(cells) == DEPARTURE_MERGED_WIDTH - 2 and i + 1 < len(body):
            nxt_no, nxt_line = body[i + 1]
            nxt = nxt_line.split("\t")
            if len(nxt) == 3:
                cells = cells + [nxt[1], nxt[2]]
                cells[42] = f"{cells[42]}\n{nxt[0]}"
                end_no = nxt_no
                pairs += 1
                i += 1
        merged.append((row_no, end_no, cells))
        i += 1
    return merged, pairs


def parse_departure(content: bytes) -> ParseResult:
    text, _enc = detect_encoding(content)
    lines = _split_lines(text)
    result = ParseResult(source_type="DEPARTURE")

    if not lines or not lines[0].strip():
        result.issues.append(ParseIssue(1, "HEADER", "", ERR_BAD_WIDTH, "檔案為空或缺少表頭"))
        return result

    body = [(no, ln) for no, ln in enumerate(lines[1:], start=2) if ln.strip()]
    body, footer = _extract_footer(body, "SUMBALANCEPERREPORT", DEPARTURE_FOOTER_KEYS)
    result.footer = footer

    merged, pairs = _merge_departure_continuations(body)
    result.merged_pairs = pairs
    result.row_count_source = len(merged)

    seen_keys: dict[str, int] = {}
    dates: list[str] = []
    zero_room_count = 0
    sum_rooms = 0
    sum_persons = 0
    sum_room_nights = 0
    sum_nights = 0

    for start_no, end_no, cells in merged:
        if len(cells) != DEPARTURE_MERGED_WIDTH:
            result.issues.append(ParseIssue(
                start_no, "ROW", f"欄數={len(cells)}", ERR_BAD_WIDTH,
                f"合併後欄數為 {len(cells)}，預期 {DEPARTURE_MERGED_WIDTH}",
            ))
            result.row_count_rejected += 1
            continue

        # 位置對位；索引超出資料列長度時回傳 ""（規格書 §3.1）
        raw = {
            col: (cells[i] if i < len(cells) else "")
            for i, col in enumerate(DEPARTURE_COLUMNS)
        }
        # 敏感欄位一律不落地
        for col in DEPARTURE_SENSITIVE_COLUMNS:
            raw[col] = ""

        missing = [c for c in _DEP_REQUIRED if not raw.get(c, "").strip()]
        if missing:
            result.issues.append(ParseIssue(
                start_no, ",".join(missing), "", ERR_MISSING_REQUIRED,
                f"缺少必要欄位：{'、'.join(missing)}",
            ))
            result.row_count_rejected += 1
            continue

        dep_date = parse_opera_date(raw["DEPARTURE"])
        arr_date = parse_opera_date(raw["ARRIVAL"])
        if not dep_date or not arr_date:
            bad_field = "DEPARTURE" if not dep_date else "ARRIVAL"
            result.issues.append(ParseIssue(
                start_no, bad_field, raw[bad_field], ERR_BAD_DATE,
                f"{bad_field} 無法解析為日期（預期 DD-MON-YY）",
            ))
            result.row_count_rejected += 1
            continue

        property_code = normalize_cell(raw["RESORT1"]) or normalize_cell(raw["RESORT"])
        if property_code and not result.property_code:
            result.property_code = property_code

        guest_raw = raw["GUEST_NAME"]
        masked = mask_guest_name(guest_raw)
        purged = is_purged_guest(guest_raw)
        identity = compute_guest_identity_hash(property_code, guest_raw, raw["GUEST_NAME_ID"])
        # 原始姓名不落地：raw 層改存遮罩後版本
        raw["GUEST_NAME"] = masked
        raw["SHARE_NAMES"] = mask_guest_name(raw["SHARE_NAMES"]) if raw["SHARE_NAMES"].strip() else ""

        no_of_rooms = to_int(raw["NO_OF_ROOMS"])
        nights = to_int(raw["NIGHTS"])
        adults = to_int(raw["ADULTS"])
        children = to_int(raw["CHILDREN"])
        room_no = normalize_cell(raw["ROOM"])
        resv_id = normalize_cell(raw["RESV_NAME_ID"])

        if no_of_rooms == 0:
            zero_room_count += 1
        sum_rooms += no_of_rooms
        sum_persons += adults
        sum_nights += nights
        sum_room_nights += no_of_rooms * nights
        dates.append(dep_date)

        row_hash = compute_row_hash(DEPARTURE_COLUMNS, raw)

        weak = not resv_id or not room_no
        record_key = (
            row_hash if weak
            else f"{property_code}|{resv_id}|{arr_date}|{dep_date}|{room_no}"
        )
        if record_key in seen_keys:
            result.issues.append(ParseIssue(
                start_no, "RECORD_KEY", record_key, ERR_DUPLICATE_KEY,
                f"同一批次出現重複業務鍵（另見第 {seen_keys[record_key]} 列）",
                severity="WARNING",
            ))
        else:
            seen_keys[record_key] = start_no

        fact = {
            "property_code":          property_code,
            "resv_name_id":           resv_id,
            "guest_name_id":          clean_guest_name_id(raw["GUEST_NAME_ID"]),
            "external_reference":     normalize_cell(raw["EXTERNAL_REFERENCE"]),
            "reservation_status":     normalize_cell(raw["RESV_STATUS"]),
            "arrival_date":           arr_date,
            "departure_date":         dep_date,
            "departure_time_minutes": parse_time_minutes(raw["DEPARTURE_TIME"]),
            "no_of_rooms":            no_of_rooms,
            "nights":                 nights,
            "room_nights":            no_of_rooms * nights,
            "adults":                 adults,
            "children":               children,
            "room_no":                room_no,
            "room_category":          normalize_cell(raw["ROOM_CATEGORY"]),
            "room_category_label":    normalize_cell(raw["ROOM_CATEGORY_LABEL"]),
            "is_shared":              1 if normalize_cell(raw["IS_SHARED_YN"]).upper() == "Y" else 0,
            "company_name":           normalize_cell(raw["COMPANY_NAME"]),
            "travel_agent_name":      normalize_cell(raw["TRAVEL_AGENT_NAME"]),
            "source_name":            normalize_cell(raw["SOURCE_NAME"]),
            "group_name":             normalize_cell(raw["GROUP_NAME"]),
            "rate_code":              normalize_cell(raw["RATE_CODE"]),
            "payment_desc":           normalize_cell(raw["PAYMENT_DESC"]),
            "balance":                to_float(raw["BALANCE"]),
            "guest_name_masked":      masked,
            "guest_identity_hash":    identity,
            "is_purged":              1 if purged else 0,
            "vip":                    normalize_cell(raw["VIP"]),
            "membership_type":        normalize_cell(raw["MEMBERSHIP_TYPE"]),
            "membership_level":       normalize_cell(raw["MEMBERSHIP_LEVEL"]),
            "row_hash":               row_hash,
            "record_key":             record_key,
            "weak_key":               1 if weak else 0,
        }

        result.records.append(ParsedRecord(
            source_row_no=start_no,
            source_row_no_end=end_no,
            raw=raw,
            fact=fact,
            row_hash=row_hash,
            record_key=record_key,
            weak_key=weak,
        ))

    if zero_room_count:
        result.issues.append(ParseIssue(
            0, "NO_OF_ROOMS", str(zero_room_count), WARN_ZERO_ROOM,
            f"有 {zero_room_count:,} 列 NO_OF_ROOMS = 0（不計入房數，語意待確認，見規格書 §17.2 Q1）",
            severity="WARNING",
        ))

    if dates:
        result.report_start_date = min(dates)
        result.report_end_date = max(dates)

    result.stats = {
        "merged_pairs":    pairs,
        "valid_rows":      len(result.records),
        "zero_room_rows":  zero_room_count,
        "sum_no_of_rooms": sum_rooms,
        "sum_adults":      sum_persons,
        "sum_nights":      sum_nights,
        "sum_room_nights": sum_room_nights,
    }
    return result


# ══════════════════════════════════════════════════════════════════════════════
# History and Forecast
# ══════════════════════════════════════════════════════════════════════════════

_HF_REQUIRED = ["REVENUE", "NO_ROOMS", "INVENTORY_ROOMS", "CF_OOO_ROOMS", "CF_CALC_INV_ROOMS"]


def parse_history_forecast(content: bytes, property_code: str = "") -> ParseResult:
    text, _enc = detect_encoding(content)
    lines = _split_lines(text)
    result = ParseResult(source_type="HISTORY_FORECAST", property_code=property_code)

    if not lines or not lines[0].strip():
        result.issues.append(ParseIssue(1, "HEADER", "", ERR_BAD_WIDTH, "檔案為空或缺少表頭"))
        return result

    body = [(no, ln) for no, ln in enumerate(lines[1:], start=2) if ln.strip()]
    body, footer = _extract_footer(body, "SUMNO_ROOMSPERREPORT", HF_FOOTER_KEYS)
    result.footer = footer
    result.row_count_source = len(body)

    seen_keys: dict[str, int] = {}
    history_dates: list[str] = []
    all_dates: list[str] = []
    # ⚠️ footer 的 SUM*PERREPORT 是「整份報表」合計 = History + Forecast
    #    （實測：10,037 History + 22 Forecast = 10,059 = SUMNO_ROOMSPERREPORT）
    #    因此對帳必須用 *_all 系列；分析實績則只取 History。
    sum_revenue_all = 0.0
    sum_sold_all = 0
    sum_available_all = 0
    sum_inventory_all = 0
    sum_revenue = 0.0
    sum_sold = 0
    sum_available = 0
    sum_inventory = 0

    for row_no, line in body:
        cells = line.split("\t")
        raw = {col: (cells[i] if i < len(cells) else "") for i, col in enumerate(HF_COLUMNS)}

        rec_type_desc = normalize_cell(raw["REC_TYPE_DESC"])
        if rec_type_desc not in HF_VALID_RECORD_TYPES:
            result.issues.append(ParseIssue(
                row_no, "REC_TYPE_DESC", rec_type_desc, ERR_BAD_RECORD_TYPE,
                f"REC_TYPE_DESC 非 History/Forecast（值：{rec_type_desc or '空白'}），已略過",
                severity="WARNING",
            ))
            result.row_count_rejected += 1
            continue

        if len(cells) < HF_WIDTH:
            result.issues.append(ParseIssue(
                row_no, "ROW", f"欄數={len(cells)}", ERR_BAD_WIDTH,
                f"欄數為 {len(cells)}，預期 {HF_WIDTH}",
                severity="WARNING",
            ))

        missing = [c for c in _HF_REQUIRED if raw.get(c, "").strip() == ""]
        if missing:
            result.issues.append(ParseIssue(
                row_no, ",".join(missing), "", ERR_MISSING_REQUIRED,
                f"缺少必要欄位：{'、'.join(missing)}",
            ))
            result.row_count_rejected += 1
            continue

        business_date = parse_opera_date(raw["CONSIDERED_DATE"])
        if not business_date:
            result.issues.append(ParseIssue(
                row_no, "CONSIDERED_DATE", raw["CONSIDERED_DATE"], ERR_BAD_DATE,
                "CONSIDERED_DATE 無法解析為日期（預期 DD-MON-YY）",
            ))
            result.row_count_rejected += 1
            continue

        revenue = to_float(raw["REVENUE"])
        sold_rooms = to_int(raw["NO_ROOMS"])
        inventory_rooms = to_int(raw["INVENTORY_ROOMS"])
        ooo_rooms = to_int(raw["CF_OOO_ROOMS"])
        # ⚠️ 可售房晚一律用 CF_CALC_INV_ROOMS（規格書 §3.4）
        available_rooms = to_int(raw["CF_CALC_INV_ROOMS"])

        record_key = f"{result.property_code}|{rec_type_desc}|{business_date}"
        if record_key in seen_keys:
            result.issues.append(ParseIssue(
                row_no, "CONSIDERED_DATE", business_date, ERR_DUPLICATE_KEY,
                f"同一批次同類型同日期重複（另見第 {seen_keys[record_key]} 列），不得靜默加總",
            ))
            result.row_count_rejected += 1
            continue
        seen_keys[record_key] = row_no

        if revenue < 0:
            result.issues.append(ParseIssue(
                row_no, "REVENUE", raw["REVENUE"], WARN_NEGATIVE_REVENUE,
                f"{business_date} 房間營收為負（{revenue:,.0f}）", severity="WARNING",
            ))
        if sold_rooms < 0 or available_rooms < 0 or inventory_rooms < 0:
            result.issues.append(ParseIssue(
                row_no, "ROOMS", f"{sold_rooms}/{available_rooms}/{inventory_rooms}",
                WARN_NEGATIVE_ROOMS, f"{business_date} 房數出現負值", severity="WARNING",
            ))
        if available_rooms and sold_rooms > available_rooms:
            result.issues.append(ParseIssue(
                row_no, "NO_ROOMS", str(sold_rooms), WARN_OVERSOLD,
                f"{business_date} 已售房晚 {sold_rooms} > 可售房晚 {available_rooms}（超賣）",
                severity="WARNING",
            ))

        all_dates.append(business_date)
        sum_revenue_all += revenue
        sum_sold_all += sold_rooms
        sum_available_all += available_rooms
        sum_inventory_all += inventory_rooms
        if rec_type_desc == RECORD_TYPE_HISTORY:
            history_dates.append(business_date)
            sum_revenue += revenue
            sum_sold += sold_rooms
            sum_available += available_rooms
            sum_inventory += inventory_rooms

        row_hash = compute_row_hash(HF_COLUMNS, raw)
        fact = {
            "property_code":                 result.property_code,
            "record_type":                   rec_type_desc,
            "business_date":                 business_date,
            "revenue":                       revenue,
            "sold_rooms":                    sold_rooms,
            "inventory_rooms":               inventory_rooms,
            "ooo_rooms":                     ooo_rooms,
            "available_rooms":               available_rooms,
            "individual_deduct_rooms":       to_int(raw["IND_DEDUCT_ROOMS"]),
            "individual_non_deduct_rooms":   to_int(raw["IND_NON_DEDUCT_ROOMS"]),
            "group_deduct_rooms":            to_int(raw["GRP_DEDUCT_ROOMS"]),
            "group_non_deduct_rooms":        to_int(raw["GRP_NON_DEDUCT_ROOMS"]),
            "individual_deduct_revenue":     to_float(raw["IND_DEDUCT_REVENUE"]),
            "individual_non_deduct_revenue": to_float(raw["IND_NON_DEDUCT_REVENUE"]),
            "group_deduct_revenue":          to_float(raw["GRP_DEDUCT_REVENUE"]),
            "group_non_deduct_revenue":      to_float(raw["GRP_NON_DEDUCT_REVENUE"]),
            "arrival_rooms":                 to_int(raw["ARRIVAL_ROOMS"]),
            "departure_rooms":               to_int(raw["DEPARTURE_ROOMS"]),
            "complimentary_rooms":           to_int(raw["COMPLIMENTARY_ROOMS"]),
            "house_use_rooms":               to_int(raw["HOUSE_USE_ROOMS"]),
            "day_use_rooms":                 to_int(raw["DAY_USE_ROOMS"]),
            "no_show_rooms":                 to_int(raw["NO_SHOW_ROOMS"]),
            "no_persons":                    to_int(raw["NO_PERSONS"]),
            "row_hash":                      row_hash,
            "record_key":                    record_key,
        }

        result.records.append(ParsedRecord(
            source_row_no=row_no,
            source_row_no_end=row_no,
            raw=raw,
            fact=fact,
            row_hash=row_hash,
            record_key=record_key,
        ))

    # History 日期連續性檢查
    gaps = _find_date_gaps(history_dates)
    if gaps:
        preview = "、".join(gaps[:10]) + ("…" if len(gaps) > 10 else "")
        result.issues.append(ParseIssue(
            0, "CONSIDERED_DATE", preview, WARN_DATE_GAP,
            f"History 日期有 {len(gaps)} 天缺口：{preview}", severity="WARNING",
        ))

    if all_dates:
        result.report_start_date = min(all_dates)
        result.report_end_date = max(all_dates)

    result.stats = {
        "valid_rows":          len(result.records),
        "history_rows":        len(history_dates),
        "forecast_rows":       len(result.records) - len(history_dates),
        # 對帳用：整份報表（History + Forecast），對應 footer SUM*PERREPORT
        "sum_revenue_all":         round(sum_revenue_all, 4),
        "sum_sold_rooms_all":      sum_sold_all,
        "sum_available_rooms_all": sum_available_all,
        "sum_inventory_rooms_all": sum_inventory_all,
        # 分析用：只取 History（實績）
        "sum_revenue":         round(sum_revenue, 4),
        "sum_sold_rooms":      sum_sold,
        "sum_available_rooms": sum_available,
        "sum_inventory_rooms": sum_inventory,
        "history_adr":         round(sum_revenue / sum_sold, 4) if sum_sold else 0.0,
        "history_occupancy":   round(sum_sold / sum_available, 6) if sum_available else 0.0,
        "history_revpar":      round(sum_revenue / sum_available, 4) if sum_available else 0.0,
        "date_gaps":           len(gaps),
    }
    return result


def _find_date_gaps(dates: list[str]) -> list[str]:
    """回傳 min~max 之間缺少的日期（ISO 字串）。"""
    if len(dates) < 2:
        return []
    from datetime import date, timedelta

    def _d(s: str) -> date:
        y, m, d = s.split("-")
        return date(int(y), int(m), int(d))

    have = {_d(s) for s in dates}
    cur, end = min(have), max(have)
    gaps: list[str] = []
    while cur <= end:
        if cur not in have:
            gaps.append(cur.isoformat())
        cur += timedelta(days=1)
    return gaps


# ══════════════════════════════════════════════════════════════════════════════
# Footer 對帳（規格書 §3.4 / §8）
# ══════════════════════════════════════════════════════════════════════════════

def reconcile_departure(result: ParseResult) -> dict:
    """Departure footer vs 程式彙總。差異必須為 0。"""
    f = result.footer
    s = result.stats
    items = [
        ("房數", "SUMNO_OF_ROOMSPERREPORT", to_int(f.get("SUMNO_OF_ROOMSPERREPORT", "")), s.get("sum_no_of_rooms", 0)),
        ("人數", "SUMPERSONSPERREPORT",     to_int(f.get("SUMPERSONSPERREPORT", "")),     s.get("sum_adults", 0)),
    ]
    return _build_reconcile(items)


def reconcile_history_forecast(result: ParseResult) -> dict:
    """History and Forecast footer vs 程式彙總。

    ⚠️ footer 的 SUM*PERREPORT 是「整份報表」合計（History + Forecast 都算），
       實測：10,037（History）+ 22（Forecast）= 10,059 = SUMNO_ROOMSPERREPORT。
       因此這裡必須用 *_all 系列比對，不能只用 History。
    """
    f = result.footer
    s = result.stats
    items = [
        ("已售房晚", "SUMNO_ROOMSPERREPORT",        to_int(f.get("SUMNO_ROOMSPERREPORT", "")),        s.get("sum_sold_rooms_all", 0)),
        ("房間營收", "SUMREVENUEPERREPORT",         to_float(f.get("SUMREVENUEPERREPORT", "")),       s.get("sum_revenue_all", 0.0)),
        ("可售房晚", "SUMCALC_INVROOMSPERREPORT",   to_int(f.get("SUMCALC_INVROOMSPERREPORT", "")),   s.get("sum_available_rooms_all", 0)),
        ("實體房晚", "SUMINVENTORY_ROOMSPERREPORT", to_int(f.get("SUMINVENTORY_ROOMSPERREPORT", "")), s.get("sum_inventory_rooms_all", 0)),
    ]
    return _build_reconcile(items)


def _build_reconcile(items: list[tuple[str, str, float, float]]) -> dict:
    rows = []
    all_ok = True
    for label, key, footer_val, computed in items:
        diff = round(float(computed) - float(footer_val), 2)
        ok = abs(diff) < 0.01
        all_ok = all_ok and ok
        rows.append({
            "label": label,
            "footer_key": key,
            "footer_value": footer_val,
            "computed_value": computed,
            "diff": diff,
            "ok": ok,
        })
    return {"ok": all_ok, "items": rows}
