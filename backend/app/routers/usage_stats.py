"""
使用監控統計 API
僅 system_admin 可存取。

端點：
  GET /api/v1/usage/summary         整體概覽（今日 DAU、總請求數、平均回應時間、錯誤率）
  GET /api/v1/usage/modules          各模組使用次數排行（可指定天數）
  GET /api/v1/usage/users            各用戶活躍度排行（請求數 + 最後活動時間）
  GET /api/v1/usage/response-times   各模組平均 / P95 回應時間
  GET /api/v1/usage/dau              每日活躍用戶數趨勢（DAU）
  GET /api/v1/usage/errors           各模組錯誤率（4xx/5xx）
  GET /api/v1/usage/timeline         依時間軸的請求量（可指定模組與天數）
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text, distinct
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.dependencies import is_system_admin
from app.models.api_access_log import ApiAccessLog
from app.core.time import twnow

router = APIRouter()


def _since(days: int) -> datetime:
    return twnow() - timedelta(days=days)


# ── 1. 整體概覽 ───────────────────────────────────────────────────────────────

@router.get("/summary")
def get_summary(
    days: int = Query(7, ge=1, le=90, description="統計天數"),
    db: Session = Depends(get_db),
    _: object = Depends(is_system_admin),
):
    """今日 DAU、期間總請求數、平均回應時間、錯誤率。"""
    since = _since(days)
    today_start = twnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_requests = (
        db.query(func.count(ApiAccessLog.id))
        .filter(ApiAccessLog.created_at >= since)
        .scalar() or 0
    )
    avg_ms = (
        db.query(func.avg(ApiAccessLog.response_ms))
        .filter(ApiAccessLog.created_at >= since)
        .scalar()
    )
    error_count = (
        db.query(func.count(ApiAccessLog.id))
        .filter(ApiAccessLog.created_at >= since, ApiAccessLog.status_code >= 400)
        .scalar() or 0
    )
    dau_today = (
        db.query(func.count(distinct(ApiAccessLog.user_id)))
        .filter(
            ApiAccessLog.created_at >= today_start,
            ApiAccessLog.user_id.isnot(None),
        )
        .scalar() or 0
    )
    unique_users_period = (
        db.query(func.count(distinct(ApiAccessLog.user_id)))
        .filter(ApiAccessLog.created_at >= since, ApiAccessLog.user_id.isnot(None))
        .scalar() or 0
    )

    return {
        "days": days,
        "total_requests": total_requests,
        "avg_response_ms": round(avg_ms, 1) if avg_ms else 0,
        "error_count": error_count,
        "error_rate_pct": round(error_count / total_requests * 100, 2) if total_requests else 0,
        "dau_today": dau_today,
        "unique_users_period": unique_users_period,
    }


# ── 2. 各模組使用次數排行 ─────────────────────────────────────────────────────

@router.get("/modules")
def get_modules(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    _: object = Depends(is_system_admin),
):
    """各模組請求次數排行（GET 為瀏覽，POST/PATCH/DELETE 為操作）。"""
    since = _since(days)
    rows = (
        db.query(
            ApiAccessLog.module,
            func.count(ApiAccessLog.id).label("total"),
            func.sum(
                func.cast(ApiAccessLog.method == "GET", db.bind.dialect.name == "sqlite" and "INTEGER" or "INT")
            ).label("reads"),
        )
        .filter(ApiAccessLog.created_at >= since)
        .group_by(ApiAccessLog.module)
        .order_by(func.count(ApiAccessLog.id).desc())
        .all()
    )

    # SQLite 不支援 CAST(bool)，改用 Python 計算
    since_dt = since
    all_rows = (
        db.query(ApiAccessLog.module, ApiAccessLog.method)
        .filter(ApiAccessLog.created_at >= since_dt)
        .all()
    )
    from collections import defaultdict
    module_stats: dict = defaultdict(lambda: {"total": 0, "reads": 0, "writes": 0})
    for module, method in all_rows:
        module_stats[module]["total"] += 1
        if method == "GET":
            module_stats[module]["reads"] += 1
        else:
            module_stats[module]["writes"] += 1

    result = [
        {
            "module":      m,
            "total":       s["total"],
            "reads":       s["reads"],
            "writes":      s["writes"],
        }
        for m, s in sorted(module_stats.items(), key=lambda x: -x[1]["total"])
    ]
    return {"days": days, "modules": result}


# ── 3. 用戶活躍度排行 ─────────────────────────────────────────────────────────

@router.get("/users")
def get_users(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(20, ge=5, le=100),
    db: Session = Depends(get_db),
    _: object = Depends(is_system_admin),
):
    """各用戶請求次數排行、最後活動時間、最常用模組。"""
    since = _since(days)
    rows = (
        db.query(
            ApiAccessLog.user_id,
            ApiAccessLog.user_email,
            func.count(ApiAccessLog.id).label("total"),
            func.max(ApiAccessLog.created_at).label("last_seen"),
        )
        .filter(ApiAccessLog.created_at >= since, ApiAccessLog.user_id.isnot(None))
        .group_by(ApiAccessLog.user_id, ApiAccessLog.user_email)
        .order_by(func.count(ApiAccessLog.id).desc())
        .limit(limit)
        .all()
    )

    result = []
    for user_id, user_email, total, last_seen in rows:
        # 最常用模組
        top_module_row = (
            db.query(ApiAccessLog.module, func.count(ApiAccessLog.id).label("cnt"))
            .filter(
                ApiAccessLog.created_at >= since,
                ApiAccessLog.user_id == user_id,
            )
            .group_by(ApiAccessLog.module)
            .order_by(func.count(ApiAccessLog.id).desc())
            .first()
        )
        result.append({
            "user_id":    user_id,
            "user_email": user_email or "—",
            "total":      total,
            "last_seen":  last_seen.isoformat() if last_seen else None,
            "top_module": top_module_row[0] if top_module_row else "—",
        })

    return {"days": days, "users": result}


# ── 4. 各模組回應時間 ─────────────────────────────────────────────────────────

@router.get("/response-times")
def get_response_times(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    _: object = Depends(is_system_admin),
):
    """各模組 平均 / P95 回應時間（毫秒）。"""
    since = _since(days)

    # 取得每個模組所有回應時間，Python 端計算 P95
    from collections import defaultdict
    import statistics

    raw = (
        db.query(ApiAccessLog.module, ApiAccessLog.response_ms)
        .filter(ApiAccessLog.created_at >= since)
        .all()
    )
    module_times: dict = defaultdict(list)
    for module, ms in raw:
        module_times[module].append(ms)

    result = []
    for module, times in sorted(module_times.items(), key=lambda x: -statistics.mean(x[1])):
        sorted_times = sorted(times)
        p95_idx = max(0, int(len(sorted_times) * 0.95) - 1)
        result.append({
            "module":   module,
            "count":    len(times),
            "avg_ms":   round(statistics.mean(times), 1),
            "p95_ms":   sorted_times[p95_idx],
            "max_ms":   max(times),
        })

    return {"days": days, "modules": result}


# ── 5. 每日活躍用戶數（DAU）趨勢 ─────────────────────────────────────────────

@router.get("/dau")
def get_dau(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    _: object = Depends(is_system_admin),
):
    """過去 N 天每日不重複用戶數（DAU）。"""
    since = _since(days)

    # SQLite: strftime('%Y-%m-%d', created_at)
    rows = db.execute(
        text("""
            SELECT
                strftime('%Y-%m-%d', created_at) AS day,
                COUNT(DISTINCT user_id)          AS dau
            FROM api_access_logs
            WHERE created_at >= :since
              AND user_id IS NOT NULL
            GROUP BY day
            ORDER BY day
        """),
        {"since": since.isoformat()},
    ).fetchall()

    return {
        "days": days,
        "data": [{"date": r[0], "dau": r[1]} for r in rows],
    }


# ── 6. 各模組錯誤率 ───────────────────────────────────────────────────────────

@router.get("/errors")
def get_errors(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    _: object = Depends(is_system_admin),
):
    """各模組 4xx / 5xx 錯誤率，依錯誤數降序排列。"""
    since = _since(days)

    raw = (
        db.query(ApiAccessLog.module, ApiAccessLog.status_code)
        .filter(ApiAccessLog.created_at >= since)
        .all()
    )

    from collections import defaultdict
    stats: dict = defaultdict(lambda: {"total": 0, "err4xx": 0, "err5xx": 0})
    for module, code in raw:
        stats[module]["total"] += 1
        if 400 <= code < 500:
            stats[module]["err4xx"] += 1
        elif code >= 500:
            stats[module]["err5xx"] += 1

    result = []
    for module, s in stats.items():
        total = s["total"]
        errors = s["err4xx"] + s["err5xx"]
        result.append({
            "module":        module,
            "total":         total,
            "err4xx":        s["err4xx"],
            "err5xx":        s["err5xx"],
            "error_rate_pct": round(errors / total * 100, 2) if total else 0,
        })

    result.sort(key=lambda x: -(x["err4xx"] + x["err5xx"]))
    return {"days": days, "modules": result}


# ── 7. 請求量時間軸 ───────────────────────────────────────────────────────────

@router.get("/timeline")
def get_timeline(
    days: int = Query(7, ge=1, le=30),
    module: Optional[str] = Query(None, description="指定模組，空白 = 全部"),
    db: Session = Depends(get_db),
    _: object = Depends(is_system_admin),
):
    """每小時請求量（可篩選模組）。"""
    since = _since(days)

    where_extra = "AND module = :module" if module else ""
    params: dict = {"since": since.isoformat()}
    if module:
        params["module"] = module

    rows = db.execute(
        text(f"""
            SELECT
                strftime('%Y-%m-%d %H:00', created_at) AS hour,
                COUNT(*)                                AS requests
            FROM api_access_logs
            WHERE created_at >= :since
              {where_extra}
            GROUP BY hour
            ORDER BY hour
        """),
        params,
    ).fetchall()

    return {
        "days":   days,
        "module": module or "all",
        "data":   [{"hour": r[0], "requests": r[1]} for r in rows],
    }
