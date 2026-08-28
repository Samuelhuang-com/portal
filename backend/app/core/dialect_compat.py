"""
跨資料庫方言的 SQL 函式（2026-08-28，PostgreSQL 遷移 Phase 1）

為什麼需要這個檔
────────────────────────────────────────────────────────────────────────────
專案原本直接用 `func.strftime()` 與 `func.group_concat()`，這兩個都是
**SQLite 專屬函式，PostgreSQL 沒有**。在真的 PostgreSQL 上實測：

    SELECT strftime('%Y-%m', now());
    ERROR:  function strftime(unknown, timestamp with time zone) does not exist

    SELECT group_concat(x) FROM ...;
    ERROR:  function group_concat(text) does not exist

用 SQLAlchemy 的 `@compiles` 依方言分別渲染，**呼叫端只寫一種寫法**，
不需要在每個查詢裡判斷 `if dialect == ...`。

⚠️ **不要用「先取出再用 Python 處理」來繞過。** 那會把聚合從 SQL 拉回
   Python，重演 `opera_segment_service` 那個 15,538 ms / 517 MB 的坑
   （見 docs/CHANGELOG.md [1.96.32]）。

用法
────────────────────────────────────────────────────────────────────────────
    from app.core.dialect_compat import year_month, group_concat

    ym = year_month(ApprovedPurchaseRequest.approved_date)
    q = db.query(ym, func.count()).group_by(ym).order_by(ym)

    db.query(group_concat(Item.vendor, " / "))

⚠️ `substr()` 兩邊都有，**不需要**包裝（專案裡 8 處維持原樣）。
"""
from __future__ import annotations

from sqlalchemy import String, literal
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement


class year_month(FunctionElement):
    """日期／日期時間欄位 → `'YYYY-MM'` 字串。

    取代 `func.strftime("%Y-%m", col)`。

    · SQLite     → `strftime('%Y-%m', col)`
    · PostgreSQL → `to_char(col, 'YYYY-MM')`

    ⚠️ 欄位為 NULL 時兩邊都回 NULL（行為一致，已實測）。
    ⚠️ **但 `ORDER BY` 時 NULL 的位置兩邊相反**：SQLite 的 NULL 永遠排最前，
       PostgreSQL 是 ASC 排最後、DESC 排最前。排序欄位可能為 NULL 時，
       請明確寫 `.nullsfirst()` / `.nullslast()`，不要依賴預設。
    """

    type = String()
    name = "year_month"
    inherit_cache = True


@compiles(year_month)
def _year_month_default(element, compiler, **kw):
    """PostgreSQL 及其他方言。"""
    col, = element.clauses
    return "to_char(%s, 'YYYY-MM')" % compiler.process(col, **kw)


@compiles(year_month, "sqlite")
def _year_month_sqlite(element, compiler, **kw):
    # ⚠️ `%` 在這裡要寫成 `%%` —— 外層是 Python 的 % 格式化
    col, = element.clauses
    return "strftime('%%Y-%%m', %s)" % compiler.process(col, **kw)


class group_concat(FunctionElement):
    """字串聚合，以 `sep` 連接。

    取代 `func.group_concat(col, sep)`。

    · SQLite     → `group_concat(col, sep)`
    · PostgreSQL → `string_agg(col, sep)`

    ⚠️ **兩邊都不保證順序**，也都不支援直接 DISTINCT（SQLite 的
       `group_concat` 帶分隔字元時不能加 DISTINCT）。需要去重或固定順序時，
       在 Python 端處理（結果通常只有幾十個字串，不是效能問題）——
       現有的 `purchase_report.py` / `nichiyo_purchase_report.py` 已經這樣做。
    """

    type = String()
    name = "group_concat"
    inherit_cache = True


def _gc_parts(element, compiler, **kw) -> tuple[str, str]:
    clauses = list(element.clauses)
    col = compiler.process(clauses[0], **kw)
    sep = compiler.process(clauses[1], **kw) if len(clauses) > 1 else "','"
    return col, sep


@compiles(group_concat)
def _group_concat_default(element, compiler, **kw):
    """PostgreSQL 及其他方言。"""
    col, sep = _gc_parts(element, compiler, **kw)
    return "string_agg(%s, %s)" % (col, sep)


@compiles(group_concat, "sqlite")
def _group_concat_sqlite(element, compiler, **kw):
    col, sep = _gc_parts(element, compiler, **kw)
    return "group_concat(%s, %s)" % (col, sep)


def sep(value: str):
    """把分隔字元包成 bind literal。

    直接傳 Python 字串給 `group_concat()` 會被 SQLAlchemy 當成欄位名稱解析，
    必須包成 `literal()`。這個 helper 只是讓呼叫端讀起來乾淨一點。
    """
    return literal(value)
