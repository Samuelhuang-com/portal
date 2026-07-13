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
from app.models.full_building_maintenance import FullBldgPMBatch, FullBldgPMItem, FullBldgPMItemWorklog
from app.models.full_bldg_pm_schedule import FullBldgPMSchedule
from app.services.ragic_adapter import RagicAdapter
from app.services.ragic_data_service import parse_images
from app.services.sync_dispatcher import register

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

# ── Ragic 連線設定（主表）────────────────────────────────────────────────────
FULL_BLDG_PM_SERVER_URL   = getattr(settings, "RAGIC_FULL_BLDG_PM_SERVER_URL",   "ap12.ragic.com")
FULL_BLDG_PM_ACCOUNT      = getattr(settings, "RAGIC_FULL_BLDG_PM_ACCOUNT",      "soutlet001")
FULL_BLDG_PM_JOURNAL_PATH = getattr(settings, "RAGIC_FULL_BLDG_PM_JOURNAL_PATH", "periodic-maintenance/21")
# 附表路徑：若全棟 items 另有獨立 Sheet 可在 .env 覆寫；預設同主表（子表格模式）
FULL_BLDG_PM_ITEMS_PATH   = getattr(settings, "RAGIC_FULL_BLDG_PM_ITEMS_PATH",   "periodic-maintenance/21")

# ── Ragic Sheet 28（子表平鋪視圖）欄位 key ──────────────────────────────────
# Sheet 28 = 全棟週期保養日誌(同仁執行) — 子表:項目
# https://ap12.ragic.com/soutlet001/periodic-maintenance/28
FULL_BLDG_PM_SHEET28_PATH = getattr(settings, "RAGIC_FULL_BLDG_PM_SHEET28_PATH", "periodic-maintenance/28")
CK28_REPAIR_HOURS = "維修工時"   # 實際維修工時（小時）
CK28_START_TIME   = "保養時間啟"  # 保養開始時間（補強既有欄位）
CK28_END_TIME     = "保養時間迄"  # 保養結束時間（補強既有欄位）
CK28_TASK_NAME    = "項目"        # 保養項目名稱（配對用）
CK28_CATEGORY     = "類別"        # 類別（配對用）
CK28_PARENT_REF   = "保養日誌編號" # ⚠️ 2026-07-13 實測：Sheet28 實際欄位 key 是「編號」，
                                   # 不是「保養日誌編號」，此常數與下方 sync_repair_hours_from_sheet28()
                                   # 已確認長期失效（策略②從未命中）。保留舊常數/舊函式僅供對照，
                                   # 新版同步請見下方 CK28L_*/CK28S_* 與 sync_items_from_sheet28()。

# ── Sheet 28 列表模式（fetch_all）欄位 key（2026-07-13 實測驗證，用於新版主要同步）──
# 實測發現：
#   1. fetch_all() 列表模式「不含」CK28_START_TIME / CK28_END_TIME / 巢狀子表格，
#      這兩個欄位與子表格只存在於 fetch_one() 單筆結果中。
#   2. Sheet28 沒有獨立的「位置」欄位（與 Sheet21 子表格不同，實測確認不存在）。
#   3. 「執行月份」「排定人員」「執行人員」在 Sheet28 回傳格式是陣列，非字串。
#   4. 「排定日期」是完整日期「YYYY/MM/DD」，需正規化為既有系統使用的「MM/DD」格式。
CK28L_SEQ_NO       = "項次"
CK28L_PARENT_REF   = "編號"        # 連回 Sheet21 主表「編號」欄位（實測確認為此 key）
CK28L_CATEGORY     = "類別"
CK28L_EXEC_MONTHS  = "執行月份"
CK28L_TASK_NAME    = "項目"
CK28L_EST_MINUTES  = "預估耗時"
CK28L_FREQUENCY    = "頻率"
CK28L_SCHEDULER    = "排定人員"
CK28L_SCHED_DATE   = "排定日期"
CK28L_EXECUTOR     = "執行人員"
CK28L_NOTE         = "備註"
CK28L_REPAIR_HOURS = "維修工時"
CK28L_IMAGES       = "圖片上傳"   # 2026-07-13 新增：只有 fetch_one() 全量結果才有實際檔名清單

# ── Sheet 28 每筆記錄底下巢狀子表格「維修記錄」欄位 key（僅 fetch_one 才有，實測驗證）──
# Ragic 內部子表格 key 為 _subtable_<動態數字>（本帳號實測為 _subtable_1015852，
# 但此數字為 Ragic 內部欄位 ID，不同環境/未來欄位異動可能不同，程式以
# 「任何以 _subtable_ 開頭的 key」通用偵測，不寫死此數字）。
CK28S_SEQ_NO     = "項次"
CK28S_NOTE       = "維修記錄"
CK28S_START_TIME = "時間開始"
CK28S_END_TIME   = "時間結束"
CK28S_STAFF      = "保養人員"


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
    orphan_removed = 0
    errors: list[str] = []
    fetched_ids = {str(k) for k in raw_data.keys()}

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

        # ── 清除孤兒批次（2026-07-13 發現）───────────────────────────────────
        # 舊版邏輯只做 upsert，Ragic 端刪除/重編過的記錄永遠不會從 Portal 清掉。
        # 實測發現 full_bldg_pm_batch 裡有 ragic_id 在 Ragic 已經不存在的孤兒
        # 資料（period_month 停留在刪除前的舊值，可能跟其他仍有效的批次 journal_no
        # 撞在一起，造成 /stats 等用 period_month 查批次時选到錯誤/過期的那筆）。
        # 這裡連同其底下的孤兒項目與維修記錄一併清除。
        orphan_batches = db.query(FullBldgPMBatch).filter(
            ~FullBldgPMBatch.ragic_id.in_(fetched_ids)
        ).all() if fetched_ids else []
        if orphan_batches:
            orphan_ids = [b.ragic_id for b in orphan_batches]
            logger.warning(
                f"[FullBldgPMSync][Batch] 發現 {len(orphan_batches)} 筆孤兒批次"
                f"（Ragic 已無對應記錄，予以刪除）：{[(b.ragic_id, b.journal_no, b.period_month) for b in orphan_batches]}"
            )
            orphan_item_ids = [
                it.ragic_id for it in
                db.query(FullBldgPMItem).filter(FullBldgPMItem.batch_ragic_id.in_(orphan_ids)).all()
            ]
            if orphan_item_ids:
                db.query(FullBldgPMItemWorklog).filter(
                    FullBldgPMItemWorklog.item_ragic_id.in_(orphan_item_ids)
                ).delete(synchronize_session=False)
                db.query(FullBldgPMItem).filter(
                    FullBldgPMItem.ragic_id.in_(orphan_item_ids)
                ).delete(synchronize_session=False)
            for b in orphan_batches:
                db.delete(b)
            orphan_removed = len(orphan_batches)

        db.commit()
        logger.info(
            f"[FullBldgPMSync][Batch] 完成：fetched={fetched}, upserted={upserted}, "
            f"orphan_batches_removed={orphan_removed}, errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[FullBldgPMSync][Batch] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {"fetched": fetched, "upserted": upserted, "orphan_batches_removed": orphan_removed, "errors": errors}


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

            # ── 批次全量替換（2026-07-01 修正）：先清空此批次現有項目，避免
            #    過去解析出的不同 row_key（同一任務、不同 ragic_id）長期殘留
            #    於 DB，造成行事曆重複顯示同一保養任務 ────────────────────────
            deleted_in_batch = db.query(FullBldgPMItem).filter(
                FullBldgPMItem.batch_ragic_id == batch_id_str
            ).delete()
            if deleted_in_batch:
                logger.info(f"[FullBldgPMSync][Items] 批次 {batch_id_str} 清空舊項目 {deleted_in_batch} 筆")

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


def _to_float(val: Any) -> float | None:
    """將 Ragic 值轉為 float，無法轉換時回傳 None。"""
    try:
        v = str(val).strip()
        return float(v) if v not in ("", "None", "null", "-") else None
    except (ValueError, TypeError):
        return None


async def sync_repair_hours_from_sheet28() -> dict:
    """
    從 Ragic Sheet 28（子表平鋪視圖）同步：
      - 維修工時（repair_hours）
      - 保養時間啟（start_time）
      - 保養時間迄（end_time）

    三層配對策略（同 mall/periodic-maintenance 的 Sheet 24 模式）：
      策略 1：sheet28_id 直接比對（最快，O(1)）
      策略 2：batch_ragic_id（保養日誌編號）+ task_name + category
      策略 3：task_name + category 跨批次，取最近一筆（最後手段）
    """
    adapter = RagicAdapter(
        server_url  = FULL_BLDG_PM_SERVER_URL,
        account     = FULL_BLDG_PM_ACCOUNT,
        api_key     = settings.RAGIC_API_KEY,
        sheet_path  = FULL_BLDG_PM_SHEET28_PATH,
    )

    try:
        raw_records = adapter.fetch_all()
    except Exception as exc:
        logger.error("[FullBldgPMSync][Sheet28] fetch_all 失敗：%s", exc)
        return {"error": str(exc), "updated": 0, "skipped": 0}

    if not isinstance(raw_records, dict):
        logger.warning("[FullBldgPMSync][Sheet28] 非預期格式：%s", type(raw_records))
        return {"error": "unexpected_format", "updated": 0, "skipped": 0}

    db = SessionLocal()
    updated = skipped = no_match = 0

    try:
        for sheet28_rec_id, row in raw_records.items():
            if not isinstance(row, dict):
                continue

            # ── 擷取 Sheet 28 欄位值 ──────────────────────────────────────────
            repair_hours_raw = _stringify(row.get(CK28_REPAIR_HOURS, ""))
            start_time_raw   = _stringify(row.get(CK28_START_TIME, ""))
            end_time_raw     = _stringify(row.get(CK28_END_TIME, ""))
            task_name        = _stringify(row.get(CK28_TASK_NAME, ""))
            category         = _stringify(row.get(CK28_CATEGORY, ""))
            parent_ref       = _stringify(row.get(CK28_PARENT_REF, ""))

            repair_hours = _to_float(repair_hours_raw)

            # 三個欄位全為空 → 跳過
            if not repair_hours and not start_time_raw and not end_time_raw:
                skipped += 1
                continue

            # ── 策略 1：sheet28_id 直接比對 ──────────────────────────────────
            target: FullBldgPMItem | None = (
                db.query(FullBldgPMItem)
                .filter(FullBldgPMItem.sheet28_id == str(sheet28_rec_id))
                .first()
            )

            # ── 策略 2：batch_ragic_id + task_name + category ─────────────────
            if target is None and parent_ref and task_name:
                target = (
                    db.query(FullBldgPMItem)
                    .filter(
                        FullBldgPMItem.batch_ragic_id == parent_ref,
                        FullBldgPMItem.task_name      == task_name,
                        FullBldgPMItem.category       == category,
                    )
                    .first()
                )

            # ── 策略 3：task_name + category 跨批次（取最近一筆）─────────────
            if target is None and task_name:
                candidates = (
                    db.query(FullBldgPMItem)
                    .filter(
                        FullBldgPMItem.task_name == task_name,
                        FullBldgPMItem.category  == category,
                    )
                    .all()
                )
                if candidates:
                    target = max(candidates, key=lambda x: x.batch_ragic_id or "")

            if target is None:
                logger.debug(
                    "[FullBldgPMSync][Sheet28] 無法配對：sheet28_id=%s task=%s cat=%s parent=%s",
                    sheet28_rec_id, task_name, category, parent_ref,
                )
                no_match += 1
                continue

            # ── 寫入三個欄位（若有值才覆蓋；空字串亦覆蓋，讓資料以 Sheet 28 為準）──
            changed = False
            if repair_hours is not None:
                target.repair_hours = repair_hours
                changed = True
            if start_time_raw:
                target.start_time = start_time_raw
                changed = True
            if end_time_raw:
                target.end_time = end_time_raw
                changed = True
            # 重算完成狀態
            if changed:
                target.is_completed = bool(target.start_time and target.end_time)
                target.sheet28_id   = str(sheet28_rec_id)
                updated += 1

        db.commit()
        logger.info(
            "[FullBldgPMSync][Sheet28] 完成：updated=%d skipped=%d no_match=%d",
            updated, skipped, no_match,
        )
    except Exception as exc:
        db.rollback()
        logger.error("[FullBldgPMSync][Sheet28] commit 失敗：%s", exc, exc_info=True)
        return {"error": str(exc), "updated": updated, "skipped": skipped}
    finally:
        db.close()

    return {"updated": updated, "skipped": skipped, "no_match": no_match}


def _normalize_full_date_to_md(raw: str) -> str:
    """
    'YYYY/MM/DD' -> 'MM/DD'（配合既有 scheduled_date 欄位 / _calc_status() 短格式）。
    格式不符（非三段 '/')時原樣回傳，不猜測。
    """
    if not raw:
        return ""
    parts = str(raw).strip().split("/")
    if len(parts) == 3:
        return f"{parts[1]}/{parts[2]}"
    return raw


def _find_worklog_subtable(full_record: dict[str, Any]) -> dict[str, dict]:
    """
    從 fetch_one() 結果中找出巢狀子表格「維修記錄」。
    Ragic 內部 key 為 _subtable_<動態數字>，不寫死數字，取第一個非空 dict。
    """
    for k, v in full_record.items():
        if not k.startswith("_subtable_"):
            continue
        if isinstance(v, dict) and v:
            inner = {rk: rv for rk, rv in v.items() if isinstance(rv, dict)}
            if inner:
                return inner
    return {}


async def sync_items_from_sheet28() -> dict:
    """
    全棟例行維護項目明細同步 —— 2026-07-13 起改以 Ragic Sheet 28 為主要來源。

    背景：Sheet 21 子表格需靠 fetch_one() 猜測子表格藏在哪個 key（A/B/C/D 四種模式），
    且無法取得逐筆維修記錄明細（時間起訖、保養人員），只能取到彙總數字。Sheet 28
    的每個項目本身就是一筆平鋪記錄，不需要猜格式；其巢狀子表格「維修記錄」則需逐筆
    fetch_one() 取得（見 CK28S_* 欄位 key，2026-07-13 實測驗證）。

    批次層（full_bldg_pm_batch）仍由 sync_batches_from_ragic()（Sheet 21 主表）負責
    同步 —— 實測確認 Sheet21 主表「編號」與 Sheet28 每筆項目的「編號」欄位值完全一致，
    因此本函式用「編號」比對回已同步的批次，batch_ragic_id 語意（Sheet21 內部數字 ID）
    維持不變，不影響既有 Ragic 深連結組法。

    找不到對應批次的項目（「編號」為空、或該批次尚未由 Sheet21 同步）一律明確跳過並
    記錄在回傳的 unmatched_batches，不做任何猜測式配對。
    """
    adapter = RagicAdapter(
        sheet_path=FULL_BLDG_PM_SHEET28_PATH,
        server_url=FULL_BLDG_PM_SERVER_URL,
        account=FULL_BLDG_PM_ACCOUNT,
    )
    logger.info("[FullBldgPMSync][Sheet28Items] 開始同步項目明細（Sheet28 為主要來源）...")
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[FullBldgPMSync][Sheet28Items] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "worklogs": 0, "errors": [str(exc)], "unmatched_batches": []}

    if not raw_data:
        logger.warning("[FullBldgPMSync][Sheet28Items] Ragic 回傳空資料")
        return {"fetched": 0, "upserted": 0, "worklogs": 0, "errors": [], "unmatched_batches": []}

    fetched  = len(raw_data)
    upserted = 0
    worklog_upserted = 0
    items_with_images = 0
    errors: list[str] = []
    unmatched_journal_nos: set[str] = set()
    journal_collisions: dict[str, list[str]] = {}
    old_style: list = []
    now = twnow()

    db = SessionLocal()
    try:
        # ── 清除舊格式殘留項目（2026-07-13 架構調整後發現）──────────────────────
        # 舊版 sync_items_from_ragic()（Sheet21 子表格解析）用的 ragic_id 是
        # "{batch_id}_{row_key}" 複合格式（如 "4_225"，含底線）；新版直接採用
        # Sheet28 項目自身的數字 ragic_id（如 "294"，不含底線）。兩種格式的
        # primary key 不同，若不清除，舊資料會與新同步的資料同時存在，造成每個
        # 項目重複兩筆。此清除只在資料庫仍殘留舊格式資料時才會實際刪除任何東西。
        #
        # ⚠️ 注意：舊格式項目上若有 Portal 標記過的 abnormal_flag/abnormal_note，
        # 會隨這次清除一併移除（新格式項目是全新 insert，不会繼承）。若需要保留，
        # 請在本次同步前先手動查詢並記錄。
        old_style = db.query(FullBldgPMItem).filter(
            FullBldgPMItem.ragic_id.contains("_")
        ).all()
        old_style_abnormal = [it for it in old_style if it.abnormal_flag]
        if old_style_abnormal:
            logger.warning(
                f"[FullBldgPMSync][Sheet28Items] 即將清除的 {len(old_style)} 筆舊格式項目中，"
                f"有 {len(old_style_abnormal)} 筆帶有 abnormal_flag=True，異常標記將遺失："
                f"{[it.ragic_id for it in old_style_abnormal]}"
            )
        if old_style:
            logger.info(f"[FullBldgPMSync][Sheet28Items] 清除 {len(old_style)} 筆舊格式（Sheet21子表格解析）殘留項目")
            for it in old_style:
                db.delete(it)
            db.flush()

        # ── 清除 full_bldg_pm_schedule 舊格式殘留排程（2026-07-13 發現，比照上方 item 清除、
        # 以及 mall_pm 同日修正）────────────────────────────────────────────────────
        # full_bldg_pm_schedule（Portal 自有排程表）以 (year_month, item_ragic_id) 判斷
        # 排程是否已存在（見 generate_full_bldg_schedule()）。item_ragic_id 格式由
        # "{batch_id}_{row_key}"（如 "4_225"）改為 Sheet28 原始 ragic_id（如 "294"）後，
        # 「產生本月排程」比對不到舊記錄，會另外新增一筆新格式記錄，卻不會清掉舊記錄，
        # 導致同一項目同一天在行事曆／排程列表上重複出現兩筆（且日期可能不一致，因為
        # 舊記錄的排定日期是改版前的舊資料，不會再更新）。此清除只在資料庫仍殘留舊格式
        # 排程時才會實際刪除任何東西（2026-07-13 實測本表尚無殘留，此為預防性修正）。
        #
        # ⚠️ 注意：舊格式排程上若有人工已完成／已標記異常／人工調整過（is_completed=True、
        # abnormal_flag=True、portal_edited_at 有值、或已填 start_time/end_time），會隨
        # 這次清除一併移除且不會被新格式記錄繼承。若偵測到這類記錄，只記錄警告、不刪除，
        # 避免遺失人工資料（需人工確認後手動處理）。
        old_style_sched_all = db.query(FullBldgPMSchedule).filter(
            FullBldgPMSchedule.item_ragic_id.contains("_")
        ).all()
        old_style_sched_risky = [
            s for s in old_style_sched_all
            if s.is_completed or s.abnormal_flag or s.portal_edited_at is not None
            or s.start_time or s.end_time
        ]
        old_style_sched_safe = [s for s in old_style_sched_all if s not in old_style_sched_risky]
        if old_style_sched_risky:
            logger.warning(
                f"[FullBldgPMSync][Sheet28Items] {len(old_style_sched_risky)} 筆舊格式 "
                f"full_bldg_pm_schedule 記錄帶有人工資料（已完成／異常／人工調整／已填執行時間），"
                f"保留不刪除，請人工確認後處理："
                f"{[(s.id, s.item_ragic_id, s.task_name) for s in old_style_sched_risky]}"
            )
        if old_style_sched_safe:
            logger.info(
                f"[FullBldgPMSync][Sheet28Items] 清除 {len(old_style_sched_safe)} 筆舊格式"
                f"（item_ragic_id 含底線）殘留 full_bldg_pm_schedule 排程記錄"
            )
            for s in old_style_sched_safe:
                db.delete(s)
            db.flush()

        # 「編號」→ batch_ragic_id 對照表，來源為 sync_batches_from_ragic() 已同步的批次
        # 防禦性檢查：若同一個「編號」對應到兩筆批次（理論上不該發生，2026-07-13
        # 曾因孤兒批次殘留而撞號），記錄警告並以較新的 ragic_created_at/ragic_id 為準，
        # 而不是靜默覆蓋。
        all_batches = db.query(FullBldgPMBatch).all()
        journal_to_batch: dict[str, str] = {}
        journal_collisions: dict[str, list[str]] = {}
        for b in all_batches:
            if not b.journal_no:
                continue
            if b.journal_no in journal_to_batch and journal_to_batch[b.journal_no] != b.ragic_id:
                journal_collisions.setdefault(b.journal_no, [journal_to_batch[b.journal_no]]).append(b.ragic_id)
            journal_to_batch[b.journal_no] = b.ragic_id
        if journal_collisions:
            logger.warning(
                f"[FullBldgPMSync][Sheet28Items] 發現「編號」撞號的批次（同一編號對應多個 batch ragic_id，"
                f"可能有孤兒批次尚未清除，請檢查 full_bldg_pm_batch）：{journal_collisions}"
            )

        for item_ragic_id, raw in raw_data.items():
            item_id = str(item_ragic_id)
            try:
                journal_no = _stringify(raw.get(CK28L_PARENT_REF, ""))
                batch_ragic_id = journal_to_batch.get(journal_no)
                if not batch_ragic_id:
                    unmatched_journal_nos.add(journal_no or "(空白)")
                    continue

                exec_months_raw    = _stringify(raw.get(CK28L_EXEC_MONTHS, ""))
                scheduled_date_md  = _normalize_full_date_to_md(_stringify(raw.get(CK28L_SCHED_DATE, "")))
                repair_hours       = _to_float(_stringify(raw.get(CK28L_REPAIR_HOURS, "")))

                # ── 逐筆項目 fetch_one() 取得巢狀「維修記錄」子表格 + 附圖 ──────────
                # 圖片欄位「圖片上傳」只有 fetch_one() 全量結果才會回傳實際檔名清單，
                # listing 模式（fetch_all）恆為空字串，所以跟維修記錄共用同一次 fetch_one()。
                try:
                    full_record = await adapter.fetch_one(item_id)
                    if item_id in full_record and len(full_record) == 1:
                        full_record = full_record[item_id]
                    sub_rows = _find_worklog_subtable(full_record)
                    images = parse_images(
                        full_record.get(CK28L_IMAGES),
                        server=FULL_BLDG_PM_SERVER_URL,
                        account=FULL_BLDG_PM_ACCOUNT,
                    )
                except Exception as exc:
                    sub_rows = {}
                    images = []
                    errors.append(f"fetch_one(item={item_id}) 維修記錄/附圖失敗：{exc}")
                    logger.warning(f"[FullBldgPMSync][Sheet28Items] fetch_one({item_id}) 失敗：{exc}")

                # 全量替換此項目的 worklog（避免舊 row_key 殘留）
                db.query(FullBldgPMItemWorklog).filter(
                    FullBldgPMItemWorklog.item_ragic_id == item_id
                ).delete()

                worklog_starts: list[str] = []
                worklog_ends: list[str] = []
                for sub_key, sub_row in sub_rows.items():
                    wl_start = _stringify(sub_row.get(CK28S_START_TIME, ""))
                    wl_end   = _stringify(sub_row.get(CK28S_END_TIME, ""))
                    if wl_start:
                        worklog_starts.append(wl_start)
                    if wl_end:
                        worklog_ends.append(wl_end)
                    db.add(FullBldgPMItemWorklog(
                        ragic_id=f"{item_id}_{sub_key}",
                        item_ragic_id=item_id,
                        seq_no=_to_int(sub_row.get(CK28S_SEQ_NO, 0)),
                        repair_note=_stringify(sub_row.get(CK28S_NOTE, "")),
                        start_time=wl_start,
                        end_time=wl_end,
                        staff_name=_stringify(sub_row.get(CK28S_STAFF, "")),
                        synced_at=now,
                    ))
                    worklog_upserted += 1

                # start_time/end_time 取巢狀子表格最早開始／最晚結束
                # （Sheet28 頂層「保養時間啟/迄」欄位 2026-07-13 實測恆為空，不可用）
                start_time = min(worklog_starts) if worklog_starts else ""
                end_time   = max(worklog_ends) if worklog_ends else ""

                existing = db.get(FullBldgPMItem, item_id)
                if existing:
                    target = existing
                else:
                    target = FullBldgPMItem(ragic_id=item_id)
                    db.add(target)

                target.batch_ragic_id    = batch_ragic_id
                target.seq_no            = _to_int(raw.get(CK28L_SEQ_NO, 0))
                target.category          = _stringify(raw.get(CK28L_CATEGORY, ""))
                target.frequency         = _stringify(raw.get(CK28L_FREQUENCY, ""))
                target.task_name         = _stringify(raw.get(CK28L_TASK_NAME, ""))
                # location：Sheet28 實測無獨立「位置」欄位，不覆蓋既有值（新項目維持空字串）
                target.estimated_minutes = _to_int(raw.get(CK28L_EST_MINUTES, 0))
                target.scheduled_date    = scheduled_date_md
                target.scheduler_name    = _stringify(raw.get(CK28L_SCHEDULER, ""))
                target.result_note       = _stringify(raw.get(CK28L_NOTE, ""))
                target.executor_name     = _stringify(raw.get(CK28L_EXECUTOR, ""))
                target.start_time        = start_time
                target.end_time          = end_time
                target.is_completed      = bool(start_time and end_time)
                target.exec_months_raw   = exec_months_raw
                target.exec_months_json  = json.dumps(_parse_exec_months(exec_months_raw), ensure_ascii=False)
                target.repair_hours      = repair_hours
                target.sheet28_id        = item_id
                target.images_json       = json.dumps(images, ensure_ascii=False)
                target.synced_at         = now

                if images:
                    items_with_images += 1
                upserted += 1
            except Exception as exc:
                errors.append(f"item {item_id}: {exc}")
                logger.warning(f"[FullBldgPMSync][Sheet28Items] 項目 {item_id} 失敗：{exc}")

        db.commit()
        if unmatched_journal_nos:
            logger.warning(
                f"[FullBldgPMSync][Sheet28Items] {len(unmatched_journal_nos)} 個「編號」在 "
                f"full_bldg_pm_batch 找不到對應批次，已跳過未同步：{sorted(unmatched_journal_nos)}"
            )
        logger.info(
            f"[FullBldgPMSync][Sheet28Items] 完成：fetched={fetched}, upserted={upserted}, "
            f"worklogs={worklog_upserted}, items_with_images={items_with_images}, "
            f"errors={len(errors)}, unmatched_batches={len(unmatched_journal_nos)}"
        )
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[FullBldgPMSync][Sheet28Items] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {
        "fetched": fetched,
        "upserted": upserted,
        "worklogs": worklog_upserted,
        "items_with_images": items_with_images,
        "old_style_removed": len(old_style),
        "old_style_abnormal_lost": [it.ragic_id for it in old_style_abnormal],
        "schedule_old_style_removed": len(old_style_sched_safe),
        "schedule_old_style_kept_risky": [
            {"id": s.id, "item_ragic_id": s.item_ragic_id, "task_name": s.task_name}
            for s in old_style_sched_risky
        ],
        "journal_collisions": journal_collisions,
        "errors": errors,
        "unmatched_batches": sorted(unmatched_journal_nos),
    }


@register("full_building_maintenance")
async def sync_from_ragic() -> dict:
    """
    完整同步：主表（Sheet21）→ 項目明細（Sheet28 為主要來源，含維修記錄明細）。

    2026-07-13 架構調整：項目明細主要來源由 Sheet21 子表格改為 Sheet28。
    舊版 sync_items_from_ragic() / sync_repair_hours_from_sheet28() 仍保留在本檔案中
    （未刪除、未呼叫），供比對驗證或回退使用。
    """
    batch_result = await sync_batches_from_ragic()
    items_result = await sync_items_from_sheet28()

    db = SessionLocal()
    try:
        _fix_period_month_format(db)
    finally:
        db.close()

    return {
        "batches": batch_result,
        "items":   items_result,
    }
