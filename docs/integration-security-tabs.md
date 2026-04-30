# 保全巡檢模組整合規劃

> 建立日期：2026-04-30
> 狀態：✅ 已實作

## 目標

將既有 `security/dashboard` 與 7 個獨立的 `security/patrol/:sheetKey` 路由整合為單一入口「保全巡檢」，以 TAB 方式在同一頁面切換。

---

## 整合前 vs 整合後

### 整合前

```
選單：保全管理
  ├── 保全巡檢Dashboard  → /security/dashboard
  ├── B1F~B4F            → /security/patrol/b1f-b4f
  ├── 1F~3F              → /security/patrol/1f-3f
  ├── 5F~10F             → /security/patrol/5f-10f
  ├── 4F                 → /security/patrol/4f
  ├── 1F飯店大廳          → /security/patrol/1f-hotel
  ├── 1F閉店巡檢          → /security/patrol/1f-close
  └── 1F開店準備          → /security/patrol/1f-open
```

### 整合後

```
選單：保全巡檢  → /security/dashboard（唯一入口）

頁面 /security/dashboard 的外層 TAB：
  ├── Tab 0: 保全巡檢Dashboard（統計 / 異常清單 / 趨勢分析）
  ├── Tab 1: B1F~B4F夜間巡檢
  ├── Tab 2: 1F~3F夜間巡檢
  ├── Tab 3: 5F~10F夜間巡檢
  ├── Tab 4: 4F夜間巡檢
  ├── Tab 5: 1F飯店大廳
  ├── Tab 6: 1F閉店巡檢
  └── Tab 7: 1F開店準備

舊路由（保留，仍可直接存取）：
  /security/patrol/:sheetKey
  /security/patrol/:sheetKey/:batchId
```

---

## 修改檔案清單

| 檔案 | 類型 | 說明 |
|------|------|------|
| `frontend/src/pages/SecurityPatrol/index.tsx` | 改 | 拆出 `SecurityPatrolContent` 接受 sheetKey prop；原 default export 改為包裝層 |
| `frontend/src/pages/SecurityDashboard/index.tsx` | 改 | 加外層 TAB；切換 Dashboard/巡檢 Sheet；嵌入 SecurityPatrolContent |
| `frontend/src/components/Layout/MainLayout.tsx` | 改 | security 群組從 8 items → 單一直連 `/security/dashboard` |
| `frontend/src/constants/navLabels.ts` | 改 | `NAV_GROUP.security` 從「保全管理」→「保全巡檢」 |
| `settings/ragic-app-directory`（DB） | 補 | 新增 7 筆保全巡檢 Sheet 記錄 |
| `docs/CHANGELOG.md` | 改 | 新增本次變更記錄 |
| `README.md` | 改 | 更新最後更新日期與最近變更 |

**不需修改**：所有後端檔案、`router/index.tsx`、API 封裝、Service、Schema、Permission 定義。

---

## TAB 設定對照表

| TAB key | 顯示標籤 | sheetKey | Ragic Sheet ID | Ragic Path |
|---------|---------|---------|---------------|-----------|
| `dashboard` | 保全巡檢Dashboard | — | — | — |
| `b1f-b4f` | B1F~B4F夜間巡檢 | b1f-b4f | 1 | security-patrol/1 |
| `1f-3f` | 1F~3F夜間巡檢 | 1f-3f | 2 | security-patrol/2 |
| `5f-10f` | 5F~10F夜間巡檢 | 5f-10f | 3 | security-patrol/3 |
| `4f` | 4F夜間巡檢 | 4f | 4 | security-patrol/4 |
| `1f-hotel` | 1F飯店大廳 | 1f-hotel | 5 | security-patrol/5 |
| `1f-close` | 1F閉店巡檢 | 1f-close | 6 | security-patrol/6 |
| `1f-open` | 1F開店準備 | 1f-open | 9 | security-patrol/9 |

---

## 權限設計

現有三個 permission key 保持不動：

| Permission Key | 用途 | 控制範圍 |
|---------------|------|---------|
| `security_view` | 保全模組顯示門檻 | 選單可見性 |
| `security_dashboard_view` | Dashboard TAB | Tab 0 內容 |
| `security_patrol_view` | 各巡檢 Sheet TAB | Tab 1-7 內容 |

---

## 架構決策說明

### SecurityPatrolContent 元件拆分

原本 `SecurityPatrolPage` 使用 `useParams()` 取得 `sheetKey`，無法直接嵌入 Dashboard TAB。
解法：拆出 `SecurityPatrolContent({ sheetKey })` 接受 prop，原 default export 保留為包裝層（向下相容舊路由）。

### TAB 切換時強制 remount

各巡檢 TAB 使用 `key={activeOuterTab}` 強制 React remount，確保切換 Sheet 時：
- 舊 Sheet 的資料完全清空
- 新 Sheet 從頭載入，不殘留舊狀態

### URL 策略

統一維持 `/security/dashboard`，不使用 query param 或 nested path 標記 TAB。
理由：簡單直接，符合本 Portal 其他整合模組（商場管理、整棟巡檢）的慣例。

---

## Ragic App Directory 補充記錄

| 模組 | TAB | Sheet ID | Path | 狀態 |
|------|-----|---------|------|------|
| 保全巡檢 | B1F~B4F夜間巡檢 | 1 | security-patrol/1 | active |
| 保全巡檢 | 1F~3F夜間巡檢 | 2 | security-patrol/2 | active |
| 保全巡檢 | 5F~10F夜間巡檢 | 3 | security-patrol/3 | active |
| 保全巡檢 | 4F夜間巡檢 | 4 | security-patrol/4 | active |
| 保全巡檢 | 1F飯店大廳夜間巡檢 | 5 | security-patrol/5 | active |
| 保全巡檢 | 1F閉店巡檢 | 6 | security-patrol/6 | active |
| 保全巡檢 | 1F開店準備 | 9 | security-patrol/9 | active |

---

## 注意事項

1. 切換 TAB 時資料重置屬預期行為（remount 設計）
2. 「查看明細」按鈕仍會 navigate 至 `/security/patrol/:sheetKey/:batchId`（獨立明細頁），屬正確行為
3. `settings/menu-config` DB 中若有舊版 7 筆 security patrol 的 custom label，整合後會成為孤兒記錄（不影響功能）
