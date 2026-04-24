"""
客房保養明細同步服務：Ragic → SQLite

資料來源：https://ap12.ragic.com/soutlet001/report2/2
（不同 server/account，需傳入客製化 RagicAdapter 參數）

Ragic naming="" 時，key 為中文欄位標籤：
  保養日期、保養人員、房號、工時計算、建立日期
  房門、消防、設備、傢俱、客房燈/電源、客房窗、
  面盆/台面、浴厠、浴間、天地壁、客房空調、陽台
"""
import logging
from datetime import datetime, timezone
from app.core.time import twnow
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.room_maintenance_detail import RoomMaintenanceDetailRecord
from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

# ── Ragic 回傳的中文欄位 key ──────────────────────────────────────────────────
CK_MAINTAIN_DATE = "保養日期"
CK_STAFF_NAME    = "保養人員"
CK_ROOM_NO       = "房號"
CK_WORK_HOURS    = "工時計算"
CK_CREATED_DATE  = "建立日期"

# 檢查項目
CK_DOOR      = "房門"
CK_FIRE      = "消防"
CK_EQUIPMENT = "設備"
CK_FURNITURE = "傢俱"
CK_LIGHT     = "客房燈/電源"
CK_WINDOW    = "客房窗"
CK_SINK      = "面盆/台面"
CK_TOILET    = "浴厠"
CK_BATH      = "浴間"
CK_SURFACE   = "天地壁"
CK_AC        = "客房空調"
CK_BALCONY   = "陽台"


def _stringify(value: Any) -> str:
    """將各種值型別轉成字串"""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(_stringify(x) for x in value)
    if isinstance(value, dict):
        return _stringify(value.get("value") or value.get("label") or "")
    return str(value).strip()


def _ragic_to_model(
    ragic_id: str, raw: dict[str, Any]
) -> RoomMaintenanceDetailRecord:
    """Ragic 原始 dict（中文 key）→ ORM 物件"""
    rec = RoomMaintenanceDetailRecord(ragic_id=ragic_id)

    rec.maintain_date = _stringify(raw.get(CK_MAINTAIN_DATE, ""))
    rec.staff_name    = _stringify(raw.get(CK_STAFF_NAME,    ""))
    rec.room_no       = _stringify(raw.get(CK_ROOM_NO,       ""))
    rec.work_hours    = _stringify(raw.get(CK_WORK_HOURS,    ""))
    rec.created_date  = _stringify(raw.get(CK_CREATED_DATE,  ""))

    rec.chk_door      = _stringify(raw.get(CK_DOOR,      ""))
    rec.chk_fire      = _stringify(raw.get(CK_FIRE,      ""))
    rec.chk_equipment = _stringify(raw.get(CK_EQUIPMENT, ""))
    rec.chk_furniture = _stringify(raw.get(CK_FURNITURE, ""))
    rec.chk_light     = _stringify(raw.get(CK_LIGHT,     ""))
    rec.chk_window    = _stringify(raw.get(CK_WINDOW,    ""))
    rec.chk_sink      = _stringify(raw.get(CK_SINK,      ""))
    rec.chk_toilet    = _stringify(raw.get(CK_TOILET,    ""))
    rec.chk_bath      = _stringify(raw.get(CK_BATH,      ""))
    rec.chk_surface   = _stringify(raw.get(CK_SURFACE,   ""))
    rec.chk_ac        = _stringify(raw.get(CK_AC,        ""))
    rec.chk_balcony   = _stringify(raw.get(CK_BALCONY,   ""))

    rec.synced_at = twnow()
    return rec


def _get_adapter() -> RagicAdapter:
    """建立指向 ap12.ragic.com/soutlet001 的 RagicAdapter"""
    return RagicAdapter(
        sheet_path=settings.RAGIC_ROOM_DETAIL_PATH,
        api_key=settings.RAGIC_API_KEY,           # 同一組 API Key
        server_url=settings.RAGIC_ROOM_DETAIL_SERVER_URL,
        account=settings.RAGIC_ROOM_DETAIL_ACCOUNT,
    )


async def sync_from_ragic() -> dict:
    """
    從 Ragic 拉取所有客房保養明細資料，Upsert 到本地 SQLite。
    回傳 { fetched, upserted, errors }
    """
    adapter = _get_adapter()

    logger.info("[RoomDetailSync] 開始從 Ragic 拉取客房保養明細資料...")
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[RoomDetailSync] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    fetched  = len(raw_data)
    upserted = 0
    errors: list[str] = []

    db = SessionLocal()
    try:
        for ragic_id, raw in raw_data.items():
            try:
                new_rec = _ragic_to_model(str(ragic_id), raw)
                existing = db.get(RoomMaintenanceDetailRecord, str(ragic_id))
                if existing:
                    # Upsert：更新所有欄位
                    for field in [
                        "maintain_date", "staff_name", "room_no", "work_hours",
                        "created_date", "chk_door", "chk_fire", "chk_equipment",
                        "chk_furniture", "chk_light", "chk_window", "chk_sink",
                        "chk_toilet", "chk_bath", "chk_surface", "chk_ac",
                        "chk_balcony", "synced_at",
                    ]:
                        setattr(existing, field, getattr(new_rec, field))
                else:
                    db.add(new_rec)

                upserted += 1
            except Exception as exc:
                errors.append(f"ragic_id={ragic_id}: {exc}")
                logger.warning(f"[RoomDetailSync] 記錄 {ragic_id} 失敗：{exc}")

        db.commit()
        logger.info(
            f"[RoomDetailSync] 完成：fetched={fetched}, upserted={upserted},"
            f" errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        logger.error(f"[RoomDetailSync] DB 寫入失敗：{exc}")
        errors.append(f"DB commit error: {exc}")
    finally:
        db.close()

    return {"fetched": fetched, "upserted": upserted, "errors": errors}
