"""
Ragic 與 Portal 欄位比對 Router

路由前綴：/api/v1/settings/ragic-field-audit

端點：
  GET  /summary           — 首頁 KPI Card 摘要
  GET  /modules           — 模組比對總覽（Tab 1）
  GET  /module            — 單一模組欄位 Mapping 明細（Tab 2）?route=...
  GET  /issues            — 異常清單（Tab 3）
  GET  /kpi-mappings      — KPI 計算追溯（Tab 4）
  POST /run               — 執行比對稽核
  GET  /export            — 匯出 Excel 報告（Tab 5）
  PATCH /mapping/{id}/resolve  — 標記異常為已處理
  GET  /runs              — 歷史執行紀錄

權限需求：
  ragic_field_audit_view    — 查看所有 GET 端點
  ragic_field_audit_manage  — 執行比對、標記已處理
  ragic_field_audit_admin   — 同 manage（預留）
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.models.ragic_field_audit import RagicPortalFieldMapping
import app.services.ragic_field_audit_service as svc

router = APIRouter()

# ── Dependency 快捷 ───────────────────────────────────────────────────────────
_view   = Depends(require_permission("ragic_field_audit_view"))
_manage = Depends(require_permission("ragic_field_audit_manage"))


# ── Pydantic Schema ───────────────────────────────────────────────────────────

class RunAuditRequest(BaseModel):
    scope: str = "all"   # "all" 或 module 路由


class ResolveMappingRequest(BaseModel):
    is_resolved: bool
    notes: Optional[str] = None


class SyncRagicFieldsRequest(BaseModel):
    item_no: int
    ragic_url: str   # 完整的 Ragic 表單 URL，例如 https://ap12.ragic.com/soutlet001/security-patrol/2


class SetModuleRagicUrlRequest(BaseModel):
    ragic_url: str   # 完整的 Ragic 表單 URL（空字串表示清除）


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    _: User = _view,
):
    """首頁 KPI Card 摘要：已設定模組數、已比對、正常、異常、未對應欄位、高風險異常。"""
    return svc.get_audit_summary(db)


@router.get("/modules")
def list_modules(
    company: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = _view,
):
    """
    取得模組比對總覽清單（Tab 1）。
    支援 company / status（normal/warning/error/not_audited）/ keyword 篩選。
    """
    modules = svc.get_module_overview(db)

    if company:
        modules = [m for m in modules if company in (m.get("company") or "")]
    if status:
        modules = [m for m in modules if m["status"] == status]
    if keyword:
        kw = keyword.lower()
        modules = [
            m for m in modules
            if kw in (m.get("module_name") or "").lower()
            or kw in (m.get("portal_name") or "").lower()
            or kw in (m.get("portal_route") or "").lower()
        ]

    return {"items": modules, "total": len(modules)}


@router.get("/module")
def get_module_detail(
    route: str = Query(..., description="Portal 路由，例如 /security/dashboard"),
    db: Session = Depends(get_db),
    _: User = _view,
):
    """
    取得單一模組的欄位 Mapping 明細（Tab 2）。
    若尚未執行比對，自動從 DB schema 生成草稿預覽。
    """
    detail = svc.get_module_field_detail(db, route)
    return {"route": route, "items": detail, "total": len(detail)}


@router.get("/issues")
def list_issues(
    severity: Optional[str] = Query(None, description="high / medium / low"),
    is_resolved: Optional[bool] = Query(None),
    module_name: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = _view,
):
    """
    取得所有異常欄位清單（Tab 3）。
    支援嚴重程度、是否已處理、模組名稱、關鍵字篩選。
    """
    issues = svc.get_all_issues(db, severity=severity, is_resolved=is_resolved)

    if module_name:
        issues = [i for i in issues if module_name in (i.get("module_name") or "")]
    if keyword:
        kw = keyword.lower()
        issues = [
            i for i in issues
            if kw in (i.get("module_name") or "").lower()
            or kw in (i.get("portal_db_field") or "").lower()
            or kw in (i.get("issue_message") or "").lower()
        ]

    return {"items": issues, "total": len(issues)}


@router.get("/kpi-mappings")
def list_kpi_mappings(
    module_name: Optional[str] = Query(None),
    trace_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = _view,
):
    """
    取得 KPI / Dashboard 計算追溯清單（Tab 4）。
    支援 module_name / trace_status 篩選。
    """
    items = svc.get_kpi_mappings(db, module_name=module_name)

    if trace_status:
        items = [i for i in items if i.get("trace_status") == trace_status]

    return {"items": items, "total": len(items)}


@router.post("/run")
def run_audit(
    payload: RunAuditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ragic_field_audit_manage")),
):
    """
    執行欄位比對稽核任務。
    掃描本地 DB schema，對比 Portal API / 前端欄位設定，生成比對紀錄。
    """
    result = svc.run_audit(
        db=db,
        triggered_by=current_user.email or current_user.username,
        scope=payload.scope,
    )
    return result


@router.get("/export")
def export_excel(
    db: Session = Depends(get_db),
    _: User = _view,
):
    """
    匯出 Excel 稽核報告（Tab 5）。
    包含 5 個工作表：模組總覽、欄位 Mapping、異常清單、KPI追溯、建議修正清單。
    """
    try:
        excel_bytes = svc.generate_excel_report(db)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    from app.core.time import twnow
    filename = f"ragic_field_audit_{twnow().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/mapping/{mapping_id}/resolve")
def resolve_mapping(
    mapping_id: int,
    payload: ResolveMappingRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("ragic_field_audit_manage")),
):
    """標記單筆欄位異常為已處理 / 取消已處理。"""
    row = db.query(RagicPortalFieldMapping).filter(
        RagicPortalFieldMapping.id == mapping_id
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="找不到 mapping 紀錄")

    row.is_resolved = payload.is_resolved
    if payload.notes is not None:
        row.notes = payload.notes

    db.commit()
    db.refresh(row)
    return {"id": row.id, "is_resolved": row.is_resolved, "notes": row.notes}



@router.post("/sync-ragic-fields")
def sync_ragic_fields(
    payload: SyncRagicFieldsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("ragic_field_audit_manage")),
):
    """
    從 Ragic API 抓取指定表單的欄位清單並儲存至 ragic_portal_field_mappings。

    - 呼叫 {ragic_url}?api=&limit=1 推斷欄位名稱與型態
    - 呼叫 {ragic_url}?info=1 取得欄位 metadata（型態、必填、公式等）
    - 有 Portal 對應的欄位 → 更新 ragic_* 資訊
    - 無 Portal 對應的欄位 → 建立 mapping_status=ragic_only 紀錄
    """
    result = svc.sync_ragic_fields_from_url(
        db=db,
        item_no=payload.item_no,
        ragic_url=payload.ragic_url,
        triggered_by=current_user.email or current_user.username,
    )
    return result


@router.get("/ragic-url-map")
def get_ragic_url_map(
    _: User = _view,
):
    """
    取得系統已知的 Ragic 表單 URL 對照表（itemNo → ragic_url）。
    供前端預填「同步 Ragic 欄位」的 URL 輸入框使用。
    """
    return {"items": [
        {"item_no": item_no, "ragic_url": url}
        for item_no, url in svc.RAGIC_URL_MAP.items()
    ]}


@router.patch("/modules/{item_no}/ragic-url")
def set_module_ragic_url(
    item_no: int,
    payload: SetModuleRagicUrlRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("ragic_field_audit_manage")),
):
    """
    設定（或清除）指定模組的 Ragic 表單 URL。
    URL 持久化存儲於 ragic_app_portal_annotations.ragic_url。
    同時回填該路由所有 ragic_portal_field_mappings 的 ragic_url 欄位，
    讓 Tab 2 Drawer 的「在 Ragic 查看」連結立即可用。
    """
    from app.models.ragic_app_directory import RagicAppPortalAnnotation
    from app.models.ragic_field_audit import RagicPortalFieldMapping
    import app.services.ragic_field_audit_service as svc_mod

    ragic_url = payload.ragic_url.strip()

    # 1. 更新 ragic_app_portal_annotations（upsert）
    annotation = db.query(RagicAppPortalAnnotation).filter(
        RagicAppPortalAnnotation.item_no == item_no
    ).first()
    if annotation:
        annotation.ragic_url = ragic_url
    else:
        annotation = RagicAppPortalAnnotation(
            item_no=item_no,
            ragic_url=ragic_url,
        )
        db.add(annotation)

    # 2. 找出此 item_no 對應的 portal_route
    portal_route = ""
    info = svc_mod.PORTAL_MODULE_MAP.get(item_no, {})
    if info.get("portal_url"):
        portal_route = info["portal_url"]

    # 3. 回填 ragic_portal_field_mappings.ragic_url（若路由已有 mapping 記錄）
    updated_mappings = 0
    if portal_route:
        result = db.query(RagicPortalFieldMapping).filter(
            RagicPortalFieldMapping.portal_route == portal_route
        ).update({"ragic_url": ragic_url or None})
        updated_mappings = result

    db.commit()

    return {
        "item_no": item_no,
        "ragic_url": ragic_url,
        "portal_route": portal_route,
        "updated_mappings": updated_mappings,
    }


@router.get("/runs")
def list_audit_runs(
    db: Session = Depends(get_db),
    _: User = _view,
):
    """取得歷史比對任務紀錄（最近 20 筆）。"""
    from app.models.ragic_field_audit import RagicPortalAuditRun
    rows = db.query(RagicPortalAuditRun).order_by(
        RagicPortalAuditRun.run_time.desc()
    ).limit(20).all()

    return {
        "items": [
            {
                "id": r.id,
                "run_time": r.run_time.isoformat(),
                "triggered_by": r.triggered_by,
                "scope": r.scope,
                "total_modules": r.total_modules,
                "normal_count": r.normal_count,
                "warning_count": r.warning_count,
                "error_count": r.error_count,
                "status": r.status,
                "notes": r.notes,
            }
            for r in rows
        ]
    }
