import hashlib, sys

def load_verify(path, expected_sha):
    data = open(path, "r", encoding="utf-8").read()
    actual = hashlib.sha256(data.encode("utf-8")).hexdigest()
    if actual != expected_sha:
        print(f"SHA MISMATCH for {path}: actual={actual}")
        sys.exit(1)
    return data

COMMENT = '''    # 2026-07-14 修正（比照 mall_periodic_maintenance.py 同日修正）：abnormal 原本算
    # 「整批全部項目」，跟 overdue/scheduled/unscheduled/in_progress 這幾個都只算
    # 「本月項目」（current_items）的口徑不一致，改為比照這幾個欄位只算本月項目。
'''

# ── 1) full_building_maintenance.py ───────────────────────────────────────────
FB_PATH = "backend/app/routers/full_building_maintenance.py"
fb = load_verify(FB_PATH, "4e4478269b885cd56e8ce7abdde399b945f6a0b3f181e9e00b62a4fef3dfad17")

OLD_FB = '''    overdue     = sum(1 for _, s in current_items if s == "overdue")
    abnormal    = sum(1 for it in items if it.abnormal_flag)
    planned     = sum(it.estimated_minutes for it, s in current_items)'''
assert fb.count(OLD_FB) == 1, f"full_bldg_pm anchor count={fb.count(OLD_FB)}"
NEW_FB = (
    '    overdue     = sum(1 for _, s in current_items if s == "overdue")\n'
    + COMMENT
    + '    abnormal    = sum(1 for it, _ in current_items if it.abnormal_flag)\n'
    + '    planned     = sum(it.estimated_minutes for it, s in current_items)'
)
fb = fb.replace(OLD_FB, NEW_FB, 1)
open(FB_PATH.replace(".py", "_tmp_v45.py"), "w", encoding="utf-8").write(fb)
print("full_building_maintenance.py OK", len(fb))


# ── 2) periodic_maintenance.py（飯店週期保養）────────────────────────────────
PM_PATH = "backend/app/routers/periodic_maintenance.py"
pm = load_verify(PM_PATH, "01ecafe61725a4322c427b69727bb680161062b4ad87b0a310bdbb146b4eca91")

OLD_PM = '''    overdue     = sum(1 for _, s in current_items if s == "overdue")
    abnormal    = sum(1 for it in items if it.abnormal_flag)
    planned     = sum(it.estimated_minutes for it, s in current_items)'''
assert pm.count(OLD_PM) == 1, f"periodic_maintenance anchor count={pm.count(OLD_PM)}"
NEW_PM = (
    '    overdue     = sum(1 for _, s in current_items if s == "overdue")\n'
    + COMMENT
    + '    abnormal    = sum(1 for it, _ in current_items if it.abnormal_flag)\n'
    + '    planned     = sum(it.estimated_minutes for it, s in current_items)'
)
pm = pm.replace(OLD_PM, NEW_PM, 1)
open(PM_PATH.replace(".py", "_tmp_v45.py"), "w", encoding="utf-8").write(pm)
print("periodic_maintenance.py OK", len(pm))


# ── 3) frontend/src/pages/FullBuildingMaintenance/index.tsx：Drawer abnormal 篩選同步收斂 ──
FE_PATH = "frontend/src/pages/FullBuildingMaintenance/index.tsx"
fe = load_verify(FE_PATH, "7bddc9300265e10f07039b5418b2987f4bcc2529eb4871803bbee86a800635ff")

OLD_FE = '''        case 'abnormal':
          filtered = detail.items.filter((it) => it.abnormal_flag)
          break'''
assert fe.count(OLD_FE) == 1, f"full_bldg_pm frontend anchor count={fe.count(OLD_FE)}"
NEW_FE = '''        case 'abnormal':
          // 2026-07-14 修正：比照 KPI 卡片數字口徑（已改為只算本月項目）同步收斂篩選條件，
          // 避免點進來的清單筆數跟卡片數字對不起來
          filtered = detail.items.filter((it) => it.abnormal_flag && it.status !== 'non_current_month')
          break'''
fe = fe.replace(OLD_FE, NEW_FE, 1)
open(FE_PATH.replace(".tsx", "_tmp_v45.tsx"), "w", encoding="utf-8").write(fe)
print("FullBuildingMaintenance/index.tsx OK", len(fe))
