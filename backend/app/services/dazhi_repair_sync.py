"""
大直工務部報修同步服務：Ragic → SQLite

設計：
  1. 呼叫 dazhi_repair_service.fetch_all_cases() 取得清洗後的 RepairCase list
  2. Upsert 到 dazhi_repair_case 表（以 ragic_id 為 PK）
  3. 回傳 { fetched, upserted, errors }

不改動任何 RepairCase 欄位解析邏輯，確保統計與同步行為一致。
"""
import logging
from datetime import datetime, timezone
from app.core.time import twnow

from app.core.database import SessionLocal
from app.models.dazhi_repair import DazhiRepairCase

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return twnow()


async def sync_from_ragic() -> dict:
    """
    從 Ragic 拉取大直工務部所有報修案件，Upsert 到本地 SQLite。
    回傳 { fetched, upserted, errors }
    """
    from app.services.dazhi_repair_service import fetch_all_cases

    logger.info("[DazhiRepair Sync] 開始從 Ragic 拉取資料...")
    try:
        cases = await fetch_all_cases()
    except Exception as exc:
        logger.error(f"[DazhiRepair Sync] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    fetched  = len(cases)
    upserted = 0
    errors: list[str] = []
    now = _now()

    db = SessionLocal()
    try:
        for case in cases:
            try:
                existing = db.get(DazhiRepairCase, case.ragic_id)
                if existing:
                    existing.case_no          = case.case_no
                    existing.title            = case.title
                    existing.reporter_name    = case.reporter_name
                    existing.repair_type      = case.repair_type
                    existing.floor            = case.floor
                    existing.floor_normalized = case.floor_normalized
                    existing.occurred_at      = case.occurred_at
                    existing.responsible_unit = case.responsible_unit
                    existing.work_hours       = case.work_hours
                    existing.status           = case.status
                    existing.outsource_fee    = case.outsource_fee
                    existing.maintenance_fee  = case.maintenance_fee
                    existing.total_fee        = case.total_fee
                    existing.deduction_item   = case.deduction_item
                    existing.deduction_fee    = case.deduction_fee
                    existing.acceptor         = case.acceptor
                    existing.accept_status    = case.accept_status
                    existing.closer           = case.closer
                    existing.finance_note     = case.finance_note
                    existing.is_completed     = case.is_completed_flag
                    existing.completed_at     = case.completed_at
                    existing.close_days       = case.close_days
                    existing.year             = case.year
                    existing.month            = case.month
                    existing.is_room_case     = case.is_room_case
                    existing.room_no          = case.room_no
                    existing.room_category    = case.room_category
                    existing.synced_at        = now
                else:
                    db.add(DazhiRepairCase(
                        ragic_id          = case.ragic_id,
                        case_no           = case.case_no,
                        title             = case.title,
                        reporter_name     = case.reporter_name,
                        repair_type       = case.repair_type,
                        floor             = case.floor,
                        floor_normalized  = case.floor_normalized,
                        occurred_at       = case.occurred_at,
                        responsible_unit  = case.responsible_unit,
                        work_hours        = case.work_hours,
                        status            = case.status,
                        outsource_fee     = case.outsource_fee,
                        maintenance_fee   = case.maintenance_fee,
                        total_fee         = case.total_fee,
                        deduction_item    = case.deduction_item,
                        deduction_fee     = case.deduction_fee,
                        acceptor          = case.acceptor,
                        accept_status     = case.accept_status,
                        closer            = case.closer,
                        finance_note      = case.finance_note,
                        is_completed      = case.is_completed_flag,
                        completed_at      = case.completed_at,
                        close_days        = case.close_days,
                        year              = case.year,
                        month             = case.month,
                        is_room_case      = case.is_room_case,
                        room_no           = case.room_no,
                        room_category     = case.room_category,
                        synced_at         = now,
                    ))
                upserted += 1
            except Exception as exc:
                errors.append(f"ragic_id={case.ragic_id}: {exc}")
                logger.warning(f"[DazhiRepair Sync] 案件 {case.ragic_id} 失敗：{exc}")

        db.commit()
        logger.info(
            f"[DazhiRepair Sync] 完成：fetched={fetched}, upserted={upserted}, errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[DazhiRepair Sync] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {"fetched": fetched, "upserted": upserted, "errors": errors}
