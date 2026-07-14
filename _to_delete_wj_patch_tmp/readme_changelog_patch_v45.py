import hashlib, sys

README_SRC = "README.md"
README_DST = "_tmp_readme_v45.md"
CHANGELOG_SRC = "docs/CHANGELOG.md"
CHANGELOG_DST = "_tmp_changelog_v45.md"

def load_verify(path, expected_sha):
    data = open(path, "r", encoding="utf-8").read()
    actual = hashlib.sha256(data.encode("utf-8")).hexdigest()
    if actual != expected_sha:
        print(f"SHA MISMATCH for {path}: actual={actual}")
        sys.exit(1)
    return data

readme = load_verify(README_SRC, "f42d7bdfd864b28a143478f7acfe85bcfa2ab09cbb1b5e1ae262e263e4a22b87")

OLD_HEADER = "**最後更新：2026-07-14（v1.80.44）**"
NEW_HEADER = "**最後更新：2026-07-14（v1.80.45）**"
assert readme.count(OLD_HEADER) == 1, f"header count={readme.count(OLD_HEADER)}"
readme = readme.replace(OLD_HEADER, NEW_HEADER, 1)

OLD_ANCHOR = "### v1.80.44 - 2026-07-14"
assert readme.count(OLD_ANCHOR) == 1, f"anchor count={readme.count(OLD_ANCHOR)}"

NEW_ENTRY = '''### v1.80.45 - 2026-07-14
- **全棟例行維護／飯店週期保養「異常待追蹤」KPI 口徑修正（比照 v1.80.44 mall_pm 同日修正一併檢查）**：使用者要求「其他模組也一併檢查修正」，追查 `full_building_maintenance.py`（全棟例行維護）與 `periodic_maintenance.py`（飯店週期保養）的 `_calc_kpi()`，發現兩者都跟修正前的 mall_pm 一樣，`abnormal` 是算整批（含跨月）全部項目，跟 `overdue`／`scheduled`／`unscheduled`／`in_progress` 只算本月項目（`current_items`）的口徑不一致；比照 v1.80.44 的修法，兩檔案均改為 `abnormal = sum(1 for it, _ in current_items if it.abnormal_flag)`。同步修正 `FullBuildingMaintenance/index.tsx` 明細 Drawer 的 `abnormal` 篩選條件（加上排除 `status === 'non_current_month'`）；`periodic_maintenance.py`（飯店週期保養）前端 Dashboard 的 KPI 卡片本身沒有點擊開明細 Drawer 的功能，故該模組僅後端口徑修正，無對應前端改動

### v1.80.44 - 2026-07-14'''

readme = readme.replace(OLD_ANCHOR, NEW_ENTRY, 1)

with open(README_DST, "w", encoding="utf-8") as f:
    f.write(readme)
print("README OK", len(readme))

changelog = load_verify(CHANGELOG_SRC, "e51be479a50a66b88ba47f93560eb9436b15d454213b09b8924475dc6b2a12f9")

OLD_CL_ANCHOR = "## [1.80.44] - 2026-07-14"
assert changelog.count(OLD_CL_ANCHOR) == 1, f"cl anchor count={changelog.count(OLD_CL_ANCHOR)}"

NEW_CL_ENTRY = '''## [1.80.45] - 2026-07-14

### Fixed — full_building_maintenance／periodic_maintenance「異常待追蹤」KPI 統計範圍不一致（比照 v1.80.44 一併檢查其他模組）

- **背景**：v1.80.44 修正 mall_periodic_maintenance 的 `abnormal` KPI 口徑後，使用者要求「其他模組也一併檢查修正」；追查 `full_building_maintenance.py`（全棟例行維護）與 `periodic_maintenance.py`（飯店週期保養）的 `_calc_kpi()`，確認兩者的 `abnormal` 都同樣是用整批（`items`，含非本月項目）計算，跟同一函式裡 `overdue`／`scheduled`／`unscheduled`／`in_progress` 都是用「排除非本月項目後」的 `current_items` 計算，口徑不一致，屬於跟 mall_pm 修正前完全相同的 bug
- **修復**：
  - `backend/app/routers/full_building_maintenance.py`：`abnormal = sum(1 for it in items if it.abnormal_flag)` 改為 `abnormal = sum(1 for it, _ in current_items if it.abnormal_flag)`
  - `backend/app/routers/periodic_maintenance.py`：同樣改為 `abnormal = sum(1 for it, _ in current_items if it.abnormal_flag)`
  - `frontend/src/pages/FullBuildingMaintenance/index.tsx`：KPI 卡片明細 Drawer 的 `abnormal` 篩選條件由 `detail.items.filter((it) => it.abnormal_flag)` 改為 `detail.items.filter((it) => it.abnormal_flag && it.status !== 'non_current_month')`，避免卡片數字改成「只算本月」之後，點進去的明細清單卻還是「全部項目」而對不起來
  - `periodic_maintenance.py`（飯店週期保養）對應前端頁面 `PeriodicMaintenance/index.tsx` 的 Dashboard KPI 卡片本身沒有點擊開明細 Drawer 的功能（無 `onClick`），確認後不需要、也無法比照新增前端篩選修正
- **範圍說明**：僅修正 `abnormal` 欄位，`completed`（已完成）仍維持原本「所有保養時間啟迄均有值的項目，含非本月」的既有口徑不變，與表格「完成」☑ 欄一致——此為使用者明確指示（「異常」也只算本月項目，未要求變更 `completed`）
- **驗證**：`py_compile` 通過（兩支後端檔案）；`diff` 確認三個檔案變更均只有對應這一行判斷式／篩選式，其餘程式碼逐行相同；檔尾比對無截斷；`.tsx` 檔案括號配對（`{`/`}`、`(`/`)`）與 U+FFFD 檢查均正常

## [1.80.44] - 2026-07-14'''

changelog = changelog.replace(OLD_CL_ANCHOR, NEW_CL_ENTRY, 1)

with open(CHANGELOG_DST, "w", encoding="utf-8") as f:
    f.write(changelog)
print("CHANGELOG OK", len(changelog))
