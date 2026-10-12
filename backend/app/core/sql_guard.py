# -*- coding: utf-8 -*-
"""
SQL 查詢工具的安全檢查（settings/sql-console，僅系統管理員）

PostgreSQL 方言。純 Python、不 import 任何 app 模組（方便單獨測試）。

規則（2026-10-12 Samuel 裁示：可下 SQL、可 DELETE，但禁止 DROP TABLE 與「刪整張表」）：
  · 一次只能一個敘述（不能用 ; 串多個）
  · 只放行三種敘述：SELECT / WITH…SELECT / EXPLAIN（唯讀）與 DELETE
  · DELETE 必須有 WHERE，且 WHERE 不能是恆真式（1=1、true、'a'='a'、id=id、或 OR 一個恆真式）
  · DELETE 只允許單一資料表（不含 USING / RETURNING / WITH）；受保護資料表一律不可刪
  · 任何位置出現 DDL／寫入／管理類關鍵字一律拒絕：
      DROP TRUNCATE ALTER CREATE GRANT REVOKE INSERT UPDATE MERGE INTO SET ANALYZE
      （COPY/VACUUM/CALL/DO/BEGIN… 因第一個字不在白名單而被擋）
  · 危險函式（pg_terminate_backend、lo_*、dblink*、setval、set_config、pg_read_file…）一律拒絕

這層只是「第一道」。真正的保險在 service：
  · SELECT 在 `SET TRANSACTION READ ONLY` 的交易裡跑（資料庫本身拒絕任何寫入）
  · DELETE 先在交易內實際執行→取得筆數與被刪資料→ROLLBACK，使用者確認後才真的 COMMIT，
    筆數有上限，被刪資料完整備份進 audit_logs.extra。

字串與註解會先被遮掉再判斷，所以 `SELECT 'drop table x'` 與 `-- drop` 不會被誤擋，
`SELECT 1; DROP TABLE x`、`/* */` 夾帶也擋得住。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

MAX_SQL_LENGTH = 20_000

# 刪除時完全禁止的資料表（帳號權限、系統設定、稽核紀錄、migration 版本）
PROTECTED_DELETE_TABLES = frozenset({
    "users", "roles", "role_permissions", "user_roles", "user_departments",
    "tenants", "system_settings", "audit_logs",
    "alembic_version", "alembic_version_cp",
})

# 一律拒絕的關鍵字（未加引號的單字）。
# 只放「不可能是一般欄位名稱、卻能在 SELECT / WITH 裡夾帶寫入或建表」的字：
#   INSERT/UPDATE/MERGE（含 WITH…INSERT、SELECT…FOR UPDATE）、INTO（SELECT INTO 會建表）、
#   DDL/權限字、SET（UPDATE … SET）、ANALYZE（EXPLAIN ANALYZE 會真的執行）。
# 其餘管理類敘述（COPY/VACUUM/CALL/DO/BEGIN/COMMIT…）由「第一個字必須是 SELECT/WITH/EXPLAIN/DELETE」擋掉；
# comment、start、lock、cluster、security 等常見欄位名稱因此不會被誤擋。
FORBIDDEN_KEYWORDS = frozenset({
    "DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE",
    "INSERT", "UPDATE", "MERGE", "INTO", "SET", "ANALYZE", "ANALYSE",
})

# 危險函式／系統表（比對小寫；加引號的識別字也會檢查）
_DANGEROUS_NAME_RE = re.compile(
    r"^(pg_terminate_backend|pg_cancel_backend|pg_reload_conf|pg_read_file|pg_read_binary_file"
    r"|pg_ls_\w+|pg_stat_file|pg_rotate_logfile|pg_switch_wal|pg_create_\w+|pg_drop_\w+"
    r"|pg_promote|pg_advisory_\w+|pg_try_advisory_\w+|lo_\w+|dblink\w*"
    r"|set_config|setval|nextval|pg_authid|pg_shadow|pg_file_settings|pg_hba_file_rules"
    r"|query_to_xml\w*|table_to_xml\w*|database_to_xml\w*|schema_to_xml\w*)$"
)

_ALLOWED_FIRST = {"SELECT", "WITH", "EXPLAIN", "DELETE"}

# 恆真式（把 WHERE 的每個 OR 分支正規化後比對）
_TAUTOLOGY_RES = [
    re.compile(r"^\(*(true|1|notfalse|nullisnull|'t'|'true'|'y'|'yes')\)*$"),
    re.compile(r"^\(*(\d+)=\1\)*$"),
    re.compile(r"^\(*'[^']*'='[^']*'\)*$"),
    re.compile(r"^\(*([a-z_][\w.]*)=\1\)*$"),
    re.compile(r"^\(*(\d+)(<=|>=)(\d+)\)*$"),
]


class SqlGuardError(Exception):
    """SQL 未通過安全檢查；訊息可直接顯示給使用者。"""


@dataclass
class Tok:
    kind: str   # word | qident | str | num | punct
    val: str
    pos: int
    end: int

    @property
    def up(self) -> str:
        return self.val.upper()

    @property
    def low(self) -> str:
        return self.val.lower()


@dataclass
class GuardResult:
    kind: str                 # 'select' | 'delete'
    sql: str                  # 清理後（已去掉結尾分號）、可直接執行的 SQL
    table: Optional[str] = None   # delete 的目標資料表（小寫、不含 schema）


_WORD_RE = re.compile(r"[A-Za-z_\u0080-￿][\w$\u0080-￿]*")
_NUM_RE = re.compile(r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
_DOLLAR_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$")


def tokenize(sql: str) -> List[Tok]:
    """切詞：註解丟棄、字串／加引號識別字／dollar-quote 各自成一個 token。"""
    toks: List[Tok] = []
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if c.isspace():
            i += 1
            continue
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j == -1 else j + 1
            continue
        if sql.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if sql.startswith("/*", j):
                    depth += 1
                    j += 2
                elif sql.startswith("*/", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            if depth:
                raise SqlGuardError("區塊註解 /* 沒有結尾 */")
            i = j
            continue
        if c == "'":
            escape = bool(toks and toks[-1].kind == "word" and toks[-1].val in ("e", "E") and toks[-1].end == i)
            j = i + 1
            while True:
                if j >= n:
                    raise SqlGuardError("字串的單引號沒有成對")
                if escape and sql[j] == "\\":
                    j += 2
                    continue
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            toks.append(Tok("str", sql[i + 1:j], i, j + 1))
            i = j + 1
            continue
        if c == '"':
            j = i + 1
            while True:
                if j >= n:
                    raise SqlGuardError("識別字的雙引號沒有成對")
                if sql[j] == '"':
                    if j + 1 < n and sql[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            toks.append(Tok("qident", sql[i + 1:j].replace('""', '"'), i, j + 1))
            i = j + 1
            continue
        if c == "$":
            m = _DOLLAR_RE.match(sql, i)
            if m:
                tag = m.group(0)
                j = sql.find(tag, m.end())
                if j == -1:
                    raise SqlGuardError("dollar-quote 字串沒有結尾")
                toks.append(Tok("str", sql[m.end():j], i, j + len(tag)))
                i = j + len(tag)
                continue
        m = _WORD_RE.match(sql, i)
        if m:
            toks.append(Tok("word", m.group(0), i, m.end()))
            i = m.end()
            continue
        m = _NUM_RE.match(sql, i)
        if m:
            toks.append(Tok("num", m.group(0), i, m.end()))
            i = m.end()
            continue
        toks.append(Tok("punct", c, i, i + 1))
        i += 1
    return toks


def _norm(toks: List[Tok]) -> str:
    """把一段 token 正規化成無空白小寫字串（字串內容保留）。"""
    out = []
    for t in toks:
        if t.kind == "str":
            out.append("'" + t.val + "'")
        elif t.kind == "qident":
            out.append(t.val.lower())
        else:
            out.append(t.low)
    return "".join(out)


def _split_top_level_or(toks: List[Tok]) -> List[List[Tok]]:
    branches, cur, depth = [], [], 0
    for t in toks:
        if t.kind == "punct" and t.val == "(":
            depth += 1
        elif t.kind == "punct" and t.val == ")":
            depth -= 1
        if depth == 0 and t.kind == "word" and t.up == "OR":
            branches.append(cur)
            cur = []
            continue
        cur.append(t)
    branches.append(cur)
    return branches


def _is_tautology(branch: List[Tok]) -> bool:
    s = _norm(branch)
    return any(r.match(s) for r in _TAUTOLOGY_RES)


def _scan_forbidden(toks: List[Tok]) -> None:
    for t in toks:
        if t.kind == "word":
            if t.up in FORBIDDEN_KEYWORDS:
                raise SqlGuardError(f"禁止使用 {t.up}（本工具只允許 SELECT 與有 WHERE 的 DELETE）")
            if _DANGEROUS_NAME_RE.match(t.low):
                raise SqlGuardError(f"禁止使用系統函式／系統表 {t.val}")
        elif t.kind == "qident":
            if _DANGEROUS_NAME_RE.match(t.low):
                raise SqlGuardError(f"禁止使用系統函式／系統表 {t.val}")


def _parse_delete(toks: List[Tok]) -> str:
    """驗證 DELETE 的結構並回傳目標資料表（小寫）。"""
    if sum(1 for t in toks if t.kind == "word" and t.up == "DELETE") != 1:
        raise SqlGuardError("DELETE 敘述中不可再出現其他 DELETE（含 WITH … DELETE）")
    for t in toks:
        if t.kind == "word" and t.up in ("RETURNING", "USING", "ONLY", "CASCADE"):
            hint = "；請改用 WHERE … IN (SELECT …)" if t.up == "USING" else ""
            raise SqlGuardError(f"DELETE 不支援 {t.up}（系統會自動備份被刪的資料）{hint}")
    if len(toks) < 3 or toks[1].up != "FROM":
        raise SqlGuardError("DELETE 格式必須是：DELETE FROM 資料表 WHERE 條件")

    i = 2
    name_tok = toks[i]
    if name_tok.kind not in ("word", "qident"):
        raise SqlGuardError("找不到 DELETE 的資料表名稱")
    schema = None
    table = name_tok
    if i + 2 < len(toks) and toks[i + 1].kind == "punct" and toks[i + 1].val == ".":
        schema = name_tok
        table = toks[i + 2]
        if table.kind not in ("word", "qident"):
            raise SqlGuardError("資料表名稱格式不正確")
        i += 2
    if schema is not None and schema.low != "public":
        raise SqlGuardError(f"只允許刪除 public schema 的資料表（收到 {schema.val}）")
    tname = table.val.lower() if table.kind == "word" else table.val
    if tname.startswith("pg_") or tname == "information_schema":
        raise SqlGuardError("不可刪除系統資料表")
    if tname.lower() in PROTECTED_DELETE_TABLES:
        raise SqlGuardError(f"資料表 {tname} 受保護（帳號／權限／系統設定／稽核紀錄），不可由本工具刪除")

    i += 1
    # 可選別名：[AS] alias
    if i < len(toks) and toks[i].kind == "word" and toks[i].up == "AS":
        i += 1
        if i >= len(toks) or toks[i].kind not in ("word", "qident"):
            raise SqlGuardError("AS 後面缺少別名")
        i += 1
    elif i < len(toks) and toks[i].kind in ("word", "qident") and toks[i].up != "WHERE":
        i += 1
    if i >= len(toks) or toks[i].kind != "word" or toks[i].up != "WHERE":
        raise SqlGuardError("DELETE 必須有 WHERE 條件（禁止刪除整張資料表）")

    where = toks[i + 1:]
    if not where:
        raise SqlGuardError("WHERE 後面沒有條件")
    for branch in _split_top_level_or(where):
        if not branch or _is_tautology(branch):
            raise SqlGuardError("WHERE 條件恆為真（例如 1=1、true）等同刪除整張資料表，已拒絕")
    return tname.lower()


def check_sql(sql: str) -> GuardResult:
    """主要入口。通過回傳 GuardResult，否則丟 SqlGuardError。"""
    if sql is None or not sql.strip():
        raise SqlGuardError("請輸入 SQL")
    if len(sql) > MAX_SQL_LENGTH:
        raise SqlGuardError(f"SQL 過長（上限 {MAX_SQL_LENGTH} 字元）")
    if "\x00" in sql:
        raise SqlGuardError("SQL 含有不合法字元")

    toks = tokenize(sql)
    # 去掉結尾分號
    end = len(toks)
    while end and toks[end - 1].kind == "punct" and toks[end - 1].val == ";":
        end -= 1
    body = toks[:end]
    if not body:
        raise SqlGuardError("請輸入 SQL")
    if any(t.kind == "punct" and t.val == ";" for t in body):
        raise SqlGuardError("一次只能執行一個 SQL 敘述（不可用 ; 串接多個）")

    first = body[0]
    if first.kind != "word" or first.up not in _ALLOWED_FIRST:
        shown = first.val if first.kind in ("word", "qident") else first.val
        raise SqlGuardError(f"不允許的敘述：{shown}（只能執行 SELECT / WITH / EXPLAIN 與 DELETE）")

    if first.up == "DELETE":
        _scan_forbidden(body)
        table = _parse_delete(body)
        clean = sql[:body[-1].end].rstrip()
        return GuardResult(kind="delete", sql=clean, table=table)

    # 唯讀敘述：任何位置都不能出現 DELETE（含 WITH … DELETE … RETURNING）
    for t in body:
        if t.kind == "word" and t.up == "DELETE":
            raise SqlGuardError("此敘述含有 DELETE；請直接寫單純的 DELETE FROM … WHERE …（不可包在 WITH／EXPLAIN 內）")
    _scan_forbidden(body)
    clean = sql[:body[-1].end].rstrip()
    return GuardResult(kind="select", sql=clean)
