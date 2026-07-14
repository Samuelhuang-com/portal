import hashlib, sys

README_SRC = "README.md"
README_DST = "_tmp_readme_v41.md"
CHANGELOG_SRC = "docs/CHANGELOG.md"
CHANGELOG_DST = "_tmp_changelog_v41.md"

readme = open(README_SRC, "r", encoding="utf-8").read()

OLD_HEADER = "**最後更新：2026-07-14（v1.80.40）**"
NEW_HEADER = "**最後更新：2026-07-14（v1.80.41）**"
assert readme.count(OLD_HEADER) == 1, f"header count={readme.count(OLD_HEADER)}"
readme = readme.replace(OLD_HEADER, NEW_HEADER, 1)

OLD_ANCHOR = "### v1.80.40 - 2026-07-14"
assert readme.count(OLD_ANCHOR) == 1, f"anchor count={readme.count(OLD_ANCHOR)}"

NEW_ENTRY = '''### v1.80.41 - 2026-07-14
- **mall/periodic-maintenance Dashboard「2026/07 商場工務每日巡檢狀況」月曆格資料來源錯誤**：使用者指出這個副標題與模組本身（商場週期保養）不符，追查後發現 Dashboard 的月曆格從一開始就是呼叫 `fetchMallFIDailyCalendar()`──也就是「商場工務巡檢（mall_facility_inspection）」模組自己的每日巡檢月曆 API，跟本模組（商場週期保養）完全是不同資料來源；標題文字其實正確描述了「顯示的是每日巡檢狀況」，只是這份資料本來就不該出現在這個模組。追查發現 `full_building_maintenance.py`（全棟例行維護，同一批 2026-07-13 Sheet 改版模組）早就有自己專屬的 `GET /calendar`（類別 × 日期）端點，但 `mall_periodic_maintenance.py` 從未補上對應版本；修復方式：在 `mall_periodic_maintenance.py` 新增 `GET /calendar` 端點（邏輯與 full_bldg_pm 版本一致，依 `MallPeriodicMaintenanceItem.category` × `scheduled_date` 算出每日完成率／異常數／待處理數），frontend 新增 `fetchMallPMCalendar()`，`MallPeriodicMaintenance/index.tsx` 改呼叫這支新端點取代 `fetchMallFIDailyCalendar()`，並將標題改為「YYYY/MM 商場例行維護狀況」、`rowHeaderLabel` 由「巡檢區域」改為「保養類別」（比照全棟例行維護頁面用詞）

### v1.80.40 - 2026-07-14'''

readme = readme.replace(OLD_ANCHOR, NEW_ENTRY, 1)

with open(README_DST, "w", encoding="utf-8") as f:
    f.write(readme)
print("README OK", len(readme))

changelog = open(CHANGELOG_SRC, "r", encoding="utf-8").read()

OLD_CL_ANCHOR = "## [1.80.40] - 2026-07-14"
assert changelog.count(OLD_CL_ANCHOR) == 1, f"cl anchor count={changelog.count(OLD_CL_ANCHOR)}"

NEW_CL_ENTRY = '''## [1.80.41] - 2026-07-14

### Fixed — mall/periodic-maintenance Dashboard 月曆格誤用商場工務巡檢資料

- **背景**：使用者指出 mall/periodic-maintenance（商場週期保養）模組 Dashboard 底部的月曆卡片副標題「2026/07 商場工務每日巡檢狀況」與模組本身（商場週期保養／例行維護）不符，要求找出真正該對應的數值並修正標題
- **排查**：追到 `frontend/src/pages/MallPeriodicMaintenance/index.tsx` 的 `loadDashboard()`，發現月曆格資料是呼叫 `fetchMallFIDailyCalendar(y, m)`──這是「商場工務巡檢」（`mall_facility_inspection` 模組，樓層別每日巡檢紀錄）自己的 API，跟本頁面（商場週期保養）完全是不同模組、不同資料表。也就是說標題文字本身沒有寫錯字，它正確描述了實際顯示的資料（每日巡檢狀況），只是這份資料從一開始就不屬於這個頁面，應該顯示的是週期保養項目自己的類別 × 日完成狀況；比對發現同一批 2026-07-13 Sheet 改版的姊妹模組 `full_building_maintenance.py`（全棟例行維護）已經有自己專屬的 `GET /calendar` 端點（依 `category` × `scheduled_date` 算完成率／異常數／待處理數），但 `mall_periodic_maintenance.py` 從未補上對應版本，Dashboard 開發時暫時借用了商場工務巡檢的月曆 API 當佔位資料，後續未再替換
- **修復**：
  - 後端：`mall_periodic_maintenance.py` 新增 `GET /calendar`（類別 × 日期月曆格），邏輯與 `full_building_maintenance.py::get_calendar()` 一致 —— 依批次月份找出 `MallPeriodicMaintenanceItem`，用 `_reconstruct_full_date()` 還原完整日期後依類別×日分組，每格回傳 `has_record`／`completion_rate`／`abnormal_count`／`pending_count`；已知類別沿用全棟例行維護的順序（水電/空調/照明/消防/申報/整體），商場實際出現的其他類別仍會自動附加在後，不會被排除
  - 前端：`frontend/src/api/mallPeriodicMaintenance.ts` 新增 `fetchMallPMCalendar(year, month)`；`MallPeriodicMaintenance/index.tsx` 的 `loadDashboard()` 改呼叫這支新端點取代 `fetchMallFIDailyCalendar()`，`calRows` 直接採用後端回傳的 `rows`（不再需要 `.sheets.map()` 轉換，因為新端點回傳格式已直接對齊 `MonthlyCalendarGrid` 元件所需的 `CalendarRow[]`）
  - 標題與欄位標籤：卡片標題由「YYYY/MM 商場工務每日巡檢狀況」改為「YYYY/MM 商場例行維護狀況」；`rowHeaderLabel` 由「巡檢區域」改為「保養類別」（比照全棟例行維護頁面「保養類別」的用詞）
- **驗證**：`py_compile` 通過；三個檔案（`mall_periodic_maintenance.py`／`mallPeriodicMaintenance.ts`／`MallPeriodicMaintenance/index.tsx`）逐一 `diff` 確認變更範圍精準對應上述項目、無誤刪；`{`/`}`、`(`/`)` 括號配對計數與 U+FFFD 檢查均正常；檔尾比對無截斷
- **後續**：此為新增端點＋換資料來源，不影響既有資料表結構，無需資料庫遷移；下次前端重新整理 mall/periodic-maintenance 頁面即可看到修正後的月曆格與標題

## [1.80.40] - 2026-07-14'''

changelog = changelog.replace(OLD_CL_ANCHOR, NEW_CL_ENTRY, 1)

with open(CHANGELOG_DST, "w", encoding="utf-8") as f:
    f.write(changelog)
print("CHANGELOG OK", len(changelog))
