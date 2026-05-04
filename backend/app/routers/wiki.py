"""
知識庫（LLM Wiki）API Router
Prefix: /api/v1/wiki
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.wiki import (
    WikiArticleCreate,
    WikiArticleOut,
    WikiArticleUpdate,
    WikiAskRequest,
    WikiAskResponse,
    WikiListResponse,
)
from app.services import wiki_service as svc

router = APIRouter()


class ObsidianSyncResult(BaseModel):
    exported: int = 0
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[str] = []
    wiki_dir: str = ""
    message: str = ""


# ── 清單（分頁 + 搜尋）────────────────────────────────────────────────────────

@router.get("", response_model=WikiListResponse, summary="知識庫文章清單")
def list_articles(
    q: str = Query("", description="關鍵字搜尋（標題/內文/標籤）"),
    category: str = Query("all", description="all | sop | dev"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=5, le=100),
    published_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.list_articles(
        db,
        q=q,
        category=category,
        page=page,
        per_page=per_page,
        published_only=published_only,
    )


# ── 自動補 [[連結]] ────────────────────────────────────────────────────────────

@router.post("/auto-link", summary="自動補充文章間 [[連結]]（冪等）")
def auto_link(
    dry_run: bool = Query(False, description="True=只預覽，不寫入"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = svc.auto_link_articles(db, dry_run=dry_run)
    return result


# ── 圖譜資料 ──────────────────────────────────────────────────────────────────
# ⚠️ 必須放在 /{article_id} 之前，否則 "graph" 會被當作 article_id

@router.get("/graph", summary="知識庫圖譜（nodes + edges）")
def get_wiki_graph(
    category: str = Query("all", description="all | sop | dev"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return svc.build_graph(db, category=category)


# ── 詳情（by ID）──────────────────────────────────────────────────────────────

@router.get("/{article_id}", response_model=WikiArticleOut, summary="文章詳情")
def get_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = svc.get_article(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return WikiArticleOut.model_validate(article)


# ── 新增 ──────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=WikiArticleOut,
    status_code=status.HTTP_201_CREATED,
    summary="新增文章",
)
def create_article(
    payload: WikiArticleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="標題不得為空")
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="內文不得為空")
    article = svc.create_article(db, payload, current_user)
    return WikiArticleOut.model_validate(article)


# ── 更新 ──────────────────────────────────────────────────────────────────────

@router.patch("/{article_id}", response_model=WikiArticleOut, summary="更新文章")
def update_article(
    article_id: str,
    payload: WikiArticleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok, err = svc.update_article(db, article_id, payload, current_user)
    if not ok:
        raise HTTPException(
            status_code=404 if err == "not_found" else 400, detail=err
        )
    article = svc.get_article(db, article_id)
    return WikiArticleOut.model_validate(article)


# ── 刪除 ──────────────────────────────────────────────────────────────────────

@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT, summary="刪除文章")
def delete_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ok = svc.delete_article(db, article_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文章不存在")


# ── AI 問答 ───────────────────────────────────────────────────────────────────

@router.post("/ask", response_model=WikiAskResponse, summary="AI 問答助手")
def ask_wiki(
    payload: WikiAskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="問題不得為空")
    result = svc.ask_ai(db, payload.question, payload.category)
    return WikiAskResponse(**result)


# ── Obsidian 同步：DB → .md 匯出 ──────────────────────────────────────────────

@router.post("/export-obsidian", response_model=ObsidianSyncResult, summary="匯出到 Obsidian（DB → .md）")
def export_to_obsidian(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = svc.export_to_obsidian(db)
    result["message"] = (
        f"✅ 匯出完成：{result['exported']} 篇新增／更新，{result['skipped']} 篇已是最新，"
        f"{'⚠️ ' + str(len(result['errors'])) + ' 個錯誤' if result['errors'] else '無錯誤'}"
    )
    return result


# ── Obsidian 同步：.md → DB 匯入 ──────────────────────────────────────────────

@router.post("/import-obsidian", response_model=ObsidianSyncResult, summary="從 Obsidian 匯入（.md → DB）")
def import_from_obsidian(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = svc.import_from_obsidian(db)
    result["message"] = (
        f"✅ 匯入完成：{result['imported']} 篇新增，{result['updated']} 篇更新，"
        f"{result['skipped']} 篇已是最新，"
        f"{'⚠️ ' + str(len(result['errors'])) + ' 個錯誤' if result['errors'] else '無錯誤'}"
    )
    return result
