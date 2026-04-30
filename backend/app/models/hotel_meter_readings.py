"""
每日數值登錄表 SQLAlchemy ORM Models【寬表格 Pivot 架構】

Ragic 來源：ap12.ragic.com/soutlet001/hotel-routine-inspection/{11,12,14,15}
4 張 Sheet 對應 4 種儀表類型，結構相同，以 sheet_key 欄位區分。

DB 架構：
  hotel_mr_batch   — 一筆 = 一次登錄（對應 Ragic 一個 Row）
  hotel_mr_reading — 一筆 = 一個儀表讀數欄位（Sync 時動態 pivot 產生）

sheet_key 對照：
  building-electric → hotel-routine-inspection/11  全棟電錶
  mall-ac-electric  → hotel-routine-inspection/12  商場空調箱電錶
  tenant-electric   → hotel-routine-inspection/14  專櫃電錶
  tenant-water      → hotel-routine-inspection/15  專櫃水錶
"""
from sqlalchemy import Column, String, Integer, DateTime, func
from app.core.database import Base


class HotelMRBatch(Base):
    """每日數值登錄場次（每筆 Ragic 記錄 = 一次完整登錄）"""
    __tablename__ = "hotel_mr_batch"

    # ── 主鍵（"{sheet_key}_{ragic_row_id}"，避免不同 Sheet 衝突）────────────────
    ragic_id = Column(
        String(80), primary_key=True,
        comment="複合鍵：{sheet_key}_{ragic_row_id}"
    )

    # ── Sheet 識別 ────────────────────────────────────────────────────────────
    sheet_key  = Column(String(40),  nullable=False, default="",
                        comment="building-electric / mall-ac-electric / tenant-electric / tenant-water")
    sheet_name = Column(String(100), nullable=False, default="",
                        comment="人類可讀的 Sheet 名稱（全棟電錶 etc.）")

    # ── 場次欄位 ──────────────────────────────────────────────────────────────
    record_date   = Column(String(20),  nullable=False, default="",
                           comment="登錄日期 YYYY/MM/DD（從 Ragic 日期欄位萃取）")
    recorder_name = Column(String(100), nullable=False, default="",
                           comment="登錄人員（動態偵測欄位，名稱依 Ragic 表單而定）")

    # ── 同步時間 ───────────────────────────────────────────────────────────────
    synced_at = Column(
        DateTime, nullable=False,
        server_default=func.now(), onupdate=func.now(),
        comment="最後同步時間"
    )

    def __repr__(self):
        return (
            f"<HotelMRBatch ragic_id={self.ragic_id} "
            f"sheet={self.sheet_key} date={self.record_date}>"
        )


class HotelMRReading(Base):
    """每日數值登錄儀表讀數（每個儀表欄位一筆，由 Sync 時動態 pivot 產生）"""
    __tablename__ = "hotel_mr_reading"

    # ── 主鍵（"{batch_ragic_id}_{seq_no}"）────────────────────────────────────
    ragic_id = Column(
        String(120), primary_key=True,
        comment="複合鍵：{batch_ragic_id}_{seq_no}"
    )

    # ── 外鍵 ──────────────────────────────────────────────────────────────────
    batch_ragic_id = Column(
        String(80), nullable=False, default="",
        comment="所屬場次 ragic_id（hotel_mr_batch.ragic_id）"
    )
    sheet_key = Column(String(40), nullable=False, default="",
                       comment="所屬 Sheet key（冗餘欄位，方便跨 Sheet 查詢）")

    # ── 項目資訊 ──────────────────────────────────────────────────────────────
    seq_no     = Column(Integer,     nullable=False, default=0,
                        comment="項次（依動態偵測欄位順序）")
    meter_name = Column(String(200), nullable=False, default="",
                        comment="儀表 / 設備名稱（Ragic 欄位名）")

    # ── 讀數值 ────────────────────────────────────────────────────────────────
    reading_value = Column(String(100), nullable=False, default="",
                           comment="儀表讀數原始值（保留 String 彈性，可能含單位）")

    # ── 同步時間 ───────────────────────────────────────────────────────────────
    synced_at = Column(
        DateTime, nullable=False,
        server_default=func.now(), onupdate=func.now(),
        comment="最後同步時間"
    )

    def __repr__(self):
        return (
            f"<HotelMRReading {self.ragic_id} "
            f"meter={self.meter_name[:20]} value={self.reading_value}>"
        )
