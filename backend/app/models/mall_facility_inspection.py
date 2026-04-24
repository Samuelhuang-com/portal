"""
春大直商場工務每日巡檢 SQLAlchemy ORM Models【寬表格 Pivot 架構】

Ragic 來源：ap12.ragic.com/soutlet001/mall-facility-inspection/{2,3,4,5,7}
5 張 Sheet 對應 5 個樓層，結構相同，以 sheet_key 欄位區分。

DB 架構：
  mall_fi_inspection_batch — 一筆 = 一次巡檢場次（對應 Ragic 一個 Row）
  mall_fi_inspection_item  — 一筆 = 一個設備欄位結果（Sync 時動態 pivot 產生）

巡檢結果狀態（item.result_status）：
  normal    — 正常（OK / 正常 / V / v / O）
  abnormal  — 異常
  pending   — 待處理 / 待修
  unchecked — 空白 / 未填
  note      — 文字備註欄位（非評分項目）

sheet_key 對照：
  4f      → mall-facility-inspection/2
  3f      → mall-facility-inspection/3
  1f-3f   → mall-facility-inspection/4
  1f      → mall-facility-inspection/5
  b1f-b4f → mall-facility-inspection/7
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, func
from app.core.database import Base


class MallFIBatch(Base):
    """商場工務巡檢場次（每筆 Ragic 記錄 = 一次完整巡檢）"""
    __tablename__ = "mall_fi_inspection_batch"

    # ── 主鍵（"{sheet_key}_{ragic_row_id}"，避免不同 Sheet 衝突）────────────────
    ragic_id = Column(
        String(80), primary_key=True,
        comment="複合鍵：{sheet_key}_{ragic_row_id}"
    )

    # ── Sheet 識別 ────────────────────────────────────────────────────────────
    sheet_key  = Column(String(20),  nullable=False, default="", comment="4f / 3f / 1f-3f / 1f / b1f-b4f")
    sheet_name = Column(String(100), nullable=False, default="", comment="人類可讀的 Sheet 名稱")

    # ── 場次欄位 ──────────────────────────────────────────────────────────────
    inspection_date = Column(String(20),  nullable=False, default="", comment="巡檢日期 YYYY/MM/DD（從開始時間萃取）")
    inspector_name  = Column(String(100), nullable=False, default="", comment="巡檢人員")
    start_time      = Column(String(30),  nullable=False, default="", comment="開始巡檢時間（原始值）")
    end_time        = Column(String(30),  nullable=False, default="", comment="巡檢結束時間（原始值）")
    work_hours      = Column(String(20),  nullable=False, default="", comment="工時計算")

    # ── 同步時間 ───────────────────────────────────────────────────────────────
    synced_at = Column(
        DateTime, nullable=False,
        server_default=func.now(), onupdate=func.now(),
        comment="最後同步時間"
    )

    def __repr__(self):
        return (
            f"<MallFIBatch ragic_id={self.ragic_id} "
            f"sheet={self.sheet_key} date={self.inspection_date}>"
        )


class MallFIItem(Base):
    """商場工務巡檢設備項目（每個設備欄位一筆，由 Sync 時動態 pivot 產生）"""
    __tablename__ = "mall_fi_inspection_item"

    # ── 主鍵（"{batch_ragic_id}_{seq_no}"）────────────────────────────────────
    ragic_id = Column(
        String(100), primary_key=True,
        comment="複合鍵：{batch_ragic_id}_{seq_no}"
    )

    # ── 外鍵 ──────────────────────────────────────────────────────────────────
    batch_ragic_id = Column(
        String(80), nullable=False, default="",
        comment="所屬場次 ragic_id（mall_fi_inspection_batch.ragic_id）"
    )
    sheet_key = Column(String(20), nullable=False, default="", comment="所屬 Sheet key（冗餘欄位，方便跨 Sheet 查詢）")

    # ── 項目資訊 ──────────────────────────────────────────────────────────────
    seq_no    = Column(Integer,     nullable=False, default=0,  comment="項次（依動態偵測欄位順序）")
    item_name = Column(String(200), nullable=False, default="", comment="設備/項目名稱（Ragic 欄位名）")

    # ── 巡檢結果 ──────────────────────────────────────────────────────────────
    result_raw    = Column(String(50),  nullable=False, default="",          comment="原始值（正常/異常/待處理/空白）")
    result_status = Column(String(20),  nullable=False, default="unchecked", comment="正規化：normal/abnormal/pending/unchecked/note")
    abnormal_flag = Column(Boolean,     nullable=False, default=False,        comment="是否有異常旗標")
    is_note       = Column(Boolean,     nullable=False, default=False,        comment="是否為文字備註欄位（非評分項目）")

    # ── 同步時間 ───────────────────────────────────────────────────────────────
    synced_at = Column(
        DateTime, nullable=False,
        server_default=func.now(), onupdate=func.now(),
        comment="最後同步時間"
    )

    def __repr__(self):
        return (
            f"<MallFIItem {self.ragic_id} "
            f"item={self.item_name[:20]} status={self.result_status}>"
        )
