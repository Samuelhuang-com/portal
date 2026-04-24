"""
SQLAlchemy 同步 engine + session factory
（所有原有 router 使用 db.query() 同步 API，故維持同步模式）
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

from app.core.config import settings


# aiosqlite URL → 換回同步 sqlite driver
_db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")

engine = create_engine(
    _db_url,
    echo=settings.DEBUG,
    connect_args=(
        {
            "check_same_thread": False,
            # OneDrive/網路磁碟鎖定時等待最多 30 秒（預設 5 秒太短）
            "timeout": 30,
        }
        if "sqlite" in _db_url
        else {}
    ),
    # SQLite 連線池：固定單一連線，避免多執行緒競爭
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI Depends — 同步 Session，每個 request 一個 session。"""
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
