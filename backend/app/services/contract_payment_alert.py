"""
H3 — 分期付款逾期提醒服務

每日 09:45 由 APScheduler 觸發。
掃描「待付款」且 due_date < today 的付款里程碑，
自動：
  1. 將狀態改為「逾期」
  2. 建立系統 Memo 通知合約管理人（冪等去重）
"""
from __future__ import annotations

import uuid
from datetime import date

from app.core.database import SessionLocal


def notify_overdue_payment_schedules() -> None:
    """掃描逾期付款里程碑，更新狀態並發送 Memo。"""
    db = SessionLocal()
    try:
        today = date.today()
        today_str = today.isoformat()

        from app.models.contract import Contract, ContractPaymentSchedule
        from app.models.memo import Memo

        # 取得所有「待付款」且已逾期的里程碑
        overdue = (
            db.query(ContractPaymentSchedule)
            .filter(
                ContractPaymentSchedule.status == "待付款",
                ContractPaymentSchedule.due_date < today_str,
            )
            .all()
        )

        if not overdue:
            print(f"[PaymentAlert] {today} — 無逾期付款里程碑")
            return

        created_memos = 0
        for schedule in overdue:
            # 更新狀態為「逾期」
            schedule.status = "逾期"

            # 取得合約資訊（供 Memo 使用）
            contract = db.query(Contract).filter(
                Contract.contract_id == schedule.contract_id
            ).first()
            contract_name = contract.contract_name if contract else schedule.contract_id
            manager = (contract.manager or "") if contract else ""

            source_id = f"payment_overdue_{schedule.id}"
            already = (
                db.query(Memo)
                .filter(Memo.source == "payment_alert", Memo.source_id == source_id)
                .first()
            )
            if already:
                continue

            body = (
                f"【逾期付款提醒】\n\n"
                f"合約：{contract_name}（{schedule.contract_id}）\n"
                f"里程碑：{schedule.milestone_name or '付款里程碑'}\n"
                f"應付日期：{schedule.due_date}\n"
                f"應付金額：${float(schedule.amount):,.0f}\n\n"
                f"上述付款里程碑已逾期，請確認是否已完成付款，"
                f"若已付款請至「付款計劃」Tab 標記為已付款。\n\n"
                f"管理人：{manager or '—'}"
            )

            memo = Memo(
                id=str(uuid.uuid4()),
                title=f"【逾期付款】{contract_name} — {schedule.milestone_name or '付款里程碑'}",
                body=body,
                visibility="org",
                author="系統",
                author_id="",
                doc_no="",
                recipient=manager,
                source="payment_alert",
                source_id=source_id,
            )
            db.add(memo)
            created_memos += 1

        db.commit()
        print(
            f"[PaymentAlert] {today} — "
            f"逾期里程碑 {len(overdue)} 筆，新增 Memo {created_memos} 筆"
        )

    except Exception as exc:
        db.rollback()
        print(f"[PaymentAlert] 執行失敗：{exc}")
        raise
    finally:
        db.close()
