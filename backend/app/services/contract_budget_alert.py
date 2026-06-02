"""
G1 — 合約預算使用率警示服務

每日 09:30 由 APScheduler 觸發。
掃描「生效中/即將到期」合約，計算請款金額使用率：
  usage_rate = (已核准 + 已付款 請款金額) / total_amount_tax_included

當使用率首次跨越以下閾值時，建立系統 Memo（冪等去重）：
  80%  → 黃色提醒
  90%  → 橘色警告
  100% → 紅色超額警示

冪等 key：source='budget_alert'，source_id='{contract_id}_{threshold}'
例：CON-2026-0001_80 代表「80% 警示已發送過」
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.contract import Contract, ContractClaim
from app.models.memo import Memo

# 警示閾值（%）
THRESHOLDS = [80, 90, 100]


def _usage_rate(total: float, used: float) -> float:
    if not total or total <= 0:
        return 0.0
    return round(used / total * 100, 2)


def check_budget_alerts() -> None:
    """掃描合約預算使用率，發送跨越閾值的 Memo 警示。"""
    db: Session = SessionLocal()
    try:
        today = datetime.now().date()

        # 取得所有生效中 / 即將到期合約
        contracts = (
            db.query(Contract)
            .filter(
                Contract.contract_status.in_(["生效中", "即將到期"]),
                Contract.total_amount_tax_included > 0,
            )
            .all()
        )

        created = 0
        for contract in contracts:
            # 計算已核准 + 已付款的請款金額加總
            used_amount = (
                db.query(func.sum(ContractClaim.amount))
                .filter(
                    ContractClaim.contract_id == contract.contract_id,
                    ContractClaim.status.in_(["已核准", "已付款"]),
                )
                .scalar()
            ) or 0.0

            rate = _usage_rate(float(contract.total_amount_tax_included), float(used_amount))

            for threshold in THRESHOLDS:
                if rate < threshold:
                    continue  # 未達此閾值，跳過

                source_id = f"{contract.contract_id}_{threshold}"

                # 冪等：此閾值是否已發送過
                already = (
                    db.query(Memo)
                    .filter(
                        Memo.source == "budget_alert",
                        Memo.source_id == source_id,
                    )
                    .first()
                )
                if already:
                    continue

                # 依閾值決定標題與語氣
                if threshold == 100:
                    prefix = "【超額警示】"
                    detail = f"請款金額已達 **{rate:.1f}%**，超過合約總額 ${contract.total_amount_tax_included:,.0f}。"
                elif threshold == 90:
                    prefix = "【使用率警告】"
                    detail = f"請款金額已達合約總額的 **{rate:.1f}%**，剩餘可用額度即將耗盡。"
                else:
                    prefix = "【使用率提醒】"
                    detail = f"請款金額已達合約總額的 **{rate:.1f}%**，請留意預算使用情況。"

                body = (
                    f"{prefix}\n\n"
                    f"合約：{contract.contract_name}（{contract.contract_id}）\n"
                    f"廠商：{contract.vendor_name or '—'}\n"
                    f"合約總額：${float(contract.total_amount_tax_included):,.0f}\n"
                    f"已請款金額：${float(used_amount):,.0f}\n"
                    f"{detail}\n\n"
                    f"管理人：{contract.manager or '—'}\n"
                    f"請確認是否需要調整預算或辦理追加。"
                )

                memo = Memo(
                    id=str(uuid.uuid4()),
                    title=f"{prefix} {contract.contract_name} 請款金額達 {threshold}%",
                    body=body,
                    visibility="org",
                    author="系統",
                    author_id="",
                    doc_no="",
                    recipient=contract.manager or "",
                    source="budget_alert",
                    source_id=source_id,
                )
                db.add(memo)
                created += 1

        if created > 0:
            db.commit()
            print(f"[BudgetAlert] {today} — 已建立 {created} 筆預算使用率警示 Memo")
        else:
            print(f"[BudgetAlert] {today} — 無新增警示")

    except Exception as exc:
        db.rollback()
        print(f"[BudgetAlert] 執行失敗：{exc}")
        raise
    finally:
        db.close()
