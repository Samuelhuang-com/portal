"""
Alembic environment — **主庫 portal.db**（`app.core.database.Base`）

⚠️ 週期採購（`cycle-purchase.db`）是**另一個獨立的 Alembic 目錄** `alembic_cp/`。
   兩個庫各自有自己的 `alembic_version` 表，互不干擾。
   （2026-08-28 Phase 0 決定採「兩套獨立目錄」，見 docs/CHANGELOG.md [1.96.34]）

用法：
    cd backend
    alembic revision --autogenerate -m "說明"     # 產生新版本
    alembic upgrade head                          # 套用
    alembic current                               # 看目前版本
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import importlib
import os
import pkgutil
import sys

# 添加 backend 目錄到 Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings
from app.core.database import Base


def _import_all_models() -> None:
    """把 `app/models` 底下所有模組 import 一遍。

    ⚠️⚠️ **這一步不能省。**
       `from app.core.database import Base` 只會拿到一個**空的** metadata
       （實測：0 張表；import 全部 models 後才有 163 張）。
       少了這步，`--autogenerate` 會認為「Model 端沒有任何表」，
       產出一份把 163 張表**全部 DROP** 的 migration —— 而且不會有任何警告。

    ⚠️ 只 import `app.models`（它的 `__init__.py` 只匯出 12 個 model）也不夠，
       必須逐一走訪整個 package。
    """
    import app.models as pkg
    failed: list[str] = []
    for m in pkgutil.iter_modules(pkg.__path__):
        try:
            importlib.import_module(f"app.models.{m.name}")
        except Exception as exc:                                   # pragma: no cover
            failed.append(f"{m.name}: {type(exc).__name__}: {exc}")
    if failed:
        # 少一個模組就少一批表，autogenerate 會把它們判成「該刪掉」——必須擋下來
        raise RuntimeError(
            "以下 model 模組 import 失敗，autogenerate 會產生錯誤的 DROP，已中止：\n  "
            + "\n  ".join(failed)
        )


_import_all_models()

# this is the Alembic Config object, which provides
# the values of the [alembic] section of the .ini
# file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("sqlalchemy.url")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # 從 Portal settings 獲取 DATABASE_URL，並轉換為同步模式
    sqlalchemy_url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")

    context.configure(
        url=sqlalchemy_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        # ⚠️ SQLite 不支援 ALTER COLUMN／DROP COLUMN，batch mode 會自動改用
        #    「建新表→搬資料→換名」。之後遷到 PostgreSQL 時這個選項無害。
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # 從 Portal settings 獲取 DATABASE_URL，並轉換為同步模式
    sqlalchemy_url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")

    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = sqlalchemy_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.StaticPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,      # 見 run_migrations_offline() 的說明
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
