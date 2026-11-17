"""
庫存管理（Phase 2：庫存核心）ORM Models — docs/SPEC_stock_management.md §8、§11

⚠️ 放在週採資料庫（CyclePurchaseBase，cycle-purchase 庫），不放主庫：
   - 料號主檔沿用週採料號（D1），同庫才能用外鍵連 cycle_purchase_items
   - 公司代碼（CH／OU／HO）與多公司隔離機制沿用週採
   - 與主庫（使用者、公司／部門主檔、Ragic 採購單）一律軟關聯（只存 ID＋名稱快照）

資料表：
  stock_warehouses       倉庫（公司 × 部門；parent_id 預留儲位）
  stock_item_settings    料號的庫存設定（是否納入庫存、採購單位換算、ABC）
  stock_moves            庫存異動帳（只新增、不修改、不刪除；更正一律用反向異動）
  stock_balances         庫存快取（由 stock_moves 計算，可隨時重建）
  stock_openings         期初開帳單（單頭；明細＝source_type='opening' 的 stock_moves）
"""
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, func,
)

from app.core.cycle_purchase_database import CyclePurchaseBase

WAREHOUSE_STATUSES = ("active", "inactive", "counting")
MOVE_TYPES = (
    "opening", "opening_void",       # 期初開帳／作廢（Phase 2）
    "receipt", "receipt_void",       # 進貨／作廢（Phase 3）
    "issue", "return", "transfer_in", "transfer_out", "scrap",   # Phase 4
    "return_void", "transfer_in_void", "transfer_out_void", "scrap_void",   # Phase 4 作廢
    "count_adjust",                  # 盤點調整（Phase 5）
)


class StockWarehouse(CyclePurchaseBase):
    __tablename__ = "stock_warehouses"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    company_code    = Column(String(10), ForeignKey("cycle_purchase_companies.code", ondelete="RESTRICT"),
                             nullable=False, index=True, comment="公司代碼（CH／OU／HO）")
    department_id   = Column(String(30), nullable=True,
                             comment="主庫 departments.id（settings/company-departments，軟關聯）")
    department_name = Column(String(100), nullable=True, comment="部門名稱快照")
    parent_id       = Column(Integer, ForeignKey("stock_warehouses.id", ondelete="RESTRICT"), nullable=True,
                             comment="上層倉（儲位用，預留）")
    name            = Column(String(100), nullable=False, comment="倉名")
    keeper_name     = Column(String(100), nullable=True, comment="倉管人員")
    status          = Column(String(20), nullable=False, default="active", server_default="active",
                             comment="active／inactive／counting（盤點中）")
    issue_requires_approval = Column(Boolean, nullable=False, default=False, server_default="false",
                                     comment="領用單是否需部門主管核准（Phase 4，D5 預設不需要）")
    notes           = Column(Text, nullable=True)
    created_by      = Column(String(100), nullable=True)
    created_at      = Column(DateTime, nullable=False, server_default=func.now())
    updated_at      = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("company_code", "name", name="uq_stock_wh_company_name"),
    )


class StockItemSetting(CyclePurchaseBase):
    """沒有這列＝預設值（納入庫存、採購單位＝庫存單位、換算 1）。安全量沿用料號主檔 min_stock／max_stock。"""
    __tablename__ = "stock_item_settings"

    item_id       = Column(Integer, ForeignKey("cycle_purchase_items.id", ondelete="CASCADE"), primary_key=True)
    is_stock_item = Column(Boolean, nullable=False, default=True, server_default="true", comment="是否納入庫存")
    purchase_unit = Column(String(20), nullable=True, comment="採購單位（如：箱）；NULL＝同庫存單位")
    unit_ratio    = Column(Numeric(14, 4), nullable=False, default=1, server_default="1",
                           comment="1 採購單位＝幾個庫存單位")
    abc_class     = Column(String(1), nullable=True, comment="A／B／C（循環盤點用，預留）")
    updated_by    = Column(String(100), nullable=True)
    updated_at    = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class StockMove(CyclePurchaseBase):
    __tablename__ = "stock_moves"

    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    company_code  = Column(String(10), nullable=False, comment="公司代碼（冗餘，查詢用）")
    warehouse_id  = Column(Integer, ForeignKey("stock_warehouses.id", ondelete="RESTRICT"), nullable=False)
    item_id       = Column(Integer, ForeignKey("cycle_purchase_items.id", ondelete="RESTRICT"), nullable=False)
    qty           = Column(Numeric(14, 4), nullable=False, comment="數量（庫存單位，正＝入、負＝出）")
    unit_cost     = Column(Numeric(14, 4), nullable=False, default=0, comment="單位成本（未稅）")
    amount        = Column(Numeric(16, 2), nullable=False, default=0, comment="金額＝qty × unit_cost")
    move_type     = Column(String(20), nullable=False)
    source_type   = Column(String(30), nullable=False, comment="來源單據類型（opening／receipt／issue…）")
    source_id     = Column(String(50), nullable=True, comment="來源單據 ID")
    source_no     = Column(String(50), nullable=True, comment="來源單號快照")
    moved_at      = Column(Date, nullable=False, comment="異動日期")
    period        = Column(String(7), nullable=False, comment="所屬月份 YYYY-MM")
    note          = Column(Text, nullable=True)
    created_by    = Column(String(100), nullable=True)
    created_at    = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_stock_moves_wh_item", "warehouse_id", "item_id", "moved_at"),
        Index("ix_stock_moves_company_period", "company_code", "period"),
        Index("ix_stock_moves_source", "source_type", "source_id"),
    )


class StockBalance(CyclePurchaseBase):
    __tablename__ = "stock_balances"

    warehouse_id  = Column(Integer, ForeignKey("stock_warehouses.id", ondelete="CASCADE"), primary_key=True)
    item_id       = Column(Integer, ForeignKey("cycle_purchase_items.id", ondelete="CASCADE"), primary_key=True)
    qty           = Column(Numeric(14, 4), nullable=False, default=0)
    reserved_qty  = Column(Numeric(14, 4), nullable=False, default=0, comment="已送出未過帳的領用保留量（Phase 4）")
    avg_cost      = Column(Numeric(14, 4), nullable=False, default=0, comment="移動平均單價（月結時改月加權平均）")
    amount        = Column(Numeric(16, 2), nullable=False, default=0)
    last_move_at  = Column(Date, nullable=True)
    updated_at    = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class StockOpening(CyclePurchaseBase):
    __tablename__ = "stock_openings"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    doc_no        = Column(String(30), nullable=False, unique=True, comment="OPN-<公司>-YYYYMM-###")
    company_code  = Column(String(10), nullable=False, index=True)
    warehouse_id  = Column(Integer, ForeignKey("stock_warehouses.id", ondelete="RESTRICT"), nullable=False)
    opening_date  = Column(Date, nullable=False)
    status        = Column(String(20), nullable=False, default="posted", comment="posted／voided")
    note          = Column(Text, nullable=True)
    line_count    = Column(Integer, nullable=False, default=0)
    total_amount  = Column(Numeric(16, 2), nullable=False, default=0)
    created_by    = Column(String(100), nullable=True)
    created_at    = Column(DateTime, nullable=False, server_default=func.now())
    voided_by     = Column(String(100), nullable=True)
    voided_at     = Column(DateTime, nullable=True)
    void_reason   = Column(Text, nullable=True)


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3（2026-11-17）進貨匯入 — docs/SPEC_stock_management.md §6
# ═══════════════════════════════════════════════════════════════════════════

IMPORT_STATUSES = ("pending", "partial", "done", "non_stock", "pre_opening", "linked_po")


class StockImportLine(CyclePurchaseBase):
    """待匯入清單：一列＝一筆 Ragic 採購單／請款單品項（快照自主庫，主庫資料只讀）。

    唯一鍵 (source_type, ragic_sheet_path, ragic_record_id, ragic_row_id)：ragic_row_id 取子表列 _ragicId，
    Ragic 重新排序也不變；累計 imported_qty 不得超過 qty（防重複入庫，SPEC §6.5）。
    status：pending 待確認／partial 部分匯入／done 已匯入／non_stock 不入庫／pre_opening 開帳前不入庫／
            linked_po 請款單已對應採購單（只做三單比對，不進待匯入）
    """
    __tablename__ = "stock_import_lines"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    company_code    = Column(String(10), nullable=False, index=True)
    source_type     = Column(String(20), nullable=False, comment="ragic_po／ragic_claim")
    source_db_id    = Column(Integer, nullable=True, comment="主庫單頭 id（軟關聯）")
    ragic_sheet_path = Column(String(100), nullable=False)
    ragic_record_id = Column(String(30), nullable=False)
    ragic_row_id    = Column(String(30), nullable=False, comment="子表列 _ragicId（沒有子表時為 seq<n>）")
    doc_no          = Column(String(50), nullable=True, comment="單號（採購編號／請款單號）")
    po_no           = Column(String(50), nullable=True, comment="採購單號（採購單＝自身；請款單＝已對應的採購單）")
    suspected_po_no = Column(String(50), nullable=True, comment="內容比對「強」的疑似採購單（樂群／日曜請款單）")
    department      = Column(String(50), nullable=True)
    doc_date        = Column(Date, nullable=True, comment="申請／到貨日期")
    vendor_name     = Column(String(200), nullable=True)
    item_code       = Column(String(50), nullable=True, comment="Ragic 帶的料號（週採採購單才有）")
    product_name    = Column(Text, nullable=True)
    qty             = Column(Numeric(14, 4), nullable=True, comment="數量（採購單位）；無法解析＝NULL")
    qty_raw         = Column(String(50), nullable=True)
    unit            = Column(String(50), nullable=True)
    unit_price      = Column(Numeric(14, 4), nullable=True, comment="未稅單價（採購單位）")
    amount          = Column(Numeric(16, 2), nullable=True, comment="未稅金額")
    imported_qty    = Column(Numeric(14, 4), nullable=False, default=0, server_default="0")
    status          = Column(String(20), nullable=False, default="pending", server_default="pending")
    status_reason   = Column(Text, nullable=True)
    marked_by       = Column(String(100), nullable=True)
    source_hash     = Column(String(64), nullable=False, default="")
    source_changed  = Column(Boolean, nullable=False, default=False, server_default="false",
                             comment="已匯入後 Ragic 來源又被修改／退回／刪除（不自動扣庫存，D18）")
    source_status   = Column(String(20), nullable=False, default="ok", server_default="ok",
                             comment="ok／changed／deleted／rejected")
    refreshed_at    = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, nullable=False, server_default=func.now())
    updated_at      = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("source_type", "ragic_sheet_path", "ragic_record_id", "ragic_row_id",
                         name="uq_stock_import_line_src"),
        Index("ix_stock_import_company_status", "company_code", "status"),
        Index("ix_stock_import_po_no", "company_code", "po_no"),
    )


class StockReceipt(CyclePurchaseBase):
    __tablename__ = "stock_receipts"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    receipt_no    = Column(String(30), nullable=False, unique=True, comment="RCV-<公司>-YYYYMM-###")
    company_code  = Column(String(10), nullable=False, index=True)
    warehouse_id  = Column(Integer, ForeignKey("stock_warehouses.id", ondelete="RESTRICT"), nullable=False)
    receipt_date  = Column(Date, nullable=False, comment="入庫日期（實際到貨日）")
    status        = Column(String(20), nullable=False, default="posted", comment="posted／voided")
    note          = Column(Text, nullable=True)
    line_count    = Column(Integer, nullable=False, default=0)
    total_amount  = Column(Numeric(16, 2), nullable=False, default=0)
    created_by    = Column(String(100), nullable=True)
    created_at    = Column(DateTime, nullable=False, server_default=func.now())
    voided_by     = Column(String(100), nullable=True)
    voided_at     = Column(DateTime, nullable=True)
    void_reason   = Column(Text, nullable=True)


class StockReceiptItem(CyclePurchaseBase):
    __tablename__ = "stock_receipt_items"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    receipt_id      = Column(Integer, ForeignKey("stock_receipts.id", ondelete="CASCADE"), nullable=False, index=True)
    import_line_id  = Column(Integer, ForeignKey("stock_import_lines.id", ondelete="RESTRICT"), nullable=False, index=True)
    item_id         = Column(Integer, ForeignKey("cycle_purchase_items.id", ondelete="RESTRICT"), nullable=False)
    purchase_qty    = Column(Numeric(14, 4), nullable=False, comment="實收數量（採購單位）")
    purchase_unit   = Column(String(50), nullable=True)
    unit_ratio      = Column(Numeric(14, 4), nullable=False, default=1, comment="1 採購單位＝幾個庫存單位")
    stock_qty       = Column(Numeric(14, 4), nullable=False, comment="入庫數量（庫存單位）")
    unit_cost       = Column(Numeric(14, 4), nullable=False, comment="入庫單價（庫存單位、未稅）")
    amount          = Column(Numeric(16, 2), nullable=False)
    is_estimated_cost = Column(Boolean, nullable=False, default=False, comment="來源無單價，改用料號參考單價")
    override_reason = Column(Text, nullable=True, comment="疑似已由採購單入庫仍匯入的確認理由")


class StockItemAlias(CyclePurchaseBase):
    """Ragic 品名 → 料號對照（第一次人工確認後寫入，下次自動帶出，SPEC §5.2、§6.4）。"""
    __tablename__ = "stock_item_aliases"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    company_code    = Column(String(10), nullable=False)
    normalized_name = Column(String(300), nullable=False)
    raw_name        = Column(Text, nullable=True)
    item_id         = Column(Integer, ForeignKey("cycle_purchase_items.id", ondelete="CASCADE"), nullable=True)
    is_non_stock    = Column(Boolean, nullable=False, default=False, server_default="false",
                             comment="同品名下次自動建議為不入庫")
    hit_count       = Column(Integer, nullable=False, default=1, server_default="1")
    confirmed_by    = Column(String(100), nullable=True)
    confirmed_at    = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("company_code", "normalized_name", name="uq_stock_alias_company_name"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Phase 4a（2026-11-17）領用／退料／調撥／報廢 — docs/SPEC_stock_management.md §7
# ═══════════════════════════════════════════════════════════════════════════

ISSUE_DOC_TYPES = ("issue", "return", "transfer", "scrap")
ISSUE_STATUSES = ("draft", "pending_approval", "approved", "posted", "cancelled", "rejected", "voided")
# 會佔用保留量的狀態（只有領用單會保留；退料是入庫、調撥／報廢由倉管開單即過帳）
RESERVING_STATUSES = ("pending_approval", "approved")


class StockIssue(CyclePurchaseBase):
    """領用／退料／調撥／報廢單（共用一張表，doc_type 區分）。

    領用：draft →送出（保留）→ pending_approval（倉庫設定需核准）／approved（待發料）→ 發料過帳 posted
          草稿、待核准、待發料可取消（cancelled，釋放保留）；待核准可退回（rejected，釋放保留）
    退料：draft →送出→ approved（待收料）→ 倉管收料過帳 posted；必須對應原領用單（ref_issue_id）
    調撥／報廢：倉管開單 → 過帳（draft → posted）
    已過帳的領用單不能改、不能作廢，只能開退料單；退料／調撥／報廢可作廢（反向異動）。
    """
    __tablename__ = "stock_issues"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    doc_no           = Column(String(30), nullable=False, unique=True,
                              comment="ISU／RTN／TRF／SCR-<公司>-YYYYMM-###")
    doc_type         = Column(String(20), nullable=False, comment="issue／return／transfer／scrap")
    company_code     = Column(String(10), nullable=False, index=True)
    warehouse_id     = Column(Integer, ForeignKey("stock_warehouses.id", ondelete="RESTRICT"), nullable=False,
                              comment="領用倉／退回倉／調出倉／報廢倉")
    to_warehouse_id  = Column(Integer, ForeignKey("stock_warehouses.id", ondelete="RESTRICT"), nullable=True,
                              comment="調入倉（調撥單）")
    doc_date         = Column(Date, nullable=False, comment="單據日期（過帳時為異動日期）")
    requester_user_id = Column(String(36), nullable=True, comment="領用人 users.id（主庫，軟關聯）")
    requester_name   = Column(String(100), nullable=True, comment="領用人姓名（可代填）")
    department_id    = Column(String(30), nullable=True, comment="領用部門（主庫 departments.id 快照）")
    department_name  = Column(String(100), nullable=True)
    purpose          = Column(Text, nullable=True, comment="用途說明／報廢原因／退料原因")
    cost_center_id   = Column(Integer, nullable=True, comment="週採成本中心 id（軟關聯）")
    cost_center_name = Column(String(150), nullable=True, comment="成本中心快照（代碼 名稱）")
    account_code     = Column(String(50), nullable=True, comment="會科（選填）")
    ref_issue_id     = Column(Integer, ForeignKey("stock_issues.id", ondelete="RESTRICT"), nullable=True,
                              comment="退料單對應的原領用單")
    status           = Column(String(20), nullable=False, default="draft", server_default="draft")
    line_count       = Column(Integer, nullable=False, default=0, server_default="0")
    total_amount     = Column(Numeric(16, 2), nullable=False, default=0, server_default="0",
                              comment="過帳金額（過帳前為 0）")
    submitted_by     = Column(String(100), nullable=True)
    submitted_at     = Column(DateTime, nullable=True)
    approved_by      = Column(String(100), nullable=True)
    approved_at      = Column(DateTime, nullable=True)
    posted_by        = Column(String(100), nullable=True)
    posted_at        = Column(DateTime, nullable=True)
    posted_date      = Column(Date, nullable=True, comment="過帳日（異動日期；發料／收料日）")
    closed_by        = Column(String(100), nullable=True, comment="取消／退回／作廢的人")
    closed_at        = Column(DateTime, nullable=True)
    close_reason     = Column(Text, nullable=True)
    created_by_user_id = Column(String(36), nullable=True)
    created_by       = Column(String(100), nullable=True)
    created_at       = Column(DateTime, nullable=False, server_default=func.now())
    updated_at       = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_stock_issues_company_type_status", "company_code", "doc_type", "status"),
        Index("ix_stock_issues_wh", "warehouse_id"),
        Index("ix_stock_issues_ref", "ref_issue_id"),
    )


class StockIssueLine(CyclePurchaseBase):
    __tablename__ = "stock_issue_lines"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    issue_id     = Column(Integer, ForeignKey("stock_issues.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id      = Column(Integer, ForeignKey("cycle_purchase_items.id", ondelete="RESTRICT"), nullable=False)
    qty          = Column(Numeric(14, 4), nullable=False, comment="數量（庫存單位，正數）")
    reserved_qty = Column(Numeric(14, 4), nullable=False, default=0, server_default="0",
                          comment="目前佔用的保留量（領用單送出後＝qty；過帳／取消後歸 0）")
    unit_cost    = Column(Numeric(14, 4), nullable=True, comment="過帳時的單位成本")
    amount       = Column(Numeric(16, 2), nullable=True, comment="過帳金額（正數）")
    ref_line_id  = Column(Integer, ForeignKey("stock_issue_lines.id", ondelete="RESTRICT"), nullable=True,
                          comment="退料單對應的原領用明細")
    note         = Column(Text, nullable=True)
