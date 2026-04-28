"""
全棟例行維護同步服務：Ragic → SQLite

資料來源：
  Sheet 21（主表）：https://ap12.ragic.com/soutlet001/periodic-maintenance/21
  子表格（附表）  ：同 Sheet 21 每筆記錄的 sub-table 欄位

【結構說明】
  - fetch_all() 回傳主表批次清單（含保養日誌編號、日期等）
  - 對每筆批次改用 fetch_one() 取完整資料（含子表格列）
  - item.ragic_id 採用 "{batch_id}_{row_key}" 格式（如 "5_1", "5_2"）

Ragic 欄位中文 key（與商場 PM 共用相同 key 名稱，若有差異請依 /debug/ragic-raw 修正）：
  主表：編號、日期
  子表格：項次、類別、頻率、執行月份、項目、預估耗時、排定日期、排定人員、
          備註、執行人員、保養時間啟、保養時間迄、位置
"""
import json
import logging
import re
from datetime import datetime, timezone
from app.core.time import twnow
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.full_building_maintenance import FullBldgPMBatch, FullBldgPMItem
from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

# ── Ragic 中文欄位 key（主表）────────────────────────────────────────────────
CK_JOURNAL_NO   = "編號"
CK_PERIOD_MONTH = "日期"

# ── Ragic 中文欄位 key（子表格列）──────────────────────────────────────────
CK_SEQ_NO      = "項次"
CK_CATEGORY    = "類別"
CK_FREQUENCY   = "頻率"
CK_EXEC_MONTHS = "執行月份"
CK_TASK_NAME   = "項目"
CK_LOCATION    = "位置"
CK_EST_HOURS   = "預估耗時"
CK_SCHED_DATE  = "排定日期"
CK_SCHEDULER   = "排定人員"
CK_NOTE        = "備註"
CK_EXECUTOR    = "執行人員"
CK_START_TIME  = "保養時間啟"
CK_END_TIME    = "保養時間迄"

# ── Ragic 連線設定 ────────────────────────────────────────────────────────────
FULL_BLDG_PM_SERVER_URL   = getattr(settings, "RAGIC_FULL_BLDG_PM_SERVER_URL",   "ap12.ragic.com")
FULL_BLDG_PM_ACCOUNT      = getattr(settings, "RAGIC_FULL_BLDG_PM_ACCOUNT",      "soutlet001")
FULL_BLDG_PM_JOURNAL_PATH = getattr(settings, "RAGIC_FULL_BLDG_PM_JOURNAL_PATH", "periodic-maintenance/21")
# 附表路徑：若全棟 items 另有獨立 Sheet 可在 .env 覆寫；預設同主表（子表格模式）
FULL_BLDG_PM_ITEMS_PATH   = getattr(settings, "RAGIC_FULL_BLDG_PM_ITEMS_PATH",   "periodic-maintenance/21")


# ── 轉換輔助函式 ──────────────────────────────────────────────────────────────

def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(_stringify(x) for x in value)
    if isinstance(value, dict):
        return _stringify(value.get("value") or value.get("label") or "")
    return str(value).strip()


def _to_int(val: Any) -> int:
    try:
        return int(float(str(val))) if val not in (None, "", "None") else 0
    except (ValueError, TypeError):
        return 0


def _parse_exec_months(raw: str) -> list[int]:
    """
    "2月 5月 8月 11月"  →  [2, 5, 8, 11]
    "每月"             →  [1,2,3,4,5,6,7,8,9,10,11,12]
    ""                 →  []
    """
    if not raw:
        return []
    raw = str(raw).strip()
    if raw in ("每月", "每月份"):
        return list(range(1, 13))
    months = []
    for part in raw.split():
        m = re.search(r"(\d+)", part)
        if m:
            month = int(m.group(1))
            if 1 <= month <= 12:
                months.append(month)
    return sorted(set(months))


def _normalize_period_month(raw_date: str) -> str:
    """'2026/04/01' → '2026/04'"""
    parts = raw_date.strip().split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return raw_date


def _ragic_batch_to_model(ragic_id: str, raw: dict[str, Any]) -> FullBldgPMBatch:
    rec = FullBldgPMBatch(ragic_id=ragic_id)
    rec.journal_no   = _stringify(raw.get(CK_JOURNAL_NO, ""))
    rec.period_month = _normalize_period_month(_stringify(raw.get(CK_PERIOD_MONTH, "")))
    ts = raw.get("_dataTimestamp")
    if ts:
        try:
            dt_str = datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc).strftime("%Y/%m/%d %H:%M:%S")
            rec.ragic_created_at = dt_str
            rec.ragic_updated_at = dt_str
        except Exception:
            pass
    rec.synced_at = twnow()
    return rec


def _ragic_item_to_model(
    ragic_id: str,
    row_raw: dict[str, Any],
    batch_ragic_id: str,
) -> FullBldgPMItem:
    rec = FullBldgPMItem(ragic_id=ragic_id)
    rec.batch_ragic_id    = batch_ragic_id
    rec.seq_no            = _to_int(row_raw.get(CK_SEQ_NO, 0))
    rec.category          = _stringify(row_raw.get(CK_CATEGORY, ""))
    rec.frequency         = _stringify(row_raw.get(CK_FREQUENCY, ""))
    rec.task_name         = _stringify(row_raw.get(CK_TASK_NAME, ""))
    rec.location          = _stringify(row_raw.get(CK_LOCATION, ""))
    rec.estimated_minutes = _to_int(row_raw.get(CK_EST_HOURS, 0))
    rec.scheduled_date    = _stringify(row_raw.get(CK_SCHED_DATE, ""))
    rec.scheduler_name    = _stringify(row_raw.get(CK_SCHEDULER, ""))
    rec.result_note       = _stringify(row_raw.get(CK_NOTE, ""))
    rec.executor_name     = _stringify(row_raw.get(CK_EXECUTOR, ""))
    rec.start_time        = _stringify(row_raw.get(CK_START_TIME, ""))
    rec.end_time          = _stringify(row_raw.get(CK_END_TIME, ""))
    rec.is_completed      = bool(rec.start_time and rec.end_time)

    exec_months_raw = _stringify(row_raw.get(CK_EXEC_MONTHS, ""))
    rec.exec_months_raw  = exec_months_raw
    rec.exec_months_json = json.dumps(_parse_exec_months(exec_months_raw), ensure_ascii=False)
    rec.synced_at = twnow()
    return rec


# ── 同步主程式 ────────────────────────────────────────────────────────────────

async def sync_batches_from_ragic() -> dict:
    """同步 Sheet 21（主表）→ full_bldg_pm_batch"""
    adapter = RagicAdapter(
        sheet_path=FULL_BLDG_PM_JOURNAL_PATH,
        server_url=FULL_BLDG_PM_SERVER_URL,
        account=FULL_BLDG_PM_ACCOUNT,
    )
    logger.info("[FullBldgPMSync][Batch] 開始同步主表...")
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[FullBldgPMSync][Batch] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    fetched  = len(raw_data)
    upserted = 0
    errors: list[str] = []

    db = SessionLocal()
    try:
        for ragic_id, raw in raw_data.items():
            try:
                new_rec = _ragic_batch_to_model(str(ragic_id), raw)
                existing = db.get(FullBldgPMBatch, str(ragic_id))
                if existing:
                    existing.journal_no       = new_rec.journal_no
                    existing.period_month     = _normalize_period_month(new_rec.period_month)
                    existing.ragic_created_at = new_rec.ragic_created_at
                    existing.ragic_updated_at = new_rec.ragic_updated_at
                    existing.synced_at        = new_rec.synced_at
                else:
                    db.add(new_rec)
                upserted += 1
            except Exception as exc:
                errors.append(f"batch ragic_id={ragic_id}: {exc}")
                logger.warning(f"[FullBldgPMSync][Batch] 記錄 {ragic_id} 失敗：{exc}")
        db.commit()
        logger.info(f"[FullBldgPMSync][Batch] 完成：fetched={fetched}, upserted={upserted}, errors={len(errors)}")
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[FullBldgPMSync][Batch] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {"fetched": fetched, "upserted": upserted, "errors": errors}


async def sync_items_from_ragic() -> dict:
    """
    同步子表格項目 → full_bldg_pm_batch_item

    策略（與商場 PM 完全相同）：
      1. fetch_all() 取得批次 ID 清單
      2. 對每筆批次 ID 呼叫 fetch_one()，取得含子表格的完整記錄
      3. 支援數字 key / 命名 dict / 命名 list / _subtable_* 四種子表格格式
      4. item.ragic_id = "{batch_id}_{row_key}"
    """
    adapter = RagicAdapter(
        sheet_path=FULL_BLDG_PM_ITEMS_PATH,
        server_url=FULL_BLDG_PM_SERVER_URL,
        account=FULL_BLDG_PM_ACCOUNT,
    )
    logger.info("[FullBldgPMSync][Items] 開始同步附表（子表格解析模式）...")
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[FullBldgPMSync][Items] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    if not raw_data:
        logger.warning("[FullBldgPMSync][Items] Ragic 回傳空資料")
        return {"fetched": 0, "upserted": 0, "errors": []}

    batch_ids = list(raw_data.keys())
    logger.info(f"[FullBldgPMSync][Items] 取得 {len(batch_ids)} 筆批次 ID，改用 fetch_one 取子表格：{batch_ids}")

    total_fetched  = 0
    total_upserted = 0
    errors: list[str] = []
    now = twnow()

    db = SessionLocal()
    try:
        # 清除舊格式記錄（ragic_id 不含底線 = 舊版同步遺留）
        old_style = db.query(FullBldgPMItem).filter(
            ~FullBldgPMItem.ragic_id.contains("_")
        ).all()
        if old_style:
            logger.info(f"[FullBldgPMSync][Items] 清除 {len(old_style)} 筆舊格式記錄")
            for it in old_style:
                db.delete(it)
            db.flush()

        for batch_ragic_id in batch_ids:
            batch_id_str = str(batch_ragic_id)
            try:
                full_record = await adapter.fetch_one(batch_id_str)
            except Exception as exc:
                errors.append(f"fetch_one({batch_id_str}): {exc}")
                logger.warning(f"[FullBldgPMSync][Items] fetch_one({batch_id_str}) 失敗：{exc}")
                continue

            # Unwrap fetch_one 外層包裝
            if batch_id_str in full_record and len(full_record) == 1:
                full_record = full_record[batch_id_str]

            # 完整結構診斷
            structure = {}
            for k, v in full_record.items():
                if isinstance(v, dict):
                    structure[k] = f"dict({len(v)}) keys={list(v.keys())[:5]}"
                elif isinstance(v, list):
                    structure[k] = f"list({len(v)})"
                else:
                    structure[k] = repr(v)[:50]
            logger.info(f"[FullBldgPMSync][Items] fetch_one({batch_id_str}) 結構={structure}")

            # 找出子表格列（方式 A/B/C/D，與商場 PM 相同邏輯）
            sub_rows: dict[str, dict] = {}

            # 方式 A：頂層數字 key
            direct_numeric = {
                k: v for k, v in full_record.items()
                if k.lstrip("-").isdigit() and isinstance(v, dict)
            }
            if direct_numeric:
                if len(direct_numeric) == 1:
                    container_key = next(iter(direct_numeric))
                    container_val = direct_numeric[container_key]
                    inner_numeric = {
                        k: v for k, v in container_val.items()
                        if k.lstrip("-").isdigit() and isinstance(v, dict)
                    }
                    if inner_numeric:
                        sub_rows = inner_numeric
                        logger.info(f"[FullBldgPMSync][Items] 批次 {batch_id_str} → 方式A深層 {len(sub_rows)} 列")
                    else:
                        sub_rows = direct_numeric
                        logger.info(f"[FullBldgPMSync][Items] 批次 {batch_id_str} → 方式A {len(sub_rows)} 列")
                else:
                    sub_rows = direct_numeric
                    logger.info(f"[FullBldgPMSync][Items] 批次 {batch_id_str} → 方式A {len(sub_rows)} 列")

            # 方式 B：命名 key → dict（key 為數字）
            if not sub_rows:
                for k, v in full_record.items():
                    if k.startswith("_"):
                        continue
                    if isinstance(v, dict) and len(v) > 0:
                        first_sub = next(iter(v.keys()), "")
                        if first_sub.lstrip("-").isdigit():
                            sub_rows = {rk: rv for rk, rv in v.items() if isinstance(rv, dict)}
                            logger.info(f"[FullBldgPMSync][Items] 批次 {batch_id_str} → 方式B('{k}') {len(sub_rows)} 列")
                            break

            # 方式 C：命名 key → list of dicts
            if not sub_rows:
                for k, v in full_record.items():
                    if k.startswith("_"):
                        continue
                    if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                        sub_rows = {str(i + 1): row for i, row in enumerate(v)}
                        logger.info(f"[FullBldgPMSync][Items] 批次 {batch_id_str} → 方式C('{k}') {len(sub_rows)} 列")
                        break

            # 方式 D：_subtable_* key
            if not sub_rows:
                for k, v in full_record.items():
                    if not k.startswith("_subtable_"):
                        continue
                    if not isinstance(v, dict) or len(v) == 0:
                        continue
                    inner_numeric = {
                        rk: rv for rk, rv in v.items()
                        if rk.lstrip("-").isdigit() and isinstance(rv, dict)
                    }
                    if inner_numeric:
                        sub_rows = inner_numeric
                        logger.info(f"[FullBldgPMSync][Items] 批次 {batch_id_str} → 方式D('{k}') {len(sub_rows)} 列")
                        break
                    inner_dicts = {rk: rv for rk, rv in v.items() if isinstance(rv, dict)}
                    if inner_dicts:
                        sub_rows = inner_dicts
                        logger.info(f"[FullBldgPMSync][Items] 批次 {batch_id_str} → 方式D-b('{k}') {len(sub_rows)} 列")
                        break

            if not sub_rows:
                logger.warning(f"[FullBldgPMSync][Items] 批次 {batch_id_str} 無子表格，keys={list(full_record.keys())}")
                continue

            # 診斷第一列
            first_row_key = next(iter(sub_rows))
            first_row_val = sub_rows[first_row_key]
            logger.info(f"[FullBldgPMSync][Items] 第一子列 key='{first_row_key}' 內容={dict(list(first_row_val.items())[:8])}")

            logger.info(f"[FullBldgPMSync][Items] 批次 {batch_id_str} → 解析 {len(sub_rows)} 列")
            total_fetched += len(sub_rows)

            for row_key, row_raw in sub_rows.items():
                item_id = f"{batch_id_str}_{row_key}"
                try:
                    new_rec = _ragic_item_to_model(item_id, row_raw, batch_id_str)
                    existing = db.get(FullBldgPMItem, item_id)

                    if existing:
                        existing.batch_ragic_id    = batch_id_str
                        existing.seq_no            = new_rec.seq_no
                        existing.category          = new_rec.category
                        existing.frequency         = new_rec.frequency
                        existing.exec_months_raw   = new_rec.exec_months_raw
                        existing.exec_months_json  = new_rec.exec_months_json
                        existing.task_name         = new_rec.task_name
                        existing.location          = new_rec.location or ""
                        existing.estimated_minutes = new_rec.estimated_minutes
                        existing.scheduled_date    = new_rec.scheduled_date
                        existing.scheduler_name    = new_rec.scheduler_name
                        existing.result_note       = new_rec.result_note
                        existing.executor_name     = new_rec.executor_name
                        existing.start_time        = new_rec.start_time
                        existing.end_time          = new_rec.end_time
                        existing.is_completed      = new_rec.is_completed
                        existing.synced_at         = now
                    else:
                        db.add(new_rec)

                    total_upserted += 1
                except Exception as exc:
                    errors.append(f"item {item_id}: {exc}")
                    logger.warning(f"[FullBldgPMSync][Items] 項目 {item_id} 失敗：{exc}")

        db.commit()
        logger.info(
            f"[FullBldgPMSync][Items] 完成："
            f"batches={len(raw_data)}, items_fetched={total_fetched}, "
            f"upserted={total_upserted}, errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[FullBldgPMSync][Items] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {"fetched": total_fetched, "upserted": total_upserted, "errors": errors}


def _fix_period_month_format(db) -> int:
    fixed = 0
    try:
        batches = db.query(FullBldgPMBatch).all()
        for b in batches:
            normalized = _normalize_period_month(b.period_month)
            if normalized != b.period_month:
                b.period_month = normalized
                fixed += 1
        if fixed:
            db.commit()
            logger.info(f"[FullBldgPMSync] period_month 格式修正：{fixed} 筆")
    except Exception as exc:
        db.rollback()
        logger.warning(f"[FullBldgPMSync] period_month 修正失敗：{exc}")
    return fixed


async def sync_from_ragic() -> dict:
    """完整同步：先同步主表，再同步附表。"""
    batch_result = await sync_batches_from_ragic()
    items_result = await sync_items_from_ragic()

    db = SessionLocal()
    try:
        _fix_period_month_format(db)
    finally:
        db.close()

    return {
        "batches": batch_result,
        "items":   items_result,
    }
