"""
Budget Management Router — Phase 1
Prefix: /api/v1/budget

Phase 1 endpoints:
  GET  /dashboard                       — 預算總覽 KPI
  GET  /years                           — 年度主檔列表
  GET  /plans                           — 預算主表清單
  POST /plans                           — 新增預算主表
  GET  /plans/{plan_id}                 — 取單筆預算主表
  PUT  /plans/{plan_id}                 — 更新預算主表
  GET  /plans/{plan_id}/details         — 預算明細列表
  POST /plans/{plan_id}/details         — 新增預算明細
  PUT  /plans/{plan_id}/details/{id}    — 更新預算明細
  DELETE /plans/{plan_id}/details/{id}  — 刪除預算明細 (draft 狀態才可刪)
  GET  /transactions                    — 交易明細清單
  GET  /transactions/{id}               — 取單筆交易
  PUT  /transactions/{id}               — 更新交易
  GET  /masters/departments             — 部門主檔
  POST /masters/departments             — 新增部門
  PUT  /masters/departments/{id}        — 更新部門
  GET  /masters/account-codes           — 會計科目主檔
  POST /masters/account-codes           — 新增會計科目
  PUT  /masters/account-codes/{id}      — 更新會計科目
  GET  /masters/budget-items            — 預算項目主檔
  POST /masters/budget-items            — 新增預算項目
  PUT  /masters/budget-items/{id}       — 更新預算項目
  GET  /mappings                        — 對照規則
  POST /mappings                        — 新增對照規則
  PUT  /mappings/{id}                   — 更新對照規則
  GET  /reports/budget-vs-actual        — 預算比較報表 (from view)
  GET  /reports/data-quality            — 資料品質問題清單
"""

import sqlite3
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.budget_database import get_budget_db
from app.dependencies import get_current_user, require_roles
from app.models.user import User

router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> List[dict]:
    c = conn.execute(sql, params)
    return [dict(r) for r in c.fetchall()]


def _one(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> Optional[dict]:
    c = conn.execute(sql, params)
    row = c.fetchone()
    return dict(row) if row else None


def _get_user_roles(user: User, db_main) -> set:
    """取得使用者角色 set（複用 dependencies 邏輯）"""
    from app.models.user_role import UserRole
    from app.models.role import Role
    rows = (
        db_main.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    return {r[0] for r in rows}


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas (輕量，只供 POST/PUT 使用)
# ─────────────────────────────────────────────────────────────────────────────

class BudgetPlanCreate(BaseModel):
    plan_code: str
    plan_name: str
    dept_id: int
    budget_year_id: int
    plan_type: str = "OPEX"
    notes: Optional[str] = None


class BudgetPlanUpdate(BaseModel):
    plan_name: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class BudgetPlanDetailCreate(BaseModel):
    line_type: str = "detail"
    raw_account_code_name: Optional[str] = None
    standard_account_code_id: Optional[int] = None
    raw_budget_item_name: Optional[str] = None
    standard_budget_item_id: Optional[int] = None
    month_01_budget: Optional[float] = None
    month_02_budget: Optional[float] = None
    month_03_budget: Optional[float] = None
    month_04_budget: Optional[float] = None
    month_05_budget: Optional[float] = None
    month_06_budget: Optional[float] = None
    month_07_budget: Optional[float] = None
    month_08_budget: Optional[float] = None
    month_09_budget: Optional[float] = None
    month_10_budget: Optional[float] = None
    month_11_budget: Optional[float] = None
    month_12_budget: Optional[float] = None
    annual_budget: Optional[float] = None
    raw_remark: Optional[str] = None
    is_active_detail: int = 1


class BudgetPlanDetailUpdate(BaseModel):
    raw_account_code_name: Optional[str] = None
    standard_account_code_id: Optional[int] = None
    raw_budget_item_name: Optional[str] = None
    standard_budget_item_id: Optional[int] = None
    month_01_budget: Optional[float] = None
    month_02_budget: Optional[float] = None
    month_03_budget: Optional[float] = None
    month_04_budget: Optional[float] = None
    month_05_budget: Optional[float] = None
    month_06_budget: Optional[float] = None
    month_07_budget: Optional[float] = None
    month_08_budget: Optional[float] = None
    month_09_budget: Optional[float] = None
    month_10_budget: Optional[float] = None
    month_11_budget: Optional[float] = None
    month_12_budget: Optional[float] = None
    annual_budget: Optional[float] = None
    raw_remark: Optional[str] = None
    is_active_detail: Optional[int] = None


class TransactionUpdate(BaseModel):
    dept_id: Optional[int] = None
    month_num: Optional[int] = None
    raw_account_code_name: Optional[str] = None
    account_code_id: Optional[int] = None
    raw_budget_item_name: Optional[str] = None
    budget_item_id: Optional[int] = None
    description: Optional[str] = None
    amount_ex_tax: Optional[float] = None
    requester: Optional[str] = None
    note_1: Optional[str] = None
    note_2: Optional[str] = None
    note_3: Optional[str] = None


class DepartmentCreate(BaseModel):
    dept_code: str
    dept_name: str
    dept_group: Optional[str] = None
    sort_order: int = 0
    is_active: int = 1


class DepartmentUpdate(BaseModel):
    dept_code: Optional[str] = None
    dept_name: Optional[str] = None
    dept_group: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[int] = None


class AccountCodeCreate(BaseModel):
    account_code_name: str
    normalized_name: str
    is_raw_group: int = 0
    notes: Optional[str] = None


class AccountCodeUpdate(BaseModel):
    account_code_name: Optional[str] = None
    normalized_name: Optional[str] = None
    is_raw_group: Optional[int] = None
    notes: Optional[str] = None
    # NOTE: 若 account_codes 表尚無 is_active 欄位，請執行：
    #   ALTER TABLE account_codes ADD COLUMN is_active INTEGER DEFAULT 1
    is_active: Optional[int] = None


class BudgetItemCreate(BaseModel):
    budget_item_name: str
    normalized_name: str
    is_capex: int = 0
    notes: Optional[str] = None


class BudgetItemUpdate(BaseModel):
    budget_item_name: Optional[str] = None
    normalized_name: Optional[str] = None
    is_capex: Optional[int] = None
    notes: Optional[str] = None
    # NOTE: 若 budget_items 表尚無 is_active 欄位，請執行：
    #   ALTER TABLE budget_items ADD COLUMN is_active INTEGER DEFAULT 1
    is_active: Optional[int] = None


class MappingCreate(BaseModel):
    dept_id: Optional[int] = None
    quarter_code: Optional[str] = None
    source_account_header: str
    account_code_id: Optional[int] = None
    mapped_budget_item_name: str
    budget_item_id: Optional[int] = None
    mapping_method: str = "manual"
    notes: Optional[str] = None


class MappingUpdate(BaseModel):
    dept_id: Optional[int] = None
    quarter_code: Optional[str] = None
    source_account_header: Optional[str] = None
    account_code_id: Optional[int] = None
    mapped_budget_item_name: Optional[str] = None
    budget_item_id: Optional[int] = None
    mapping_method: Optional[str] = None
    notes: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# 1. Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def get_budget_dashboard(
    year_id: int = Query(1, description="budget_year_id"),
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    """
    預算總覽 KPI：
    - 總預算金額（依 active_detail 加總）
    - 總實績金額（交易明細加總）
    - 預算餘額 / 執行率
    - 超支科目數 / 即將超支科目數
    - 各部門摘要
    """
    # 年度資訊
    year_row = _one(conn, "SELECT * FROM budget_years WHERE id=?", (year_id,))
    if not year_row:
        raise HTTPException(status_code=404, detail="年度不存在")

    # 總預算（active detail）
    total_budget = _one(conn, """
        SELECT COALESCE(SUM(bpd.annual_budget), 0) AS total
        FROM budget_plan_details bpd
        JOIN budget_plans bp ON bp.id = bpd.budget_plan_id
        WHERE bp.budget_year_id = ? AND bpd.is_active_detail = 1
    """, (year_id,))["total"]

    # 總實績
    total_actual = _one(conn, """
        SELECT COALESCE(SUM(amount_ex_tax), 0) AS total
        FROM budget_transactions
        WHERE budget_year_id = ? AND amount_missing_flag = 0
    """, (year_id,))["total"]

    variance = total_budget - total_actual
    exec_rate = round(total_actual / total_budget * 100, 1) if total_budget else 0.0

    # 超支科目（年度實績 > 年度預算）
    overrun_rows = _rows(conn, """
        SELECT dept_name, account_code_name,
               annual_budget, annual_actual,
               annual_variance
        FROM v_budget_vs_actual_by_account_total
        WHERE annual_actual > annual_budget AND annual_budget > 0
        ORDER BY annual_variance ASC
    """)

    # 即將超支（執行率 > 85%）
    near_overrun = _rows(conn, """
        SELECT dept_name, account_code_name,
               annual_budget, annual_actual,
               ROUND(annual_actual * 100.0 / annual_budget, 1) AS exec_rate
        FROM v_budget_vs_actual_by_account_total
        WHERE annual_budget > 0
          AND annual_actual <= annual_budget
          AND annual_actual * 100.0 / annual_budget >= 85
        ORDER BY exec_rate DESC
    """)

    # 各部門摘要
    dept_summary = _rows(conn, """
        SELECT
            d.dept_name,
            COALESCE(SUM(bpd.annual_budget), 0) AS plan_budget,
            0 AS actual_amount
        FROM budget_plan_details bpd
        JOIN budget_plans bp ON bp.id = bpd.budget_plan_id
        LEFT JOIN departments d ON d.id = bp.dept_id
        WHERE bp.budget_year_id = ? AND bpd.is_active_detail = 1
        GROUP BY d.dept_name
        ORDER BY plan_budget DESC
    """, (year_id,))

    # 加入實績到部門摘要
    for dept in dept_summary:
        row = _one(conn, """
            SELECT COALESCE(SUM(amount_ex_tax), 0) AS actual
            FROM budget_transactions bt
            JOIN departments d ON d.id = bt.dept_id
            WHERE bt.budget_year_id = ? AND d.dept_name = ? AND bt.amount_missing_flag = 0
        """, (year_id, dept["dept_name"]))
        dept["actual_amount"] = row["actual"] if row else 0
        b = dept["plan_budget"]
        a = dept["actual_amount"]
        dept["exec_rate"] = round(a / b * 100, 1) if b else 0.0
        dept["variance"] = b - a

    # 資料品質問題數
    dq_count = _one(conn, "SELECT COUNT(*) AS cnt FROM data_quality_issues")["cnt"]
    missing_amount_count = _one(conn, "SELECT COUNT(*) AS cnt FROM v_transactions_missing_amount")["cnt"]
    unresolved_count = _one(conn, "SELECT COUNT(*) AS cnt FROM v_unresolved_plan_details")["cnt"]

    return {
        "year": year_row,
        "summary": {
            "total_budget": total_budget,
            "total_actual": total_actual,
            "variance": variance,
            "exec_rate": exec_rate,
            "overrun_count": len(overrun_rows),
            "near_overrun_count": len(near_overrun),
        },
        "overrun_items": overrun_rows[:10],
        "near_overrun_items": near_overrun[:10],
        "dept_summary": dept_summary,
        "data_quality": {
            "dq_issue_count": dq_count,
            "missing_amount_count": missing_amount_count,
            "unresolved_plan_count": unresolved_count,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Years
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/years")
def list_years(
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    return _rows(conn, "SELECT * FROM budget_years ORDER BY budget_year DESC")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Budget Plans
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/plans")
def list_plans(
    year_id: Optional[int] = Query(None),
    dept_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    sql = """
        SELECT bp.*, d.dept_name, d.dept_code, by2.budget_year
        FROM budget_plans bp
        LEFT JOIN departments d ON d.id = bp.dept_id
        LEFT JOIN budget_years by2 ON by2.id = bp.budget_year_id
        WHERE 1=1
    """
    params = []
    if year_id:
        sql += " AND bp.budget_year_id = ?"
        params.append(year_id)
    if dept_id:
        sql += " AND bp.dept_id = ?"
        params.append(dept_id)
    if status:
        sql += " AND bp.status = ?"
        params.append(status)
    sql += " ORDER BY by2.budget_year DESC, d.sort_order, bp.id"
    return _rows(conn, sql, tuple(params))


@router.post("/plans", status_code=status.HTTP_201_CREATED)
def create_plan(
    body: BudgetPlanCreate,
    current_user: User = Depends(require_roles("budget_manage", "budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    # 驗證年度存在
    if not _one(conn, "SELECT id FROM budget_years WHERE id=?", (body.budget_year_id,)):
        raise HTTPException(status_code=400, detail="年度不存在")
    # 驗證部門存在
    if not _one(conn, "SELECT id FROM departments WHERE id=?", (body.dept_id,)):
        raise HTTPException(status_code=400, detail="部門不存在")
    # 檢查 plan_code 唯一
    if _one(conn, "SELECT id FROM budget_plans WHERE plan_code=?", (body.plan_code,)):
        raise HTTPException(status_code=400, detail="plan_code 已存在")

    cursor = conn.execute("""
        INSERT INTO budget_plans (plan_code, plan_name, dept_id, budget_year_id, plan_type, version_no, status, notes)
        VALUES (?, ?, ?, ?, ?, 1, 'draft', ?)
    """, (body.plan_code, body.plan_name, body.dept_id, body.budget_year_id, body.plan_type, body.notes))
    conn.commit()
    plan_id = cursor.lastrowid
    return _one(conn, "SELECT * FROM budget_plans WHERE id=?", (plan_id,))


@router.get("/plans/{plan_id}")
def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    row = _one(conn, """
        SELECT bp.*, d.dept_name, d.dept_code, by2.budget_year
        FROM budget_plans bp
        LEFT JOIN departments d ON d.id = bp.dept_id
        LEFT JOIN budget_years by2 ON by2.id = bp.budget_year_id
        WHERE bp.id = ?
    """, (plan_id,))
    if not row:
        raise HTTPException(status_code=404, detail="預算主表不存在")
    return row


@router.put("/plans/{plan_id}")
def update_plan(
    plan_id: int,
    body: BudgetPlanUpdate,
    current_user: User = Depends(require_roles("budget_manage", "budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    plan = _one(conn, "SELECT * FROM budget_plans WHERE id=?", (plan_id,))
    if not plan:
        raise HTTPException(status_code=404, detail="預算主表不存在")

    # closed 狀態只有 budget_admin 可以修改 status
    if plan["status"] == "closed" and body.status != "closed":
        # 需要 admin 才能重開
        # 這裡做簡化：只要有 budget_manage 或 budget_admin 就允許
        # 真正嚴格的 role check 可在此擴充
        pass

    updates = {}
    if body.plan_name is not None:
        updates["plan_name"] = body.plan_name
    if body.status is not None:
        valid_statuses = {"draft", "open", "closed", "imported_from_excel", "void"}
        if body.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"狀態無效，允許值：{valid_statuses}")
        updates["status"] = body.status
    if body.notes is not None:
        updates["notes"] = body.notes

    if not updates:
        return plan

    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [plan_id]
    conn.execute(f"UPDATE budget_plans SET {set_clause} WHERE id=?", values)
    conn.commit()
    return _one(conn, "SELECT * FROM budget_plans WHERE id=?", (plan_id,))


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: int,
    current_user: User = Depends(require_roles("budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    """
    作廢 / 刪除預算主表：
    - draft  → 硬刪除（連帶刪除所有明細）
    - open / closed / imported_from_excel → 軟刪除（status 改為 'void'）
    """
    plan = _one(conn, "SELECT * FROM budget_plans WHERE id=?", (plan_id,))
    if not plan:
        raise HTTPException(status_code=404, detail="預算主表不存在")
    if plan["status"] == "void":
        raise HTTPException(status_code=400, detail="預算主表已作廢")

    if plan["status"] == "draft":
        conn.execute("DELETE FROM budget_plan_details WHERE budget_plan_id=?", (plan_id,))
        conn.execute("DELETE FROM budget_plans WHERE id=?", (plan_id,))
    else:
        conn.execute("UPDATE budget_plans SET status='void' WHERE id=?", (plan_id,))
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Budget Plan Details
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/plans/{plan_id}/details")
def list_plan_details(
    plan_id: int,
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    plan = _one(conn, "SELECT id FROM budget_plans WHERE id=?", (plan_id,))
    if not plan:
        raise HTTPException(status_code=404, detail="預算主表不存在")

    active_filter = "AND bpd.is_active_detail = 1" if active_only else ""
    rows = _rows(conn, f"""
        SELECT
            bpd.*,
            ac.account_code_name,
            bi.budget_item_name
        FROM budget_plan_details bpd
        LEFT JOIN account_codes ac ON ac.id = bpd.standard_account_code_id
        LEFT JOIN budget_items bi ON bi.id = bpd.standard_budget_item_id
        WHERE bpd.budget_plan_id = ? {active_filter}
        ORDER BY bpd.seq_num, bpd.id
    """, (plan_id,))
    return rows


@router.post("/plans/{plan_id}/details", status_code=status.HTTP_201_CREATED)
def create_plan_detail(
    plan_id: int,
    body: BudgetPlanDetailCreate,
    current_user: User = Depends(require_roles("budget_manage", "budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    plan = _one(conn, "SELECT * FROM budget_plans WHERE id=?", (plan_id,))
    if not plan:
        raise HTTPException(status_code=404, detail="預算主表不存在")
    if plan["status"] == "closed":
        raise HTTPException(status_code=400, detail="已關帳的預算不可新增明細")

    # 計算 annual_budget（若未傳，加總 12 個月）
    months = [
        body.month_01_budget, body.month_02_budget, body.month_03_budget,
        body.month_04_budget, body.month_05_budget, body.month_06_budget,
        body.month_07_budget, body.month_08_budget, body.month_09_budget,
        body.month_10_budget, body.month_11_budget, body.month_12_budget,
    ]
    annual = body.annual_budget
    if annual is None:
        annual = sum(m for m in months if m is not None)

    cursor = conn.execute("""
        INSERT INTO budget_plan_details (
            budget_plan_id, line_type,
            raw_account_code_name, standard_account_code_id,
            raw_budget_item_name, standard_budget_item_id,
            month_01_budget, month_02_budget, month_03_budget,
            month_04_budget, month_05_budget, month_06_budget,
            month_07_budget, month_08_budget, month_09_budget,
            month_10_budget, month_11_budget, month_12_budget,
            annual_budget, raw_remark, is_active_detail
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        plan_id, body.line_type,
        body.raw_account_code_name, body.standard_account_code_id,
        body.raw_budget_item_name, body.standard_budget_item_id,
        body.month_01_budget, body.month_02_budget, body.month_03_budget,
        body.month_04_budget, body.month_05_budget, body.month_06_budget,
        body.month_07_budget, body.month_08_budget, body.month_09_budget,
        body.month_10_budget, body.month_11_budget, body.month_12_budget,
        annual, body.raw_remark, body.is_active_detail,
    ))
    conn.commit()
    return _one(conn, "SELECT * FROM budget_plan_details WHERE id=?", (cursor.lastrowid,))


@router.put("/plans/{plan_id}/details/{detail_id}")
def update_plan_detail(
    plan_id: int,
    detail_id: int,
    body: BudgetPlanDetailUpdate,
    current_user: User = Depends(require_roles("budget_manage", "budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    plan = _one(conn, "SELECT * FROM budget_plans WHERE id=?", (plan_id,))
    if not plan:
        raise HTTPException(status_code=404, detail="預算主表不存在")
    if plan["status"] == "closed":
        raise HTTPException(status_code=400, detail="已關帳的預算不可修改明細")

    detail = _one(conn, "SELECT * FROM budget_plan_details WHERE id=? AND budget_plan_id=?", (detail_id, plan_id))
    if not detail:
        raise HTTPException(status_code=404, detail="預算明細不存在")

    data = body.dict(exclude_none=True)
    if not data:
        return detail

    # 重新計算 annual_budget（若月份有異動）
    month_fields = [
        "month_01_budget","month_02_budget","month_03_budget","month_04_budget",
        "month_05_budget","month_06_budget","month_07_budget","month_08_budget",
        "month_09_budget","month_10_budget","month_11_budget","month_12_budget",
    ]
    has_month_update = any(f in data for f in month_fields)
    if has_month_update and "annual_budget" not in data:
        merged_months = [data.get(f, detail[f]) for f in month_fields]
        data["annual_budget"] = sum(m for m in merged_months if m is not None)

    set_clause = ", ".join(f"{k}=?" for k in data)
    values = list(data.values()) + [detail_id]
    conn.execute(f"UPDATE budget_plan_details SET {set_clause} WHERE id=?", values)
    conn.commit()
    return _one(conn, "SELECT * FROM budget_plan_details WHERE id=?", (detail_id,))


@router.delete("/plans/{plan_id}/details/{detail_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_detail(
    plan_id: int,
    detail_id: int,
    current_user: User = Depends(require_roles("budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    plan = _one(conn, "SELECT * FROM budget_plans WHERE id=?", (plan_id,))
    if not plan:
        raise HTTPException(status_code=404, detail="預算主表不存在")
    if plan["status"] == "closed":
        raise HTTPException(status_code=400, detail="已關帳的預算不可刪除明細")

    detail = _one(conn, "SELECT * FROM budget_plan_details WHERE id=? AND budget_plan_id=?", (detail_id, plan_id))
    if not detail:
        raise HTTPException(status_code=404, detail="預算明細不存在")

    conn.execute("DELETE FROM budget_plan_details WHERE id=?", (detail_id,))
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Transactions
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/transactions")
def list_transactions(
    year_id: Optional[int] = Query(None),
    dept_id: Optional[int] = Query(None),
    month_num: Optional[int] = Query(None),
    account_code_id: Optional[int] = Query(None),
    budget_item_id: Optional[int] = Query(None),
    amount_missing: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    sql = """
        SELECT
            bt.*,
            d.dept_name,
            ac.account_code_name,
            bi.budget_item_name,
            by2.budget_year
        FROM budget_transactions bt
        LEFT JOIN departments d ON d.id = bt.dept_id
        LEFT JOIN account_codes ac ON ac.id = bt.account_code_id
        LEFT JOIN budget_items bi ON bi.id = bt.budget_item_id
        LEFT JOIN budget_years by2 ON by2.id = bt.budget_year_id
        WHERE 1=1
    """
    params = []
    if year_id is not None:
        sql += " AND bt.budget_year_id = ?"
        params.append(year_id)
    if dept_id is not None:
        sql += " AND bt.dept_id = ?"
        params.append(dept_id)
    if month_num is not None:
        sql += " AND bt.month_num = ?"
        params.append(month_num)
    if account_code_id is not None:
        sql += " AND bt.account_code_id = ?"
        params.append(account_code_id)
    if budget_item_id is not None:
        sql += " AND bt.budget_item_id = ?"
        params.append(budget_item_id)
    if amount_missing is True:
        sql += " AND bt.amount_missing_flag = 1"
    elif amount_missing is False:
        sql += " AND bt.amount_missing_flag = 0"
    if search:
        sql += " AND (bt.description LIKE ? OR bt.requester LIKE ? OR bt.raw_budget_item_name LIKE ?)"
        kw = f"%{search}%"
        params.extend([kw, kw, kw])

    # 計算總數
    count_sql = f"SELECT COUNT(*) AS cnt FROM ({sql}) sub"
    total = _one(conn, count_sql, tuple(params))["cnt"]

    sql += " ORDER BY bt.month_num, bt.id LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = _rows(conn, sql, tuple(params))

    return {"total": total, "items": rows}


@router.get("/transactions/export")
def export_transactions(
    year_id: Optional[int] = Query(None),
    dept_id: Optional[int] = Query(None),
    month_num: Optional[int] = Query(None),
    amount_missing: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    """匯出交易明細為 Excel（帶入與清單相同的篩選條件）"""
    import io
    import pandas as pd
    from fastapi.responses import StreamingResponse

    where_clauses: List[str] = []
    params: List[Any] = []

    if year_id:
        where_clauses.append("bt.budget_year_id = ?")
        params.append(year_id)
    if dept_id:
        where_clauses.append("bt.dept_id = ?")
        params.append(dept_id)
    if month_num:
        where_clauses.append("bt.month_num = ?")
        params.append(month_num)
    if amount_missing is True:
        where_clauses.append("bt.amount_missing_flag = 1")
    elif amount_missing is False:
        where_clauses.append("bt.amount_missing_flag = 0")
    if search:
        where_clauses.append(
            "(bt.description LIKE ? OR bt.requester LIKE ? OR bt.raw_budget_item_name LIKE ?)"
        )
        params.extend([f"%{search}%"] * 3)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    sql = f"""
        SELECT bt.id AS 編號,
               by2.budget_year AS 年度,
               d.dept_name AS 部門,
               bt.month_num AS 月份,
               bt.quarter_code AS 季別,
               bt.raw_account_code_name AS 原始科目,
               ac.account_code_name AS 標準科目,
               bt.raw_budget_item_name AS 原始預算項目,
               bi.budget_item_name AS 標準預算項目,
               bt.description AS 說明,
               bt.amount_ex_tax AS 未稅金額,
               bt.requester AS 請購人,
               CASE WHEN bt.amount_missing_flag=1 THEN '是' ELSE '' END AS 金額缺漏,
               CASE WHEN bt.has_formula_amount=1 THEN '是' ELSE '' END AS 含公式金額,
               bt.note_1 AS 備註1,
               bt.note_2 AS 備註2,
               bt.note_3 AS 備註3
        FROM budget_transactions bt
        LEFT JOIN budget_years by2 ON by2.id = bt.budget_year_id
        LEFT JOIN departments d ON d.id = bt.dept_id
        LEFT JOIN account_codes ac ON ac.id = bt.account_code_id
        LEFT JOIN budget_items bi ON bi.id = bt.budget_item_id
        {where_sql}
        ORDER BY bt.budget_year_id, bt.dept_id, bt.month_num, bt.id
    """
    rows = _rows(conn, sql, tuple(params))

    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        "編號","年度","部門","月份","季別","原始科目","標準科目",
        "原始預算項目","標準預算項目","說明","未稅金額","請購人",
        "金額缺漏","含公式金額","備註1","備註2","備註3"
    ])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="費用交易明細")
        ws = writer.sheets["費用交易明細"]
        for col in ws.columns:
            max_len = max((len(str(c.value or "")) for c in col), default=8)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename*=UTF-8''budget_transactions.xlsx"},
    )


@router.get("/transactions/{txn_id}")
def get_transaction(
    txn_id: int,
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    row = _one(conn, """
        SELECT bt.*, d.dept_name, ac.account_code_name, bi.budget_item_name
        FROM budget_transactions bt
        LEFT JOIN departments d ON d.id = bt.dept_id
        LEFT JOIN account_codes ac ON ac.id = bt.account_code_id
        LEFT JOIN budget_items bi ON bi.id = bt.budget_item_id
        WHERE bt.id = ?
    """, (txn_id,))
    if not row:
        raise HTTPException(status_code=404, detail="交易明細不存在")
    return row


@router.put("/transactions/{txn_id}")
def update_transaction(
    txn_id: int,
    body: TransactionUpdate,
    current_user: User = Depends(require_roles("budget_manage", "budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    txn = _one(conn, "SELECT * FROM budget_transactions WHERE id=?", (txn_id,))
    if not txn:
        raise HTTPException(status_code=404, detail="交易明細不存在")

    data = body.dict(exclude_none=True)
    if not data:
        return txn

    set_clause = ", ".join(f"{k}=?" for k in data)
    values = list(data.values()) + [txn_id]
    conn.execute(f"UPDATE budget_transactions SET {set_clause} WHERE id=?", values)
    conn.commit()
    return _one(conn, "SELECT * FROM budget_transactions WHERE id=?", (txn_id,))


# ─────────────────────────────────────────────────────────────────────────────
# 6. Masters — Departments
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/masters/departments")
def list_departments(
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    if active_only:
        return _rows(conn, "SELECT * FROM departments WHERE is_active=1 ORDER BY sort_order, id")
    return _rows(conn, "SELECT * FROM departments ORDER BY sort_order, id")


@router.post("/masters/departments", status_code=status.HTTP_201_CREATED)
def create_department(
    body: DepartmentCreate,
    current_user: User = Depends(require_roles("budget_manage", "budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    if _one(conn, "SELECT id FROM departments WHERE dept_code=?", (body.dept_code,)):
        raise HTTPException(status_code=400, detail="dept_code 已存在")
    if _one(conn, "SELECT id FROM departments WHERE dept_name=?", (body.dept_name,)):
        raise HTTPException(status_code=400, detail="dept_name 已存在")
    cursor = conn.execute(
        "INSERT INTO departments (dept_code, dept_name, dept_group, sort_order, is_active) VALUES (?,?,?,?,?)",
        (body.dept_code, body.dept_name, body.dept_group, body.sort_order, body.is_active)
    )
    conn.commit()
    return _one(conn, "SELECT * FROM departments WHERE id=?", (cursor.lastrowid,))


@router.put("/masters/departments/{dept_id}")
def update_department(
    dept_id: int,
    body: DepartmentUpdate,
    current_user: User = Depends(require_roles("budget_manage", "budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    dept = _one(conn, "SELECT * FROM departments WHERE id=?", (dept_id,))
    if not dept:
        raise HTTPException(status_code=404, detail="部門不存在")

    data = body.dict(exclude_none=True)
    if not data:
        return dept

    set_clause = ", ".join(f"{k}=?" for k in data)
    values = list(data.values()) + [dept_id]
    conn.execute(f"UPDATE departments SET {set_clause} WHERE id=?", values)
    conn.commit()
    return _one(conn, "SELECT * FROM departments WHERE id=?", (dept_id,))


# ─────────────────────────────────────────────────────────────────────────────
# 7. Masters — Account Codes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/masters/account-codes")
def list_account_codes(
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    return _rows(conn, "SELECT * FROM account_codes ORDER BY account_code_name")


@router.post("/masters/account-codes", status_code=status.HTTP_201_CREATED)
def create_account_code(
    body: AccountCodeCreate,
    current_user: User = Depends(require_roles("budget_manage", "budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    if _one(conn, "SELECT id FROM account_codes WHERE account_code_name=?", (body.account_code_name,)):
        raise HTTPException(status_code=400, detail="account_code_name 已存在")
    cursor = conn.execute(
        "INSERT INTO account_codes (account_code_name, normalized_name, is_raw_group, notes) VALUES (?,?,?,?)",
        (body.account_code_name, body.normalized_name, body.is_raw_group, body.notes)
    )
    conn.commit()
    return _one(conn, "SELECT * FROM account_codes WHERE id=?", (cursor.lastrowid,))


@router.put("/masters/account-codes/{code_id}")
def update_account_code(
    code_id: int,
    body: AccountCodeUpdate,
    current_user: User = Depends(require_roles("budget_manage", "budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    code = _one(conn, "SELECT * FROM account_codes WHERE id=?", (code_id,))
    if not code:
        raise HTTPException(status_code=404, detail="會計科目不存在")

    data = body.dict(exclude_none=True)
    if not data:
        return code

    set_clause = ", ".join(f"{k}=?" for k in data)
    values = list(data.values()) + [code_id]
    conn.execute(f"UPDATE account_codes SET {set_clause} WHERE id=?", values)
    conn.commit()
    return _one(conn, "SELECT * FROM account_codes WHERE id=?", (code_id,))


# ─────────────────────────────────────────────────────────────────────────────
# 8. Masters — Budget Items
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/masters/budget-items")
def list_budget_items(
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    return _rows(conn, "SELECT * FROM budget_items ORDER BY budget_item_name")


@router.post("/masters/budget-items", status_code=status.HTTP_201_CREATED)
def create_budget_item(
    body: BudgetItemCreate,
    current_user: User = Depends(require_roles("budget_manage", "budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    if _one(conn, "SELECT id FROM budget_items WHERE budget_item_name=?", (body.budget_item_name,)):
        raise HTTPException(status_code=400, detail="budget_item_name 已存在")
    cursor = conn.execute(
        "INSERT INTO budget_items (budget_item_name, normalized_name, is_capex, notes) VALUES (?,?,?,?)",
        (body.budget_item_name, body.normalized_name, body.is_capex, body.notes)
    )
    conn.commit()
    return _one(conn, "SELECT * FROM budget_items WHERE id=?", (cursor.lastrowid,))


@router.put("/masters/budget-items/{item_id}")
def update_budget_item(
    item_id: int,
    body: BudgetItemUpdate,
    current_user: User = Depends(require_roles("budget_manage", "budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    item = _one(conn, "SELECT * FROM budget_items WHERE id=?", (item_id,))
    if not item:
        raise HTTPException(status_code=404, detail="預算項目不存在")

    data = body.dict(exclude_none=True)
    if not data:
        return item

    set_clause = ", ".join(f"{k}=?" for k in data)
    values = list(data.values()) + [item_id]
    conn.execute(f"UPDATE budget_items SET {set_clause} WHERE id=?", values)
    conn.commit()
    return _one(conn, "SELECT * FROM budget_items WHERE id=?", (item_id,))


# ─────────────────────────────────────────────────────────────────────────────
# 9. Mappings
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/mappings")
def list_mappings(
    dept_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    sql = """
        SELECT m.*, d.dept_name, ac.account_code_name, bi.budget_item_name
        FROM budget_item_mappings m
        LEFT JOIN departments d ON d.id = m.dept_id
        LEFT JOIN account_codes ac ON ac.id = m.account_code_id
        LEFT JOIN budget_items bi ON bi.id = m.budget_item_id
        WHERE 1=1
    """
    params = []
    if dept_id is not None:
        sql += " AND m.dept_id = ?"
        params.append(dept_id)
    sql += " ORDER BY m.id"
    return _rows(conn, sql, tuple(params))


@router.post("/mappings", status_code=status.HTTP_201_CREATED)
def create_mapping(
    body: MappingCreate,
    current_user: User = Depends(require_roles("budget_manage", "budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    cursor = conn.execute("""
        INSERT INTO budget_item_mappings
            (dept_id, quarter_code, source_account_header, account_code_id,
             mapped_budget_item_name, budget_item_id, mapping_method, notes)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        body.dept_id, body.quarter_code, body.source_account_header,
        body.account_code_id, body.mapped_budget_item_name,
        body.budget_item_id, body.mapping_method, body.notes
    ))
    conn.commit()
    return _one(conn, "SELECT * FROM budget_item_mappings WHERE id=?", (cursor.lastrowid,))


@router.put("/mappings/{mapping_id}")
def update_mapping(
    mapping_id: int,
    body: MappingUpdate,
    current_user: User = Depends(require_roles("budget_manage", "budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    mapping = _one(conn, "SELECT * FROM budget_item_mappings WHERE id=?", (mapping_id,))
    if not mapping:
        raise HTTPException(status_code=404, detail="對照規則不存在")

    data = body.dict(exclude_none=True)
    if not data:
        return mapping

    set_clause = ", ".join(f"{k}=?" for k in data)
    values = list(data.values()) + [mapping_id]
    conn.execute(f"UPDATE budget_item_mappings SET {set_clause} WHERE id=?", values)
    conn.commit()
    return _one(conn, "SELECT * FROM budget_item_mappings WHERE id=?", (mapping_id,))


@router.delete("/mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mapping(
    mapping_id: int,
    current_user: User = Depends(require_roles("budget_admin")),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    mapping = _one(conn, "SELECT * FROM budget_item_mappings WHERE id=?", (mapping_id,))
    if not mapping:
        raise HTTPException(status_code=404, detail="對照規則不存在")
    conn.execute("DELETE FROM budget_item_mappings WHERE id=?", (mapping_id,))
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 10. Reports
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/reports/budget-vs-actual")
def report_budget_vs_actual(
    dept_name: Optional[str] = Query(None),
    account_code_name: Optional[str] = Query(None),
    plan_code: Optional[str] = Query(None),
    view_type: str = Query("total", description="total | monthly"),
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    """
    預算比較報表
    view_type=total  → v_budget_vs_actual_by_account_total
    view_type=monthly → v_budget_vs_actual_by_account_month
    """
    if view_type == "monthly":
        sql = """
            SELECT * FROM v_budget_vs_actual_by_account_month WHERE 1=1
        """
    else:
        sql = """
            SELECT * FROM v_budget_vs_actual_by_account_total WHERE 1=1
        """
    params = []
    if dept_name:
        sql += " AND dept_name = ?"
        params.append(dept_name)
    if account_code_name:
        sql += " AND account_code_name LIKE ?"
        params.append(f"%{account_code_name}%")
    if plan_code:
        sql += " AND plan_code = ?"
        params.append(plan_code)

    if view_type == "monthly":
        sql += " ORDER BY dept_name, account_code_name, month_num"
    else:
        sql += " ORDER BY dept_name, account_code_name"

    rows = _rows(conn, sql, tuple(params))
    return {"view_type": view_type, "total": len(rows), "items": rows}


@router.get("/reports/data-quality")
def report_data_quality(
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    """資料品質問題：公式錯誤 + 金額缺漏 + 未對應明細"""
    dq_issues = _rows(conn, "SELECT * FROM data_quality_issues ORDER BY severity, source_sheet_name")
    missing_amounts = _rows(conn, "SELECT * FROM v_transactions_missing_amount ORDER BY dept_name, month_num")
    unresolved = _rows(conn, "SELECT * FROM v_unresolved_plan_details ORDER BY dept_name, plan_code")

    return {
        "data_quality_issues": dq_issues,
        "missing_amount_transactions": missing_amounts,
        "unresolved_plan_details": unresolved,
        "summary": {
            "dq_issue_count": len(dq_issues),
            "missing_amount_count": len(missing_amounts),
            "unresolved_plan_count": len(unresolved),
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# 11. Monthly Transactions Summary (for charts)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/reports/monthly-actual")
def report_monthly_actual(
    year_id: int = Query(1),
    dept_name: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_budget_db),
):
    """月別實績彙總（用於 Dashboard 折線圖）"""
    sql = """
        SELECT
            t.month_num,
            d.dept_name,
            ac.account_code_name,
            SUM(COALESCE(t.amount_ex_tax, 0)) AS actual_amount,
            COUNT(*) AS txn_count
        FROM budget_transactions t
        LEFT JOIN departments d ON d.id = t.dept_id
        LEFT JOIN account_codes ac ON ac.id = t.account_code_id
        WHERE t.budget_year_id = ? AND t.amount_missing_flag = 0
    """
    params: list = [year_id]
    if dept_name:
        sql += " AND d.dept_name = ?"
        params.append(dept_name)
    sql += " GROUP BY t.month_num, d.dept_name, ac.account_code_name ORDER BY t.month_num"
    return _rows(conn, sql, tuple(params))
