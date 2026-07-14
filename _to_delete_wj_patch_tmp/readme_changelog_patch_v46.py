import hashlib, sys

README_SRC = "README.md"
README_DST = "_tmp_readme_v46.md"
CHANGELOG_SRC = "docs/CHANGELOG.md"
CHANGELOG_DST = "_tmp_changelog_v46.md"

def load_verify(path, expected_sha):
    data = open(path, "r", encoding="utf-8").read()
    actual = hashlib.sha256(data.encode("utf-8")).hexdigest()
    if actual != expected_sha:
        print(f"SHA MISMATCH for {path}: actual={actual}")
        sys.exit(1)
    return data

readme = load_verify(README_SRC, "b9a7a9d04bd02859515eb6b4ccf5f4ec81dc984420647e66f862d4539e0bbd44")

OLD_HEADER = "**最後更新：2026-07-14（v1.80.45）**"
NEW_HEADER = "**最後更新：2026-07-14（v1.80.46）**"
assert readme.count(OLD_HEADER) == 1, f"header count={readme.count(OLD_HEADER)}"
readme = readme.replace(OLD_HEADER, NEW_HEADER, 1)

OLD_ANCHOR = "### v1.80.45 - 2026-07-14"
assert readme.count(OLD_ANCHOR) == 1, f"anchor count={readme.count(OLD_ANCHOR)}"

NEW_ENTRY = '''### v1.80.46 - 2026-07-14
- **mall/periodic-maintenance、mall/full-building-maintenance Dashboard 月曆區塊先隱藏（保留程式碼）**：使用者確認兩模組 Dashboard 的月曆卡片（「YYYY/MM 商場例行維護狀況」、「全棟例行維護排程狀況」）先隱藏、不刪除程式碼，之後如需要可再開回。兩個頁面元件各自新增 `const SHOW_MONTHLY_CALENDAR = false`（含說明註解），並把原本的月曆 `<Card>` 區塊整段用 `{SHOW_MONTHLY_CALENDAR && (...)}` 包起來；只影響是否渲染，元件本身、資料抓取、`onCellClick` 明細 Drawer 等既有邏輯完全未變動，日後只要把常數改回 `true` 即可復原顯示

### v1.80.45 - 2026-07-14'''

readme = readme.replace(OLD_ANCHOR, NEW_ENTRY, 1)

with open(README_DST, "w", encoding="utf-8") as f:
    f.write(readme)
print("README OK", len(readme))

changelog = load_verify(CHANGELOG_SRC, "c519dd6c4cee3ff35aad83f85b0a7e8f391ab501b3824ff8b3d48b9efb635266")

OLD_CL_ANCHOR = "## [1.80.45] - 2026-07-14"
assert changelog.count(OLD_CL_ANCHOR) == 1, f"cl anchor count={changelog.count(OLD_CL_ANCHOR)}"

NEW_CL_ENTRY = '''## [1.80.46] - 2026-07-14

### Changed — mall_periodic_maintenance／full_building_maintenance Dashboard 月曆區塊先隱藏

- **背景**：使用者要求把兩個模組 Dashboard 上的月曆卡片先隱藏起來（mall/periodic-maintenance 的「YYYY/MM 商場例行維護狀況」與 mall/full-building-maintenance 的「全棟例行維護排程狀況」），並明確要求「程式不要刪除，先隱藏起來」——即只改變是否顯示，不能移除既有功能程式碼，以便日後隨時可以再開回來
- **實作**：
  - `frontend/src/pages/MallPeriodicMaintenance/index.tsx`：在元件上方新增 `const SHOW_MONTHLY_CALENDAR = false`（含說明註解），並把原本的月曆 `<Card>` 區塊（含 `MonthlyCalendarGrid` 與其 `onCellClick` 明細 Drawer 串接）整段用 `{SHOW_MONTHLY_CALENDAR && (...)}` 包住
  - `frontend/src/pages/FullBuildingMaintenance/index.tsx`：作法相同，同樣新增 `const SHOW_MONTHLY_CALENDAR = false` 並包住對應的月曆 `<Card>` 區塊
  - 兩個檔案的資料抓取（`calRows`／`calMaxDay` 等）、後端 `/calendar` 端點、共用元件 `MonthlyCalendarGrid` 本身均未變動，之後如需重新顯示，只要把各自檔案裡的 `SHOW_MONTHLY_CALENDAR` 改回 `true` 即可，不需要復原任何程式碼
- **驗證**：`diff` 確認兩檔案變更均只有「新增常數＋包一層條件渲染」，其餘程式碼逐行相同；檔尾比對無截斷；括號配對（`{`/`}`、`(`/`)`）計數兩檔案皆平衡；U+FFFD 檢查均為 0

## [1.80.45] - 2026-07-14'''

changelog = changelog.replace(OLD_CL_ANCHOR, NEW_CL_ENTRY, 1)

with open(CHANGELOG_DST, "w", encoding="utf-8") as f:
    f.write(changelog)
print("CHANGELOG OK", len(changelog))
