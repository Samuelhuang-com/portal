"""
合約管理系統 - API 路由層

router 掛載於 /api/v1/contract（見 main.py）

端點一覽：
  GET    /                       合約列表（分頁、篩選、排序）
  POST   /                       新增合約
  GET    /stats                  合約統計
  POST   /sync                   立即同步（v2 Portal 版回傳空結果）
  GET    /dashboard/kpi          Dashboard KPI 指標
  GET    /dashboard/by-dept      Dashboard 部門金額分組
  GET    /budget-analysis        預算執行率分析（依預算科目聚合）
  GET    /{contract_id}          單筆合約詳情
  PUT    /{contract_id}          編輯合約
  DELETE /{contract_id}          邏輯刪除合約

  GET    /vendors/options         廠商下拉（用於表單）
  GET    /vendors                 廠商列表
  POST   /vendors                 新增廠商
  GET    /vendors/{vendor_id}             單筆廠商
  PUT    /vendors/{vendor_id}             編輯廠商
  DELETE /vendors/{vendor_id}             刪除廠商
  GET    /vendors/{vendor_id}/performance 廠商績效（準時率、爭議率、評分）

  GET    /budget-categories/options  預算科目下拉（用於表單）
  GET    /budget-categories          預算科目列表
  POST   /budget-categories          新增預算科目
  PUT    /budget-categories/{id}     編輯預算科目
  DELETE /budget-categories/{id}     刪除預算科目

注意：FastAPI 路由按宣告順序匹配，靜態路徑必須在動態路徑（{id}）之前宣告。
"""

import io
import uuid
from pathlib import Path
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ContractManagementException
from app.dependencies import get_current_user, get_user_permissions
from app.models.user import User
from app.models.contract import ContractAttachment
from app.services.contract_service import (
    ContractService,
    VendorService,
    BudgetCategoryService,
    ClaimService,
    ContractItemService,
    RenewalService,
    generate_contract_excel,
    generate_claims_excel,
    get_budget_analysis,
)
from app.schemas.contract import (
    ContractCreate,
    ContractUpdate,
    ContractDetailResponse,
    ContractListResponse,
    ContractStatsResponse,
    DashboardKPIResponse,
    DashboardByDeptResponse,
    VendorCreate,
    VendorUpdate,
    VendorResponse,
    VendorListResponse,
    VendorPagedResponse,
    BudgetCategoryCreate,
    BudgetCategoryUpdate,
    BudgetCategoryResponse,
    BudgetCategoryListResponse,
    BudgetCategoryPagedResponse,
    ContractClaimCreate,
    ContractClaimUpdate,
    ContractClaimResponse,
    ContractClaimReviewRequest,
    ContractClaimBatchReviewRequest,
    ContractItemCreate,
    ContractItemUpdate,
    ContractItemResponse,
    RenewalCreate,
    RenewalReview,
    RenewalResponse,
    VendorImportResult,
    ContractApprovalRequest,
)

router = APIRouter(tags=["合約管理"])


# ─────────────────────────────────────────────────────────────────────────────
# 合約列表 / 新增
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=ContractListResponse,
    summary="查詢合約列表",
)
def list_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1, description="頁碼"),
    size: int = Query(20, ge=1, le=200, description="每頁筆數"),
    search: Optional[str] = Query(None, description="搜尋編號或名稱"),
    status: Optional[str] = Query(None, description="合約狀態"),
    vendor_id: Optional[str] = Query(None, description="廠商ID"),
    risk_level: Optional[str] = Query(None, description="風險等級"),
    budget_year: Optional[int] = Query(None, description="預算年度"),
    responsible_dept: Optional[str] = Query(None, description="負責部門"),
    sort_by: str = Query("updated_at", description="排序欄位"),
    sort_order: str = Query("desc", description="排序順序"),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足，需要 contract_view")

        skip = (page - 1) * size
        contracts, total = ContractService.list_contracts(
            db,
            skip=skip,
            limit=size,
            search=search,
            status=status,
            vendor_id=vendor_id,
            risk_level=risk_level,
            budget_year=budget_year,
            responsible_dept=responsible_dept,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return ContractListResponse(total=total, page=page, size=size, items=contracts)

    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.post(
    "",
    response_model=ContractDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增合約",
)
def create_contract(
    contract_data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_create_edit" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足，需要 contract_create_edit")

        return ContractService.create_contract(db, contract_data)

    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# 統計 / 同步（靜態路徑，必須在 /{contract_id} 之前）
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    response_model=ContractStatsResponse,
    summary="合約統計",
)
def get_contract_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        return ContractService.get_stats(db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.post(
    "/sync",
    summary="立即同步（Portal v2 版）",
)
def sync_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Portal v2 無 Ragic 依賴，此端點保留以維持前端相容性。
    回傳 synced=0 表示無需同步。
    """
    user_permissions = get_user_permissions(current_user.id, db)
    if "*" not in user_permissions and "contract_admin" not in user_permissions:
        raise HTTPException(status_code=403, detail="權限不足，需要 contract_admin")
    return {"success": True, "synced": 0, "errors": []}


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard（靜態路徑，必須在 /{contract_id} 之前）
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/dashboard/kpi",
    response_model=DashboardKPIResponse,
    summary="Dashboard KPI 指標",
)
def get_dashboard_kpi(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    budget_year: Optional[int] = Query(None, description="預算年度（預設當年）"),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        return ContractService.get_dashboard_kpi(db, budget_year)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.get(
    "/dashboard/by-dept",
    response_model=DashboardByDeptResponse,
    summary="Dashboard 部門金額分組",
)
def get_dashboard_by_dept(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    budget_year: Optional[int] = Query(None, description="預算年度（預設當年）"),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        return ContractService.get_by_dept(db, budget_year)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# 到期預警清單（靜態路徑，必須在 /{contract_id} 之前）
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/expiring",
    summary="即將到期合約清單",
)
def list_expiring_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(90, ge=1, le=365, description="未來幾天內到期（預設 90）"),
):
    """
    傳回到期日在今天 ~ 今天+days 之間且狀態不是「已終止」的合約。
    依剩餘天數升冪排列。
    """
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        return ContractService.get_expiring(db, days)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# 合約列表匯出 Excel
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/export",
    summary="匯出合約列表 Excel（串流）",
)
def export_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    vendor_id: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    budget_year: Optional[int] = Query(None),
    responsible_dept: Optional[str] = Query(None),
):
    """帶入與列表頁相同的篩選條件，匯出全部符合記錄（不分頁）。"""
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        contracts, _ = ContractService.list_contracts(
            db, skip=0, limit=10000,
            search=search, status=status, vendor_id=vendor_id,
            risk_level=risk_level, budget_year=budget_year,
            responsible_dept=responsible_dept,
        )
        excel_bytes = generate_contract_excel(contracts)
        filename = f"合約列表_{date.today().strftime('%Y%m%d')}.xlsx"
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗：{str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# 預算執行率分析
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/budget-analysis",
    summary="預算執行率分析（依預算科目聚合）",
)
def get_budget_analysis_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    budget_year: int = Query(2026, ge=2020, le=2100, description="預算年度"),
):
    """
    依預算科目（L1 / L2）聚合：
    - contract_count：合約數量
    - total_claimed：請款總額
    - paid_amount：已付款金額
    - approved_amount：已核准待撥款金額
    - pending_amount：待審核金額
    """
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        return get_budget_analysis(db, budget_year)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# 單筆合約（動態路徑，必須在所有靜態路徑之後）
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/vendors/options",
    response_model=List[VendorListResponse],
    summary="廠商下拉選項（用於合約表單）",
)
def list_vendors_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = Query(None),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        vendors, _ = VendorService.list_vendors(db, skip=0, limit=2000, search=search)
        return [VendorListResponse(vendor_id=v.vendor_id, vendor_name=v.vendor_name) for v in vendors]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.post(
    "/vendors/import",
    response_model=VendorImportResult,
    summary="廠商 Excel 批次匯入（upsert）",
)
def import_vendors(
    file: UploadFile = File(..., description="廠商 Excel 檔（.xlsx）"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_vendor_manage" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")

        if not file.filename or not file.filename.lower().endswith(".xlsx"):
            raise HTTPException(status_code=400, detail="請上傳 .xlsx 格式的 Excel 檔案")

        file_bytes = file.file.read()
        result = VendorService.import_vendors_from_excel(db, file_bytes)
        return VendorImportResult(**result)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯入失敗：{str(e)}")


@router.get(
    "/vendors",
    response_model=VendorPagedResponse,
    summary="查詢廠商列表",
)
def list_vendors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    search: Optional[str] = Query(None),
    vendor_type: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    is_critical: Optional[bool] = Query(None),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_vendor_manage" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")

        skip = (page - 1) * size
        vendors, total = VendorService.list_vendors(
            db,
            skip=skip,
            limit=size,
            search=search,
            vendor_type=vendor_type,
            risk_level=risk_level,
            is_critical=is_critical,
        )
        return VendorPagedResponse(total=total, items=vendors)

    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.post(
    "/vendors",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增廠商",
)
def create_vendor(
    vendor_data: VendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_vendor_manage" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        return VendorService.create_vendor(db, vendor_data)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.get(
    "/vendors/{vendor_id}",
    response_model=VendorResponse,
    summary="查詢單筆廠商",
)
def get_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_vendor_manage" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        return VendorService.get_vendor(db, vendor_id)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise


@router.put(
    "/vendors/{vendor_id}",
    response_model=VendorResponse,
    summary="編輯廠商",
)
def update_vendor(
    vendor_id: str,
    vendor_data: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_vendor_manage" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        return VendorService.update_vendor(db, vendor_id, vendor_data)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.delete(
    "/vendors/{vendor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="刪除廠商",
)
def delete_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_vendor_manage" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        VendorService.delete_vendor(db, vendor_id)
        return None
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise


@router.get(
    "/vendors/{vendor_id}/performance",
    summary="廠商績效評分（準時率、爭議率、平均處理天數）",
)
def get_vendor_performance(
    vendor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return VendorService.get_vendor_performance(db, vendor_id)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# 預算科目 — options 必須在 /{category_id} 之前
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/budget-categories/options",
    response_model=List[BudgetCategoryListResponse],
    summary="預算科目下拉選項（用於合約表單）",
)
def list_budget_categories_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    budget_year: Optional[int] = Query(None),
    dept: Optional[str] = Query(None),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        categories, _ = BudgetCategoryService.list_budget_categories(
            db, skip=0, limit=2000, budget_year=budget_year, dept=dept, is_enabled=True
        )
        return [
            BudgetCategoryListResponse(
                id=c.id,
                budget_year=c.budget_year,
                category_l1=c.category_l1,
                category_l2=c.category_l2,
                accounting_code=c.accounting_code,
            )
            for c in categories
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.get(
    "/budget-categories",
    response_model=BudgetCategoryPagedResponse,
    summary="查詢預算科目列表",
)
def list_budget_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    budget_year: Optional[int] = Query(None),
    dept: Optional[str] = Query(None),
    category_l1: Optional[str] = Query(None),
    is_enabled: Optional[bool] = Query(None),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")

        skip = (page - 1) * size
        categories, total = BudgetCategoryService.list_budget_categories(
            db,
            skip=skip,
            limit=size,
            budget_year=budget_year,
            dept=dept,
            category_l1=category_l1,
            is_enabled=is_enabled,
        )
        return BudgetCategoryPagedResponse(total=total, items=categories)

    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.post(
    "/budget-categories",
    response_model=BudgetCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增預算科目",
)
def create_budget_category(
    category_data: BudgetCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_admin" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足，需要 contract_admin")
        return BudgetCategoryService.create_budget_category(db, category_data)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.put(
    "/budget-categories/{category_id}",
    response_model=BudgetCategoryResponse,
    summary="編輯預算科目",
)
def update_budget_category(
    category_id: int,
    category_data: BudgetCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_admin" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足，需要 contract_admin")
        return BudgetCategoryService.update_budget_category(db, category_id, category_data)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.delete(
    "/budget-categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="刪除預算科目",
)
def delete_budget_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_admin" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足，需要 contract_admin")
        BudgetCategoryService.delete_budget_category(db, category_id)
        return None
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise


# ─────────────────────────────────────────────────────────────────────────────
# 請款 / 核銷記錄（靜態路徑，必須在 /{contract_id} 之前）
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/claims/{claim_id}/review",
    response_model=ContractClaimResponse,
    summary="請款審核（核准 / 拒絕 / 付款 / 重送）",
)
def review_claim(
    claim_id: int,
    review_data: ContractClaimReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_claims_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        actor = getattr(current_user, "username", "") or getattr(current_user, "email", "")
        return ClaimService.review_claim(db, claim_id, review_data, actor)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise


@router.post(
    "/claims/batch-review",
    response_model=dict,
    summary="批次審核請款（approve / reject）",
)
def batch_review_claims(
    batch_data: ContractClaimBatchReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = getattr(current_user, "permissions", [])
        if "*" not in user_permissions and "contract_claims_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        actor = getattr(current_user, "username", "") or getattr(current_user, "email", "")
        return ClaimService.batch_review_claims(db, batch_data, actor)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/claims/export",
    summary="匯出請款清單 Excel（串流）",
)
def export_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    contract_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """帶入與請款頁相同的篩選條件，匯出全部符合記錄（不分頁）。"""
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_claims_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        claims, _ = ClaimService.list_claims(
            db, contract_id=contract_id, status=status,
            skip=0, limit=10000,
        )
        excel_bytes = generate_claims_excel(claims)
        filename = f"請款清單_{date.today().strftime('%Y%m%d')}.xlsx"
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匯出失敗：{str(e)}")


@router.get(
    "/claims/stats",
    response_model=dict,
    summary="請款統計（各狀態筆數/金額、當月請款）",
)
def get_claims_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        return ClaimService.get_stats(db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.get(
    "/claims",
    response_model=dict,
    summary="請款記錄清單（可按合約篩選）",
)
def list_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    contract_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        skip = (page - 1) * size
        items, total = ClaimService.list_claims(db, contract_id, status_filter, skip, size)
        return {"total": total, "page": page, "size": size, "items": [i.dict() for i in items]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.post(
    "/claims",
    response_model=ContractClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新增請款記錄",
)
def create_claim(
    claim_data: ContractClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_create_edit" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        return ClaimService.create_claim(db, claim_data)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.get(
    "/claims/{claim_id}",
    response_model=ContractClaimResponse,
    summary="單筆請款記錄",
)
def get_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        return ClaimService.get_claim(db, claim_id)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise


@router.put(
    "/claims/{claim_id}",
    response_model=ContractClaimResponse,
    summary="更新請款記錄",
)
def update_claim(
    claim_id: int,
    claim_data: ContractClaimUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_create_edit" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        return ClaimService.update_claim(db, claim_id, claim_data)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise


@router.delete(
    "/claims/{claim_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="刪除請款記錄",
)
def delete_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_create_edit" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        ClaimService.delete_claim(db, claim_id)
        return None
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise


# ─────────────────────────────────────────────────────────────────────────────
# 請款附件  /claims/{claim_id}/attachments  （靜態路徑優先於動態 {claim_id}）
# ─────────────────────────────────────────────────────────────────────────────

CLAIM_UPLOAD_DIR = Path("uploads/claims")
ATTACHMENT_ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg", "image/jpg", "image/png", "image/webp",
}
ATTACHMENT_MAX_SIZE = 20 * 1024 * 1024   # 20 MB


def _get_attachment_or_404(db, attachment_id: int):
    from app.models.contract import ContractClaimAttachment
    att = db.query(ContractClaimAttachment).filter(ContractClaimAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")
    return att


@router.post(
    "/claims/{claim_id}/attachments",
    summary="上傳請款附件（PDF / 圖片）",
    status_code=status.HTTP_201_CREATED,
)
async def upload_claim_attachment(
    claim_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.contract import ContractClaim, ContractClaimAttachment

    # 權限
    user_permissions = get_user_permissions(current_user.id, db)
    if "*" not in user_permissions and "contract_claims_view" not in user_permissions:
        raise HTTPException(status_code=403, detail="權限不足")

    # 請款存在
    claim = db.query(ContractClaim).filter(ContractClaim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="請款記錄不存在")

    # 類型檢查
    content_type = file.content_type or ""
    if content_type not in ATTACHMENT_ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="只接受 PDF / JPG / PNG / WEBP 格式")

    content = await file.read()
    if len(content) > ATTACHMENT_MAX_SIZE:
        raise HTTPException(status_code=400, detail="檔案大小不得超過 20 MB")

    # 儲存
    CLAIM_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "file").suffix or ".bin"
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    (CLAIM_UPLOAD_DIR / stored_name).write_bytes(content)

    att = ContractClaimAttachment(
        claim_id=claim_id,
        stored_filename=stored_name,
        original_filename=file.filename or stored_name,
        content_type=content_type,
        file_size=len(content),
        uploader=current_user.username,
    )
    db.add(att)
    db.commit()
    db.refresh(att)

    return {
        "id": att.id,
        "claim_id": att.claim_id,
        "original_filename": att.original_filename,
        "content_type": att.content_type,
        "file_size": att.file_size,
        "uploader": att.uploader,
        "created_at": att.created_at.isoformat(),
        "download_url": f"/api/v1/contract/claims/attachments/{att.id}/download",
    }


@router.get(
    "/claims/{claim_id}/attachments",
    summary="列出請款附件",
)
def list_claim_attachments(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.contract import ContractClaimAttachment

    user_permissions = get_user_permissions(current_user.id, db)
    if "*" not in user_permissions and "contract_claims_view" not in user_permissions:
        raise HTTPException(status_code=403, detail="權限不足")

    attachments = (
        db.query(ContractClaimAttachment)
        .filter(ContractClaimAttachment.claim_id == claim_id)
        .order_by(ContractClaimAttachment.created_at)
        .all()
    )
    return [
        {
            "id": a.id,
            "claim_id": a.claim_id,
            "original_filename": a.original_filename,
            "content_type": a.content_type,
            "file_size": a.file_size,
            "uploader": a.uploader,
            "created_at": a.created_at.isoformat(),
            "download_url": f"/api/v1/contract/claims/attachments/{a.id}/download",
        }
        for a in attachments
    ]


@router.get(
    "/claims/attachments/{attachment_id}/download",
    summary="下載 / 預覽請款附件",
)
def download_claim_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_permissions = get_user_permissions(current_user.id, db)
    if "*" not in user_permissions and "contract_claims_view" not in user_permissions:
        raise HTTPException(status_code=403, detail="權限不足")

    att = _get_attachment_or_404(db, attachment_id)
    file_path = CLAIM_UPLOAD_DIR / att.stored_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="附件檔案遺失")

    # 瀏覽器直接預覽（PDF / 圖片），使用 inline；下載用 attachment
    disposition = "inline" if att.content_type.startswith("image/") or att.content_type == "application/pdf" else "attachment"
    encoded_name = att.original_filename.encode("utf-8").decode("latin-1", errors="replace")
    return FileResponse(
        str(file_path),
        media_type=att.content_type,
        headers={"Content-Disposition": f"{disposition}; filename*=UTF-8''{att.original_filename}"},
    )


@router.delete(
    "/claims/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="刪除請款附件",
)
def delete_claim_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_permissions = get_user_permissions(current_user.id, db)
    if "*" not in user_permissions and "contract_claims_view" not in user_permissions:
        raise HTTPException(status_code=403, detail="權限不足")

    att = _get_attachment_or_404(db, attachment_id)
    file_path = CLAIM_UPLOAD_DIR / att.stored_filename
    if file_path.exists():
        file_path.unlink(missing_ok=True)
    db.delete(att)
    db.commit()
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 單筆合約 CRUD  /{contract_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{contract_id}",
    response_model=ContractDetailResponse,
    summary="單筆合約詳情",
)
def get_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        return ContractService.get_contract(db, contract_id)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.put(
    "/{contract_id}",
    response_model=ContractDetailResponse,
    summary="編輯合約",
)
def update_contract(
    contract_id: str,
    contract_data: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_create_edit" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足，需要 contract_create_edit")
        return ContractService.update_contract(db, contract_id, contract_data)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.delete(
    "/{contract_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="刪除合約",
)
def delete_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_create_edit" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足，需要 contract_create_edit")
        ContractService.delete_contract(db, contract_id)
        return None
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# 合約項目 (Line Items)  /{contract_id}/items
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{contract_id}/items",
    summary="查詢合約項目清單",
)
def list_contract_items(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        items = ContractItemService.list_items(db, contract_id)
        return {"total": len(items), "items": [i.dict() for i in items]}
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise


@router.post(
    "/{contract_id}/items",
    response_model=ContractItemResponse,
    summary="新增合約項目",
)
def create_contract_item(
    contract_id: str,
    item_data: ContractItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_create_edit" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足，需要 contract_create_edit")
        return ContractItemService.create_item(db, contract_id, item_data)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise


@router.put(
    "/{contract_id}/items/{item_id}",
    response_model=ContractItemResponse,
    summary="更新合約項目",
)
def update_contract_item(
    contract_id: str,
    item_id: int,
    item_data: ContractItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_create_edit" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足，需要 contract_create_edit")
        return ContractItemService.update_item(db, contract_id, item_id, item_data)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise


@router.delete(
    "/{contract_id}/items/{item_id}",
    summary="刪除合約項目",
)
def delete_contract_item(
    contract_id: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_create_edit" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足，需要 contract_create_edit")
        ContractItemService.delete_item(db, contract_id, item_id)
        return {"success": True}
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise


# ─────────────────────────────────────────────────────────────────────────────
# 合約續約  renewals
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/renewals/all",
    summary="查詢所有續約申請（跨合約）",
)
def list_all_renewals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    status: Optional[str] = Query(None),
    contract_id: Optional[str] = Query(None),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        from app.models.contract import ContractRenewal
        from app.schemas.contract import RenewalResponse
        q = db.query(ContractRenewal)
        if status:
            q = q.filter(ContractRenewal.status == status)
        if contract_id:
            q = q.filter(ContractRenewal.contract_id == contract_id)
        total = q.count()
        items = q.order_by(ContractRenewal.id.desc()).offset((page - 1) * size).limit(size).all()
        return {"total": total, "page": page, "size": size, "items": [
            RenewalResponse.from_orm(r) for r in items
        ]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.get(
    "/{contract_id}/renewals",
    summary="查詢單一合約的續約申請清單",
)
def list_renewals_by_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        from app.models.contract import ContractRenewal
        from app.schemas.contract import RenewalResponse
        items = db.query(ContractRenewal).filter(
            ContractRenewal.contract_id == contract_id
        ).order_by(ContractRenewal.id.desc()).all()
        return [RenewalResponse.from_orm(r) for r in items]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.post(
    "/{contract_id}/renewals",
    summary="申請合約續約",
)
def apply_for_renewal(
    contract_id: str,
    renewal_data: RenewalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_create_edit" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足，需要 contract_create_edit")
        contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail=f"合約 {contract_id} 不存在")
        from app.models.contract import ContractRenewal
        from app.schemas.contract import RenewalResponse
        renewal = ContractRenewal(
            contract_id=contract_id,
            renewal_start_date=renewal_data.renewal_start_date,
            renewal_end_date=renewal_data.renewal_end_date,
            new_amount=renewal_data.new_amount,
            renewal_reason=renewal_data.renewal_reason,
            remarks=renewal_data.remarks,
            applicant=current_user.full_name or current_user.email,
            applicant_dept=renewal_data.applicant_dept or "",
            status="待審核",
        )
        db.add(renewal)
        db.commit()
        db.refresh(renewal)
        return RenewalResponse.from_orm(renewal)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"申請失敗：{str(e)}")


@router.post(
    "/renewals/{renewal_id}/review",
    summary="審核 / 拒絕 / 撤回續約申請",
)
def review_renewal(
    renewal_id: int,
    review_data: RenewalReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_approve" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足，需要 contract_approve")
        from app.models.contract import ContractRenewal
        from app.schemas.contract import RenewalResponse
        renewal = db.query(ContractRenewal).filter(ContractRenewal.id == renewal_id).first()
        if not renewal:
            raise HTTPException(status_code=404, detail=f"續約申請 #{renewal_id} 不存在")
        action = review_data.action
        if action == "approve":
            renewal.status = "已核准"
            renewal.reviewer = current_user.full_name or current_user.email
            renewal.review_comment = review_data.review_comment
        elif action == "reject":
            renewal.status = "已拒絕"
            renewal.reviewer = current_user.full_name or current_user.email
            renewal.review_comment = review_data.review_comment
        elif action == "withdraw":
            renewal.status = "已撤回"
        else:
            raise HTTPException(status_code=400, detail=f"不支援的操作：{action}，請使用 approve / reject / withdraw")
        db.commit()
        db.refresh(renewal)
        return RenewalResponse.from_orm(renewal)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"審核失敗：{str(e)}")


# ════════════════════════════════════════════════════════════════════════════
# 合約審核流程端點
# ════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{contract_id}/submit",
    response_model=ContractDetailResponse,
    summary="送審（草稿 → 審核中）",
)
def submit_contract_for_review(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_view" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足")
        submitter = getattr(current_user, "username", "") or ""
        return ContractService.submit_for_review(db, contract_id, submitter)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.post(
    "/{contract_id}/approve",
    response_model=ContractDetailResponse,
    summary="核准合約（審核中 → 生效中）",
)
def approve_contract(
    contract_id: str,
    body: ContractApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_approve" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足（需 contract_approve 權限）")
        approver = getattr(current_user, "username", "") or ""
        return ContractService.approve_contract(db, contract_id, approver, body.comment)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


@router.post(
    "/{contract_id}/reject",
    response_model=ContractDetailResponse,
    summary="拒絕合約（審核中 → 草稿）",
)
def reject_contract(
    contract_id: str,
    body: ContractApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_permissions = get_user_permissions(current_user.id, db)
        if "*" not in user_permissions and "contract_approve" not in user_permissions:
            raise HTTPException(status_code=403, detail="權限不足（需 contract_approve 權限）")
        rejector = getattr(current_user, "username", "") or ""
        return ContractService.reject_contract(db, contract_id, rejector, body.comment)
    except ContractManagementException as e:
        raise HTTPException(status_code=e.status_code, detail={"message": e.message, "error_code": e.error_code})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"伺服器錯誤：{str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# 合約本體附件  /{contract_id}/attachments
# 靜態前綴 /doc-attachments/{id}/... 需在動態路由之前（已在頂端聲明 router order）
# ─────────────────────────────────────────────────────────────────────────────

CONTRACT_UPLOAD_DIR = Path("uploads/contracts")
_CONTRACT_ATTACH_ALLOWED = {
    "application/pdf",
    "image/jpeg", "image/png", "image/webp",
}
_CONTRACT_ATTACH_MAX_BYTES = 20 * 1024 * 1024  # 20 MB


def _get_contract_attachment_or_404(db: Session, attachment_id: int) -> ContractAttachment:
    att = db.query(ContractAttachment).filter(ContractAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="附件不存在")
    return att


@router.post(
    "/{contract_id}/attachments",
    summary="上傳合約附件",
)
async def upload_contract_attachment(
    contract_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_permissions = get_user_permissions(current_user.id, db)
    if "*" not in user_permissions and "contract_create_edit" not in user_permissions:
        raise HTTPException(status_code=403, detail="權限不足（需 contract_create_edit）")

    from app.models.contract import Contract
    if not db.query(Contract).filter(Contract.contract_id == contract_id).first():
        raise HTTPException(status_code=404, detail="合約不存在")

    content = await file.read()
    if len(content) > _CONTRACT_ATTACH_MAX_BYTES:
        raise HTTPException(status_code=413, detail="檔案超過 20MB 限制")
    if file.content_type not in _CONTRACT_ATTACH_ALLOWED:
        raise HTTPException(status_code=415, detail="僅支援 PDF / JPG / PNG / WEBP")

    CONTRACT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "file").suffix or ".bin"
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    (CONTRACT_UPLOAD_DIR / stored_name).write_bytes(content)

    att = ContractAttachment(
        contract_id=contract_id,
        stored_filename=stored_name,
        original_filename=file.filename or stored_name,
        content_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        uploader=getattr(current_user, "username", "") or "",
    )
    db.add(att)
    db.commit()
    db.refresh(att)

    return {
        "id": att.id,
        "original_filename": att.original_filename,
        "content_type": att.content_type,
        "file_size": att.file_size,
        "uploader": att.uploader,
        "created_at": att.created_at.isoformat() if att.created_at else None,
        "download_url": f"/api/v1/contract/doc-attachments/{att.id}/download",
    }


@router.get(
    "/{contract_id}/attachments",
    summary="列出合約附件",
)
def list_contract_attachments(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachments = (
        db.query(ContractAttachment)
        .filter(ContractAttachment.contract_id == contract_id)
        .order_by(ContractAttachment.created_at)
        .all()
    )
    return [
        {
            "id": a.id,
            "original_filename": a.original_filename,
            "content_type": a.content_type,
            "file_size": a.file_size,
            "uploader": a.uploader,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "download_url": f"/api/v1/contract/doc-attachments/{a.id}/download",
        }
        for a in attachments
    ]


@router.get(
    "/doc-attachments/{attachment_id}/download",
    summary="下載合約附件",
)
def download_contract_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    att = _get_contract_attachment_or_404(db, attachment_id)
    file_path = CONTRACT_UPLOAD_DIR / att.stored_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="附件檔案遺失")
    return FileResponse(
        path=str(file_path),
        media_type=att.content_type,
        filename=att.original_filename,
    )


@router.delete(
    "/doc-attachments/{attachment_id}",
    summary="刪除合約附件",
)
def delete_contract_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_permissions = get_user_permissions(current_user.id, db)
    if "*" not in user_permissions and "contract_create_edit" not in user_permissions:
        raise HTTPException(status_code=403, detail="權限不足（需 contract_create_edit）")

    att = _get_contract_attachment_or_404(db, attachment_id)
    file_path = CONTRACT_UPLOAD_DIR / att.stored_filename
    if file_path.exists():
        file_path.unlink()
    db.delete(att)
    db.commit()
    return {"success": True}
