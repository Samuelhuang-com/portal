"""
RagicConnection 通用同步服務

run_sync(connection_id, triggered_by)
  - 從 RagicConnection 記錄取得連線資訊（解密 API Key）
  - 呼叫 RagicAdapter.fetch_all() 拉取全量資料
  - 計算 checksum；若資料未變更則略過寫入 DataSnapshot
  - 寫入 SyncLog（started_at / finished_at / status / records_fetched）
  - 更新 RagicConnection.last_synced_at

sync_all_active()
  - 掃描所有 is_active=True 的連線並依序執行 run_sync
  - 排程器或 API /sync-all 呼叫用
"""
from datetime import datetime, timezone
from app.core.time import twnow

from app.core.database import SessionLocal
from app.core.crypto import decrypt
from app.models.ragic_connection import RagicConnection
from app.models.sync_log import SyncLog
from app.models.data_snapshot import DataSnapshot
from app.services.ragic_adapter import RagicAdapter


def _now() -> datetime:
    return twnow()


async def run_sync(connection_id: str, triggered_by: str = "manual") -> dict:
    """
    執行單一 RagicConnection 同步。

    回傳 { "status": "success"|"skipped"|"error", "records_fetched": int, "error": str|None }
    """
    db = SessionLocal()
    log = None
    try:
        conn = (
            db.query(RagicConnection)
            .filter(
                RagicConnection.id == connection_id,
                RagicConnection.is_active == True,
            )
            .first()
        )
        if not conn:
            return {"status": "error", "records_fetched": 0, "error": "連線不存在或已停用"}

        # 建立 SyncLog
        log = SyncLog(
            connection_id=connection_id,
            triggered_by=triggered_by,
            started_at=_now(),
            status="running",
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        # 建立 Adapter（解密 API Key，自動組合 server URL）
        api_key = decrypt(conn.api_key_enc)
        server_url = (
            conn.server if "." in conn.server else f"{conn.server}.ragic.com"
        )
        adapter = RagicAdapter(
            sheet_path=conn.sheet_path,
            api_key=api_key,
            server_url=server_url,
            account=conn.account_name,
        )

        data = await adapter.fetch_all()
        checksum = RagicAdapter.compute_checksum(data)

        # 若資料未變更則跳過寫入 DataSnapshot
        last = (
            db.query(DataSnapshot)
            .filter(DataSnapshot.connection_id == connection_id)
            .order_by(DataSnapshot.synced_at.desc())
            .first()
        )

        if last and last.checksum == checksum:
            log.status = "success"
            log.records_fetched = 0
            log.finished_at = _now()
            log.error_msg = "資料未變更，跳過儲存"
        else:
            snapshot = DataSnapshot(
                connection_id=connection_id,
                sync_log_id=log.id,
                data=data,
                record_count=len(data),
                checksum=checksum,
                synced_at=_now(),
            )
            db.add(snapshot)
            log.status = "success"
            log.records_fetched = len(data)
            log.finished_at = _now()

        conn.last_synced_at = _now()
        db.commit()
        return {"status": "success", "records_fetched": log.records_fetched, "error": None}

    except Exception as exc:
        if log:
            log.status = "error"
            log.error_msg = str(exc)
            log.finished_at = _now()
            try:
                db.commit()
            except Exception:
                pass
        return {"status": "error", "records_fetched": 0, "error": str(exc)}
    finally:
        db.close()


async def sync_all_active() -> dict:
    """
    排程用：同步所有 is_active=True 的 RagicConnection。
    回傳 { connection_id: result_dict }
    """
    db = SessionLocal()
    try:
        conn_ids = [
            c.id
            for c in db.query(RagicConnection)
            .filter(RagicConnection.is_active == True)
            .all()
        ]
    finally:
        db.close()

    results = {}
    for conn_id in conn_ids:
        results[conn_id] = await run_sync(conn_id, triggered_by="scheduler")
    return results
