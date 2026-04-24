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
    return db.query(Tenant).filter(Tenant.is_active == True).all()


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
