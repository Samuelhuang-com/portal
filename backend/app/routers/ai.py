"""
AI 工單查詢 Router
Prefix: /api/v1/ai

端點：
  POST /query-workorder  — 自然語言查詢工務工單（需登入 + AI_ENABLED）
  GET  /history          — 取得目前使用者的歷史問答記錄

設計：
  - AI_ENABLED=false 時回傳 503
  - 依用戶 permissions 動態決定可查詢地點，不開放跨權限存取
  - 查詢快取（AIQueryCache）：相同問題 1 小時內直接從 DB 回傳，節省 API 額度
  - 對話記錄（AIConversationLog）：每次查詢永久寫入，供「歷史問答」面板使用
  - 地點顯示名稱：飯店（飯店工務部）、商場（商場工務報修）
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dependencies import get_current_user, get_user_permissions
from app.models.ai_cache import AIQueryCache
from app.models.ai_conversation_log import AIConversationLog
from app.models.user import User
from app.schemas.ai import AIHistoryItem, AIQueryRequest, AIQueryResponse, RepairRow
from app.services.ai_service import run_ai_query

logger = logging.getLogger(__name__)
router = APIRouter()

_CACHE_TTL_HOURS = 1
_CLEANUP_PROB = 0.1


# ── 快取工具 ──────────────────────────────────────────────────────────────────

def _cache_key(question: str, allowed_locations: list[str]) -> str:
    loc_str = "|".join(sorted(allowed_locations))
    raw = f"{question}\x00{loc_str}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_cache(db: Session, key: str) -> AIQueryCache | None:
    return (
        db.query(AIQueryCache)
        .filter(AIQueryCache.question_hash == key, AIQueryCache.expires_at > datetime.now())
        .first()
    )


def _set_cache(db: Session, key: str, question: str, allowed_locations: list[str], result: dict) -> None:
    now = datetime.now()
    db.query(AIQueryCache).filter(AIQueryCache.question_hash == key).delete()
    db.add(AIQueryCache(
        id=str(uuid.uuid4()),
        question_hash=key,
        question_text=question.strip()[:500],
        locations_key="|".join(sorted(allowed_locations)),
        answer=result.get("answer", ""),
        has_table=result.get("has_table", False),
        table_data_json=json.dumps(result.get("table_data", []), ensure_ascii=False),
        total_count=result.get("total_count"),
        hit_count=0,
        created_at=now,
        expires_at=now + timedelta(hours=_CACHE_TTL_HOURS),
    ))
    db.commit()


def _lazy_cleanup(db: Session) -> None:
    if random.random() < _CLEANUP_PROB:
        deleted = db.query(AIQueryCache).filter(AIQueryCache.expires_at <= datetime.now()).delete()
        if deleted:
            db.commit()
            logger.info("AI cache lazy cleanup: 清除 %d 筆過期條目", deleted)


# ── 對話記錄工具 ──────────────────────────────────────────────────────────────

def _log_query(
    db: Session,
    user_id: str,
    user_email: str,
    question: str,
    allowed_locations: list[str],
    result: dict,
    from_cache: bool,
) -> None:
    """將查詢結果寫入永久對話記錄表（失敗不影響主流程）"""
    try:
        db.add(AIConversationLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            user_email=user_email,
            question=question.strip()[:500],
            answer=result.get("answer", ""),
            has_table=result.get("has_table", False),
            table_data_json=json.dumps(result.get("table_data", []), ensure_ascii=False),
            total_count=result.get("total_count"),
            locations_key="|".join(sorted(allowed_locations)),
            from_cache=from_cache,
        ))
        db.commit()
    except Exception as exc:
        logger.warning("寫入 AI 對話記錄失敗: %s", exc)
        db.rollback()


# ── Permission → 地點 ─────────────────────────────────────────────────────────

def _resolve_allowed_locations(user_id: str, db: Session) -> list[str]:
    """
    依用戶 permissions 決定可查詢的工單地點（飯店 / 商場）。

    - system_admin → 全部
    - dazhi_repair_view 或 ai_workorder_view → 飯店
    - luqun_repair_view 或 ai_workorder_view → 商場
    """
    permissions = get_user_permissions(user_id, db)
    if "*" in permissions:
        return ["飯店", "商場"]

    locations: list[str] = []
    if "dazhi_repair_view" in permissions or "ai_workorder_view" in permissions:
        locations.append("飯店")
    if "luqun_repair_view" in permissions or "ai_workorder_view" in permissions:
        locations.append("商場")
    return locations


# ── 端點 ──────────────────────────────────────────────────────────────────────

@router.post("/query-workorder", response_model=AIQueryResponse)
def query_workorder(
    payload: AIQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    自然語言查詢工務工單。
    命中快取時直接回傳，不消耗 Anthropic API 額度。
    每次查詢（含快取命中）寫入 ai_conversation_log 供「歷史問答」使用。
    """
    if not settings.AI_ENABLED:
        raise HTTPException(status_code=503, detail="AI 功能目前未啟用")

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI 服務尚未設定（ANTHROPIC_API_KEY 未填）")

    allowed_locations = _resolve_allowed_locations(current_user.id, db)
    if not allowed_locations:
        raise HTTPException(status_code=403, detail="您目前沒有任何工單查詢權限，請聯絡系統管理員")

    # ── 快取查詢 ──────────────────────────────────────────────────────────────
    _lazy_cleanup(db)
    key = _cache_key(payload.question, allowed_locations)
    cached = _get_cache(db, key)

    if cached:
        logger.info("AI cache HIT user=%s key=%s... hits=%d", current_user.email, key[:12], cached.hit_count + 1)
        cached.hit_count += 1
        db.commit()
        result = {
            "answer": cached.answer,
            "has_table": cached.has_table,
            "table_data": json.loads(cached.table_data_json),
            "total_count": cached.total_count,
        }
        _log_query(db, current_user.id, current_user.email, payload.question, allowed_locations, result, from_cache=True)
        return AIQueryResponse(**result)

    # ── 呼叫 AI ───────────────────────────────────────────────────────────────
    logger.info("AI cache MISS user=%s locations=%s question=%r", current_user.email, allowed_locations, payload.question[:50])

    try:
        result = run_ai_query(
            question=payload.question,
            messages=[m.model_dump() for m in payload.messages],
            db=db,
            allowed_locations=allowed_locations,
        )
        if result.get("answer"):
            _set_cache(db, key, payload.question, allowed_locations, result)
        _log_query(db, current_user.id, current_user.email, payload.question, allowed_locations, result, from_cache=False)
        return AIQueryResponse(**result)
    except Exception as exc:
        logger.error("AI 查詢失敗 user=%s: %s", current_user.email, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="AI 查詢發生錯誤，請稍後再試")


@router.get("/history", response_model=list[AIHistoryItem])
def get_history(
    limit: int = Query(default=30, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    取得目前使用者的歷史問答記錄（最多 50 筆，最新優先）。
    """
    logs = (
        db.query(AIConversationLog)
        .filter(AIConversationLog.user_id == current_user.id)
        .order_by(AIConversationLog.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for log in logs:
        try:
            table_data = json.loads(log.table_data_json) if log.table_data_json else []
        except Exception:
            table_data = []
        result.append(AIHistoryItem(
            id=log.id,
            question=log.question,
            answer=log.answer,
            has_table=log.has_table,
            table_data=[RepairRow(**row) for row in table_data],
            total_count=log.total_count,
            from_cache=log.from_cache,
            created_at=log.created_at.strftime("%m/%d %H:%M"),
        ))
    return result
