"""庫存管理：使用者可見公司（後端強制）— 比照週採 cycle_purchase_company_scope（方案 B）

權限鍵 stock_company_<代碼小寫>（stock_company_ch／ou／ho）在角色設定勾選；
使用者可見公司＝其所有角色這類權限的聯集；系統管理員（"*"）可見全部啟用公司。
請求以查詢參數 `co` 指定公司；不在可見範圍一律 403；單筆跨公司一律 404。
與週採的可見公司權限分開：會看庫存的人不一定有週採權限。
"""
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.core.database import get_db
from app.dependencies import get_current_user, get_user_permissions
from app.services.cycle_purchase_company_scope import all_active_codes, resolve_company_code

STOCK_COMPANY_PREFIX = "stock_company_"
DEFAULT_COMPANY_CODE = "CH"


@dataclass(frozen=True)
class StockContext:
    codes: frozenset
    code: str
    is_admin: bool
    user_name: str
    user_id: str = ""                       # Phase 4：領用單資料範圍（所屬部門）
    perms: frozenset = frozenset()          # Phase 4：同一請求內判斷權限，不用再查 DB

    def has(self, key: str) -> bool:
        return self.is_admin or key in self.perms


def stock_codes_from_perms(perms, cp_db: Session) -> frozenset:
    out = set()
    for key in perms:
        if key.startswith(STOCK_COMPANY_PREFIX):
            code = key[len(STOCK_COMPANY_PREFIX):].upper()
            if resolve_company_code(cp_db, code):
                out.add(code)
    return frozenset(out)


def stock_context(
    co: Optional[str] = Query(None, description="公司代碼（CH／OU／HO）；未帶則預設第一個可見公司"),
    current_user=Depends(get_current_user),
    main_db: Session = Depends(get_db),
    cp_db: Session = Depends(get_cycle_purchase_db),
) -> StockContext:
    perms = get_user_permissions(current_user.id, main_db)
    is_admin = "*" in perms
    codes = all_active_codes(cp_db) if is_admin else stock_codes_from_perms(perms, cp_db)
    if not codes:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="尚未指派任何庫存可見公司（請於角色設定勾選「庫存可見公司」）")
    if co is None or not co.strip():
        code = DEFAULT_COMPANY_CODE if DEFAULT_COMPANY_CODE in codes else sorted(codes)[0]
    else:
        code = resolve_company_code(cp_db, co)
        if code is None or code not in codes:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="無此公司別的庫存權限")
    name = getattr(current_user, "full_name", None) or getattr(current_user, "email", "") or ""
    return StockContext(codes=codes, code=code, is_admin=is_admin, user_name=name,
                        user_id=str(current_user.id), perms=frozenset(perms))
