"""
保全巡檢 同步服務【統一 Sync + 寬表格 Pivot + 動態欄位偵測】

支援 7 張 Ragic Sheet（security-patrol/1、2、3、4、5、6、9）。
所有 Sheet 結構相同：
  每一 Row = 一次完整巡檢場次（寬表格格式）
  場次欄位：巡檢人員、開始巡檢時間、巡檢結束時間、工時計算（或類似欄位）
  結果欄位：N 個巡檢點，各自儲存 正常/異常 等狀態值

【動態欄位偵測】
  同步時自動掃描欄位，排除已知 metadata 欄位後，其餘視為巡檢點欄位。
"""
import logging
from datetime import datetime, timezone
from app.core.time import twnow
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.security_patrol import SecurityPatrolBatch, SecurityPatrolItem
from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

# ── Sheet 設定表 ──────────────────────────────────────────────────────────────
SHEET_CONFIGS: dict[str, dict] = {
    "b1f-b4f": {
        "id":   1,
        "name": "保全每日巡檢 - B1F~B4F夜間巡檢",
        "path": "security-patrol/1",
    },
    "1f-3f": {
        "id":   2,
        "name": "保全巡檢 - 1F ~ 3F (夜間巡檢)",
        "path": "security-patrol/2",
    },
    "5f-10f": {
        "id":   3,
        "name": "保全巡檢 - 5F ~ 10F (夜間巡檢)",
        "path": "security-patrol/3",
    },
    "4f": {
        "id":   4,
        "name": "保全巡檢 - 4F (夜間巡檢)",
        "path": "security-patrol/4",
    },
    "1f-hotel": {
        "id":   5,
        "name": "保全巡檢 - 1F夜間巡檢 (飯店大廳)",
        "path": "security-patrol/5",
    },
    "1f-close": {
        "id":   6,
        "name": "保全巡檢 - 1F 閉店巡檢",
        "path": "security-patrol/6",
    },
    "1f-open": {
        "id":   9,
        "name": "保全巡檢 - 1F 開店準備",
        "path": "security-patrol/9",
    },
}

# ── Ragic 連線設定 ─────────────────────────────────────────────────────────────
SP_SERVER_URL = getattr(settings, "RAGIC_SP_SERVER_URL", "ap12.ragic.com")
SP_ACCOUNT    = getattr(settings, "RAGIC_SP_ACCOUNT",    "soutlet001")

# ── 場次 metadata 欄位（不視為巡檢點）────────────────────────────────────────
SESSION_FIELDS = {
    "巡檢人員",
    "保全人員",
    "開始巡檢時間",
    "開始時間",
    "巡檢開始時間",
    "巡檢結束時間",
    "結束時間",
    "結束巡檢時間",
    "工時計算",
    "巡檢日期",
    "日期",
    "_ragicId",
    "_owner",
    "_create",
    "_modify",
}

# 常用的場次欄位 key（候選清單，sync 時逐一嘗試）
INSPECTOR_CANDIDATES  = ["巡檢人員", "保全人員"]
START_TIME_CANDIDATES = ["開始巡檢時間", "開始時間", "巡檢開始時間", "巡檢日期", "日期"]
END_TIME_CANDIDATES   = ["巡檢結束時間", "結束時間", "結束巡檢時間"]
WORK_HOURS_CANDIDATES = ["工時計算"]

# ── 巡檢結果 → result_status 對照 ────────────────────────────────────────────
RESULT_STATUS_MAP: dict[str, str] = {
    "正常":   "normal",
    "OK":     "normal",
    "ok":     "normal",
    "O":      "normal",
    "✓":      "normal",
    "V":      "normal",
    "v":      "normal",
    "異常":   "abnormal",
    "待處理": "pending",
    "待修":   "pending",
    "待修繕": "pending",
    "X":      "abnormal",
    "x":      "abnormal",
}


# ── 輔助函式 ──────────────────────────────────────────────────────────────────

def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(_stringify(x) for x in value)
    if isinstance(value, dict):
        return _stringify(value.get("value") or value.get("label") or "")
    return str(value).strip()


def _extract_date(raw_datetime: str) -> str:
    """從 '2026/4/14 09:26' 或 '2026-04-14 09:26' 萃取 YYYY/MM/DD。"""
    raw = (raw_datetime or "").strip()
    if not raw:
        return ""
    date_part = raw[:10].replace("-", "/")
    parts = date_part.split("/")
    if len(parts) == 3:
        try:
            return f"{parts[0]}/{int(parts[1]):02d}/{int(parts[2]):02d}"
        except ValueError:
            pass
    return date_part


def _normalize_result_status(raw: str) -> tuple[str, bool]:
    """將原始值轉為正規化狀態與異常旗標。"""
    raw = (raw or "").strip()
    status = RESULT_STATUS_MAP.get(raw, "unchecked" if not raw else "abnormal")
    return status, status in ("abnormal", "pending")


def _pick_field(raw: dict, candidates: list[str]) -> str:
    """從候選欄位清單中挑選第一個存在且有值的欄位。"""
    for key in candidates:
        val = _stringify(raw.get(key, ""))
        if val:
            return val
    return ""


def _extract_check_items(row: dict) -> list[str]:
    """
    從 Ragic Row dict 動態提取巡檢點欄位清單。
    排除場次 metadata 欄位、系統欄位（底線開頭）、純數字 key，
    以及拍照欄位（含「拍照」字樣，如拍照、拍照2、拍照3 等）。
    """
    items = []
    for key in row.keys():
        if key in SESSION_FIELDS:
            continue
        if str(key).startswith("_"):
            continue
        if "拍照" in str(key):  # 排除拍照類欄位（Ragic 必填但非巡檢評分項目）
            continue
        try:
            int(key)  # 數字型 key 跳過
            continue
        except (ValueError, TypeError):
            pass
        items.append(key)
    return items


# ── 單一 Sheet 同步 ───────────────────────────────────────────────────────────

async def sync_sheet(sheet_key: str) -> dict:
    """
    同步指定 sheet_key 的 Ragic Sheet：
      每個 Row → 1 筆 SecurityPatrolBatch + pivot 成 N 筆 SecurityPatrolItem。
    """
    if sheet_key not in SHEET_CONFIGS:
        return {"fetched": 0, "upserted": 0, "item_rows": 0,
                "errors": [f"未知的 sheet_key: {sheet_key}"]}

    cfg        = SHEET_CONFIGS[sheet_key]
    sheet_id   = cfg["id"]
    sheet_name = cfg["name"]
    sheet_path = cfg["path"]

    adapter = RagicAdapter(
        sheet_path=sheet_path,
        server_url=SP_SERVER_URL,
        account=SP_ACCOUNT,
    )
    logger.info(f"[SPSync:{sheet_key}] 開始同步 {sheet_path}...")

    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[SPSync:{sheet_key}] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "item_rows": 0, "errors": [str(exc)]}

    fetched   = len(raw_data)
    upserted  = 0
    item_rows = 0
    errors: list[str] = []
    now = twnow()

    # 從第一筆取得巡檢點欄位清單
    check_items: list[str] = []
    if fetched > 0:
        first_rec = next(iter(raw_data.values()))
        check_items = _extract_check_items(first_rec)
        logger.info(
            f"[SPSync:{sheet_key}] 第一筆偵測到 {len(check_items)} 個巡檢點：{check_items}"
        )

    db = SessionLocal()
    try:
        for ragic_row_id, raw in raw_data.items():
            # batch ragic_id = "{sheet_key}_{ragic_row_id}"（避免不同 sheet 衝突）
            batch_id = f"{sheet_key}_{ragic_row_id}"
            try:
                start_raw = _pick_field(raw, START_TIME_CANDIDATES)
                batch = SecurityPatrolBatch(
                    ragic_id        = batch_id,
                    sheet_key       = sheet_key,
                    sheet_id        = sheet_id,
                    sheet_name      = sheet_name,
                    inspection_date = _extract_date(start_raw),
                    inspector_name  = _pick_field(raw, INSPECTOR_CANDIDATES),
                    start_time      = start_raw,
                    end_time        = _pick_field(raw, END_TIME_CANDIDATES),
                    work_hours      = _pick_field(raw, WORK_HOURS_CANDIDATES),
                    synced_at       = now,
                )

                existing = db.get(SecurityPatrolBatch, batch_id)
                if existing:
                    existing.inspection_date = batch.inspection_date
                    existing.inspector_name  = batch.inspector_name
                    existing.start_time      = batch.start_time
                    existing.end_time        = batch.end_time
                    existing.work_hours      = batch.work_hours
                    existing.synced_at       = now
                else:
                    db.add(batch)

                # Pivot：清除舊 items，重新產生
                db.query(SecurityPatrolItem).filter(
                    SecurityPatrolItem.batch_ragic_id == batch_id
                ).delete(synchronize_session=False)

                row_check_items = check_items or _extract_check_items(raw)
                for seq, col_name in enumerate(row_check_items, start=1):
                    result_raw = _stringify(raw.get(col_name, ""))
                    is_note = "異常說明" in str(col_name)

                    if is_note:
                        # 文字備註欄位：保留原始文字，不做狀態正規化，不計入統計
                        result_status = "note"
                        abnormal_flag = False
                    else:
                        result_status, abnormal_flag = _normalize_result_status(result_raw)

                    db.add(SecurityPatrolItem(
                        ragic_id       = f"{batch_id}_{seq}",
                        batch_ragic_id = batch_id,
                        sheet_key      = sheet_key,
                        seq_no         = seq,
                        item_name      = col_name,
                        result_raw     = result_raw,
                        result_status  = result_status,
                        abnormal_flag  = abnormal_flag,
                        is_note        = is_note,
                        synced_at      = now,
                    ))
                    item_rows += 1

                upserted += 1

            except Exception as exc:
                errors.append(f"ragic_row_id={ragic_row_id}: {exc}")
                logger.warning(f"[SPSync:{sheet_key}] 記錄 {ragic_row_id} 失敗：{exc}")

        db.commit()
        logger.info(
            f"[SPSync:{sheet_key}] 完成：fetched={fetched}, "
            f"batches={upserted}, items={item_rows}, errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[SPSync:{sheet_key}] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {
        "fetched":          fetched,
        "upserted":         upserted,
        "item_rows":        item_rows,
        "check_item_count": len(check_items),
        "errors":           errors,
    }


# ── 全部 Sheet 同步 ───────────────────────────────────────────────────────────

async def sync_all() -> dict:
    """同步所有 7 張保全巡檢 Sheet。"""
    results = {}
    for sheet_key in SHEET_CONFIGS:
        results[sheet_key] = await sync_sheet(sheet_key)
    return results
