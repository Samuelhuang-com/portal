"""
UserDepartment — 使用者 ↔ 部門 多對多關聯（2026-09-01 新增）

使用者裁示：一個 User 可屬多公司、多部門；同部門的人都能操作該部門的
週採請購單。因此：

    settings/company-departments（Company / RefDepartment）← 唯一真實來源
            ▲
       本表 user_departments（user_id ↔ department_id，多對多）
            ▲
       users ──tenant_id──▶ tenants（保留，語意退化為「主要公司別」）

設計要點：
  - **不另建 user_companies 表**：部門本來就屬於公司（RefDepartment.company_id），
    使用者掛了哪些部門就自動屬於哪些公司。
  - `users.tenant_id` 保留不動（NOT NULL FK，被 user_roles／audit_logs 綁著，
    CLAUDE.md §5 禁止移除欄位），只做顯示與稽核歸屬。
  - 週採權限鏈（cycle_purchase_requests._ensure_own_department）：
    請購單.department_id → cycle_purchase_departments.source_department_id
        → 本表 department_id → 部門成員即可操作（owner_user_id 保留為備援通道）。
  - ondelete：user 刪除連帶刪關聯（使用者本來就少刪）；department 用 CASCADE ——
    部門在公司/部門管理被刪時，成員關聯跟著消失是正確語意（成員名單是
    部門的附屬資料，不是歷史紀錄）。
"""
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import twnow
from app.core.database import Base


def _now():
    return twnow()


class UserDepartment(Base):
    __tablename__ = "user_departments"
    __table_args__ = (
        UniqueConstraint("user_id", "department_id", name="uq_user_department"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
