# KPI 資料來源對照表 — 決策駕駛艙

> 每個 KPI 均需可回答：來源模組、API、Portal Table、欄位、計算邏輯、月份判斷、狀態邏輯

---

## TAB A — 決策總覽

| 指標名稱 | 來源模組 | Portal API | Portal Table / Service | 使用欄位 | 計算邏輯 | 月份欄位 | 狀態邏輯 | 可點擊明細 |
|---------|---------|-----------|----------------------|---------|---------|---------|---------|-----------|
| 集團整體健康分數 | 所有模組 | 多 API 前端計算 | 多表 | completion_rate, overdue_count, abnormal_count | 四維加權（見 HEALTH_SCORE_SPEC.md） | 查詢月份 | ≥80綠/≥60黃/<60紅 | ❌ |
| 飯店管理健康分數 | hotel/overview | 六來源 API | 六表 | 同上 | 同上（飯店六來源） | year+month | 同上 | ✅ → /hotel/overview |
| 商場管理健康分數 | mall/overview | 五工項 API | 五表 | 同上 | 同上（商場五工項） | year+month | 同上 | ✅ → /mall/overview |
| 工務維護健康分數 | dazhi + luqun | `/dazhi-repair/dashboard`、`/luqun-repair/dashboard` | dazhi_repair_case, luqun_repair_cases | completion_rate, overdue, abnormal | 兩來源均權加總 | occ_year/occ_month | 同上 | ✅ → /dazhi-repair/dashboard |
| 本月總案件數 | 所有模組 | 多 API | 多表 | case_count（各 API 欄位） | 各來源 case_count 加總 | 查詢月份 | — | ❌ |
| 本月完成件數 | 所有模組 | 多 API | 多表 | completed_count | 各來源 completed_count 加總 | 查詢月份 | — | ❌ |
| 本月未完成件數 | 所有模組 | 多 API | 多表 | total - completed | 加總差值 | 查詢月份 | >0 橘色 | ❌ |
| 本月待驗件數 | 飯店PM + 商場PM | `/periodic-maintenance/stats`、`/mall-periodic-maintenance/stats` | pm_batch_item, mall_pm_batch_item | overdue_count / pending_count | 彙總逾期未完成 | period_month | >0 橘色 | ✅ → /hotel/periodic-maintenance |
| 本月總工時(HR) | 飯店 + 商場 | `/hotel/monthly-hours`、`/mall/monthly-hours` | 六表 + 五表 | TOTAL row 對應月份 hours | 飯店月工時 + 商場月工時 | year+month | — | ❌ |
| 高風險待處理數 | dashboard/graph | `/dashboard/graph` | 多表（即時） | nodes[*].alert（≥5） | 計算 alert≥5 節點數 | 即時（無月份） | >0 紅色 | ✅ → /dashboard |
| 主管最該注意的 5 件事 | 規則式前端 | 多 API | — | 各 KPI 欄位 | 優先順序規則（見 riskDetector.ts） | 查詢月份 | — | ✅ 各自跳轉 |

---

## TAB B — 飯店管理摘要

| 指標名稱 | 來源模組 | Portal API | Portal Table | 使用欄位 | 計算邏輯 | 月份欄位 | 備註 |
|---------|---------|-----------|-------------|---------|---------|---------|------|
| 客房保養管理 KPI | room_maintenance_detail | `/room-maintenance-detail/maintenance-stats?year=&month=` | room_maintenance_detail_records | case_count, completed, work_hours | 直接 | maintain_date | |
| 飯店週期保養 KPI | pm_batch_item | `/periodic-maintenance/stats?year=&month=` | pm_batch, pm_batch_item | total, completed, overdue, abnormal, actual_minutes | 直接 | period_month | |
| IHG 客房保養 KPI | ihg_rm_master | `/ihg-room-maintenance/stats?year=&month=` | ihg_rm_master | case_count, completed, work_hours | 每筆固定 0.5hr | maint_date | |
| 飯店每日巡檢 KPI | hotel_di_batch | `/hotel-daily-inspection/dashboard/summary` | hotel_di_inspection_batch | batch_count, completion_rate | 直接 | inspection_date | 暫無月份參數 |
| 保全巡檢 KPI | security_patrol | `/security/dashboard/summary` | security_patrol_batch | batch_count, abnormal_count | 直接 | inspection_date | 暫無月份參數 |
| 大直工務部 KPI | dazhi_repair | `/dazhi-repair/dashboard?year=&month=` | dazhi_repair_case | total, completed, overdue, work_hours | 直接 | occ_year/occ_month | |
| 飯店月工時彙整 | 六來源 | `/hotel/monthly-hours?year=` | 六表 | TOTAL row 對應月份 | 取對應月份欄位 | year+month | |
| 飯店人員工時 Top 5 | 六來源 | `/hotel/person-hours?year=` | 六表 | persons[0..4], person_totals | 取前 5 名 | **年度口徑**（無月份） | ⚠️ 限制 |

---

## TAB C — 商場管理摘要

| 指標名稱 | 來源模組 | Portal API | Portal Table | 使用欄位 | 計算邏輯 | 月份欄位 | 備註 |
|---------|---------|-----------|-------------|---------|---------|---------|------|
| 商場例行維護 KPI | mall_pm | `/mall-periodic-maintenance/stats?year=&month=` | mall_pm_batch, mall_pm_batch_item | total, completed, overdue, actual_hours | 直接 | period_month | |
| 全棟例行維護 KPI | full_bldg_pm | `/full-building-maintenance/stats?year=&month=` | full_bldg_pm_batch, full_bldg_pm_item | total, completed, overdue, actual_hours | 直接 | period_month | |
| 商場每日巡檢 KPI | mall_fi | `/mall-facility-inspection/dashboard/summary` | mall_fi_inspection_batch | batch_count, inspection_rate | 直接 | inspection_date | |
| 商場現場報修 KPI | luqun_repair | `/luqun-repair/dashboard?year=&month=` | luqun_repair_cases | total, completed, overdue, work_hours | 直接 | occ_year/occ_month | |
| 商場上級交辦 | 尚未建立 | — | — | — | — | — | ⚠️ 資料準備中 |
| 商場緊急事件 | 尚未建立 | — | — | — | — | — | ⚠️ 資料準備中 |
| 商場月工時彙整 | 五工項 | `/mall/monthly-hours?year=` | 五表 | TOTAL row 對應月份 | 取對應月份 | year+month | |
| 商場人員工時 Top 5 | 三來源 | `/mall/person-hours?year=` | 三表 | persons[0..4] | 取前 5 名 | **年度口徑**（無月份） | ⚠️ 限制 |

---

## TAB D — 工務與報修摘要

| 指標名稱 | 來源 | API | 欄位 | 計算邏輯 |
|---------|------|-----|------|---------|
| 本月報修總件數（大直） | dazhi_repair | `/dazhi-repair/dashboard` | this_month_new | 直接 |
| 本月報修總件數（樂群） | luqun_repair | `/luqun-repair/dashboard` | this_month_new | 直接 |
| 本月完成件數 | 兩來源 | 同上 | this_month_completed | 加總 |
| 本月未完成件數 | 兩來源 | 同上 | total - completed | 差值 |
| 本月待驗件數 | 兩來源 | 同上 | overdue_count | 加總 |
| 平均結案天數 | 兩來源 | 同上 | avg_close_days | 加權平均 |
| 本月工時（大直） | dazhi_repair | 同上 | total_work_hours | 直接 |
| 本月工時（樂群） | luqun_repair | 同上 | total_work_hours | 直接 |
| 報修費用摘要 | 大直 | `/dazhi-repair/dashboard` | outsource_fee, maintenance_fee, deduction_fee | 直接 |

---

## TAB E — 人員工時與效率

| 指標名稱 | 來源 | API | 欄位 | 說明 |
|---------|------|-----|------|------|
| 飯店人員工時排行（Top 15） | 飯店六來源 | `/hotel/person-hours?year=` | persons[], person_totals[] | 年度口徑 |
| 商場人員工時排行（Top 15） | 商場三來源 | `/mall/person-hours?year=` | persons[], person_totals[] | 年度口徑 |
| 飯店 vs 商場人員工時比較 | 兩側 | 兩 API | 同上 | 加 tag「飯店/商場」區分 |

> ⚠️ **限制說明：** 人員工時 API 目前均為年度口徑（無月份過濾）。UI 顯示「※ 人員工時為全年統計」說明。

---

## TAB F — 異常與風險雷達

| 燈號 | 判斷邏輯 | 資料來源 | API |
|------|---------|---------|-----|
| 🔴 紅燈 | alert ≥ 5 或 closure_rate < 50% | dashboard/graph nodes | `/dashboard/graph` |
| 🟡 黃燈 | 1 ≤ alert < 5 或 50% ≤ closure_rate < 80% | 同上 | 同上 |
| 🟢 綠燈 | alert = 0 且 closure_rate ≥ 80% | 同上 | 同上 |
| ⚫ 灰燈 | 模組未建立 / 資料準備中 | 上級交辦、緊急事件 | — |

---

## TAB G — 趨勢分析

| 圖表 | 資料來源 | API | 欄位 |
|------|---------|-----|------|
| 近 7/14/30 日折線 | 商場巡檢/保全/客房 | `/dashboard/trend?days=N` | mall_completion, security_completion, hotel_completion |
| 月度工時趨勢（飯店） | 飯店六來源 | `/hotel/monthly-hours?year=` | TOTAL row hours[1..12] |
| 月度工時趨勢（商場） | 商場五工項 | `/mall/monthly-hours?year=` | TOTAL row hours[1..12] |
| 飯店 vs 商場月度對比 | 兩側 | 兩 API | TOTAL row 逐月比較 |

---

## TAB H — 主管晨會摘要

規則式文字模板，不使用 AI API。

**模板欄位：**
```
{year} 年 {month} 月  |  集團累計案件 {total_cases} 件  |  完成率 {completion_rate}%
飯店管理：工時 {hotel_hours} HR，主要工作：{top_hotel_category}
商場管理：工時 {mall_hours} HR，主要工作：{top_mall_category}
主要風險：{risk_items（紅燈清單）}
建議追蹤：{priority_actions}
```

---

## TAB I — 資料品質監控

| 檢查項目 | 計算方式 | 影響 KPI |
|---------|---------|---------|
| 缺負責人 | count(empty executor_name or acceptor) | 人員工時排行不準確 |
| 缺工時 | count(work_hours = 0 or null) | 工時加總低估 |
| 缺日期 | count(empty maintain_date or inspection_date) | 月份歸屬無法判斷 |
| 缺狀態 | count(empty work_item or is_completed null) | 完成率計算不準 |
| 月份欄位格式異常 | count(period_month format error) | 所有月份 KPI |
| 上級交辦/緊急事件 | 模組未開發 | 商場摘要不完整（灰燈） |

資料品質分數 = (完整記錄數 / 總記錄數) × 100，依各模組分別計算。
