"""
金旭 PMS 分析 — 資料匯入 API Router
Prefix: /api/v1/jinxu/import

規格書：docs/SPEC_jinxu_analytics.md §12.1

端點：
  POST /validate                  — 上傳 xlsx 驗證（不寫入）
  POST /commit                    — 正式匯入
  GET  /batches                   — 匯入紀錄清單
  GET  /batches/{id}              — 批次明細
  GET  /batches/{id}/errors       — 錯誤／警示明細
  GET  /batches/{id}/errors.csv   — 錯誤明細 CSV 下載
  POST /batches/{id}/rollback     — 回捲批次
  GET  /status                    — 資料涵蓋範圍

⚠️ 除了必須 await UploadFile.read() 的兩個上傳端點外，一律使用同步 def；
   重運算透過 run_in_threadpool 丟出去，不可在 async def 內直接呼叫 db.query()
   （見 CLAUDE.md 與 project_async_def_blocking_fix 事故）。
"""
from __future__ import annotations

import csv
import io
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.audit_log import AuditLog
from app.models.jinxu_import import (
    SOURCE_LABELS,
    SOURCE_TYPES,
    JinxuImportBatch,
    JinxuImportError,
)
from app.models.user import User
from app.services import jinxu_import_service as SVC

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024   # 20 MB（§15.5）
ALLOWED_SUFFIX = ".xlsx"


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _check_upload(file: UploadFile, content: bytes) -> None:
    """副檔名、大小、zip 檔頭檢查（§15.5）。"""
    name = (file.filename or "").lower()
    if not name.endswith(ALLOWED_SUFFIX):
        raise HTTPException(400, f"只接受 {ALLOWED_SUFFIX} 檔案")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, f"檔案超過 {MAX_UPLOAD_BYTES // 1024 // 1024} MB 上限")
    if not content.startswith(b"PK"):
        raise HTTPException(400, "檔案內容不是有效的 xlsx（缺少 zip 檔頭）")


def _fmt_dt(dt) -> str:
    return dt.isoformat(sep=" ", timespec="seconds") if dt else ""


def _batch_summary(b: JinxuImportBatch) -> dict:
    return {
        "id": b.id,
        "source_type": b.source_type,
        "source_label": b.source_label,
        "source_file_name": b.source_file_name,
        "file_size": b.file_size,
        "report_start_date": b.report_start_date,
        "report_end_date": b.report_end_date,
        "row_count_data": b.row_count_data,
        "row_count_inserted": b.row_count_inserted,
        "row_count_updated": b.row_count_updated,
        "row_count_skipped": b.row_count_skipped,
        "row_count_rejected": b.row_count_rejected,
        "row_count_child": b.row_count_child,
        "status": b.status,
        "quality_result": b.quality_result,
        "started_at": _fmt_dt(b.started_at),
        "completed_at": _fmt_dt(b.completed_at),
        "uploaded_by_name": b.uploaded_by_name,
        "error_message": b.error_message or "",
    }


# ── /validate ────────────────────────────────────────────────────────────────

@router.post("/validate", summary="上傳 xlsx 驗證（不寫入資料庫）")
async def validate_file(
    file: UploadFile = File(...),
    source_type: str | None = Form(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("jinxu_import")),
):
    content = await file.read()
    _check_upload(file, content)
    if source_type and source_type not in SOURCE_TYPES:
        raise HTTPException(400, f"未知的來源類型：{source_type}")

    try:
        return await run_in_threadpool(
            SVC.validate,
            db,
            content=content,
            file_name=file.filename or "",
            source_type=source_type,
        )
    except HTTPException:
        raise
    except Exception as exc:                       # noqa: BLE001
        logger.exception("金旭驗證失敗：%s", file.filename)
        raise HTTPException(400, f"檔案解析失敗：{exc}") from exc


# ── /commit ──────────────────────────────────────────────────────────────────

@router.post("/commit", summary="正式匯入 xlsx")
async def commit_file(
    request: Request,
    file: UploadFile = File(...),
    source_type: str | None = Form(None),
    session_id: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("jinxu_import")),
):
    content = await file.read()
    _check_upload(file, content)
    if source_type and source_type not in SOURCE_TYPES:
        raise HTTPException(400, f"未知的來源類型：{source_type}")

    try:
        result = await run_in_threadpool(
            SVC.commit,
            db,
            content=content,
            file_name=file.filename or "",
            source_type=source_type,
            session_id=session_id or str(uuid.uuid4()),
            user_id=str(current_user.id),
            user_name=getattr(current_user, "name", "") or getattr(current_user, "username", ""),
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:                       # noqa: BLE001
        logger.exception("金旭匯入失敗：%s", file.filename)
        raise HTTPException(400, f"匯入失敗：{exc}") from exc

    await run_in_threadpool(
        _write_audit, db, current_user, _client_ip(request),
        "jinxu_import_commit",
        f"{SOURCE_LABELS.get(result.get('source_type',''), '')} "
        f"{file.filename} → batch #{result.get('batch_id')} "
        f"新增{result.get('row_count_inserted',0)}/更新{result.get('row_count_updated',0)}/"
        f"略過{result.get('row_count_skipped',0)}",
        resource_id=str(result.get("batch_id") or ""),
    )
    return result


def _write_audit(
    db: Session,
    user: User,
    ip: str | None,
    action: str,
    detail: str,
    *,
    resource_id: str = "",
) -> None:
    """寫稽核日誌。AuditLog 無 detail 欄位，明細放 extra（JSON）。"""
    try:
        db.add(AuditLog(
            user_id=str(user.id),
            tenant_id=getattr(user, "tenant_id", None),
            action=action,
            resource_type="jinxu_import_batch",
            resource_id=resource_id or None,
            ip_address=ip,
            extra={"detail": detail[:1000]},
        ))
        db.commit()
    except Exception:                              # noqa: BLE001
        db.rollback()
        logger.warning("金旭稽核日誌寫入失敗（不影響主流程）", exc_info=True)


# ── /batches ─────────────────────────────────────────────────────────────────

@router.get("/batches", summary="匯入紀錄清單")
def list_batches(
    source_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("jinxu_import")),
):
    q = db.query(JinxuImportBatch)
    if source_type:
        q = q.filter(JinxuImportBatch.source_type == source_type)
    if status:
        q = q.filter(JinxuImportBatch.status == status)
    total = q.count()
    rows = (
        q.order_by(JinxuImportBatch.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_batch_summary(b) for b in rows],
    }


@router.get("/batches/{batch_id}", summary="批次明細")
def get_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("jinxu_import")),
):
    b = db.get(JinxuImportBatch, batch_id)
    if not b:
        raise HTTPException(404, f"批次 #{batch_id} 不存在")

    counts: dict[str, dict] = {}
    rows = (
        db.query(JinxuImportError.error_code, JinxuImportError.severity)
        .filter(JinxuImportError.batch_id == batch_id)
        .all()
    )
    for code, sev in rows:
        d = counts.setdefault(code, {"error_code": code, "severity": sev, "count": 0})
        d["count"] += 1

    out = _batch_summary(b)
    out.update({
        "session_id": b.session_id,
        "property_code": b.property_code,
        "property_name": b.property_name,
        "file_sha256": b.file_sha256,
        "sheet_name": b.sheet_name,
        "printed_at": b.printed_at,
        "row_count_source": b.row_count_source,
        "program_version": b.program_version,
        "totals": b.get_totals(),
        "reconcile": b.get_reconcile(),
        "issue_summary": sorted(counts.values(), key=lambda x: -x["count"]),
    })
    return out


@router.get("/batches/{batch_id}/errors", summary="批次錯誤／警示明細")
def list_batch_errors(
    batch_id: int,
    severity: str | None = Query(None),
    error_code: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("jinxu_import")),
):
    q = db.query(JinxuImportError).filter(JinxuImportError.batch_id == batch_id)
    if severity:
        q = q.filter(JinxuImportError.severity == severity)
    if error_code:
        q = q.filter(JinxuImportError.error_code == error_code)
    total = q.count()
    rows = (
        q.order_by(JinxuImportError.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [{
            "id": e.id,
            "source_row_no": e.source_row_no,
            "field_name": e.field_name,
            "raw_value": e.raw_value,
            "error_code": e.error_code,
            "error_message": e.error_message,
            "severity": e.severity,
        } for e in rows],
    }


@router.get("/batches/{batch_id}/errors.csv", summary="錯誤明細 CSV 下載")
def download_batch_errors(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("jinxu_import")),
):
    rows = (
        db.query(JinxuImportError)
        .filter(JinxuImportError.batch_id == batch_id)
        .order_by(JinxuImportError.id)
        .all()
    )
    buf = io.StringIO()
    buf.write("﻿")          # BOM，讓 Excel 正確辨識 UTF-8
    w = csv.writer(buf)
    w.writerow(["來源列號", "欄位", "原始值", "錯誤碼", "說明", "層級"])
    for e in rows:
        w.writerow([e.source_row_no, e.field_name, e.raw_value,
                    e.error_code, e.error_message, e.severity])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="jinxu_batch_{batch_id}_errors.csv"'},
    )


# ── /rollback ────────────────────────────────────────────────────────────────

@router.post("/batches/{batch_id}/rollback", summary="回捲批次")
def rollback_batch(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("jinxu_import")),
):
    try:
        result = SVC.rollback_batch(db, batch_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    _write_audit(
        db, current_user, _client_ip(request), "jinxu_import_rollback",
        f"batch #{batch_id} 回捲，刪除原始列 {result['deleted_raw_rows']} 筆，"
        f"曾覆蓋 {result['updated_keys_count']} 筆（無法還原）",
        resource_id=str(batch_id),
    )
    return result


# ── /status ──────────────────────────────────────────────────────────────────

@router.get("/status", summary="資料庫涵蓋範圍")
def import_status(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("jinxu_view")),
):
    return SVC.get_import_status(db)
