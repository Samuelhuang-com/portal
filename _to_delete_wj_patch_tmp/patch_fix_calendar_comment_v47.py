import hashlib, sys

def load_verify(path, expected_sha):
    data = open(path, "r", encoding="utf-8").read()
    actual = hashlib.sha256(data.encode("utf-8")).hexdigest()
    if actual != expected_sha:
        print(f"SHA MISMATCH for {path}: actual={actual}")
        sys.exit(1)
    return data

# ── full_building_maintenance/index.tsx: 修正 v46 造成的 JSX 語法錯誤 ──────────
# 問題：{SHOW_MONTHLY_CALENDAR && ( ... )} 的括號內第一行是 {/* 月曆格：類別 × 日期 */}
# 這個 JSX 註解語法只能當「JSX 子項」使用，不能出現在一個 JS 運算式的括號內（(...)
# 內只能有一個運算式），造成 Vite/Babel 解析失敗（Unexpected token, expected ","）。
# 修法：把註解移到 {SHOW_MONTHLY_CALENDAR && ( 外面，變成獨立的 JSX 子項。
FB_PATH = "frontend/src/pages/FullBuildingMaintenance/index.tsx"
fb = load_verify(FB_PATH, "444c3447457b5cb80ba3ce54723995a649501ce296fa9de6e403d939658af217")

OLD = '''      {SHOW_MONTHLY_CALENDAR && (
      {/* 月曆格：類別 × 日期 */}
      <Card'''
assert fb.count(OLD) == 1, f"anchor count={fb.count(OLD)}"

NEW = '''      {/* 月曆格：類別 × 日期 */}
      {SHOW_MONTHLY_CALENDAR && (
      <Card'''
fb = fb.replace(OLD, NEW, 1)

open(FB_PATH.replace(".tsx", "_tmp_v47.tsx"), "w", encoding="utf-8").write(fb)
print("full_bldg_pm OK", len(fb))
