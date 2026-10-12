# -*- coding: utf-8 -*-
"""
SQL 查詢工具安全檢查（app/core/sql_guard.py）— 禁止 DROP / TRUNCATE / 刪整張表

純函式測試，不需要資料庫。重點是「該擋的一定擋、不該擋的不誤擋」。
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.sql_guard import SqlGuardError, check_sql  # noqa: E402


# ── 必須被擋 ─────────────────────────────────────────────────────────────────
BLOCKED = [
    "DROP TABLE audit_cells",
    "drop table if exists audit_cells",
    "  DrOp   TABLE x",
    "TRUNCATE audit_cells",
    "TRUNCATE TABLE audit_cells CASCADE",
    "ALTER TABLE audit_cells ADD COLUMN x int",
    "CREATE TABLE t (id int)",
    "INSERT INTO audit_cells VALUES (1)",
    "UPDATE audit_cells SET comment = 'x' WHERE id = 1",
    "GRANT ALL ON audit_cells TO public",
    "COPY audit_cells TO '/tmp/x'",
    "VACUUM FULL",
    "SET search_path TO x",
    "BEGIN",
    "COMMIT",
    # 多敘述／夾帶
    "SELECT 1; DROP TABLE audit_cells",
    "SELECT 1;DROP TABLE audit_cells;",
    "DELETE FROM audit_cells WHERE id = 1; DELETE FROM audit_cells WHERE id = 2",
    "SELECT 1 /* x */ ; /* y */ DROP TABLE t",
    # 刪整張表
    "DELETE FROM audit_cells",
    "DELETE FROM audit_cells;",
    "DELETE FROM public.audit_cells",
    "DELETE FROM audit_cells WHERE 1=1",
    "DELETE FROM audit_cells WHERE 1 = 1",
    "DELETE FROM audit_cells WHERE true",
    "DELETE FROM audit_cells WHERE TRUE;",
    "DELETE FROM audit_cells WHERE (1=1)",
    "DELETE FROM audit_cells WHERE id = 5 OR 1=1",
    "DELETE FROM audit_cells WHERE 1=1 OR id = 5",
    "DELETE FROM audit_cells WHERE 'a'='a'",
    "DELETE FROM audit_cells WHERE id = id",
    "DELETE FROM audit_cells WHERE 2=2",
    "DELETE FROM audit_cells WHERE NULL IS NULL",
    "DELETE FROM audit_cells WHERE",
    "DELETE FROM audit_cells -- WHERE id = 1",
    "DELETE FROM audit_cells /* WHERE id = 1 */",
    # DELETE 結構限制
    "DELETE FROM audit_cells WHERE id = 1 RETURNING *",
    "DELETE FROM a USING b WHERE a.id = b.id",
    "DELETE FROM ONLY audit_cells WHERE id = 1",
    "WITH d AS (DELETE FROM audit_cells WHERE id = 1 RETURNING *) SELECT * FROM d",
    "EXPLAIN DELETE FROM audit_cells WHERE id = 1",
    "DELETE FROM other_schema.audit_cells WHERE id = 1",
    "DELETE audit_cells WHERE id = 1",
    # 受保護資料表
    "DELETE FROM users WHERE id = 'x'",
    "DELETE FROM public.users WHERE id = 'x'",
    'DELETE FROM "users" WHERE id = \'x\'',
    "DELETE FROM role_permissions WHERE id = 1",
    "DELETE FROM audit_logs WHERE id = 'x'",
    "DELETE FROM alembic_version WHERE version_num = 'x'",
    "DELETE FROM system_settings WHERE key = 'x'",
    "DELETE FROM pg_class WHERE oid = 1",
    # SELECT 的副作用寫法
    "SELECT * INTO new_t FROM audit_cells",
    "SELECT * FROM audit_cells FOR UPDATE",
    "EXPLAIN ANALYZE SELECT 1",
    "SELECT pg_terminate_backend(123)",
    "SELECT setval('audit_cells_id_seq', 1)",
    "SELECT nextval('audit_cells_id_seq')",
    "SELECT lo_import('/etc/passwd')",
    "SELECT pg_read_file('/etc/passwd')",
    "SELECT set_config('x','y',false)",
    'SELECT "setval"(\'s\', 1)',
    "SELECT * FROM pg_authid",
    "SELECT * FROM pg_shadow",
    "SELECT * FROM dblink('x','select 1') AS t(a int)",
    # 其他
    "",
    "   ",
    ";",
    "-- only a comment",
    "SELECT 'unterminated",
    "SELECT 1 /* unterminated",
    "SHOW ALL",
    "CALL some_proc()",
    "DO $$ BEGIN PERFORM 1; END $$",
    "(SELECT 1)",
]


@pytest.mark.parametrize("sql", BLOCKED)
def test_blocked(sql):
    with pytest.raises(SqlGuardError):
        check_sql(sql)


# ── 必須放行 ─────────────────────────────────────────────────────────────────
ALLOWED_SELECT = [
    "SELECT 1",
    "select * from audit_cells limit 10;",
    "SELECT * FROM public.audit_sheet_departments ORDER BY id",
    "SELECT 'drop table x' AS t",
    "SELECT 'a;b' AS t",
    "SELECT * FROM audit_cells WHERE comment LIKE '%update%'",
    "SELECT updated_at, created_at FROM audit_cells",
    "SELECT * FROM audit_cells -- drop table x",
    "SELECT /* delete from x */ 1",
    'SELECT "update" FROM t',
    "SELECT $$drop table x$$",
    "SELECT E'it\\'s; drop' AS t",
    "WITH a AS (SELECT 1 AS x) SELECT * FROM a",
    "EXPLAIN SELECT * FROM audit_cells",
    "SELECT a.id, b.id FROM a JOIN b ON a.id = b.id WHERE a.x = ':bind'",
    "SELECT jsonb_set('{}'::jsonb, '{a}', '1')",
    "SELECT * FROM information_schema.columns WHERE table_name = 'audit_cells'",
    "SELECT current_database()",
]


@pytest.mark.parametrize("sql", ALLOWED_SELECT)
def test_allowed_select(sql):
    r = check_sql(sql)
    assert r.kind == "select"
    assert not r.sql.endswith(";")


ALLOWED_DELETE = [
    ("DELETE FROM audit_cells WHERE id = 5", "audit_cells"),
    ("delete from audit_cells where id = 5;", "audit_cells"),
    ("DELETE FROM public.audit_cells WHERE id = 5", "audit_cells"),
    ("DELETE FROM audit_cells AS c WHERE c.id = 5", "audit_cells"),
    ("DELETE FROM audit_cells c WHERE c.id = 5", "audit_cells"),
    ("DELETE FROM audit_cells WHERE id IN (1, 2, 3)", "audit_cells"),
    ("DELETE FROM audit_cells WHERE sheet_id IN (SELECT id FROM audit_sheets WHERE period_id = 4)", "audit_cells"),
    ("DELETE FROM audit_cells WHERE id = 5 AND 1=1", "audit_cells"),
    ("DELETE FROM audit_cells WHERE comment = 'a=a' AND id = 5", "audit_cells"),
    ("DELETE FROM audit_cells WHERE id = 5 -- 測試資料", "audit_cells"),
    ('DELETE FROM "audit_cells" WHERE id = 5', "audit_cells"),
]


@pytest.mark.parametrize("sql,table", ALLOWED_DELETE)
def test_allowed_delete(sql, table):
    r = check_sql(sql)
    assert r.kind == "delete"
    assert r.table == table
    assert not r.sql.endswith(";")


def test_clean_sql_strips_trailing_semicolon_only():
    assert check_sql("SELECT 1 ;  ").sql == "SELECT 1"
    assert check_sql("SELECT ';' ;").sql == "SELECT ';'"


def test_trailing_line_comment_cannot_swallow_appended_clause():
    # service 會在 DELETE 後面接 "\nRETURNING *"；結尾註解保留但不會吃掉換行後的內容
    r = check_sql("DELETE FROM audit_cells WHERE id = 5 -- note")
    assert (r.sql + "\nRETURNING *").splitlines()[-1] == "RETURNING *"
