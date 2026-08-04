"""
OPERA 營運分析 — 資料匯入 API Router
Prefix: /api/v1/opera/import

規格書：docs/SPEC_opera_analytics.md §10.1

端點：
  POST /validate            — 上傳 TXT 驗證（不寫入）
  POST /commit              — 正式匯入
  GET  /batches             — 匯入紀錄清單
  GET  /batches/{id}        — 批次明細
  GET  /batches/{id}/errors — 錯誤明細
  GET  /batches/{id}/errors.csv — 錯誤明細 CSV 下載
  GET  /batches/{id}/raw/{raw_id} — 原始資料列（Drawer「原始資料列」用）
  GET  /status              — 資料庫涵蓋範圍

⚠️ 除了必須 await UploadFile.read() 的兩個上傳端點外，一律使用同步 def；
   重運算透過 run_in_threadpool 丟出去，不可在 async def 內直接呼叫 db.query()。
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
from app.models.opera_departure import OperaDepartureRaw
from app.models.opera_import import OperaImportBatch, OperaImportError, SOURCE_DEPARTURE
from app.models.opera_revenue import OperaHistoryForecastRaw
from app.models.user import User
from app.services import opera_import_service as SVC

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


# ── /validate ────────────────────────────────────────────────────────────────

@router.post("/validate", summary="上傳 TXT 驗證（不寫入資料庫）")
async def validate_file(
    file: UploadFile = File(...),
    source_type: str | None = Form(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_import")),
):
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="僅支援 OPERA 匯出的 .txt 檔案")

    content = await file.read()
    try:
        return await run_in_threadpool(
            SVC.validate, db, file.filename, content, source_type,
        )
    except SVC.OperaImportError_ as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── /commit ──────────────────────────────────────────────────────────────────

@router.post("/commit", summary="正式匯入 TXT")
async def commit_file(
    request: Request,
    file: UploadFile = File(...),
    source_type: str | None = Form(None),
    session_id: str | None = Form(None),
    allow_warnings: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opera_import")),
):
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="僅支援 OPERA 匯出的 .txt 檔案")

    content = await file.read()
    ip = _client_ip(request)
    try:
        return await run_in_threadpool(
            SVC.commit,
            db=db,
            file_name=file.filename,
            content=content,
            source_type=source_type,
            session_id=session_id or str(uuid.uuid4()),
            user_id=current_user.id,
            user_name=getattr(current_user, "full_name", "") or getattr(current_user, "username", ""),
            ip_address=ip,
            allow_warnings=allow_warnings,
        )
    except SVC.OperaImportError_ as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:                    # noqa: BLE001 — 需回可讀訊息給前端
        logger.exception("[OPERA] 匯入失敗")
        raise HTTPException(status_code=500, detail=f"匯入失敗，已整批復原：{exc}")


# ── /batches ─────────────────────────────────────────────────────────────────

@router.get("/batches", summary="匯入紀錄清單")
def list_batches(
    source_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_view")),
):
    q = db.query(OperaImportBatch)
    if source_type:
        q = q.filter(OperaImportBatch.source_type == source_type)
    if status:
        q = q.filter(OperaImportBatch.status == status)
    total = q.count()
    rows = (
        q.order_by(OperaImportBatch.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [r.to_dict() for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/batches/{batch_id}", summary="批次明細")
def get_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_view")),
):
    row = db.query(OperaImportBatch).filter(OperaImportBatch.id == batch_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="找不到此匯入批次")
    return row.to_dict()


@router.get("/batches/{batch_id}/errors", summary="批次錯誤／警示明細")
def list_batch_errors(
    batch_id: int,
    severity: str | None = Query(None, description="ERROR / WARNING"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_view")),
):
    q = db.query(OperaImportError).filter(OperaImportError.batch_id == batch_id)
    if severity:
        q = q.filter(OperaImportError.severity == severity)
    total = q.count()
    rows = (
        q.order_by(OperaImportError.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [r.to_dict() for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/batches/{batch_id}/errors.csv", summary="錯誤明細 CSV 下載")
def download_batch_errors(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_view")),
):
    rows = (
        db.query(OperaImportError)
        .filter(OperaImportError.batch_id == batch_id)
        .order_by(OperaImportError.id)
        .all()
    )
    buf = io.StringIO()
    buf.write("﻿")                      # BOM，讓 Excel 正確辨識 UTF-8
    writer = csv.writer(buf)
    writer.writerow(["原始列號", "欄位", "原始值", "錯誤代碼", "說明", "嚴重度"])
    for r in rows:
        writer.writerow([
            r.source_row_no, r.field_name, r.raw_value,
            r.error_code, r.error_message, r.severity,
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="opera_batch_{batch_id}_errors.csv"'},
    )


# ── 原始資料列（明細 Drawer 的「🔗 原始資料列」）────────────────────────────

@router.get("/raw/{source_type}/{raw_id}", summary="取得單筆原始資料列")
def get_raw_row(
    source_type: str,
    raw_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_view")),
):
    model = OperaDepartureRaw if source_type == SOURCE_DEPARTURE else OperaHistoryForecastRaw
    row = db.query(model).filter(model.id == raw_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="找不到此原始資料列")
    return {
        "id":                row.id,
        "batch_id":          row.batch_id,
        "source_row_no":     row.source_row_no,
        "source_row_no_end": getattr(row, "source_row_no_end", row.source_row_no),
        "row_hash":          row.row_hash,
        "record_key":        row.record_key,
        "imported_at":       row.imported_at.strftime("%Y/%m/%d %H:%M") if row.imported_at else "",
        "fields":            row.to_source_dict(),
    }


# ── /status ──────────────────────────────────────────────────────────────────

@router.get("/status", summary="資料庫涵蓋範圍與最新批次")
def import_status(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_view")),
):
    return SVC.get_import_status(db)
