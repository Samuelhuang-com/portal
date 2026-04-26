# Portal 正式環境部署指南

> 目標機器：`192.168.0.210`，路徑 `D:\portal`，全新 Windows 電腦  
> 部署模式：**後端（FastAPI）+ 前端靜態檔案，統一由 port 8000 服務**  
> 最後更新：2026-04-25

---

## 總覽

```
開發機 (C:\OneDrive\_Ragic\portal)
        │
        │  robocopy 或壓縮複製
        ▼
正式機 (D:\portal)
  ├── backend/         ← uvicorn port 8000（含 API + 靜態前端）
  └── frontend/dist/   ← npm run build 產生的靜態檔案
```

整個系統對外只需開放 **port 8000**，瀏覽器連 `http://192.168.0.210:8000` 即可使用。

---

## 第一步：正式機環境安裝

在 192.168.0.210 上以系統管理員執行以下動作。

### 1-1 安裝 Python 3.11+

1. 前往 https://www.python.org/downloads/ 下載 **Python 3.11.x** Windows installer（64-bit）
2. 安裝時勾選 **"Add Python to PATH"**（重要）
3. 安裝完後驗證：
   ```cmd
   python --version
   pip --version
   ```

### 1-2 安裝 Node.js 20 LTS

1. 前往 https://nodejs.org/ 下載 **Node.js 20 LTS** Windows installer
2. 安裝完後驗證：
   ```cmd
   node --version
   npm --version
   ```

### 1-3 安裝 NSSM（讓後端跑成 Windows 服務）

1. 前往 https://nssm.cc/download 下載 nssm
2. 解壓後將 `nssm.exe`（64-bit 版）複製到 `C:\Windows\System32\`
3. 驗證：
   ```cmd
   nssm version
   ```

---

## 第二步：複製程式碼到正式機

### 方法 A：在開發機打包，再複製（推薦）

在開發機（你的電腦）的 PowerShell 執行：

```powershell
# 壓縮（排除不需要的目錄與本地資料庫）
Compress-Archive -Path "C:\OneDrive\_Ragic\portal\*" `
  -DestinationPath "C:\portal_deploy.zip" `
  -CompressionLevel Optimal

# 注意：壓縮前確認不含以下項目（手動從 zip 移除或用下方 robocopy）
# - frontend\node_modules\
# - backend\__pycache__\
# - backend\app\**\__pycache__\
# - backend\.env          ← 正式機要用新的 .env
# - backend\portal.db     ← 視情況決定是否帶資料
# - backend\budget_system_v1.sqlite  ← 同上
```

複製 `portal_deploy.zip` 到正式機 `D:\`，解壓到 `D:\portal\`。

### 方法 B：使用 robocopy（在開發機執行，需網路共用或 USB）

```cmd
robocopy "C:\OneDrive\_Ragic\portal" "D:\portal" /E /XD node_modules __pycache__ .git /XF portal.db budget_system_v1.sqlite .env
```

---

## 第三步：正式機建立 `.env` 設定檔

在正式機建立 `D:\portal\backend\.env`，內容如下（**完整複製後修改標記的幾行**）：

```dotenv
# ─── App ────────────────────────────────────────────────────────────────────
APP_NAME="集團 Portal"
APP_ENV=production          # ← 改為 production
ENV=production              # ← 改為 production
DEBUG=false                 # ← 改為 false
API_PREFIX=/api/v1

# ─── Database ───────────────────────────────────────────────────────────────
DATABASE_URL=sqlite:///./portal.db

# ─── JWT ────────────────────────────────────────────────────────────────────
# ★ 必須重新產生！在正式機執行：
#   python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=請貼上新產生的金鑰
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ─── Ragic API Key 加密金鑰 ─────────────────────────────────────────────────
# ★ 必須重新產生！在正式機執行：
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=請貼上新產生的金鑰

# ─── CORS ───────────────────────────────────────────────────────────────────
# ★ 改為正式機 IP（前端從同一 origin 來，這行主要給外部工具用）
CORS_ORIGINS=["http://192.168.0.210:8000","http://localhost:8000"]

# ─── Scheduler ──────────────────────────────────────────────────────────────
SCHEDULER_ENABLED=true
SCHEDULER_DEFAULT_INTERVAL_MINUTES=60

# ─── OpenAI ─────────────────────────────────────────────────────────────────
OPENAI_API_KEY=

# ─── Ragic（以下保持與開發機相同）───────────────────────────────────────────
RAGIC_API_KEY=dy9XMFExT0pqZElkVlZhYWxGN1VWQlhKeXZRS0lPNHhyNmpsWjIra1pTdDNPSkFJSlhLNWtmWk92eTdEbkZzaA
RAGIC_SERVER_URL=ap16.ragic.com
RAGIC_SERVER=ap16
RAGIC_ACCOUNT_NAME=intraragicapp
RAGIC_ACCOUNT=intraragicapp
RAGIC_VERIFY_SSL=true
RAGIC_API_VERSION=2025-01-01
RAGIC_NAMING=
RAGIC_TAB=ragicsales-order-management
RAGIC_SHEET_INDEX=1
RAGIC_FIELD_LABELS_FILE=app/config_data/field_labels.json
RAGIC_FORM_CONFIG_FILE=app/config_data/sales_order_config.json
RAGIC_ROOM_MAINTENANCE_PATH=ragicsales-order-management/1
RAGIC_FIELD_ROOM_NO=1000006
RAGIC_FIELD_INSPECT_ITEMS=1000007
RAGIC_FIELD_WORK_ITEM=1000008
RAGIC_FIELD_INSPECT_DT=1000009
RAGIC_FIELD_DEPT=1000019
RAGIC_FIELD_CLOSE_DATE=1000018
RAGIC_FIELD_SUBTOTAL=1000011
RAGIC_FIELD_INCOMPLETE=1000012
RAGIC_ROOM_DETAIL_SERVER_URL=ap12.ragic.com
RAGIC_ROOM_DETAIL_ACCOUNT=soutlet001
RAGIC_ROOM_DETAIL_PATH=report2/2
RAGIC_PM_SERVER_URL=ap12.ragic.com
RAGIC_PM_JOURNAL_PATH=periodic-maintenance/6
RAGIC_PM_ITEMS_PATH=periodic-maintenance/8
RAGIC_MALL_PM_SERVER_URL=ap12.ragic.com
RAGIC_MALL_PM_ACCOUNT=soutlet001
RAGIC_MALL_PM_JOURNAL_PATH=periodic-maintenance/18
RAGIC_MALL_PM_ITEMS_PATH=periodic-maintenance/18
RAGIC_LUQUN_REPAIR_SERVER_URL=ap12.ragic.com
RAGIC_LUQUN_REPAIR_ACCOUNT=soutlet001
RAGIC_LUQUN_REPAIR_PATH=luqun-public-works-repair-reporting-system/6
RAGIC_DAZHI_REPAIR_SERVER_URL=ap12.ragic.com
RAGIC_DAZHI_REPAIR_ACCOUNT=soutlet001
RAGIC_DAZHI_REPAIR_PATH=lequn-public-works/8
RAGIC_DAZHI_REPAIR_PAGEID=fV8
```

**產生新金鑰的指令（在正式機的 cmd 執行）：**

```cmd
python -c "import secrets; print(secrets.token_hex(32))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 第四步：修改 `main.py` 加入靜態前端服務

> 這個修改讓 FastAPI 直接 serve 前端的 `dist/` 靜態檔案，**只需要一個 port 8000 對外**。

在正式機編輯 `D:\portal\backend\app\main.py`，找到最後一行 `app.include_router(budget.router ...)` 之後，在**檔案最底部**加入以下內容：

```python
# ── 正式環境：serve 前端靜態檔案（放在所有路由之後）────────────────────────
import os as _os
from fastapi.staticfiles import StaticFiles as _StaticFiles

_frontend_dist = _os.path.join(_os.path.dirname(__file__), "..", "..", "frontend", "dist")
if _os.path.isdir(_frontend_dist):
    app.mount("/", _StaticFiles(directory=_frontend_dist, html=True), name="frontend")
    print(f"[Portal] Frontend static files served from: {_frontend_dist}")
```

這樣寫的好處是：dist 資料夾不存在（開發機）時自動跳過，不影響開發環境。

---

## 第五步：後端安裝與初始化

在正式機，以系統管理員開 **命令提示字元（cmd）** 執行：

```cmd
cd D:\portal\backend

:: 安裝 Python 套件
pip install -r requirements.txt

:: 初始化資料庫（建立所有表格 + 種子帳號）
python init_db.py
```

驗證資料庫已建立：

```cmd
dir D:\portal\backend\portal.db
```

---

## 第六步：前端建置

```cmd
cd D:\portal\frontend

:: 安裝 npm 套件
npm install

:: 建置正式版靜態檔案 → 輸出到 frontend/dist/
npm run build
```

建置完成後確認：

```cmd
dir D:\portal\frontend\dist
```

應看到 `index.html` 和 `assets\` 資料夾。

---

## 第七步：以 Windows 服務啟動後端

### 7-1 確認 uvicorn 路徑

```cmd
where uvicorn
:: 通常是 C:\Users\<使用者>\AppData\Local\Programs\Python\Python311\Scripts\uvicorn.exe
:: 或 C:\Python311\Scripts\uvicorn.exe
```

### 7-2 用 NSSM 安裝服務

以系統管理員開 cmd：

```cmd
nssm install PortalBackend
```

會開啟 GUI，填入：

| 欄位 | 填入值 |
|------|--------|
| Path | `C:\Python311\Scripts\uvicorn.exe`（填你的實際路徑） |
| Startup directory | `D:\portal\backend` |
| Arguments | `app.main:app --host 0.0.0.0 --port 8000 --workers 2` |

切到 **Environment** 頁籤，加入（如果 PATH 沒有自動包含 Python）：

```
PATH=C:\Python311;C:\Python311\Scripts;%PATH%
```

切到 **I/O** 頁籤，設定 log 輸出（方便除錯）：

| 欄位 | 填入值 |
|------|--------|
| stdout | `D:\portal\logs\portal_stdout.log` |
| stderr | `D:\portal\logs\portal_stderr.log` |

先建立 log 資料夾：

```cmd
mkdir D:\portal\logs
```

### 7-3 啟動服務

```cmd
nssm start PortalBackend
```

確認狀態：

```cmd
nssm status PortalBackend
:: 應顯示 SERVICE_RUNNING
```

---

## 第八步：Windows 防火牆開放 port 8000

以系統管理員執行：

```cmd
netsh advfirewall firewall add rule name="Portal Port 8000" dir=in action=allow protocol=TCP localport=8000
```

---

## 第九步：驗證

在同網段的電腦瀏覽器開啟：

```
http://192.168.0.210:8000
```

應看到登入頁面。使用初始帳號登入：

| 帳號 | 密碼 |
|------|------|
| `admin` | `Admin@2026` |
| `samuel.huang` | `Samuel@2026` |

API 文件：`http://192.168.0.210:8000/api/docs`

---

## 第十步：（選用）搬移現有資料庫

如果需要把開發機的資料帶到正式機：

```cmd
:: 在開發機複製 DB 到正式機（替換步驟五產生的空 DB）
copy "C:\OneDrive\_Ragic\portal\backend\portal.db" "D:\portal\backend\portal.db"
copy "C:\OneDrive\_Ragic\portal\backend\budget_system_v1.sqlite" "D:\portal\backend\budget_system_v1.sqlite"
```

> ⚠️ 複製 DB 前要確保開發機後端已停止，避免 SQLite 鎖定造成資料不完整。

---

## 日常維護指令

```cmd
:: 重啟後端服務
nssm restart PortalBackend

:: 停止服務
nssm stop PortalBackend

:: 查看即時 log（tail 效果）
powershell Get-Content D:\portal\logs\portal_stderr.log -Wait -Tail 50

:: 更新程式碼後重新建置前端
cd D:\portal\frontend
npm run build
nssm restart PortalBackend

:: 移除服務（需要時）
nssm remove PortalBackend confirm
```

---

## 常見問題

**Q：服務啟動失敗，看 stderr.log 顯示 ModuleNotFoundError**  
A：Python 套件安裝路徑問題。確認 NSSM 的 Path 指向的 uvicorn.exe 與安裝 `pip install` 的 Python 是同一個版本。

**Q：前端出現空白頁或 404**  
A：確認 `D:\portal\frontend\dist\index.html` 存在，且 `main.py` 的 StaticFiles 修改已套用。

**Q：API 呼叫出現 CORS 錯誤**  
A：前端若從同一 port 8000 來，理論上沒有 CORS 問題。若從其他 port 連，在 `.env` 的 `CORS_ORIGINS` 加入對應網址。

**Q：資料庫同步失敗**  
A：確認正式機可以連外網到 `ap12.ragic.com` 和 `ap16.ragic.com`（port 443）。可測試：
```cmd
curl https://ap16.ragic.com
```

**Q：如何升級程式碼**  
A：從開發機複製最新的 `backend/` 和 `frontend/src/` 到正式機，重新 `npm run build`，然後 `nssm restart PortalBackend`。不需要重跑 `init_db.py`（既有資料表不受影響）。
