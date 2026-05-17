"""
Ragic Sheet 設定 ORM Model

資料表：ragic_sheet_config
用途：儲存各模組各部門對應的 Ragic Sheet 路徑，取代 model 檔案中的硬編碼清單。
      直接修改此表即可更新同步路徑，無需動程式碼或重啟服務。

module 值：
  purchase         — 樂群核准請購單
  claim            — 樂群核准請款單
  nichiyo_purchase — 日曜核准請購單
  nichiyo_claim    — 日曜核准請款單
"""
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    UniqueConstraint, func,
)

from app.core.database import Base


class RagicSheetConfig(Base):
    """各模組各部門對應的 Ragic Sheet 路徑設定"""
    __tablename__ = "ragic_sheet_config"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    module       = Column(String(50),  nullable=False, index=True)
    # module 可選值：purchase / claim / nichiyo_purchase / nichiyo_claim

    display_name = Column(String(50),  nullable=False)
    # Portal 顯示名稱，例如 "執董室" / "停管部" / "工務部"

    ragic_dept   = Column(String(50),  nullable=False)
    # Ragic API 原始部門欄位值（停管部 Ragic 值為「客服」）

    list_path    = Column(String(200), nullable=False)
    # 清單 API 路徑，格式：{slug}/{sheet_no}
    # 例如：community-management-department/24

    detail_path  = Column(String(200), nullable=False)
    # 品項內頁 API 路徑（與 list_path 相同或不同）

    extra_json   = Column(Text, default="{}")
    # 模組特定欄位，JSON 字串
    # purchase：{"pageid": "9xg"}
    # claim：{"flow_type": "零用金型"}
    # nichiyo_purchase / nichiyo_claim：{}

    sort_order   = Column(Integer, default=0)
    # 部門排列順序（前端顯示用）

    is_active    = Column(Boolean, default=True)
    # False = 暫停此部門同步（異常時可快速關閉，不必刪除）

    updated_at   = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint("module", "list_path", name="uq_module_list_path"),
    )

    def to_dict(self) -> dict:
        """轉換為與 DEPT_SHEETS 相容的 dict 格式"""
        import json
        base = {
            "display_name": self.display_name,
            "ragic_dept":   self.ragic_dept,
            "list_path":    self.list_path,
            "detail_path":  self.detail_path,
        }
        try:
            extra = json.loads(self.extra_json or "{}")
        except Exception:
            extra = {}
        base.update(extra)
        return base
