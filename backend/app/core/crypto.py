import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings


def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        # 開發模式：從 JWT_SECRET_KEY 自動產生 Fernet key
        raw = hashlib.sha256(settings.JWT_SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(raw).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
