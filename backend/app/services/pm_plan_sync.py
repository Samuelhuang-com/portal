"""
週期保養預排同步服務：Ragic → SQLite

資料來源（主管排定 Sheets）：
  Sheet 7  → periodic-maintenance/7  （飯店週期保養主管排定）
  Sheet 13 → periodic-maintenance/13 （商場週期保養主管排定）
  Sheet 20 → periodic-maintenance/20 （全棟例行維護主管排定）

這三個 Sheet 的欄位結構與執行端 Sheet（/8、/18、/21）相同，
差異在於「排定日期」欄位由主管填入完整計畫日期，用於行事曆預排顯示。

排定日期格式（Ragic 回傳可能有多種，本服務統一處理）：
  "YYYY/MM/DD"  → 直接轉 YYYY-MM-DD（最常見）
  "MM/DD"       → 結合主表 period_month 組成完整日期
  "YYYY-MM-DD"  → 直接使用
  空字串        → 跳過此筆記錄（不放入行事曆）
"""
import logging
import re
from datetime import datetime
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.pm_plan import PmPlanItem
from app.services.ragic_adapter import RagicAdapter
from app.services.sync_dispatcher import register

logger = logging.getLogger(__name__)

# ── 來源 Sheet 設定 ───────────────────────────────────────────────────────────
_SERVER   = "ap12.ragic.com"
_ACCOUNT  = "soutlet001"

SHEET_CONFIGS = [
    {
        "sheet_no":    7,
        "path":        getattr(settings, "RAGIC_PM_PLAN_HOTEL_PATH",   "periodic-maintenance/7"),
        "label":       "飯店",
    },
    {
        "sheet_no":    13,
        "path":        getattr(settings, "RAGIC_PM_PLAN_MALL_PATH",    "periodic-maintenance/13"),
        "label":       "商場",
    },
    {
        "sheet_no":    20,
        "path":        getattr(settings, "RAGIC_PM_PLAN_FULL_PATH",    "periodic-maintenance/20"),
        "label":       "全棟",
    },
]

# ── Ragic 中文欄位 key（與執行端 Sheet 相同命名）────────────────────────────
CK_TASK_NAME   = "項目"
CK_CATEGORY    = "類別"
CK_FREQUENCY   = "頻率"
CK_EXEC_MONTHS = "執行月份"
CK_SCHED_DATE  = "排定日期"
CK_SCHEDULER   = "排定人員"
CK_LOCATION    = "位置"
CK_NOTE        = "備註"
CK_PERIOD_MONTH = "日期"    # 主表批次的月份欄位（YYYY/MM），用於補充日期年份


# ── 工具函式 ──────────────────────────────────────────────────────────────────

def _str(value: Any) -> str:
    """Ragic 任意型別 → 乾淨字串"""
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(_str(v) for v in value)
    if isinstance(value, dict):
        return _str(value.get("value") or value.get("label") or "")
    return str(value).strip()


def _parse_date(raw: str, period_month: str = "") -> str:
    """
    將 Ragic 各種日期格式統一轉為 YYYY-MM-DD。

    Args:
        raw:          Ragic 回傳的日期字串，如 "2026/05/15"、"05/15"
        period_month: 主表批次的月份，如 "2026/05"，用於補充 MM/DD 格式的年份

    Returns:
        "YYYY-MM-DD" 或 "" (無法解析時)
    """
    if not raw:
        return ""

    raw = raw.strip()

    # ── 格式1：YYYY/MM/DD 或 YYYY-MM-DD ─────────────────────────────────────
    m = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$", raw)
    if m:
        try:
            return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        except ValueError:
            pass

    # ── 格式2：MM/DD（搭配 period_month 補年份）──────────────────────────────
    m = re.match(r"^(\d{1,2})/(\d{1,2})$", raw)
    if m:
        month_int, day_int = int(m.group(1)), int(m.group(2))
        # 從 period_month 取得年份
        year = datetime.now().year
        if period_month and "/" in period_month:
            try:
                year = int(period_month.split("/")[0])
            except ValueError:
                pass
        try:
            return f"{year:04d}-{month_int:02d}-{day_int:02d}"
        except ValueError:
            pass

    # ── 格式3：YYYYMMDD（8 位數字串）─────────────────────────────────────────
    m = re.match(r"^(\d{4})(\d{2})(\d{2})$", raw)
    if m:
        try:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        except ValueError:
            pass

    logger.debug("pm_plan_sync: 無法解析日期 %r", raw)
    return ""


def _ragic_url(sheet_no: int, record_id: str) -> str:
    return f"https://{_SERVER}/{_ACCOUNT}/periodic-maintenance/{sheet_no}/{record_id}"


# ── 單一 Sheet 同步 ──────────────────────────────────────────────────────────

async def _sync_one_sheet(db, cfg: dict, stats: dict) -> None:
    """同步單一主管排定 Sheet（含主表批次 + 子表格項目）"""
    sheet_no = cfg["sheet_no"]
    path     = cfg["path"]
    label    = cfg["label"]

    logger.info("pm_plan_sync: 開始同步 Sheet %d (%s) path=%s", sheet_no, label, path)

    # 每個 Sheet 使用獨立的 adapter（sheet_path 在 constructor 設定）
    adapter = RagicAdapter(sheet_path=path)

    # ── Step 1：抓主表批次清單 ────────────────────────────────────────────────
    try:
        batches_raw = await adapter.fetch_all()
    except Exception as exc:
        logger.error("pm_plan_sync: Sheet %d 抓取失敗: %s", sheet_no, exc)
        stats["errors"] += 1
        return

    if not batches_raw:
        logger.info("pm_plan_sync: Sheet %d 無資料", sheet_no)
        return

    # ── Step 2：逐批次抓完整資料（含子表格項目）──────────────────────────────
    upserted = 0
    for batch_id, batch_data in batches_raw.items():
        if not isinstance(batch_data, dict):
            continue

        # 取主表的 period_month（用於補充 MM/DD 日期格式的年份）
        period_month = _str(batch_data.get(CK_PERIOD_MONTH, ""))

        # 抓完整批次資料（含子表格）
        try:
            full = await adapter.fetch_one(batch_id)
        except Exception as exc:
            logger.warning("pm_plan_sync: Sheet %d 批次 %s fetch_one 失敗: %s",
                           sheet_no, batch_id, exc)
            # 退而求其次：用清單資料
            full = batch_data

        if not isinstance(full, dict):
            continue

        # ── Step 3：解析子表格項目 ─────────────────────────────────────────
        for row_key, row_data in full.items():
            # 子表格的 key 是純數字
            if not str(row_key).isdigit():
                continue
            if not isinstance(row_data, dict):
                continue

            task_name = _str(row_data.get(CK_TASK_NAME, ""))
            sched_raw = _str(row_data.get(CK_SCHED_DATE, ""))

            # 沒有排定日期 → 跳過（無法在行事曆顯示）
            if not sched_raw:
                continue

            sched_iso = _parse_date(sched_raw, period_month)
            if not sched_iso:
                continue

            # 組合唯一 ragic_id
            item_id = f"{sheet_no}_{batch_id}_{row_key}"

            item = db.query(PmPlanItem).filter(PmPlanItem.ragic_id == item_id).first()
            if item is None:
                item = PmPlanItem(ragic_id=item_id)
                db.add(item)

            item.source_sheet   = sheet_no
            item.source_label   = label
            item.task_name      = task_name
            item.category       = _str(row_data.get(CK_CATEGORY, ""))
            item.frequency      = _str(row_data.get(CK_FREQUENCY, ""))
            item.exec_months_raw = _str(row_data.get(CK_EXEC_MONTHS, ""))
            item.location       = _str(row_data.get(CK_LOCATION, ""))
            item.scheduled_date = sched_iso
            item.scheduler_name = _str(row_data.get(CK_SCHEDULER, ""))
            item.note           = _str(row_data.get(CK_NOTE, ""))
            item.ragic_url      = _ragic_url(sheet_no, batch_id)
            item.ragic_created_at = _str(batch_data.get("_ragicCreate", ""))
            item.ragic_updated_at = _str(batch_data.get("_ragicUpdate", ""))

            upserted += 1

    db.commit()
    stats["upserted"] += upserted
    logger.info("pm_plan_sync: Sheet %d (%s) 完成，upsert %d 筆", sheet_no, label, upserted)


# ── 公開同步函式 ─────────────────────────────────────────────────────────────

@register("週期保養預排")
async def sync_from_ragic() -> dict:
    """
    同步三個主管排定 Sheet（/7、/13、/20）的預排資料到本地 SQLite。

    Returns:
        {"upserted": N, "errors": N}
    """
    stats = {"upserted": 0, "errors": 0}

    db = SessionLocal()
    try:
        for cfg in SHEET_CONFIGS:
            await _sync_one_sheet(db, cfg, stats)
    except Exception as exc:
        logger.error("pm_plan_sync: 頂層例外 %s", exc, exc_info=True)
        stats["errors"] += 1
        db.rollback()
    finally:
        db.close()

    logger.info("pm_plan_sync: 全部完成 → upserted=%d errors=%d",
                stats["upserted"], stats["errors"])
    return stats

