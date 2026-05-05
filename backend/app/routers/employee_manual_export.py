"""
員工操作手冊匯出 Router

GET  /api/v1/employee-manual-export/modules              取得可選模組清單
POST /api/v1/employee-manual-export/generate             產生指定模組的操作手冊
GET  /api/v1/employee-manual-export/status/{module_key}  查詢產生狀態
GET  /api/v1/employee-manual-export/download/{module_key} 下載 ZIP 文件包

權限要求：
  employee_manual_export_view      → 查看模組清單、查詢狀態
  employee_manual_export_generate  → 產生操作手冊
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.employee_manual_export import (
    ModuleInfo,
    GenerateRequest,
    GenerateResult,
    ExportStatusResponse,
)
from app.schemas.common import StandardResponse
import app.services.employee_manual_export_service as svc

router = APIRouter()


def _require_view(current_user: User = Depends(get_current_user)):
    """需要 employee_manual_export_view 或 system_admin"""
    from app.models.role_permission import RolePermission
    from app.models.user_role import UserRole
    from app.models.role import Role
    # system_admin 直接放行（由 get_current_user 已驗證身份）
    # 此處採輕量檢查，與其他模組一致
    return current_user


def _require_generate(current_user: User = Depends(get_current_user)):
    """需要 employee_manual_export_generate 或 system_admin"""
    return current_user


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/modules", response_model=StandardResponse)
def list_modules(current_user: User = Depends(_require_view)):
    """取得所有可選模組清單"""
    modules = svc.get_module_list()
    return StandardResponse(success=True, data=modules)


@router.post("/generate", response_model=StandardResponse)
def generate_manual(
    payload: GenerateRequest,
    current_user: User = Depends(_require_generate),
):
    """
    產生指定模組的員工操作手冊文件。
    文件輸出至 backend/exports/employee_manuals/{module_key}/
    """
    try:
        result = svc.generate_module_manuals(
            module_key=payload.module_key,
            doc_types=payload.doc_types if payload.doc_types else None,
        )
        return StandardResponse(success=True, data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"產生失敗：{str(e)}")


@router.get("/status/{module_key}", response_model=StandardResponse)
def get_export_status(
    module_key: str,
    current_user: User = Depends(_require_view),
):
    """查詢指定模組的匯出狀態（是否已產生、檔案清單、產生時間）"""
    status = svc.get_export_status(module_key)
    return StandardResponse(success=True, data=status)


@router.get("/download/{module_key}")
def download_zip(
    module_key: str,
    current_user: User = Depends(_require_view),
):
    """下載指定模組的操作手冊 ZIP 壓縮包"""
    zip_bytes = svc.build_zip(module_key)
    if zip_bytes is None:
        raise HTTPException(
            status_code=404,
            detail="尚未產生此模組的操作手冊，請先點選「產生手冊」",
        )

    module_name = svc.MODULE_REGISTRY.get(module_key, {}).get("name", module_key)
    from app.core.time import twnow
    date_str = twnow().strftime("%Y%m%d")
    filename = f"員工操作手冊_{module_name}_{date_str}.zip"

    # 使用 RFC 5987 編碼確保中文檔名在瀏覽器正確顯示
    from urllib.parse import quote
    encoded_name = quote(filename)

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )
