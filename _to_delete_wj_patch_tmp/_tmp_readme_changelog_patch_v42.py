import hashlib, sys

README_SRC = "README.md"
README_DST = "_tmp_readme_v42.md"
CHANGELOG_SRC = "docs/CHANGELOG.md"
CHANGELOG_DST = "_tmp_changelog_v42.md"

readme = open(README_SRC, "r", encoding="utf-8").read()

OLD_HEADER = "**最後更新：2026-07-14（v1.80.41）**"
NEW_HEADER = "**最後更新：2026-07-14（v1.80.42）**"
assert readme.count(OLD_HEADER) == 1, f"header count={readme.count(OLD_HEADER)}"
readme = readme.replace(OLD_HEADER, NEW_HEADER, 1)

OLD_ANCHOR = "### v1.80.41 - 2026-07-14"
assert readme.count(OLD_ANCHOR) == 1, f"anchor count={readme.count(OLD_ANCHOR)}"

NEW_ENTRY = '''### v1.80.42 - 2026-07-14
- **後端啟動時因 SQLite「database is locked」整台當機**：使用者回報照建議手動跑 `sync_tool.py` 觸發同步時，後端剛好重啟，`_migrate_pm_batch_item()` 啟動 migration 的回填 UPDATE 因資料庫被 sync_tool.py 的長交易鎖住超過既有 60 秒 busy_timeout，直接拋出 `OperationalError`，導致 `Application startup failed. Exiting.`，整個後端無法啟動；根本問題是 `main.py` 裡全部 19 個啟動時 migration 都是直接呼叫、沒有任何重試機制，任一個遇到暫時性鎖定就會讓整台服務起不來。修復：新增 `_run_startup_migration()` 包裝函式，所有啟動 migration 一律透過它呼叫，遇到「database is locked」會等 3 秒後重試（最多 5 次），仍失敗則記錄警告後略過該項（這些 migration 本身都是「檢查欄位/資料是否需要補、需要才動作」的自我修復型 patch，下次啟動會再檢查一次，略過一次不會遺漏）；非鎖定類的例外仍照原樣拋出，不吃掉真正的錯誤

### v1.80.41 - 2026-07-14'''

readme = readme.replace(OLD_ANCHOR, NEW_ENTRY, 1)

with open(README_DST, "w", encoding="utf-8") as f:
    f.write(readme)
print("README OK", len(readme))

changelog = open(CHANGELOG_SRC, "r", encoding="utf-8").read()

OLD_CL_ANCHOR = "## [1.80.41] - 2026-07-14"
assert changelog.count(OLD_CL_ANCHOR) == 1, f"cl anchor count={changelog.count(OLD_CL_ANCHOR)}"

NEW_CL_ENTRY = '''## [1.80.42] - 2026-07-14

### Fixed — 啟動時 migration 遇 SQLite 鎖定會讓整台後端啟動失敗

- **背景**：使用者依前一輪建議手動執行 `sync_tool.py` 觸發 full_bldg_pm／mall_pm 同步以驗證附圖修復，過程中後端剛好重啟，啟動 log 出現：
  ```
  sqlite3.OperationalError: database is locked
  [SQL: UPDATE pm_batch_item SET is_completed = 1 WHERE start_time != '' AND end_time != '' AND is_completed = 0]
  ...
  ERROR:    Application startup failed. Exiting.
  ```
  整個後端服務直接無法啟動
- **排查**：錯誤發生在 `_migrate_pm_batch_item()`（飯店週期保養 `pm_batch_item` 表的欄位補丁＋資料回填，與這次 mall_pm/full_bldg_pm 附圖修復無關的既有 migration）。`app/core/database.py` 已設定 SQLite WAL 模式＋60 秒 `busy_timeout`，理論上應能撐過大部分暫時性鎖定；但 `sync_tool.py` 觸發的 full_bldg_pm／mall_pm 同步，每個項目都要對 Ragic 呼叫一次 `fetch_one()`（HTTP 往返），且整批同步（50+ 筆項目）在同一個交易內、直到迴圈跑完才 `db.commit()`——這種寫入交易持續的時間很容易超過 60 秒，導致同一時間想寫入的後端啟動 migration 等到逾時。根本問題不是這次鎖定本身（那只是正常的併發現象），而是 `main.py` 裡全部 19 個啟動時 migration 都是直接呼叫、沒有任何重試或容錯機制：任何一個因為暫時性鎖定丟出例外，就會讓 `lifespan()` 整個啟動流程失敗、拖垮整台服務，即使其餘 18 個 migration 完全沒問題
- **修復**：新增 `_run_startup_migration(name, fn)` 包裝函式：捕捉 `sqlalchemy.exc.OperationalError`，訊息含「locked」時等待 3 秒後重試，最多重試 5 次；非鎖定類例外原樣往外拋出，不會誤吞真正的程式錯誤；`lifespan()` 內全部 19 個 `_migrate_*()` 呼叫點統一改為 `_run_startup_migration("_migrate_*", _migrate_*)`。重試多次仍失敗時只記錄警告訊息並略過該項 migration，不會讓應用程式啟動失敗——這些 migration 本身都是「先檢查欄位/資料是否已符合預期，需要才動作」的自我修復型 patch，略過一次不影響資料正確性，下次啟動會再檢查一次
- **驗證**：`py_compile` 通過；`diff` 確認變更僅為新增 `_run_startup_migration()` 定義＋19 個呼叫點逐一改寫，其餘程式碼逐行相同；檔尾比對無截斷；`grep -c '_run_startup_migration('` 確認新函式定義 1 次＋呼叫點 19 次共 20 次出現，數量與既有 `_migrate_*()` 呼叫點總數一致
- **後續建議**（未在本次一併處理，記錄供評估）：若日後 sync_tool.py 手動同步與後端重啟同時發生的頻率提高，可考慮讓 full_bldg_pm／mall_pm 這類逐項目呼叫 Ragic 的同步改為每處理 N 筆項目就 commit 一次，縮短單一交易持續鎖定資料庫的時間，而不只是讓其他寫入方重試等待

## [1.80.41] - 2026-07-14'''

changelog = changelog.replace(OLD_CL_ANCHOR, NEW_CL_ENTRY, 1)

with open(CHANGELOG_DST, "w", encoding="utf-8") as f:
    f.write(changelog)
print("CHANGELOG OK", len(changelog))
