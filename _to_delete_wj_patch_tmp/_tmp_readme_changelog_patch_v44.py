import hashlib, sys

README_SRC = "README.md"
README_DST = "_tmp_readme_v44.md"
CHANGELOG_SRC = "docs/CHANGELOG.md"
CHANGELOG_DST = "_tmp_changelog_v44.md"

readme = open(README_SRC, "r", encoding="utf-8").read()

OLD_HEADER = "**最後更新：2026-07-14（v1.80.43）**"
NEW_HEADER = "**最後更新：2026-07-14（v1.80.44）**"
assert readme.count(OLD_HEADER) == 1, f"header count={readme.count(OLD_HEADER)}"
readme = readme.replace(OLD_HEADER, NEW_HEADER, 1)

OLD_ANCHOR = "### v1.80.43 - 2026-07-14"
assert readme.count(OLD_ANCHOR) == 1, f"anchor count={readme.count(OLD_ANCHOR)}"

NEW_ENTRY = '''### v1.80.44 - 2026-07-14
- **mall/periodic-maintenance「異常待追蹤」KPI 口徑修正為只算本月項目**：使用者詢問後確認，`_calc_kpi()` 裡 `abnormal` 原本是算整批（含跨月）全部項目，跟 `overdue`／`scheduled`／`unscheduled`／`in_progress` 都只算本月項目（`current_items`）的口徑不一致；改為 `abnormal = sum(1 for it, _ in current_items if it.abnormal_flag)`，只算本月項目。同步修正前端明細 Drawer 的 `abnormal` 篩選條件（加上排除 `status === 'non_current_month'`），確保點卡片看到的清單筆數跟卡片數字一致

### v1.80.43 - 2026-07-14'''

readme = readme.replace(OLD_ANCHOR, NEW_ENTRY, 1)

with open(README_DST, "w", encoding="utf-8") as f:
    f.write(readme)
print("README OK", len(readme))

changelog = open(CHANGELOG_SRC, "r", encoding="utf-8").read()

OLD_CL_ANCHOR = "## [1.80.43] - 2026-07-14"
assert changelog.count(OLD_CL_ANCHOR) == 1, f"cl anchor count={changelog.count(OLD_CL_ANCHOR)}"

NEW_CL_ENTRY = '''## [1.80.44] - 2026-07-14

### Fixed — mall/periodic-maintenance「異常待追蹤」KPI 統計範圍不一致

- **背景**：使用者詢問 Dashboard「異常待追蹤」KPI 卡片的計算方式，追查後發現 `_calc_kpi()`（`backend/app/routers/mall_periodic_maintenance.py`）裡 `abnormal` 是用整批（`items`，含非本月項目）計算，跟同一函式裡 `overdue`／`scheduled`／`unscheduled`／`in_progress` 都是用「排除非本月項目後」的 `current_items` 計算，口徑並不一致；使用者確認後要求「異常」也比照只算本月項目
- **修復**：
  - 後端：`abnormal = sum(1 for it in items if it.abnormal_flag)` 改為 `abnormal = sum(1 for it, _ in current_items if it.abnormal_flag)`，與 overdue 等欄位口徑對齊
  - 前端：`MallPeriodicMaintenance/index.tsx` 的 KPI 卡片明細 Drawer，`abnormal` 篩選條件由 `detail.items.filter((it) => it.abnormal_flag)` 改為 `detail.items.filter((it) => it.abnormal_flag && it.status !== 'non_current_month')`，避免卡片數字改成「只算本月」之後，點進去的明細清單卻還是「全部項目」而對不起來
- **驗證**：`py_compile` 通過；`diff` 確認兩檔案變更均只有這一行判斷式，其餘程式碼逐行相同；檔尾比對無截斷
- **範圍說明**：此次僅修正 mall_periodic_maintenance 模組；`full_building_maintenance.py`（全棟例行維護）與 `periodic_maintenance.py`（飯店週期保養）的 `_calc_kpi()` 是否有同樣的口徑不一致，尚未逐一確認，待使用者需要時再一併檢查

## [1.80.43] - 2026-07-14'''

changelog = changelog.replace(OLD_CL_ANCHOR, NEW_CL_ENTRY, 1)

with open(CHANGELOG_DST, "w", encoding="utf-8") as f:
    f.write(changelog)
print("CHANGELOG OK", len(changelog))
