"""
週期採購 — 異常稽核紀錄 Service 層（第五期）

record_audit() 是給其他 service（cycle_purchase_receiving_service /
cycle_purchase_payment_service）內部呼叫的小工具，只負責組出一筆
CyclePurchaseAuditLog 並 db.add()，不 commit（沿用呼叫端既有的 transaction）。
這期沒有對外的新增／修改 API，前端只讀（GET /audit-log）。
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.cycle_purchase_audit import CyclePurchaseAuditLog


def record_audit(
    db: Session,
    document_type: str,
    document_id: int,
    document_no: str,
    event_type: str,
    description: str,
    operator_name: Optional[str] = None,
    operator_user_id: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
) -> CyclePurchaseAuditLog:
    row = CyclePurchaseAuditLog(
        document_type=document_type,
        document_id=document_id,
        document_no=document_no,
        event_type=event_type,
        description=description,
        operator_user_id=operator_user_id,
        operator_name=operator_name,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(row)
    return row


def list_audit_log(
    db: Session,
    document_type: Optional[str] = None,
    event_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    query = db.query(CyclePurchaseAuditLog)
    if document_type:
        query = query.filter(CyclePurchaseAuditLog.document_type == document_type)
    if event_type:
        query = query.filter(CyclePurchaseAuditLog.event_type == event_type)
    if date_from:
        query = query.filter(CyclePurchaseAuditLog.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(CyclePurchaseAuditLog.created_at <= datetime.combine(date_to, datetime.max.time()))
    return query.order_by(CyclePurchaseAuditLog.created_at.desc()).all()
