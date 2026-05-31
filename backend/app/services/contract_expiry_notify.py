"""
E3 — 合約到期自動通知服務

每日 09:00 由 APScheduler 觸發。
- 查詢 30 天內到期且狀態為「生效中」或「即將到期」的合約
- 為每份合約建立一筆系統 Memo（source='contract_expiry', source_id=contract_id）
- 使用 source_id 做冪等去重，同一合約同一天只會產生一筆
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.contract import Contract
from app.models.memo import Memo


def notify_expiring_contracts() -> None:
    """掃描即將到期合約，寫入系統 Memo（冪等）。"""
    db: Session = SessionLocal()
    try:
        today = date.today()
        deadline = today + timedelta(days=30)

        # 取得 30 天內到期、且狀態在「生效中」或「即將到期」的合約
        contracts = (
            db.query(Contract)
            .filter(
                Contract.end_date != None,  # noqa: E711
                Contract.end_date <= str(deadline),
                Contract.end_date >= str(today),
                Contract.contract_status.in_(["生效中", "即將到期"]),
            )
            .all()
        )

        created = 0
        for contract in contracts:
            days_left = (
                date.fromisoformat(str(contract.end_date)[:10]) - today
            ).days

            # 冪等判斷：今天是否已建立過此合約的到期通知
            today_str = today.isoformat()
            already = (
                db.query(Memo)
                .filter(
                    Memo.source == "contract_expiry",
                    Memo.source_id == contract.contract_id,
                    Memo.created_at >= f"{today_str} 00:00:00",
                )
                .first()
            )
            if already:
                continue

            title = (
                f"【合約到期提醒】{contract.contract_name} "
                f"（{contract.contract_id}）將於 {days_left} 天後到期"
            )
            body = (
                f"合約「{contract.contract_name}」（{contract.contract_id}）\n"
                f"廠商：{contract.vendor_name or '—'}\n"
                f"到期日：{str(contract.end_date)[:10]}\n"
                f"剩餘天數：{days_left} 天\n"
                f"管理人：{contract.manager or '—'}\n"
                f"審核人：{contract.reviewer or '—'}\n\n"
                f"請盡快確認是否需要續約或終止合約。"
            )

            memo = Memo(
                id=str(uuid.uuid4()),
                title=title,
                body=body,
                visibility="org",
                author="系統",
                author_id="",
                doc_no="",
                recipient=contract.manager or "",
                source="contract_expiry",
                source_id=contract.contract_id,
            )
            db.add(memo)
            created += 1

        if created > 0:
            db.commit()
            print(f"[ContractExpiry] 已建立 {created} 筆到期通知 Memo（{today}）")
        else:
            print(f"[ContractExpiry] 無新增通知（{today}）")

    except Exception as exc:
        db.rollback()
        print(f"[ContractExpiry] 通知失敗：{exc}")
        raise
    finally:
        db.close()
