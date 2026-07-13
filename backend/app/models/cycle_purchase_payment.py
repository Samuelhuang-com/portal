"""
週期採購 — 請款單（獨立資料庫 cycle-purchase.db）

2026-07-11（第五期規劃，與 Samuel 確認）：
  1. 請款單關聯到「一張採購單」（po_id），不是單一驗收單。實務上供應商
     通常把同一張採購單底下好幾次到貨的貨款合併開一張發票，第四期也已經
     確認「一張採購單可以分好幾次驗收」，所以請款單改成用一個關聯子表
     （CyclePurchasePaymentReceiving）記錄「這張請款單涵蓋這張採購單底下
     的哪幾張驗收單」，範圍限制在同一張採購單內（不跨採購單合併請款）。
     一張採購單可以視情況開好幾張請款單（例如分期付款），但同一張驗收單
     只能被一張請款單涵蓋（UniqueConstraint on receiving_id），避免重複請款。
     只有狀態為 completed／discrepancy（已送出）的驗收單才能被請款單涵蓋，
     草稿驗收單（還沒確定數量）不行。
  2. 費用分攤明細（CyclePurchasePaymentAllocation）：建立請款單時，系統會
     自動回溯這張採購單的每個採購明細行 -> 對應的彙整列（同週期＋期別＋
     公司＋料號）-> 當初已核准的請購明細，依各部門原始請購數量的占比，
     試算出這張請款單金額應該怎麼分攤到各部門／成本中心／會計科目，
     寫成 suggested_amount（系統試算值，之後不會再變動，供追溯對照）；
     allocated_amount 預設等於 suggested_amount，財務人員可以再手動調整
     （調整後與試算值不同時，adjust_reason 必填，比照彙整單「調整量」的
     設計）。萬一某個採購明細行完全找不回原始請購部門資料（正常情況下
     不會發生，防呆用），department_id 會是 NULL，代表「系統無法自動分攤
     這筆金額，需要財務人員手動指定部門」。
  3. 送出請款單時（draft -> submitted），系統會檢查「分攤金額加總」是否
     等於「發票金額」；因為試算基礎是採購金額（未稅／未計入實際發票的
     稅金或折讓），跟發票金額本來就不一定會完全對上，兩者不同時要求填
     amount_diff_reason 才能送出，並自動寫一筆稽核紀錄（見
     cycle_purchase_audit.py）。
  4. 狀態機：draft（可編輯發票資訊／分攤明細）-> submitted（已送出，
     分攤明細鎖定不可再改）-> paying（付款中）-> paid（已付款）。
     這期先不做主管簽核關卡，有 cycle_purchase_finance 權限的人可以直接
     推進全部狀態（比照請購單「先做流程雛形，之後有需要再加簽核」的
     漸進式做法）。也先不做「取消」狀態，原規劃就只有這四個狀態。
"""
from sqlalchemy import (
    Column, Integer, String, Numeric, Text, DateTime, Date,
    ForeignKey, UniqueConstraint, func,
)

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchasePayment(CyclePurchaseBase):
    """週期採購請款單（一張採購單可以有多張請款單，例如分期付款）"""
    __tablename__ = "cycle_purchase_payments"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    payment_no     = Column(String(30), nullable=False, unique=True,
                             comment="請款單號（系統產生，如 PAY-202607-0001）")
    po_id          = Column(
        Integer, ForeignKey("cycle_purchase_pos.id", ondelete="RESTRICT"), nullable=False
    )

    invoice_no     = Column(String(50), nullable=False, comment="發票號碼")
    invoice_date   = Column(Date, nullable=False, comment="發票日期")
    invoice_amount = Column(Numeric(14, 2), nullable=False, comment="發票金額")

    status = Column(String(20), nullable=False, default="draft",
                     comment="狀態：draft | submitted | paying | paid")

    amount_diff_reason = Column(
        Text, nullable=True,
        comment="分攤金額加總與發票金額不同時的說明（送出時檢查，不同時必填）",
    )

    processor_user_id = Column(String(36), nullable=True, comment="財務處理人員（portal.db users.id，軟關聯）")
    processor_name    = Column(String(100), nullable=True, comment="財務處理人員姓名快照")

    notes      = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CyclePurchasePayment id={self.id} no={self.payment_no}>"


class CyclePurchasePaymentReceiving(CyclePurchaseBase):
    """請款單涵蓋的驗收單（多對一：一張請款單可以涵蓋同一張採購單底下的
    好幾張驗收單；一張驗收單只能被一張請款單涵蓋，避免重複請款）"""
    __tablename__ = "cycle_purchase_payment_receivings"
    __table_args__ = (
        UniqueConstraint("receiving_id", name="uq_cp_payment_receiving_once"),
    )

    id           = Column(Integer, primary_key=True, autoincrement=True)
    payment_id   = Column(
        Integer, ForeignKey("cycle_purchase_payments.id", ondelete="CASCADE"), nullable=False
    )
    receiving_id = Column(
        Integer, ForeignKey("cycle_purchase_receiving.id", ondelete="RESTRICT"), nullable=False
    )

    created_at = Column(DateTime, nullable=False, server_default=func.now())

    def __repr__(self):
        return f"<CyclePurchasePaymentReceiving payment_id={self.payment_id} receiving_id={self.receiving_id}>"


class CyclePurchasePaymentAllocation(CyclePurchaseBase):
    """請款單費用分攤明細（一列＝這張請款單分攤到某個部門／成本中心／
    會計科目的金額）"""
    __tablename__ = "cycle_purchase_payment_allocations"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    payment_id     = Column(
        Integer, ForeignKey("cycle_purchase_payments.id", ondelete="CASCADE"), nullable=False
    )

    company        = Column(String(50), nullable=False, comment="公司別（快照自採購單，僅供報表顯示用）")
    department_id  = Column(
        Integer, ForeignKey("cycle_purchase_departments.id", ondelete="RESTRICT"), nullable=True,
        comment="部門（系統依原始請購資料自動回溯；NULL 代表系統無法自動歸屬，"
                 "需要財務人員手動指定）",
    )
    cost_center_id = Column(
        Integer, ForeignKey("cycle_purchase_cost_centers.id", ondelete="SET NULL"), nullable=True,
        comment="成本中心（沿用原始請購單選的成本中心，可能為 NULL）",
    )
    account_code_id = Column(
        Integer, ForeignKey("cycle_purchase_account_codes.id", ondelete="SET NULL"), nullable=True,
        comment="會計科目（沿用原始請購明細選的會計科目，可能為 NULL）",
    )

    suggested_amount = Column(Numeric(12, 2), nullable=False, default=0,
                               comment="系統試算值（建立當下計算，之後不再變動，供追溯對照）")
    allocated_amount = Column(Numeric(12, 2), nullable=False, default=0,
                               comment="實際分攤金額，預設＝試算值，財務人員可調整")
    adjust_reason    = Column(Text, nullable=True,
                               comment="調整原因（allocated_amount ≠ suggested_amount 時必填）")

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CyclePurchasePaymentAllocation id={self.id} payment_id={self.payment_id} dept={self.department_id}>"
