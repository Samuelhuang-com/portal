"""
倉庫庫存同步服務：Ragic → SQLite

Ragic 以 naming="" 回傳時，key 為中文欄位標籤，如：
  "庫存編號", "倉庫代碼", "倉庫名稱", "商品編號", "商品名稱", "數量", "種類", "規格"
"""
import logging
from datetime import datetime, timezone
from app.core.time import twnow
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.inventory import InventoryRecord
from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

# ── Ragic 回傳的中文欄位 key（naming="" 時的格式）────────────────────────────
CK_INVENTORY_NO   = "庫存編號"
CK_WAREHOUSE_CODE = "倉庫代碼"
CK_WAREHOUSE_NAME = "倉庫名稱"
CK_PRODUCT_NO     = "商品編號"
CK_PRODUCT_NAME   = "商品名稱"
CK_QUANTITY       = "數量"
CK_CATEGORY       = "種類"
CK_SPEC           = "規格"


def _stringify(value: Any) -> str:
    """將各種值型別轉成字串"""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(_stringify(x) for x in value)
    if isinstance(value, dict):
        return _stringify(value.get("value") or value.get("label") or "")
    return str(value)


def _to_int(val: Any) -> int:
    try:
        return int(float(str(val))) if val not in (None, "", "None") else 0
    except (ValueError, TypeError):
        return 0


def _ragic_to_model(ragic_id: str, raw: dict[str, Any]) -> InventoryRecord:
    """Ragic 原始 dict（中文 key）→ ORM 物件"""
    rec = InventoryRecord(ragic_id=ragic_id)

    rec.inventory_no   = _stringify(raw.get(CK_INVENTORY_NO,   ""))
    rec.warehouse_code = _stringify(raw.get(CK_WAREHOUSE_CODE, ""))
    rec.warehouse_name = _stringify(raw.get(CK_WAREHOUSE_NAME, ""))
    rec.product_no     = _stringify(raw.get(CK_PRODUCT_NO,     ""))
    rec.product_name   = _stringify(raw.get(CK_PRODUCT_NAME,   ""))
    rec.quantity       = _to_int(raw.get(CK_QUANTITY, 0))
    rec.category       = _stringify(raw.get(CK_CATEGORY, ""))
    rec.spec           = _stringify(raw.get(CK_SPEC,     ""))

    # Ragic 時間戳（ms epoch）→ 字串
    ts = raw.get("_dataTimestamp")
    if ts:
        try:
            dt_str = datetime.fromtimestamp(
                int(ts) / 1000, tz=timezone.utc
            ).strftime("%Y/%m/%d %H:%M:%S")
            rec.ragic_created_at = dt_str
            rec.ragic_updated_at = dt_str
        except Exception:
            pass

    rec.synced_at = twnow()
    return rec


async def sync_from_ragic() -> dict:
    """
    從 Ragic 拉取所有倉庫庫存資料，Upsert 到本地 SQLite。
    回傳 { fetched, upserted, errors }
    """
    adapter = RagicAdapter(sheet_path=settings.RAGIC_INVENTORY_PATH)

    logger.info("[Inventory Sync] 開始從 Ragic 拉取倉庫庫存資料...")
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[Inventory Sync] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    fetched  = len(raw_data)
    upserted = 0
    errors: list[str] = []

    db = SessionLocal()
    try:
        for ragic_id, raw in raw_data.items():
            try:
                new_rec = _ragic_to_model(str(ragic_id), raw)

                existing = db.get(InventoryRecord, str(ragic_id))
                if existing:
                    existing.inventory_no   = new_rec.inventory_no
                    existing.warehouse_code = new_rec.warehouse_code
                    existing.warehouse_name = new_rec.warehouse_name
                    existing.product_no     = new_rec.product_no
                    existing.product_name   = new_rec.product_name
                    existing.quantity       = new_rec.quantity
                    existing.category       = new_rec.category
                    existing.spec           = new_rec.spec
                    existing.ragic_created_at = new_rec.ragic_created_at
                    existing.ragic_updated_at = new_rec.ragic_updated_at
                    existing.synced_at        = new_rec.synced_at
                else:
                    db.add(new_rec)

                upserted += 1
            except Exception as exc:
                errors.append(f"ragic_id={ragic_id}: {exc}")
                logger.warning(f"[Inventory Sync] 記錄 {ragic_id} 失敗：{exc}")

        db.commit()
        logger.info(
            f"[Inventory Sync] 完成：fetched={fetched}, upserted={upserted}, errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        logger.error(f"[Inventory Sync] DB 寫入失敗：{exc}")
        errors.append(f"DB commit error: {exc}")
    finally:
        db.close()

    return {"fetched": fetched, "upserted": upserted, "errors": errors}
