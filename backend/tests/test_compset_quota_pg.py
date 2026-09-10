"""
競品分析 — 配額併發測試（**需要真的 PostgreSQL**）

⭐ 為什麼要另外開一支
────────────────────────────────────────────────────────────────────────────
`tests/test_compset_quota.py` 的 21 項全部跑在 SQLite 上，而 **SQLite 是整庫
序列化的** —— 兩個「同時」的預留其實是一前一後。也就是說：即使把 `reserve()`
寫成最容易寫錯的「先讀 quota_used、算一算、再寫回去」，那 21 項**照樣全過**。

2026-09-09 實測（把 `reserve()` 換成先讀再寫的版本）：

| 環境 | 結果 |
|---|---|
| SQLite（既有 21 項） | ✅ **全過** —— 完全抓不到 |
| PostgreSQL（本檔） | ❌ 20 條全部成功（配額 100、卻發出 200 次）；另一項帳面記 1、實際發出 70 |

也就是說，少了這支測試，一個 **2 倍成本超發**的 bug 可以毫無阻礙地上線，
而且帳面上完全看不出來（`quota_used` 是小的那個數字）。
本模組是 Portal 唯一會產生外部費用的模組，這個風險不能只靠 code review。

⚠️ 這支不是「多測一次」，它測的是**另一件事**：`reserve()` 是不是真的
   單一原子 UPDATE。功能正確性由 `test_compset_quota.py` 負責。

執行
────────────────────────────────────────────────────────────────────────────
沒設定 `COMPSET_PG_URL` 時整支 skip（開發機不需要裝 PostgreSQL）：

    # 本機起一個臨時 PG
    initdb -D /tmp/pgdata -U portal --auth=trust
    pg_ctl -D /tmp/pgdata -o "-p 55432" start
    createdb -h localhost -p 55432 -U portal compset_test

    COMPSET_PG_URL="postgresql+psycopg://portal@localhost:5432/portal" \
        python -m pytest tests/test_compset_quota_pg.py -v

⚠️ **不要指到正式庫**。本檔會建立與刪除 `compset_conc_test` schema。
"""
from __future__ import annotations

import importlib
import os
import pkgutil
import threading
from datetime import date

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

import app.models as _models_pkg
from app.core.database import Base

for _m in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"app.models.{_m.name}")

from app.models.compset_analysis import CompsetSubscriber      # noqa: E402
from app.services import compset_quota_service as QS           # noqa: E402

PG_URL = os.environ.get("COMPSET_PG_URL", "")
SCHEMA = "compset_conc_test"
TODAY = date(2026, 9, 9)
QUOTA = 100

pytestmark = pytest.mark.skipif(
    not PG_URL,
    reason="需要 PostgreSQL。設 COMPSET_PG_URL 才會跑（SQLite 測不出併發）。",
)


@pytest.fixture()
def pg():
    """獨立 schema，測完清掉。⚠️ search_path 只放這個 schema，不含 public。"""
    admin = create_engine(PG_URL)
    with admin.begin() as c:
        c.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
        c.execute(text(f"CREATE SCHEMA {SCHEMA}"))

    # ⚠️ pool 要夠大，否則執行緒會排隊等連線 —— 那就測不到併發了
    engine = create_engine(PG_URL, pool_size=25, max_overflow=10)

    @event.listens_for(engine, "connect")
    def _set_search_path(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute(f"SET search_path TO {SCHEMA}")
        cur.close()

    tables = [t for n, t in Base.metadata.tables.items()
              if n.startswith("compset_") or n == "users"]
    Base.metadata.create_all(engine, tables=tables)

    Session = sessionmaker(bind=engine)
    s = Session()
    s.add(CompsetSubscriber(
        code="INTERNAL", name="內部", plan_level="A",
        window_a_days=14, window_b_days=45, window_c_days=120,
        freq_a_days=1, freq_b_days=3, freq_c_days=7,
        monthly_quota=QUOTA, quota_used=0, quota_anchor_day=1,
        quota_period_start="", location_query="", param_adults=2,
        param_nights=1, param_gl="tw", param_hl="zh-tw", param_currency="TWD",
        is_active=True, contact_name="", contact_email="", note=""))
    s.commit()
    sid = s.execute(text("SELECT id FROM compset_subscribers")).scalar_one()
    QS.ensure_period(s, sid, TODAY)
    s.commit()
    s.close()

    yield Session, sid

    engine.dispose()
    with admin.begin() as c:
        c.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
    admin.dispose()


def _used(Session) -> int:
    s = Session()
    try:
        return s.execute(text("SELECT quota_used FROM compset_subscribers")).scalar_one()
    finally:
        s.close()


def test_concurrent_reserve_never_exceeds_the_quota(pg):
    """
    ⭐ 20 條執行緒同時各搶 10 次，配額 100 → **剛好 10 條成功、10 條失敗**。

    先讀再寫的版本會讓多條同時讀到同一個 `quota_used`，各自寫回，
    最後 20 條全部成功 —— 發出 200 次請求、帳面卻只記一部分。
    超發是真的多花錢，而且**帳面上看不出來**（`quota_used` 是小的那個數字）。
    """
    Session, sid = pg
    results: list[bool] = []
    errors: list[str] = []
    barrier = threading.Barrier(20)          # 讓 20 條盡量同一瞬間送出

    def worker():
        s = Session()
        try:
            barrier.wait()
            ok = QS.reserve(s, sid, 10, TODAY)
            s.commit()
            results.append(ok)
        except Exception as exc:             # noqa: BLE001
            s.rollback()
            errors.append(repr(exc))
        finally:
            s.close()

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    granted = sum(1 for r in results if r)
    used = _used(Session)

    assert not errors, f"併發時噴例外：{errors[:3]}"
    assert granted == 10, f"應該剛好 10 條成功，實際 {granted} —— 超發"
    assert used == QUOTA, f"quota_used 應為 {QUOTA}，實際 {used}"
    assert used == granted * 10, "帳面用量 ≠ 實際發出的額度 ＝ 超發或漏記"


def test_concurrent_reserve_with_uneven_group_sizes_keeps_the_ledger_honest(pg):
    """
    不同組大小交錯搶（模擬 A 級一次 6 家、B 級一次 1 筆同時到）。

    誰成功不重要 —— 重要的是**帳面用量必須等於成功者拿走的總量**，
    而且永遠不超過上限。這條在測 D15「整組原子化」在併發下仍然成立。
    """
    Session, sid = pg
    sizes = [6, 1] * 10
    got: list[int] = []
    errors: list[str] = []
    barrier = threading.Barrier(len(sizes))

    def worker(n: int):
        s = Session()
        try:
            barrier.wait()
            if QS.reserve(s, sid, n, TODAY):
                got.append(n)
            s.commit()
        except Exception as exc:             # noqa: BLE001
            s.rollback()
            errors.append(repr(exc))
        finally:
            s.close()

    threads = [threading.Thread(target=worker, args=(n,)) for n in sizes]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    used = _used(Session)
    assert not errors, f"併發時噴例外：{errors[:3]}"
    assert used == sum(got), f"帳面 {used} ≠ 實際發出 {sum(got)} ＝ 超發或漏記"
    assert used <= QUOTA, f"超過配額上限：{used}"


def test_exhausted_quota_rejects_everyone_concurrently(pg):
    """
    配額已經用完時，同時湧入的預留**必須全部被擋**。

    硬停（SPEC D3）是這個模組的成本上限。這條在驗「用完之後不會因為
    併發而漏出去幾次」—— 漏出去的每一次都是真的錢。
    """
    Session, sid = pg
    s = Session()
    assert QS.reserve(s, sid, QUOTA, TODAY) is True      # 先一次用光
    s.commit()
    s.close()

    results: list[bool] = []
    barrier = threading.Barrier(15)

    def worker():
        s = Session()
        try:
            barrier.wait()
            results.append(QS.reserve(s, sid, 1, TODAY))
            s.commit()
        finally:
            s.close()

    threads = [threading.Thread(target=worker) for _ in range(15)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not any(results), "配額用盡後仍有預留成功 ＝ 硬停漏了"
    assert _used(Session) == QUOTA
