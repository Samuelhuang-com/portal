import hashlib, sys

def load_verify(path, expected_sha):
    data = open(path, "r", encoding="utf-8").read()
    actual = hashlib.sha256(data.encode("utf-8")).hexdigest()
    if actual != expected_sha:
        print(f"SHA MISMATCH for {path}: actual={actual}")
        sys.exit(1)
    return data

# ── 1) backend/app/routers/mall_periodic_maintenance.py: abnormal 改為只算本月項目 ──
BACKEND_PATH = "backend/app/routers/mall_periodic_maintenance.py"
backend = load_verify(BACKEND_PATH, "898e2457ef800d287568e855c5dec46df2e14036bef44577de2671ab10505f50")

OLD_B = '''    overdue     = sum(1 for _, s in current_items if s == "overdue")
    abnormal    = sum(1 for it in items if it.abnormal_flag)
    planned     = sum(it.estimated_minutes for it, s in current_items)'''
assert backend.count(OLD_B) == 1, f"backend anchor count={backend.count(OLD_B)}"
NEW_B = '''    overdue     = sum(1 for _, s in current_items if s == "overdue")
    # 2026-07-14 修正：abnormal 原本算「整批全部項目」，跟 overdue/scheduled/
    # unscheduled/in_progress 這幾個都只算「本月項目」（current_items）的口徑不一致；
    # 使用者確認後改為比照這幾個欄位，只算本月項目裡標記異常的筆數。
    abnormal    = sum(1 for it, _ in current_items if it.abnormal_flag)
    planned     = sum(it.estimated_minutes for it, s in current_items)'''
backend = backend.replace(OLD_B, NEW_B, 1)

open(BACKEND_PATH.replace(".py", "_tmp_v44.py"), "w", encoding="utf-8").write(backend)
print("backend OK", len(backend))


# ── 2) frontend: Drawer 的 abnormal 篩選也排除非本月項目，維持跟 KPI 卡片一致 ──
PAGE_PATH = "frontend/src/pages/MallPeriodicMaintenance/index.tsx"
page = load_verify(PAGE_PATH, "d0345871de4ac9d6a0bcb89bf98a18787d7848720d7d209aca59387798bcc339")

OLD_P = '''        case 'abnormal':
          filtered = detail.items.filter((it) => it.abnormal_flag)
          break'''
assert page.count(OLD_P) == 1, f"page anchor count={page.count(OLD_P)}"
NEW_P = '''        case 'abnormal':
          // 2026-07-14 修正：比照 KPI 卡片數字口徑改為只算本月項目，避免點進來的清單
          // 筆數跟卡片上的數字對不起來
          filtered = detail.items.filter((it) => it.abnormal_flag && it.status !== 'non_current_month')
          break'''
page = page.replace(OLD_P, NEW_P, 1)

open(PAGE_PATH.replace(".tsx", "_tmp_v44.tsx"), "w", encoding="utf-8").write(page)
print("page OK", len(page))
