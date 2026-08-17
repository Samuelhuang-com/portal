"""
F1 — 基礎參考資料 Router
  /api/v1/settings/companies
  /api/v1/settings/departments
  /api/v1/settings/pricing-specs
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission, require_roles
from app.models.reference_data import Company, RefDepartment, PricingSpec, SlaMetricType
from app.models.user import User
from app.schemas.reference_data import (
    CompanyCreate, CompanyUpdate, CompanyResponse, CompanyOption,
    DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentOption,
    PricingSpecCreate, PricingSpecUpdate, PricingSpecResponse, PricingSpecOption,
    SlaMetricTypeCreate, SlaMetricTypeUpdate, SlaMetricTypeResponse, SlaMetricTypeOption,
)

router = APIRouter()

# 管理員 dependency（沿用現有 require_roles，system_admin 自動放行）
# ⚠ 2026-08-17：公司別／部門別改用下面的 _dept_admin_dep（見該處說明），
# 這個 _admin_dep 現在只剩計價規格／SLA 指標類型在用，維持原樣不動。
_admin_dep = require_roles("system_admin", "tenant_admin")

# 2026-08-17 新增：公司別／部門別要開放給「系統設定 → 公司/部門管理」這個新頁面，
# 也要讓週期採購鏡像同步的來源資料可以被非 system_admin 角色管理，因此改用跟
# 全站其他模組一致的 permission_key 模型，不再沿用寫死的 require_roles。
#
# tenant_admin 這個角色目前資料庫裡 0 人持有（跟 2026-08-12 users.py 改用
# settings_users_manage 時的情況完全相同，可比照辦理），改掉不影響任何真實
# 使用者；system_admin 仍透過 permissions=["*"] 無條件通過。
#
# 刻意不影響 pricing-specs／sla-metric-types（維持 _admin_dep）：那兩個是合約
# 模組的 K2 SLA 設定，跟這次「公司/部門」的整合範圍無關，不順手一起改。
_dept_admin_dep = require_permission("settings_departments_manage")


# ═══════════════════════════════════════════════════════════════════════════
# 公司別
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/companies/options", response_model=List[CompanyOption], summary="公司別下拉（啟用中）")
def company_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(Company).filter(Company.is_active == True).order_by(Company.name).all()
    return [CompanyOption(value=r.name, label=r.name, id=r.id) for r in rows]


@router.get("/companies", response_model=List[CompanyResponse], summary="公司別清單")
def list_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(_dept_admin_dep),
):
    return db.query(Company).order_by(Company.name).all()


@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED, summary="新增公司別")
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_dept_admin_dep),
):
    if db.query(Company).filter(Company.name == payload.name).first():
        raise HTTPException(status_code=400, detail=f"公司「{payload.name}」已存在")
    obj = Company(name=payload.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/companies/{company_id}", response_model=CompanyResponse, summary="修改公司別名稱")
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_dept_admin_dep),
):
    obj = db.query(Company).filter(Company.id == company_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="公司不存在")
    dup = db.query(Company).filter(Company.name == payload.name, Company.id != company_id).first()
    if dup:
        raise HTTPException(status_code=400, detail=f"公司名稱「{payload.name}」已被使用")
    obj.name = payload.name
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/companies/{company_id}/toggle", response_model=CompanyResponse, summary="切換公司啟用狀態")
def toggle_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_dept_admin_dep),
):
    obj = db.query(Company).filter(Company.id == company_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="公司不存在")
    obj.is_active = not obj.is_active
    db.commit()
    db.refresh(obj)
    return obj


# ═══════════════════════════════════════════════════════════════════════════
# 部門別
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/departments/options", response_model=List[DepartmentOption], summary="部門別下拉（啟用中）")
def department_options(
    company_id: Optional[int] = Query(None, description="依公司別篩選"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(RefDepartment).filter(RefDepartment.is_active == True)
    if company_id is not None:
        q = q.filter(RefDepartment.company_id == company_id)
    rows = q.order_by(RefDepartment.name).all()
    return [DepartmentOption(value=r.name, label=r.name) for r in rows]


@router.get("/departments", response_model=List[DepartmentResponse], summary="部門別清單")
def list_departments(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(_dept_admin_dep),
):
    q = db.query(RefDepartment)
    if company_id is not None:
        q = q.filter(RefDepartment.company_id == company_id)
    rows = q.order_by(RefDepartment.company_id, RefDepartment.name).all()
    # 填入 company_name
    result = []
    for r in rows:
        resp = DepartmentResponse.from_orm(r)
        resp.company_name = r.company.name if r.company else ""
        result.append(resp)
    return result


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED, summary="新增部門別")
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_dept_admin_dep),
):
    company = db.query(Company).filter(Company.id == payload.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="公司不存在")
    dup = db.query(RefDepartment).filter(
        RefDepartment.name == payload.name,
        RefDepartment.company_id == payload.company_id,
    ).first()
    if dup:
        raise HTTPException(status_code=400, detail=f"「{company.name}」下已有部門「{payload.name}」")
    obj = RefDepartment(name=payload.name, company_id=payload.company_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    resp = DepartmentResponse.from_orm(obj)
    resp.company_name = company.name
    return resp


@router.put("/departments/{dept_id}", response_model=DepartmentResponse, summary="修改部門別")
def update_department(
    dept_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_dept_admin_dep),
):
    obj = db.query(RefDepartment).filter(RefDepartment.id == dept_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="部門不存在")
    if payload.name is not None:
        new_company_id = payload.company_id if payload.company_id is not None else obj.company_id
        dup = db.query(RefDepartment).filter(
            RefDepartment.name == payload.name,
            RefDepartment.company_id == new_company_id,
            RefDepartment.id != dept_id,
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"同公司下已有部門「{payload.name}」")
        obj.name = payload.name
    if payload.company_id is not None:
        if not db.query(Company).filter(Company.id == payload.company_id).first():
            raise HTTPException(status_code=404, detail="目標公司不存在")
        obj.company_id = payload.company_id
    db.commit()
    db.refresh(obj)
    resp = DepartmentResponse.from_orm(obj)
    resp.company_name = obj.company.name if obj.company else ""
    return resp


@router.patch("/departments/{dept_id}/toggle", response_model=DepartmentResponse, summary="切換部門啟用狀態")
def toggle_department(
    dept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_dept_admin_dep),
):
    obj = db.query(RefDepartment).filter(RefDepartment.id == dept_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="部門不存在")
    obj.is_active = not obj.is_active
    db.commit()
    db.refresh(obj)
    resp = DepartmentResponse.from_orm(obj)
    resp.company_name = obj.company.name if obj.company else ""
    return resp


# ═══════════════════════════════════════════════════════════════════════════
# 計價規格
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/pricing-specs/options", response_model=List[PricingSpecOption], summary="計價規格下拉（啟用中）")
def pricing_spec_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(PricingSpec).filter(PricingSpec.is_active == True).order_by(PricingSpec.name).all()
    return [PricingSpecOption(value=r.name, label=r.name) for r in rows]


@router.get("/pricing-specs", response_model=List[PricingSpecResponse], summary="計價規格清單")
def list_pricing_specs(
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_dep),
):
    return db.query(PricingSpec).order_by(PricingSpec.name).all()


@router.post("/pricing-specs", response_model=PricingSpecResponse, status_code=status.HTTP_201_CREATED, summary="新增計價規格")
def create_pricing_spec(
    payload: PricingSpecCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_dep),
):
    if db.query(PricingSpec).filter(PricingSpec.name == payload.name).first():
        raise HTTPException(status_code=400, detail=f"計價規格「{payload.name}」已存在")
    obj = PricingSpec(name=payload.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/pricing-specs/{spec_id}", response_model=PricingSpecResponse, summary="修改計價規格")
def update_pricing_spec(
    spec_id: int,
    payload: PricingSpecUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_dep),
):
    obj = db.query(PricingSpec).filter(PricingSpec.id == spec_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="計價規格不存在")
    dup = db.query(PricingSpec).filter(PricingSpec.name == payload.name, PricingSpec.id != spec_id).first()
    if dup:
        raise HTTPException(status_code=400, detail=f"計價規格「{payload.name}」已存在")
    obj.name = payload.name
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/pricing-specs/{spec_id}/toggle", response_model=PricingSpecResponse, summary="切換計價規格啟用狀態")
def toggle_pricing_spec(
    spec_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_dep),
):
    obj = db.query(PricingSpec).filter(PricingSpec.id == spec_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="計價規格不存在")
    obj.is_active = not obj.is_active
    db.commit()
    db.refresh(obj)
    return obj


# ═══════════════════════════════════════════════════════════════════════════
# K2 — SLA 指標類型  /settings/sla-metric-types
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/sla-metric-types/options", response_model=List[SlaMetricTypeOption], summary="SLA 指標類型下拉（啟用中）")
def sla_type_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(SlaMetricType).filter(SlaMetricType.is_active == True).order_by(SlaMetricType.name).all()
    return [SlaMetricTypeOption(value=r.name, label=r.name) for r in rows]


@router.get("/sla-metric-types", response_model=List[SlaMetricTypeResponse], summary="SLA 指標類型清單")
def list_sla_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_dep),
):
    return db.query(SlaMetricType).order_by(SlaMetricType.name).all()


@router.post("/sla-metric-types", response_model=SlaMetricTypeResponse, status_code=status.HTTP_201_CREATED, summary="新增 SLA 指標類型")
def create_sla_type(
    payload: SlaMetricTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_dep),
):
    if db.query(SlaMetricType).filter(SlaMetricType.name == payload.name).first():
        raise HTTPException(status_code=400, detail=f"指標類型「{payload.name}」已存在")
    obj = SlaMetricType(name=payload.name, description=payload.description)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/sla-metric-types/{type_id}", response_model=SlaMetricTypeResponse, summary="修改 SLA 指標類型")
def update_sla_type(
    type_id: int,
    payload: SlaMetricTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_dep),
):
    obj = db.query(SlaMetricType).filter(SlaMetricType.id == type_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="指標類型不存在")
    if payload.name and payload.name != obj.name:
        if db.query(SlaMetricType).filter(SlaMetricType.name == payload.name).first():
            raise HTTPException(status_code=400, detail=f"名稱「{payload.name}」已存在")
        obj.name = payload.name
    if payload.description is not None:
        obj.description = payload.description
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/sla-metric-types/{type_id}/toggle", response_model=SlaMetricTypeResponse, summary="切換 SLA 指標類型啟用狀態")
def toggle_sla_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_dep),
):
    obj = db.query(SlaMetricType).filter(SlaMetricType.id == type_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="指標類型不存在")
    obj.is_active = not obj.is_active
    db.commit()
    db.refresh(obj)
    return obj
