"""
核准請購單 SQLAlchemy ORM Models

資料表：
  approved_purchase_requests      — 主單表（每張請購單一列）
  approved_purchase_request_items — 品項子表（每個品項一列，月報表以此為粒度）

設計原則：
  - Step1 清單 API 同步後 detail_synced=False，amount/status/approved_date 已填
  - Step2 Detail API 同步後補入品項子表、amount_tax、vendor1~3、detail_synced=True
  - department_display 由 DEPT_DISPLAY_MAP 對照 Ragic 原始部門值轉換（停管部特別處理）
  - raw_data_json 保留完整 API 原始 JSON，供欄位 mapping 補正
  - UNIQUE (ragic_sheet_path, ragic_record_id) 防重複同步
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
# val  = Portal 顯示名稱（月報表使用）
# 注意：停管部 Ragic 值為「客服」，必須做映射
DEPT_DISPLAY_MAP: dict[str, str] = {
    "執董室": "執董室",
    "營業":   "營業部",
    "行銷":   "行銷部",
    "財務":   "財務部",
    "客服":   "停管部",   # ← 停管部 Ragic 值 = 「客服」
    "管理":   "管理部",
    "資訊":   "資訊部",
    "工務":   "工務部",
    "專案":   "專案",
}

# ── 9 個部門的 Ragic 設定（清單路徑 + Detail 路徑）────────────────────────────
DEPT_SHEETS: list[dict] = [
    {
        "display_name": "執董室",
        "ragic_dept":   "執董室",
        "list_path":    "lequn-executive-office/10",
        "detail_path":  "lequn-executive-office/2",
        "pageid":       "0l4",
    },
    {
        "display_name": "營業部",
        "ragic_dept":   "營業",
        "list_path":    "new-tab/10",
        "detail_path":  "new-tab/10",
        "pageid":       "",
    },
    {
        "display_name": "行銷部",
        "ragic_dept":   "行銷",
        "list_path":    "lequn-marketing-department/12",
        "detail_path":  "lequn-marketing-department/2",   # ← /9 不存在；/2 為簽呈表單（有申請日期/說明/簽核狀態）
        "pageid":       "DfW",
    },
    {
        "display_name": "財務部",
        "ragic_dept":   "財務",
        "list_path":    "lequn-finance-department/9",
        "detail_path":  "lequn-finance-department/11",   # ← /2 是印鑑借用；/11 為請購單（採購編號/擬定廠商/小計/營業稅）
        "pageid":       "",
    },
    {
        "display_name": "停管部",
        "ragic_dept":   "客服",
        "list_path":    "lequn-traffic-management/6",
        "detail_path":  "lequn-traffic-management/6",   # ← 內頁與清單同 sheet，/6/record_id（8 是 record ID 非 sheet）
        "pageid":       "",
    },
    {
        "display_name": "管理部",
        "ragic_dept":   "管理",
        "list_path":    "community-management-department/22",
        "detail_path":  "community-management-department/22",  # ← 內頁與清單同 sheet，/22/record_id
        "pageid":       "9xg",
    },
    {
        "display_name": "資訊部",
        "ragic_dept":   "資訊",
        "list_path":    "joy-group-it-department/11",
        "detail_path":  "joy-group-it-department/12",   # ← /5(財務部sheet)錯誤；/12 為資訊部請購單（採購編號/擬定廠商/小計/營業稅）
        "pageid":       "",
    },
    {
        "display_name": "工務部",
        "ragic_dept":   "工務",
        "list_path":    "lequn-public-works-department/1",
        "detail_path":  "lequn-public-works-department/2",   # ← /60 不存在；/2 為工務請購單（工請編號/採購編號/申請人/小計）
        "pageid":       "hBY",
    },
    {
        "display_name": "專案",
        "ragic_dept":   "專案",
        "list_path":    "happy-group-project/2",
        "detail_path":  "happy-group-project/1",   # ← /39 不存在；/1 為專案請購單（專請編號/採購編號/申請人/小計）
        "pageid":       "NVk",
    },
]


class ApprovedPurchaseRequest(Base):
    """核准請購單主單表（每張請購單一列）"""
    __tablename__ = "approved_purchase_requests"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 公司 / 部門 ──────────────────────────────────────────────────────────
    company             = Column(String(20),  nullable=False, default="樂群",
                                  comment="公司別")
    department_raw      = Column(String(20),  nullable=False, default="",
                                  comment="Ragic 原始部門值（如「客服」）")
    department_display  = Column(String(50),  nullable=False, default="",
                                  comment="Portal 顯示名稱（如「停管部」）")

    # ── Ragic 來源識別 ───────────────────────────────────────────────────────
    ragic_sheet_path    = Column(String(100), nullable=False, default="",
                                  comment="來源 Sheet 路徑，如 lequn-traffic-management/6")
    ragic_record_id     = Column(String(30),  nullable=False, default="",
                                  comment="Ragic 記錄主鍵")

    # ── 請購單主欄位 ─────────────────────────────────────────────────────────
    purchase_no         = Column(String(30),  nullable=False, default="",
                                  comment="編號：樂[部門碼]購YYYYMMXXXXX")
    account_category    = Column(String(100), nullable=True,
                                  comment="會科（費用科目）")
    request_date        = Column(Date,        nullable=True,
                                  comment="申請日期（YYYY-MM-DD）")
    approved_date       = Column(Date,        nullable=True,
                                  comment="核准完成日期（最後更新日期，status=F 時有意義）")
    applicant           = Column(String(50),  nullable=True,
                                  comment="申請人姓名")
    description         = Column(Text,        nullable=True,
                                  comment="說明／請購事由（前 500 字元）")

    # ── 金額 ─────────────────────────────────────────────────────────────────
    amount              = Column(Integer,     nullable=False, default=0,
                                  comment="全案小計（未稅，新台幣元）—清單 API 可取得")
    amount_tax          = Column(Integer,     nullable=True,
                                  comment="營業稅（需 Detail API；業主確認必要顯示）")
    amount_total        = Column(Integer,     nullable=True,
                                  comment="全案總計（含稅，存 DB 備用，不在月報表顯示）")

    # ── 簽核狀態 ─────────────────────────────────────────────────────────────
    status              = Column(String(5),   nullable=False, default="N",
                                  comment="F=已核准 / N=待審 / REJ=退回")

    # ── 廠商（主單層，從 Detail API 取得）───────────────────────────────────
    vendor1             = Column(String(100), nullable=True, comment="廠商(一)名稱")
    vendor2             = Column(String(100), nullable=True, comment="廠商(二)名稱")
    vendor3             = Column(String(100), nullable=True, comment="廠商(三)名稱")

    # ── 備註 ─────────────────────────────────────────────────────────────────
    remark              = Column(Text,        nullable=True, comment="備註欄位")

    # ── 同步狀態旗標 ─────────────────────────────────────────────────────────
    detail_synced       = Column(Boolean,     nullable=False, default=False,
                                  comment="是否已完成 Detail API 同步（品項+廠商+稅額）")

    # ── 原始資料備援 ─────────────────────────────────────────────────────────
    raw_data_json       = Column(Text,        nullable=False, default="{}",
                                  comment="清單 API 原始 JSON（供欄位 mapping 補正）")

    # ── 時間戳 ───────────────────────────────────────────────────────────────
    last_updated_at     = Column(DateTime,    nullable=True,
                                  comment="Ragic「最後更新日期」原始值（台灣時區）")
    sync_at             = Column(DateTime,    nullable=False, server_default=func.now(),
                                  comment="本次同步時間")
    created_at          = Column(DateTime,    nullable=False, server_default=func.now(),
                                  comment="首次建立時間")
    updated_at          = Column(DateTime,    nullable=False, server_default=func.now(),
                                  onupdate=func.now(), comment="最後更新時間（upsert 自動更新）")

    __table_args__ = (
        UniqueConstraint("ragic_sheet_path", "ragic_record_id",
                         name="uq_apr_sheet_record"),
        Index("ix_apr_status_approved_date", "status", "approved_date"),
        Index("ix_apr_company_dept",         "company", "department_display"),
        Index("ix_apr_applicant",            "applicant"),
        Index("ix_apr_detail_synced",        "detail_synced"),
    )

    def get_raw(self) -> dict:
        try:
            return json.loads(self.raw_data_json or "{}")
        except Exception:
            return {}

    def __repr__(self):
        return (
            f"<APR id={self.id} no={self.purchase_no} "
            f"dept={self.department_display} status={self.status}>"
        )


class ApprovedPurchaseRequestItem(Base):
    """核准請購單品項子表（每個品項一列；月報表以此為輸出粒度）"""
    __tablename__ = "approved_purchase_request_items"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    id              = Column(Integer, primary_key=True, autoincrement=True)

    # ── 關聯主單 ─────────────────────────────────────────────────────────────
    order_id        = Column(Integer, nullable=False,
                              comment="FK → approved_purchase_requests.id")

    # ── 品項資訊 ─────────────────────────────────────────────────────────────
    seq             = Column(Integer,      nullable=False, default=0,
                              comment="項次（子表格序號）")
    product_name    = Column(Text,         nullable=True,
                              comment="產品名稱（品名）—月報表品名欄")
    qty             = Column(String(30),   nullable=True,
                              comment="數量（保留原始字串格式，如 10、10.5）")
    unit            = Column(String(20),   nullable=True,
                              comment="單位（件/尺/式/小時等）")
    item_remark     = Column(Text,         nullable=True,
                              comment="品項備註")

    # ── 廠商報價 ─────────────────────────────────────────────────────────────
    vendor1_price   = Column(Integer,      nullable=True, comment="廠商(一)金額")
    vendor2_price   = Column(Integer,      nullable=True, comment="廠商(二)金額")
    vendor3_price   = Column(Integer,      nullable=True, comment="廠商(三)金額")

    # ── 擬定廠商（最終選定）─────────────────────────────────────────────────
    selected_vendor      = Column(String(100), nullable=True,
                                   comment="擬定廠商名稱—月報表廠商欄")
    selected_unit_price  = Column(Integer,     nullable=True,
                                   comment="擬定單價—月報表顯示")
    selected_amount      = Column(Integer,     nullable=True,
                                   comment="擬定金額—月報表品項金額欄")

    # ── 勾選狀態 ─────────────────────────────────────────────────────────────
    is_confirmed    = Column(Boolean,      nullable=True,
                              comment="勾選（True=已選定此品項）")

    # ── 同步時間 ─────────────────────────────────────────────────────────────
    sync_at         = Column(DateTime,     nullable=False, server_default=func.now(),
                              comment="同步時間")

    __table_args__ = (
        UniqueConstraint("order_id", "seq", name="uq_apri_order_seq"),
        Index("ix_apri_order_id", "order_id"),
    )

    def __repr__(self):
        return (
            f"<APRItem id={self.id} order_id={self.order_id} "
            f"seq={self.seq} name={str(self.product_name or '')[:30]}>"
        )
