"""
主管交辦／緊急事件同步服務：Ragic → SQLite

設計：
  1. 呼叫 other_tasks_service.fetch_all_records() 取得清洗後的 OtherTaskRecord list
  2. Upsert 到 other_task 表（以 ragic_id 為 PK）
  3. 回傳 { fetched, upserted, errors }
"""
import json
import logging
from app.core.time import twnow

from app.core.database import SessionLocal
from app.models.other_tasks import OtherTask, OtherTaskRecord
from app.services.sync_dispatcher import register
from app.services.repair_detail_utils import extract_detail_records

logger = logging.getLogger(__name__)


@register("other_tasks")
async def sync_from_ragic() -> dict:
    """
    從 Ragic 拉取主管交辦／緊急事件所有記錄，Upsert 到本地 SQLite。
    回傳 { fetched, upserted, errors }
    """
    from app.services.other_tasks_service import fetch_all_records

    logger.info("[OtherTasks Sync] 開始從 Ragic 拉取資料...")
    try:
        records = await fetch_all_records()
    except Exception as exc:
        logger.error(f"[OtherTasks Sync] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}

    fetched  = len(records)
    upserted = 0
    errors: list[str] = []
    now = twnow()

    db = SessionLocal()
    try:
        all_ragic_ids = [r.ragic_id for r in records]
        existing_map: dict = {
            row.ragic_id: row
            for row in db.query(OtherTask).filter(
                OtherTask.ragic_id.in_(all_ragic_ids)
            ).all()
        }

        for rec in records:
            try:
                existing = existing_map.get(rec.ragic_id)
                if existing:
                    existing.task_type   = rec.task_type
                    existing.venue       = rec.venue
                    existing.supervisor  = rec.supervisor
                    existing.engineer    = rec.engineer
                    existing.created_at  = rec.created_at
                    existing.description = rec.description
                    existing.notes       = rec.notes
                    existing.updated_at  = rec.updated_at
                    existing.status      = rec.status
                    existing.work_hours  = rec.work_hours
                    existing.year        = rec.year
                    existing.month       = rec.month
                    existing.images_json = json.dumps(rec.images, ensure_ascii=False) if rec.images else None
                    existing.synced_at   = now
                else:
                    db.add(OtherTask(
                        ragic_id    = rec.ragic_id,
                        task_type   = rec.task_type,
                        venue       = rec.venue,
                        supervisor  = rec.supervisor,
                        engineer    = rec.engineer,
                        created_at  = rec.created_at,
                        description = rec.description,
                        notes       = rec.notes,
                        updated_at  = rec.updated_at,
                        status      = rec.status,
                        work_hours  = rec.work_hours,
                        year        = rec.year,
                        month       = rec.month,
                        images_json = json.dumps(rec.images, ensure_ascii=False) if rec.images else None,
                        synced_at   = now,
                    ))
                upserted += 1
            except Exception as exc:
                errors.append(f"ragic_id={rec.ragic_id}: {exc}")
                logger.warning(f"[OtherTasks Sync] 記錄 {rec.ragic_id} 失敗：{exc}")

        # ── 工單明細子表（維修記錄）：整批 delete + insert ────────────────────
        sub_count = 0
        try:
            db.query(OtherTaskRecord).filter(
                OtherTaskRecord.parent_ragic_id.in_(all_ragic_ids)
            ).delete(synchronize_session=False)
            for rec in records:
                for sub in extract_detail_records(getattr(rec, "_raw", None) or {}):
                    db.add(OtherTaskRecord(
                        ragic_id        = sub["ragic_id"],
                        parent_ragic_id = rec.ragic_id,
                        seq             = sub["seq"],
                        status          = sub["status"],
                        record          = sub["record"],
                        start_at        = sub["start_at"],
                        end_at          = sub["end_at"],
                        person          = sub["person"],
                        synced_at       = now,
                    ))
                    sub_count += 1
        except Exception as exc:
            errors.append(f"detail records: {exc}")
            logger.warning(f"[OtherTasks Sync] 子表同步失敗：{exc}")

        db.commit()
        logger.info(f"[OtherTasks Sync] 完成：共 {upserted} 筆，子表 {sub_count} 列，錯誤 {len(errors)} 筆")
    except Exception as exc:
        db.rollback()
        logger.error(f"[OtherTasks Sync] DB 寫入失敗：{exc}")
        return {"fetched": fetched, "upserted": 0, "errors": [str(exc)]}
    finally:
        db.close()

    return {"fetched": fetched, "upserted": upserted, "errors": errors}
