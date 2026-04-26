# Portal 開發日誌 (DEV_LOG)

> 用途：記錄每次開發的修改摘要、對應會議決議、待辦與問題。
> Claude AI 讀取入口：開新對話時說「請讀 docs/DEV_LOG.md 和 docs/FEATURE_MAP.md」即可快速重建 context。
>
> **維護規則**
> - 每次 commit 前補記一筆，不需要長篇大論，3~5 行摘要即可
> - 已完成的項目不刪，改標記 ✅
> - 跨天未完成的項目保留在「進行中」直到完成

---

## 格式範本

```
## YYYY-MM-DD

### ✅ 完成
- `檔案路徑` 修改內容（一行說明）→ 對應：會議/決議來源

### 🔧 進行中
- `檔案路徑` 預計做什麼 → 對應：XXX

### ❓ 問題 / 待釐清
- 問題描述（等誰確認）
```

---

## 2026-04-26（補充）

### ✅ 完成
- `docs/FEATURE_MAP.md` IHG 季度視角移入「已完成」區塊（`?view=quarter` 前端已實作）→ 會議決議 §客房保養/巡檢

### 🔧 進行中
- 無

### ❓ 問題 / 待釐清
- **IHG 代碼對照表**：待業主提供正式代碼定義文件版本，確認後才能建 `ihg_code_reference` 表與 API
- **預算使用月份欄位**：`budget_transactions.budget_usage_month`（YYYY-MM）欄位尚缺，待財務確認口徑
- **財務解鎖/留痕**：`budget_adjustments` schema 設計待討論

---

## 2026-04-26

### ✅ 完成
- `backend/app/routers/*.py`（19 個 router）補上 `APIRouter(dependencies=[Depends(get_current_user)])`，業務資料全面需登入 → 安全補強
- `backend/app/routers/*.py`（13 個 router，30 個 endpoint）sync/debug 補上 `require_roles("system_admin","module_manager")` → 安全補強
- `frontend/src/api/securityPatrol.ts` 改用 `apiClient`（移除裸 axios），BASE 去掉 `/api/v1` 前綴 → Task A
- `frontend/src/api/mallFacilityInspection.ts` 改用 `apiClient`，BASE 去掉 `/api/v1` 前綴 → Task A
- `frontend/src/pages/Login/index.tsx` `devLogin()` 改呼叫真實後端，不再寫 fake token → Task B
- `backend/app/schemas/mall_dashboard.py` `FloorInspectionStats` 新增 `has_data: bool` 欄位 → Task C
- `backend/app/routers/mall_dashboard.py` `_floor_stats_for_date()` 設定 `has_data = len(batches) > 0` → Task C
- `frontend/src/types/mallDashboard.ts` `FloorInspectionStats` 新增 `has_data: boolean` → Task C
- `frontend/src/pages/MallDashboard/index.tsx` 樓層卡片 `has_data=false` 改顯示「尚無資料」；KPI sub-label 同步修正 → Task C
- `frontend/src/pages/IHGRoomMaintenance/index.tsx` 季度視角（`?view=quarter`）完整實作：`quarterRooms` useMemo 聚合、`QuarterCellComp`、月份/季度切換 `Segmented`、季度彙整 Drawer（含各月「查看」穿透至月份明細）→ 04-23 整合會議 §客房保養/巡檢 P1 缺口
- `docs/FEATURE_MAP.md` IHG 區塊補上季度視角說明列，`§待開發模組` 移除 IHG 季度視角缺口項目 → 同上
- `backend/app/routers/work_category_analysis.py` 新增第 4 來源 `ihg_room`（`IHGRoomMaintenanceMaster`），工時=`raw_json["工時計算"]`÷60，類別=「例行維護」→ ExecDashboard + WorkCategoryAnalysis 自動納入，零前端改動

### 🔧 進行中
- 無

### ❓ 問題 / 待釐清
- 事件單（IncidentCase）模組：Ragic 端欄位尚未完成，待確認後再開發
- case_progress 雙欄位（progress_note / progress_attachments）：同上，Ragic 端未就緒

---

## 2026-04-25

### ✅ 完成
- `docs/FEATURE_MAP.md` 建立全功能地圖（首版）→ 標準化作業建立
- `docs/DEV_LOG.md` 建立開發日誌（首版）→ 標準化作業建立
- `04-23整合會議_差異分析.xlsx` 完成 36 項功能缺口分析 → 對應：04-23 整合會議全部決議

### 🔧 進行中
- 無

### ❓ 問題 / 待釐清
- 退驗二段工時：Ragic 端欄位設計尚未確認，待工程部確認後再開發
- IHG 代碼（如 5.2）正式定義文件版本待確認
- 「將超支」門檻最終版本待財務確認

---

<!-- 往下新增新日期，最新在上 -->
