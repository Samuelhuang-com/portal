"""
Ragic 簽核掃描 SQLAlchemy Model（2026-11-12）
對應資料庫表：ragic_scan_fingerprint / ragic_scan_sheet / ragic_scan_hit
由 app.services.ragic_signoff_scan_sync 每日寫入（sync_tool 排程「Ragic簽核掃描」）。
"""
from sqlalchemy import Column, DateTime, Integer, String
from app.core.database import Base


class RagicScanFingerprint(Base):
    """記錄內容雜湊快照：用來判斷哪些記錄與上次不同（異動偵測）。"""
    __tablename__ = "ragic_scan_fingerprint"

    sheet_path = Column(String(200), primary_key=True, comment="Ragic 表單路徑，如 lequn-executive-office/9")
    record_id = Column(String(50), primary_key=True, comment="Ragic 記錄編號")
    fp = Column(String(64), nullable=False, comment="記錄內容 SHA-256")
    updated_at = Column(DateTime, nullable=False, comment="本次寫入時間（台北）")


class RagicScanSheet(Base):
    """每張表的掃描摘要與最後異動時間（編輯歷史取得）。"""
    __tablename__ = "ragic_scan_sheet"

    sheet_path = Column(String(200), primary_key=True)
    sheet_name = Column(String(200), nullable=False, default="")
    sheet_type = Column(String(50), nullable=False, default="")
    record_count = Column(Integer, nullable=False, default=0)
    changed_count = Column(Integer, nullable=False, default=0, comment="與上次快照不同的記錄數；基準執行為 0")
    last_edit_at = Column(DateTime, nullable=True, comment="最新編輯時間（台北）；基準或無異動時沿用上次值")
    scanned_at = Column(DateTime, nullable=False)


class RagicScanHit(Base):
    """簽核人含「楊國鼎」的記錄（每次掃描依表單整批取代）。"""
    __tablename__ = "ragic_scan_hit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sheet_path = Column(String(200), nullable=False, index=True)
    sheet_name = Column(String(200), nullable=False, default="")
    record_id = Column(String(50), nullable=False)
    link = Column(String(400), nullable=False)
    status_values = Column(String(300), nullable=False, default="")
    scanned_at = Column(DateTime, nullable=False)
