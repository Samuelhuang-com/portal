"""
I3 — 保證金退還提醒服務

每日 10:00 由 APScheduler 觸發。
掃描「保留中」且 expected_return_date 在 30 天內的保證金，
建立系統 Memo 提醒（冪等去重）。
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from app.core.database import SessionLocal


def notify_expiring_deposits() -> None:
    """掃描即將到期保證金，發送 Memo 提醒。"""
    db = SessionLocal()
    try:
        today = date.today()
        threshold = today + timedelta(days=30)
        today_str = today.isoformat()
        threshold_str = threshold.isoformat()

        from app.models.contract import Contract, ContractDeposit
        from app.models.memo import Memo

        deposits = (
            db.query(ContractDeposit)
            .filter(
                ContractDeposit.status == "保留中",
                ContractDeposit.expected_return_date >= today_str,
                ContractDeposit.expected_return_date <= threshold_str,
            )
            .all()
        )

        if not deposits:
            print(f"[DepositAlert] {today} — 無即將到期保證金")
            return

        created = 0
        for deposit in deposits:
            source_id = f"deposit_expiry_{deposit.id}"
            already = (
                db.query(Memo)
                .filter(Memo.source == "deposit_alert", Memo.source_id == source_id)
                .first()
            )
            if already:
                continue

            contract = db.query(Contract).filter(
                Contract.contract_id == deposit.contract_id
            ).first()
            contract_name = contract.contract_name if contract else deposit.contract_id
            manager = (contract.manager or "") if contract else ""

            days_left = (date.fromisoformat(deposit.expected_return_date) - today).days

            body = (
                f"【保證金退還提醒】\n\n"
                f"合約：{contract_name}（{deposit.contract_id}）\n"
                f"保證金類型：{deposit.deposit_type}\n"
                f"保證金金額：${float(deposit.deposit_amount):,.0f}\n"
                f"預計退還日：{deposit.expected_return_date}（還有 {days_left} 天）\n"
                f"銀行：{deposit.bank_name or '—'}\n\n"
                f"請確認是否需要辦理退還手續，或申請延期。\n\n"
                f"管理人：{manager or '—'}"
            )

            memo = Memo(
                id=str(uuid.uuid4()),
                title=f"【保證金退還】{contract_name} — {deposit.deposit_type}（{days_left} 天後到期）",
                body=body,
                visibility="org",
                author="系統",
                author_id="",
                doc_no="",
                recipient=manager,
                source="deposit_alert",
                source_id=source_id,
            )
            db.add(memo)
            created += 1

        db.commit()
        print(f"[DepositAlert] {today} — 即將到期保證金 {len(deposits)} 筆，新增 Memo {created} 筆")

    except Exception as exc:
        db.rollback()
        print(f"[DepositAlert] 執行失敗：{exc}")
        raise
    finally:
        db.close()
