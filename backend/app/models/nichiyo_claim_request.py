"""
日曜核准請款單 SQLAlchemy ORM Models

資料表：
  nichiyo_claim_requests      — 主單表（每張請款單一列）
  nichiyo_claim_request_items — 品項子表（每個品項一列，月報表以此為粒度）

設計原則：
  - 與 approved_claim_requests（樂群）完全獨立，避免資料混用
  - raw_data_json 保留完整 API 原始 JSON，供 reparse 修正欄位 mapping
  - UNIQUE (ragic_sheet_path, ragic_record_id) 防重複同步
  - detail_synced=False → 品項尚未從 subtable 解析；True → 已同步完成
"""
import json
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Boolean,
    Index, UniqueConstraint, func,
)

from app.core.database import Base

# ── 部門顯示名稱對照表 ────────────────────────────────────────────────────────
# key  = Ragic 原始部門值（API 回傳）
# val  = Portal 顯示名稱
NICHIYO_CLAIM_DEPT_DISPLAY_MAP: dict[str, str] = {
    "執董室": "執董室",
    "營業":   "營業部",
    "行銷":   "行銷部",
    "財務":   "財務部",
    "客服":   "客服部",
    "管理":   "管理部",
    "資訊":   "資訊部",
    "設計":   "設計部",
}

# ── 8 個部門的 Ragic 請款單 Sheet 設定 ───────────────────────────────────────
# list_path   = 清單 API 路徑（同步主單用）
# detail_path = 內頁 API 路徑（同步品項用）
# 來源 URL 格式：https://ap12.ragic.com/soutlet001/{list_path}
NICHIYO_CLAIM_DEPT_SHEETS: list[dict] = [
    {
        "display_name": "執董室",
        "ragic_dept":   "執董室",
        "list_path":    "free-executive-office/9",
        "detail_path":  "free-executive-office/9",
    },
    {
        "display_name": "營業部",
        "ragic_dept":   "營業",
        "list_path":    "free-business-division/21",
        "detail_path":  "free-business-division/21",
    },
    {
        "display_name": "行銷部",
        "ragic_dept":   "行銷",
        "list_path":    "marketing/40",
        "detail_path":  "marketing/40",
    },
    {
        "display_name": "管理部",
        "ragic_dept":   "管理",
        "list_path":    "freed-management-division/19",
        "detail_path":  "freed-management-division/19",
    },
    {
        "display_name": "資訊部",
        "ragic_dept":   "資訊",
        "list_path":    "department-of-free-information/23",
        "detail_path":  "department-of-free-information/23",
    },
    {
        "display_name": "客服部",
        "ragic_dept":   "客服",
        "list_path":    "free-management-department/10",
        "detail_path":  "free-management-department/10",
    },
    {
        "display_name": "財務部",
        "ragic_dept":   "財務",
        "list_path":    "free-finance-department/15",
        "detail_path":  "free-finance-department/15",
    },
    {
        "display_name": "設計部",
        "ragic_dept":   "設計",
        "list_path":    "free-design-department/2",
        "detail_path":  "free-design-department/2",
    },
]


class NichiyoClaimRequest(Base):
    """日曜核准請款單主單表（每張請款單一列）"""
    __tablename__ = "nichiyo_claim_requests"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 公司 / 部門 ──────────────────────────────────────────────────────────
    company             = Column(String(20),  nullable=False, default="日曜",
                                  comment="公司別")
    department_raw      = Column(String(20),  nullable=False, default="",
                                  comment="Ragic 原始部門值")
    department_display  = Column(String(50),  nullable=False, default="",
                                  comment="Portal 顯示名稱")

    # ── Ragic 來源識別 ───────────────────────────────────────────────────────
    ragic_sheet_path    = Column(String(100), nullable=False, default="",
                                  comment="來源 Sheet 路徑")
    ragic_record_id     = Column(String(30),  nullable=False, default="",
                                  comment="Ragic 記錄主鍵")

    # ── 請款單主欄位 ─────────────────────────────────────────────────────────
    claim_no            = Column(String(50),  nullable=False, default="",
                                  comment="請款單號")
    account_category    = Column(String(100), nullable=True,
                                  comment="會科（費用科目）")
    request_date        = Column(Date,        nullable=True,
                                  comment="申請日期")
    approved_date       = Column(Date,        nullable=True,
                                  comment="核准完成日期")
    applicant           = Column(String(50),  nullable=True,
                                  comment="申請人姓名")
    purpose_description = Column(Text,        nullable=True,
                                  comment="事由／說明（前 500 字元）")
    payment_type        = Column(String(20),  nullable=True,
                                  comment="付款種類：零用金 / 匯款")

    # ── 金額 ─────────────────────────────────────────────────────────────────
    subtotal            = Column(Integer,     nullable=True,
                                  comment="小計（未稅）")
    tax                 = Column(Integer,     nullable=True,
                                  comment="營業稅")
    total               = Column(Integer,     nullable=True,
                                  comment="總計（含稅）")
    payable_amount      = Column(Integer,     nullable=True,
                                  comment="應付(繳)款（最終付款金額）")

    # ── 付款資訊 ─────────────────────────────────────────────────────────────
    payee               = Column(String(100), nullable=True,
                                  comment="受款者（收款人／公司）")
    payment_date        = Column(Date,        nullable=True,
                                  comment="付款日期（預計付款日）")

    # ── 簽核狀態 ─────────────────────────────────────────────────────────────
    status              = Column(String(5),   nullable=False, default="N",
                                  comment="F=已核准 / N=待審 / REJ=退回")

    # ── 同步狀態旗標 ─────────────────────────────────────────────────────────
    detail_synced       = Column(Boolean,     nullable=False, default=False)

    # ── 原始資料備援（reparse 用）────────────────────────────────────────────
    raw_data_json       = Column(Text,        nullable=False, default="{}")

    # ── 時間戳 ───────────────────────────────────────────────────────────────
    last_updated_at     = Column(DateTime,    nullable=True)
    sync_at             = Column(DateTime,    nullable=False, server_default=func.now())
    created_at          = Column(DateTime,    nullable=False, server_default=func.now())
    updated_at          = Column(DateTime,    nullable=False, server_default=func.now(),
                                  onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("ragic_sheet_path", "ragic_record_id",
                         name="uq_nichiyo_cr_sheet_record"),
        Index("ix_nichiyo_cr_status_date",   "status", "approved_date"),
        Index("ix_nichiyo_cr_dept",          "department_display"),
        Index("ix_nichiyo_cr_detail_synced", "detail_synced"),
    )

    def get_raw(self) -> dict:
        try:
            return json.loads(self.raw_data_json or "{}")
        except Exception:
            return {}

    def __repr__(self):
        return (
            f"<NichiyoCR id={self.id} no={self.claim_no} "
            f"dept={self.department_display} status={self.status}>"
        )


class NichiyoClaimRequestItem(Base):
    """日曜核准請款單品項子表（每個品項一列）"""
    __tablename__ = "nichiyo_claim_request_items"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    order_id        = Column(Integer, nullable=False,
                              comment="FK → nichiyo_claim_requests.id")
    seq             = Column(Integer,      nullable=False, default=0)
    product_name    = Column(Text,         nullable=True,  comment="品項名稱／摘要")
    qty             = Column(String(30),   nullable=True,  comment="數量")
    unit            = Column(String(20),   nullable=True,  comment="單位")
    unit_price      = Column(Integer,      nullable=True,  comment="單價")
    amount          = Column(Integer,      nullable=True,  comment="品項金額")
    item_remark     = Column(Text,         nullable=True,  comment="品項備註")
    sync_at         = Column(DateTime,     nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("order_id", "seq", name="uq_nichiyo_cri_order_seq"),
        Index("ix_nichiyo_cri_order_id", "order_id"),
    )

    def __repr__(self):
        return (
            f"<NichiyoCRItem id={self.id} order_id={self.order_id} "
            f"seq={self.seq} name={str(self.product_name or '')[:30]}>"
        )
