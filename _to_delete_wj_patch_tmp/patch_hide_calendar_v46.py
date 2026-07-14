import hashlib, sys

def load_verify(path, expected_sha):
    data = open(path, "r", encoding="utf-8").read()
    actual = hashlib.sha256(data.encode("utf-8")).hexdigest()
    if actual != expected_sha:
        print(f"SHA MISMATCH for {path}: actual={actual}")
        sys.exit(1)
    return data

FLAG_COMMENT = (
    "\n// 2026-07-14 使用者要求先隱藏 Dashboard 月曆區塊（保留程式碼與功能，只是先不顯示，\n"
    "// 之後如需重新開啟只要把這個常數改回 true 即可，不要刪除下方程式碼）。\n"
    "const SHOW_MONTHLY_CALENDAR = false\n"
)

# ── 1) mall_periodic_maintenance/index.tsx ──────────────────────────────────
MALL_PATH = "frontend/src/pages/MallPeriodicMaintenance/index.tsx"
mall = load_verify(MALL_PATH, "63291f2fdd1786e3ee8298ed5f267b1abe336321665cf8ea761cbad0582a1145")

OLD_MALL_ANCHOR = "export default function MallPeriodicMaintenancePage() {"
assert mall.count(OLD_MALL_ANCHOR) == 1, f"mall anchor count={mall.count(OLD_MALL_ANCHOR)}"
mall = mall.replace(OLD_MALL_ANCHOR, FLAG_COMMENT + "\n" + OLD_MALL_ANCHOR, 1)

OLD_MALL_CARD = '''      <Card
        size="small"
        style={{ marginTop: 16 }}
        title={
          <Space>
            <CalendarOutlined style={{ color: '#4BA8E8' }} />
            <Text strong style={{ color: '#1B3A5C' }}>
              {dashYear}/{String(dashMonth).padStart(2, '0')} 商場例行維護狀況
            </Text>
          </Space>
        }
        loading={loading}
      >
        {calRows.length > 0 ? (
          <MonthlyCalendarGrid
            year={parseInt(dashYear)}
            month={dashMonth}
            maxDay={calMaxDay}
            rows={calRows}
            rowHeaderLabel="保養類別"
            onCellClick={(day, rowKey) => openCalendarCellDrawer(day, rowKey)}
          />
        ) : (
          <Text type="secondary">尚無資料</Text>
        )}
      </Card>'''
assert mall.count(OLD_MALL_CARD) == 1, f"mall card anchor count={mall.count(OLD_MALL_CARD)}"

NEW_MALL_CARD = "      {SHOW_MONTHLY_CALENDAR && (\n" + OLD_MALL_CARD + "\n      )}"
mall = mall.replace(OLD_MALL_CARD, NEW_MALL_CARD, 1)

open(MALL_PATH.replace(".tsx", "_tmp_v46.tsx"), "w", encoding="utf-8").write(mall)
print("mall_pm OK", len(mall))


# ── 2) full_building_maintenance/index.tsx ──────────────────────────────────
FB_PATH = "frontend/src/pages/FullBuildingMaintenance/index.tsx"
fb = load_verify(FB_PATH, "d04b2168dc98b6cb2be05c7ebe898da4a0b02ca4b8f660ecfc7fda862ff7d5bb")

OLD_FB_ANCHOR = "export default function FullBuildingMaintenancePage() {"
assert fb.count(OLD_FB_ANCHOR) == 1, f"fb anchor count={fb.count(OLD_FB_ANCHOR)}"
fb = fb.replace(OLD_FB_ANCHOR, FLAG_COMMENT + "\n" + OLD_FB_ANCHOR, 1)

OLD_FB_CARD = '''      {/* 月曆格：類別 × 日期 */}
      <Card
        size="small"
        style={{ marginTop: 16 }}
        title={
          <Space>
            <CalendarOutlined />
            <Text strong>全棟例行維護排程狀況</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              （{dashYear}/{String(dashMonth).padStart(2, '0')}）
            </Text>
          </Space>
        }
        loading={loading}
      >
        {calRows.length > 0 ? (
          <MonthlyCalendarGrid
            year={parseInt(dashYear)}
            month={dashMonth}
            maxDay={calMaxDay}
            rows={calRows}
            rowHeaderLabel="保養類別"
          />
        ) : (
          <Text type="secondary">尚無月曆資料</Text>
        )}
      </Card>'''
assert fb.count(OLD_FB_CARD) == 1, f"fb card anchor count={fb.count(OLD_FB_CARD)}"

NEW_FB_CARD = "      {SHOW_MONTHLY_CALENDAR && (\n" + OLD_FB_CARD + "\n      )}"
fb = fb.replace(OLD_FB_CARD, NEW_FB_CARD, 1)

open(FB_PATH.replace(".tsx", "_tmp_v46.tsx"), "w", encoding="utf-8").write(fb)
print("full_bldg_pm OK", len(fb))
