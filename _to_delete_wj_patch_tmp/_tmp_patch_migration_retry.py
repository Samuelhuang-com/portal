import hashlib, re, sys

PATH = "backend/app/main.py"
data = open(PATH, "r", encoding="utf-8").read()

expected_sha = "4b5f313a2001226c5173207fc41ddb45745836a21dfb6a985890f8e9cab71b63"
actual_sha = hashlib.sha256(data.encode("utf-8")).hexdigest()
if actual_sha != expected_sha:
    print("SHA MISMATCH, aborting. actual=", actual_sha)
    sys.exit(1)

# ── 1) 插入 retry helper（放在第一個 _migrate_* def 之前）─────────────────────
OLD_ANCHOR = "def _migrate_b4f_flatten():\n"
assert data.count(OLD_ANCHOR) == 1, f"anchor count={data.count(OLD_ANCHOR)}"

HELPER = '''def _run_startup_migration(name: str, fn) -> None:
    """
    執行單一啟動時 migration，遇到 SQLite "database is locked" 時重試而非讓整個
    應用程式啟動失敗。

    2026-07-14 新增：使用者回報 sync_tool.py 手動觸發同步進行中時，若同時重啟
    後端，_migrate_pm_batch_item() 的回填 UPDATE 會因 SQLite 寫入鎖定逾時
    （已設定 60s busy_timeout，仍可能因 sync 本身是長交易而超過）直接拋出
    OperationalError，導致 lifespan() 啟動失敗、整台後端無法啟動（見
    "Application startup failed. Exiting."）。單一 migration 的暫時性鎖定
    不應該讓整個服務起不來，因此所有啟動時 migration 一律透過本函式呼叫，
    遇到鎖定就短暫等待後重試；重試多次仍失敗則記錄警告、略過本次啟動的
    這一項 migration（皆為自我修復型 schema/回填 patch，下次啟動仍會再檢查
    一次，並非只有一次機會）。
    """
    import time
    from sqlalchemy.exc import OperationalError

    retries = 5
    delay   = 3.0
    for attempt in range(1, retries + 1):
        try:
            fn()
            return
        except OperationalError as exc:
            if "locked" not in str(exc).lower():
                raise
            if attempt >= retries:
                print(
                    f"[Migration] {name} 因資料庫鎖定重試 {retries} 次仍失敗，"
                    f"略過本次啟動的這項 migration（下次啟動會再檢查一次）：{exc}"
                )
                return
            print(
                f"[Migration] {name} 遇到資料庫鎖定（可能有 sync_tool.py 或排程同步"
                f"正在寫入），{delay}s 後重試（第 {attempt}/{retries} 次）..."
            )
            time.sleep(delay)


def _migrate_b4f_flatten():
'''

data = data.replace(OLD_ANCHOR, HELPER, 1)

# ── 2) 所有啟動呼叫改走 retry wrapper ─────────────────────────────────────────
pattern = re.compile(r"^(\s*)(_migrate_\w+)\(\)\s*$", re.MULTILINE)
matches = pattern.findall(data)
assert len(matches) == 19, f"expected 19 call sites, found {len(matches)}: {matches}"

def _sub(m):
    indent, fn_name = m.group(1), m.group(2)
    return f'{indent}_run_startup_migration("{fn_name}", {fn_name})'

data, n = pattern.subn(_sub, data)
assert n == 19, f"substituted {n} call sites, expected 19"

with open(PATH.replace(".py", "_tmp_v42.py"), "w", encoding="utf-8") as f:
    f.write(data)
print("OK", len(data))
