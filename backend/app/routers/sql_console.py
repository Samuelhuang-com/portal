# -*- coding: utf-8 -*-
"""
SQL 查詢工具 Router（僅系統管理員）

模組名稱：SQL 查詢工具 / SQL Console
前端路徑：/settings/sql-console（系統設定 選單下）
路由前綴：/api/v1/settings/sql-console

端點：
  GET  /tables           — 資料表與欄位清單（左側結構樹）
  POST /execute          — 執行 SELECT；DELETE 兩段式（先預覽拿 token，帶 token 再確認）
  POST /export           — 匯出 Excel / CSV（只限 SELECT，最多 50,000 筆）
  GET  /logs             — 操作紀錄（audit_logs，action = sql_console.*）
  GET  /logs/{id}        — 單筆紀錄（含 DELETE 被刪資料備份）

權限：全部端點 is_system_admin（只有「系統管理員」角色；不吃 permission key，
      也就不會被角色管理指派給別人）。
安全規則見 app/core/sql_guard.py 與 app/services/sql_console_service.py。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import is_system_admin
from app.models.user import User
import app.services.sql_console_service as svc

router = APIRouter()


class ExecuteBody(BaseModel):
    sql: str = Field(..., description="單一 SQL 敘述")
    limit: int = Field(svc.VIEW_DEFAULT_ROWS, ge=1, le=svc.VIEW_MAX_ROWS)
    confirm_token: Optional[str] = Field(None, description="DELETE 預覽後取得的確認碼")


class ExportBody(BaseModel):
    sql: str
    format: str = "xlsx"


def _ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


def _checked(db: Session, actor: dict, sql: str, request: Request):
    try:
        return svc.guard(sql)
    except svc.SqlGuardError as e:
        svc.log_blocked(db, actor, sql, str(e), _ip(request))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tables")
def get_tables(db: Session = Depends(get_db), _: User = Depends(is_system_admin)):
    try:
        return {"tables": svc.list_tables(db)}
    except svc.SqlConsoleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/execute")
def execute(body: ExecuteBody, request: Request, db: Session = Depends(get_db),
            user: User = Depends(is_system_admin)):
    actor = svc.actor_of(user)          # 先取出，之後 db.rollback() 會讓 ORM 物件過期
    gr = _checked(db, actor, body.sql, request)
    try:
        if gr.kind == "select":
            return svc.run_select(db, actor, gr, body.limit, _ip(request))
        if body.confirm_token:
            return svc.commit_delete(db, actor, gr, body.confirm_token, _ip(request))
        return svc.preview_delete(db, actor, gr)
    except svc.SqlConsoleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/export")
def export(body: ExportBody, request: Request, db: Session = Depends(get_db),
           user: User = Depends(is_system_admin)):
    actor = svc.actor_of(user)
    gr = _checked(db, actor, body.sql, request)
    if gr.kind != "select":
        raise HTTPException(status_code=400, detail="只有 SELECT 查詢可以匯出")
    try:
        res = svc.export_result(db, actor, gr, body.format, _ip(request))
    except svc.SqlConsoleError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(
        content=res["data"],
        media_type=res["content_type"],
        headers={
            # 檔名純 ASCII：Content-Disposition 走 Latin-1，中文會 500（見 project_export_filename_latin1）
            "Content-Disposition": f'attachment; filename="{res["filename"]}"',
            "X-Row-Count": str(res["row_count"]),
            "X-Truncated": "1" if res["truncated"] else "0",
            "Access-Control-Expose-Headers": "X-Row-Count, X-Truncated, Content-Disposition",
        },
    )


@router.get("/logs")
def logs(limit: int = 100, db: Session = Depends(get_db), _: User = Depends(is_system_admin)):
    return {"logs": svc.list_logs(db, limit)}


@router.get("/logs/{log_id}")
def log_detail(log_id: str, db: Session = Depends(get_db), _: User = Depends(is_system_admin)):
    d = svc.get_log_detail(db, log_id)
    if not d:
        raise HTTPException(status_code=404, detail="找不到這筆紀錄")
    return d
