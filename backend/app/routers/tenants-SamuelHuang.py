from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.dependencies import get_current_user, is_system_admin
from app.models.tenant import Tenant
from app.schemas.tenant import TenantOut, TenantCreate

router = APIRouter()


@router.get("", response_model=List[TenantOut])
def list_tenants(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 2026-09-01：加上 order_by(name)。本表已改為「公司/部門管理」Company 的
    # 鏡像（見 services/tenant_company_sync.py），而公司清單是
    # `order_by(Company.name)`；這裡不排序的話，人員管理下拉的順序會跟
    # 公司/部門管理頁面對不起來（PG 不保證回傳順序）。
    return db.query(Tenant).filter(Tenant.is_active == True).order_by(Tenant.name).all()


@router.post("", response_model=TenantOut)
def create_tenant(
    data: TenantCreate,
    current_user=Depends(is_system_admin),
    db: Session = Depends(get_db),
):
    if db.query(Tenant).filter(Tenant.code == data.code.upper()).first():
        raise HTTPException(400, "據點代碼已存在")
    tenant = Tenant(code=data.code.upper(), name=data.name, type=data.type)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant
