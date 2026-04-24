"""
整棟工務每日巡檢 - B4F 同步服務【寬表格 Pivot 架構】

資料來源：
  https://ap12.ragic.com/soutlet001/full-building-inspection/2

【結構說明】
  Ragic Sheet 2 每一 Row = 一次完整巡檢場次（寬表格格式）
  場次欄位：巡檢人員、開始巡檢時間、巡檢結束時間、工時計算
  結果欄位：35 個設備/項目欄位，各自儲存 正常/異常 等狀態值

【同步邏輯】
  fetch_all() 取得所有 Row，對每個 Row：
  1. 寫入 b4f_inspection_batch（一次場次）
  2. 清除舊 items，再 pivot 35 個欄位 → 35 筆 b4f_inspection_item
"""
import logging
from datetime import datetime, timezone
from app.core.time import twnow
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.b4f_inspection import B4FInspectionBatch, B4FInspectionItem
from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

# ── Ragic 連線設定 ────────────────────────────────────────────────────────────
B4F_SERVER_URL = getattr(settings, "RAGIC_B4F_SERVER_URL",  "ap12.ragic.com")
B4F_ACCOUNT    = getattr(settings, "RAGIC_B4F_ACCOUNT",     "soutlet001")
B4F_SHEET_PATH = getattr(settings, "RAGIC_B4F_SHEET_PATH",  "full-building-inspection/2")

# ── Ragic 場次欄位 key ────────────────────────────────────────────────────────
CK_INSPECTOR  = "巡檢人員"
CK_START_TIME = "開始巡檢時間"
CK_END_TIME   = "巡檢結束時間"
CK_WORK_HOURS = "工時計算"

# ── 巡檢設備/項目欄位清單（依 Ragic 欄位順序，Pivot 時一欄 → 一列）────────────
CHECK_ITEMS = [
    # B4F 冰水主機
    "基本運轉狀態",
    "冷媒系統檢查",
    "電機運轉電流",
    "電壓是否正常",
    "蒸發器壓力",
    "冷凝器壓力",
    "冷媒液位",
    "冰水進水溫度",
    "冰水出水溫度",
    "冰水進出溫差",
    "流量 / 壓力值",
    "管路、閥件有無滲漏",
    "隔熱材是否完好",
    "設備地面有無積水",
    # 連續壁汙廢水
    "滲漏狀況",
    "排水管順暢",
    "槽體結構無破損滲漏",
    "槽蓋密合",
    "液位顯示正常(浮球)",
    "高水位警報測試",
    "液位未超限或接近滿槽",
    "幫浦運轉聲音正常、自動 / 手動運轉正常",
    "抽水流量正常、無漏水漏油",
    "進出水管無阻塞或破裂",
    "止回閥、閘閥功能正常",
    "無強烈異味外洩",
    "遠端液位或滿水警報通知系統",
    "無蚊蟲、蟑螂等孳生",
    # 下水塔
    "水塔結構完整無裂縫",
    "液位、浮球感測器正常",
    "幫浦啟停控制正常",
    "止回閥與電磁閥功能良好",
    "無懸浮物漂浮",
    "進水/出水管無滲漏",
    "接頭與法蘭固定良好",
]

# ── 巡檢結果 → result_status 對照 ────────────────────────────────────────────
RESULT_STATUS_MAP: dict[str, str] = {
    "正常":   "normal",
    "OK":     "normal",
    "ok":     "normal",
    "O":      "normal",
    "異常":   "abnormal",
    "待處理": "pending",
    "待修":   "pending",
    "待修繕": "pending",
    "X":      "abnormal",
}


# ── 轉換輔助函式 ──────────────────────────────────────────────────────────────

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
    # 取前 10 字元並正規化
    date_part = raw[:10].replace("-", "/")
    # 補零：2026/4/14 → 2026/04/14
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


# ── 同步主程式 ────────────────────────────────────────────────────────────────

async def sync_from_ragic() -> dict:
    """
    從 Ragic Sheet 2 同步：
      每個 Row → 1 筆 B4FInspectionBatch + pivot 成 N 筆 B4FInspectionItem。
    """
    adapter = RagicAdapter(
        sheet_path=B4F_SHEET_PATH,
        server_url=B4F_SERVER_URL,
        account=B4F_ACCOUNT,
    )
    logger.info("[B4FSync] 開始同步（寬表格 Pivot 模式）...")

    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[B4FSync] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "item_rows": 0, "errors": [str(exc)]}

    fetched   = len(raw_data)
    upserted  = 0
    item_rows = 0
    errors: list[str] = []
    now = twnow()

    if fetched > 0:
        first_id  = next(iter(raw_data))
        first_rec = raw_data[first_id]
        logger.info(f"[B4FSync] 第一筆 id={first_id} keys={list(first_rec.keys())}")

    db = SessionLocal()
    try:
        for ragic_id, raw in raw_data.items():
            batch_id = str(ragic_id)
            try:
                # ── 1. 寫入場次（Batch）──────────────────────────────────────
                start_raw = _stringify(raw.get(CK_START_TIME, ""))
                batch = B4FInspectionBatch(
                    ragic_id        = batch_id,
                    inspection_date = _extract_date(start_raw),
                    inspector_name  = _stringify(raw.get(CK_INSPECTOR, "")),
                    start_time      = start_raw,
                    end_time        = _stringify(raw.get(CK_END_TIME, "")),
                    work_hours      = _stringify(raw.get(CK_WORK_HOURS, "")),
                    synced_at       = now,
                )

                existing_batch = db.get(B4FInspectionBatch, batch_id)
                if existing_batch:
                    existing_batch.inspection_date = batch.inspection_date
                    existing_batch.inspector_name  = batch.inspector_name
                    existing_batch.start_time      = batch.start_time
                    existing_batch.end_time        = batch.end_time
                    existing_batch.work_hours      = batch.work_hours
                    existing_batch.synced_at       = now
                else:
                    db.add(batch)

                # ── 2. 清除舊 Items，再 Pivot 產生新 Items ───────────────────
                db.query(B4FInspectionItem).filter(
                    B4FInspectionItem.batch_ragic_id == batch_id
                ).delete(synchronize_session=False)

                for seq, col_name in enumerate(CHECK_ITEMS, start=1):
                    result_raw = _stringify(raw.get(col_name, ""))
                    result_status, abnormal_flag = _normalize_result_status(result_raw)

                    db.add(B4FInspectionItem(
                        ragic_id       = f"{batch_id}_{seq}",
                        batch_ragic_id = batch_id,
                        seq_no         = seq,
                        item_name      = col_name,
                        result_raw     = result_raw,
                        result_status  = result_status,
                        abnormal_flag  = abnormal_flag,
                        synced_at      = now,
                    ))
                    item_rows += 1

                upserted += 1

            except Exception as exc:
                errors.append(f"ragic_id={ragic_id}: {exc}")
                logger.warning(f"[B4FSync] 記錄 {ragic_id} 失敗：{exc}")

        db.commit()
        logger.info(
            f"[B4FSync] 完成：fetched={fetched}, batches_upserted={upserted}, "
            f"items={item_rows}, errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[B4FSync] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {
        "fetched":   fetched,
        "upserted":  upserted,
        "item_rows": item_rows,
        "errors":    errors,
    }
