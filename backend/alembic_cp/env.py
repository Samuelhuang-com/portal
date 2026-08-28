"""
Alembic environment — **週期採購庫 cycle-purchase.db**（`CyclePurchaseBase`）

⚠️ 主庫 `portal.db` 用的是另一個目錄 `alembic/`。
   兩個庫各自有自己的 `alembic_version` 表，互不干擾。
   （2026-08-28 Phase 0 決定採「兩套獨立目錄」，見 docs/CHANGELOG.md [1.96.34]）

用法（注意要指定 -c）：
    cd backend
    alembic -c alembic_cp.ini revision --autogenerate -m "說明"
    alembic -c alembic_cp.ini upgrade head
    alembic -c alembic_cp.ini current

⚠️ 這個目錄的存活期是暫時的：Phase 3 把兩個庫併進同一個 PostgreSQL
   （各自一個 schema）之後，`alembic_cp/` 就可以退役、版本鏈併回 `alembic/`。
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import importlib
import os
import pkgutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings
from app.core.cycle_purchase_database import CyclePurchaseBase


def _import_cycle_purchase_models() -> None:
    """import 所有掛在 `CyclePurchaseBase` 底下的 model。

    ⚠️⚠️ 這一步不能省，理由與 `alembic/env.py` 相同：
       只 import Base 會拿到空的 metadata，`--autogenerate` 會產出
       把所有表 DROP 掉的 migration，而且不會有任何警告。

    ⚠️ 這裡走訪整個 `app.models` package（而不是只挑 `cycle_purchase_*.py`）：
       模組命名不保證永遠帶那個前綴，漏掉一個就是漏掉一批表。
       掛在主庫 `Base` 的 model 被 import 進來也沒關係 ——
       `target_metadata` 只認 `CyclePurchaseBase.metadata`。
    """
    import app.models as pkg
    failed: list[str] = []
    for m in pkgutil.iter_modules(pkg.__path__):
        try:
            importlib.import_module(f"app.models.{m.name}")
        except Exception as exc:                                   # pragma: no cover
            failed.append(f"{m.name}: {type(exc).__name__}: {exc}")
    if failed:
        raise RuntimeError(
            "以下 model 模組 import 失敗，autogenerate 會產生錯誤的 DROP，已中止：\n  "
            + "\n  ".join(failed)
        )


_import_cycle_purchase_models()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = CyclePurchaseBase.metadata


def _url() -> str:
    return settings.CYCLE_PURCHASE_DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        # SQLite 不支援 ALTER COLUMN／DROP COLUMN，batch mode 會改用
        # 「建新表→搬資料→換名」。遷到 PostgreSQL 後這個選項無害。
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = _url()

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
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
