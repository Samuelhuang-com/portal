"""
API 存取稽核 Middleware

攔截所有 /api/v1/ 請求，非同步寫入 api_access_logs 資料表。
設計原則：
  1. 寫入為 fire-and-forget（asyncio.create_task），不阻塞主請求
  2. 寫入失敗只 log，絕不影響業務回應
  3. APScheduler 的 sync job 直接呼叫 service，不走 HTTP，天然不進 middleware
  4. 排除清單：/api/v1/auth/（登入/登出由 audit_logs 處理）、/api/docs、靜態資源

模組名稱解析規則（優先序）：
  /api/v1/mall/b4f-inspection/… → b4f-inspection
  /api/v1/security/patrol/…    → security-patrol
  /api/v1/room-maintenance/…   → room-maintenance
  /api/v1/settings/…           → settings（不排除，記錄系統設定操作）
"""

import asyncio
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# ── 排除前綴（這些路徑不記錄）────────────────────────────────────────────────
_EXCLUDE_PREFIXES = (
    "/api/v1/auth/",        # login/logout 由 audit_logs 負責
    "/api/docs",            # Swagger UI
    "/api/redoc",
    "/api/openapi.json",
    "/assets/",             # 前端靜態資源
    "/favicon",
)

# ── 排除特定 GET 端點（高頻輪詢，記錄意義低）──────────────────────────────────
_EXCLUDE_EXACT = {
    ("GET", "/api/v1/auth/me"),          # 每次頁面重整都會打
}


def _extract_module(path: str) -> str:
    """
    從 request path 解析模組名稱。
    /api/v1/{prefix}/           → 取第一段（忽略 mall/security 等命名空間）
    /api/v1/mall/b4f-inspection → b4f-inspection
    /api/v1/security/patrol     → security-patrol
    """
    # 去掉前綴 /api/v1/
    stripped = path.removeprefix("/api/v1/").strip("/")
    if not stripped:
        return "root"

    parts = stripped.split("/")

    # 特殊命名空間：mall、security → 取第二段並串接
    if len(parts) >= 2 and parts[0] in ("mall", "security"):
        return f"{parts[1]}"

    # settings 子路徑保留 settings
    if parts[0] == "settings":
        return f"settings/{parts[1]}" if len(parts) >= 2 else "settings"

    return parts[0]


def _get_real_ip(request: Request) -> str | None:
    """取得真實 IP（支援 nginx X-Forwarded-For）。"""
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


def _decode_user_from_token(request: Request) -> tuple[str | None, str | None]:
    """
    從 Authorization Header 解出 user_id / user_email。
    失敗時回傳 (None, None)，不拋例外（middleware 不可影響主業務）。
    """
    try:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None, None
        token = auth[7:]

        # 直接用專案 security 模組解碼（避免重複邏輯）
        from app.core.security import decode_token
        payload = decode_token(token)
        if not payload:
            return None, None
        return payload.get("sub"), payload.get("email")
    except Exception:
        return None, None


def _write_log_sync(
    user_id: str | None,
    user_email: str | None,
    module: str,
    method: str,
    path: str,
    status_code: int,
    response_ms: int,
    ip_address: str | None,
) -> None:
    """實際落地寫入（同步 SQLAlchemy），只能在 thread pool 執行緒呼叫，不可直接在事件迴圈執行緒呼叫。"""
    from app.core.database import SessionLocal
    from app.models.api_access_log import ApiAccessLog
    from app.core.time import twnow

    db = SessionLocal()
    try:
        db.add(ApiAccessLog(
            user_id=user_id,
            user_email=user_email,
            module=module,
            method=method,
            path=path,
            status_code=status_code,
            response_ms=response_ms,
            ip_address=ip_address,
            created_at=twnow(),
        ))
        db.commit()
    finally:
        db.close()


async def _write_log(
    user_id: str | None,
    user_email: str | None,
    module: str,
    method: str,
    path: str,
    status_code: int,
    response_ms: int,
    ip_address: str | None,
) -> None:
    """
    非同步寫入 api_access_logs，失敗僅 log 不拋例外。

    2026-07-16 修正（重要）：
      這個函式雖然是用 asyncio.create_task() 以「不阻塞當前請求」的方式觸發，
      但它本身仍然是跑在同一條事件迴圈上的 coroutine。舊版寫法直接在這個
      async def 裡呼叫同步的 db.commit()——這是一個會阻塞的呼叫，一旦 SQLite
      當下被 sync_tool.py 的批次同步（或其他寫入）鎖住，db.commit() 會原地
      等到 busy_timeout（60 秒）才回來。因為沒有透過 run_in_threadpool 丟到
      背景執行緒，這 60 秒的等待會直接卡住整個事件迴圈，導致「當下所有」
      使用者的所有 API 請求全部一起卡住／轉圈圈，直到這次 commit 完成為止。
      這跟先前修過的 70 個 router 是同一類問題，只是這個檔案在 app/middleware/
      底下，不在 app/routers/ 掃描範圍內，先前的稽核沒有涵蓋到。

      這個 middleware 掛在幾乎所有 /api/v1/ 請求上，所以只要 sync_tool 正在
      大量寫入、造成 SQLite 短暫鎖定，整個網站就會在那段時間內全面卡住——
      這正是「sync_tool 同步全部時 Portal 網站轉圈圈、同步結束後就恢復正常」
      的根本原因。

      修法：把實際寫入（db.commit()）透過 run_in_threadpool 丟到背景執行緒，
      就算真的卡在等待 SQLite 鎖，也只會卡住這個背景 task 自己，不會影響
      事件迴圈、不會影響其他任何使用者的請求。
    """
    try:
        from fastapi.concurrency import run_in_threadpool

        await run_in_threadpool(
            _write_log_sync,
            user_id,
            user_email,
            module,
            method,
            path,
            status_code,
            response_ms,
            ip_address,
        )
    except Exception as exc:
        logger.debug("[AuditMiddleware] write failed: %s", exc)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    使用監控 Middleware。
    掛載方式（在 main.py CORS middleware 之後）：
        app.add_middleware(AuditMiddleware)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path   = request.url.path
        method = request.method

        # ── 排除不需記錄的路徑 ───────────────────────────────────────────────
        if any(path.startswith(p) for p in _EXCLUDE_PREFIXES):
            return await call_next(request)

        if (method, path) in _EXCLUDE_EXACT:
            return await call_next(request)

        # ── 只記錄 /api/v1/ 底下的端點 ──────────────────────────────────────
        if not path.startswith("/api/v1/"):
            return await call_next(request)

        # ── 解析請求資訊（在呼叫 call_next 之前，token 仍有效）──────────────
        user_id, user_email = _decode_user_from_token(request)
        module     = _extract_module(path)
        ip_address = _get_real_ip(request)

        # ── 呼叫實際 endpoint，計時 ──────────────────────────────────────────
        t0 = time.monotonic()
        response = await call_next(request)
        response_ms = int((time.monotonic() - t0) * 1000)

        # ── Fire-and-forget 寫入（不等待，不阻塞回應）───────────────────────
        asyncio.create_task(_write_log(
            user_id=user_id,
            user_email=user_email,
            module=module,
            method=method,
            path=path,
            status_code=response.status_code,
            response_ms=response_ms,
            ip_address=ip_address,
        ))

        return response
