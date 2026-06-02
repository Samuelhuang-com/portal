"""
G4 — 合約到期自動終止服務

每日 01:00 由 APScheduler 觸發。
掃描 end_date < today 且狀態仍為「生效中」或「即將到期」的合約，
自動將狀態改為「已終止」，並記錄操作日誌。
"""
from __future__ import annotations

from datetime import date

from app.core.database import SessionLocal


def auto_close_expired_contracts() -> None:
    """將已逾期合約改為「已終止」（每日 01:00 執行）。"""
    db = SessionLocal()
    try:
        from sqlalchemy import text
        today = date.today()

        result = db.execute(
            text(
                "UPDATE contracts "
                "SET contract_status = '已終止', updated_at = CURRENT_TIMESTAMP "
                "WHERE end_date < :today "
                "  AND contract_status IN ('生效中', '即將到期')"
            ),
            {"today": today.isoformat()},
        )
        db.commit()

        count = result.rowcount
        if count > 0:
            print(f"[AutoClose] {today} — 已自動終止 {count} 份逾期合約")
        else:
            print(f"[AutoClose] {today} — 無需自動終止")

    except Exception as exc:
        db.rollback()
        print(f"[AutoClose] 執行失敗：{exc}")
        raise
    finally:
        db.close()
