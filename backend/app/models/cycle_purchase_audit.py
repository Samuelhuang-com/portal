"""
週期採購 — 異常稽核紀錄（獨立資料庫 cycle-purchase.db）

2026-07-11（第五期規劃，與 Samuel 確認）：
原規劃的事件類型涵蓋 6 種（補填 backfill／逾期 overdue／缺貨 shortage／
替代品 substitute／驗收差異 receiving_variance／請款差異 payment_variance），
但「補填」「逾期」「缺貨」「替代品」目前系統都沒有對應的既有流程可以觸發
（沒有補件機制、沒有缺貨標記），做了也是永遠空的稽核紀錄。這期先只做
「驗收差異」「請款差異」這兩種的自動記錄：
  - 驗收單送出時，若有明細行差異數量≠0（見 cycle_purchase_receiving_service.
    submit_receiving），系統自動為每一筆有差異的明細行寫一筆稽核紀錄，
    不需要人工登錄。
  - 請款單送出時，若分攤金額加總與發票金額不同（見
    cycle_purchase_payment_service.submit_payment），系統自動寫一筆稽核紀錄。
其餘 4 種事件類型先保留在 event_type 的可能值清單裡（避免以後要 migrate
資料表），但這期不做觸發流程，之後有對應流程（例如「缺貨標記」）時再接上。

document_type／document_id 是應用層軟關聯（比照本專案一貫原則），不建
跨表 FK，因為同一個 document_id 在不同 document_type 下會撞號（例如
request 的 id=5 跟 receiving 的 id=5 是完全不同的東西）。document_no 是
建立當下的單號快照，供列表顯示不必額外 join。

查看權限：cycle_purchase_admin（比較偏管理／治理性質，不是一般人員需要
看到的資訊；這期沒有另外開一個 cycle_purchase_audit 權限）。
本表只有系統內部寫入（無 POST/PUT/DELETE endpoint），前端只提供
GET /audit-log 列表查詢。
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchaseAuditLog(CyclePurchaseBase):
    """週期採購異常稽核紀錄（append-only，沒有 updated_at，紀錄本身不可修改）"""
    __tablename__ = "cycle_purchase_audit_logs"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    document_type  = Column(String(20), nullable=False,
                             comment="關聯類型：request | po | receiving | payment")
    document_id    = Column(Integer, nullable=False, comment="關聯單據 id（軟關聯，依 document_type 對應不同表）")
    document_no    = Column(String(30), nullable=False, comment="關聯單號快照（列表顯示用，不必額外 join）")

    event_type     = Column(String(30), nullable=False,
                             comment="事件類型：backfill(補填) | overdue(逾期) | shortage(缺貨) | "
                                      "substitute(替代品) | receiving_variance(驗收差異) | "
                                      "payment_variance(請款差異)。這期只有後兩種會被系統自動觸發。")
    description    = Column(Text, nullable=False, comment="事件說明")

    operator_user_id = Column(String(36), nullable=True, comment="操作人員（portal.db users.id，軟關聯）")
    operator_name     = Column(String(100), nullable=True, comment="操作人員姓名快照")

    old_value  = Column(Text, nullable=True, comment="原始值（文字快照，依事件類型內容不同）")
    new_value  = Column(Text, nullable=True, comment="變更後值（文字快照，依事件類型內容不同）")

    created_at = Column(DateTime, nullable=False, server_default=func.now())

    def __repr__(self):
        return f"<CyclePurchaseAuditLog id={self.id} type={self.document_type} event={self.event_type}>"
