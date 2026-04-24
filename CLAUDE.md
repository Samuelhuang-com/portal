# Portal 專案 — Claude 行為規則

## ⚡ 必讀規則（每次對話都適用）

### 1. 每次程式碼變更，必須執行以下更新

| 動作 | 必須更新 |
|------|---------|
| 任何程式碼修改 | `README.md` → 更新「最後更新」日期與「最近變更」區塊 |
| 新增套件 / 服務 / 架構模式 | `docs/TECH_SPEC.md` → 在對應表格加入新技術說明 |
| 功能新增 / 修復 / 移除 | `docs/CHANGELOG.md` → 在最新版本下加一行 |
| 重大設計決策 | `docs/TECH_SPEC.md` → 「重要設計決策」表格 |

> 若使用者說「先不用更新文件」，才可跳過。預設必須更新。

---

### 2. 受保護元素 — 未經使用者明確指示，絕對禁止修改

詳細規格見 `docs/PROTECTED.md`，重點摘要：

**🎨 顏色（不可修改）**
- 品牌主色：`#1B3A5C`、輔色：`#4BA8E8`
- Sidebar：`#111827`、頁面背景：`#f0f4f8`
- 未完成附表底色：`#fff5f5`、框線：`#ffccc7`
- 圖表按鈕：`linear-gradient(135deg, #667eea, #764ba2)`
- 未完成附表標題：`linear-gradient(135deg, #c0392b, #e74c3c, #e67e22)`

**📐 版型（不可修改）**
- Sidebar 寬度展開：220px、收合：80px
- Header 高度：56px、內距：24px
- KPI 卡片：4 欄 Row、`size="small"`
- 工作狀態色彩映射（已完成=綠、進行中=藍、非本月=灰、待排程=黃）

**🔌 API 規格（不可修改）**
- 所有 API 前綴：`/api/v1/`
- Ragic Basic auth：API key 直接用，不做 base64

---

### 3. 禁止行為

- ❌ 不可移除現有路由、端點、資料表欄位
- ❌ 不可將同步模式 SQLAlchemy 改回 async
- ❌ 不可在沒說明的情況下更換 UI 元件庫（目前固定 Ant Design 5）
- ❌ 不可自行修改 `.env` 裡的 RAGIC_API_KEY 等敏感值
- ❌ 不可在現有表格加入 nullable=False 且無 default 的新欄位

---

### 4. 優先使用的模式（保持一致性）

**後端**
```python
# DB Session — 永遠用 Depends(get_db)，不直接用 SessionLocal()（除 sync service 外）
def endpoint(db: Session = Depends(get_db)): ...

# JWT — subject 必須是純 UUID 字串
create_access_token(subject=user.id, extra_claims={"email": ..., "roles": ...})

# Ragic Auth — 不做 base64
headers = {"Authorization": f"Basic {settings.RAGIC_API_KEY}"}
```

**前端**
```typescript
// API 呼叫統一用 @/api/ 下的封裝函數，不在元件內直接用 axios
// 狀態管理：Zustand（只用於 auth），其他用 useState/useCallback
// 路由：React Router v6 Outlet 模式
```

---

## 📁 專案結構速查

```
portal/
├── backend/
│   ├── app/
│   │   ├── core/           # config, database, security
│   │   ├── models/         # SQLAlchemy ORM
│   │   ├── routers/        # FastAPI endpoints
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # 業務邏輯（ragic_adapter, sync, service）
│   │   ├── dependencies.py # get_current_user, require_roles
│   │   └── main.py         # FastAPI app + APScheduler
│   └── .env
├── frontend/
│   └── src/
│       ├── api/            # axios 封裝函數
│       ├── components/Layout/  # MainLayout（sidebar + header）
│       ├── pages/          # Login, Dashboard, RoomMaintenance, Settings/
│       ├── router/         # React Router 路由定義
│       ├── stores/         # Zustand stores（authStore）
│       └── types/          # TypeScript 型別定義
├── docs/
│   ├── PROTECTED.md        # 受保護設計規格
│   ├── TECH_SPEC.md        # 技術規格
│   └── CHANGELOG.md        # 版本紀錄
├── CLAUDE.md               # 本文件
└── README.md
```

---

## 💡 Token 節省策略

1. **讀取文件時**：先讀摘要/目錄，再按需深入
2. **修改程式碼時**：用 `Edit`（差異補丁），不用 `Write`（整檔覆寫）
3. **除錯時**：先看 log 的最後 20 行，不要一次讀整個 log
4. **長對話時**：適時開新對話，把關鍵資訊整理成一段摘要貼入

---

## 🏃 快速啟動

```bash
# 後端
cd backend && uvicorn app.main:app --reload --port 8000

# 前端
cd frontend && npm run dev
# → http://localhost:5173
```

預設帳號：`admin` / `admin1234`（或依 `.env` 設定）
