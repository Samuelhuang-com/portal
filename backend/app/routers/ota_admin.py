"""
OTA 口碑分析 — 管理 API Router
Prefix: /api/v1/ota/admin

規格：`docs/SPEC_ota_reviews.md` §8.3

⚠️ 全部端點皆為同步 def。

【P2 起】
`POST /sync/run` 手動觸發爬蟲（`ota_scraper_service`）。
⚠️ **背景執行、立即回傳** —— 翻 20 頁可能要好幾分鐘，同步等待一定會 HTTP 逾時。
   前端靠輪詢 `/sync/status` 與 `/sync/logs` 看結果。

⚠️ CSV 匯入（`POST /api/v1/ota/reviews/import/upload`）**不會因為爬蟲上線而移除** ——
   OTA 隨時可能改版或跳 CAPTCHA，那是模組的救生艇（規格書 §6.6）。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.time import twnow
from app.dependencies import get_current_user, require_permission
from app.models.ota_review import (OtaPlatform, OtaSource, OtaSyncLog,
                                   OtaTopicCandidate, OtaTopicRule)
from app.models.user import User
from pydantic import BaseModel

from app.schemas.ota_review import (OtaSourceCreate, OtaSourceOut,
                                    OtaSourceUpdate, SyncLogOut,
                                    TopicCandidateAcceptIn, TopicCandidateOut,
                                    TopicRuleCreate, TopicRuleOut,
                                    TopicRuleUpdate)
from app.services import ota_platform_service as PLAT
from app.services import ota_source_service as SRC
from app.services.ota_normalize import PLATFORM_LABEL
from app.services.ota_sync_recovery import reap_stale_running

router = APIRouter(dependencies=[Depends(get_current_user)])
_VIEW = require_permission("ota_view")
_SOURCE_ADMIN = require_permission("ota_sources_admin")
_TOPIC_ADMIN = require_permission("ota_topic_admin")
# 與 sources_admin 分開：能設定來源不等於能隨時對 OTA 發請求（抓太頻繁會被封 IP）
_SYNC_RUN = require_permission("ota_sync_run")


def _bad(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


# ══════════════════════════════════════════════════════════════════════════
# 來源設定
# ══════════════════════════════════════════════════════════════════════════
@router.get("/sources", response_model=list[OtaSourceOut], summary="OTA 來源清單")
def list_sources(
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db),
    _: User = Depends(_VIEW),
):
    """`stored_count` 是實際落地筆數（不含跨站重複），與站方公布的
    `review_count_site` 比對即可看出翻頁有沒有抓完。"""
    return SRC.list_sources(db, enabled_only)


@router.get("/sources/platforms", summary="平台選項（含預設分制）")
def platforms(db: Session = Depends(get_db), _: User = Depends(_VIEW)):
    return SRC.platform_options(db)


# ══════════════════════════════════════════════════════════════════════════
# ⭐ 平台維護（2026-08-23 平台改為資料驅動）
# ══════════════════════════════════════════════════════════════════════════
# 使用者要加 Hotels.com、Trip.com、KKday…… 原本每加一個都要改程式重新部署。
# 但新增平台其實不需要寫任何邏輯 —— 有代碼／名稱／分制／網域就能建來源、
# 匯入 CSV、跑分析、進統計。需要寫程式的只有「自動擷取器」那一件事。
def _platform_out(row: OtaPlatform) -> dict:
    from app.services.ota_parser import PARSERS

    return {
        "id": row.id,
        "code": row.code,
        "label": row.label,
        "score_scale": row.score_scale,
        "domains": row.domains,
        "note": row.note,
        "is_enabled": row.is_enabled,
        "is_builtin": row.is_builtin,
        "sort_order": row.sort_order,
        # ⚠️ 現算不存 DB —— 程式碼才是唯一真相
        "has_parser": row.code in PARSERS,
    }


class PlatformIn(BaseModel):
    code: str = ""              # 新增時必填；修改時忽略（code 不可改）
    label: str
    score_scale: int = 10
    domains: str = ""
    note: str = ""
    is_enabled: bool = True


@router.get("/platforms", summary="平台清單（可維護）")
def list_platforms(db: Session = Depends(get_db), _: User = Depends(_VIEW)):
    return [_platform_out(r) for r in PLAT.list_platforms(db)]


@router.post("/platforms", summary="新增平台")
def create_platform(payload: PlatformIn, db: Session = Depends(get_db),
                    user: User = Depends(_SOURCE_ADMIN)):
    try:
        row = PLAT.create_platform(
            db, code=payload.code, label=payload.label,
            score_scale=payload.score_scale, domains=payload.domains,
            note=payload.note, created_by=str(user.id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _platform_out(row)


@router.put("/platforms/{platform_id}", summary="修改平台")
def update_platform(platform_id: int, payload: PlatformIn,
                    db: Session = Depends(get_db),
                    _: User = Depends(_SOURCE_ADMIN)):
    """⚠️ `code` 不可改 —— 它是既有評論的 platform 欄位值與統計分組鍵。"""
    try:
        row = PLAT.update_platform(
            db, platform_id, label=payload.label,
            score_scale=payload.score_scale, domains=payload.domains,
            note=payload.note, is_enabled=payload.is_enabled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _platform_out(row)


@router.delete("/platforms/{platform_id}", summary="刪除平台")
def delete_platform(platform_id: int, db: Session = Depends(get_db),
                    _: User = Depends(_SOURCE_ADMIN)):
    try:
        PLAT.delete_platform(db, platform_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/sources", response_model=OtaSourceOut, summary="新增 OTA 來源")
def create_source(
    payload: OtaSourceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(_SOURCE_ADMIN),
):
    try:
        return SRC.create_source(db, payload)
    except ValueError as exc:
        raise _bad(exc) from exc


@router.put("/sources/{source_id}", response_model=OtaSourceOut, summary="修改 OTA 來源")
def update_source(
    source_id: int,
    payload: OtaSourceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_SOURCE_ADMIN),
):
    try:
        return SRC.update_source(db, source_id, payload)
    except ValueError as exc:
        raise _bad(exc) from exc


@router.post("/sources/{source_id}/toggle", response_model=OtaSourceOut, summary="啟用／停用")
def toggle_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_SOURCE_ADMIN),
):
    try:
        return SRC.toggle_source(db, source_id)
    except ValueError as exc:
        raise _bad(exc) from exc


@router.delete("/sources/{source_id}", summary="刪除 OTA 來源")
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_SOURCE_ADMIN),
):
    """底下還有評論時會拒絕刪除（FK RESTRICT）。要停止同步請用「停用」。"""
    try:
        SRC.delete_source(db, source_id)
    except ValueError as exc:
        raise _bad(exc) from exc
    return {"ok": True}




# ══════════════════════════════════════════════════════════════════════════
# 手動觸發同步（P2）
# ══════════════════════════════════════════════════════════════════════════
class SyncRunIn(BaseModel):
    """省略 `source_ids` ＝ 所有啟用中的來源。"""

    source_ids: list[int] = []
    # 手動觸發預設忽略「每日至多一次」—— 使用者按了就是要跑
    force: bool = True


def _run_sync_background(source_ids: list[int], user_id: str) -> None:
    """
    背景執行緒裡的同步。

    ⚠️ **自己開 session，不能沿用請求的 db** ——
       請求結束後 `Depends(get_db)` 那個 session 就被關掉了，
       背景任務再用它會是 DetachedInstanceError。

    ⚠️ 自己加鎖：API 這條路徑沒有外層 `sync_lock`
       （只有 sync_tool.py 有）。不加會與排程搶著寫 portal.db。
    """
    from app.core.database import SessionLocal
    from app.core.sync_lock import sync_lock
    from app.services.ota_scraper_service import sync_sources

    db = SessionLocal()
    try:
        with sync_lock("OTA 評論擷取（手動）"):
            result = sync_sources(
                db, source_ids or None,
                trigger_type="manual", triggered_by=user_id,
                respect_daily_limit=False,
            )
        print(f"[Portal] OTA manual sync: {result['success']}/{result['attempted']} ok")
        for err in result.get("errors", []):
            print(f"[Portal] OTA manual sync error: {err}")
    except Exception as exc:            # noqa: BLE001 —— 背景任務不可把例外丟回請求
        print(f"[Portal] OTA manual sync failed: {exc}")
    finally:
        db.close()


@router.post("/sync/run", summary="手動觸發 OTA 評論擷取")
def run_sync(
    payload: SyncRunIn,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(_SYNC_RUN),
):
    """
    ⚠️ **立即回傳，實際擷取在背景跑**。翻 20 頁可能要好幾分鐘，
       同步等待一定會 HTTP 逾時。前端請輪詢 `/sync/status` 與 `/sync/logs`。
    """
    # ⚠️ 先回收孤兒 running 再判斷（2026-08-24）。
    #    在這之前，一列沒收乾淨的 running 會讓這支端點**永遠**回 409 ——
    #    畫面上只顯示「擷取中…」，整個模組的同步從此按不下去。
    if reap_stale_running(db):
        db.commit()

    running = db.execute(
        select(OtaSyncLog).where(OtaSyncLog.status == "running")
    ).scalars().all()
    if running:
        raise HTTPException(
            status_code=409,
            detail="目前已有同步在執行中，請等它跑完再觸發（可到下方同步紀錄查看進度）。"
                   "若確定它其實已經中斷，請按「強制解除」。",
        )

    if payload.source_ids:
        found = db.execute(
            select(OtaSource.id).where(OtaSource.id.in_(payload.source_ids))
        ).scalars().all()
        missing = set(payload.source_ids) - set(found)
        if missing:
            raise HTTPException(status_code=404, detail=f"找不到來源 id：{sorted(missing)}")
    else:
        enabled = db.execute(
            select(OtaSource).where(OtaSource.is_enabled.is_(True))
        ).scalars().all()
        if not enabled:
            raise HTTPException(status_code=400, detail="目前沒有啟用中的 OTA 來源")

    background.add_task(_run_sync_background, list(payload.source_ids), str(user.id))
    return {
        "started": True,
        "message": "已開始擷取，請稍候重新整理查看結果（翻頁較多時可能需要數分鐘）",
    }


# ══════════════════════════════════════════════════════════════════════════
# 同步紀錄
# ══════════════════════════════════════════════════════════════════════════
def _fmt(value) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


@router.get("/sync/logs", response_model=list[SyncLogOut], summary="同步／匯入歷程")
def sync_logs(
    source_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(_VIEW),
):
    """
    ⚠️ `warnings` 與 `error_message` 語意不同：
       前者是「某幾筆略過／解析不了」，後者是「整個來源失敗」。
       畫面上不要把 warnings 畫成紅色，否則久了沒人看
       （CLAUDE.md §9 規則 8 的教訓）。
    """
    stmt = select(OtaSyncLog, OtaSource).join(OtaSource, OtaSource.id == OtaSyncLog.source_id)
    if source_id:
        stmt = stmt.where(OtaSyncLog.source_id == source_id)
    stmt = stmt.order_by(OtaSyncLog.started_at.desc(), OtaSyncLog.id.desc()).limit(limit)

    out = []
    for log, source in db.execute(stmt).all():
        try:
            warnings = json.loads(log.warnings_json) if log.warnings_json else []
        except (json.JSONDecodeError, TypeError):
            warnings = []
        out.append(SyncLogOut(
            id=log.id,
            source_id=log.source_id,
            hotel_name=source.hotel_name,
            platform_label=PLATFORM_LABEL.get(source.platform, source.platform),
            trigger_type=log.trigger_type,
            started_at=_fmt(log.started_at),
            completed_at=_fmt(log.completed_at),
            status=log.status,
            pages_fetched=log.pages_fetched,
            found_count=log.found_count,
            inserted_count=log.inserted_count,
            updated_count=log.updated_count,
            skipped_count=log.skipped_count,
            warnings=warnings,
            error_message=log.error_message or "",
            duration_ms=log.duration_ms,
        ))
    return out


@router.get("/sync/status", summary="目前同步狀態")
def sync_status(db: Session = Depends(get_db), _: User = Depends(_VIEW)):
    # ⚠️ 讀狀態之前先回收孤兒 running（2026-08-24）。
    #    這支是前端 `syncing` 的唯一來源 —— 不先收，畫面會一直「擷取中…」。
    reaped = reap_stale_running(db)
    if reaped:
        db.commit()

    running = db.execute(
        select(OtaSyncLog).where(OtaSyncLog.status == "running")
    ).scalars().all()
    from app.core.config import settings
    from app.services.ota_parser import PARSERS

    return {
        "is_running": bool(running),
        "running_source_ids": [log.source_id for log in running],
        # 讓畫面能講出「剛剛幫你收掉了幾列」，而不是狀態默默變了
        "reaped": [{"log_id": r.log_id, "source_id": r.source_id, "reason": r.reason}
                   for r in reaped],
        "scraper_available": True,
        # 前端用來提示「哪些平台還沒有擷取器」（P2 只有 Booking）
        "supported_platforms": sorted(PARSERS.keys()),
        "browser_mode": settings.OTA_BROWSER_MODE,
        "note": (
            "Booking 已支援自動擷取；Expedia／Tripadvisor 為 P3，"
            "目前請用 CSV 匯入。"
        ),
    }


@router.post("/sync/force-unlock", summary="強制解除卡住的「擷取中」")
def force_unlock(db: Session = Depends(get_db), _: User = Depends(_SYNC_RUN)):
    """
    最後一道保險：把所有 `running` 直接收成 `failed`。

    ⚠️ **不做任何存活判定** —— 呼叫這支就是人已經確定它其實中斷了。
       `/sync/status` 與 `/sync/run` 已經會自動回收「pid 不在了」和
       「超過 90 分鐘」兩種，會走到這裡的是那兩層都判不出來的情況
       （例如同步跑在另一台機器、或還沒超過門檻但人知道它死了）。

    ⚠️ 若同步其實**還在跑**，按下去會讓那個行程之後的 `finish_sync_log()`
       把 status 再寫回 success／failed —— 不會壞資料，但畫面會閃一下。
       真正的風險是有人接著按「立即同步全部」，兩個行程同時擷取同一批來源；
       `sync_lock` 擋得住並行寫入，只是第二個會等到第一個結束。
    """
    reaped = reap_stale_running(db, force=True)
    db.commit()
    return {
        "reaped": len(reaped),
        "details": [{"log_id": r.log_id, "source_id": r.source_id} for r in reaped],
        "message": (f"已解除 {len(reaped)} 列卡住的紀錄"
                    if reaped else "目前沒有卡住的紀錄"),
    }


class AnalyzeRunIn(BaseModel):
    """`rerun_all=True` 會重跑全部（改了字典之後要用）。"""

    rerun_all: bool = False
    limit: int = 2000


def _run_analyze_background(rerun_all: bool, limit: int) -> None:
    """
    背景執行緒裡的分析。

    ⚠️ 自己開 session（請求結束後 `Depends(get_db)` 那個已被關閉）。
    ⚠️ 自己加鎖 —— API 這條路徑沒有外層 `sync_lock`。
    """
    from app.core.database import SessionLocal
    from app.core.sync_lock import sync_lock
    from app.services.ota_analysis_service import analyze_pending

    db = SessionLocal()
    try:
        with sync_lock("OTA 情緒分析（手動）"):
            result = analyze_pending(db, limit=limit, rerun_all=rerun_all)
        print(f"[Portal] OTA analyze: rule={result['rule_count']} "
              f"ai={result['ai_count']} cache={result['cache_hit']} "
              f"alert={result['alert_count']}")
        for w in result.get("warnings", []):
            print(f"[Portal] OTA analyze warning: {w}")
    except Exception as exc:            # noqa: BLE001
        print(f"[Portal] OTA analyze failed: {exc}")
    finally:
        db.close()


@router.post("/analyze/run", summary="手動觸發情緒與主題分析")
def run_analyze(
    payload: AnalyzeRunIn,
    background: BackgroundTasks,
    _: User = Depends(_TOPIC_ADMIN),
):
    """
    ⚠️ **背景執行、立即回傳**。`rerun_all` 重跑上千則時可能要幾分鐘
       （尤其有 AI 補判時），同步等待會 HTTP 逾時。

    ⚠️ 重跑**不會**清掉人工填的警示處理狀態
       （`alert_status` / `alert_note`），只重算 `is_alert`。
    """
    background.add_task(_run_analyze_background, payload.rerun_all, payload.limit)
    return {
        "started": True,
        "message": ("已開始重新分析全部評論，請稍候重新整理"
                    if payload.rerun_all else "已開始分析尚未處理的評論"),
    }


# ══════════════════════════════════════════════════════════════════════════
# 主題關鍵字字典
# ══════════════════════════════════════════════════════════════════════════
def _rule_out(rule: OtaTopicRule) -> TopicRuleOut:
    return TopicRuleOut(
        id=rule.id, topic=rule.topic, keyword=rule.keyword,
        polarity=rule.polarity, weight=rule.weight,
        is_enabled=rule.is_enabled, is_builtin=rule.is_builtin,
    )


@router.get("/topic-rules", response_model=list[TopicRuleOut], summary="主題字典清單")
def list_topic_rules(
    topic: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(_VIEW),
):
    stmt = select(OtaTopicRule)
    if topic:
        stmt = stmt.where(OtaTopicRule.topic == topic)
    stmt = stmt.order_by(OtaTopicRule.topic, OtaTopicRule.polarity, OtaTopicRule.keyword)
    return [_rule_out(r) for r in db.execute(stmt).scalars().all()]


@router.post("/topic-rules", response_model=TopicRuleOut, summary="新增關鍵詞")
def create_topic_rule(
    payload: TopicRuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_TOPIC_ADMIN),
):
    rule = OtaTopicRule(
        topic=payload.topic.strip(),
        keyword=payload.keyword.strip(),
        polarity=payload.polarity,
        weight=payload.weight,
        is_enabled=payload.is_enabled,
        is_builtin=False,
        created_by=str(user.id),
    )
    db.add(rule)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"「{payload.topic} / {payload.keyword}」已存在（同極性）",
        ) from exc
    db.refresh(rule)
    return _rule_out(rule)


@router.put("/topic-rules/{rule_id}", response_model=TopicRuleOut, summary="修改關鍵詞")
def update_topic_rule(
    rule_id: int,
    payload: TopicRuleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_TOPIC_ADMIN),
):
    """
    ⚠️ topic / keyword / polarity 是唯一鍵，改了等於換一筆，
       所以本端點只允許改 `weight` 與 `is_enabled`。
       要換詞請刪除後重建（內建詞不可刪，只能停用）。
    """
    rule = db.get(OtaTopicRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="找不到這筆關鍵詞")

    if payload.weight is not None:
        rule.weight = payload.weight
    if payload.is_enabled is not None:
        rule.is_enabled = payload.is_enabled
    if payload.polarity is not None and not rule.is_builtin:
        rule.polarity = payload.polarity

    rule.updated_at = twnow()
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="與既有關鍵詞重複") from exc
    db.refresh(rule)
    return _rule_out(rule)


@router.delete("/topic-rules/{rule_id}", summary="刪除關鍵詞")
def delete_topic_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_TOPIC_ADMIN),
):
    """
    ⚠️ 內建詞（`is_builtin=True`）**拒絕刪除**，只能停用。
       刪掉之後沒有還原機制，停用是可逆的。
    """
    rule = db.get(OtaTopicRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="找不到這筆關鍵詞")
    if rule.is_builtin:
        raise HTTPException(
            status_code=400,
            detail="內建關鍵詞不可刪除，請改用「停用」（停用是可逆的，刪除不是）",
        )
    db.delete(rule)
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════════
# ⭐ AI 發現的字典外主題候選（2026-08-23）
# ══════════════════════════════════════════════════════════════════════════
# 閉環：AI 發現 → 候選累積 → 管理員確認 → 進字典 → 規則層免費抓到
#       （之後同樣的評論不必再送 AI）
def _candidate_out(row: OtaTopicCandidate) -> TopicCandidateOut:
    def _json_list(raw, default=None):
        try:
            value = json.loads(raw) if raw else []
        except (TypeError, ValueError):
            return default or []
        return value if isinstance(value, list) else (default or [])

    return TopicCandidateOut(
        id=row.id,
        name=row.name,
        description=row.description or "",
        keywords=[str(k) for k in _json_list(row.keywords_json)],
        hit_count=row.hit_count,
        neg_count=row.neg_count,
        sample_review_ids=[int(i) for i in _json_list(row.sample_review_ids)
                           if isinstance(i, int)],
        status=row.status,
        first_seen_at=_fmt(row.first_seen_at),
        last_seen_at=_fmt(row.last_seen_at),
    )


@router.get("/topic-candidates", response_model=list[TopicCandidateOut],
            summary="AI 發現的字典外主題候選")
def list_topic_candidates(
    status: str = Query("pending", pattern="^(pending|accepted|rejected|all)$"),
    db: Session = Depends(get_db),
    _: User = Depends(_VIEW),
):
    """出現次數多的排前面 —— 那些是最值得先收進字典的。"""
    stmt = select(OtaTopicCandidate)
    if status != "all":
        stmt = stmt.where(OtaTopicCandidate.status == status)
    rows = db.execute(
        stmt.order_by(OtaTopicCandidate.hit_count.desc(), OtaTopicCandidate.id)
    ).scalars().all()
    return [_candidate_out(r) for r in rows]


@router.post("/topic-candidates/{candidate_id}/accept",
             summary="採納候選主題，寫進主題字典")
def accept_topic_candidate(
    candidate_id: int,
    payload: TopicCandidateAcceptIn,
    db: Session = Depends(get_db),
    user: User = Depends(_TOPIC_ADMIN),
):
    """
    把候選變成正式的字典關鍵詞。

    ⚠️ 建立的規則 `is_builtin=False` —— 它們是這個案場長出來的，不是內建詞，
       管理員之後應該可以自由刪除。標成 builtin 會讓它們變得刪不掉。

    ⚠️ 已經存在的 (主題, 關鍵詞, 極性) 直接略過**不報錯** ——
       管理員很可能已經手動加過其中一兩個詞，為此讓整個採納失敗很惱人。
    """
    candidate = db.get(OtaTopicCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="找不到這個候選主題")
    if candidate.status == "accepted":
        raise HTTPException(status_code=400, detail="這個候選已經採納過了")

    existing = {
        (t, k, p) for t, k, p in db.execute(
            select(OtaTopicRule.topic, OtaTopicRule.keyword, OtaTopicRule.polarity)
        ).all()
    }
    added = 0
    for keyword in payload.keywords:
        keyword = keyword.strip()
        if not keyword or (payload.topic, keyword, payload.polarity) in existing:
            continue
        db.add(OtaTopicRule(topic=payload.topic, keyword=keyword,
                            polarity=payload.polarity, is_builtin=False,
                            created_by=str(user.id)))
        added += 1

    candidate.status = "accepted"
    candidate.reviewed_by = str(user.id)
    candidate.reviewed_at = twnow()
    db.commit()
    return {"ok": True, "added": added, "topic": payload.topic}


@router.post("/topic-candidates/{candidate_id}/reject", summary="否決候選主題")
def reject_topic_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_TOPIC_ADMIN),
):
    """
    ⚠️ 否決之後**不會再跳出來**（`record_topic_candidates` 不復活 rejected）。
       這是刻意的 —— 否則管理員每次分析完都要重看一次同樣不想要的東西，
       那個按鈕就等於沒有用。要反悔的話把狀態改回 pending。
    """
    candidate = db.get(OtaTopicCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="找不到這個候選主題")
    candidate.status = "rejected"
    candidate.reviewed_by = str(user.id)
    candidate.reviewed_at = twnow()
    db.commit()
    return {"ok": True}
