"""
台中核准請購單 SQLAlchemy ORM Models（2026-09-16 完整複製自樂群 purchase_request.py）

資料表：
  taichung_purchase_requests      — 主單表（每張請購單一列）
  taichung_purchase_request_items — 品項子表（每個品項一列，月報表以此為粒度）

與樂群的差異（使用者 2026-09-16 裁示）：
  - 獨立資料表（比照日曜），不與樂群共用 approved_purchase_requests
  - department_display 一律取「表單歸屬」（ragic_sheet_config.display_name），
    不看 Ragic「部門」欄位值（公用表單的單 Ragic 部門值是「資訊」，但不算資訊部）
  - 各部門單號在 Ragic 會重複（台資購-YYYYMMDD-NNN 各部門各自流水），
    唯一鍵維持 (ragic_sheet_path, ragic_record_id)
  - 額外欄位：主旨、31事由、24/25 擬定廠商編號與名稱、26~29 擬定受款資訊、幣別；品項「應稅金額」
"""
import json
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Boolean,
    Index, UniqueConstraint, func,
)

from app.core.database import Base

# ── 10 個表單的 Ragic 設定（硬編碼備援，正式使用 ragic_sheet_config 資料表 module=taichung_purchase）
# display_name = ragic_dept：台中的部門顯示名稱一律依表單歸屬，不做 Ragic 值對照
TAICHUNG_DEPT_SHEETS: list[dict] = [
    {"display_name": "公用表單", "ragic_dept": "公用表單", "list_path": "taichung-public-form/7", "detail_path": "taichung-public-form/7", "pageid": ""},
    {"display_name": "客務部", "ragic_dept": "客務部", "list_path": "customer-service/9", "detail_path": "customer-service/9", "pageid": ""},
    {"display_name": "業務部", "ragic_dept": "業務部", "list_path": "business/3", "detail_path": "business/3", "pageid": ""},
    {"display_name": "工程部", "ragic_dept": "工程部", "list_path": "construction/3", "detail_path": "construction/3", "pageid": ""},
    {"display_name": "財務部", "ragic_dept": "財務部", "list_path": "finance/9", "detail_path": "finance/9", "pageid": ""},
    {"display_name": "資訊部", "ragic_dept": "資訊部", "list_path": "info/43", "detail_path": "info/43", "pageid": ""},
    {"display_name": "行政辦公室", "ragic_dept": "行政辦公室", "list_path": "hr/5", "detail_path": "hr/5", "pageid": ""},
    {"display_name": "廚房", "ragic_dept": "廚房", "list_path": "kitchen/2", "detail_path": "kitchen/2", "pageid": ""},
    {"display_name": "餐飲", "ragic_dept": "餐飲", "list_path": "food-drink/2", "detail_path": "food-drink/2", "pageid": ""},
    {"display_name": "房務部", "ragic_dept": "房務部", "list_path": "housekeeping/2", "detail_path": "housekeeping/2", "pageid": ""},
]


class TaichungPurchaseRequest(Base):
    """台中核准請購單主單表（每張請購單一列）"""
    __tablename__ = "taichung_purchase_requests"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 公司 / 部門 ──────────────────────────────────────────────────────────
    company             = Column(String(20),  nullable=False, default="台中",
                                  comment="公司別")
    department_raw      = Column(String(20),  nullable=False, default="",
                                  comment="Ragic 原始部門值")
    department_display  = Column(String(50),  nullable=False, default="",
                                  comment="Portal 顯示名稱（＝表單歸屬，如「客務部」）")

    # ── Ragic 來源識別 ───────────────────────────────────────────────────────
    ragic_sheet_path    = Column(String(100), nullable=False, default="",
                                  comment="來源 Sheet 路徑，如 lequn-traffic-management/6")
    ragic_record_id     = Column(String(30),  nullable=False, default="",
                                  comment="Ragic 記錄主鍵")

    # ── 請購單主欄位 ─────────────────────────────────────────────────────────
    purchase_no         = Column(String(30),  nullable=False, default="",
                                  comment="編號：台資購-YYYYMMDD-NNN（各部門會重複）")
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

    # ── 台中額外欄位（2026-09-16 使用者指定加入並顯示）──────────────────────
    subject             = Column(Text,        nullable=True, comment="主旨")
    reason_31           = Column(Text,        nullable=True, comment="31事由")
    final_vendor_no     = Column(String(30),  nullable=True, comment="24最終擬定廠商編號（V-00156）")
    final_vendor_name   = Column(String(200), nullable=True, comment="25擬定廠商名稱")
    final_payee         = Column(String(200), nullable=True, comment="26擬定受款者")
    final_bank_name     = Column(String(200), nullable=True, comment="27擬定受款銀行")
    final_bank_account  = Column(String(50),  nullable=True, comment="28擬定匯款帳號")
    final_bank_code     = Column(String(30),  nullable=True, comment="29擬定銀行代號")
    currency            = Column(String(20),  nullable=True, comment="幣別")

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
                         name="uq_tc_pr_sheet_record"),
        Index("ix_tc_pr_status_approved_date", "status", "approved_date"),
        Index("ix_tc_pr_company_dept",         "company", "department_display"),
        Index("ix_tc_pr_applicant",            "applicant"),
        Index("ix_tc_pr_detail_synced",        "detail_synced"),
    )

    def get_raw(self) -> dict:
        try:
            return json.loads(self.raw_data_json or "{}")
        except Exception:
            return {}

    def __repr__(self):
        return (
            f"<TCPR id={self.id} no={self.purchase_no} "
            f"dept={self.department_display} status={self.status}>"
        )


class TaichungPurchaseRequestItem(Base):
    """台中核准請購單品項子表（每個品項一列；月報表以此為輸出粒度）"""
    __tablename__ = "taichung_purchase_request_items"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    id              = Column(Integer, primary_key=True, autoincrement=True)

    # ── 關聯主單 ─────────────────────────────────────────────────────────────
    order_id        = Column(Integer, nullable=False,
                              comment="FK → taichung_purchase_requests.id")

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

    taxable_amount       = Column(Integer,     nullable=True,
                                   comment="應稅金額（台中額外欄位）")

    # ── 勾選狀態 ─────────────────────────────────────────────────────────────
    is_confirmed    = Column(Boolean,      nullable=True,
                              comment="勾選（True=已選定此品項）")

    # ── 同步時間 ─────────────────────────────────────────────────────────────
    sync_at         = Column(DateTime,     nullable=False, server_default=func.now(),
                              comment="同步時間")

    __table_args__ = (
        UniqueConstraint("order_id", "seq", name="uq_tc_pri_order_seq"),
        Index("ix_tc_pri_order_id", "order_id"),
    )

    def __repr__(self):
        return (
            f"<TCPRItem id={self.id} order_id={self.order_id} "
            f"seq={self.seq} name={str(self.product_name or '')[:30]}>"
        )
