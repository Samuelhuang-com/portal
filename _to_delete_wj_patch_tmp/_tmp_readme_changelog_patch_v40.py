import hashlib, sys

README_SRC = "README.md"
README_DST = "_tmp_readme_v40.md"
CHANGELOG_SRC = "docs/CHANGELOG.md"
CHANGELOG_DST = "_tmp_changelog_v40.md"

readme = open(README_SRC, "r", encoding="utf-8").read()

OLD_HEADER = "**最後更新：2026-07-14（v1.80.39）**"
NEW_HEADER = "**最後更新：2026-07-14（v1.80.40）**"
assert readme.count(OLD_HEADER) == 1, f"header count={readme.count(OLD_HEADER)}"
readme = readme.replace(OLD_HEADER, NEW_HEADER, 1)

OLD_ANCHOR = "### v1.80.39 - 2026-07-14"
assert readme.count(OLD_ANCHOR) == 1, f"anchor count={readme.count(OLD_ANCHOR)}"

NEW_ENTRY = '''### v1.80.40 - 2026-07-14
- **full_bldg_pm／mall_pm 附圖仍抓不到：新增欄位 key 備援偵測（`_images_fallback` 邏輯）**：使用者再以另一筆記錄（Sheet28 item id=262）驗證，確認 Ragic 上有圖檔，但「工作日誌」Drawer 仍未顯示附圖（前一版 v1.80.38 已修正 `images_json` 欄位缺少自動遷移的問題，但這次追查發現另一個潛在成因：`full_building_maintenance_sync.py`／`mall_periodic_maintenance_sync.py` 讀取圖片的欄位常數 `CK28L_IMAGES`／`CK24L_IMAGES`＝`"圖片上傳"`，是 2026-07-13 新增時的假設值，並沒有像同檔案其餘 `CK28L_*`／`CK24L_*` 常數一樣附上「實測驗證」註記，代表這個 Ragic 欄位 label 是否正確從未被證實過，若猜錯就會讓 `full_record.get(CK28L_IMAGES)` 永遠拿不到值，即使 Ragic 記錄確實有圖檔，同步結果也會是空清單）；`sync_items_from_sheet28()`／`sync_items_from_sheet24()` 新增備援邏輯：主要欄位 key 抓不到值時，改在該筆記錄的 Ragic 原始回傳資料中尋找任何含「圖片／附件／照片／相片／附圖／拍照／image／upload／photo」關鍵字的欄位當備援來源，並在同步結果新增 `images_fallback_used` 計數＋首次觸發時記錄警告（含真正命中的欄位 key），方便後續從 log 確認正確欄位名稱以徹底修正常數；此變更為「有資料才生效」的純備援層，若原本設定的 key 本來就正確則完全不影響現有行為

### v1.80.39 - 2026-07-14'''

readme = readme.replace(OLD_ANCHOR, NEW_ENTRY, 1)

with open(README_DST, "w", encoding="utf-8") as f:
    f.write(readme)
print("README OK", len(readme))

changelog = open(CHANGELOG_SRC, "r", encoding="utf-8").read()

OLD_CL_ANCHOR = "## [1.80.39] - 2026-07-14"
assert changelog.count(OLD_CL_ANCHOR) == 1, f"cl anchor count={changelog.count(OLD_CL_ANCHOR)}"

NEW_CL_ENTRY = '''## [1.80.40] - 2026-07-14

### Fixed — full_bldg_pm／mall_pm 附圖仍抓不到：新增 Ragic 圖片欄位 key 備援偵測

- **背景**：v1.80.38 已修正 `images_json` 欄位缺少自動遷移導致查詢報錯的問題，但使用者以另一筆記錄（https://ap12.ragic.com/soutlet001/periodic-maintenance/28/262）再次驗證，確認 Ragic 上確實有圖檔，「工作日誌」Drawer 仍未顯示附圖，代表除了欄位缺失之外還有其他成因
- **排查**：檢視 `full_building_maintenance_sync.py`／`mall_periodic_maintenance_sync.py` 的欄位常數區塊，發現 `CK28L_IMAGES`／`CK24L_IMAGES`＝`"圖片上傳"` 的註解只寫「2026-07-13 新增」，不像同檔案其餘 `CK28L_*`／`CK24L_*`／`CK28S_*` 常數都明確標註「實測驗證」（即已對照 Ragic 實際 API 回傳資料確認過欄位 key 正確）。也就是說這個圖片欄位的 key 從一開始就只是假設值，從未被證實與 Ragic 實際回傳的欄位 label 相符；若猜錯，`full_record.get(CK28L_IMAGES)` 會永遠回傳 `None`，`parse_images(None, ...)` 依其設計直接回傳空陣列，導致即使 Ragic 記錄確實有圖檔，`images_json` 仍會被同步寫入為空清單 `[]`，而非因為缺欄位而報錯（因此這個成因不會在 log 留下任何錯誤訊息，比 v1.80.38 那個缺欄位的問題更難察覺）
- **修復**：`sync_items_from_sheet28()`／`sync_items_from_sheet24()` 在讀取圖片欄位時新增備援偵測：若設定的欄位 key（`CK28L_IMAGES`／`CK24L_IMAGES`）抓不到值，改在該筆記錄 `fetch_one()` 回傳的全部欄位 key 中尋找任何含「圖片／附件／照片／相片／附圖／拍照／image／upload／photo」關鍵字者作為備援來源；新增 `images_fallback_used` 計數並納入同步結果與完成時的 log 摘要，備援命中時另外記錄一次警告（含 item id 與實際命中的欄位 key），同一次同步同一個備援 key 只警告一次避免洗版；此為純備援層，若原設定的常數本來就正確，此邏輯完全不會被觸發、不影響既有行為
- **驗證**：`py_compile` 通過；`diff` 確認兩檔案變更僅限於新增的計數器初始化、備援偵測區塊、以及最終 log／回傳結果新增 `images_fallback_used` 三處，其餘程式碼逐行相同；檔尾比對無截斷
- **後續**：若下次同步後 Drawer 仍未顯示附圖，後端 log 中的 `images_fallback_used` 計數與（如有觸發）警告訊息會直接標出真正命中的欄位 key，屆時可據此把 `CK28L_IMAGES`／`CK24L_IMAGES` 常數改為正確值並補上「實測驗證」註記；若備援也未命中任何欄位，則需另外確認該筆記錄在 Ragic 端是否真的有成功上傳圖片、或圖片欄位是否屬於子表格內另一層結構

## [1.80.39] - 2026-07-14'''

changelog = changelog.replace(OLD_CL_ANCHOR, NEW_CL_ENTRY, 1)

with open(CHANGELOG_DST, "w", encoding="utf-8") as f:
    f.write(changelog)
print("CHANGELOG OK", len(changelog))
