from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from threading import Lock
from collections import defaultdict
from app.core.time import twnow
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, decode_token
from app.dependencies import get_current_user, get_user_permissions
from app.models.user import User
from app.models.user_role import UserRole
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.audit_log import AuditLog
from app.schemas.auth import LoginRequest, TokenResponse, UserInfo

router = APIRouter()

# ── 登入 Rate Limiter（In-Memory，不需要額外套件）──────────────────────────────
# 設計：IP + 帳號識別碼 各自獨立計數，兩者任一超限都拒絕。
# 這樣即使攻擊者換 IP，帳號維度仍然被保護；即使換帳號，IP 維度仍然被保護。

_MAX_FAILURES   = 5          # 連續失敗幾次後鎖定
_LOCKOUT_SECS   = 300        # 鎖定秒數（5 分鐘）
_WINDOW_SECS    = 600        # 失敗計數時間窗口（10 分鐘）

_lock           = Lock()
# { key: { "count": int, "first_at": datetime, "locked_until": datetime | None } }
_attempts: dict = defaultdict(lambda: {"count": 0, "first_at": None, "locked_until": None})


def _rate_limit_key_ip(request: Request) -> str:
    """從 Request 取得真實 IP（支援 nginx / 反向代理 X-Forwarded-For）。"""
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return f"ip:{xff.split(',')[0].strip()}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


def _check_and_record_failure(key: str) -> None:
    """
    記錄一次失敗。若已超過上限，raise 429；否則更新計數。
    同一把鎖保護讀寫，避免競態條件。
    """
    with _lock:
        now  = datetime.now(timezone.utc)
        rec  = _attempts[key]

        # 已在鎖定期 → 拒絕
        if rec["locked_until"] and now < rec["locked_until"]:
            remaining = int((rec["locked_until"] - now).total_seconds())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"登入失敗次數過多，請於 {remaining} 秒後再試",
            )

        # 時間窗口外 → 重置計數
        if rec["first_at"] is None or (now - rec["first_at"]).total_seconds() > _WINDOW_SECS:
            rec["count"]       = 1
            rec["first_at"]    = now
            rec["locked_until"] = None
            return

        rec["count"] += 1

        # 達到上限 → 鎖定
        if rec["count"] >= _MAX_FAILURES:
            rec["locked_until"] = now + timedelta(seconds=_LOCKOUT_SECS)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"連續登入失敗 {_MAX_FAILURES} 次，帳號已鎖定 {_LOCKOUT_SECS // 60} 分鐘",
            )


def _reset_failures(key: str) -> None:
    """登入成功後清除失敗紀錄。"""
    with _lock:
        _attempts.pop(key, None)


def _check_rate_limit(request: Request, identifier: str) -> tuple[str, str]:
    """
    同時檢查 IP 維度與帳號維度是否超限。
    回傳 (ip_key, account_key) 供登入成功後清除用。
    """
    ip_key      = _rate_limit_key_ip(request)
    account_key = f"account:{identifier}"
    _check_and_record_failure(ip_key)
    _check_and_record_failure(account_key)
    return ip_key, account_key


# ── 輔助函式 ──────────────────────────────────────────────────────────────────

def _get_user_roles(user_id: str, db: Session) -> list[str]:
    rows = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .all()
    )
    return [r[0] for r in rows]


def _build_user_info(user: User, db: Session) -> UserInfo:
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    return UserInfo(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=user.tenant_id,
        tenant_name=tenant.name if tenant else "",
        roles=_get_user_roles(user.id, db),
        permissions=get_user_permissions(user.id, db),
        is_active=user.is_active,
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    identifier = data.identifier.lower().strip()
    if "@" not in identifier:
        identifier = f"{identifier}@portal.local"

    # ── Rate limiting：IP + 帳號雙維度（失敗才扣點，成功前先檢查）────────────
    ip_key, account_key = _check_rate_limit(request, identifier)

    user = (
        db.query(User).filter(User.email == identifier, User.is_active == True).first()
    )
    if not user or not verify_password(data.password, user.hashed_password):
        # 驗證失敗：不需要再呼叫 _check_and_record_failure（已在 _check_rate_limit 記錄過）
        # 但這裡需要「再記一次」—— _check_rate_limit 是事前檢查，實際失敗要再加計
        _check_and_record_failure(ip_key)
        _check_and_record_failure(account_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="帳號或密碼錯誤"
        )

    # 登入成功 → 清除失敗計數
    _reset_failures(ip_key)
    _reset_failures(account_key)

    roles = _get_user_roles(user.id, db)
    token = create_access_token(
        subject=user.id,
        extra_claims={"email": user.email, "roles": roles},
    )

    user.last_login = twnow()
    db.add(
        AuditLog(
            user_id=user.id,
            tenant_id=user.tenant_id,
            action="login",
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()

    return TokenResponse(access_token=token, user=_build_user_info(user, db))


@router.get("/me", response_model=UserInfo)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _build_user_info(current_user, db)


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    db.add(
        AuditLog(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            action="logout",
        )
    )
    db.commit()
    return {"message": "已登出"}
