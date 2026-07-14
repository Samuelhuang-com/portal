"""
週期保養表同步服務：Ragic → SQLite

【2026-07-14 起主要來源改為 Sheet 11（平表），Sheet 6／Sheet 8 正式退役】
  Sheet 11：https://ap12.ragic.com/soutlet001/periodic-maintenance/11

  背景：docs/FEASIBILITY_hotel_pm_sheet6_11.md（2026-05-27）評估過把 Sheet 8
  內嵌子表格改為 Sheet 11 平表。2026-07-14 使用者指示啟動遷移，並額外確認
  「Sheet 6（批次主表）也一併退役」——這點與 mall/periodic-maintenance 實際做法
  不同（mall_pm 保留 Sheet 18 當批次來源，只換項目來源改 Sheet 24），是使用者
  明確要求後的差異決策。細節與已知風險見 project memory
  project_hotel_pm_sheet11_migration.md。

  即時查證（2026-07-14，用瀏覽器直連 Ragic ?api&v=3，不採用 5 月舊評估文件結論）
  確認：
    - Sheet 11 單筆完整讀取（fetch_one）已有「保養時間啟」「保養時間迄」欄位
      （5 月評估的「風險 A：時間欄位缺失」已解決，Ragic 端已補上）。
    - 仍然沒有獨立「位置」欄位（5 月評估的風險 B，維持原判斷：低影響，可接受）。
    - 沒有巢狀「維修記錄」子表格（跟 mall_pm 的 Sheet24 不同），是「一組保養時間
      啟/迄 + 一個彙總維修工時」的結構，跟舊 Sheet 8 概念相同，只是搬到平表、
      每筆項目有獨立 _ragicId。
    - listing 模式（fetch_all）抓不到「保養時間啟/迄」「預估耗時」「備註」
      「圖片上傳」，要逐筆 fetch_one() 才有（跟 mall_pm Sheet24 的既有經驗一致）。
    - Sheet 11 目前只依「編號」記錄批次歸屬，沒有獨立批次記錄／日期欄位；
      批次月份改由「編號」內嵌的 YYYYMM 反推（見 _period_month_from_journal_no()）。

  【已知資料缺口】2026-07-14 查證時，202606-001（6月批次）在 Sheet 11 完全沒有
  對應項目（Sheet 6 舊資料裡仍有這筆批次記錄）。使用者已確認「缺口先不管，直接
  開始遷移」——本檔案的新同步邏輯只會 upsert Sheet 11 目前實際回傳的資料，
  不會刪除任何既有 DB 記錄，所以缺口月份的舊資料（若先前已透過 Sheet 6/8 同步過）
  會維持同步前的狀態（不會被清空，但也不會再更新），不是真的整批消失。

  舊版 Sheet 6 + Sheet 8 同步函式（sync_batches_from_ragic / sync_items_from_ragic）
  保留在本檔案中未刪除、未被 sync_from_ragic() 呼叫，供比對或回退使用。

【Sheet 11 平表結構】
  - fetch_all()（listing 模式）：{"_ragicId": {項次/編號/類別/執行月份/項目/頻率/
    排定人員/排定日期/執行人員/維修工時, ...}, ...}，每筆本身就是一個獨立保養項目
    （不需要子表格解析）。
  - fetch_one(ragic_id)：額外含「保養時間啟」「保養時間迄」「預估耗時」「備註」
    「圖片上傳」。
  - item.ragic_id 直接採用 Sheet 11 自身的 _ragicId（不再是 "{batch_id}_{row_key}"
    組合格式）。
  - 批次由「編號」欄位分組合成，沒有獨立 Ragic 記錄。
"""
import json
import logging
import re
from datetime import datetime, timezone
from app.core.time import twnow
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.periodic_maintenance import (
    PeriodicMaintenanceBatch, PeriodicMaintenanceItem, PeriodicMaintenanceItemWorklog,
)
from app.models.pm_schedule import PMSchedule
from app.services.ragic_adapter import RagicAdapter
from app.services.ragic_data_service import parse_images
from app.services.sync_dispatcher import register

logger = logging.getLogger(__name__)

# ── Ragic 中文欄位 key（舊 Sheet 6 主表，已停用，僅供 sync_batches_from_ragic() 參考）──
CK_JOURNAL_NO    = "編號"
CK_PERIOD_MONTH  = "日期"

# ── Ragic 中文欄位 key（舊 Sheet 8 子表格列，已停用，僅供 sync_items_from_ragic() 參考）──
CK_SEQ_NO       = "項次"
CK_CATEGORY     = "類別"
CK_FREQUENCY    = "頻率"
CK_EXEC_MONTHS  = "執行月份"
CK_TASK_NAME    = "項目"
CK_LOCATION     = "位置"        # Sheet 8 無此欄，保留用於未來
CK_EST_HOURS    = "預估耗時"
CK_SCHED_DATE   = "排定日期"
CK_SCHEDULER    = "排定人員"
CK_NOTE         = "備註"        # Ragic 備註欄 → result_note（Portal 未回填時同步）
CK_EXECUTOR     = "執行人員"
CK_START_TIME   = "保養時間啟"
CK_END_TIME     = "保養時間迄"
CK_WORK_HOURS   = "工時計算"    # Ragic 實際工時欄位（分鐘），直接採用，不重算

# ── Ragic 中文欄位 key（Sheet 11 平表，2026-07-14 起為主要來源，實測驗證）──────
CK11_SEQ_NO       = "項次"
CK11_JOURNAL_NO   = "編號"        # 唯一批次識別依據（Sheet 6 已退役）
CK11_CATEGORY     = "類別"
CK11_EXEC_MONTHS  = "執行月份"
CK11_TASK_NAME    = "項目"
CK11_FREQUENCY    = "頻率"
CK11_SCHEDULER    = "排定人員"
CK11_SCHED_DATE   = "排定日期"
CK11_EXECUTOR     = "執行人員"
CK11_EST_MINUTES  = "預估耗時"     # 僅 fetch_one() 才有
CK11_NOTE         = "備註"         # 僅 fetch_one() 才有
# 維修工時：僅 fetch_one() 才有；命名與語意比照 mall_pm Sheet24「維修工時」（小時，Float）。
# 2026-07-14 查證時所有樣本均為空字串，尚未實測過有值時的實際格式，若日後發現非純數字
# 字串（例如帶單位或時分格式），需回頭複核 _to_float() 是否需要調整解析方式。
CK11_REPAIR_HOURS = "維修工時"
CK11_IMAGES       = "圖片上傳"     # 僅 fetch_one() 才有
CK11_START_TIME   = "保養時間啟"   # 僅 fetch_one() 才有，2026-07-14 查證確認已存在（惟實測記錄常為空）
CK11_END_TIME     = "保養時間迄"   # 僅 fetch_one() 才有，2026-07-14 查證確認已存在（惟實測記錄常為空）

# ── Ragic 中文欄位 key（Sheet 11 每筆記錄底下巢狀子表格「維修記錄」，僅 fetch_one() 才有）──
# 2026-07-14 同日追加：原始遷移評估誤判 Sheet 11 無子表格，使用者實測記錄（277/477）
# 證實有此結構，欄位與 mall_pm Sheet24 完全相同（見 mall_periodic_maintenance_sync.py
# 的 CK24S_* 常數），比照同一模式補上。
CK11S_SEQ_NO     = "項次"
CK11S_NOTE       = "維修記錄"
CK11S_START_TIME = "時間開始"
CK11S_END_TIME   = "時間結束"
CK11S_STAFF      = "保養人員"

# ── Ragic 連線設定 ────────────────────────────────────────────────────────────
PM_SERVER_URL = getattr(settings, "RAGIC_PM_SERVER_URL", "ap12.ragic.com")
PM_ACCOUNT    = "soutlet001"
PM_JOURNAL_PATH = getattr(settings, "RAGIC_PM_JOURNAL_PATH", "periodic-maintenance/6")   # 已停用，僅供回退/比對
PM_ITEMS_PATH   = getattr(settings, "RAGIC_PM_ITEMS_PATH",   "periodic-maintenance/8")   # 已停用，僅供回退/比對
PM_SHEET11_PATH = getattr(settings, "RAGIC_PM_SHEET11_PATH", "periodic-maintenance/11")  # 2026-07-14 起主要來源


# ── 轉換輔助函式 ──────────────────────────────────────────────────────────────

def _stringify(value: Any) -> str:
    """將各種 Ragic 值型別轉成字串"""
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


def _to_float(val: Any) -> float | None:
    """比照 mall_periodic_maintenance_sync._to_float()：轉換 Sheet11「維修工時」欄位。"""
    try:
        v = str(val).strip()
        return float(v) if v not in ("", "None", "null", "-") else None
    except (ValueError, TypeError):
        return None


_JOURNAL_MONTH_RE = re.compile(r"(\d{4})(\d{2})-\d+$")


def _period_month_from_journal_no(journal_no: str) -> str:
    """
    從「編號」欄位解析保養月份，如 '英週保202607-001' → '2026/07'。

    2026-07-14 起 Sheet 6（含獨立「日期」欄位）已退役，批次月份改從「編號」
    內嵌的 YYYYMM 反推。格式不符或月份不在 1~12 範圍時回傳空字串，不猜測。
    """
    if not journal_no:
        return ""
    m = _JOURNAL_MONTH_RE.search(journal_no.strip())
    if not m:
        return ""
    yyyy, mm = m.group(1), m.group(2)
    if not (1 <= int(mm) <= 12):
        return ""
    return f"{yyyy}/{mm}"


def _parse_exec_months(raw: str) -> list[int]:
    """
    將執行月份文字解析為整數月份陣列。
    "2月 5月 8月 11月"  →  [2, 5, 8, 11]
    "每月"             →  [1,2,3,4,5,6,7,8,9,10,11,12]
    "3月 9月"          →  [3, 9]
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
    """
    將 Ragic 日期欄正規化為 'YYYY/MM' 格式。
    "2026/04/01" → "2026/04"
    "2026/04"    → "2026/04"（原樣）
    """
    parts = raw_date.strip().split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return raw_date


def _ragic_batch_to_model(ragic_id: str, raw: dict[str, Any]) -> PeriodicMaintenanceBatch:
    """Ragic 主表原始 dict → ORM 物件"""
    rec = PeriodicMaintenanceBatch(ragic_id=ragic_id)
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
) -> PeriodicMaintenanceItem:
    """
    Ragic 子表格列（row_raw）→ ORM 物件。
    batch_ragic_id 由呼叫端傳入（來自父記錄 ID），不從 row 內欄位讀取。
    """
    rec = PeriodicMaintenanceItem(ragic_id=ragic_id)

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

    # 工時計算：直接採用 Ragic「工時計算」欄位（分鐘整數）；若空值存 None
    _wh_raw = row_raw.get(CK_WORK_HOURS)
    rec.ragic_work_minutes = _to_int(_wh_raw) if _wh_raw not in (None, "", "None") else None

    # 完成標記：保養時間啟 AND 保養時間迄 均有值 → 視為完成
    rec.is_completed = bool(rec.start_time and rec.end_time)

    exec_months_raw = _stringify(row_raw.get(CK_EXEC_MONTHS, ""))
    rec.exec_months_raw  = exec_months_raw
    rec.exec_months_json = json.dumps(_parse_exec_months(exec_months_raw), ensure_ascii=False)

    rec.synced_at = twnow()
    return rec


# ── 同步主程式 ────────────────────────────────────────────────────────────────

async def sync_batches_from_ragic() -> dict:
    """同步 Sheet 6（主表）→ pm_batch"""
    adapter = RagicAdapter(
        sheet_path=PM_JOURNAL_PATH,
        server_url=PM_SERVER_URL,
        account=PM_ACCOUNT,
    )
    logger.info("[PMSync][Batch] 開始同步主表...")
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[PMSync][Batch] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    fetched  = len(raw_data)
    upserted = 0
    errors: list[str] = []

    BATCH_SIZE = 50  # 每批 commit，避免長事務持鎖
    db = SessionLocal()
    try:
        for i, (ragic_id, raw) in enumerate(raw_data.items()):
            try:
                new_rec = _ragic_batch_to_model(str(ragic_id), raw)
                existing = db.get(PeriodicMaintenanceBatch, str(ragic_id))
                if existing:
                    existing.journal_no      = new_rec.journal_no
                    existing.period_month    = _normalize_period_month(new_rec.period_month)
                    existing.ragic_created_at = new_rec.ragic_created_at
                    existing.ragic_updated_at = new_rec.ragic_updated_at
                    existing.synced_at       = new_rec.synced_at
                else:
                    db.add(new_rec)
                upserted += 1
            except Exception as exc:
                errors.append(f"batch ragic_id={ragic_id}: {exc}")
                logger.warning(f"[PMSync][Batch] 記錄 {ragic_id} 失敗：{exc}")

            # 每 BATCH_SIZE 筆提交一次，縮短鎖定時間
            if (i + 1) % BATCH_SIZE == 0:
                try:
                    db.commit()
                except Exception as exc:
                    db.rollback()
                    errors.append(f"batch commit at {i}: {exc}")
                    logger.error(f"[PMSync][Batch] 中間 commit 失敗：{exc}")

        db.commit()  # 最後剩餘筆數
        logger.info(f"[PMSync][Batch] 完成：fetched={fetched}, upserted={upserted}, errors={len(errors)}")
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[PMSync][Batch] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {"fetched": fetched, "upserted": upserted, "errors": errors}


async def sync_items_from_ragic() -> dict:
    """
    同步 Sheet 8（附表）→ pm_batch_item

    策略：
      1. fetch_all() 取得批次 ID 清單（列表 API 不含子表格）
      2. 對每筆批次 ID 呼叫 fetch_one()，取得含子表格的完整記錄
      3. 從完整記錄提取子表格列（支援數字 key / 命名 dict / 命名 list 三種格式）
      4. item.ragic_id = "{batch_id}_{row_key}"（如 "5_1", "5_2"…）
    """
    adapter = RagicAdapter(
        sheet_path=PM_ITEMS_PATH,
        server_url=PM_SERVER_URL,
        account=PM_ACCOUNT,
    )
    logger.info("[PMSync][Items] 開始同步附表（子表格解析模式）...")
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[PMSync][Items] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    if not raw_data:
        logger.warning("[PMSync][Items] Ragic 回傳空資料")
        return {"fetched": 0, "upserted": 0, "errors": []}

    # fetch_all 只回傳主表欄位，不含子表格。
    # 對每筆記錄改用 fetch_one() 取得完整資料（含子表格列）。
    batch_ids = list(raw_data.keys())
    logger.info(f"[PMSync][Items] 取得 {len(batch_ids)} 筆批次 ID，改用 fetch_one 取子表格：{batch_ids}")

    total_fetched  = 0
    total_upserted = 0
    errors: list[str] = []
    now = twnow()

    db = SessionLocal()
    try:
        # ── Step 1：清除舊格式記錄（ragic_id 不含底線 = 舊版同步遺留的空白記錄）──
        old_style = db.query(PeriodicMaintenanceItem).filter(
            ~PeriodicMaintenanceItem.ragic_id.contains("_")
        ).all()
        if old_style:
            logger.info(f"[PMSync][Items] 清除 {len(old_style)} 筆舊格式記錄")
            for it in old_style:
                db.delete(it)
            db.flush()

        # ── Step 2：逐筆 fetch_one 取完整記錄（含子表格）────────────────────
        for batch_ragic_id in batch_ids:
            batch_id_str = str(batch_ragic_id)
            try:
                full_record = await adapter.fetch_one(batch_id_str)
            except Exception as exc:
                errors.append(f"fetch_one({batch_id_str}): {exc}")
                logger.warning(f"[PMSync][Items] fetch_one({batch_id_str}) 失敗：{exc}")
                continue

            # Ragic fetch_one 回傳 {"recordId": {fields...}}，需要 unwrap
            if batch_id_str in full_record and len(full_record) == 1:
                full_record = full_record[batch_id_str]

            # 第一筆完整記錄的結構診斷 log
            if batch_id_str == batch_ids[0]:
                key_types = {k: type(v).__name__ for k, v in full_record.items() if not k.startswith("_")}
                logger.info(f"[PMSync][Items] fetch_one({batch_id_str}) unwrapped 欄位型別={key_types}")

            # ── 完整結構診斷：列出所有 key 及第一層 value 摘要（包含 _subtable_* 等隱藏 key）──
            structure = {}
            for k, v in full_record.items():
                if isinstance(v, dict):
                    inner_keys = list(v.keys())[:5]
                    structure[k] = f"dict({len(v)}) inner_keys={inner_keys}"
                elif isinstance(v, list):
                    structure[k] = f"list({len(v)})"
                else:
                    structure[k] = repr(v)[:50]
            logger.info(f"[PMSync][Items] fetch_one({batch_id_str}) 完整結構={structure}")

            # 找出子表格列
            sub_rows: dict[str, dict] = {}

            # 方式 A：頂層數字 key → 直接是子列
            direct_numeric = {
                k: v for k, v in full_record.items()
                if k.lstrip("-").isdigit() and isinstance(v, dict)
            }
            if direct_numeric:
                # 判斷是否為「單一 Field-ID 包裝」：只有 1 個數字 key 且其 value 內含更多數字 key
                if len(direct_numeric) == 1:
                    container_key = next(iter(direct_numeric))
                    container_val = direct_numeric[container_key]
                    inner_numeric = {
                        k: v for k, v in container_val.items()
                        if k.lstrip("-").isdigit() and isinstance(v, dict)
                    }
                    if inner_numeric:
                        # 是包裝層，去一層深
                        sub_rows = inner_numeric
                        logger.info(f"[PMSync][Items] 批次 {batch_id_str} → 方式A深層(container='{container_key}') {len(sub_rows)} 列")
                    else:
                        # 只有 1 個子列（正常情況）
                        sub_rows = direct_numeric
                        logger.info(f"[PMSync][Items] 批次 {batch_id_str} → 方式A {len(sub_rows)} 列")
                else:
                    sub_rows = direct_numeric
                    logger.info(f"[PMSync][Items] 批次 {batch_id_str} → 方式A {len(sub_rows)} 列")

            # 方式 B：命名 key → dict（key 為數字）
            if not sub_rows:
                for k, v in full_record.items():
                    if k.startswith("_"):
                        continue
                    if isinstance(v, dict) and len(v) > 0:
                        first_sub = next(iter(v.keys()), "")
                        if first_sub.lstrip("-").isdigit():
                            sub_rows = {rk: rv for rk, rv in v.items() if isinstance(rv, dict)}
                            logger.info(f"[PMSync][Items] 批次 {batch_id_str} → 方式B('{k}') {len(sub_rows)} 列")
                            break

            # 方式 C：命名 key → list of dicts
            if not sub_rows:
                for k, v in full_record.items():
                    if k.startswith("_"):
                        continue
                    if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                        sub_rows = {str(i + 1): row for i, row in enumerate(v)}
                        logger.info(f"[PMSync][Items] 批次 {batch_id_str} → 方式C('{k}') {len(sub_rows)} 列")
                        break

            # 方式 D：Ragic 內部 _subtable_{id} key（key 以底線開頭，前面方式都跳過）
            # 確認結構：full_record["_subtable_1011397"] = {"1": {row_data}, "2": {row_data}, ...}
            if not sub_rows:
                for k, v in full_record.items():
                    if not k.startswith("_subtable_"):
                        continue
                    if not isinstance(v, dict) or len(v) == 0:
                        continue
                    # value 的 key 應為數字字串（"1", "2", ...）
                    inner_numeric = {
                        rk: rv for rk, rv in v.items()
                        if rk.lstrip("-").isdigit() and isinstance(rv, dict)
                    }
                    if inner_numeric:
                        sub_rows = inner_numeric
                        logger.info(
                            f"[PMSync][Items] 批次 {batch_id_str} → 方式D('{k}') {len(sub_rows)} 列"
                        )
                        break
                    # 若 value 本身就是一個 dict of dicts（非數字 key），也嘗試
                    inner_dicts = {rk: rv for rk, rv in v.items() if isinstance(rv, dict)}
                    if inner_dicts:
                        sub_rows = inner_dicts
                        logger.info(
                            f"[PMSync][Items] 批次 {batch_id_str} → 方式D-b('{k}') {len(sub_rows)} 列"
                        )
                        break

            if not sub_rows:
                logger.warning(f"[PMSync][Items] 批次 {batch_id_str} 無子表格，full_record keys={list(full_record.keys())}")
                continue

            # 診斷：印出第一列的實際 key-value（確認是中文 label 還是 field ID）
            first_row_key = next(iter(sub_rows))
            first_row_val = sub_rows[first_row_key]
            logger.info(f"[PMSync][Items] 第一子列 key='{first_row_key}' 內容={dict(list(first_row_val.items())[:8])}")

            logger.info(f"[PMSync][Items] 批次 {batch_id_str} → 解析 {len(sub_rows)} 列")
            total_fetched += len(sub_rows)

            # ── 批次全量替換（2026-07-01 修正）：先清空此批次現有項目，避免
            #    過去解析出的不同 row_key（同一任務、不同 ragic_id）長期殘留
            #    於 DB，造成行事曆重複顯示同一保養任務 ────────────────────────
            deleted_in_batch = db.query(PeriodicMaintenanceItem).filter(
                PeriodicMaintenanceItem.batch_ragic_id == batch_id_str
            ).delete()
            if deleted_in_batch:
                logger.info(f"[PMSync][Items] 批次 {batch_id_str} 清空舊項目 {deleted_in_batch} 筆")

            _item_write_count = 0
            for row_key, row_raw in sub_rows.items():
                item_id = f"{batch_id_str}_{row_key}"
                try:
                    new_rec = _ragic_item_to_model(item_id, row_raw, batch_id_str)
                    existing = db.get(PeriodicMaintenanceItem, item_id)

                    if existing:
                        # 全部以 Ragic 為準（Portal 不提供編輯，無保護機制）
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
                        existing.start_time           = new_rec.start_time
                        existing.end_time             = new_rec.end_time
                        existing.ragic_work_minutes   = new_rec.ragic_work_minutes
                        existing.is_completed         = new_rec.is_completed
                        existing.synced_at         = now
                    else:
                        db.add(new_rec)

                    total_upserted += 1
                    _item_write_count += 1
                except Exception as exc:
                    errors.append(f"item {item_id}: {exc}")
                    logger.warning(f"[PMSync][Items] 項目 {item_id} 失敗：{exc}")

                # 每 50 筆提交，避免長事務持鎖
                if _item_write_count % 50 == 0 and _item_write_count > 0:
                    try:
                        db.commit()
                    except Exception as exc:
                        db.rollback()
                        errors.append(f"items batch commit: {exc}")
                        logger.error(f"[PMSync][Items] 中間 commit 失敗：{exc}")

        db.commit()
        logger.info(
            f"[PMSync][Items] 完成："
            f"batches={len(raw_data)}, items_fetched={total_fetched}, "
            f"upserted={total_upserted}, errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[PMSync][Items] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {"fetched": total_fetched, "upserted": total_upserted, "errors": errors}


def _find_worklog_subtable(full_record: dict[str, Any]) -> dict[str, dict]:
    """
    從 fetch_one() 結果中找出巢狀子表格「維修記錄」。
    Ragic 內部 key 為 _subtable_<動態數字>，不寫死數字，取第一個非空 dict。
    2026-07-14 同日追加，比照 mall_periodic_maintenance_sync.py 同名函式（複製而非
    共用，兩模組各自獨立維護）。
    """
    for k, v in full_record.items():
        if not k.startswith("_subtable_"):
            continue
        if isinstance(v, dict) and v:
            inner = {rk: rv for rk, rv in v.items() if isinstance(rv, dict)}
            if inner:
                return inner
    return {}


async def sync_from_sheet11() -> dict:
    """
    2026-07-14 起：pm_batch（批次）與 pm_batch_item（項目明細）改為完全以 Ragic
    Sheet 11（平表）為來源。Sheet 6（主表）／Sheet 8（附表子表格）正式退役，
    不再被本函式呼叫（sync_batches_from_ragic() / sync_items_from_ragic() 仍保留
    在本檔案中未刪除，供比對或回退使用）。

    批次沒有獨立 Ragic 記錄了，由 Sheet 11 項目的「編號」欄位分組合成：
      - 已存在的批次（沿用舊 Sheet6 數字 ragic_id，或先前已合成過的「編號」字串）
        依「編號」比對，找到後沿用其既有 ragic_id，只更新 period_month/synced_at。
      - 全新批次（該編號從未出現過）以「編號」字串本身作為 ragic_id。
      - 若某月批次在 Sheet 11 完全沒有項目（如 2026-07-14 發現的 202606-001 缺口），
        該月批次不會被建立/更新，但也【不會被刪除】——沿用同步前的既有狀態（若之前
        從未透過 Sheet 6/8 同步過，則單純不存在）。這是使用者已確認接受的已知風險，
        見 project memory project_hotel_pm_sheet11_migration.md。

    "在 Ragic 查看" 連結語意變更（連結字串由呼叫端 router 組出，本函式不處理）：
      - 批次沒有獨立 Ragic 記錄了，主表連結改為 Sheet 11 這個 Tab 本身（不含記錄 ID）。
      - 項目改用自己的 Sheet 11 _ragicId 直連（periodic-maintenance/11/{ragic_id}）。

    2026-07-14 同日追加（原始遷移評估誤判所致）：Sheet 11 項目底下其實有巢狀子表格
    「維修記錄」（欄位與 mall_pm Sheet24 完全相同：項次/維修記錄/時間開始/時間結束/
    保養人員），使用者實測記錄（277/477）證實存在。本函式逐筆項目 fetch_one() 時
    一併解析並全量替換寫入 pm_item_worklog；item.start_time/end_time 優先採頂層
    「保養時間啟/迄」，該二欄為空時改採子表格最早開始／最晚結束時間（比照 mall_pm
    Sheet24 的做法）。
    """
    adapter = RagicAdapter(
        sheet_path=PM_SHEET11_PATH,
        server_url=PM_SERVER_URL,
        account=PM_ACCOUNT,
    )
    logger.info("[PMSync][Sheet11] 開始同步（Sheet11 為批次+項目共同來源）...")
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[PMSync][Sheet11] 拉取失敗：{exc}")
        return {"fetched": 0, "batches_upserted": 0, "items_upserted": 0, "errors": [str(exc)]}

    if not raw_data:
        logger.warning("[PMSync][Sheet11] Ragic 回傳空資料")
        return {"fetched": 0, "batches_upserted": 0, "items_upserted": 0, "errors": []}

    fetched            = len(raw_data)
    batches_upserted   = 0
    items_upserted     = 0
    items_with_images  = 0
    worklogs_upserted  = 0
    errors: list[str]  = []
    blank_journal_no   = 0
    now = twnow()

    db = SessionLocal()
    try:
        # ── Step 0：清除舊格式殘留項目（架構調整後發現，比照 mall_pm/full_bldg_pm
        #    2026-07-13 同型改版）。舊版 sync_items_from_ragic()（Sheet8 子表格解析）
        #    用的 ragic_id 是 "{batch_id}_{row_key}" 複合格式（如 "9_1"，含底線）；
        #    新版直接採用 Sheet11 項目自身的數字 ragic_id（如 "477"，不含底線）。
        #    兩種格式的 primary key 不同，若不清除，舊資料會與新同步的資料同時存在，
        #    造成每個項目重複兩筆。此清除只在資料庫仍殘留舊格式資料時才會實際刪除。
        #
        #    ⚠️ 注意：舊格式項目上若有 Portal 標記過的 abnormal_flag/abnormal_note，
        #    會隨這次清除一併移除（新格式項目是全新 insert，不会繼承）。
        old_style_items = db.query(PeriodicMaintenanceItem).filter(
            PeriodicMaintenanceItem.ragic_id.contains("_")
        ).all()
        old_style_abnormal = [it for it in old_style_items if it.abnormal_flag]
        if old_style_abnormal:
            logger.warning(
                f"[PMSync][Sheet11] 即將清除的 {len(old_style_items)} 筆舊格式項目中，"
                f"有 {len(old_style_abnormal)} 筆帶有 abnormal_flag=True，異常標記將遺失："
                f"{[it.ragic_id for it in old_style_abnormal]}"
            )
        if old_style_items:
            logger.info(f"[PMSync][Sheet11] 清除 {len(old_style_items)} 筆舊格式（Sheet8子表格解析）殘留項目")
            for it in old_style_items:
                db.delete(it)
            db.flush()

        # 同理清除 pm_schedule 舊格式殘留（item_ragic_id 含底線）。與 mall_pm 2026-07-13
        # 同型改版一致：帶有人工資料（已完成／異常／人工調整／已填執行時間）的記錄
        # 只警告不刪除，避免遺失人工資料。
        old_style_sched_all = db.query(PMSchedule).filter(
            PMSchedule.item_ragic_id.contains("_")
        ).all()
        old_style_sched_risky = [
            s for s in old_style_sched_all
            if s.is_completed or s.abnormal_flag or s.portal_edited_at is not None
            or s.start_time or s.end_time
        ]
        old_style_sched_safe = [s for s in old_style_sched_all if s not in old_style_sched_risky]
        if old_style_sched_risky:
            logger.warning(
                f"[PMSync][Sheet11] {len(old_style_sched_risky)} 筆舊格式 pm_schedule 記錄"
                f"帶有人工資料，保留不刪除，請人工確認後處理："
                f"{[(s.id, s.item_ragic_id, s.task_name) for s in old_style_sched_risky]}"
            )
        if old_style_sched_safe:
            logger.info(f"[PMSync][Sheet11] 清除 {len(old_style_sched_safe)} 筆舊格式殘留 pm_schedule 排程記錄")
            for s in old_style_sched_safe:
                db.delete(s)
            db.flush()

        # ── Step 1：既有批次「編號」→ ragic_id 對照表（沿用既有識別，含舊 Sheet6 legacy）──
        journal_to_batch: dict[str, str] = {
            b.journal_no: b.ragic_id for b in db.query(PeriodicMaintenanceBatch).all() if b.journal_no
        }

        # ── Step 2：依「編號」分組，合成/更新批次記錄（Sheet 11 沒有獨立批次記錄）──
        journal_groups: dict[str, list[str]] = {}
        for ragic_id, raw in raw_data.items():
            journal_no = _stringify(raw.get(CK11_JOURNAL_NO, ""))
            if not journal_no:
                blank_journal_no += 1
                continue
            journal_groups.setdefault(journal_no, []).append(str(ragic_id))

        for journal_no in journal_groups:
            period_month = _period_month_from_journal_no(journal_no)
            batch_ragic_id = journal_to_batch.get(journal_no)
            if batch_ragic_id:
                existing_batch = db.get(PeriodicMaintenanceBatch, batch_ragic_id)
                if existing_batch:
                    if period_month:
                        existing_batch.period_month = period_month
                    existing_batch.synced_at = now
            else:
                batch_ragic_id = journal_no  # 沒有獨立 Ragic 記錄，直接用「編號」當識別碼
                db.add(PeriodicMaintenanceBatch(
                    ragic_id=batch_ragic_id,
                    journal_no=journal_no,
                    period_month=period_month,
                    ragic_created_at="",
                    ragic_updated_at="",
                    synced_at=now,
                ))
                journal_to_batch[journal_no] = batch_ragic_id
            batches_upserted += 1
        db.flush()

        # ── Step 3：逐筆項目 upsert（item.ragic_id 直接採用 Sheet11 自己的 _ragicId）───
        for item_ragic_id, raw in raw_data.items():
            item_id = str(item_ragic_id)
            try:
                journal_no = _stringify(raw.get(CK11_JOURNAL_NO, ""))
                batch_ragic_id = journal_to_batch.get(journal_no)
                if not batch_ragic_id:
                    continue  # 「編號」為空，已於 Step 2 計入 blank_journal_no

                exec_months_raw = _stringify(raw.get(CK11_EXEC_MONTHS, ""))

                # listing 模式（fetch_all）抓不到「保養時間啟/迄」「預估耗時」「備註」
                # 「圖片上傳」，逐筆 fetch_one() 才有（2026-07-14 即時查證確認，
                # 比照 mall_pm Sheet24 同一模式）。
                try:
                    full_record = await adapter.fetch_one(item_id)
                    if item_id in full_record and len(full_record) == 1:
                        full_record = full_record[item_id]
                except Exception as exc:
                    full_record = {}
                    errors.append(f"fetch_one(item={item_id}) 失敗：{exc}")
                    logger.warning(f"[PMSync][Sheet11] fetch_one({item_id}) 失敗：{exc}")

                top_start_time = _stringify(full_record.get(CK11_START_TIME, ""))
                top_end_time   = _stringify(full_record.get(CK11_END_TIME, ""))
                est_minutes  = _to_int(full_record.get(CK11_EST_MINUTES, raw.get(CK11_EST_MINUTES, 0)))
                note         = _stringify(full_record.get(CK11_NOTE, ""))
                repair_hours = _to_float(full_record.get(CK11_REPAIR_HOURS, raw.get(CK11_REPAIR_HOURS, "")))
                images = parse_images(
                    full_record.get(CK11_IMAGES),
                    server=PM_SERVER_URL,
                    account=PM_ACCOUNT,
                )

                # ── 巢狀子表格「維修記錄」解析（2026-07-14 同日追加）───────────────
                # 全量替換此項目的 worklog（避免舊 sub_key 殘留），比照 mall_pm Sheet24。
                sub_rows = _find_worklog_subtable(full_record)
                db.query(PeriodicMaintenanceItemWorklog).filter(
                    PeriodicMaintenanceItemWorklog.item_ragic_id == item_id
                ).delete()

                worklog_starts: list[str] = []
                worklog_ends: list[str] = []
                for sub_key, sub_row in sub_rows.items():
                    wl_start = _stringify(sub_row.get(CK11S_START_TIME, ""))
                    wl_end   = _stringify(sub_row.get(CK11S_END_TIME, ""))
                    if wl_start:
                        worklog_starts.append(wl_start)
                    if wl_end:
                        worklog_ends.append(wl_end)
                    db.add(PeriodicMaintenanceItemWorklog(
                        ragic_id=f"{item_id}_{sub_key}",
                        item_ragic_id=item_id,
                        seq_no=_to_int(sub_row.get(CK11S_SEQ_NO, 0)),
                        repair_note=_stringify(sub_row.get(CK11S_NOTE, "")),
                        start_time=wl_start,
                        end_time=wl_end,
                        staff_name=_stringify(sub_row.get(CK11S_STAFF, "")),
                        synced_at=now,
                    ))
                    worklogs_upserted += 1

                # start_time/end_time：優先頂層「保養時間啟/迄」；為空則取子表格
                # 最早開始／最晚結束（比照 mall_pm Sheet24，多數實測記錄頂層是空的）。
                start_time = top_start_time or (min(worklog_starts) if worklog_starts else "")
                end_time   = top_end_time   or (max(worklog_ends)   if worklog_ends   else "")

                existing = db.get(PeriodicMaintenanceItem, item_id)
                target = existing if existing else PeriodicMaintenanceItem(ragic_id=item_id)
                if not existing:
                    db.add(target)

                target.batch_ragic_id    = batch_ragic_id
                target.seq_no            = _to_int(raw.get(CK11_SEQ_NO, 0))
                target.category          = _stringify(raw.get(CK11_CATEGORY, ""))
                target.frequency         = _stringify(raw.get(CK11_FREQUENCY, ""))
                target.exec_months_raw   = exec_months_raw
                target.exec_months_json  = json.dumps(_parse_exec_months(exec_months_raw), ensure_ascii=False)
                target.task_name         = _stringify(raw.get(CK11_TASK_NAME, ""))
                # location：Sheet 11 無獨立「位置」欄位（2026-07-14 即時查證確認，
                # 沿用 Sheet 8 時代已知限制），不覆蓋既有值（新項目維持空字串）
                target.estimated_minutes = est_minutes
                target.scheduled_date    = _stringify(raw.get(CK11_SCHED_DATE, ""))
                target.scheduler_name    = _stringify(raw.get(CK11_SCHEDULER, ""))
                target.executor_name     = _stringify(raw.get(CK11_EXECUTOR, ""))
                target.result_note       = note
                target.start_time        = start_time
                target.end_time          = end_time
                target.is_completed      = bool(start_time and end_time)
                target.repair_hours      = repair_hours
                target.images_json       = json.dumps(images, ensure_ascii=False)
                target.synced_at         = now

                if images:
                    items_with_images += 1
                items_upserted += 1
            except Exception as exc:
                errors.append(f"item {item_id}: {exc}")
                logger.warning(f"[PMSync][Sheet11] 項目 {item_id} 失敗：{exc}")

        db.commit()
        if blank_journal_no:
            logger.warning(f"[PMSync][Sheet11] {blank_journal_no} 筆項目「編號」為空，已跳過未同步")
        logger.info(
            f"[PMSync][Sheet11] 完成：fetched={fetched}, batches_upserted={batches_upserted}, "
            f"items_upserted={items_upserted}, items_with_images={items_with_images}, "
            f"worklogs_upserted={worklogs_upserted}, "
            f"old_style_items_removed={len(old_style_items)}, "
            f"schedule_old_style_removed={len(old_style_sched_safe)}, errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[PMSync][Sheet11] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {
        "fetched":            fetched,
        "batches_upserted":   batches_upserted,
        "items_upserted":     items_upserted,
        "items_with_images":  items_with_images,
        "worklogs_upserted":  worklogs_upserted,
        "blank_journal_no":   blank_journal_no,
        "errors":             errors,
    }


def _fix_period_month_format(db) -> int:
    """
    一次性修正舊資料：將 pm_batch.period_month 從 'YYYY/MM/DD' 截斷為 'YYYY/MM'。
    回傳修正筆數。
    """
    fixed = 0
    try:
        batches = db.query(PeriodicMaintenanceBatch).all()
        for b in batches:
            normalized = _normalize_period_month(b.period_month)
            if normalized != b.period_month:
                b.period_month = normalized
                fixed += 1
        if fixed:
            db.commit()
            logger.info(f"[PMSync] period_month 格式修正：{fixed} 筆")
    except Exception as exc:
        db.rollback()
        logger.warning(f"[PMSync] period_month 修正失敗：{exc}")
    return fixed


@register("periodic_maintenance")
async def sync_from_ragic() -> dict:
    """
    完整同步：2026-07-14 起改為 Sheet 11（批次+項目共同來源），Sheet 6/8 停用。

    舊版 sync_batches_from_ragic()（Sheet 6）/ sync_items_from_ragic()（Sheet 8）
    仍保留在本檔案中未刪除、未呼叫，供比對驗證或回退使用。
    """
    result = await sync_from_sheet11()

    # 修正舊資料中 period_month 格式（幂等，safe to run every time；主要處理
    # Sheet6/8 時代遺留的 'YYYY/MM/DD' 格式，Sheet11 新資料本來就是 'YYYY/MM'）
    db = SessionLocal()
    try:
        _fix_period_month_format(db)
    finally:
        db.close()

    return {
        "sheet11": result,
    }
