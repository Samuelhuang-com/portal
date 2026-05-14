"""
SQLAlchemy 同步 engine + session factory
（所有原有 router 使用 db.query() 同步 API，故維持同步模式）
"""
from sqlalchemy import create_engine, event
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
            # OneDrive/網路磁碟鎖定時等待最多 60 秒
            # （purchase sync 批次間有 3s 休眠，需要足夠的等待時間）
            "timeout": 60,
        }
        if "sqlite" in _db_url
        else {}
    ),
    pool_pre_ping=True,
)

# 啟用 WAL（Write-Ahead Logging）模式：
#   - 讀寫互不阻塞（讀不擋寫、寫不擋讀）
#   - 大幅降低 "database is locked" 機率
#   - synchronous=NORMAL：WAL 下安全且速度更快
if "sqlite" in _db_url:
    @event.listens_for(engine, "connect")
    def _set_sqlite_wal(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        # 多個 scheduler job 同時寫入時，等待最多 30 秒再回報 locked
        # busy_timeout 與 connect_args timeout 對齊（都是 60 秒）
        # 避免長批次 sync（purchase 約 67s）觸發不必要的 locked 錯誤
        cursor.execute("PRAGMA busy_timeout=60000")
        # WAL checkpoint 每 2000 頁才自動觸發（預設 1000），
        # 減少 sync_tool 批次寫入中途被 checkpoint 阻塞的機率
        cursor.execute("PRAGMA wal_autocheckpoint=2000")
        cursor.close()

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
