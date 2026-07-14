import hashlib, sys

def load_verify(path, expected_sha):
    data = open(path, "r", encoding="utf-8").read()
    actual = hashlib.sha256(data.encode("utf-8")).hexdigest()
    if actual != expected_sha:
        print(f"SHA MISMATCH for {path}: actual={actual}")
        sys.exit(1)
    return data


# ── 1) backend/app/routers/mall_periodic_maintenance.py: 新增 GET /calendar ────

BACKEND_PATH = "backend/app/routers/mall_periodic_maintenance.py"
backend = load_verify(BACKEND_PATH, "e688583e43b8c6a3559e3f0ff50dc03cafcf24fc82cd0c3398a20b276e5066e0")

OLD_B = '''        category_stats      = cats,
        status_distribution = status_dist,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /items/task-history
# ══════════════════════════════════════════════════════════════════════════════'''
assert backend.count(OLD_B) == 1, f"backend anchor count={backend.count(OLD_B)}"

NEW_B = '''        category_stats      = cats,
        status_distribution = status_dist,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /calendar  — 月曆格（類別 × 日期）
# 2026-07-14 新增：Dashboard 原本沿用 mall_facility_inspection（商場工務巡檢，完全
# 不同模組）的每日巡檢月曆（fetchMallFIDailyCalendar）當佔位資料，標題「...每日巡檢
# 狀況」其實正確描述了那份資料本身，只是那份資料根本不屬於本模組（商場週期保養）。
# 比照 full_building_maintenance.py::get_calendar()（同一批 2026-07-13 Sheet 改版
# 模組，資料結構相同）補上本模組專屬版本，改為呈現週期保養項目的類別 × 日完成狀況。
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/calendar", summary="商場週期保養月曆格（類別 × 日）")
def get_mall_pm_calendar(
    year:  int = Query(..., description="年份，如 2026"),
    month: int = Query(..., ge=1, le=12, description="月份，如 5"),
    db:    Session = Depends(get_db),
):
    """
    回傳指定年月的類別 × 日期月曆格資料。
    cell key = str(d)（非零填充，配合 MonthlyCalendarGrid）。
    """
    import calendar as cal_mod
    max_day   = cal_mod.monthrange(year, month)[1]
    target_ym = f"{year}/{month:02d}"

    batch = db.query(MallPeriodicMaintenanceBatch).filter(
        MallPeriodicMaintenanceBatch.period_month == target_ym
    ).first()

    # 已知類別順序（比照全棟例行維護；若商場實際類別不同，未知類別仍會依下方邏輯附加在後）
    CATEGORY_ORDER = ["水電", "空調", "照明", "消防", "申報", "整體"]

    def _empty_daily() -> dict:
        return {
            str(d): {"has_record": False, "completion_rate": 0, "abnormal_count": 0, "pending_count": 0}
            for d in range(1, max_day + 1)
        }

    if not batch:
        return {
            "year": year, "month": month, "max_day": max_day,
            "rows": [{"key": c, "label": c, "daily": _empty_daily()} for c in CATEGORY_ORDER],
        }

    items = db.query(MallPeriodicMaintenanceItem).filter(
        MallPeriodicMaintenanceItem.batch_ragic_id == batch.ragic_id
    ).all()

    # 依類別 × 日分組（用 scheduled_date 的 MM/DD 推算日期）
    from collections import defaultdict
    cat_day: dict[str, dict[int, list]] = defaultdict(lambda: defaultdict(list))
    for it in items:
        fd = _reconstruct_full_date(it.scheduled_date, batch.period_month)
        if fd is None or fd.year != year or fd.month != month:
            continue
        cat_day[it.category or "其他"][fd.day].append(it)

    # 確保所有已知類別都出現；額外類別附加在後
    all_cats = list(CATEGORY_ORDER)
    for c in cat_day:
        if c not in all_cats:
            all_cats.append(c)

    rows_out = []
    for cat in all_cats:
        daily: dict[str, dict] = {}
        for d in range(1, max_day + 1):
            day_items = cat_day[cat].get(d, [])
            if not day_items:
                daily[str(d)] = {"has_record": False, "completion_rate": 0, "abnormal_count": 0, "pending_count": 0}
            else:
                total     = len(day_items)
                completed = sum(1 for it in day_items if it.start_time and it.end_time)
                abnormal  = sum(1 for it in day_items if it.abnormal_flag)
                pending   = total - completed
                rate      = round(completed / total * 100, 1) if total > 0 else 0.0
                daily[str(d)] = {
                    "has_record":      True,
                    "completion_rate": rate,
                    "abnormal_count":  abnormal,
                    "pending_count":   pending,
                }
        rows_out.append({"key": cat, "label": cat, "daily": daily})

    return {"year": year, "month": month, "max_day": max_day, "rows": rows_out}


# ══════════════════════════════════════════════════════════════════════════════
# GET /items/task-history
# ══════════════════════════════════════════════════════════════════════════════'''

backend = backend.replace(OLD_B, NEW_B, 1)
open(BACKEND_PATH.replace(".py", "_tmp_v41.py"), "w", encoding="utf-8").write(backend)
print("backend OK", len(backend))


# ── 2) frontend/src/api/mallPeriodicMaintenance.ts: 新增 fetchMallPMCalendar ──

API_PATH = "frontend/src/api/mallPeriodicMaintenance.ts"
api_ts = load_verify(API_PATH, "419f4af59e58ef6af2509a20d474f5825532ea392c81b625f48eb9359748405b")

OLD_A = '''/** 手動觸發 Ragic 同步 */
export async function syncMallPMFromRagic(): Promise<{ status: string; result: unknown }> {'''
assert api_ts.count(OLD_A) == 1, f"api.ts anchor count={api_ts.count(OLD_A)}"

NEW_A = '''/** 月曆格（類別 × 日期），Dashboard 用。2026-07-14 新增：修正 Dashboard 原本誤用
 *  mall_facility_inspection（商場工務巡檢）每日巡檢月曆頂替顯示的問題，改回真正屬於
 *  本模組（商場週期保養）的類別 × 日完成狀況。 */
export async function fetchMallPMCalendar(
  year: number,
  month: number,
): Promise<{ year: number; month: number; max_day: number; rows: import('@/components/MonthlyCalendarGrid').CalendarRow[] }> {
  const res = await apiClient.get(`${BASE}/calendar`, { params: { year, month } })
  return res.data
}

/** 手動觸發 Ragic 同步 */
export async function syncMallPMFromRagic(): Promise<{ status: string; result: unknown }> {'''

api_ts = api_ts.replace(OLD_A, NEW_A, 1)
open(API_PATH.replace(".ts", "_tmp_v41.ts"), "w", encoding="utf-8").write(api_ts)
print("api.ts OK", len(api_ts))


# ── 3) frontend/src/pages/MallPeriodicMaintenance/index.tsx ───────────────────

PAGE_PATH = "frontend/src/pages/MallPeriodicMaintenance/index.tsx"
page = load_verify(PAGE_PATH, "ff91e10975458864105d5f8c5cb488003b266dc9247186a678279f007c4a2e75")

# 3a) import：移除 fetchMallFIDailyCalendar，改用本模組自己的 fetchMallPMCalendar
OLD_P_IMPORT = "import { fetchMallFIDailyCalendar } from '@/api/mallFacilityInspection'\n"
assert page.count(OLD_P_IMPORT) == 1, f"page import anchor count={page.count(OLD_P_IMPORT)}"
page = page.replace(OLD_P_IMPORT, "", 1)

# 找到既有的 mallPeriodicMaintenance import 區塊，附加 fetchMallPMCalendar（用 fetchMallPMStats 那行當錨點附加到同一批 import 內較整潔；
# 但為求 patch 穩定，改用「在 fetchMallPMStats 的 import 陳述式所在那一整行」後面補一行 import）
import re
m = re.search(r"^import \{[^}]*fetchMallPMStats[^}]*\} from '@/api/mallPeriodicMaintenance'\n", page, re.MULTILINE)
assert m, "could not find fetchMallPMStats import line in page"
old_import_line = m.group(0)
assert "fetchMallPMCalendar" not in old_import_line
new_import_line = old_import_line.rstrip("\n") + "\nimport { fetchMallPMCalendar } from '@/api/mallPeriodicMaintenance'\n"
assert page.count(old_import_line) == 1, f"page import line count={page.count(old_import_line)}"
page = page.replace(old_import_line, new_import_line, 1)

# 3b) loadDashboard：改抓本模組月曆資料
OLD_P_LOAD = '''      const [s, calData] = await Promise.all([
        fetchMallPMStats(dashYear, dashMonth),
        fetchMallFIDailyCalendar(y, m).catch(() => null),
      ])
      setStats(s)
      if (calData) {
        setCalMaxDay(calData.max_day)
        setCalRows(calData.sheets.map((sh) => ({
          key:   sh.key,
          label: sh.floor,
          daily: sh.daily,
        })))
      }'''
assert page.count(OLD_P_LOAD) == 1, f"page loadDashboard anchor count={page.count(OLD_P_LOAD)}"

NEW_P_LOAD = '''      const [s, calData] = await Promise.all([
        fetchMallPMStats(dashYear, dashMonth),
        fetchMallPMCalendar(y, m).catch(() => null),
      ])
      setStats(s)
      if (calData) {
        setCalMaxDay(calData.max_day)
        setCalRows(calData.rows)
      }'''

page = page.replace(OLD_P_LOAD, NEW_P_LOAD, 1)

# 3c) 標題文字 + rowHeaderLabel
OLD_P_TITLE = '''              {dashYear}/{String(dashMonth).padStart(2, '0')} 商場工務每日巡檢狀況'''
assert page.count(OLD_P_TITLE) == 1, f"page title anchor count={page.count(OLD_P_TITLE)}"
NEW_P_TITLE = '''              {dashYear}/{String(dashMonth).padStart(2, '0')} 商場例行維護狀況'''
page = page.replace(OLD_P_TITLE, NEW_P_TITLE, 1)

OLD_P_ROWLABEL = '''            rowHeaderLabel="巡檢區域"'''
assert page.count(OLD_P_ROWLABEL) == 1, f"page rowHeaderLabel anchor count={page.count(OLD_P_ROWLABEL)}"
NEW_P_ROWLABEL = '''            rowHeaderLabel="保養類別"'''
page = page.replace(OLD_P_ROWLABEL, NEW_P_ROWLABEL, 1)

open(PAGE_PATH.replace(".tsx", "_tmp_v41.tsx"), "w", encoding="utf-8").write(page)
print("page.tsx OK", len(page))
