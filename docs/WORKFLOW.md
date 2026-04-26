# Portal 日常作業流程

> 開發機：`C:\OneDrive\_Ragic\portal`  
> 正式機：`192.168.0.210`，路徑 `D:\portal`  
> 最後更新：2026-04-26（補充 git reset --hard 說明）

---

## 開發區作業

### 啟動開發環境

開兩個 cmd 視窗分別執行：

**後端**
```cmd
cd C:\OneDrive\_Ragic\portal\backend
py -3.11 -m uvicorn app.main:app --reload --port 8000
```

**前端**
```cmd
cd C:\OneDrive\_Ragic\portal\frontend
npm run dev
```

瀏覽器開啟：`http://localhost:5173`

---

### 完成開發，推上 GitHub

```powershell
cd C:\OneDrive\_Ragic\portal

# 確認哪些檔案有變動
git status

# 加入所有變動
git add .

# 建立 commit（說明這次改了什麼）
git commit -m "fix: 說明內容"

# 推上 GitHub
git push
```

> `.env`、`portal.db` 在 `.gitignore` 裡，不會被推上去。

---

## 正式區作業

### 啟動 Web 服務

開一個**管理員 cmd**，執行：

```cmd
cd D:\portal\backend
py -3.11 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

瀏覽器開啟：`http://192.168.0.210:8000`

> cmd 視窗不能關，關掉服務就停了。  
> 若要背景執行，改用 NSSM（見 `docs/DEPLOY_PRODUCTION.md`）。

---

### 從 GitHub 更新正式區

**方法 A：執行 update.bat（推薦）**

1. 先停止目前跑著的 uvicorn（`Ctrl+C`）
2. 對 `D:\portal\update.bat` 按右鍵 → **以系統管理員身分執行**
3. 等待完成後，重新啟動後端：
   ```cmd
   cd D:\portal\backend
   py -3.11 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

**方法 B：手動指令（管理員 cmd）**

```cmd
cd D:\portal
git fetch origin main
git reset --hard origin/main

cd D:\portal\backend
py -3.11 -m pip install -r requirements.txt -q

cd D:\portal\frontend
npm install --silent
npm run build
```

> ⚠️ **關於 `git reset --hard` 的重要說明**
>
> `update.bat` 使用的是 `git reset --hard origin/main`，而不是一般的 `git pull`。
> 兩者的差異：
> - `git pull`：合併遠端變更，若本地有修改可能產生衝突
> - `git reset --hard`：強制讓正式機與 GitHub 完全一致，**本地任何手動修改都會被覆蓋**
>
> 因此，**正式機不應該直接修改程式碼**。所有變更都必須在開發機完成、推上 GitHub，再透過 `update.bat` 同步到正式機。
>
> 正式機上不被 git 管理的檔案（`.env`、`portal.db` 等在 `.gitignore` 的項目）則完全不受影響。

---

## 完整日常流程圖

```
開發機                          GitHub                    正式機
  │                               │                          │
  │  寫程式、測試                  │                          │
  │  git add .                    │                          │
  │  git commit -m "..."          │                          │
  │  git push ─────────────────► │                          │
  │                               │                          │
  │                               │  ◄── update.bat 執行    │
  │                               │      git fetch           │
  │                               │      git reset --hard ──►│
  │                               │      npm run build       │
  │                               │      重啟 uvicorn         │
```

---

## 快速指令對照

| 動作 | 開發機 | 正式機 |
|------|--------|--------|
| 啟動後端 | `uvicorn app.main:app --reload --port 8000` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| 啟動前端 | `npm run dev` | 不需要（由後端 serve） |
| 網址 | `http://localhost:5173` | `http://192.168.0.210:8000` |
| 推送更新 | `git add . && git commit && git push` | — |
| 取得更新 | — | 執行 `update.bat` |
| 帳號 | `admin` / `Admin@2026` | `admin` / `Admin@2026` |
