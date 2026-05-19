"""
每日數值登錄表 SQLAlchemy ORM Models

Ragic 來源：ap12.ragic.com/soutlet001/hotel-routine-inspection/{11,12,14,15}
4 張 Sheet 對應 4 種儀表類型，結構相同，以 sheet_key 欄位區分。

DB 架構：
  hotel_mr_batch   — 主表。一筆 = 一次抄表場次（對應 Ragic 一個 Row）
                     欄位：record_date / recorder_name / start_time / end_time / work_hours
  hotel_mr_reading — 扁平化摘要。與 batch 一對一，直接存 sheet_name（TYPE）及所有場次欄位，
                     方便跨表查詢與 Ragic App Directory 顯示。

sheet_key 對照：
  building-electric → hotel-routine-inspection/11  全棟水電錶
  mall-ac-electric  → hotel-routine-inspection/12  商場空調箱電錶
  tenant-electric   → hotel-routine-inspection/14  專櫃電錶
  tenant-water      → hotel-routine-inspection/15  專櫃水錶
"""
from sqlalchemy import Column, String, DateTime, func
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
                           comment="抄表人員（動態偵測欄位，名稱依 Ragic 表單而定）")
    start_time    = Column(String(20),  nullable=False, default="",
                           comment="抄表時間起（HH:MM 格式）")
    end_time      = Column(String(20),  nullable=False, default="",
                           comment="抄表時間迄（HH:MM 格式）")
    work_hours    = Column(String(20),  nullable=False, default="",
                           comment="工時計算（Ragic 計算欄位，如 1.5h）")

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
    """
    每日數值登錄場次摘要（扁平化，每場次一筆，方便跨表查詢）

    對應 hotel_mr_batch 的去正規化版本，直接包含所有關鍵欄位：
      sheet_name（表單類型）/ record_date / recorder_name / start_time / end_time / work_hours

    ragic_id = batch_ragic_id（一對一對應，無子記錄）
    """
    __tablename__ = "hotel_mr_reading"

    # ── 主鍵（= batch_ragic_id，一場次一筆）───────────────────────────────────
    ragic_id = Column(
        String(80), primary_key=True,
        comment="= batch_ragic_id（{sheet_key}_{ragic_row_id}）"
    )

    # ── 表單識別 ──────────────────────────────────────────────────────────────
    sheet_key  = Column(String(40),  nullable=False, default="",
                        comment="building-electric / mall-ac-electric / tenant-electric / tenant-water")
    sheet_name = Column(String(100), nullable=False, default="",
                        comment="表單類型：全棟水電錶 / 商場空調箱電錶 / 專櫃電錶 / 專櫃水錶")

    # ── 場次欄位 ──────────────────────────────────────────────────────────────
    record_date   = Column(String(20),  nullable=False, default="", comment="抄表日期 YYYY/MM/DD")
    recorder_name = Column(String(100), nullable=False, default="", comment="抄表人員")
    start_time    = Column(String(20),  nullable=False, default="", comment="抄表時間起 HH:MM")
    end_time      = Column(String(20),  nullable=False, default="", comment="抄表時間迄 HH:MM")
    work_hours    = Column(String(20),  nullable=False, default="", comment="工時計算")

    # ── 同步時間 ───────────────────────────────────────────────────────────────
    synced_at = Column(
        DateTime, nullable=False,
        server_default=func.now(), onupdate=func.now(),
        comment="最後同步時間"
    )

    def __repr__(self):
        return (
            f"<HotelMRReading {self.ragic_id} "
            f"type={self.sheet_name} date={self.record_date}>"
        )
