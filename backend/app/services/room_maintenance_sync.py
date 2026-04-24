"""
客房保養同步服務：Ragic → SQLite

Ragic 以 naming="" 回傳時，key 為中文欄位標籤（非數字 ID），如：
  "房號", "檢查項目", "工作項目選擇", "小計" …
本模組直接以中文 key 取值，不做 key 正規化。
"""
import logging
from datetime import datetime, timezone
from app.core.time import twnow
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.room_maintenance import RoomMaintenanceRecord
from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

# ── Ragic 回傳的中文欄位 key（naming="" 時的格式）────────────────────────────
CK_ROOM_NO       = "房號"
CK_INSPECT_ITEMS = "檢查項目"
CK_WORK_ITEM     = "工作項目選擇"
CK_INSPECT_DT    = "檢查日期時間"
CK_DEPT          = "報修部門"
CK_CLOSE_DATE    = "結案日期"
CK_SUBTOTAL      = "小計"
CK_INCOMPLETE    = "未完成小計"


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


def _to_inspect_list(val: Any) -> list[str]:
    """
    Ragic 的「檢查項目」可能是：
      - list 內含一個逗號分隔字串：["客房房門,配電盤,浴廁"]
      - 純字串："客房房門,配電盤,浴廁"
      - list 內多個字串：["客房房門", "配電盤"]
    統一展開並去空白。
    """
    items: list[str] = []
    if isinstance(val, list):
        for item in val:
            # 每個 item 可能還是逗號串
            for part in str(item).split(","):
                part = part.strip()
                if part:
                    items.append(part)
    elif isinstance(val, str):
        for part in val.split(","):
            part = part.strip()
            if part:
                items.append(part)
    return items


def _ragic_to_model(ragic_id: str, raw: dict[str, Any]) -> RoomMaintenanceRecord:
    """Ragic 原始 dict（中文 key）→ ORM 物件"""
    rec = RoomMaintenanceRecord(ragic_id=ragic_id)

    rec.room_no          = _stringify(raw.get(CK_ROOM_NO, ""))
    rec.dept             = _stringify(raw.get(CK_DEPT, ""))
    rec.work_item        = _stringify(raw.get(CK_WORK_ITEM, ""))
    rec.inspect_datetime = _stringify(raw.get(CK_INSPECT_DT, ""))
    rec.close_date       = _stringify(raw.get(CK_CLOSE_DATE, ""))
    rec.subtotal         = _to_int(raw.get(CK_SUBTOTAL, 0))
    rec.incomplete       = _to_int(raw.get(CK_INCOMPLETE, 0))
    rec.set_inspect_items(_to_inspect_list(raw.get(CK_INSPECT_ITEMS, "")))

    # Ragic 時間戳（ms epoch）→ 字串
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


async def sync_from_ragic() -> dict:
    """
    從 Ragic 拉取所有客房保養資料，Upsert 到本地 SQLite。
    回傳 { fetched, upserted, errors }
    """
    adapter = RagicAdapter(sheet_path=settings.RAGIC_ROOM_MAINTENANCE_PATH)

    logger.info("[RoomMaintenance Sync] 開始從 Ragic 拉取資料...")
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[RoomMaintenance Sync] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    fetched  = len(raw_data)
    upserted = 0
    errors: list[str] = []

    db = SessionLocal()
    try:
        for ragic_id, raw in raw_data.items():
            try:
                new_rec = _ragic_to_model(str(ragic_id), raw)

                existing = db.get(RoomMaintenanceRecord, str(ragic_id))
                if existing:
                    existing.room_no          = new_rec.room_no
                    existing.inspect_items    = new_rec.inspect_items
                    existing.dept             = new_rec.dept
                    existing.work_item        = new_rec.work_item
                    existing.inspect_datetime = new_rec.inspect_datetime
                    existing.close_date       = new_rec.close_date
                    existing.subtotal         = new_rec.subtotal
                    existing.incomplete       = new_rec.incomplete
                    existing.ragic_created_at = new_rec.ragic_created_at
                    existing.ragic_updated_at = new_rec.ragic_updated_at
                    existing.synced_at        = new_rec.synced_at
                else:
                    db.add(new_rec)

                upserted += 1
            except Exception as exc:
                errors.append(f"ragic_id={ragic_id}: {exc}")
                logger.warning(f"[RoomMaintenance Sync] 記錄 {ragic_id} 失敗：{exc}")

        db.commit()
        logger.info(
            f"[RoomMaintenance Sync] 完成：fetched={fetched}, upserted={upserted}, errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        logger.error(f"[RoomMaintenance Sync] DB 寫入失敗：{exc}")
        errors.append(f"DB commit error: {exc}")
    finally:
        db.close()

    return {"fetched": fetched, "upserted": upserted, "errors": errors}
