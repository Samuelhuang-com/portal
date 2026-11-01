"""週採多公司隔離：公司代碼解析與使用者可見公司（後端強制）

- 公司代碼以週採庫 cycle_purchase_companies 為準（CH 春大直／OU 日曜／HO 台中）。
- 可見公司由「角色權限」決定（2026-11 改版，方案 B）：
    權限鍵 cycle_purchase_company_<代碼小寫> 在角色設定中勾選，使用者可見的公司
    = 其所有角色的這類權限聯集。系統管理員（權限 "*"）可見全部啟用公司。
- 部門歸屬不再決定「看得到什麼」，只決定「能不能編輯」（部門成員 OR 承辦人）。
- 請求公司以查詢參數 `co` 指定（未帶則預設 CH，或使用者第一個可見公司）。
  `co` 不在可見範圍內一律 403；單筆跨公司一律 404。
"""
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.core.database import get_db
from app.dependencies import get_current_user, get_user_permissions
from app.models.cycle_purchase_company import CyclePurchaseCompany

DEFAULT_COMPANY_CODE = "CH"
COMPANY_PERM_PREFIX = "cycle_purchase_company_"

# 既有字串（含歷史別名）→ 公司代碼。與 alembic_cp 的 cpco1 一致。
ALIAS_TO_CODE = {
    "春大直": "CH", "樂群": "CH",
    "日曜": "OU", "日曜天地": "OU", "日耀": "OU", "自由": "OU",
    "台中": "HO", "智選": "HO",
}


@dataclass(frozen=True)
class CompanyContext:
    codes: frozenset      # 使用者可見的公司代碼
    code: str             # 本次請求選定的公司代碼（已通過可見性檢查）
    is_admin: bool


def resolve_company_code(cp_db: Session, value: Optional[str]) -> Optional[str]:
    """代碼或名稱 → 公司代碼（僅回傳存在且啟用的公司）；無法解析回 None。"""
    v = (value or "").strip()
    if not v:
        return None
    row = (cp_db.query(CyclePurchaseCompany)
           .filter(CyclePurchaseCompany.code == v.upper()).first())
    if row is None:
        row = (cp_db.query(CyclePurchaseCompany)
               .filter(CyclePurchaseCompany.name == v).first())
    if row is None:
        code = ALIAS_TO_CODE.get(v)
        if code:
            row = (cp_db.query(CyclePurchaseCompany)
                   .filter(CyclePurchaseCompany.code == code).first())
    if row is None or not row.is_active:
        return None
    return row.code


def require_company_code(cp_db: Session, value: Optional[str]) -> str:
    """服務層用：無法解析即丟 ValueError（路由轉 400）。"""
    code = resolve_company_code(cp_db, value)
    if code is None:
        raise ValueError(f"無法辨識的公司別：{value!r}")
    return code


def company_codes_from_perms(perms, cp_db: Session) -> frozenset:
    """由權限清單取出可見公司：cycle_purchase_company_<code> → CODE（須為啟用的公司）。"""
    out = set()
    for key in perms:
        if key.startswith(COMPANY_PERM_PREFIX):
            code = key[len(COMPANY_PERM_PREFIX):].upper()
            if resolve_company_code(cp_db, code):
                out.add(code)
    return frozenset(out)


def all_active_codes(cp_db: Session) -> frozenset:
    return frozenset(
        c for (c,) in cp_db.query(CyclePurchaseCompany.code)
        .filter(CyclePurchaseCompany.is_active.is_(True)).all()
    )


def visible_codes_for_user(main_db: Session, cp_db: Session, user) -> frozenset:
    """使用者可見公司（依其角色權限；系統管理員＝全部）。"""
    perms = get_user_permissions(user.id, main_db)
    if "*" in perms:
        return all_active_codes(cp_db)
    return company_codes_from_perms(perms, cp_db)


def company_context(
    co: Optional[str] = Query(None, description="公司代碼（CH／OU／HO）；未帶則預設 CH"),
    current_user=Depends(get_current_user),
    main_db: Session = Depends(get_db),
    cp_db: Session = Depends(get_cycle_purchase_db),
) -> CompanyContext:
    perms = get_user_permissions(current_user.id, main_db)
    is_admin = "*" in perms
    codes = all_active_codes(cp_db) if is_admin else company_codes_from_perms(perms, cp_db)
    if not codes:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="尚未指派任何可見公司（請於角色設定勾選）")

    if co is None or not co.strip():
        code = DEFAULT_COMPANY_CODE if DEFAULT_COMPANY_CODE in codes else sorted(codes)[0]
    else:
        code = resolve_company_code(cp_db, co)
        if code is None or code not in codes:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="無此公司別的權限")
    return CompanyContext(codes=codes, code=code, is_admin=is_admin)


def assert_visible(ctx: CompanyContext, company_code: str) -> None:
    """單筆資料的公司代碼必須在可見範圍內，否則 404（不洩漏存在與否）。"""
    if company_code not in ctx.codes:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="找不到資料")


def assert_company_visible_by_name(cp_db: Session, ctx: CompanyContext, company_name: Optional[str]) -> str:
    """POST 流程：payload 的公司字串（或代碼）必須可解析且在可見範圍內，回傳代碼。"""
    code = resolve_company_code(cp_db, company_name)
    if code is None or code not in ctx.codes:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="無此公司別的權限")
    return code


def assert_requests_visible(cp_db: Session, ctx: CompanyContext, request_ids) -> None:
    """依請購單 id 清單檢查全部在可見範圍內；任一不符回 404。"""
    from app.models.cycle_purchase_request import CyclePurchaseRequest
    ids = list(request_ids or [])
    if not ids:
        return
    rows = cp_db.query(CyclePurchaseRequest.id, CyclePurchaseRequest.company_code).filter(
        CyclePurchaseRequest.id.in_(ids)).all()
    found = {r.id: r.company_code for r in rows}
    if len(found) != len(set(ids)) or any(c not in ctx.codes for c in found.values()):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="找不到請購單")


# 路徑參數 → 資料表。資料表名稱只來自這裡的常數，不接受外部輸入。
PATH_PARAM_TABLES = {
    "item_id": "cycle_purchase_items",
    "po_id": "cycle_purchase_pos",
    "receiving_id": "cycle_purchase_receiving",
    "payment_id": "cycle_purchase_payments",
    "request_id": "cycle_purchase_requests",
    "source_request_id": "cycle_purchase_requests",
    "summary_id": "cycle_purchase_summary",
    "vendor_id": "cycle_purchase_vendors",
    "dept_id": "cycle_purchase_departments",
    "cc_id": "cycle_purchase_cost_centers",
    "ac_id": "cycle_purchase_account_codes",
    "category_id": "cycle_purchase_categories",
}


def assert_row_visible(cp_db: Session, ctx: CompanyContext, table: str, pk) -> None:
    """單筆資料：不存在或不屬於可見公司一律 404（不洩漏存在與否）。"""
    from sqlalchemy import text
    if table not in set(PATH_PARAM_TABLES.values()):
        raise ValueError(f"未登記的資料表：{table}")
    row = cp_db.execute(text(f"SELECT company_code FROM {table} WHERE id = :pk"), {"pk": pk}).first()
    if row is None or row[0] not in ctx.codes:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="找不到資料")
