"""
JWT token utilities
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def _jwt_secret() -> str:
    """
    JWT signing key：優先使用 JWT_SECRET_KEY（原有程式的變數名稱），
    若未設定則 fallback 到 SECRET_KEY。
    """
    return settings.JWT_SECRET_KEY or settings.SECRET_KEY


def create_access_token(
    subject: Any,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )
    payload: dict = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, _jwt_secret(), algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """驗證並解碼 JWT token，回傳 payload dict 或 None。"""
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


# 相容原有程式的別名：auth.py / dependencies.py 使用 decode_token 這個名稱
decode_token = verify_token


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
