"""
競品分析 — CSV 備援匯入

建立日期：2026-09-09
規格書：`docs/SPEC_compset_analysis.md` §6.4、D16、D17

═══════════════════════════════════════════════════════════════════════════
這條通道不是「附加功能」，是模組的救生艇
═══════════════════════════════════════════════════════════════════════════
擷取是整個模組最脆弱的一環：供應商可能改版、可能斷線、正式機的網路可能連不出去
（P0 實測時 session 的兩個環境都被政策擋掉 serpapi.com）。

沒有這條通道，抓取一掛掉整個模組就變空殼。
所以資料層階段就要做，而且**不可**因為排程上線就移除。

⚠️ 匯入走的是與抓取**完全相同**的落地邏輯（`compset_fetch_service.upsert_snapshot`）。
   不可在這裡另外實作一份寫入 —— 兩份寫入遲早會長歪。

═══════════════════════════════════════════════════════════════════════════
四條規則
═══════════════════════════════════════════════════════════════════════════
1. **⭐ D16：與 SerpApi 並存時，統計採 SerpApi 那一筆。**
   唯一鍵含 `source`，所以同一格可以同時有 `serpapi` 與 `csv` 兩列。
   優先序寫在 `compset_analysis.SOURCE_PRIORITY`，統計層照它取。
   CSV 的用途是**補上抓不到的格子**，不是覆蓋抓得到的格子。

2. **⭐ D17：逐列匯入 ＋ 錯誤報表。**
   能匯的先匯，有問題的列列出行號與原因。CSV 是救生艇，
   一列拼錯就整檔退回會讓人沒辦法用。

3. **⭐ `tax_included = 'no'` 只有這裡合法。**
   SerpApi 的回應永遠推導不出 `no`（見 `compset_serpapi_client` 規則 4）。
   只有人工匯入時，使用者才能明確宣告「這是稅前價」。

4. **沒有價 ＋ 標示滿房 ＝ 合法的一列。**
   `is_sold_out='yes'` 本身就是有價值的資料（SPEC §5.4），
   不可以因為「沒有價格」就把該列當成錯誤丟掉。

═══════════════════════════════════════════════════════════════════════════
欄位
═══════════════════════════════════════════════════════════════════════════
必填：`入住日期`、`飯店`、（`含稅價` 或 `是否滿房=是` 二擇一）
選填：`快照日期`（空 ＝ 匯入當天）、`稅前價`、`幣別`、`含稅`、`是否滿房`、
      `通路`、`房型`、`入住人數`

`飯店` 可以填 `hotel_code` 或名稱；名稱比對會先正規化（去空白與分隔符）。
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compset_analysis import CompsetHotel, CompsetSubscriber
from app.services import compset_serpapi_client as SC
from app.services.compset_fetch_service import _norm, upsert_snapshot

SOURCE_CSV = "csv"

COL_STAY = "入住日期"
COL_HOTEL = "飯店"
COL_GROSS = "含稅價"
COL_SNAPSHOT = "快照日期"
COL_PRETAX = "稅前價"
COL_CURRENCY = "幣別"
COL_TAX = "含稅"
COL_SOLD = "是否滿房"
COL_OTA = "通路"
COL_ROOM = "房型"
COL_GUESTS = "入住人數"

REQUIRED_HEADERS = [COL_STAY, COL_HOTEL]
TEMPLATE_HEADERS = [COL_SNAPSHOT, COL_STAY, COL_HOTEL, COL_GROSS, COL_PRETAX,
                    COL_CURRENCY, COL_TAX, COL_SOLD, COL_OTA, COL_ROOM, COL_GUESTS]

# 使用者可能填中文、英文或直接留空
_YES = {"是", "y", "yes", "true", "1", "含稅", "有"}
_NO = {"否", "n", "no", "false", "0", "未稅", "無", "沒有"}
_UNKNOWN = {"不確定", "unknown", "未知", "?"}

# 價格可能被貼成 "$1,900"、"NT$1,900"、"1,900 元"
_PRICE_JUNK = re.compile(r"[^\d.\-]")


@dataclass
class ImportResult:
    """對齊 `ota_review` 的 `ImportResultOut`，router 可以直接轉成同一個 schema。"""

    total_rows: int = 0
    inserted: int = 0
    skipped: int = 0
    warnings: list[str] = None            # type: ignore[assignment]
    errors: list[str] = None              # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []

    def as_dict(self) -> dict[str, Any]:
        return {"total_rows": self.total_rows, "inserted": self.inserted,
                "skipped": self.skipped, "warnings": self.warnings,
                "errors": self.errors}


# ══════════════════════════════════════════════════════════════════════════
# 純函式：欄位解析
# ══════════════════════════════════════════════════════════════════════════
def parse_price(value: str) -> float | None:
    """
    `"$1,900"` / `"NT$1,900"` / `"1,900 元"` → `1900.0`；空字串 → None。

    ⚠️ 解析不出數字時**拋 ValueError**，不是回 None ——
       「打錯字」與「刻意留空」必須分得開，否則錯字會變成靜默的缺值。
    """
    raw = (value or "").strip()
    if not raw:
        return None
    cleaned = _PRICE_JUNK.sub("", raw)
    if not cleaned or cleaned in {"-", ".", "-."}:
        raise ValueError(f"價格無法解析：{raw!r}")
    return float(cleaned)


def parse_date(value: str) -> str | None:
    """接受 `2026-09-20`、`2026/9/20`、`2026.9.20`；空字串 → None。"""
    raw = (value or "").strip().replace("/", "-").replace(".", "-")
    if not raw:
        return None
    parts = raw.split("-")
    if len(parts) != 3:
        raise ValueError(f"日期無法解析：{value!r}")
    y, m, d = (int(p) for p in parts)
    return date(y, m, d).isoformat()          # 非法日期會在這裡 ValueError


def parse_tristate(value: str, default: str) -> str:
    """`是/否/不確定` → `yes/no/unknown`。空字串用 `default`。"""
    raw = (value or "").strip().lower()
    if not raw:
        return default
    if raw in _YES:
        return "yes"
    if raw in _NO:
        return "no"
    if raw in _UNKNOWN:
        return "unknown"
    raise ValueError(f"只接受 是／否／不確定，收到 {value!r}")


def parse_csv(content: bytes) -> tuple[list[dict[str, str]], list[str]]:
    """
    解析 CSV，回傳 `(rows, errors)`。

    編碼依序試 utf-8-sig（Excel 匯出的標準）、utf-8、cp950（舊版 Excel 繁中）。
    比照 `ota_import_service.parse_csv`。
    """
    text = ""
    for encoding in ("utf-8-sig", "utf-8", "cp950"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        return [], ["檔案編碼無法辨識（試過 utf-8-sig／utf-8／cp950）"]

    reader = csv.DictReader(io.StringIO(text))
    headers = [(h or "").strip() for h in (reader.fieldnames or [])]
    missing = [h for h in REQUIRED_HEADERS if h not in headers]
    if missing:
        return [], [f"缺少必要欄位：{'、'.join(missing)}"]

    rows = [{(k or "").strip(): (v or "") for k, v in row.items()} for row in reader]
    return rows, []


# ══════════════════════════════════════════════════════════════════════════
# 匯入
# ══════════════════════════════════════════════════════════════════════════
def _hotel_index(db: Session, subscriber_id: int) -> dict[str, CompsetHotel]:
    """`hotel_code` 與正規化名稱都可以查得到同一家。"""
    index: dict[str, CompsetHotel] = {}
    hotels = db.execute(
        select(CompsetHotel).where(CompsetHotel.subscriber_id == subscriber_id)
    ).scalars().all()
    for h in hotels:
        if h.hotel_code:
            index.setdefault(_norm(h.hotel_code), h)
        for name in (h.display_name, h.google_query_name):
            if name:
                index.setdefault(_norm(name), h)
    return index


def _row_to_parsed(row: dict[str, str], sub: CompsetSubscriber) -> SC.ParsedRate:
    """把一列 CSV 轉成與抓取層相同的 `ParsedRate`。任何格式問題都拋 ValueError。"""
    gross = parse_price(row.get(COL_GROSS, ""))
    pretax = parse_price(row.get(COL_PRETAX, ""))

    # 沒有價 → 預設當成滿房未知；有價 → 預設不是滿房
    sold = parse_tristate(row.get(COL_SOLD, ""),
                          SC.SOLD_NO if gross is not None else SC.SOLD_UNKNOWN)
    if gross is None and sold != SC.SOLD_YES:
        raise ValueError(f"必須填 {COL_GROSS}，或把 {COL_SOLD} 標成「是」")

    # ⭐ 規則 3：只有 CSV 能宣告 `no`。留空時沿用抓取層的推導邏輯
    tax = parse_tristate(row.get(COL_TAX, ""), SC.tax_state(gross, pretax))

    guests_raw = (row.get(COL_GUESTS, "") or "").strip()
    return SC.ParsedRate(
        name=(row.get(COL_HOTEL, "") or "").strip(),
        price_gross=gross,
        price_pretax=pretax,
        currency=(row.get(COL_CURRENCY, "") or "").strip() or sub.param_currency,
        tax_included=tax,
        ota_name=(row.get(COL_OTA, "") or "").strip()[:50],
        num_guests=int(float(guests_raw)) if guests_raw else None,
        room_type_raw=(row.get(COL_ROOM, "") or "").strip()[:200],
        is_sold_out=sold,
    )


def import_rates(db: Session, *, subscriber_id: int, content: bytes,
                 today: date | None = None) -> ImportResult:
    """
    CSV 備援匯入。逐列處理（D17）：能匯的先匯，有問題的列列出行號與原因。

    ⚠️ 落地走 `compset_fetch_service.upsert_snapshot`，與抓取層同一條路。
    ⚠️ `source='csv'`，**不會覆蓋** SerpApi 的那一列（唯一鍵含 source）；
       統計時採哪一筆由 `SOURCE_PRIORITY` 決定（D16：SerpApi 優先）。
    """
    result = ImportResult()
    today = today or date.today()

    sub = db.get(CompsetSubscriber, subscriber_id)
    if sub is None:
        result.errors.append(f"訂閱客戶 id={subscriber_id} 不存在")
        return result

    rows, errors = parse_csv(content)
    if errors:
        result.errors = errors
        return result

    result.total_rows = len(rows)
    index = _hotel_index(db, subscriber_id)
    default_snapshot = today.isoformat()

    for i, row in enumerate(rows, start=2):        # 第 1 列是表頭
        try:
            stay_date = parse_date(row.get(COL_STAY, ""))
            if not stay_date:
                raise ValueError(f"{COL_STAY} 不可空白")
            snapshot_date = parse_date(row.get(COL_SNAPSHOT, "")) or default_snapshot

            key = _norm(row.get(COL_HOTEL, ""))
            hotel = index.get(key)
            if hotel is None:
                raise ValueError(
                    f"找不到競爭組成員「{row.get(COL_HOTEL, '')}」"
                    "（可填代碼或名稱，需先在競爭組設定建檔）"
                )
            parsed = _row_to_parsed(row, sub)
        except ValueError as exc:
            result.errors.append(f"第 {i} 列：{exc}")
            result.skipped += 1
            continue

        upsert_snapshot(db, sub_id=subscriber_id, hotel_id=hotel.id,
                        snapshot_date=snapshot_date, stay_date=stay_date,
                        tier="", fetch_path="", parsed=parsed, source=SOURCE_CSV)
        result.inserted += 1

    if result.inserted:
        db.commit()
    else:
        db.rollback()
    return result


def csv_template() -> bytes:
    """
    範本檔。utf-8-sig（帶 BOM），Excel 開起來中文不會變亂碼。

    附一列範例，以及一列「滿房」的寫法 —— 沒有價格但標示滿房是**合法的一列**，
    不寫範例的話沒有人會知道可以這樣填。
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(TEMPLATE_HEADERS)
    writer.writerow(["2026-09-09", "2026-09-20", "承攜行旅-台北台大館",
                     "1274", "1103", "TWD", "是", "否", "Booking.com", "標準雙人房", "2"])
    writer.writerow(["2026-09-09", "2026-12-31", "瀚寓夏天",
                     "", "", "", "", "是", "", "", ""])
    return buffer.getvalue().encode("utf-8-sig")
