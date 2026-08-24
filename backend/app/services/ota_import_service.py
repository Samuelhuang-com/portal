"""
OTA 口碑分析 — CSV 備援匯入

規格書：`docs/SPEC_ota_reviews.md` §6.6

═══════════════════════════════════════════════════════════════════════════
這條通道不是「附加功能」，是模組的救生艇
═══════════════════════════════════════════════════════════════════════════
爬蟲是整個模組最脆弱的一環：OTA 隨時可能改版、跳 CAPTCHA、封 IP，
正式區的 Windows Service 甚至可能連 Chrome 都開不起來（規格書 §3.3 R1）。

沒有這條通道，爬蟲一掛掉整個模組就變空殼。
所以 P1 就要做，而且**不可**因為 P2 爬蟲上線就移除。

⚠️ 匯入走的是與爬蟲**完全相同**的正規化管線（`ota_normalize.normalize_review`）
   與落地邏輯（`ota_ingest_service.upsert_reviews`）。
   不可在這裡另外實作分制換算或日期解析。
"""
from __future__ import annotations

import csv
import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ota_review import OtaSource
from app.schemas.ota_review import ImportResultOut
from app.services.ota_ingest_service import (finish_sync_log, start_sync_log,
                                             upsert_reviews)
from app.services.ota_normalize import (PLATFORM_LABEL, PLATFORM_SCALE,
                                        RawReview, normalize_review)

# 匯入欄位（與 ota_review_service.EXPORT_HEADERS 對齊，可匯出後修改再匯回）
REQUIRED_HEADERS = ["飯店代碼", "OTA平台"]

# 平台顯示名稱 → 代碼（使用者可能直接貼匯出檔的中文名稱）
_LABEL_TO_CODE = {label.lower(): code for code, label in PLATFORM_LABEL.items()}
_LABEL_TO_CODE.update({code: code for code in PLATFORM_SCALE})
_LABEL_TO_CODE["booking.com"] = "booking"
_LABEL_TO_CODE["trip advisor"] = "tripadvisor"


def _to_float(value: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _resolve_platform(value: str) -> str:
    return _LABEL_TO_CODE.get((value or "").strip().lower(), "")


def parse_csv(content: bytes) -> tuple[list[dict], list[str]]:
    """
    解析 CSV。回傳 `(rows, errors)`。

    編碼依序試 utf-8-sig（Excel 匯出的標準）、utf-8、cp950（舊版 Excel 繁中）。
    """
    text = None
    for encoding in ("utf-8-sig", "utf-8", "cp950"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        return [], ["檔案編碼無法辨識，請另存為 UTF-8 或 CSV UTF-8 格式"]

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], ["檔案是空的或沒有標題列"]

    headers = [h.strip() for h in reader.fieldnames]
    missing = [h for h in REQUIRED_HEADERS if h not in headers]
    if missing:
        return [], [f"缺少必要欄位：{'、'.join(missing)}"]

    rows = [{(k or "").strip(): (v or "") for k, v in row.items()} for row in reader]
    return rows, []


def import_reviews(
    db: Session,
    content: bytes,
    *,
    user_id: str | None = None,
) -> ImportResultOut:
    """
    CSV → 正規化 → 落地。

    ⚠️ 找不到對應來源的資料列會被**略過並記入 warnings**，不是 errors。
       依 CLAUDE.md §9 規則 8：只要 errors 非空就會被標成失敗（黃燈），
       「有幾列對不到來源」是可預期的狀況，不該讓整批匯入變紅字。
    """
    result = ImportResultOut()

    rows, errors = parse_csv(content)
    if errors:
        result.errors = errors
        return result

    result.total_rows = len(rows)
    if not rows:
        result.warnings.append("檔案沒有任何資料列")
        return result

    # ── 依 (飯店代碼, 平台) 分組，一組對應一個來源 ─────────────────────
    sources = {
        (s.hotel_code, s.platform): s
        for s in db.execute(select(OtaSource)).scalars().all()
    }

    grouped: dict[tuple[str, str], list[RawReview]] = {}
    for idx, row in enumerate(rows, start=2):   # 第 1 列是標題
        hotel_code = (row.get("飯店代碼") or "").strip()
        platform = _resolve_platform(row.get("OTA平台", ""))

        if not hotel_code or not platform:
            result.warnings.append(
                f"第 {idx} 列：飯店代碼或 OTA 平台空白／無法辨識，已略過"
            )
            result.skipped += 1
            continue

        if (hotel_code, platform) not in sources:
            result.warnings.append(
                f"第 {idx} 列：找不到來源「{hotel_code} / {PLATFORM_LABEL.get(platform, platform)}」，"
                f"請先到「OTA 來源設定」建立，已略過"
            )
            result.skipped += 1
            continue

        grouped.setdefault((hotel_code, platform), []).append(RawReview(
            author=row.get("旅客暱稱", ""),
            score_raw=_to_float(row.get("原始分數", "")),
            score_scale=_to_int(row.get("分制", "")),
            title=row.get("標題", ""),
            positive_text=row.get("正評", ""),
            negative_text=row.get("負評", ""),
            comment=row.get("完整留言", ""),
            review_date_text=row.get("評論日期", ""),
            stay_date_text=row.get("入住年月", ""),
            nationality=row.get("國籍", ""),
            traveler_type=row.get("旅客類型", ""),
            room_type=row.get("房型", ""),
            nights=_to_int(row.get("入住晚數", "")),
            review_url=row.get("評論網址", ""),
            raw={"import_row": idx},
        ))

    # ── 逐來源正規化並落地 ─────────────────────────────────────────────
    for (hotel_code, platform), raws in grouped.items():
        source = sources[(hotel_code, platform)]
        log = start_sync_log(db, source.id, "import", user_id)

        normalized = [
            normalize_review(
                raw,
                hotel_code=hotel_code,
                platform=platform,
                default_scale=source.score_scale,
            )
            for raw in raws
        ]
        upsert = upsert_reviews(db, source, normalized, sync_log_id=log.id)

        result.inserted += upsert.inserted
        result.updated += upsert.updated
        result.marked_duplicate += upsert.marked_duplicate
        # 正規化過程的警示（日期解析失敗、分制判不出來）要讓匯入者看到，
        # 不能只寫進 sync_log —— 使用者是在畫面上按匯入的，不會去翻同步歷程
        result.warnings.extend(upsert.warnings)

        finish_sync_log(
            db, log,
            status="success",
            found_count=len(raws),
            result=upsert,
        )

    db.commit()
    return result


def csv_template() -> bytes:
    """下載空白範本，讓使用者知道欄位長怎樣。"""
    from app.services.ota_review_service import EXPORT_HEADERS

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_HEADERS)
    writer.writerow([
        "HANNS", "瀚寓", "Booking.com", "8.5", "10", "8.5",
        "Amy", "情侶", "台灣", "豪華雙人房", "2",
        "住得很舒服", "位置方便、房間乾淨", "隔音稍差", "",
        "2026-07-15", "2026-07", "", "", "否", "https://...", "",
    ])
    return buffer.getvalue().encode("utf-8-sig")
