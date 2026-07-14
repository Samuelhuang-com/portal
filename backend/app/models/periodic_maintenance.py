"""
週期保養表 SQLAlchemy ORM Models

資料表：
  pm_batch          — 保養批次主表（2026-07-14 起由 Ragic Sheet 11 依「編號」欄位分組合成，
                       Sheet 6 已退役，不再有獨立 Ragic 記錄；ragic_id 對舊資料沿用當時的
                       Sheet 6 數字 ID，對新資料採用「編號」字串本身）
  pm_batch_item     — 保養項目明細（2026-07-14 起改為 Ragic Sheet 11 平表，取代原本 Sheet 8
                       內嵌子表格解析；item.ragic_id 改用 Sheet 11 自身的 _ragicId，不再是
                       "{batch_id}_{row_key}" 組合格式）
  pm_item_worklog   — 保養項目維修記錄明細（2026-07-14 同日新增：實測發現 Sheet 11 項目
                       底下其實有巢狀子表格「維修記錄」——原始遷移評估誤判為無子表格，
                       實際測試記錄（277/477）證實存在，欄位與 mall_pm Sheet24 完全相同
                       [項次/維修記錄/時間開始/時間結束/保養人員]，比照 MallPMItemWorklog
                       同一模式新增此表，「複製而非共用」，不與 mall_pm 共用 ORM 類別）

見 project memory project_hotel_pm_sheet11_migration.md 與
docs/FEASIBILITY_hotel_pm_sheet6_11.md（原始評估，2026-05-27）。
"""
import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Boolean, func, Index
from app.core.database import Base


class PeriodicMaintenanceBatch(Base):
    """保養批次主表（每月/每期一筆）"""
    __tablename__ = "pm_batch"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    # 2026-07-14 起：Sheet 6 已退役，批次沒有獨立 Ragic 記錄了。
    # 舊資料（遷移前已同步）沿用當時的 Sheet 6 數字 ID；新資料直接採用
    # Ragic Sheet 11「編號」欄位字串本身（如 "英週保202607-001"）當 ragic_id。
    ragic_id = Column(String(50), primary_key=True, comment="批次識別碼：舊資料為 Ragic Sheet 6 記錄 ID，新資料為「編號」字串本身")

    # ── 業務欄位 ──────────────────────────────────────────────────────────────
    journal_no    = Column(String(50),  nullable=False, default="", comment="保養日誌編號，如 英週保202604-001")
    period_month  = Column(String(10),  nullable=False, default="", comment="保養月份，如 2026/04")

    # ── Ragic 時間戳 ──────────────────────────────────────────────────────────
    # 2026-07-14 起：Sheet 11 平表沒有批次層級的建立/更新時間戳可用（Sheet 6 退役後
    # 不再查詢），新批次此二欄一律留空字串；沿用舊 Sheet 6 資料的既有值不受影響。
    ragic_created_at = Column(String(30), nullable=False, default="", comment="Ragic 建立時間（Sheet 6 退役後新批次恆為空）")
    ragic_updated_at = Column(String(30), nullable=False, default="", comment="Ragic 更新時間（Sheet 6 退役後新批次恆為空）")

    # ── Portal 同步時間 ────────────────────────────────────────────────────────
    synced_at = Column(DateTime, nullable=False, server_default=func.now(),
                       onupdate=func.now(), comment="最後同步時間")

    __table_args__ = (
        Index("ix_pm_batch_month", "period_month"),
    )

    def __repr__(self):
        return f"<PMBatch ragic_id={self.ragic_id} journal_no={self.journal_no} period_month={self.period_month}>"


class PeriodicMaintenanceItem(Base):
    """保養項目明細（每個保養任務一筆）"""
    __tablename__ = "pm_batch_item"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    # 2026-07-14 起：改用 Ragic Sheet 11 自身的 _ragicId（平表，每筆項目本身就是
    # 一筆獨立記錄）。舊資料（遷移前）為 "{batch_id}_{row_key}" 組合格式，同步時
    # 會被清除（見 periodic_maintenance_sync.sync_from_sheet11() 的舊格式清除邏輯）。
    ragic_id = Column(String(50), primary_key=True, comment="Ragic Sheet 11 記錄 ID（2026-07-14 前為 Sheet 8 組合格式，已停用）")

    # ── 外鍵關聯 ──────────────────────────────────────────────────────────────
    batch_ragic_id = Column(String(50), nullable=False, default="", comment="關聯 pm_batch.ragic_id")

    # ── 保養項目基本資料（Ragic 同步，不可被 Portal 編輯覆寫）──────────────────
    seq_no            = Column(Integer,     nullable=False, default=0,  comment="項次")
    category          = Column(String(50),  nullable=False, default="", comment="類別：水電、空調等")
    frequency         = Column(String(20),  nullable=False, default="", comment="頻率：月/季/半年/年")
    exec_months_raw   = Column(String(100), nullable=False, default="", comment="執行月份原始文字，如「2月 5月 8月 11月」")
    exec_months_json  = Column(Text,        nullable=False, default="[]", comment="解析後整數陣列 JSON，如 [2,5,8,11]")
    task_name         = Column(String(200), nullable=False, default="", comment="保養項目描述")
    location          = Column(String(100), nullable=False, default="", comment="區域/位置（Sheet 11 無此欄位，恆為空字串，2026-07-14 即時查證確認）")
    estimated_minutes = Column(Integer,     nullable=False, default=0,  comment="預估耗時（分鐘）")

    # ── 排定與執行欄位（Ragic 同步來源，Portal 亦可編輯）─────────────────────
    scheduled_date  = Column(String(10),  nullable=False, default="", comment="排定日期，如 04/23")
    scheduler_name  = Column(String(100), nullable=False, default="", comment="排定人員")
    executor_name   = Column(String(100), nullable=False, default="", comment="執行人員（多人以空格分隔）")
    # 2026-07-14 補充：優先取 Sheet 11 頂層「保養時間啟/迄」；該二欄為空時，改取
    # pm_item_worklog（巢狀「維修記錄」子表格）最早開始／最晚結束時間（比照 mall_pm
    # Sheet24 的做法，因為多數實測記錄頂層時間欄位是空的，實際時間記在子表格裡）
    start_time      = Column(String(30),  nullable=False, default="", comment="保養開始時間（Sheet 11「保養時間啟」，為空則取子表格 worklog 最早開始時間）")
    end_time        = Column(String(30),  nullable=False, default="", comment="保養結束時間（Sheet 11「保養時間迄」，為空則取子表格 worklog 最晚結束時間；仍空白=尚未完成）")
    ragic_work_minutes = Column(Integer, nullable=True,               comment="舊 Sheet 8「工時計算」欄位（分鐘）。Sheet 11 無此欄位，2026-07-14 後新同步不再寫入，改用 repair_hours")

    # ── Sheet 11「維修工時」欄位（2026-07-14 新增，比照 mall_pm Sheet24 語意：小時，Float）──
    repair_hours = Column(Float, nullable=True, comment="維修工時（小時），來源 Sheet 11「維修工時」欄位")

    # ── 附圖（2026-07-14 新增，來源 Ragic Sheet11「圖片上傳」欄位）───────────
    # 格式：JSON list，元素為 {"url": "...", "filename": "..."}（見 ragic_data_service.parse_images）
    images_json = Column(Text, nullable=True, default=None, comment="附圖 JSON，來源 Ragic Sheet11「圖片上傳」欄位")

    # ── 完成標記（Ragic 同步時自動計算：start_time + end_time 均有值 → True）──
    # Portal 亦可手動覆寫（設定後即受 portal_edited_at 保護）
    is_completed   = Column(Boolean, nullable=False, default=False, comment="保養是否完成（啟+迄均有值即自動標記）")

    # ── Portal 回填欄位（Portal 獨有，不被 Ragic 同步覆寫）──────────────────
    result_note    = Column(Text,    nullable=False, default="",    comment="執行結果備註")
    abnormal_flag  = Column(Boolean, nullable=False, default=False, comment="是否有異常")
    abnormal_note  = Column(Text,    nullable=False, default="",    comment="異常說明")

    # ── Portal 編輯時間戳（若設定，則 Ragic 同步不覆寫執行欄位）──────────────
    portal_edited_at = Column(DateTime, nullable=True, comment="Portal 最後編輯時間（保護機制）")

    # ── Ragic 時間戳 & 同步時間 ────────────────────────────────────────────────
    synced_at = Column(DateTime, nullable=False, server_default=func.now(),
                       onupdate=func.now(), comment="最後同步時間")

    __table_args__ = (
        Index("ix_pm_item_batch",     "batch_ragic_id"),
        Index("ix_pm_item_completed", "is_completed"),
        Index("ix_pm_item_abnormal",  "abnormal_flag"),
    )

    # ── Helper ────────────────────────────────────────────────────────────────
    def get_exec_months(self) -> list[int]:
        try:
            return json.loads(self.exec_months_json or "[]")
        except Exception:
            return []

    def get_images(self) -> list:
        if not self.images_json:
            return []
        try:
            return json.loads(self.images_json)
        except Exception:
            return []

    def __repr__(self):
        return f"<PMItem ragic_id={self.ragic_id} seq_no={self.seq_no} task_name={self.task_name[:20]}>"


class PeriodicMaintenanceItemWorklog(Base):
    """
    飯店週期保養項目維修記錄明細（每個保養項目底下可有多筆維修記錄）

    資料來源：Ragic Sheet 11（週期保養日誌）每筆記錄的巢狀子表格「維修記錄」
              （Ragic 內部 key 為 _subtable_<動態數字>，需以 fetch_one() 逐筆項目
              取得，無法從 fetch_all()/listing 模式取得）

    2026-07-14 同日新增：原始遷移評估（見 docs/FEASIBILITY_hotel_pm_sheet6_11.md）
    誤判 Sheet 11 無巢狀子表格，因此當時設計的 PMItemDetailDrawer.tsx 只做單筆時間+
    附圖版本；使用者實測記錄（ragic_id 277/477）證實 Sheet 11 其實有子表格，欄位與
    mall_pm Sheet24 完全相同，因此比照 MallPMItemWorklog 同一模式補上此表，並將
    Drawer 改為多筆維修記錄列表版本（比照 MallPMItemWorklogDrawer.tsx）。
    """
    __tablename__ = "pm_item_worklog"

    # ── 主鍵：{item_ragic_id}_{sub_ragic_id}（sub_ragic_id 為子表格內部序號，非全域唯一）──
    ragic_id = Column(String(50), primary_key=True, comment="格式 {item_ragic_id}_{sub_ragic_id}")

    # ── 外鍵關聯 ──────────────────────────────────────────────────────────────
    item_ragic_id = Column(String(50), nullable=False, default="", comment="關聯 pm_batch_item.ragic_id")

    # ── Ragic 子表格欄位（同步來源，不可被 Portal 編輯覆寫）───────────────────
    seq_no      = Column(Integer,     nullable=False, default=0,  comment="子表格項次")
    repair_note = Column(Text,        nullable=False, default="", comment="維修記錄文字")
    start_time  = Column(String(30),  nullable=False, default="", comment="時間開始，完整日期時間字串")
    end_time    = Column(String(30),  nullable=False, default="", comment="時間結束，完整日期時間字串")
    staff_name  = Column(String(100), nullable=False, default="", comment="保養人員")

    # ── 同步時間 ───────────────────────────────────────────────────────────────
    synced_at = Column(DateTime, nullable=False, server_default=func.now(),
                       onupdate=func.now(), comment="最後同步時間")

    __table_args__ = (
        Index("ix_pm_item_worklog_item", "item_ragic_id"),
    )

    def __repr__(self):
        return f"<PMItemWorklog ragic_id={self.ragic_id} item_ragic_id={self.item_ragic_id}>"
