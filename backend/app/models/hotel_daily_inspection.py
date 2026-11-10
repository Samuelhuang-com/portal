"""
飯店每日巡檢 SQLAlchemy ORM Models【寬表格 Pivot 架構】

2026-11-10 改版（比照商場工務巡檢）：一個頁籤（sheet_key）可對應多張 Ragic Sheet（現行＋封存），
來源登錄見 app/services/hotel_daily_inspection_sources.py。

DB 架構：
  hotel_di_inspection_batch — 一筆 = 一次巡檢場次（對應 Ragic 一個 Row）
  hotel_di_inspection_item  — 一筆 = 一個設備欄位結果（Sync 時動態 pivot 產生）

場次 ID：'{source_key}_{Ragic Row ID}'（例：rf_17_0、4f_a32_12、rf_legacy_5）

巡檢結果狀態（item.result_status，由 hotel_daily_inspection_sheet.item_status 判定）：
  normal / abnormal / pending / unchecked / measure（填數字欄）/ note（附註欄）

sheet_key（頁籤）：rf / 5f-10f / 4f / b1f-hv / b1f-office / b4f-water / b4f-ac
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, func
from app.core.database import Base


class HotelDIBatch(Base):
    """飯店每日巡檢場次（每筆 Ragic 記錄 = 一次完整巡檢）"""
    __tablename__ = "hotel_di_inspection_batch"

    # ── 主鍵（"{sheet_key}_{ragic_row_id}"，避免不同 Sheet 衝突）────────────────
    ragic_id = Column(
        String(80), primary_key=True,
        comment="複合鍵：{sheet_key}_{ragic_row_id}"
    )

    # ── Sheet 識別 ────────────────────────────────────────────────────────────
    sheet_key  = Column(String(20),  nullable=False, default="", comment="rf / 5f-10f / 4f / b1f-hv / b1f-office / b4f-water / b4f-ac")
    sheet_name = Column(String(100), nullable=False, default="", comment="人類可讀的 Sheet 名稱")

    # ── 場次欄位 ──────────────────────────────────────────────────────────────
    inspection_date = Column(String(20),  nullable=False, default="", comment="巡檢日期 YYYY/MM/DD（從開始時間萃取）")
    inspector_name  = Column(String(100), nullable=False, default="", comment="巡檢人員")
    start_time      = Column(String(30),  nullable=False, default="", comment="開始巡檢時間（原始值）")
    end_time        = Column(String(30),  nullable=False, default="", comment="巡檢結束時間（原始值）")
    work_hours      = Column(String(20),  nullable=False, default="", comment="工時計算")
    estimated_minutes = Column(Integer, nullable=True, comment="預估時間（分鐘，Ragic 預排時間）")

    # ── 同步時間 ───────────────────────────────────────────────────────────────
    synced_at = Column(
        DateTime, nullable=False,
        server_default=func.now(), onupdate=func.now(),
        comment="最後同步時間"
    )

    def __repr__(self):
        return (
            f"<HotelDIBatch ragic_id={self.ragic_id} "
            f"sheet={self.sheet_key} date={self.inspection_date}>"
        )


class HotelDIItem(Base):
    """飯店每日巡檢設備項目（每個設備欄位一筆，由 Sync 時動態 pivot 產生）"""
    __tablename__ = "hotel_di_inspection_item"

    # ── 主鍵（"{batch_ragic_id}_{seq_no}"）────────────────────────────────────
    ragic_id = Column(
        String(100), primary_key=True,
        comment="複合鍵：{batch_ragic_id}_{seq_no}"
    )

    # ── 外鍵 ──────────────────────────────────────────────────────────────────
    batch_ragic_id = Column(
        String(80), nullable=False, default="",
        comment="所屬場次 ragic_id（hotel_di_inspection_batch.ragic_id）"
    )
    sheet_key = Column(String(20), nullable=False, default="", comment="所屬 Sheet key（冗餘欄位，方便跨 Sheet 查詢）")

    # ── 項目資訊 ──────────────────────────────────────────────────────────────
    seq_no    = Column(Integer,     nullable=False, default=0,  comment="項次（依動態偵測欄位順序）")
    item_name = Column(String(200), nullable=False, default="", comment="設備/項目名稱（Ragic 欄位名）")

    # ── 巡檢結果 ──────────────────────────────────────────────────────────────
    result_raw    = Column(Text,        nullable=False, default="",          comment="原始值（正常/異常/待處理/空白；附件欄位為檔名清單）")
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
            f"<HotelDIItem {self.ragic_id} "
            f"item={self.item_name[:20]} status={self.result_status}>"
        )
