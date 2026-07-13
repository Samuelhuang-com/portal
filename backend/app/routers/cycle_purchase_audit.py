"""
週期採購 — 異常稽核紀錄 API Router
Prefix: /api/v1/cycle-purchase

2026-07-11（第五期新增）：這期只讀，沒有新增／修改／刪除 endpoint——紀錄
一律由系統內部在驗收單／請款單送出時自動寫入（見
cycle_purchase_receiving_service.submit_receiving／
cycle_purchase_payment_service.submit_payment）。

GET /audit-log   異常稽核紀錄清單（依關聯類型／事件類型／日期區間篩選）

查看權限用 cycle_purchase_admin（比較偏管理／治理性質，不是一般人員需要
看到的資訊，這期沒有另外開一個 cycle_purchase_audit 權限）。
"""
from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.cycle_purchase_audit import AuditLogOut
from app.services import cycle_purchase_audit_service as svc

router = APIRouter()


@router.get("/audit-log", response_model=List[AuditLogOut], summary="週期採購異常稽核紀錄清單")
def list_audit_log(
    document_type: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_audit_log(db, document_type=document_type, event_type=event_type, date_from=date_from, date_to=date_to)
