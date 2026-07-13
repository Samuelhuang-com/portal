"""
週期採購 SQLAlchemy 獨立 engine + session factory

2026-07-10 與 Samuel 確認之架構決策（見
docs/週期採購_Portal規劃評估_v1.0.md 第九節後續討論）：
  - 週期採購使用獨立 SQLite 檔案（cycle-purchase.db），不與 portal.db 共用，
    避免 portal.db 檔案持續變大。
  - 週期採購與 portal.db 之間一律採「應用層軟關聯」：只存純數值 ID
    （如 created_by_user_id），不建立跨檔案的資料庫層外鍵，不做 SQLite
    ATTACH DATABASE。需要顯示名稱時由後端另外查 portal.db（get_db）再組合。
  - 供應商主檔、部門／成本中心／會計科目主檔，週期採購全部自建獨立主檔
    （存在本檔案 cycle-purchase.db），不與 Contract 模組的 Vendors、
    Budget 模組的 budget_system_v1.sqlite、reference_data.py 的
    Company/RefDepartment 關聯（三者目前彼此也不相通，見規劃文件附錄）。
  - 僅使用者／角色／權限（portal.db）沿用既有 get_db() 依賴。

寫法比照 app/core/database.py（同步 SQLAlchemy engine + WAL），
差別只在於另開一個 engine／Base／SessionLocal，指向不同的 SQLite 檔案，
且採用獨立的 DeclarativeBase（CyclePurchaseBase），與主要的 Base 分開管理
metadata，互不影響。
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

from app.core.config import settings

# aiosqlite URL → 換回同步 sqlite driver（比照 database.py 的處理方式）
_cp_db_url = settings.CYCLE_PURCHASE_DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")

cycle_purchase_engine = create_engine(
    _cp_db_url,
    echo=settings.DEBUG,
    connect_args=(
        {
            "check_same_thread": False,
            # OneDrive/網路磁碟鎖定時等待最多 60 秒，與 database.py 對齊
            "timeout": 60,
        }
        if "sqlite" in _cp_db_url
        else {}
    ),
    pool_pre_ping=True,
)

if "sqlite" in _cp_db_url:
    @event.listens_for(cycle_purchase_engine, "connect")
    def _set_cycle_purchase_sqlite_pragmas(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=60000")
        # cycle-purchase.db 內部（同一檔案）的資料表之間可以正常使用 FK
        # （例如 cycle_purchase_item_mappings → cycle_purchase_items），
        # 只有「跨檔案」到 portal.db 的關聯才刻意不做 FK。
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

CyclePurchaseSessionLocal = sessionmaker(
    bind=cycle_purchase_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class CyclePurchaseBase(DeclarativeBase):
    """週期採購獨立 declarative base，metadata 與主要 Base 分開管理。"""
    pass


def get_cycle_purchase_db():
    """FastAPI Depends — 週期採購獨立資料庫 Session（cycle-purchase.db）。
    用法與 app.core.database.get_db() 完全對稱：
        db: Session = Depends(get_cycle_purchase_db)
    """
    db: Session = CyclePurchaseSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
