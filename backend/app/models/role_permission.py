"""
角色權限映射 Model
role_permissions 表：多對多關聯 roles → permission_key
每個角色可擁有零至多個 permission_key，system_admin 透過程式邏輯
隱式擁有所有權限（不需實際存入此表）。
"""
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
import uuid
from app.core.database import Base


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    role_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # 格式：<module>_<action>，例如 settings_users_manage、mall_dashboard_view
    permission_key: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("role_id", "permission_key", name="uq_role_permission"),
    )
