"""
Application configuration — loaded from .env
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── General ───────────────────────────────────────────────────────────────
    APP_NAME: str = "集團 Portal"
    APP_ENV: str = "development"
    ENV: str = "development"            # alias，與 APP_ENV 同步
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── JWT（相容舊有命名）────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = ""            # 若設定，優先使用（相容原有程式）
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./portal.db"

    # ── Database — 週期採購（獨立檔案，不與 portal.db 共用）───────────────────
    # 2026-07-10 與 Samuel 確認：擔心 portal.db 持續變大，週期採購另開一個
    # SQLite 檔案，避免寫入量隨週期採購資料成長而拖累主要 portal.db。
    # 僅使用者／角色／權限沿用既有 portal.db（見 app/core/cycle_purchase_database.py）。
    CYCLE_PURCHASE_DATABASE_URL: str = "sqlite:///./cycle-purchase.db"

    # ── Database — 預算系統（獨立 SQLite 檔案，可透過 .env 覆寫路徑）──────────
    # 2026-07-15：與 Samuel 確認正式區/開發機 DB 統一搬離 OneDrive 同步資料夾。
    # 預設空字串 = 維持舊行為（相對於專案根目錄的 budget_system_v1.sqlite，
    # 見 app/core/budget_database.py）；若設定則直接使用此絕對路徑
    # （例如 C:/Portal_Data/budget_system_v1.sqlite）。
    BUDGET_DB_PATH: str = ""

    # ── Ragic — 連線基本設定 ──────────────────────────────────────────────────
    RAGIC_API_KEY: str = ""

    # Server 設定：支援兩種格式
    #   RAGIC_SERVER_URL = ap16.ragic.com   （完整 domain，原有程式使用）
    #   RAGIC_SERVER     = ap16             （server prefix，新模組使用）
    # 兩者填一即可；ragic_adapter 優先使用 RAGIC_SERVER_URL
    RAGIC_SERVER_URL: str = "ap16.ragic.com"
    RAGIC_SERVER: str = "ap16"              # 由 RAGIC_SERVER_URL 的第一段推導

    # 帳號名稱：兩個變數名稱都支援（相容原有程式）
    RAGIC_ACCOUNT_NAME: str = "intraragicapp"   # 原有程式使用
    RAGIC_ACCOUNT: str = "intraragicapp"        # 新模組使用

    # SSL & API 版本（原有程式參數）
    RAGIC_VERIFY_SSL: bool = True
    RAGIC_API_VERSION: str = "2025-01-01"
    RAGIC_NAMING: str = ""              # Ragic naming 參數（預設空字串）

    # ── Ragic — 原有程式（Sales Order）Sheet 設定 ────────────────────────────
    RAGIC_TAB: str = "ragicsales-order-management"
    RAGIC_SHEET_INDEX: int = 1

    # 設定檔路徑（原有程式使用）
    RAGIC_FIELD_LABELS_FILE: str = "app/config_data/field_labels.json"
    RAGIC_FORM_CONFIG_FILE: str = "app/config_data/sales_order_config.json"

    # ── Ragic — 客房保養 Sheet 設定（路徑與 Field ID 來自 forms_registry.json）──
    RAGIC_ROOM_MAINTENANCE_PATH: str = "ragicsales-order-management/1"

    # ── Ragic — 倉庫庫存 Sheet 設定 ───────────────────────────────────────────
    # URL: https://ap16.ragic.com/intraragicapp/ragicinventory/20008
    RAGIC_INVENTORY_PATH: str = "ragicinventory/20008"

    # ── Ragic — 客房保養明細 Sheet 設定（不同 Server & Account）────────────────
    # URL: https://ap12.ragic.com/soutlet001/report2/2
    RAGIC_ROOM_DETAIL_SERVER_URL: str = "ap12.ragic.com"
    RAGIC_ROOM_DETAIL_ACCOUNT: str = "soutlet001"
    RAGIC_ROOM_DETAIL_PATH: str = "report2/2"

    # ── Ragic — 飯店週期保養表（ap12 / soutlet001）────────────────────────────
    # Sheet 6：主表單  Sheet 8：附表明細
    RAGIC_PM_SERVER_URL: str = "ap12.ragic.com"
    RAGIC_PM_JOURNAL_PATH: str = "periodic-maintenance/6"
    RAGIC_PM_ITEMS_PATH: str   = "periodic-maintenance/8"

    # ── Ragic — 商場週期保養表（ap12 / soutlet001）────────────────────────────
    # Sheet 18：主表單（附表子表格內嵌同一 Sheet）
    RAGIC_MALL_PM_SERVER_URL:   str = "ap12.ragic.com"
    RAGIC_MALL_PM_ACCOUNT:      str = "soutlet001"
    RAGIC_MALL_PM_JOURNAL_PATH: str = "periodic-maintenance/18"
    RAGIC_MALL_PM_ITEMS_PATH:   str = "periodic-maintenance/18"

    # ── Ragic — 整棟工務每日巡檢 B4F（ap12 / soutlet001）──────────────────────
    # Sheet 2：full-building-inspection/2
    RAGIC_B4F_SERVER_URL: str = "ap12.ragic.com"
    RAGIC_B4F_ACCOUNT:    str = "soutlet001"
    RAGIC_B4F_SHEET_PATH: str = "full-building-inspection/2"

    # ── Ragic — IHG 客房保養（ap12 / soutlet001）─────────────────────────────
    # Sheet 4：periodic-maintenance/4
    RAGIC_IHG_RM_SERVER_URL:  str = "ap12.ragic.com"
    RAGIC_IHG_RM_ACCOUNT:     str = "soutlet001"
    RAGIC_IHG_RM_SHEET_PATH:  str = "periodic-maintenance/4"

    # ── Ragic — 保全巡檢（ap12 / soutlet001）─────────────────────────────────
    # Sheets 1, 2, 3, 4, 5, 6, 9：security-patrol/{id}
    RAGIC_SP_SERVER_URL: str = "ap12.ragic.com"
    RAGIC_SP_ACCOUNT:    str = "soutlet001"

    # 客房保養 Field ID（由 forms_registry.json 確認）
    RAGIC_FIELD_ROOM_NO: str = "1000006"        # 房號
    RAGIC_FIELD_INSPECT_ITEMS: str = "1000007"  # 檢查項目（多選）
    RAGIC_FIELD_WORK_ITEM: str = "1000008"      # 工作項目選擇
    RAGIC_FIELD_INSPECT_DT: str = "1000009"     # 檢查日期時間
    RAGIC_FIELD_DEPT: str = "1000019"           # 報修部門
    RAGIC_FIELD_CLOSE_DATE: str = "1000018"     # 結案日期
    RAGIC_FIELD_SUBTOTAL: str = "1000011"       # 小計
    RAGIC_FIELD_INCOMPLETE: str = "1000012"     # 未完成小計

    # ── Ragic — 商場工務報修（ap12 / soutlet001）────────────────────────────
    RAGIC_LUQUN_REPAIR_SERVER_URL: str = "ap12.ragic.com"
    RAGIC_LUQUN_REPAIR_ACCOUNT: str = "soutlet001"
    RAGIC_LUQUN_REPAIR_PATH: str = "luqun-public-works-repair-reporting-system/6"
    # 圖片 attachment 欄位存在 /8（同大直工務部）；清單抓 /6，圖片抓 /8
    RAGIC_LUQUN_REPAIR_IMAGE_PATH: str = "lequn-public-works/8"

    # ── Ragic — 大直工務部（ap12 / soutlet001）──────────────────────────────
    # URL: https://ap12.ragic.com/soutlet001/lequn-public-works/8?PAGEID=fV8
    RAGIC_DAZHI_REPAIR_SERVER_URL: str = "ap12.ragic.com"
    RAGIC_DAZHI_REPAIR_ACCOUNT: str = "soutlet001"
    RAGIC_DAZHI_REPAIR_PATH: str = "lequn-public-works/8"
    RAGIC_DAZHI_REPAIR_PAGEID: str = "fV8"

    # ── OpenAI ────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""

    # ── Anthropic Claude（知識庫 AI 問答）─────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""

    # ── AI 助理設定 ───────────────────────────────────────────────────────────
    # AI_ENABLED=false 時 AI router 不掛載（端點不存在）
    AI_ENABLED: bool = False
    # 使用 Haiku 模型：速度快、成本低，足夠結構化工單查詢使用
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"
    # 單次查詢最多回傳筆數，防止大量資料塞爆 Claude context
    AI_QUERY_MAX_ROWS: int = 50

    # ── Encryption（Fernet key）───────────────────────────────────────────────
    ENCRYPTION_KEY: str = ""

    # ── Scheduler ─────────────────────────────────────────────────────────────
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_DEFAULT_INTERVAL_MINUTES: int = 60

    # ── 郵件設定（報修未完成報表排程寄信）────────────────────────────────────
    MAIL_HOST:       str  = ""
    MAIL_SMTP_PORT:  int  = 25
    MAIL_POP3_PORT:  int  = 110
    MAIL_USERNAME:   str  = ""
    MAIL_PASSWORD:   str  = ""
    MAIL_FROM:       str  = ""
    MAIL_FROM_NAME:  str  = "維春集團報修系統"   # 寄件人顯示名稱
    MAIL_USE_TLS:    bool = False
    MAIL_USE_SSL:    bool = False

    # ── 便利屬性：統一取 server prefix ───────────────────────────────────────
    @property
    def ragic_server_prefix(self) -> str:
        """
        永遠回傳 server prefix（e.g. 'ap16'）。
        優先從 RAGIC_SERVER_URL 的第一段解析，
        若 RAGIC_SERVER_URL 為空則直接用 RAGIC_SERVER。
        """
        if self.RAGIC_SERVER_URL:
            return self.RAGIC_SERVER_URL.split(".")[0]
        return self.RAGIC_SERVER

    @property
    def ragic_account(self) -> str:
        """統一帳號名稱，RAGIC_ACCOUNT_NAME 優先。"""
        return self.RAGIC_ACCOUNT_NAME or self.RAGIC_ACCOUNT


settings = Settings()
