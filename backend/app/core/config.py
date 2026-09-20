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

    # ── Ragic — 週期採購「週採請購單」拋轉（ap12 / soutlet001）─────────────
    # URL: https://ap12.ragic.com/soutlet001/community-management-department/58
    # 這是**唯一一個 Portal 會「寫入」Ragic 的模組**，其餘 Ragic 設定都只讀。
    #
    # ⚠️ 2026-09-18 改版：拋轉目標由 sheet 57「週採採購單」改為
    #    sheet 58「★週採請購單」（Samuel 裁示：先前指到採購單是下錯任務，
    #    彙整單應該進請購單，由 Ragic 內建簽核流程簽核；sheet 57 自此停用）。
    #    sheet 58 是樂群**比價式請購單**的原樣複製（廠商(一)(二)(三) 三組比價欄
    #    ＋ Ragic 內建簽核流程 ＋「拋轉採購單／拋轉請款單」動作鈕），
    #    與 sheet 57 的欄位完全不同，欄位代號整批換過。
    #    設計背景與各欄位取捨見 services/cycle_purchase_ragic_push.py 檔頭。
    RAGIC_CP_SUMMARY_SERVER_URL: str = "ap12.ragic.com"
    RAGIC_CP_SUMMARY_ACCOUNT:    str = "soutlet001"
    RAGIC_CP_SUMMARY_PATH:       str = "community-management-department/58"
    # false ＝ 不真的寫 Ragic，退回 stub 行為（Portal 端狀態照常更新）。
    # 測試區想跑完整流程但不要污染 Ragic 正式資料時設 false。
    RAGIC_CP_SUMMARY_ENABLED:    bool = True
    RAGIC_CP_SUMMARY_TIMEOUT:    int = 60
    # 主表「申請人」是 Ragic 的使用者選單（唯讀欄，預設值 $USERNAME），
    # 2026-09-15 Samuel 裁示一律帶 Samuel。
    RAGIC_CP_SUMMARY_APPLICANT:  str = "Samuel"
    # ── 主表表頭的「部門」「會科」（2026-09-20 改版）────────────────────────
    # 真正的部門與會科自 2026-09-20 起**逐列放在子表**（Ragic 端已改好），主表
    # 這兩欄退化成表頭欄位。但它們在 Ragic 仍是**必填單選**，留空會被整筆退，
    # 所以 Portal 照送一個固定值把必填餵飽。
    #
    # ⚠️ 「部門」那欄的選單**沒有開放自訂選項**，只吃這七個字串之一：
    #     營業／管理／行銷／資訊／執董室／財務／工務
    #    所以不能送「多部門」這種說明文字。送「管理」代表「這張是管理部彙整出來
    #    的週採單」，實際歸屬一律看子表。
    # ⚠️ 「會科」那欄有開放自訂選項，但沿用既有清單裡的「雜項購置」最不會誤導。
    #
    # 👉 之後若把 Ragic 端那兩欄的「必填」取消掉，把這兩個設定改成空字串即可，
    #    Portal 就不再送、表頭留白，**不需要改程式**。
    RAGIC_CP_SUMMARY_HEADER_DEPT:  str = "管理"
    RAGIC_CP_SUMMARY_ACCOUNT_CODE: str = "雜項購置"
    # 子表「會計課目」逐列要送的字串格式。來源是料號對照表的會計科目
    # （公司＋部門＋料號 → account_code_id）。0919 會議舉的例子是「6238 清潔費」，
    # 所以預設是 代碼＋名稱；只想送名稱就改成 "{name}"。
    RAGIC_CP_SUMMARY_ACCOUNT_FORMAT: str = "{code} {name}"
    # 營業稅率：Portal 端只用於畫面顯示與對帳檢查，實際稅額是 Ragic 公式算的
    RAGIC_CP_SUMMARY_TAX_RATE:   float = 0.05

    # ── 主表欄位代號（sheet 58）──────────────────────────────────────────────
    RAGIC_CP_F_DOC_NO:     str = "1020805"  # 編號（自動編號 樂管購{yyyyMM}{00000}，不送）
    RAGIC_CP_F_DEPT:       str = "1020806"  # 部門（表頭，必填單選，送 RAGIC_CP_SUMMARY_HEADER_DEPT）
    RAGIC_CP_F_ACCOUNT:    str = "1020807"  # 會科（表頭，必填單選，送 RAGIC_CP_SUMMARY_ACCOUNT_CODE）
    RAGIC_CP_F_APPLY_DATE: str = "1020816"  # 申請日期（必填，格式 yyyy/MM/dd）
    RAGIC_CP_F_APPLICANT:  str = "1020808"  # 申請人（唯讀單選，預設 $USERNAME）
    RAGIC_CP_F_PURPOSE:    str = "1020809"  # 說明（必填，同時是這張表的標題欄 tf）
    RAGIC_CP_F_VENDOR:     str = "1020818"  # 廠商(一)（連結「廠商資料表」sheet 15，送廠商名稱）
    RAGIC_CP_F_REQUESTER:  str = "1020860"  # 請購人（必填，送該部門承辦人）
    # 2026-09-18 在 Ragic 端新增的 Portal 追蹤欄位
    RAGIC_CP_F_COMPANY:    str = "1020875"  # 公司別
    RAGIC_CP_F_CYCLE:      str = "1020876"  # 週期名稱
    RAGIC_CP_F_BATCH:      str = "1020877"  # 拋轉批次號
    RAGIC_CP_F_PUSHED_AT:  str = "1020878"  # 拋轉時間（日期型態，格式 yyyy/MM/dd HH:mm:ss）
    RAGIC_CP_F_NOTE:       str = "1020879"  # Portal備註
    # 下面幾個是 Ragic 公式欄位，**Portal 只讀不寫**（寫入後回讀來做空殼防呆）。
    # ⚠️ 公式只有在 POST 帶 doFormula=true 時才會算，見 cycle_purchase_ragic_push.py
    #
    # ⚠️ 2026-09-20 Ragic 端整理過金額區，欄位代號整批換過（Samuel 手動執行）：
    #    舊的「小計 1020838 / 稅 1020843 / 總計 1020849」這一組（比價版型裡
    #    廠商(一) 專用的那組）**已經被刪除**，改成下面這一組。刪除之前程式仍指著
    #    1020838，`record.get()` 永遠拿到 None ——「空殼防呆」因此**每推一張單都誤報**
    #    「小計是空的」，而真正該看的全案小計其實是對的。
    RAGIC_CP_F_GRAND_SUB:   str = "1020810"  # 全案小計 = O5（子表「金額2(選定)」加總）
    RAGIC_CP_F_TAX:         str = "1020846"  # 營業稅   = M10*0.05
    RAGIC_CP_F_GRAND_TOTAL: str = "1020852"  # 全案總計 = M10+M11
    # 2026-09-20 起這兩個都指到「全案」那一組：整理後表單只剩一組金額
    # （Portal 拋出來的單一張只有一家廠商，本來就沒有「各廠商各自小計」的概念）。
    RAGIC_CP_F_TOTAL:       str = "1020852"  # ＝全案總計，保留舊名給既有呼叫端
    # ⚠️ 1020840「小計」是比價版型留下來的**殘留欄位**，公式還是 `L5`
    #    （L 欄＝子表「上月累計預算」，整欄都空），所以它**永遠顯示 0**。
    #    空殼防呆刻意**不看它**（看了會被 "0" 騙過去），改看全案小計。
    #    這個欄位建議在 Ragic 端刪掉，留著只會讓人以為金額算錯。
    RAGIC_CP_F_SUBTOTAL:    str = "1020840"  # 小計（殘留欄位，=L5，恆為 0，勿當判斷依據）

    # ── 子表欄位代號（子表 id 1020873）───────────────────────────────────────
    RAGIC_CP_SUBTABLE:        str = "1020873"
    RAGIC_CP_SF_SEQ:          str = "1020821"  # 項次（$SEQ 自動序號，不送）
    RAGIC_CP_SF_ITEM_NAME:    str = "1020822"  # 產品名稱
    RAGIC_CP_SF_QTY:          str = "1020823"  # 數量
    RAGIC_CP_SF_UNIT:         str = "1020824"  # 單位
    RAGIC_CP_SF_NOTE:         str = "1020825"  # 品項備註
    RAGIC_CP_SF_PRICE:        str = "1020826"  # 單價（廠商一）
    RAGIC_CP_SF_AMOUNT:       str = "1020827"  # 金額（廠商一，公式 C5*F5，不送）
    # 2026-09-20 Ragic 端把原本「單價(二)/金額(二)/單價(三)/金額(三)」四欄
    # repurpose 成下面這四欄（改名＋清掉殘留公式＋型態由金額改回文字）。
    # ⚠️ 欄位代號沿用舊的，不是新建，所以不要以為換了號。
    RAGIC_CP_SF_ACCOUNT:      str = "1020828"  # 會計課目（文字，逐列；來源見 service 的 _line_account_name）
    RAGIC_CP_SF_DEPT:         str = "1020829"  # 部門（文字，逐列，直接送部門名稱如「工務部」）
    RAGIC_CP_SF_BUDGET_M:     str = "1020830"  # 本月預算（金額，人工填，Portal 不送）
    RAGIC_CP_SF_BUDGET_ACC:   str = "1020831"  # 上月累計預算（金額，人工填，Portal 不送）
    RAGIC_CP_SF_VENDOR:       str = "1020832"  # 擬定廠商（連結廠商資料表，送與廠商(一) 同一個名稱）
    RAGIC_CP_SF_CHOSEN:       str = "1020835"  # 勾選（打勾選項 Yes/No，送 Yes）
    RAGIC_CP_SF_ITEM_CODE:    str = "1020880"  # 料號（2026-09-18 新增）
    RAGIC_CP_SF_SUMMARY_ID:   str = "1020881"  # Portal彙整列ID（2026-09-18 新增）

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

    # ── 同步告警收件人（2026-08-13 新增）────────────────────────────────────
    # 逗號或分號分隔的 email。**留空＝不寄告警信**（開發機的預設行為）。
    # 起因：同步失敗、模組從未執行、回補假性完成，先前都沒有任何通知管道，
    #       只能靠人工翻 log 才會發現。詳見 services/sync_alert_service.py 檔頭。
    ALERT_EMAIL_TO:  str  = ""

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
