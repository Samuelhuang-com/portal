import hashlib, sys

README_SRC = "README.md"
README_DST = "_tmp_readme_v39.md"
CHANGELOG_SRC = "docs/CHANGELOG.md"
CHANGELOG_DST = "_tmp_changelog_v39.md"

# ── README.md ──────────────────────────────────────────────────────────────

readme = open(README_SRC, "r", encoding="utf-8").read()

OLD_HEADER = "**最後更新：2026-07-14（v1.80.38）**"
NEW_HEADER = "**最後更新：2026-07-14（v1.80.39）**"
assert readme.count(OLD_HEADER) == 1, f"header count={readme.count(OLD_HEADER)}"
readme = readme.replace(OLD_HEADER, NEW_HEADER, 1)

OLD_ANCHOR = "### v1.80.38 - 2026-07-14"
assert readme.count(OLD_ANCHOR) == 1, f"anchor count={readme.count(OLD_ANCHOR)}"

NEW_ENTRY = '''### v1.80.39 - 2026-07-14
- **修正整棟保養／商場週期保養「工作日誌」顯示日期：有維修記錄時改用實際日期，不再只認排定日期**：使用者以 Ragic record（棟週保202607-001，Sheet28 item id=262）驗證，該項目排定日期是 07/10，但因故延期、實際維修在 07/13（子表維修記錄明細可查），「工作日誌」TAB 卻沒有依實際維修日期呈現；追查發現 `work_journal.py` 的 `_fetch_mall_pm()`／`_fetch_full_bldg_pm()` 原本以 `item.scheduled_date == 查詢日` 篩選項目，完全未考慮子表維修記錄（`mall_pm_item_worklog`／`full_bldg_pm_item_worklog`）的實際執行日期。新增 `_parse_pm_datetime()`（解析子表原始日期時間字串）與 `_group_pm_worklog_rows()`（比照既有 dazhi／luqun 子表歸戶規格 `_group_detail_rows()`），改為：有維修記錄子表時一律以子表「時間開始」實際日期歸戶（不再採用排定日期，可能因此改出現在其他天、或同一項目分散在多天各自的工時列）；無維修記錄（或子表無可解析時間）則維持原本「排定日期＋預估工時」的邏輯不變

### v1.80.38 - 2026-07-14'''

readme = readme.replace(OLD_ANCHOR, NEW_ENTRY, 1)

with open(README_DST, "w", encoding="utf-8") as f:
    f.write(readme)
print("README OK", len(readme))

# ── docs/CHANGELOG.md ────────────────────────────────────────────────────────

changelog = open(CHANGELOG_SRC, "r", encoding="utf-8").read()

OLD_CL_ANCHOR = "## [1.80.38] - 2026-07-14"
assert changelog.count(OLD_CL_ANCHOR) == 1, f"cl anchor count={changelog.count(OLD_CL_ANCHOR)}"

NEW_CL_ENTRY = '''## [1.80.39] - 2026-07-14

### Fixed — full_bldg_pm／mall_pm「工作日誌」顯示日期：有維修記錄時應以實際日期為準，不應只認排定日期

- **背景**：使用者以 Ragic 記錄 https://ap12.ragic.com/soutlet001/periodic-maintenance/28/262（日誌編號 棟週保202607-001）驗證：排定日期 07/10，但實際維修時間是 2026/07/13（子表「維修記錄」明細可查，經使用者直接對照 Ragic 原始資料確認），「工作日誌」TAB 卻沒有依 07/13 呈現該筆記錄；使用者並要求評估「當有『維護記錄』時應優先於上方欄位所示日期」這個原則在 Portal 內的適用範圍
- **排查**：`backend/app/routers/work_journal.py` 的 `_fetch_mall_pm()`／`_fetch_full_bldg_pm()` 在 SQL 層以 `item.scheduled_date == 查詢日` 篩選當日項目，`scheduled_date` 是 Ragic 主表的「排定」欄位，與子表 `mall_pm_item_worklog`／`full_bldg_pm_item_worklog`（Sheet24／Sheet28 巢狀維修記錄，`start_time`／`end_time` 為原始字串、來源即實際執行時間）完全獨立，兩者可能因延期、補做等情況不一致；此前只有 dazhi／luqun 報修類（`_group_detail_rows()`，2026-06-11 業主確認規格）已支援「有子表則以子表時間開始日期歸戶」，週期保養類（mall_pm／full_bldg_pm）尚未套用同一原則
- **修復**：
  - 新增 `_parse_pm_datetime(s)`：解析子表 `start_time`／`end_time` 的 Ragic 原始日期時間字串（`YYYY/MM/DD HH:MM:SS` 或無秒/純日期變體），解析失敗回 `None`
  - 新增 `_group_pm_worklog_rows(recs, target, fallback_person)`：`_group_detail_rows()` 的週期保養子表版本，篩選子表「時間開始」日期 == target 後依人員（`staff_name`，透過既有 `_split_detail_persons()` 拆多人、空白時掛回 `executor_name`）分組合併，計算該日工時（起訖秒數加總後轉分鐘）
  - `_fetch_mall_pm()`／`_fetch_full_bldg_pm()`：SQL 查詢改為只用 `batch_ragic_id` 篩選（取得整批項目，不再以 `scheduled_date` 篩選），逐項目判斷：子表有可解析「時間開始」的記錄 → 呼叫 `_group_pm_worklog_rows()`，只在該日有子表活動時才產生列（人員/工時/起訖時間皆取自子表當日資料），忽略排定日期；子表無可解析時間（含完全沒有子表）→ 維持原本「`scheduled_date == 查詢日`＋預估工時」邏輯不變
  - `detail_records`（Drawer 明細子表，透過 `_pm_detail_records_payload()`）維持顯示該項目全部歷史子表記錄，不受本次日期篩選變更影響
- **驗證**：`py_compile` 通過；`diff` 確認變更僅限 `_fetch_mall_pm()`／`_fetch_full_bldg_pm()` 兩函式本體與新增的兩個 helper，其餘程式碼逐行相同；檔尾比對無截斷
- **後續**：使用者要求評估的「Portal 全域顯示日期規則（有維護記錄用維護記錄，否則用上方欄位日期）」屬於較大範圍的評估項目（行事曆彙整、年度矩陣、KPI 計算等其他頁面是否有類似排定日期／實際日期不一致風險），將另行整理調查結果供使用者確認後再決定是否擴大修改範圍，本次先只處理「工作日誌」TAB 這個明確回報的案例

## [1.80.38] - 2026-07-14'''

changelog = changelog.replace(OLD_CL_ANCHOR, NEW_CL_ENTRY, 1)

with open(CHANGELOG_DST, "w", encoding="utf-8") as f:
    f.write(changelog)
print("CHANGELOG OK", len(changelog))
