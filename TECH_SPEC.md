---
name: portal-tech-spec
description: >
  集團 Portal 系統技術規格書。適用於以下情境：
  開發新功能模組、設計資料庫 Schema、串接 Ragic API、
  設計 FastAPI 路由、實作 RBAC 權限、建立 React 元件、
  撰寫同步排程或報表邏輯。本規格書定義了整個系統的
  技術決策、架構設計、命名慣例與開發流程，所有 AI 協作
  任務應優先參考本文件以確保一致性。
version: 1.0.0
last_updated: 2026-04-08
---
# 集團 Portal 系統 — 技術規格書

## 目錄

1. [專案概述](#1-專案概述)
2. [技術選型](#2-技術選型)
3. [系統架構](#3-系統架構)
4. [資料庫 Schema](#4-資料庫-schema)
5. [Ragic API 整合規格](#5-ragic-api-整合規格)
6. [身份驗證與 RBAC 權限](#6-身份驗證與-rbac-權限)
7. [FastAPI 專案結構](#7-fastapi-專案結構)
8. [React 前端結構](#8-react-前端結構)
9. [API 路由設計](#9-api-路由設計)
10. [同步排程設計](#10-同步排程設計)
11. [報表引擎設計](#11-報表引擎設計)
12. [環境變數與設定](#12-環境變數與設定)
13. [命名慣例](#13-命名慣例)
14. [開發流程](#14-開發流程)
15. [部署規格](#15-部署規格)

---

## 1. 專案概述

### 背景

集團旗下包含總公司 + 飯店 ×2 + 商場 ×2，共 5 個據點、200 人以下使用者。現有 Ragic 系統已完成 Phase 1 作業數位化，本專案建立獨立的 Portal 層，提供：

- 跨據點統一入口（Portal）
- 多模組管理（各據點業務）
- 跨據點 Dashboard 與報表
- 細粒度角色權限（RBAC）
- Ragic 資料同步與快照

### 設計原則

- **Ragic 不替換，加層疊加**：Ragic 繼續作為作業系統，Portal 提供報表、整合、分析層。
- **快照優先**：Dashboard 和報表讀 DATA_SNAPSHOTS，不即時打 Ragic API。
- **多租戶設計**：所有資料表都有 `tenant_id`，權限從 DB 層就已隔離。
- **加密敏感資料**：Ragic API Key 用 Fernet 加密後存入 DB。

---

## 2. 技術選型

### 後端

| 項目        | 選擇                  | 版本   | 理由                                  |
| ----------- | --------------------- | ------ | ------------------------------------- |
| 語言        | Python                | 3.12+  | AI/報表生態最豐富                     |
| 框架        | FastAPI               | 0.111+ | 自動 OpenAPI、async 支援、Pydantic v2 |
| ORM         | SQLAlchemy            | 2.0+   | async 支援、型別安全                  |
| 資料驗證    | Pydantic              | 2.x    | 與 FastAPI 原生整合                   |
| 排程        | APScheduler           | 3.x    | cron 語法、async job                  |
| 報表        | pandas + openpyxl     | latest | 資料處理與 Excel 匯出                 |
| 加密        | cryptography (Fernet) | latest | API Key 加密存放                      |
| HTTP Client | httpx                 | latest | async HTTP，用於打 Ragic API          |
| 權限        | casbin                | latest | RBAC policy engine                    |
| 測試        | pytest + httpx        | latest | -                                     |

### 前端

| 項目 | 選擇               | 版本   | 理由                  |
| ---- | ------------------ | ------ | --------------------- |
| 框架 | React              | 18+    | 生態成熟              |
| 語言 | TypeScript         | 5.x    | 型別安全              |
| UI   | Ant Design Pro     | 6.x    | 企業 Portal 元件完整  |
| 圖表 | Recharts / ECharts | latest | Dashboard 視覺化      |
| 狀態 | Zustand            | 4.x    | 輕量、TypeScript 友好 |
| 路由 | React Router       | 6.x    | -                     |
| HTTP | axios              | 1.x    | 攔截器管理 JWT        |
| 建置 | Vite               | 5.x    | 快速 HMR              |

### 資料庫

| 項目         | 選擇          | 理由                                |
| ------------ | ------------- | ----------------------------------- |
| 主資料庫     | PostgreSQL 16 | 多並發寫入、JSONB 支援、免費        |
| 開發環境     | SQLite        | 快速起步，SQLAlchemy 只需改連線字串 |
| 快取（選用） | Redis         | Session、排程鎖（Phase 2 引入）     |

---

## 3. 系統架構

```
┌──────────────────────────────────────────────────────────────────┐
│                        React + TypeScript                         │
│   Portal Router · Auth Pages · Dashboard · Module Pages          │
│   RBAC Guards · API Service (axios) · State (Zustand)            │
│   Ant Design Pro · Recharts / ECharts                            │
└─────────────────────────┬────────────────────────────────────────┘
                          │ HTTPS REST + JWT
┌─────────────────────────▼────────────────────────────────────────┐
│                      FastAPI Backend                              │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │ Authentication   │  │ RBAC Permissions │  │ Ragic Adapter  │◄─┼──┐
│  │ JWT · OAuth2     │  │ Casbin · tenant  │  │ fetch·cache    │  │  │
│  └─────────────────┘  └──────────────────┘  └────────────────┘  │  │
│  ┌─────────────────┐  ┌──────────────────┐                      │  │
│  │ Sync Scheduler  │  │ Report Engine    │                      │  │
│  │ APScheduler     │  │ pandas·openpyxl  │                      │  │
│  └─────────────────┘  └──────────────────┘                      │  │
│  Pydantic · SQLAlchemy 2.0 · uvicorn                            │  │
└─────────────────────────┬────────────────────────────────────────┘  │
                          │ SQLAlchemy ORM                             │
┌─────────────────────────▼────────────────────────────────────────┐  │
│                       PostgreSQL 16                               │  │
│  Users · Roles · Tenants · Ragic Connections · Snapshots         │  │
└──────────────────────────────────────────────────────────────────┘  │
                                                                       │
┌──────────────────────────────────────────────────────────────────┐  │
│                      Ragic Cloud API                              │──┘
│  REST · HTTPS · JSON · API Key Auth (HTTP Basic)                 │
│  GET  /{account}/{tab}/{sheet}?v=3&api                           │
│  POST /{account}/{tab}/{sheet}?api                               │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. 資料庫 Schema

### 4.1 說明

- 主鍵全部使用 `UUID`（`gen_random_uuid()`）
- 所有時間欄位使用 `TIMESTAMP WITH TIME ZONE`（UTC 存放）
- 敏感欄位（API Key）在應用層加密後存入，DB 層不解密
- JSONB 用於彈性欄位（Ragic field mappings、快照資料）

### 4.2 CREATE TABLE 語法

```sql
-- 啟用 UUID 擴充
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ────────────────────────────────────────────
-- 1. TENANTS（據點/租戶）
-- ────────────────────────────────────────────
CREATE TABLE tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(20)  NOT NULL UNIQUE,  -- e.g. HQ, HOTEL_A, HOTEL_B, MALL_A, MALL_B
    name        VARCHAR(100) NOT NULL,
    type        VARCHAR(20)  NOT NULL CHECK (type IN ('headquarters','hotel','mall')),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 初始資料
INSERT INTO tenants (code, name, type) VALUES
  ('HQ',      '總公司',  'headquarters'),
  ('HOTEL_A', '飯店A',   'hotel'),
  ('HOTEL_B', '飯店B',   'hotel'),
  ('MALL_A',  '商場A',   'mall'),
  ('MALL_B',  '商場B',   'mall');

-- ────────────────────────────────────────────
-- 2. ROLES（角色定義）
-- ────────────────────────────────────────────
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(50) NOT NULL UNIQUE, -- system_admin, tenant_admin, module_manager, viewer
    scope       VARCHAR(20) NOT NULL CHECK (scope IN ('global','tenant','module')),
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO roles (name, scope, description) VALUES
  ('system_admin',    'global',  '可操作所有據點、所有模組'),
  ('tenant_admin',    'tenant',  '可操作指定據點的所有模組'),
  ('module_manager',  'module',  '可跨據點存取特定模組（如財務主管）'),
  ('viewer',          'module',  '唯讀存取指定據點+模組');

-- ────────────────────────────────────────────
-- 3. USERS（使用者）
-- ────────────────────────────────────────────
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    email           VARCHAR(255) NOT NULL UNIQUE,
    full_name       VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email  ON users(email);

-- ────────────────────────────────────────────
-- 4. USER_ROLES（使用者角色對應）
-- ────────────────────────────────────────────
-- 設計：user + role + tenant 三欄組合代表一條授權
-- 例：user A 在 HOTEL_A 有 tenant_admin 角色
--     user A 在 HQ      有 viewer 角色（財務模組）
CREATE TABLE user_roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id     UUID NOT NULL REFERENCES roles(id),
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    module      VARCHAR(50),          -- 若 scope=module，指定模組名稱
    granted_by  UUID REFERENCES users(id),
    granted_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, role_id, tenant_id, module)
);

CREATE INDEX idx_user_roles_user   ON user_roles(user_id);
CREATE INDEX idx_user_roles_tenant ON user_roles(tenant_id);

-- ────────────────────────────────────────────
-- 5. RAGIC_CONNECTIONS（Ragic 連線設定）
-- ────────────────────────────────────────────
-- 每筆代表一個 Ragic Sheet 的連線
-- 一個 tenant 可以有多個 Sheet 連線
CREATE TABLE ragic_connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    display_name    VARCHAR(100) NOT NULL,              -- 人類可讀名稱，如「飯店A 訂房記錄」
    server          VARCHAR(20)  NOT NULL,              -- www | ap8 | na3 | eu2 | ap5
    account_name    VARCHAR(100) NOT NULL,              -- Ragic 帳號名稱
    api_key_enc     TEXT         NOT NULL,              -- Fernet 加密後的 API Key
    sheet_path      VARCHAR(200) NOT NULL,              -- {tab_folder}/{sheet_index}，例：hotel/3
    field_mappings  JSONB        NOT NULL DEFAULT '{}', -- {"1000001": "房型", "1000002": "金額"}
    sync_interval   INTEGER      NOT NULL DEFAULT 60,   -- 同步間隔（分鐘）
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    last_synced_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ragic_conn_tenant ON ragic_connections(tenant_id);

-- ────────────────────────────────────────────
-- 6. SYNC_LOGS（同步執行記錄）
-- ────────────────────────────────────────────
CREATE TABLE sync_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id   UUID NOT NULL REFERENCES ragic_connections(id),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    records_fetched INTEGER,
    status          VARCHAR(20) NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running','success','error','partial')),
    error_msg       TEXT,
    triggered_by    VARCHAR(20) NOT NULL DEFAULT 'scheduler'  -- scheduler | manual | api
);

CREATE INDEX idx_sync_logs_conn ON sync_logs(connection_id);
CREATE INDEX idx_sync_logs_status ON sync_logs(status, started_at DESC);

-- ────────────────────────────────────────────
-- 7. DATA_SNAPSHOTS（Ragic 資料快照）
-- ────────────────────────────────────────────
-- 儲存從 Ragic 拉回的原始 JSON，Dashboard 和報表讀此表
CREATE TABLE data_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id   UUID NOT NULL REFERENCES ragic_connections(id),
    sync_log_id     UUID REFERENCES sync_logs(id),
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data            JSONB NOT NULL,                     -- 原始 Ragic response
    record_count    INTEGER NOT NULL DEFAULT 0,
    checksum        VARCHAR(64)                         -- SHA256 of data，避免重複儲存
);

CREATE INDEX idx_snapshots_conn    ON data_snapshots(connection_id);
CREATE INDEX idx_snapshots_synced  ON data_snapshots(connection_id, synced_at DESC);
CREATE INDEX idx_snapshots_data    ON data_snapshots USING GIN (data);  -- JSONB 搜尋加速

-- ────────────────────────────────────────────
-- 8. AUDIT_LOGS（操作稽核記錄）
-- ────────────────────────────────────────────
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    tenant_id       UUID REFERENCES tenants(id),
    action          VARCHAR(50)  NOT NULL,  -- login, logout, create, update, delete, export
    resource_type   VARCHAR(50),            -- user, role, ragic_connection, report ...
    resource_id     VARCHAR(100),
    ip_address      INET,
    user_agent      TEXT,
    extra           JSONB,                  -- 額外 context
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_user   ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_tenant ON audit_logs(tenant_id, created_at DESC);
```

### 4.3 Ragic Field Mappings 格式說明

`field_mappings` 欄位的 JSONB 格式：

```json
{
  "1000001": { "label": "房型", "type": "select" },
  "1000002": { "label": "訂房金額", "type": "number" },
  "1000003": { "label": "入住日期", "type": "date" },
  "1000004": { "label": "退房日期", "type": "date" },
  "1000005": { "label": "訂房狀態", "type": "select" }
}
```

### 4.4 DATA_SNAPSHOTS 資料格式說明

`data` 欄位儲存 Ragic 原始回應，格式如下：

```json
{
  "1": {
    "1000001": "豪華客房",
    "1000002": 5800,
    "1000003": "2026/04/10",
    "_ragic_id": 1,
    "_create_time": "2026-04-08 10:00:00"
  },
  "2": {
    "1000001": "標準客房",
    "1000002": 3200,
    "1000003": "2026/04/11",
    "_ragic_id": 2,
    "_create_time": "2026-04-08 11:00:00"
  }
}
```

---

## 5. Ragic API 整合規格

### 5.1 Ragic API 基本規則

| 項目        | 規格                                                                |
| ----------- | ------------------------------------------------------------------- |
| Base URL    | `https://{server}.ragic.com/{account_name}`                       |
| Server 選項 | `www` / `ap8` / `na3` / `eu2` / `ap5`（依帳號所在伺服器） |
| 必要參數    | `?v=3&api`（GET 讀取）/ `?api`（POST 寫入）                     |
| 認證方式    | HTTP Basic，username = API Key，password = 空白                     |
| Header      | `Authorization: Basic {base64(API_KEY + ":")}`                    |
| 最大筆數    | 預設 1000 筆/次，需分頁時用 `limit` + `offset`                  |
| 回傳格式    | JSON，key 為 Ragic field ID（數字字串）                             |
| 強制版本    | 所有請求必須帶 `v=3`，避免 API 變更影響                           |

### 5.2 Endpoint 格式

```
# 讀取 Sheet 所有資料
GET https://{server}.ragic.com/{account}/{tab}/{sheet_index}?v=3&api

# 讀取單筆
GET https://{server}.ragic.com/{account}/{tab}/{sheet_index}/{record_id}?v=3&api

# 分頁讀取
GET ...?v=3&api&limit=200&offset=0

# 篩選條件
GET ...?v=3&api&where=1000001,eq,豪華客房

# 排序
GET ...?v=3&api&sortBy=1000003&order=desc

# 建立新記錄
POST https://{server}.ragic.com/{account}/{tab}/{sheet_index}?api
Content-Type: application/json
Body: { "1000001": "豪華客房", "1000002": 5800 }

# 更新記錄
POST https://{server}.ragic.com/{account}/{tab}/{sheet_index}/{record_id}?api
```

### 5.3 RagicAdapter 類別規格

```python
# app/services/ragic_adapter.py

class RagicAdapter:
    """
    封裝所有 Ragic API 呼叫。
    使用 httpx.AsyncClient 做 async HTTP。
    API Key 在此類別內解密使用，不對外暴露。
    """

    def __init__(self, connection: RagicConnection):
        self.server       = connection.server        # e.g. "ap8"
        self.account      = connection.account_name  # e.g. "mycompany"
        self.sheet_path   = connection.sheet_path    # e.g. "hotel/3"
        self.api_key      = decrypt_api_key(connection.api_key_enc)  # Fernet 解密

    @property
    def base_url(self) -> str:
        return f"https://{self.server}.ragic.com/{self.account}/{self.sheet_path}"

    @property
    def auth_header(self) -> dict:
        import base64
        token = base64.b64encode(f"{self.api_key}:".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    async def fetch_all(self, limit: int = 1000, offset: int = 0) -> dict:
        """
        分頁拉取所有資料，處理 1000 筆限制。
        回傳合併後的完整 dict。
        """
        ...

    async def fetch_one(self, record_id: int) -> dict:
        """讀取單筆記錄"""
        ...

    async def create(self, data: dict) -> dict:
        """建立新記錄，data 的 key 為 Ragic field ID"""
        ...

    async def update(self, record_id: int, data: dict) -> dict:
        """更新記錄"""
        ...
```

### 5.4 分頁拉取邏輯

```python
async def fetch_all_paginated(adapter: RagicAdapter) -> dict:
    """
    Ragic GET 預設最多 1000 筆。
    此函式自動分頁直到拉完所有資料。
    """
    all_data = {}
    offset = 0
    limit = 1000

    async with httpx.AsyncClient() as client:
        while True:
            params = {"v": "3", "api": "", "limit": limit, "offset": offset}
            resp = await client.get(
                adapter.base_url,
                headers=adapter.auth_header,
                params=params,
                timeout=30.0
            )
            resp.raise_for_status()
            batch = resp.json()

            if not batch:
                break

            all_data.update(batch)

            if len(batch) < limit:
                break  # 最後一頁

            offset += limit

    return all_data
```

### 5.5 API Key 加密/解密

```python
# app/core/crypto.py

from cryptography.fernet import Fernet
from app.core.config import settings

_fernet = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_api_key(plain_key: str) -> str:
    """存入 DB 前加密"""
    return _fernet.encrypt(plain_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    """從 DB 取出後解密，僅在 RagicAdapter 內使用"""
    return _fernet.decrypt(encrypted_key.encode()).decode()
```

---

### 5.5 樂群工務報修 Ragic 連線規格

| 項目             | 規格                                           |
| ---------------- | ---------------------------------------------- |
| Server URL       | `ap12.ragic.com`                              |
| Account          | `soutlet001`                                   |
| Sheet Path       | `luqun-public-works-repair-reporting-system/6` |
| 設定變數         | `RAGIC_LUQUN_REPAIR_SERVER_URL` / `_ACCOUNT` / `_PATH` |
| Auth             | Basic Auth（API Key 直接帶，不做 base64）       |
| 資料抓取方式     | 即時抓取（無本地快取），`limit=500` 全量拉取    |

---

## 6. 身份驗證與 RBAC 權限

### 6.1 JWT Token 設計

```
Access Token：
  - 有效期：30 分鐘
  - Payload: { user_id, tenant_id, email, roles[], exp }

Refresh Token：
  - 有效期：7 天
  - 儲存於 httpOnly cookie
  - 同一 user 最多 5 個有效 refresh token
```

### 6.2 RBAC 角色矩陣

| 角色               | 所有據點  | 指定據點      | 指定模組    | 說明                |
| ------------------ | --------- | ------------- | ----------- | ------------------- |
| `system_admin`   | ✅ 全部   | -             | -           | IT 管理員，最高權限 |
| `tenant_admin`   | -         | ✅ 本據點全部 | -           | 各據點主管          |
| `module_manager` | ✅ 跨據點 | -             | ✅ 特定模組 | 如集團財務長        |
| `viewer`         | -         | ✅ 本據點     | ✅ 特定模組 | 一般使用者          |

### 6.3 權限檢查流程

```
Request 進入 FastAPI
    ↓
JWT 驗證（middleware）
    ↓
取得 user_id → 查 USER_ROLES（含 tenant_id + module）
    ↓
Casbin enforce(user_id, tenant_code/module, action)
    ↓
通過 → 執行 handler
失敗 → 403 Forbidden
```

### 6.4 Casbin Policy 範例

```
# casbin/policy.csv

# 格式：p, subject, object, action

# system_admin 可做任何事
p, system_admin, *, *

# tenant_admin 可操作本據點所有模組
p, tenant_admin, HOTEL_A/*, *
p, tenant_admin, HOTEL_B/*, *

# module_manager 可跨據點讀取財務模組
p, module_manager, */finance, read
p, module_manager, */finance, export

# viewer 唯讀
p, viewer, HOTEL_A/hotel-ops, read
```

---

## 7. FastAPI 專案結構

```
backend/
├── app/
│   ├── main.py                  # FastAPI app 入口，middleware，router 註冊
│   ├── core/
│   │   ├── config.py            # Settings（Pydantic BaseSettings）
│   │   ├── crypto.py            # Fernet 加解密
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   └── security.py          # JWT 建立/驗證
│   ├── models/                  # SQLAlchemy ORM models
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── user_role.py
│   │   ├── ragic_connection.py
│   │   ├── sync_log.py
│   │   ├── data_snapshot.py
│   │   └── audit_log.py
│   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── tenant.py
│   │   ├── ragic.py
│   │   └── report.py
│   ├── routers/                 # FastAPI APIRouter（每個模組一個檔）
│   │   ├── auth.py              # POST /auth/login, /auth/refresh, /auth/logout
│   │   ├── users.py             # CRUD /users
│   │   ├── tenants.py           # CRUD /tenants
│   │   ├── ragic.py             # /ragic/connections, /ragic/sync/{id}
│   │   ├── reports.py           # /reports/generate, /reports/download
│   │   └── dashboard.py         # /dashboard/summary, /dashboard/cross-property
│   ├── services/                # 業務邏輯層
│   │   ├── ragic_adapter.py     # RagicAdapter 類別
│   │   ├── sync_service.py      # 同步邏輯（呼叫 RagicAdapter，寫 Snapshot）
│   │   ├── report_service.py    # pandas 報表生成
│   │   └── auth_service.py      # 登入、token 管理
│   ├── scheduler/
│   │   └── jobs.py              # APScheduler job 定義
│   └── dependencies.py          # FastAPI Depends（get_db, get_current_user, rbac_check）
├── alembic/                     # 資料庫 migration
│   ├── env.py
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_ragic_adapter.py
│   └── test_sync.py
├── casbin/
│   ├── model.conf
│   └── policy.csv
├── .env.example
├── pyproject.toml               # 依賴管理（Poetry 或 uv）
└── Dockerfile
```

---

## 8. React 前端結構

```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── router/
│   │   └── index.tsx            # React Router 設定（含 RBAC Route Guard）
│   ├── stores/                  # Zustand stores
│   │   ├── authStore.ts         # user, token, roles
│   │   └── uiStore.ts           # loading, sidebar 狀態
│   ├── api/                     # axios 實例 + API 函式
│   │   ├── client.ts            # axios instance + JWT 攔截器
│   │   ├── auth.ts
│   │   ├── ragic.ts
│   │   ├── reports.ts
│   │   └── dashboard.ts
│   ├── pages/
│   │   ├── Login/
│   │   ├── Dashboard/
│   │   │   ├── index.tsx        # 跨據點 Dashboard
│   │   │   └── components/
│   │   ├── HotelModule/         # 飯店模組頁面
│   │   ├── MallModule/          # 商場模組頁面
│   │   ├── Reports/             # 報表產生與下載
│   │   ├── Settings/
│   │   │   ├── Users.tsx
│   │   │   ├── Roles.tsx
│   │   │   └── RagicConnections.tsx
│   │   └── Audit/               # 稽核日誌
│   ├── components/              # 共用元件
│   │   ├── RbacGuard.tsx        # 路由/元件層級權限控制
│   │   ├── TenantSelector.tsx   # 切換據點
│   │   └── charts/
│   │       ├── KpiCard.tsx
│   │       └── TrendChart.tsx
│   └── types/                   # TypeScript 型別定義
│       ├── auth.ts
│       ├── tenant.ts
│       └── ragic.ts
├── public/
├── vite.config.ts
└── tsconfig.json
```

---

## 9. API 路由設計

所有 API 前綴：`/api/v1`

### 9.1 Auth

| Method | Path              | 說明                                             |
| ------ | ----------------- | ------------------------------------------------ |
| POST   | `/auth/login`   | email + password → access_token + refresh_token |
| POST   | `/auth/refresh` | refresh_token → 新 access_token                 |
| POST   | `/auth/logout`  | 作廢 refresh_token                               |
| GET    | `/auth/me`      | 當前使用者資訊 + 角色                            |

### 9.2 Tenants & Users

| Method | Path                  | 說明                           | 權限          |
| ------ | --------------------- | ------------------------------ | ------------- |
| GET    | `/tenants`          | 列出所有據點                   | system_admin  |
| GET    | `/users`            | 列出使用者（含 tenant filter） | tenant_admin+ |
| POST   | `/users`            | 建立使用者                     | tenant_admin+ |
| PUT    | `/users/{id}`       | 更新使用者                     | tenant_admin+ |
| POST   | `/users/{id}/roles` | 指派角色                       | tenant_admin+ |

### 9.3 Ragic

| Method | Path                                        | 說明                        | 權限          |
| ------ | ------------------------------------------- | --------------------------- | ------------- |
| GET    | `/ragic/connections`                      | 列出連線設定                | system_admin  |
| POST   | `/ragic/connections`                      | 新增連線（含 API Key 加密） | system_admin  |
| PUT    | `/ragic/connections/{id}`                 | 修改連線                    | system_admin  |
| POST   | `/ragic/connections/{id}/sync`            | 手動觸發同步                | system_admin  |
| GET    | `/ragic/connections/{id}/logs`            | 查看同步記錄                | system_admin  |
| GET    | `/ragic/snapshots/{connection_id}/latest` | 取最新快照                  | tenant_admin+ |

### 9.4 Dashboard

| Method | Path                                 | 說明            | 權限            |
| ------ | ------------------------------------ | --------------- | --------------- |
| GET    | `/dashboard/summary`               | 各據點 KPI 摘要 | viewer+         |
| GET    | `/dashboard/cross-property`        | 跨據點比較資料  | module_manager+ |
| GET    | `/dashboard/trend/{connection_id}` | 時間序列趨勢    | viewer+         |

### 9.5 Reports

| Method | Path                              | 說明                   | 權限    |
| ------ | --------------------------------- | ---------------------- | ------- |
| POST   | `/reports/generate`             | 產生報表（JSON/Excel） | viewer+ |
| GET    | `/reports/download/{report_id}` | 下載 Excel             | viewer+ |

### 9.6 標準回應格式

```json
// 成功
{
  "success": true,
  "data": { ... },
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 20
  }
}

// 失敗
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "您沒有存取此資源的權限",
    "detail": {}
  }
}
```

---

## 10. 同步排程設計

### 10.1 排程策略

```
每個 RAGIC_CONNECTION 可設定獨立的 sync_interval（分鐘）
預設：60 分鐘同步一次

APScheduler 在 FastAPI startup 時初始化：
- IntervalTrigger：依各 connection 的 sync_interval
- 每次執行前檢查 is_active = TRUE 的連線
- 使用 coalesce=True 避免積壓執行
```

### 10.2 同步流程

```
SyncJob 執行
    │
    ├─ 建立 SYNC_LOGS 記錄（status = 'running'）
    │
    ├─ 呼叫 RagicAdapter.fetch_all_paginated()
    │       ├─ GET Ragic API（分頁直到取完）
    │       └─ 合併所有頁面資料
    │
    ├─ 計算 SHA256 checksum
    │       └─ 若與上一份 snapshot 相同 → 跳過儲存（節省空間）
    │
    ├─ 寫入 DATA_SNAPSHOTS
    │
    ├─ 更新 RAGIC_CONNECTIONS.last_synced_at
    │
    └─ 更新 SYNC_LOGS（status = 'success' 或 'error'）
```

### 10.3 錯誤處理

```python
# 同步失敗不應中斷其他 connection 的同步
# 每個 job 獨立 try/except，失敗寫入 sync_logs.error_msg

# Ragic API 常見錯誤碼對應
RAGIC_ERROR_CODES = {
    401: "API Key 無效或已過期",
    403: "帳號無此 Sheet 存取權限",
    404: "Sheet 路徑不存在",
    303: "Ragic 帳號已過期",
}
```

---

## 11. 報表引擎設計

### 11.1 報表輸入格式

```python
# POST /reports/generate 的 request body
{
  "connection_ids": ["uuid1", "uuid2"],   # 要納入的 Ragic 連線
  "tenant_ids": ["uuid3"],                # 或指定據點（取該據點全部連線）
  "date_range": {
    "start": "2026-01-01",
    "end": "2026-03-31"
  },
  "group_by": "month",                    # month | week | day
  "fields": ["1000001", "1000002"],       # 要匯總的 Ragic field ID
  "format": "excel"                       # excel | json
}
```

### 11.2 pandas 處理流程

```python
# 從 DATA_SNAPSHOTS 讀取 JSONB → 轉 DataFrame → 欄位 mapping → 匯總

import pandas as pd
from sqlalchemy import select

async def generate_report(params: ReportParams, db: AsyncSession) -> bytes:
    # 1. 從 DB 取得快照
    snapshots = await get_latest_snapshots(params.connection_ids, db)

    # 2. 展開 JSONB 為 DataFrame
    frames = []
    for snap in snapshots:
        df = pd.DataFrame.from_dict(snap.data, orient='index')
        df['_tenant'] = snap.connection.tenant.name
        df['_snapshot_at'] = snap.synced_at
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)

    # 3. 套用 field_mappings 重新命名欄位
    combined = combined.rename(columns=field_label_map)

    # 4. 日期篩選
    combined = combined[
        (combined['入住日期'] >= params.date_range.start) &
        (combined['入住日期'] <= params.date_range.end)
    ]

    # 5. 輸出 Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        combined.to_excel(writer, index=False, sheet_name='資料')
    return output.getvalue()
```

---

## 12. 環境變數與設定

### 12.1 `.env.example`

```bash
# ─── 基本設定 ───────────────────────────────────────
APP_NAME="集團 Portal"
APP_ENV=development           # development | production
DEBUG=true
API_PREFIX=/api/v1

# ─── 資料庫 ─────────────────────────────────────────
# 開發（SQLite）
DATABASE_URL=sqlite+aiosqlite:///./portal.db

# 正式（PostgreSQL）
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/portal_db

# ─── JWT ─────────────────────────────────────────────
JWT_SECRET_KEY=your-secret-key-here-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ─── Ragic API Key 加密金鑰 ───────────────────────────
# 產生方式：from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())
ENCRYPTION_KEY=your-fernet-key-here

# ─── CORS ────────────────────────────────────────────
CORS_ORIGINS=["http://localhost:5173","https://portal.yourcompany.com"]

# ─── 排程 ────────────────────────────────────────────
SCHEDULER_ENABLED=true
SCHEDULER_DEFAULT_INTERVAL_MINUTES=60
```

### 12.2 FastAPI Settings 類別

```python
# app/core/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "集團 Portal"
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ENCRYPTION_KEY: str
    CORS_ORIGINS: list[str] = []
    SCHEDULER_ENABLED: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

---

## 13. 命名慣例

### 13.1 Python（後端）

| 類型             | 慣例                                     | 範例                                      |
| ---------------- | ---------------------------------------- | ----------------------------------------- |
| 檔案/目錄        | `snake_case`                           | `ragic_adapter.py`                      |
| 類別             | `PascalCase`                           | `RagicAdapter`, `SyncService`         |
| 函式/方法        | `snake_case`                           | `fetch_all_paginated()`                 |
| 常數             | `UPPER_SNAKE`                          | `RAGIC_ERROR_CODES`                     |
| Pydantic Schema  | `PascalCase` + `Schema`/`Response` | `UserCreateSchema`, `LoginResponse`   |
| SQLAlchemy Model | `PascalCase`                           | `RagicConnection`, `DataSnapshot`     |
| DB 資料表名      | `snake_case` 複數                      | `ragic_connections`, `data_snapshots` |
| DB 欄位名        | `snake_case`                           | `tenant_id`, `last_synced_at`         |

### 13.2 TypeScript（前端）

| 類型           | 慣例                     | 範例                         |
| -------------- | ------------------------ | ---------------------------- |
| 元件           | `PascalCase`           | `TenantSelector.tsx`       |
| Hook           | `camelCase` 加 `use` | `useAuthStore`             |
| Type/Interface | `PascalCase`           | `TenantType`, `UserRole` |
| API 函式       | `camelCase`            | `fetchDashboardSummary()`  |
| Zustand Store  | `camelCase`            | `authStore`, `uiStore`   |
| 常數           | `UPPER_SNAKE`          | `API_PREFIX`               |

### 13.3 API 路由

- 使用 `kebab-case`：`/ragic/connections`, `/cross-property`
- 複數資源名：`/users`, `/tenants`, `/roles`
- 動作用 POST + 名詞：`/connections/{id}/sync`（不用 `/sync-connection/{id}`）

---

## 14. 開發流程

### 14.1 環境設定

```bash
# 後端
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 資料庫 migration
alembic upgrade head

# 啟動開發伺服器
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev    # http://localhost:5173

# API 文件
http://localhost:8000/docs        # Swagger UI
http://localhost:8000/redoc       # ReDoc
```

### 14.2 開發順序（Phase 1）

```
Week 1-2：資料庫 + Auth 基礎
  ✅ DB Schema 建立（alembic）
  ✅ 使用者登入 / JWT / refresh token
  ✅ RBAC 基礎（Casbin 設定）

Week 3-4：Ragic 整合核心
  ✅ RagicConnection CRUD API
  ✅ RagicAdapter 類別（fetch + 分頁）
  ✅ 手動同步 API
  ✅ Sync Scheduler（APScheduler）
  ✅ DataSnapshot 儲存

Week 5-6：前端 Portal 基礎
  ✅ React 專案架構 + Zustand
  ✅ 登入頁 + JWT 攔截器
  ✅ Portal 主框架（Ant Design Pro 側欄）
  ✅ RBAC Route Guard
  ✅ RagicConnection 管理頁

Week 7-8：Dashboard + 報表
  ✅ Dashboard 頁（讀 snapshot）
  ✅ KPI Cards + Recharts 圖表
  ✅ 報表產生 + Excel 下載
  ✅ 跨據點比較視圖
```

### 14.3 測試規範

```python
# 每個 service 要有單元測試
# 每個 router 要有整合測試（使用 TestClient）
# Ragic API 呼叫用 httpx mock

# 測試命名：test_{函式名}_{情境}
def test_fetch_all_paginated_handles_empty_response(): ...
def test_encrypt_decrypt_api_key_roundtrip(): ...
def test_login_with_invalid_password_returns_401(): ...
```

---

## 15. 部署規格

### 15.1 Docker Compose（開發/測試）

```yaml
version: '3.9'
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: portal_db
      POSTGRES_USER: portal_user
      POSTGRES_PASSWORD: portal_pass
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app
    environment:
      DATABASE_URL: postgresql+asyncpg://portal_user:portal_pass@db:5432/portal_db
    ports:
      - "8000:8000"
    depends_on:
      - db

  frontend:
    build: ./frontend
    command: npm run dev -- --host
    volumes:
      - ./frontend:/app
    ports:
      - "5173:5173"

volumes:
  pgdata:
```

### 15.2 正式環境建議

| 元件     | 建議                               | 說明                       |
| -------- | ---------------------------------- | -------------------------- |
| 反向代理 | Nginx                              | SSL 終止、靜態檔案 serving |
| 後端     | uvicorn + gunicorn                 | 多 worker process          |
| 前端     | `npm run build` → Nginx         | 靜態部署                   |
| DB       | PostgreSQL（非 Docker 或 managed） | 資料持久性                 |
| 備份     | pg_dump 每日                       | 至少保留 7 天              |
| HTTPS    | Let's Encrypt / 自有憑證           | 必須，Ragic API 要求 HTTPS |

---

*本規格書版本 1.0.0，由 Samuel 建立，2026-04-08*
