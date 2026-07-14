import hashlib, sys

README_SRC = "README.md"
README_DST = "_tmp_readme_v43.md"
CHANGELOG_SRC = "docs/CHANGELOG.md"
CHANGELOG_DST = "_tmp_changelog_v43.md"

readme = open(README_SRC, "r", encoding="utf-8").read()

OLD_HEADER = "**最後更新：2026-07-14（v1.80.42）**"
NEW_HEADER = "**最後更新：2026-07-14（v1.80.43）**"
assert readme.count(OLD_HEADER) == 1, f"header count={readme.count(OLD_HEADER)}"
readme = readme.replace(OLD_HEADER, NEW_HEADER, 1)

OLD_ANCHOR = "### v1.80.42 - 2026-07-14"
assert readme.count(OLD_ANCHOR) == 1, f"anchor count={readme.count(OLD_ANCHOR)}"

NEW_ENTRY = '''### v1.80.43 - 2026-07-14
- **mall/periodic-maintenance 月曆格加上點擊開明細 Drawer**：使用者確認新月曆格資料正確後，希望點格子能看明細。`MonthlyCalendarGrid`（共用元件）新增選填的 `onCellClick` prop（僅 `has_record` 的格子可點、其餘頁面未傳入此 prop 則行為不變），`MallPeriodicMaintenance/index.tsx` 串接後點格子會用「類別＋排定日期」篩出當日項目，開啟既有的 KPI 明細 Drawer（與 KPI 卡片共用同一個 Drawer，不重複造輪子）

### v1.80.42 - 2026-07-14'''

readme = readme.replace(OLD_ANCHOR, NEW_ENTRY, 1)

with open(README_DST, "w", encoding="utf-8") as f:
    f.write(readme)
print("README OK", len(readme))

changelog = open(CHANGELOG_SRC, "r", encoding="utf-8").read()

OLD_CL_ANCHOR = "## [1.80.42] - 2026-07-14"
assert changelog.count(OLD_CL_ANCHOR) == 1, f"cl anchor count={changelog.count(OLD_CL_ANCHOR)}"

NEW_CL_ENTRY = '''## [1.80.43] - 2026-07-14

### Added — mall/periodic-maintenance 月曆格點擊可開明細 Drawer

- **背景**：v1.80.41 修好月曆格資料來源後，使用者確認畫面正確，並提出希望點擊月曆格子能看到當天／該類別的明細清單（比照 KPI 卡片點擊已有的明細 Drawer）
- **實作**：
  - `frontend/src/components/MonthlyCalendarGrid.tsx`（共用元件，多個模組頁面都在用）新增選填的 `onCellClick?: (day, rowKey, data) => void` prop；只有 `has_record` 為真的格子會套用 `cursor: pointer` 並在點擊時觸發回呼，未傳入此 prop 或格子本身無資料時行為與之前完全一致，不影響其餘已使用本元件的頁面（full_bldg_pm、mall_fi、hotel_di 等）
  - `frontend/src/pages/MallPeriodicMaintenance/index.tsx` 新增 `openCalendarCellDrawer(day, category)`：以「類別 = 該列＋排定日期 = 該格日期（MM/DD）」向 `fetchMallPMBatchDetail()` 取回的整批項目做篩選，篩選口徑刻意對齊月曆格本身依 `scheduled_date` 分組的邏輯，確保點進去的清單筆數跟格子本身呈現的統計一致；直接重用既有的 KPI 卡片明細 Drawer（`kpiDrawerOpen`／`kpiDrawerTitle`／`kpiDrawerItems`／`kpiDrawerLoading` 這組 state），不另外新增一個 Drawer 元件
- **驗證**：`diff` 確認兩檔案變更範圍精準對應上述項目；`{`/`}`、`(`/`)` 括號配對計數與 U+FFFD 檢查均正常；檔尾比對無截斷
- **範圍說明**：這次只在 mall_pm 頁面串接點擊行為（使用者本次要求的範圍）；`onCellClick` 是通用共用元件的新選填 prop，其餘模組（如全棟例行維護）目前仍維持原樣不可點擊，之後如有需要可用同樣方式個別串接，不需要再改共用元件本身

## [1.80.42] - 2026-07-14'''

changelog = changelog.replace(OLD_CL_ANCHOR, NEW_CL_ENTRY, 1)

with open(CHANGELOG_DST, "w", encoding="utf-8") as f:
    f.write(changelog)
print("CHANGELOG OK", len(changelog))
