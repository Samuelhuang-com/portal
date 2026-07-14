import hashlib, sys

README_SRC = "README.md"
README_DST = "_tmp_readme_v47.md"
CHANGELOG_SRC = "docs/CHANGELOG.md"
CHANGELOG_DST = "_tmp_changelog_v47.md"

def load_verify(path, expected_sha):
    data = open(path, "r", encoding="utf-8").read()
    actual = hashlib.sha256(data.encode("utf-8")).hexdigest()
    if actual != expected_sha:
        print(f"SHA MISMATCH for {path}: actual={actual}")
        sys.exit(1)
    return data

readme = load_verify(README_SRC, "1a329eac2bcdcbf9cb312f1f4e1ce801ee41ec704826c6d74b9da5309f43856f")

OLD_HEADER = "**最後更新：2026-07-14（v1.80.46）**"
NEW_HEADER = "**最後更新：2026-07-14（v1.80.47）**"
assert readme.count(OLD_HEADER) == 1, f"header count={readme.count(OLD_HEADER)}"
readme = readme.replace(OLD_HEADER, NEW_HEADER, 1)

OLD_ANCHOR = "### v1.80.46 - 2026-07-14"
assert readme.count(OLD_ANCHOR) == 1, f"anchor count={readme.count(OLD_ANCHOR)}"

NEW_ENTRY = '''### v1.80.47 - 2026-07-14
- **修復 v1.80.46 造成的 full_building_maintenance 前端建置錯誤（JSX 語法錯誤）**：使用者回報 Vite 建置報錯 `Unexpected token, expected ","`，指向 `FullBuildingMaintenance/index.tsx` 月曆卡片附近；追查發現 v1.80.46 把 `{SHOW_MONTHLY_CALENDAR && (` 包在既有的 `{/* 月曆格：類別 × 日期 */}` JSX 註解「外層」時順序寫反，變成註解出現在 `(...)` 運算式括號內部，而 JSX 註解語法只能當獨立子項使用、不能放在一個運算式括號內，導致語法錯誤。修復：把 `{/* 月曆格：類別 × 日期 */}` 移到 `{SHOW_MONTHLY_CALENDAR && (` 外面、恢復成獨立的 JSX 子項；`mall/periodic-maintenance` 頁面因為原本就沒有這種註解在卡片正上方，未受影響、不需修改
- **驗證**：`diff` 確認只有這兩行順序對調，其餘完全相同；檔尾比對無截斷；括號配對與 U+FFFD 檢查正常；改用 `esbuild` 對兩個檔案個別做語法解析（`transform`／`buildSync` 皆通過），確認建置錯誤已排除

### v1.80.46 - 2026-07-14'''

readme = readme.replace(OLD_ANCHOR, NEW_ENTRY, 1)

with open(README_DST, "w", encoding="utf-8") as f:
    f.write(readme)
print("README OK", len(readme))

changelog = load_verify(CHANGELOG_SRC, "cc1b2840d36e1eff050fe65a6f6412f126cc218fbedef79214afdc28c539efdf")

OLD_CL_ANCHOR = "## [1.80.46] - 2026-07-14"
assert changelog.count(OLD_CL_ANCHOR) == 1, f"cl anchor count={changelog.count(OLD_CL_ANCHOR)}"

NEW_CL_ENTRY = '''## [1.80.47] - 2026-07-14

### Fixed — v1.80.46 造成的 full_building_maintenance 前端建置失敗（JSX 語法錯誤）

- **背景**：使用者回報 Vite/Babel 建置錯誤：`Unexpected token, expected ","`，錯誤位置在 `frontend/src/pages/FullBuildingMaintenance/index.tsx` 月曆卡片 `<Card size="small" ...>` 那一行；追查發現是上一版（v1.80.46，把月曆區塊改為 `{SHOW_MONTHLY_CALENDAR && (...)}` 條件渲染以先行隱藏）的疏漏
- **根因**：該檔案的月曆卡片正上方原本就有一行 JSX 註解 `{/* 月曆格：類別 × 日期 */}`；v1.80.46 修改時把整個「註解 + `<Card>...</Card>`」區塊一起包進 `{SHOW_MONTHLY_CALENDAR && ( ... )}` 的括號內，變成：
  ```
  {SHOW_MONTHLY_CALENDAR && (
  {/* 月曆格：類別 × 日期 */}
  <Card ...
  ```
  JSX 註解語法 `{/* ... */}` 只能作為獨立的 JSX 子項使用，不能出現在一個 JavaScript 運算式的括號（`(...)`）內部——括號內只能有單一運算式，多了這個註解會讓解析器把後面的 `<Card` 誤判成比較運算子而非 JSX 標籤，造成語法錯誤
  - `mall_periodic_maintenance/index.tsx` 的月曆卡片正上方沒有這種註解，所以 v1.80.46 對該檔案的修改沒有這個問題，本次不需要修正
- **修復**：把 `{/* 月曆格：類別 × 日期 */}` 移回 `{SHOW_MONTHLY_CALENDAR && (` 外面，恢復成獨立的 JSX 子項，僅對調這兩行的先後順序，不改動任何其他程式碼
- **驗證**：`diff` 確認變更僅為兩行順序對調，其餘逐行相同；檔尾比對無截斷；括號（`{`/`}`、`(`/`)`）配對計數平衡；U+FFFD 檢查為 0；改用 `esbuild.buildSync()` 分別對兩個頁面檔案做語法解析，確認皆可正常解析（不再報錯）

## [1.80.46] - 2026-07-14'''

changelog = changelog.replace(OLD_CL_ANCHOR, NEW_CL_ENTRY, 1)

with open(CHANGELOG_DST, "w", encoding="utf-8") as f:
    f.write(changelog)
print("CHANGELOG OK", len(changelog))
