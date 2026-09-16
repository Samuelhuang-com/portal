"""taichung_purchase_claim 台中核准請購單／請款單四張表

Revision ID: tcpurch
Revises: compset
Create Date: 2026-09-16

背景（使用者 2026-09-16 裁示）
────────────────────────────────────────────────────────────────────────────
新增「台中」二階的「核准請購單」「核准請款單」月報表模組，完整複製樂群
purchase-report / claim-report。資料表比照日曜採**獨立新表**，不與樂群共用
approved_purchase_requests / approved_claim_requests。

PostgreSQL 方言。純新增四張表，不動任何既有表。

⚠️ 可重跑：main.py 啟動時的 `Base.metadata.create_all()` 可能已先把表建出來
（後端比 `alembic upgrade` 先起的情況），所以每張表／索引都先檢查存在與否，
不存在才建，避免 DuplicateTable。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "tcpurch"
down_revision: Union[str, None] = "compset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _ensure_index(name: str, table: str, cols: list[str]) -> None:
    existing = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, cols, unique=False)


def upgrade() -> None:
    if not _has_table('taichung_purchase_requests'):
        op.create_table('taichung_purchase_requests',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('company', sa.String(length=20), nullable=False, comment='公司別'),
            sa.Column('department_raw', sa.String(length=20), nullable=False, comment='Ragic 原始部門值'),
            sa.Column('department_display', sa.String(length=50), nullable=False, comment='Portal 顯示名稱（＝表單歸屬，如「客務部」）'),
            sa.Column('ragic_sheet_path', sa.String(length=100), nullable=False, comment='來源 Sheet 路徑，如 lequn-traffic-management/6'),
            sa.Column('ragic_record_id', sa.String(length=30), nullable=False, comment='Ragic 記錄主鍵'),
            sa.Column('purchase_no', sa.String(length=30), nullable=False, comment='編號：台資購-YYYYMMDD-NNN（各部門會重複）'),
            sa.Column('account_category', sa.String(length=100), nullable=True, comment='會科（費用科目）'),
            sa.Column('request_date', sa.Date(), nullable=True, comment='申請日期（YYYY-MM-DD）'),
            sa.Column('approved_date', sa.Date(), nullable=True, comment='核准完成日期（最後更新日期，status=F 時有意義）'),
            sa.Column('applicant', sa.String(length=50), nullable=True, comment='申請人姓名'),
            sa.Column('description', sa.String(length=None), nullable=True, comment='說明／請購事由（前 500 字元）'),
            sa.Column('amount', sa.Integer(), nullable=False, comment='全案小計（未稅，新台幣元）—清單 API 可取得'),
            sa.Column('amount_tax', sa.Integer(), nullable=True, comment='營業稅（需 Detail API；業主確認必要顯示）'),
            sa.Column('amount_total', sa.Integer(), nullable=True, comment='全案總計（含稅，存 DB 備用，不在月報表顯示）'),
            sa.Column('status', sa.String(length=5), nullable=False, comment='F=已核准 / N=待審 / REJ=退回'),
            sa.Column('vendor1', sa.String(length=100), nullable=True, comment='廠商(一)名稱'),
            sa.Column('vendor2', sa.String(length=100), nullable=True, comment='廠商(二)名稱'),
            sa.Column('vendor3', sa.String(length=100), nullable=True, comment='廠商(三)名稱'),
            sa.Column('subject', sa.String(length=None), nullable=True, comment='主旨'),
            sa.Column('reason_31', sa.String(length=None), nullable=True, comment='31事由'),
            sa.Column('final_vendor_no', sa.String(length=30), nullable=True, comment='24最終擬定廠商編號（V-00156）'),
            sa.Column('final_vendor_name', sa.String(length=200), nullable=True, comment='25擬定廠商名稱'),
            sa.Column('final_payee', sa.String(length=200), nullable=True, comment='26擬定受款者'),
            sa.Column('final_bank_name', sa.String(length=200), nullable=True, comment='27擬定受款銀行'),
            sa.Column('final_bank_account', sa.String(length=50), nullable=True, comment='28擬定匯款帳號'),
            sa.Column('final_bank_code', sa.String(length=30), nullable=True, comment='29擬定銀行代號'),
            sa.Column('currency', sa.String(length=20), nullable=True, comment='幣別'),
            sa.Column('remark', sa.String(length=None), nullable=True, comment='備註欄位'),
            sa.Column('detail_synced', sa.Boolean(), nullable=False, comment='是否已完成 Detail API 同步（品項+廠商+稅額）'),
            sa.Column('raw_data_json', sa.String(length=None), nullable=False, comment='清單 API 原始 JSON（供欄位 mapping 補正）'),
            sa.Column('last_updated_at', sa.DateTime(), nullable=True, comment='Ragic「最後更新日期」原始值（台灣時區）'),
            sa.Column('sync_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='本次同步時間'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='首次建立時間'),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='最後更新時間（upsert 自動更新）'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('ragic_sheet_path', 'ragic_record_id', name='uq_tc_pr_sheet_record'),
        )
    _ensure_index('ix_tc_pr_applicant', 'taichung_purchase_requests', ['applicant'])
    _ensure_index('ix_tc_pr_company_dept', 'taichung_purchase_requests', ['company', 'department_display'])
    _ensure_index('ix_tc_pr_detail_synced', 'taichung_purchase_requests', ['detail_synced'])
    _ensure_index('ix_tc_pr_status_approved_date', 'taichung_purchase_requests', ['status', 'approved_date'])

    if not _has_table('taichung_purchase_request_items'):
        op.create_table('taichung_purchase_request_items',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('order_id', sa.Integer(), nullable=False, comment='FK → taichung_purchase_requests.id'),
            sa.Column('seq', sa.Integer(), nullable=False, comment='項次（子表格序號）'),
            sa.Column('product_name', sa.String(length=None), nullable=True, comment='產品名稱（品名）—月報表品名欄'),
            sa.Column('qty', sa.String(length=30), nullable=True, comment='數量（保留原始字串格式，如 10、10.5）'),
            sa.Column('unit', sa.String(length=20), nullable=True, comment='單位（件/尺/式/小時等）'),
            sa.Column('item_remark', sa.String(length=None), nullable=True, comment='品項備註'),
            sa.Column('vendor1_price', sa.Integer(), nullable=True, comment='廠商(一)金額'),
            sa.Column('vendor2_price', sa.Integer(), nullable=True, comment='廠商(二)金額'),
            sa.Column('vendor3_price', sa.Integer(), nullable=True, comment='廠商(三)金額'),
            sa.Column('selected_vendor', sa.String(length=100), nullable=True, comment='擬定廠商名稱—月報表廠商欄'),
            sa.Column('selected_unit_price', sa.Integer(), nullable=True, comment='擬定單價—月報表顯示'),
            sa.Column('selected_amount', sa.Integer(), nullable=True, comment='擬定金額—月報表品項金額欄'),
            sa.Column('taxable_amount', sa.Integer(), nullable=True, comment='應稅金額（台中額外欄位）'),
            sa.Column('is_confirmed', sa.Boolean(), nullable=True, comment='勾選（True=已選定此品項）'),
            sa.Column('sync_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='同步時間'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('order_id', 'seq', name='uq_tc_pri_order_seq'),
        )
    _ensure_index('ix_tc_pri_order_id', 'taichung_purchase_request_items', ['order_id'])

    if not _has_table('taichung_claim_requests'):
        op.create_table('taichung_claim_requests',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('company', sa.String(length=20), nullable=False, comment='公司別'),
            sa.Column('department_raw', sa.String(length=20), nullable=False, comment='Ragic 原始部門值'),
            sa.Column('department_display', sa.String(length=50), nullable=False, comment='Portal 顯示名稱（＝表單歸屬，如「客務部」）'),
            sa.Column('ragic_sheet_path', sa.String(length=100), nullable=False, comment='來源 Sheet 路徑，如 lequn-finance-department/6'),
            sa.Column('ragic_record_id', sa.String(length=30), nullable=False, comment='Ragic 記錄主鍵'),
            sa.Column('request_no', sa.String(length=30), nullable=False, comment='請款單號（系統唯一單號）'),
            sa.Column('department_request_no', sa.String(length=30), nullable=True, comment='部門請款編號（財請/工請/管請/專請等，各部門標籤不同）'),
            sa.Column('purchase_no', sa.String(length=30), nullable=True, comment='採購編號（有採購流程時填入）'),
            sa.Column('payment_no', sa.String(length=30), nullable=True, comment='付款編號（常空白）'),
            sa.Column('voucher_no', sa.String(length=30), nullable=True, comment='傳票號碼（底色偏橘，多數有）'),
            sa.Column('account_subject', sa.String(length=100), nullable=True, comment='會科（費用科目）'),
            sa.Column('apply_date', sa.Date(), nullable=True, comment='申請日期（YYYY-MM-DD）'),
            sa.Column('approved_date', sa.Date(), nullable=True, comment='核准日期（status=F 時有意義，月報以此為基準）'),
            sa.Column('applicant', sa.String(length=50), nullable=True, comment='申請人姓名'),
            sa.Column('payment_type', sa.String(length=20), nullable=True, comment='付款種類：零用金 / 匯款'),
            sa.Column('purpose_description', sa.String(length=None), nullable=True, comment='事由/說明（各部門標籤不同但統一映射）'),
            sa.Column('subtotal', sa.Integer(), nullable=True, comment='小計（未稅）'),
            sa.Column('tax', sa.Integer(), nullable=True, comment='營業稅'),
            sa.Column('total', sa.Integer(), nullable=True, comment='總計（含稅）'),
            sa.Column('payable_amount', sa.Integer(), nullable=True, comment='應付(繳)款（最終付款金額）'),
            sa.Column('total_amount', sa.Integer(), nullable=True, comment='總金額'),
            sa.Column('advance_offset', sa.Integer(), nullable=True, comment='沖預支'),
            sa.Column('currency', sa.String(length=20), nullable=True, comment='幣別'),
            sa.Column('payment_bank', sa.String(length=200), nullable=True, comment='付款銀行（公司出款銀行）'),
            sa.Column('payee', sa.String(length=100), nullable=True, comment='受款者（收款人/公司）'),
            sa.Column('bank_name', sa.String(length=100), nullable=True, comment='受款銀行（匯款型必填）'),
            sa.Column('bank_branch', sa.String(length=100), nullable=True, comment='受款銀行分行（匯款型必填）'),
            sa.Column('bank_account', sa.String(length=50), nullable=True, comment='匯款帳號（匯款型必填）'),
            sa.Column('payment_date', sa.Date(), nullable=True, comment='付款日期（預計付款日）'),
            sa.Column('status', sa.String(length=5), nullable=False, comment='F=已核准 / N=待審 / REJ=退回'),
            sa.Column('detail_synced', sa.Boolean(), nullable=False, comment='是否已完成品項子表同步'),
            sa.Column('raw_data_json', sa.String(length=None), nullable=False, comment='清單 API 原始 JSON（供欄位 mapping 補正）'),
            sa.Column('last_updated_at', sa.DateTime(), nullable=True, comment='Ragic「最後更新日期」原始值'),
            sa.Column('sync_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='本次同步時間'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='首次建立時間'),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='最後更新時間'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('ragic_sheet_path', 'ragic_record_id', name='uq_tc_cr_sheet_record'),
        )
    _ensure_index('ix_tc_cr_applicant', 'taichung_claim_requests', ['applicant'])
    _ensure_index('ix_tc_cr_company_dept', 'taichung_claim_requests', ['company', 'department_display'])
    _ensure_index('ix_tc_cr_detail_synced', 'taichung_claim_requests', ['detail_synced'])
    _ensure_index('ix_tc_cr_payment_type', 'taichung_claim_requests', ['payment_type'])
    _ensure_index('ix_tc_cr_status_approved_date', 'taichung_claim_requests', ['status', 'approved_date'])

    if not _has_table('taichung_claim_request_items'):
        op.create_table('taichung_claim_request_items',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('claim_id', sa.Integer(), nullable=False, comment='FK → taichung_claim_requests.id'),
            sa.Column('seq', sa.Integer(), nullable=False, comment='項次（子表格序號）'),
            sa.Column('item_name', sa.String(length=None), nullable=True, comment='產品名稱（品項/服務/工程項目）'),
            sa.Column('quantity', sa.String(length=30), nullable=True, comment='數量（保留原始字串格式）'),
            sa.Column('unit', sa.String(length=20), nullable=True, comment='單位（式/個/月等）'),
            sa.Column('item_note', sa.String(length=None), nullable=True, comment='品項備註（憑證號碼/付款月份等）'),
            sa.Column('proposed_vendor_amount', sa.Integer(), nullable=True, comment='擬定廠商金額（請款核心金額）'),
            sa.Column('invoice_no', sa.String(length=50), nullable=True, comment='發票號碼'),
            sa.Column('receipt_no', sa.String(length=50), nullable=True, comment='憑證號碼（油資/收據/其他）'),
            sa.Column('sync_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='同步時間'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('claim_id', 'seq', name='uq_tc_cri_claim_seq'),
        )
    _ensure_index('ix_tc_cri_claim_id', 'taichung_claim_request_items', ['claim_id'])



def downgrade() -> None:
    op.drop_table("taichung_claim_request_items")
    op.drop_table("taichung_claim_requests")
    op.drop_table("taichung_purchase_request_items")
    op.drop_table("taichung_purchase_requests")
