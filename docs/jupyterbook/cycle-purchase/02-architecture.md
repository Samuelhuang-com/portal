# 架構

## 雙資料庫佈局

```{mermaid}
flowchart TB
    subgraph P["portal.db（主庫）"]
        U[users / roles / role_permissions]
        V[vendors（合約模組，廠商唯一主檔）]
        D[部門參考資料]
    end
    subgraph C["cycle-purchase.db（獨立庫）"]
        CV[cycle_purchase_vendors]
        CD[cycle_purchase_departments]
        REST[items / cycles / requests / summary<br/>pos / receiving / payments / audit_logs]
    end
    V -->|cycle_purchase_vendor_sync<br/>單向鏡像| CV
    D -->|cycle_purchase_department_sync<br/>單向鏡像| CD
    U -.->|軟關聯：只存 user_id 字串<br/>+ 姓名快照| REST
```

### 為什麼要拆兩個檔案

`backend/app/core/cycle_purchase_database.py` 定義了獨立的
`cycle_purchase_engine` / `CyclePurchaseBase` / `CyclePurchaseSessionLocal`。

- 兩份 metadata 互不影響，`create_all()` 不會誤建對方的表。
- 週採寫入頻繁（多階段交易），與 `portal.db` 分開可降低 SQLite 鎖競爭。

### 拆檔的代價：跨庫只能軟關聯

| 情境 | 做法 |
|------|------|
| 記操作人員 | 只存 `*_user_id`（`String(36)`）+ `*_name` 姓名快照，**不建 FK** |
| 記部門／供應商來源 | 鏡像表加 `source_department_id` / `source_vendor_id`（unique、**nullable**）當跨庫對照鍵 |
| 想 JOIN portal.db | **不做**。專案明訂不用 `ATTACH DATABASE`；需要顯示名稱時由 router 端 `_attach_owner_names()` 這類函式二次查詢後貼回 |

```{admonition} 姓名快照不是冗餘
:class: note

`submitted_by_name`、`buyer_name`、`operator_name` 這類欄位是**刻意的快照**。
使用者離職改名後，歷史單據仍要顯示當時的姓名，且跨庫無法即時 JOIN。
```

## 分層

```{mermaid}
flowchart LR
    FE["frontend/src/pages/CyclePurchase/*"] --> API["frontend/src/api/cyclePurchase.ts"]
    API --> R["routers/cycle_purchase_*.py<br/>（權限守衛 + HTTP 轉譯）"]
    R --> S["services/cycle_purchase_*_service.py<br/>（業務規則）"]
    S --> M["models/cycle_purchase_*.py<br/>（SQLAlchemy ORM）"]
    M --> DB[(cycle-purchase.db)]
```

- **router 只做兩件事**：掛 `Depends(require_permission(...))`、把 service 丟出的 `ValueError` 轉成 HTTP 4xx。
  多數 router 有一個共用的 `_handle(fn, *args, **kwargs)` 包裝器。
- **業務規則全在 service**：狀態機、退回擋點、金額重算、單號產生。
- 資料庫 Session 一律 `Depends(get_cycle_purchase_db)`；需要同時查主庫時另外注入 `portal_db`。

## 啟動時的自動 migration

`backend/app/main.py` 在啟動時依序執行（皆為冪等）：

| 順序 | 函式 | 做什麼 |
|------|------|--------|
| 1 | `CyclePurchaseBase.metadata.create_all()` | 建**缺少的**資料表（不會改既有表的欄位） |
| 2 | `_migrate_cycle_purchase_vendor_source()` | 補 `cycle_purchase_vendors.source_vendor_id` / `synced_at` + unique index |
| 3 | `_migrate_cycle_purchase_department_source()` | 補 `cycle_purchase_departments.source_department_id` + unique index |
| 4 | `_migrate_cycle_purchase_item_mapping_unique()` | 重建 `cycle_purchase_item_mappings` 的唯一鍵 |

```{admonition} create_all() 只建表、不加欄位
:class: warning

這就是第 2～4 步存在的原因。既有資料表新增欄位時，`create_all()` **完全不會動它**，
啟動後會直接噴 `no such column: cycle_purchase_vendors.source_vendor_id`。
新增欄位到既有週採表時，務必比照上面的寫法補一支啟動時 migration。
```

## 排程

| Job ID | 觸發 | 內容 |
|--------|------|------|
| `cycle_purchase_auto_close` | 每天 `00:05`（CronTrigger，`misfire_grace_time=3600`） | 期別已過的請購單自動關閉（`auto_close_expired_requests()`） |

挑 00:05 而不是 00:00，是為了避開整點大量排程同時觸發；用每天而非每小時，
是因為這件事只在跨月那一刻會有變化，每小時跑只會白白增加 `cycle-purchase.db` 的寫入鎖競爭。
