"""
合約管理系統 - 自訂例外定義

所有業務邏輯例外集中定義在此，由 router 層轉換為 HTTPException 回傳給前端。
遵循 Portal 統一的錯誤處理模式。
"""

from typing import Optional, Any


class ContractManagementException(Exception):
    """合約管理系統基底例外類別"""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# ─────────────────────────────────────────────────────────────────────────────
# 合約相關例外
# ─────────────────────────────────────────────────────────────────────────────

class ContractNotFound(ContractManagementException):
    """合約不存在"""

    def __init__(self, contract_id: str):
        super().__init__(
            message=f"合約 {contract_id} 不存在",
            error_code="CONTRACT_NOT_FOUND",
            status_code=404,
            details={"contract_id": contract_id},
        )


class ContractAlreadyExists(ContractManagementException):
    """合約編號已存在"""

    def __init__(self, contract_id: str):
        super().__init__(
            message=f"合約編號 {contract_id} 已存在",
            error_code="CONTRACT_ALREADY_EXISTS",
            status_code=409,
            details={"contract_id": contract_id},
        )


class InvalidContractDates(ContractManagementException):
    """合約日期無效"""

    def __init__(self, start_date: str, end_date: str, reason: str = "開始日期必須早於結束日期"):
        super().__init__(
            message=f"合約日期無效：{reason}（起日: {start_date}, 迄日: {end_date}）",
            error_code="INVALID_CONTRACT_DATES",
            status_code=400,
            details={
                "start_date": start_date,
                "end_date": end_date,
                "reason": reason,
            },
        )


class ContractVendorNotFound(ContractManagementException):
    """合約指定的廠商不存在"""

    def __init__(self, vendor_id: str):
        super().__init__(
            message=f"廠商 {vendor_id} 不存在，無法建立合約",
            error_code="CONTRACT_VENDOR_NOT_FOUND",
            status_code=400,
            details={"vendor_id": vendor_id},
        )


class ContractBudgetCategoryNotFound(ContractManagementException):
    """合約指定的預算科目不存在或停用"""

    def __init__(self, budget_year: int, category_l1: str, category_l2: str):
        super().__init__(
            message=f"預算科目不存在或停用（{budget_year} / {category_l1} / {category_l2}）",
            error_code="CONTRACT_BUDGET_CATEGORY_NOT_FOUND",
            status_code=400,
            details={
                "budget_year": budget_year,
                "category_l1": category_l1,
                "category_l2": category_l2,
            },
        )


class InvalidContractAmount(ContractManagementException):
    """合約金額無效"""

    def __init__(self, amount: float, reason: str = "金額必須大於 0"):
        super().__init__(
            message=f"合約金額無效：{reason}（金額: {amount}）",
            error_code="INVALID_CONTRACT_AMOUNT",
            status_code=400,
            details={
                "amount": amount,
                "reason": reason,
            },
        )


class ContractHasItems(ContractManagementException):
    """合約包含明細項目，無法刪除"""

    def __init__(self, contract_id: str, item_count: int):
        super().__init__(
            message=f"合約 {contract_id} 包含 {item_count} 項明細，無法刪除",
            error_code="CONTRACT_HAS_ITEMS",
            status_code=400,
            details={
                "contract_id": contract_id,
                "item_count": item_count,
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# 合約明細相關例外
# ─────────────────────────────────────────────────────────────────────────────

class ContractItemNotFound(ContractManagementException):
    """合約明細項目不存在"""

    def __init__(self, contract_id: str, item_id: int):
        super().__init__(
            message=f"合約 {contract_id} 的明細項目 {item_id} 不存在",
            error_code="CONTRACT_ITEM_NOT_FOUND",
            status_code=404,
            details={
                "contract_id": contract_id,
                "item_id": item_id,
            },
        )


class InvalidContractItemAmount(ContractManagementException):
    """合約明細金額無效"""

    def __init__(self, item_seq: int, reason: str = "未稅金額或含稅金額必須大於 0"):
        super().__init__(
            message=f"第 {item_seq} 項明細金額無效：{reason}",
            error_code="INVALID_CONTRACT_ITEM_AMOUNT",
            status_code=400,
            details={
                "item_seq": item_seq,
                "reason": reason,
            },
        )


class DuplicateContractItemSeq(ContractManagementException):
    """合約明細項次重複"""

    def __init__(self, contract_id: str, item_seq: int):
        super().__init__(
            message=f"合約 {contract_id} 的項次 {item_seq} 已存在",
            error_code="DUPLICATE_CONTRACT_ITEM_SEQ",
            status_code=400,
            details={
                "contract_id": contract_id,
                "item_seq": item_seq,
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# 廠商相關例外
# ─────────────────────────────────────────────────────────────────────────────

class VendorNotFound(ContractManagementException):
    """廠商不存在"""

    def __init__(self, vendor_id: str):
        super().__init__(
            message=f"廠商 {vendor_id} 不存在",
            error_code="VENDOR_NOT_FOUND",
            status_code=404,
            details={"vendor_id": vendor_id},
        )


class VendorAlreadyExists(ContractManagementException):
    """廠商編號或名稱已存在"""

    def __init__(self, vendor_id: str = None, vendor_name: str = None):
        if vendor_id:
            message = f"廠商編號 {vendor_id} 已存在"
            details = {"vendor_id": vendor_id}
        else:
            message = f"廠商名稱 {vendor_name} 已存在"
            details = {"vendor_name": vendor_name}

        super().__init__(
            message=message,
            error_code="VENDOR_ALREADY_EXISTS",
            status_code=409,
            details=details,
        )


class VendorCannotDelete(ContractManagementException):
    """廠商有關聯的合約，無法刪除"""

    def __init__(self, vendor_id: str, contract_count: int):
        super().__init__(
            message=f"廠商 {vendor_id} 有 {contract_count} 份合約，無法刪除",
            error_code="VENDOR_CANNOT_DELETE",
            status_code=400,
            details={
                "vendor_id": vendor_id,
                "contract_count": contract_count,
            },
        )


class InvalidVendorData(ContractManagementException):
    """廠商資料無效"""

    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"廠商欄位 {field} 無效：{reason}",
            error_code="INVALID_VENDOR_DATA",
            status_code=400,
            details={
                "field": field,
                "reason": reason,
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# 預算科目相關例外
# ─────────────────────────────────────────────────────────────────────────────

class BudgetCategoryNotFound(ContractManagementException):
    """預算科目不存在"""

    def __init__(self, budget_year: int, category_l1: str, category_l2: str = None):
        if category_l2:
            message = f"預算科目不存在（{budget_year} / {category_l1} / {category_l2}）"
            details = {
                "budget_year": budget_year,
                "category_l1": category_l1,
                "category_l2": category_l2,
            }
        else:
            message = f"預算大項不存在（{budget_year} / {category_l1}）"
            details = {
                "budget_year": budget_year,
                "category_l1": category_l1,
            }

        super().__init__(
            message=message,
            error_code="BUDGET_CATEGORY_NOT_FOUND",
            status_code=404,
            details=details,
        )


class BudgetCategoryDisabled(ContractManagementException):
    """預算科目已停用"""

    def __init__(self, budget_year: int, category_l1: str, category_l2: str):
        super().__init__(
            message=f"預算科目已停用（{budget_year} / {category_l1} / {category_l2}）",
            error_code="BUDGET_CATEGORY_DISABLED",
            status_code=400,
            details={
                "budget_year": budget_year,
                "category_l1": category_l1,
                "category_l2": category_l2,
            },
        )


class DuplicateBudgetCategory(ContractManagementException):
    """預算科目重複"""

    def __init__(self, budget_year: int, category_l1: str, category_l2: str, dept: str):
        super().__init__(
            message=f"預算科目已存在（{budget_year} / {category_l1} / {category_l2} / {dept}）",
            error_code="DUPLICATE_BUDGET_CATEGORY",
            status_code=409,
            details={
                "budget_year": budget_year,
                "category_l1": category_l1,
                "category_l2": category_l2,
                "dept": dept,
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# 權限相關例外
# ─────────────────────────────────────────────────────────────────────────────

class PermissionDenied(ContractManagementException):
    """權限不足"""

    def __init__(self, required_permission: str, user_id: str = None):
        super().__init__(
            message=f"權限不足，需要 {required_permission}",
            error_code="PERMISSION_DENIED",
            status_code=403,
            details={
                "required_permission": required_permission,
                "user_id": user_id,
            },
        )


class UnauthorizedAccess(ContractManagementException):
    """未授權的存取"""

    def __init__(self, reason: str = "使用者未登入或 Token 已過期"):
        super().__init__(
            message=reason,
            error_code="UNAUTHORIZED_ACCESS",
            status_code=401,
            details={"reason": reason},
        )


# ─────────────────────────────────────────────────────────────────────────────
# 資料驗證相關例外
# ─────────────────────────────────────────────────────────────────────────────

class InvalidInputData(ContractManagementException):
    """無效的輸入資料"""

    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"欄位 {field} 無效：{reason}",
            error_code="INVALID_INPUT_DATA",
            status_code=400,
            details={
                "field": field,
                "reason": reason,
            },
        )


class MissingRequiredField(ContractManagementException):
    """缺少必填欄位"""

    def __init__(self, field_name: str):
        super().__init__(
            message=f"缺少必填欄位：{field_name}",
            error_code="MISSING_REQUIRED_FIELD",
            status_code=400,
            details={"field_name": field_name},
        )


# ─────────────────────────────────────────────────────────────────────────────
# 業務邏輯相關例外
# ─────────────────────────────────────────────────────────────────────────────

class InvalidBudgetAllocation(ContractManagementException):
    """預算分攤配置無效"""

    def __init__(self, reason: str):
        super().__init__(
            message=f"預算分攤配置無效：{reason}",
            error_code="INVALID_BUDGET_ALLOCATION",
            status_code=400,
            details={"reason": reason},
        )


class ContractStatusTransitionNotAllowed(ContractManagementException):
    """合約狀態轉移不允許"""

    def __init__(self, current_status: str, target_status: str):
        super().__init__(
            message=f"無法從「{current_status}」狀態轉移至「{target_status}」",
            error_code="CONTRACT_STATUS_TRANSITION_NOT_ALLOWED",
            status_code=400,
            details={
                "current_status": current_status,
                "target_status": target_status,
            },
        )


class ContractCannotModify(ContractManagementException):
    """合約無法修改（因為已生效或已結束）"""

    def __init__(self, contract_id: str, status: str):
        super().__init__(
            message=f"合約 {contract_id} 狀態為「{status}」，無法修改",
            error_code="CONTRACT_CANNOT_MODIFY",
            status_code=400,
            details={
                "contract_id": contract_id,
                "status": status,
            },
        )


# ─────────────────────────────────────────────────────────────────────────────
# 系統相關例外
# ─────────────────────────────────────────────────────────────────────────────

class DatabaseError(ContractManagementException):
    """資料庫操作失敗"""

    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"資料庫操作失敗：{operation} - {reason}",
            error_code="DATABASE_ERROR",
            status_code=500,
            details={
                "operation": operation,
                "reason": reason,
            },
        )


class InternalServerError(ContractManagementException):
    """內部伺服器錯誤"""

    def __init__(self, reason: str = "系統發生未預期的錯誤"):
        super().__init__(
            message=reason,
            error_code="INTERNAL_SERVER_ERROR",
            status_code=500,
            details={"reason": reason},
        )
