# CHANGELOG

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)

## [1.59.2] - 2026-05-12

### Fixed
- **大直報修「維修工時」Ragic 欄位讀取修正** — `work_hours` 原本優先讀「維修天數(天)」×24，但大直 Ragic sheet 實際欄位名稱為「維修工時」（直接以小時為單位），導致 DB 全部寫入 0.0，Dashboard「本月工時統計」永遠顯示 0.00 hr；修正後讀取順序：① 維修工時（直接小時）→ ② 維修天數(天)×24 → ③ 維修天數×24 → ④ 花費工時；需重跑 Sync 使 DB 更新

## [1.59.1] - 2026-05-12

### Fixed
- **Dashboard「本月工時統計」漏算跨月完工案件** — `total_work_hours` / `top_hours` / `kpi_hours_detail` 原本使用 `this_month_cases`（上月累積未結 + 本月新增），跨月完工案件（上月報修、本月驗收）不在該集合內導致工時漏算；修正後改用 `hours_month_cases = filter_cases(...)`（驗收月口徑），與費用統計口徑一致，確保所有本月完工案件的工時都被計入

## [1.59.0] - 2026-05-12

### Fixed
- **Dashboard 全年模式 KPI 口徑修正** — `compute_dashboard(month=0)` 的 `this_month_cases` 改用 `occ_year`（報修日期），與 3.1/3.3 全年總數口徑一致；原本 `filter_cases`（完工日期）導致跨年結案案件（如 2024 報修/2025 完工）在 2025 Dashboard 被計入但在 3.1 2024 ④ 中
- **4.4 客房報修表口徑修正** — `compute_room_repair_table()` 改用 `occ_year/occ_month`（報修日期），原本 `filter_cases`（完工日期）導致月份 Tab 看不到跨月完工的客房案件
- **3.3 類型統計「上月」跨年修正** — `compute_type_stats()` 的 `prev_m_val` 當 `focus_month=1` 時，上月為上一年 12 月；原本只取月份數字（12）查 `type_monthly`（僅含當年資料），固定回傳 0；修正後另外計算前一年對應月份的類型分布
- **金額統計口徑確認** — `compute_fee_stats()` 確認以「驗收月」（`completed_at` 月份）統計，符合業主需求，新增說明注釋

## [1.58.9] - 2026-05-12

### Fixed
- **3.3 報修類型統計 — 口徑改為「報修日期」與 3.1 對齊** — `compute_type_stats()` 原本以 `_stat_year/_stat_month`（完工日期）分組，導致跨年結案案件計入不同年份，造成 3.3 年度加總與 3.1「本月報修」加總不一致；修正後改用 `occ_year/occ_month`（報修日期），與 4.1 報修統計 Tab 同口徑，確保兩者年度總數相同
- **Dashboard 報修類型分布 — 口徑同步改為「報修日期」** — `compute_dashboard()` 的 `type_dist` 原本用 `filter_cases`（完工日期）篩案件，與 3.3 口徑不一致；修正後改用 `occ_year/occ_month`，月份檢視與全年檢視均以報修日期為準，圖表數字與 3.3 Tab 一致

## [1.58.8] - 2026-05-11

### Performance
- **`GET /trend` date-range 批次查詢** — 移除 `_mall_completion_for_day` / `_security_completion_for_day` 兩個每日 per-query 函數；改為一次撈 `inspection_date >= start_str` 的所有 batch（1 次），再用 `IN` 撈全部 items（1 次）；商場 3 樓層各 2 次、保全 2 次，共 8 次 query 替代原本最多 120 次（30 天 × 4 模組）

## [1.58.7] - 2026-05-11

### Performance
- **`GET /kpi` 5 分鐘 TTL cache** — 在 `dashboard.py` 加入 in-process `_kpi_cache`（`threading.Lock` + `time.monotonic`），快取命中時跳過全部 DB query；TTL = 300 秒，無需外部依賴（純 stdlib）

## [1.58.7] - 2026-05-12

### Fixed
- **3.3 報修類型統計 — 遺漏非標準類型修正** — `compute_type_stats()` 原本 `rows` 迴圈只輸出 `REPAIR_TYPE_ORDER` 內的標準類型，導致 48 種客房特有類型（如「天花板」「衣櫃拉門」「止水條」等）完全不計入顯示與加總，造成 `year_total` 偏低；修正後新增 ② 迴圈將不在 `REPAIR_TYPE_ORDER` 的類型依件數降序追加，`year_total` 現在涵蓋所有案件
- **報修類型 mapping 修正 2 項** — ① 新增 `"衛厠": "衛廁"`（常見錯字廁/厠不同 Unicode）；② 新增 `"浴廁": "衛廁"` 與 `"浴室玻璃": "衛廁"`，避免「浴室玻璃門」因 "玻璃" 關鍵字被錯誤歸入「建築」
- **API response 新增 `extra_types` 欄位** — `/stats/type` 回傳額外輸出 `extra_types` 列表（前端可視需要在標準類型後加分隔線）

## [1.58.6] - 2026-05-11

### Fixed
- **大直報修 Dashboard 趨勢圖完成數口徑修正** — `compute_dashboard()` 的 `trend_12m` 將 `completed` 計算從 `is_completed(c.status)`（當前狀態）改為 `_completed_in(c, y, m)`（`completed_at` 落在該月），與 4.1 報修統計 Tab 口徑對齊；消除「跨月結案」被計回報修月造成完成率虛高的問題（例：1月趨勢 completed 268 → 240，完成率 94.0% → 84.2%）

## [1.58.6] - 2026-05-11

### Performance
- **`hotel/overview` N+1 修復** — `get_hotel_monthly_hours` / `get_hotel_person_hours` 中飯店週期保養的 batch→items 迴圈改用 `PeriodicMaintenanceItem.batch_ragic_id.in_(batch_ids)`，由原本 N+1 次 query 降為 2 次（1 batch + 1 items）
- **`mall/overview` N+1 修復** — `get_mall_monthly_hours` / `get_mall_person_hours` 中 MallPM + FullBldgPM 兩組 batch→items 迴圈各改用 `IN` query，共節省 4 組 N+1 → 2 次

## [1.58.5] - 2026-05-11

### Performance
- **SQLite 移出 OneDrive** — `DATABASE_URL` 改為絕對路徑 `sqlite:///C:/portal_data/portal.db`，消除 OneDrive 檔案鎖定造成的每次 DB 操作延遲
- **補齊所有 Item/Batch 表 Index** — B1F/B2F/RF/B4F 巡檢、飯店週期保養、商場週期保養六組 model 加入 `inspection_date`、`batch_ragic_id`、`abnormal_flag`、`is_completed` 索引；新增 `create_indexes.py` 一次性遷移腳本（20 個 index）
- **`GET /api/v1/dashboard/kpi` 改用 SQL aggregation** — `get_kpi()` 移除 `db.query(RoomMaintenanceRecord).all()` 全表掃描，改用 `func.count()`/`func.sum(case(...))`/`func.coalesce()` 直接在資料庫端彙總；庫存統計改用 `GROUP BY category` 單次查詢；重點房間改為 `.filter(incomplete > 0).order_by(...).limit(10)`

## [1.58.4] - 2026-05-11

### Fixed
- **IHG 客房保養 `/stats` 工時計算修正** — 移除工時加總前的 `(room_no, maint_month)` 去重步驟，改對全部原始記錄加總 `工時計算`（分鐘），使 `hotel/overview` 顯示的 IHG 工時與 `hotel/ihg-room-maintenance` 矩陣表口徑一致（22.4 HR → 23.13 HR）；狀態計數（completed/abnormal/pending）仍使用去重後記錄，行為不變

## [1.58.3] - 2026-05-11

### Added
- **IHG 客房保養表明細：樓層快選按鈕** — 將樓層篩選從下拉選單改為直覺式按鈕組（全部/5F/6F/7F/8F/9F/10F），置於「清除篩選」旁；選中樓層以 primary 樣式高亮，底下房號矩陣同步篩選
- **IHG 客房保養表明細：全房號顯示** — 引入 `CANONICAL_ROOMS`（59 間）清單，即使當月無保養記錄也會出現；無資料房號顯示「未執行」灰色底色（`has_data: boolean` 欄位）；完成率分母改為含未執行房間的全部房間數；標題顯示「共 N 間，M 間未執行」
- **IHG 客房保養表明細：點擊格子開啟保養明細** — 點擊任意房號 × 類別格子（有資料或空格皆可），觸發右側 Drawer 顯示該房號當月保養明細（`onCellClick` prop 串接至主元件 `handleCellClick`）；Tooltip 提示「點擊查看明細」

### Fixed
- **後端 section-matrix API** — 重建 `ihg_room_maintenance.py`，修復截斷導致 `/records` 與 `/{ragic_id}` 端點遺失；樓層篩選移至正規房間清單迴圈而非 DB 查詢

## [1.58.2] - 2026-05-11

### Fixed
- **IHG 客房保養 閃退修復** — 修正前端 `IHGRoomMaintenance/index.tsx` 在 Python 多次修補後末端 JSX 結構截斷（缺少 `/>`, `)}`, `</Drawer>`, `</div>`, `)`, `}` 六行）；將年度矩陣 Tabs children 抽出為 `const matrixTabContent`，解決 TypeScript parser 無法解析深層巢狀 JSX in object literal 的問題（TSC 錯誤 TS17008）；新增 `destroyInactiveTabPane` 隔離兩個 TAB；`SECTION_VALUE_CFG[val]` 加上 `?? V` fallback 防非預期值當機

## [1.58.1] - 2026-05-11

### Added
- **IHG 客房保養表明細 TAB** — 新增 `ihg_rm_section` 資料表（`id`, `master_ragic_id`, `room_no`, `maint_year`, `maint_month`, `category`, `value`, `synced_at`），每月x每房x每類別一列，值域 V/X；Ragic 主表同步時自動拆出 12 個區段欄位（客房房門/消防/設備/傢俱/燈電源/窗/面盆台面/浴厠/浴間/天地壁/空調/陽台）；新增 `GET /api/v1/ihg-room-maintenance/section-matrix?year=&month=` API；前端 IHGRoomMaintenance 頁面新增「客房保養表明細」TAB，房號x類別彩色矩陣，底部含保養完成 TOTAL 與完成率統計列

## [1.58.0] - 2026-05-10

### Added
- **專案知識圖譜（graphify 整合）** — 系統設定新增「專案知識圖譜」頁面（`/settings/knowledge-graph`）；後端整合 graphify CLI（`pip install graphifyy`），以 BackgroundTask 非同步分析整個 portal 專案（Python AST + TypeScript + SQL + Markdown），輸出互動式 HTML 圖譜存於 `backend/static/knowledge_graph/`；FastAPI StaticFiles 掛載 `/kg-files/`；前端以 iframe 嵌入呈現，含狀態輪詢（每 3 秒）+ 進度條 + 錯誤提示；新增後端 `routers/knowledge_graph.py`（GET /status、POST /generate、GET /result）、`services/graphify_runner.py`、前端 `api/knowledgeGraph.ts`、`pages/Settings/KnowledgeGraph/index.tsx`；menu icon：ApartmentOutlined；permissionKey：`system_admin_only`

## [1.57.97] - 2026-05-07

### Added
- **集團工務決策駕駛艙 Phase 6：異常提醒區（ROW 0.40）** — 新增 `AlertPanel` 元件，預設展開；規則：未完成件數 > 0（🔴）、完成率 < 60%（🔴）或 < 80%（🟠）、工項類別占比 > 60%（🟡）、人員工時 > 80h（🟠）、單日工時 > 月均 × 2（🔵）；無異常時顯示「✅ 本月無異常警示」

## [1.57.96] - 2026-05-07

### Added
- **集團工務決策駕駛艙 Phase 5：工項類別 × 單位矩陣（ROW 0.39）** — 後端新增 `_build_category_source_matrix()` 函式（來源：dazhi/luqun），回傳每類別的飯店件數、商場件數、合計件數、件占比、飯店工時、商場工時、總工時；前端新增 `CategorySourceMatrixItem` 型別及 `CategorySourceMatrix` 元件，含合計列（exec-total-row）；`CategoryStats.category_source_matrix` 欄位加入 API 型別定義

## [1.57.95] - 2026-05-07

### Added
- **集團工務決策駕駛艙 Phase 4：飯店 vs 商場比較表（ROW 0.38）** — 新增 `UnitComparisonTable` 元件，列：飯店（大直工務）/ 商場（商場工務）/ 合計；欄：案件數、工時（h）、完成件數、未完成件數、完成率、主要工項類別；資料來源：`dazhiData.kpi`、`luqunData.kpi`、`execStats.source_breakdown`，無新增 API 呼叫

## [1.57.94] - 2026-05-07

### Added
- **集團工務決策駕駛艙 Phase 3：集團 KPI Card（ROW 0）** — 8 個 `Statistic` 卡片（lg=3）：集團總案件數、已完成件數、未完成件數、集團總工時、完成率、平均工時/件、飯店案件占比、商場案件占比；所有數值由 `dazhiData.kpi`＋`luqunData.kpi`＋`execStats.kpi` 即時計算，無新增 API 呼叫

## [1.57.93] - 2026-05-07

### Added
- **集團工務決策駕駛艙（ExecWorkDashboard）Phase 1+2 完成** — 新建 `frontend/src/pages/ExecWorkDashboard/index.tsx`（993 行），以 Dashboard 為基底精簡：移除保全/商場巡檢/預算/GraphView 非工務區塊，`loadAll` 從 13 個 API 精簡為 7 個，完整保留工務報修摘要、每日/月累計、工時分析、人員負荷等所有工務表格；Phase 2 新增路由 `/exec-work-dashboard`、navLabels key `execWorkDashboard`、MainLayout sidebar 項目（`RadarChartOutlined`）、`permissionKey: exec_work_dashboard_view`；原始 Dashboard 完全不受影響

## [1.57.92] - 2026-05-07

### Changed
- **Dashboard「人員負荷與效率分析」改為獨立 Collapse 面板（ROW 0.37）** — 從 ExecRankingTable 拆出為獨立 `ExecBurdenTable` 元件，置於所有工時表最下方；「人員工時佔比表」與「人員排名詳細表」兩個面板從 Collapse 移除（隱藏）；`ALL_ANALYSIS_KEYS` 同步更新為 `['exec-daily', 'exec-monthly', 'exec-burden']`

## [1.57.91] - 2026-05-07

### Added
- **Dashboard 人員排名詳細表新增「人員負荷與效率分析」子表** — 後端 `_build_person_ranking` 新增 `cases`（去重件數）與 `avg_hr`（平均工時/件）欄位；前端在既有排名表下方加第二張表，欄位：人員／工時／件數／均工時/件／主要類別／判斷；判斷閾值：均工時 ≥3.0 → 需關注（紅）、2.5–3.0 → 工時偏高（橙）、<2.5 → 正常（綠）

## [1.57.90] - 2026-05-07

### Changed
- **Dashboard 工項類別比較表新增「合計」與「占比」欄** — 合計欄即時計算飯店＋商場件數；占比欄顯示各類別佔總件數百分比（≥50% 紅、≥20% 橙、其餘灰）；小計列同步補齊兩欄（合計總數 / 100%）

## [1.57.89] - 2026-05-07

### Changed
- **Dashboard 工項類別比較表新增小計列** — 使用 `Table.Summary` 在表格最底部加入「小計」固定列，飯店／商場各欄自動加總；底色 `#f0f4f8`、粗體，字級與內容列一致（15px）
- **Dashboard 隱藏 ROW 6 模組關聯圖譜（GraphView）** — 實體移除 JSX 區塊及 import，60 秒輪詢 API 不再發出，效能零影響

## [1.57.88] - 2026-05-07

### Changed
- **Dashboard 所有表格字體放大 2 級** — 飯店/商場每日累計表、明細分析 4 張工時表（每日/每月/人員/排名）內所有 `fontSize` 統一 +2：9→11、10→12、11→13、12→14、13→15；Collapse 標籤（16px）及主要 UI chrome 不受影響

## [1.57.87] - 2026-05-07

### Changed
- **Dashboard 明細分析面板標題年月文字字級統一為 16px** — 「每日累計工時表」與「每月累計工時表」Collapse 面板 label 中的年月副文字（`Typography.Text type="secondary"`）由 11px 改為 16px，與「飯店每日累計案件數」等面板字級一致

## [1.57.86] - 2026-05-07

### Changed
- **Dashboard 全展開/全收合按鈕移至左側；移除「明細分析（可收合）」Divider 標籤**

## [1.57.85] - 2026-05-07

### Added
- **Dashboard 折疊區塊新增「全展開／全收合」按鈕** — ROW 0.35 上方加入右對齊切換按鈕；兩組 Collapse（每日累計 × 2 面板、明細分析 × 4 面板）改為受控模式（`activeKey` + `onChange`）；全部展開時顯示「⊖ 全收合」、全部收合時顯示「⊕ 全展開」；各面板仍可獨立點擊收合，互不影響

## [1.57.84] - 2026-05-07

### Changed
- **Dashboard ROW 0.4～ROW 5 暫時隱藏** — 主管指標（ExecMetricsCard）、今日重點摘要（TodaySummaryCard）、KPI 完成率卡（商場/保全/客房）、群組摘要卡、同步紀錄、完成率趨勢、結案率追蹤等全部 mark 不呈現；ROW 6 模組關聯圖譜保留；程式碼以注釋標記保留，可隨時恢復

## [1.57.83] - 2026-05-07

### Added
- **Dashboard 新增商場近12個月報修趨勢 + 報修類型分布雙欄 Row（ROW 0.33）** — 飯店雙欄（ROW 0.32）下方；左欄（lg=14）：近12個月報修趨勢折線圖（`luqunData.trend_12m`）；右欄（lg=10）：報修類型分布圓餅圖（`luqunData.type_dist`）；零新增 API 呼叫；mall/overview 不動

## [1.57.82] - 2026-05-07

### Added
- **Dashboard 新增近12個月報修趨勢 + 報修類型分布雙欄 Row（ROW 0.32）** — 三卡列下方、每日累計折疊表上方；左欄（lg=14）：近12個月報修趨勢折線圖（報修件數/完成件數，來自 `dazhiData.trend_12m`）；右欄（lg=10）：報修類型分布圓餅圖（來自 `dazhiData.type_dist`）；零新增 API 呼叫，使用已載入的 `dazhiData`；補充 recharts `PieChart/Pie/Cell` import 及 `TypeDistItem` type import；dazhi-repair/dashboard 不動

## [1.57.81] - 2026-05-07

### Changed
- **Dashboard 明細分析四張表內容字級 +1 級** — `execRenderHr` 11→12；`execRenderCat` Tag 10→11；每日表日期標頭 9→10 / 8→9；每月表月份標頭 10→11、未來格 11→12；人員表人員標頭 10→11、佔比值 11→12；排名表類別 Tag 10→11、來源 Tag 9→10

## [1.57.80] - 2026-05-07

### Changed
- **Dashboard 每日累計 / 明細分析標題字級統一放大至 16px** — 飯店每日累計案件數、商場每日累計案件數 Collapse 標題加 `fontSize: 16`；明細分析 Divider 從 12→16；exec 四個面板標題從 13→16；三區塊統一對齊

## [1.57.79] - 2026-05-07

### Added
- **Dashboard 新增「明細分析（可收合）」區塊** — 移植 exec-dashboard 的四張工時分析表至集團管理總覽，放置於商場每日累計折疊表下方（ROW 0.36）；包含：📅 每日累計工時表、📆 每月累計工時表、🧑‍💼 人員工時佔比表、🏆 人員排名詳細表；以 `Collapse`（`defaultActiveKey=[]` 預設全收合）包覆；`loadAll` 擴充為 13 項平行呼叫，新增 `fetchStats({ year, month, sources/category/person=all })`；新增 `execStats: CategoryStats` state；exec-dashboard 本身完全不動

## [1.57.78] - 2026-05-07

### Added
- **Dashboard 工務報修區塊加入 Section Header** — ROW 0.3（三卡列）上方新增「工務報修」區塊標題卡（Card + `borderTop: 3px solid #1B3A5C`），含 `ToolOutlined` 圖示、「工務報修」標題、年月副標；樣式與「主管指標」Section Header 一致

## [1.57.77] - 2026-05-07

### Changed
- **Dashboard 每日累計表工項類別與數字加入超連結** — `HotelDailyTable` / `MallDailyTable`：工項類別標籤（現場報修／例行維護／每日巡檢）改為可點擊連結；各日期格及「案件數」欄的非零數字亦改為連結；飯店對應路由：`/dazhi-repair`、`/hotel/periodic-maintenance`、`/hotel/daily-inspection`；商場對應路由：`/luqun-repair`、`/mall/periodic-maintenance`、`/mall-facility-inspection`；上級交辦／緊急事件（固定 0）不加連結；新增 `HOTEL_CAT_ROUTES` / `MALL_CAT_ROUTES` 常數，兩個 table component 各自呼叫 `useNavigate()`

## [1.57.76] - 2026-05-07

### Added
- **Dashboard 新增飯店／商場每日累計案件數折疊表格** — `Dashboard/index.tsx`：新增 `HotelDailyTable` / `MallDailyTable` 元件，顯示各工項類別每日案件數（飯店六來源合併為五類：現場報修=飯店工務部、例行維護=客房保養管理+飯店週期保養+IHG客房保養、每日巡檢=飯店每日巡檢+保全巡檢、上級交辦/緊急事件=0；商場直接顯示）；以 Ant Design `Collapse`（`defaultActiveKey=[]` 預設全收合）包覆，放置於工務報修三卡列與主管指標之間；`loadAll` 擴充為 12 項平行呼叫，加入 `fetchHotelDailyHours`、`fetchMallDailyHours`；表格與上方年月篩選器連動

## [1.57.75] - 2026-05-07

### Fixed
- **Dashboard 工項比較表「飯店」欄數值修正** — `categoryComparison` useMemo 改套用與 `HotelMgmtDashboard TAB C` 相同的多來源合併邏輯：`現場報修`=`飯店工務部.cases[mi]`；`例行維護`=`客房保養管理+飯店週期保養+IHG客房保養`；`每日巡檢`=`飯店每日巡檢+保全巡檢`；`上級交辦`/`緊急事件`=0；商場維持直接 find（API 已回傳五類名稱）

## [1.57.74] - 2026-05-07

### Changed
- **Dashboard 工項類別比較表改用每月累計 API（與 hotel/overview、mall/overview TAB C 口徑一致）** — `Dashboard/index.tsx`：將 `fetchHotelDailyHours`/`fetchMallDailyHours` 改為 `fetchHotelMonthlyHours`/`fetchMallMonthlyHours`（傳入 `selectedYear`）；`categoryComparison` useMemo 改取 `cases[selectedMonth - 1]`，確保比較表數字與 hotel/overview、mall/overview TAB C「每月累計」完全相同

## [1.57.73] - 2026-05-07

### Changed
- **Dashboard 飯店工務部／商場工務報修卡新增「當月金額」區塊** — `Dashboard/index.tsx`：`RepairSummaryCard` 摘要文字下方加入費用小表（委外+維修 / 扣款費用 / 扣款專櫃 / 當月小計），資料來自 `kpi.month_outsource_fee`、`month_maintenance_fee`、`month_deduction_fee`、`month_deduction_counter`、`month_total_fee`；值為 0 時顯示「-」

## [1.57.72] - 2026-05-07

### Changed
- **Dashboard「主管指標」移至工務報修三卡列下方** — `Dashboard/index.tsx`：ROW 0（ExecMetricsCard）移至 ROW 0.3（飯店工務部＋商場工務報修＋比較表）之後，改編號為 ROW 0.4

## [1.57.71] - 2026-05-07

### Fixed
- **集團管理總覽 Dashboard 年月篩選 + 3 卡佈局恢復** — `Dashboard/index.tsx`：修復 revert 過程中意外遺失的 v1.57.65-67 功能；`curYear`/`curMonth` 常數改回 `selectedYear`/`selectedMonth` state；新增 `hotelDailyData`/`mallDailyData` state；`loadAll` 擴充為 10 項平行呼叫（加入 `fetchHotelDailyHours` / `fetchMallDailyHours`）；加回 `categoryComparison` useMemo；ROW 0.3 恢復年月 Select 篩選器 + 飯店工務部（colLg=8）+ 商場工務報修（colLg=8）+ 工項類別比較表（colLg=8）三欄佈局

## [1.57.70] - 2026-05-07

### Reverted
- **還原 Dashboard 與 mall/overview 費用嵌入變更（v1.57.68、v1.57.69）** — `Dashboard/index.tsx` 移除 `showCosts`/`costLabel` props 及費用 footer block；`MallMgmtDashboard/index.tsx` 恢復獨立「商場報修費用摘要」Divider + Row 三卡版面，`SourceStatusCard` 的 `footer` prop 保留（optional，不影響現有使用）

## [1.57.69] - 2026-05-07

### Changed
- **集團管理總覽 Dashboard「商場工務報修」卡嵌入費用摘要** — `Dashboard/index.tsx`：`RepairSummaryCard` 新增 `showCosts`/`costLabel` props；商場工務報修卡傳入 `showCosts` 後，卡片底部顯示費用摘要 3 欄（委外+維修費用 / 扣款費用 / 扣款專櫃），資料來自 `luqunData?.kpi.annual_*` 欄位，隨頂層 YYYY/MM 篩選自動連動；新增 `QuestionCircleOutlined` icon import

## [1.57.68] - 2026-05-07

### Changed
- **商場管理 Dashboard 費用摘要嵌入「商場工務報修」卡** — `MallMgmtDashboard/index.tsx`：移除獨立「商場報修費用摘要」Divider + Row；費用資料（委外+維修費用 / 扣款費用 / 扣款專櫃）改以 compact 3欄 footer 形式嵌入 `luqun_repair` SourceStatusCard 底部，隨頂層年月篩選（`year`/`month`）自動連動；`SourceStatusCard` 新增 `footer?: React.ReactNode` prop，供其他卡片擴充使用

## [1.57.67] - 2026-05-07

### Changed
- **集團管理總覽 Dashboard 工務報修二卡 + 工項比較表合為同一列** — `Dashboard/index.tsx`：原兩個 `<Row>` 合併為一個 `<Row align="stretch">`；`RepairSummaryCard` 新增 `colLg` prop 覆寫 Col span（預設 12，此處傳 8）；工項類別比較表 Col 改為 `lg={8}`；三卡在大螢幕等寬並排

## [1.57.66] - 2026-05-07

### Changed
- **集團管理總覽 Dashboard 工務報修卡左右對調，「大直」→「飯店」** — `Dashboard/index.tsx`：兩張 `RepairSummaryCard` 順序對調（飯店工務部在左、商場工務報修在右）；模組內所有「大直」顯示文字（label、註解）改為「飯店」；API 呼叫端變數名稱不變（`dazhiData`、`fetchDazhiDashboard`）

## [1.57.65] - 2026-05-07

### Added
- **集團管理總覽 Dashboard 年月篩選 + 工項類別比較表** — `Dashboard/index.tsx`；不新增後端 API，沿用既有 `/api/v1/hotel/daily-hours` 與 `/api/v1/mall/daily-hours`
  - 頁面頂部新增 YYYY / MM 兩個 Select（預設當年當月），同步控制報修數據與比較表
  - Block 1「報修數據」：商場工務報修（路易莎）數字改接 `luqun-repair/dashboard?year&month`，大直工務部數字改接 `dazhi-repair/dashboard?year&month`，確保與各自 overview 一致
  - Block 2（新增）「飯店/商場工項類別比較表」：5 行（現場報修 / 上級交辦 / 緊急事件 / 例行維護 / 每日巡檢），左欄飯店件數、右欄商場件數，資料來源 `daily-hours` API 的 `cases_total` 欄位；飯店側：現場報修=飯店工務部、例行維護=週期保養+IHG客房保養、每日巡檢=飯店每日巡檢+保全巡檢；商場側對應五類直接映射

## [1.57.64] - 2026-05-07

### Changed
- **飯店 Dashboard 主管摘要 KPI Card 改為全寬均分** — `HotelMgmtDashboard/index.tsx` `KpiAggregate()` 函式內 5 張 Card 的 `Col` 由 `xs={12} sm={8} md={4}` 改為 `flex="1"`，讓 Ant Design Row 自動均分全寬

## [1.57.63] - 2026-05-07

### Changed
- **商場 Dashboard 頂層月份篩選預設值改為當月** — `MallMgmtDashboard/index.tsx` `month` state 初始值由 `0`（全年）改為 `thisMonth`；頁面載入即自動帶入當月篩選，API 呼叫隨之傳入當月月份參數

## [1.57.62] - 2026-05-07

### Changed
- **商場 Dashboard KPI 卡移除「整體完成率」** — `MallMgmtDashboard/index.tsx` 刪除 Progress circle「整體完成率」Card（原為 6 張 `md={4}`）；剩餘 5 張 KPI Card（本期總工項 / 已完成工項 / 本期工時合計 / 異常未結案件 / 逾期未保養）均改為 `<Col flex="1">`，讓 Ant Design Row 自動均分全寬；`overallRate` 計算值保留，仍顯示於「已完成工項」卡的副標文字（完成率 X%）

## [1.57.61] - 2026-05-07

### Fixed
- **商場 Dashboard Tab B/C/D 表格數字全空白修正** — 根本原因：`mall_overview.py` 的 `/mall/daily-hours` 與 `/mall/monthly-hours` endpoint 只回傳 `hours/total/pct`，未計算案件件數，導致前端 `row.cases?.[i]` 取得 `undefined` → 0 → 全部顯示 `—`；修正方式：兩個 endpoint 各新增 `case_bucket: dict[str, dict[int, int]]` 進行案件計件（現場報修 = LuqunRepairCase 筆數、例行維護 = PM item 筆數、每日巡檢 = inspection batch 筆數、上級交辦/緊急事件模組未建置故仍為 0），組裝 result_rows 時追加 `cases`（逐日/月陣列）、`cases_total`（合計）、`cases_pct`（佔比）三欄；TOTAL 列同步追加；`daily-hours` 1021 行，`monthly-hours` 相同檔案

## [1.57.60] - 2026-05-07

### Added
- **Dashboard B/C Tab 新增「匯出 CSV」按鈕（飯店 + 商場）** — 純前端實作，不新增後端 API；兩個 Dashboard 各加 `exportCSV` helper（BOM `﻿` + `text/csv;charset=utf-8` Blob，URL.createObjectURL 觸發下載）；`HotelMgmtDashboard` TabBDaily 篩選列加匯出按鈕（檔名：`飯店管理_每日累計_{year}年{month}月.csv`，欄位：工項類別 / N日(週X) / 案件數 / %）、TabCMonthly 篩選列加匯出按鈕（`飯店管理_每月累計_{year}年.csv`，欄位：工項類別 / 1–12月 / 案件數 / %）；`MallMgmtDashboard` Tab B / Tab C 同樣新增匯出按鈕（`商場管理_每日累計_{year}年{month}月.csv` / `商場管理_每月累計_{year}年.csv`）；資料未載入時按鈕 disabled；`DownloadOutlined` icon 已加入兩個檔案的 import

## [1.57.59] - 2026-05-07

### Fixed
- **`hotel/overview` 來源卡路由路徑修正** — `HotelMgmtDashboard/index.tsx` `HOTEL_SOURCE_ROUTES` 修正兩條錯誤路徑：`daily_inspection` 由 `'/hotel/hotel-daily-inspection/dashboard'` 改為 `'/hotel/daily-inspection'`；`security` 由 `'/hotel/security/dashboard'` 改為 `'/security/dashboard'`（對照 `router/index.tsx` 實際路由確認）

## [1.57.58] - 2026-05-07

### Refactor
- **抽取共用 `SourceStatusCard` React Component** — 新增 `frontend/src/components/SourceStatusCard/index.tsx`，exports `SourceStatusCardProps` 介面與 `SourceStatusCard` 元件；支援 props：`source_key/name/color`、`case_count/completed_count/work_hours/actual_hours/completion_rate/abnormal_count/overdue_count/status_label`（`-1` = 不適用）、`is_placeholder/loading/error/onClick/icon/cardSize/titleFontSize/statFontSize/infoFontSize`；`source_key === 'dazhi'` 自動將「異常」改為「未完成」；`actual_hours` 有值 → PM 雙行模式（預估工時 + 保養時間），無值 → 單行工時；`HotelMgmtDashboard` `SourceCards()` 替換為 `<SourceStatusCard {...s} icon=... onClick=... />`，佔位卡改用 `is_placeholder`；`MallMgmtDashboard` 刪除 local `SourceCard` function，ROW1/ROW2 改用 `<SourceStatusCard>` 傳入 `cardSize="small" titleFontSize={16} statFontSize={22} infoFontSize={17}`（保持原有視覺大小）

## [1.57.57] - 2026-05-07

### Fixed
- **`hotel/overview` `adaptDazhi` source_name 與後端對齊** — `HotelMgmtDashboard/index.tsx` `adaptDazhi` 函式中 `source_name: '工務部'` 改為 `'飯店工務部'`，與後端 `HOTEL_CATEGORIES` 第 5 項一致

## [1.57.56] - 2026-05-07

### Fixed
- **`hotel/overview` 週期保養批次查詢補月份格式容錯** — `hotel_overview.py` `get_hotel_daily_hours` 中週期保養批次查詢由 `period_month == f"{year}/{month:02d}"` 改為 LIKE `f"{year}/%"` 再以 Python `int(period_month.split("/")[1]) == month` 過濾，容錯非補零格式（如 `2026/5`），與 `mall_overview.py` 對齊；`get_hotel_monthly_hours` 與 `get_hotel_person_hours` 已是 LIKE 無需異動；未修改前端

## [1.57.55] - 2026-05-07

### Changed
- **`mall/overview` 每年累計 Tab 改為 Running Total 格式（比照 hotel/overview）** — `MallMgmtDashboard/index.tsx` 重寫 Tab E：移除多年比較（`yearlyDataMap`/`yearlyBaseYear`/`loadYearlyHours` 3年版），改為單年 Running Total；新增 state `yearlyData`（`MallMonthlyHoursData | null`）與 `yearlyYear`；新增 `MallRow5Y` 型別；`buildMallYearlyCols()` 改為生成「工項類別 + 1月–12月 + 案件數 + %」欄（未來月份顯示 —）；`TabYearly` 改為 function component，`loadYearlyHours` 改為單年版，`handleTabChange` 改為 `!yearlyData` null-check；篩選 Card（年度累計案件數 label + 年份選單 + 重新整理 + YYYY年（累計）label）、五類別圖例 + ⓘ Tooltip + ⓘ 累計說明 tooltip，表格 Card 標題「年度累計案件數」extra「YYYY年（累計至各月）」

## [1.57.54] - 2026-05-07

### Refactor
- **抽取共用 `parse_minutes` 至 `app/services/time_utils.py`** — 新增 `backend/app/services/time_utils.py`，將 `hotel_overview.py`（原 line 60）與 `mall_overview.py`（原 line 43）中邏輯完全相同的 `_parse_minutes` 函式統一為 `parse_minutes`，補齊完整 docstring（含跨日修正說明與範例）；兩個 router 各刪除本地定義，改以 `from app.services.time_utils import parse_minutes as _parse_minutes` 引入，別名保持 `_parse_minutes` 使所有呼叫端零修改；`docs/TECH_SPEC.md` 新增「服務層共用工具」表格

## [1.57.53] - 2026-05-07

### Added
- **`mall/overview` 人員排名 Tab 補上來源分解堆疊 BarChart** — `MallMgmtDashboard/index.tsx` 新增 `MALL_3CATS`（現場報修/例行維護/每日巡檢）與 `MALL_CAT_HEX` 色彩映射；新增 `breakdownData` useMemo 將 `personRanking` 反轉並展開每人各來源工時（`total_hours * pct / 100`）；在 TabRanking 既有排名 BarChart 與明細表之間插入 Card「人員工時分解（HR）」，內含 220px 高度 `ResponsiveContainer` + `BarChart layout="vertical"` 堆疊圖（`stackId="src"`），最後一條 Bar 加 radius `[0,4,4,0]`；含 `Legend`、`RcTooltip`（顯示 HR）；未修改後端

## [1.57.52] - 2026-05-07

### Changed
- **`hotel/overview` 各工時 Tab 改為獨立篩選** — `HotelMgmtDashboard/index.tsx` 新增四個獨立 state：`tabBYear`/`tabBMonth`（Tab B 每日）、`tabCYear`（Tab C 每月）、`personYear`（人員工時%/人員排名共用）；新增 `monthOptions12`（1–12 月，無全年，供 Tab B）；`handleTabChange` 從 `loadedTabs` ref 改為 null-check 觸發（`!dailyData`/`!monthlyData`/`!yearlyData`/`!personData`），移除 `loadedTabs` ref；Tab B/C 篩選 Card 的 `onChange` 直接觸發 fetch；Tab D/人員排名 各加篩選 Card（`personFilterCard`/`rankingFilterCard`），null check return 也附上 filterCard；Dashboard Tab 的 year/month state 保持原有邏輯，不受影響

## [1.57.51] - 2026-05-07

### Added
- **`hotel/overview` 每日/每月/每年累計表補 `cases_pct` 欄位** — 後端 `hotel_overview.py` `get_hotel_daily_hours` 與 `get_hotel_monthly_hours` 各非 TOTAL 列計算 `cases_pct`（`cases_total / grand_cases_tot * 100`，1 位小數）；TOTAL 列固定 `cases_pct: 100.0`；TypeScript `hotelOverview.ts` `HotelDailyRow` 與 `HotelMonthlyRow` 補 `cases_pct: number`；前端 `HotelMgmtDashboard/index.tsx` Tab B/C/D 的本地 `Row5`/`Row5M`/`Row5Y` 型別由 `pct` 改為 `cases_pct`，`dataIndex: 'pct'` 改為 `dataIndex: 'cases_pct'`，`buildDailyCols`/`buildMonthlyCols` column key 同步更新

## [1.57.50] - 2026-05-06

### Changed
- **`hotel/overview` Tab key 命名與商場統一** — `HotelMgmtDashboard/index.tsx` 中 `key: 'overview'` → `'dashboard'`、`key: 'person'` → `'person_pct'`；`handleTabChange` 條件判斷同步更新（`=== 'person'` → `=== 'person_pct'`）；label・children・loadedTabs 邏輯均不變

## [1.57.49] - 2026-05-06

### Fixed
- **`mall/overview` PPTX 後端 endpoint + 前端按鈕** — `mall_overview.py` 從 git HEAD 完整復元（997→997 行，修復截斷的 `_build_mall_pptx` 函式）；`POST /overview/export/pptx`（`export_mall_overview_pptx`）已隨 git 版本恢復；前端匯出按鈕（FilePptOutlined，loading={exportLoading}，linear-gradient 樣式）在 Header Card 已正確渲染（T04 復元時一併確認）

## [1.57.48] - 2026-05-06

### Fixed
- **`mall/overview` 人員排名 Tab 改用五項來源** — `MallMgmtDashboard/index.tsx` Tab E 人員排名資料來源由 `luqunData.top_hours`（僅報修 1 項）改為 `/mall/person-hours`（現場報修+上級交辦+緊急事件+例行維護+每日巡檢 5 項）；`personRanking` useMemo 重寫（`persons`/`person_totals`/`cats` 欄位）；`handleTabChange` 補上 `ranking` key 觸發 `loadPersonHours()`；Alert 說明文字更新；BarChart `dataKey` 改為 `total_hours`；排名明細表「案件數」欄改為「來源分解」Tooltip；Table.Summary 同步更新
- **`frontend/src/api/mallOverview.ts` 補上 `person_totals` 欄位** — `MallPersonHoursData` interface 新增 `person_totals: number[]`（後端已回傳，前端型別缺少）

## [1.57.47] - 2026-05-06

### Fixed
- **`hotel/overview` API summary 「六項來源」→「五項來源」** — `hotel_overview.py` 三個 GET endpoint 的 summary 字串（line 80 / 270 / 443）由「六項來源」統一修正為「五項來源」，與 `HOTEL_CATEGORIES`（5 項）一致；同步修正 module docstring（line 3–5）

## [1.57.46] - 2026-05-06

### Fixed
- **`hotel/overview` PPTX Slide 2 佔位卡名稱錯誤** — `_build_slide2_kpi` 內 placeholder card 名稱由 `["商場主管交辦", "商場緊急事件"]` 修正為 `["飯店主管交辦", "飯店緊急事件"]`（`hotel_overview.py` line 797）

## [1.57.45] - 2026-05-06

### Added
- **`hotel/overview` PPTX 匯出 POST endpoint** — `backend/app/routers/hotel_overview.py` 新增 `POST /overview/export/pptx`（絕對路徑：`/api/v1/hotel/overview/export/pptx`）；接收 `year`/`month` Query 參數與 `HotelPptxPayload` Request body；內部呼叫 `get_hotel_daily_hours` / `get_hotel_monthly_hours` / `get_hotel_person_hours` 取得資料後傳入 `_build_hotel_pptx`；以 `StreamingResponse`（Content-Type: `application/vnd.openxmlformats-officedocument.presentationml.presentation`）回傳，Content-Disposition 檔名為 `飯店管理報告_{year}年{month:02d}月.pptx`（RFC 5987 URL-encoded）

## [1.57.44] - 2026-05-06

### Changed
- **`mall/overview` Tab B 每日巡檢口徑改為 Dashboard 同口徑** — 後端 `daily-hours` 的⑤每日巡檢改採與 `/monthly-dashboard` 相同邏輯：每天 = 實際登錄場次數 + 缺漏場次數（5 張表各應每天巡一次）；過去月份所有天均計入、當月截至今日；同時容錯 `YYYY/MM/DD` 與 `YYYY/M/DD` 日期格式；ⓘ Tooltip 說明同步更新

## [1.57.43] - 2026-05-06

### Changed
- **`mall/overview` B/C/D TAB 現場報修口徑改為 `_stat_dt`** — 後端 `daily-hours` 與 `monthly-hours` 的①現場報修改採與 `luqun-repair/dashboard` 相同的統計口徑：已結案以 `completed_at` 歸屬日期、未結案以 `occurred_at` 歸屬、排除「取消」案件；月曆數字從 51→56 與 dashboard 一致
- **`mall/overview` B/C/D TAB 加工項 ⓘ Tooltip** — 仿 `hotel/overview` 做法，在 Tab B/C/D 類別 Tag 旁新增 ⓘ Tooltip，說明各工項計算口徑（現場報修 = `_stat_dt` 規則、例行維護 = PM 項目數、每日巡檢 = 批次數）

## [1.57.42] - 2026-05-06

### Changed
- **全模組顯示文字「樂群」統一改為「商場」** — 以 `sed` 批次替換前後端共 30 支檔案中所有中文顯示字串、注釋、標籤內的「樂群」為「商場」（英文程式識別字 `luqun`/`luqunRepair`/`luqun_repair`/`/luqun-repair/` 路由均保持不變）；涵蓋 `navLabels.ts`、`workCategoryAnalysis.ts`、`role_permissions.py`、`work_category_analysis.py`、`main.py` API tags、`RagicAppDirectory.tsx`（55 處）等

## [1.57.41] - 2026-05-06

### Changed
- **`mall/overview` B/C/D TAB 由工時改為案件數** — 後端 `/daily-hours` 和 `/monthly-hours` 各自新增 `cases_bucket` 平行統計：現場報修＝LuqunRepairCase 筆數（`occurred_at` 歸屬）、例行維護＝MallPeriodicMaintenanceItem + FullBldgPMItem 件數、每日巡檢＝MallFIBatch + RFInspectionBatch 批次數；每 row 加 `cases[]`、`cases_total`、`cases_pct` 欄位；前端 `MallDailyRow`/`MallMonthlyRow` 型別同步補充，`buildMallDailyCols`/`buildMallMonthlyCols` 欄位 render 改為 `renderMallCase(row.cases[i])`，TOTAL 欄改 `cases_total`，% 欄改 `cases_pct`；D.每年累計用 `cases_total` 取代 `total`；所有 Tab Card 標題與提示文字由「工時 (HR)」改為「案件數」

### Fixed
- **`mall/overview` PPTX 匯出函式結尾補齊** — 修復上一版 `for ri i` 截斷語法錯誤，補上 `for ri in range(n_rows5)` 行高設定及 `StreamingResponse` return 語句

## [1.57.40] - 2026-05-06

### Changed
- **`mall/overview` Tab A 篩選列重構** — 年月 Select 從 Header Card 移至 Tab A 篩選列，格式改為「工務篩選：[年▼] [月▼] | 巡檢日期：[DatePicker] [今日]」；年/月變更即時自動重載 PM / 全棟 PM / 巡檢 / 報修資料；Header Card 右側僅保留匯出 PPTX 按鈕；「工務巡檢日期」標籤改為「巡檢日期」

## [1.57.39] - 2026-05-06

### Changed
- **`mall/overview` 顯示文字「大直」統一改為「商場」** — Tooltip、Alert、Card 標題、元件注釋中全部 8 處「大直工務報修」/「大直報修」改為「商場工務報修」/「商場報修」
- **`mall/overview` 新增 Tab D「每年累計」** — 複數年份各呼叫一次既有 `fetchMallMonthlyHours` API，取各類別全年 `total`，組成年份 × 5 工項交叉表；預設顯示最近 3 年（BaseYear−2 ～ BaseYear）；零新增後端 API；狀態：`yearlyDataMap`/`loadingYearly`/`yearlyBaseYear`；`handleTabChange` 懶載入
- **`mall/overview` TAB 標籤調整** — 新增「D. 每年累計」（插入 C/人員工時% 之間）；原「D. 人員工時%」移除 D. 前綴改為「人員工時%」；全部 TAB label 字體 +2（14→16px）
- **`Settings/RagicAppDirectory` 補充全棟例行維護** — 新增 itemNo 220（全棟週期保養日誌，`periodic-maintenance/21`）至靜態資料表及 LOCAL_TABLE_MAP（`full_bldg_pm_batch/full_bldg_pm_batch_item`）；portal_defaults 對應 `/mall/overview`

## [1.57.38] - 2026-05-06

### Changed
- **`hotel/overview` B/C/D/人員工時%/人員排名 TAB 表格字體放大 2 級** — 所有 Table 及欄位 render 內字體統一 +2（9→11、10→12、11→13、12→14、14→16）；Table `style={{ fontSize }}` 同步調整

## [1.57.37] - 2026-05-06

### Added
- **`hotel/overview` B/C/D TAB 類別圖例加入計算公式說明 Tooltip** — 每個工作類別（現場報修／上級交辦／緊急事件／例行維護／每日巡檢）旁加 ⓘ，hover 顯示來源模組（中英文）、資料口徑、欄位說明；D. 每年累計另保留「ⓘ 累計說明」；`HOTEL_5CAT_TOOLTIPS` 常數以 `React.createElement` 定義避免模組層 JSX 解析問題

## [1.57.36] - 2026-05-06

### Fixed
- **`hotel/overview` 飯店週期保養案件數口徑修正** — B/C TAB 的「飯店週期保養」案件數改用與 `hotel/periodic-maintenance` TAB=每月維護「本月週期保養項目數」相同邏輯：frequency 在月維護關鍵字集合（月/每月/月維護/Monthly/monthly）+ exec_months 過濾 + `scheduled_date` 重組完整日期後確認在目標月份；後端加 `import json`、`PM_MONTHLY_FREQ` 常數；日/月兩支 API 同步修正；2026/04 飯店週期保養案件數應回傳 0
- **`hotel/overview` B TAB IHG 案件數 cases_total 口徑修正** — `get_hotel_daily_hours` 新增 `ihg_month_rooms` set 追蹤本月不重複房號；`cases_total` 改用 `len(ihg_month_rooms)` 取代 `sum(day_c)`；TOTAL row 的 `cases_total` 改為各列 `cases_total` 加總（含修正後的 IHG 值）；確保 B TAB 合計與 C/D TAB 口徑一致（2026/04 = 69）

## [1.57.35] - 2026-05-06

### Fixed
- **`hotel/overview` 現場報修案件數口徑修正** — 從「有 completed_at → completed_at」改為正確的 `_stat_year/_stat_month` 口徑：`is_completed(status) AND completed_at is not None → completed_at`；否則 `occurred_at`（與工務部 Tab 一致）；import `is_completed as _repair_is_completed` from `dazhi_repair_service`；日/月兩支 API 同步修正

## [1.57.34] - 2026-05-06

### Changed
- **`hotel/overview` B/C/D TAB 改顯示案件數** — 後端 `hotel_overview.py` 新增 `cases_bucket` 平行統計（`/daily-hours`、`/monthly-hours` 各 row 加 `cases: list[int]`、`cases_total: int`）；口徑：現場報修用 TAB 3.1（有 completed_at → completed_at，否則 occurred_at）、每日巡檢＝批次數、保全巡檢＝批次數、IHG 每月＝不重複房號數、週期保養＝工項數；前端 `hotelOverview.ts` 介面加 `cases/cases_total`；`buildDailyCols`/`buildMonthlyCols` 改用 `row.cases` 顯示整數（0→'—'，無小數）；B/C/D TAB 表格標題改為「案件數」

## [1.57.33] - 2026-05-06

### Changed
- **`hotel/overview` 飯店管理 Dashboard 調整** — Placeholder 卡片「商場主管交辦/商場緊急事件」改為「飯店主管交辦/飯店緊急事件」（顯示文字修正，不影響路由）；新增「D. 每年累計」TAB（選年份 → 顯示 12 個月 Running Total 累計工時，沿用 `fetchHotelMonthlyHours`，前端計算 toCumulative，零新增 API）；原「D. 人員工時%」移除 D. 前綴改為「人員工時%」；TAB 順序：B. 每日累計 → C. 每月累計 → D. 每年累計 → 人員工時% → 人員排名

---

## [1.57.32] - 2026-05-06

### Changed
- **`mall/full-building-maintenance` 同步商場例行維護 SPEC 規格** — 後端 `_calc_year_matrix()` / `_calc_period_stats_core()` 加 `frequency_type` 頻率過濾（monthly/quarterly/yearly）；新增 `/period-stats/year-matrix/items` 矩陣明細端點與 `/items/catalog` 保養項目目錄端點；前端矩陣欄位標籤更新（「截至上月底累計未結案數」/「其中本月已結案數」加?Tooltip）；三個統計 TAB 矩陣移至頂部；矩陣數字可點擊開 `MatrixDetailModal`（含 Ragic 連結）；各 TAB 增「保養項目」按鈕開 `CatalogModal`；字體全面放大至 18px；欄寬擴大（label 310、月份 90、合計 100）

---

## [1.57.31] - 2026-05-06

### Fixed
- **`mall/periodic-maintenance` `METRIC_LABELS` 標籤通用化** — `MatrixDetailModal` 標題中 `period_total` 改為「本期應完成總數」、`period_completed` 改為「本期已完成」（去除月份特定的「本月」字眼，與 SPEC 第 8 節一致）

---

## [1.57.30] - 2026-05-06

### Changed
- **`mall/periodic-maintenance` 同步飯店例行維護 v1.57.25–v1.57.29 規格** — 後端 `_calc_year_matrix()` / `_calc_period_stats_core()` 加 `frequency_type` 頻率過濾（monthly/quarterly/yearly）；新增 `/period-stats/year-matrix/items` 矩陣明細端點與 `/items/catalog` 保養項目目錄端點；前端矩陣欄位標籤更新（「截至上月底累計未結案數」/「其中本月已結案數」加?Tooltip）；三個統計 TAB 矩陣移至頂部；矩陣數字可點擊開 `MatrixDetailModal`（含 Ragic 連結）；各 TAB 增「保養項目」按鈕開 `CatalogModal`；字體全面放大至 18px；欄寬擴大（label 310、月份 90、合計 100）

---

## [1.57.29] - 2026-05-06

### Changed
- **`hotel/periodic-maintenance` 年度矩陣總表字體全面放大 3 級** — `YearMatrixTable` 內所有字體：一般 cell/label/rate/number 12px→18px、備註文字 11px→17px；`?` badge 11→12px（圓圈 16→18px）；label 欄寬 260→310、月份欄寬 75→90、合計欄寬 80→100；月份表頭與合計標題加 `fontSize: 18`；商場 SPEC 第 6 節同步

---

## [1.57.28] - 2026-05-06

### Changed
- **`hotel/periodic-maintenance` 矩陣表字體統一 + 移除 ①② 前綴** — `MATRIX_METRICS` 的 `prev_carry_over` 改為「截至上月底累計未結案數」、`prev_resolved_in_period` 改為「其中本月已結案數」（去除 ①②）；label 欄 render 移除 `isHighlight` 分支，全列統一 `fontSize: 12`；`METRIC_LABELS` 同步更新；商場 SPEC 第 5、6、8 節同步修正

---

## [1.57.27] - 2026-05-06

### Changed
- **`hotel/periodic-maintenance` 三個 TAB 矩陣統一移至頂部** — 每季/每年 TAB 的 `YearMatrixTable` 從底部「全年矩陣總覽」區塊移至年度選擇器正下方（與每月 TAB 對齊）；每季底部 Divider「全年矩陣總覽（每季維護）」移除，改為頂部直接呈現；每年底部同樣調整；每年 TAB 重新整理按鈕改為同時觸發 `loadYearlyMatrix()` + `loadYearlyStats()`；鑽取區塊加 Divider「季度鑽取」/「年度鑽取」區隔；三個 TAB 字體一致（共用同一 `YearMatrixTable` 元件）；商場 SPEC 第 7 節同步更新

---

## [1.57.26] - 2026-05-06

### Changed
- **`hotel/periodic-maintenance` 模組更名** — 導覽列標籤由「1. 飯店週期保養表」改為「飯店例行維護」（`navLabels.ts`）；頁面內卡片標題「飯店週期保養每日狀況」改為「飯店例行維護每日狀況」
- **年度矩陣欄位標籤更新** — `prev_carry_over` 改為「①截至上月底累計未結案數」、`prev_resolved_in_period` 改為「②其中本月已結案數」；兩欄各新增藍色圓形「?」Tooltip 說明計算方式；Label 欄字體從 12px 放大為 15px（highlight 行）；Label 欄寬從 230 擴為 260
- **各 TAB 新增「保養項目」按鈕** — 每月／每季／每年三個 TAB 的年度選擇器旁各增加「保養項目」按鈕（紫色漸層 `#667eea→#764ba2`，ToolOutlined 圖示）；點擊後開啟 `CatalogModal` 顯示對應頻率的保養項目清單（類別/頻率/保養項目/區域位置/執行月份/預估工時）

### Added
- **後端新增 `GET /api/v1/periodic-maintenance/items/catalog`** — 依 `frequency_type`（monthly/quarterly/yearly）篩選，回傳去重後的保養項目清單（seq_no/category/frequency/task_name/location/estimated_minutes/exec_months_raw）
- **前端新增 `CatalogModal` 元件** — 顯示對應頻率的保養項目清單，支援分頁（每頁 15 項），Spin 載入動畫
- **API 函數新增 `fetchPMCatalog`** — `periodicMaintenance.ts` 新增 `PMCatalogItem`、`PMCatalogResponse` 型別及 `fetchPMCatalog(frequency_type?)` 函數

---

## [1.57.25] - 2026-05-06

### Changed
- **`hotel/periodic-maintenance` 每月／每季／每年 TAB 依頻率分類計算** — 後端 `_calc_year_matrix()` / `_calc_period_stats_core()` 加入 `frequency_type` 參數（monthly/quarterly/yearly），對 `PeriodicMaintenanceItem.frequency` 欄位進行關鍵字比對過濾（月/每月/月維護/Monthly；季/每季/季維護/Quarterly；年/每年/年維護/Annual/Yearly）；`GET /period-stats/year-matrix` 及 `GET /period-stats` 端點新增 `frequency_type` query param；新增 `GET /period-stats/year-matrix/items` 端點（params: year/month/metric/frequency_type），供矩陣數字點擊查詢對應明細；前端三個 TAB 傳入對應 `frequency_type`；`YearMatrixTable` 新增 `frequencyType` / `onCellClick` props，可點擊數字欄位（藍色底線）觸發 `MatrixDetailModal`（顯示：類別/保養項目/頻率/批次月份/排定日期/完成時間/狀態/執行人員/未完成原因/Ragic 連結）；每季維護 TAB 加入年度矩陣總表（frequency=季）；每年維護 TAB 加入年度矩陣總表（frequency=年）

---

## [1.57.22] - 2026-05-05

### Fixed
- **`dazhi-repair/dashboard` 報修類型分布口徑修正** — Dashboard KPI Card「報修類型分布」改用與工務部 Tab 相同的 `filter_cases`（`_stat_year/_stat_month`）口徑取代原本的 `this_month_cases`（`occ_year/occ_month` + 上月未結）；輸出依 `REPAIR_TYPE_ORDER` 排序，與 Tab 3.3 報修類型一致

---

## [1.57.24] - 2026-05-05

### Fixed
- **`security/dashboard` 每日巡檢表 TAB 篩選器修正** — 由全日期 DatePicker（YYYY/MM/DD）改為月份 DatePicker（picker="month"，YYYY/MM）；`yearMonth` state 取代 `inspectionDate`；API 呼叫不傳 `inspection_date`（整月合併）；空資料 Alert 訊息改為「YYYY年M月 尚無巡檢資料」

---

## [1.57.23] - 2026-05-05

### Added
- **`security/dashboard` 新增「每日巡檢表」TAB** — 後端新增 `security_patrol_daily_template.py`（83 列 5 樓層：1~10F/4F/1F~3F/1F/B1F~B4F，7 source_tab，來源 #2.4保全-每日巡檢表.xlsx）+ `security_patrol_daily_builder.py`（查詢 SecurityPatrolBatch/Item，精確+模糊比對 item_name，多 batch 合併）+ `GET /dashboard/daily-form`；前端 `SecurityDailyFormTab`（DatePicker 單日篩選、floor/item rowSpan 合併、異常紅底、有資料/空資料 Alert、獨立同步按鈕）；OUTER_TABS 插在 Dashboard 後第二位，CalendarOutlined 圖示

---

## [1.57.21] - 2026-05-05

### Added
- **`full-building-inspection` 新增「每日巡檢表」TAB** — 後端新增 `full_building_inspection_template.py`（82 列 4 樓層：RF/B1F/B2F/B4F，來源 #2.3整棟-每日巡檢表.xlsx）+ `GET /daily-form`（模板結構，matched=False，待本地同步接通後填充）；前端 `FullBuildingDailyFormTab`（DatePicker 單日篩選、floor/item rowSpan 合併、異常紅底、底部標準時間摘要 80 分鐘）；TAB 插在 Dashboard 後、RF 巡檢前

---

## [1.57.20] - 2026-05-05

### Added
- **`full-building-inspection/dashboard` Dashboard 月曆格** — 後端新增 `GET /dashboard/calendar`（4 樓層 RF/B4F/B2F/B1F × 逐日空結構，待本地同步接通後填充真實巡檢狀態）；前端 `SummaryTabContent` 新增 `calRows/calMaxDay` state，`loadSummary` 改為 `Promise.all` 平行載入 calendar（`.catch(() => null)` 不阻斷主流程）；Alert 下方加 `MonthlyCalendarGrid` Card，rowHeaderLabel="樓層"

---

## [1.57.19] - 2026-05-05

### Added
- **`security/dashboard` Dashboard 月曆格** — 後端新增 `GET /security/dashboard/calendar`（2 次 DB 查詢，7 個巡檢表 × 逐日完成率/異常/待處理）；前端 `SecurityDashboard/index.tsx` 新增 `calRows/calMaxDay` state，`loadAll` 兩個分支（單日/全月）皆以 `Promise.all` 平行載入 calendar（`.catch(() => null)` 不阻斷主流程）；DashboardContent 末尾加 `MonthlyCalendarGrid` Card，rowHeaderLabel="巡檢表"

---

## [1.57.19] - 2026-05-05

### Changed
- **`hotel/ihg-room-maintenance` 矩陣表字體放大 2 級** — 表格 `size` 由 `small` 改 `middle`；整體 fontSize 12→14；表頭 11→13、副文字 9→11；房號數字 13→15；樓層文字 10→12；格子內計數 9→11

---

## [1.57.18] - 2026-05-05

### Added
- **`hotel/ihg-room-maintenance` KPI 卡片點擊明細** — 全年應保養/已完成/異常/待保養卡片加入 `onClick`（完成率不可點擊）；點擊後右側 Drawer 顯示對應狀態的房號×月份清單（房號、月份、狀態Tag、正/完/維/未計數、保養日期、完成日期、保養人員、查看按鈕跳轉到保養明細）；每頁 20 筆分頁

### Fixed
- **`hotel/ihg-room-maintenance` KPI 數字與明細筆數不一致** — `/stats` 端點改為先對 `(room_no, maint_month)` 去重（後者覆蓋前者，與矩陣表行為一致），排除同一房號同月份存在多筆 Ragic 記錄時重複計數的問題

---

## [1.57.17] - 2026-05-05

### Changed
- **`hotel/ihg-room-maintenance` 固定規範房號清單** — router 新增 `CANONICAL_ROOMS`（149 間：5F×28、6F×28、7F×28、8F×27、9F×21、10F×17）；矩陣表以規範清單為基礎初始化，無資料的房號顯示空列、Ragic 資料中不在清單內的房號一律排除；`/stats`、`/records` 端點同步套用清單過濾

---

## [1.57.16] - 2026-05-05

### Added
- **`mall/full-building-maintenance` Dashboard 新增月曆格** — 後端新增 `GET /api/v1/mall/full-building-maintenance/calendar?year=&month=`（類別 × 日，6 類別：水電/空調/照明/消防/申報/整體，依 `scheduled_date` MM/DD 推算日期）；`loadDashboard` 改為 `Promise.all` 平行載入（calendar 失敗不阻斷 stats）；Dashboard 底部新增「全棟例行維護排程狀況」月曆格 Card（`rowHeaderLabel="保養類別"`）

---

## [1.57.15] - 2026-05-05

### Added
- **`mall/full-building-maintenance` 新增「每月保養表」TAB** — 插入第二 TAB（key=`form`，Dashboard 後）；獨立 `formYear`/`formMonth` state + `loadFormItems` useCallback（`fetchFullBldgPMBatches` 找批次 → `fetchFullBldgPMBatchDetail`）；類別 rowSpan 分組（水電/空調/照明/消防/申報/整體）；欄位：序號/類別/頻率/執行月份/項目+區域/預估(分)/排定日期+人員/執行人員/狀態Tag/備註；異常列 #fff1f0，非本月列 #bbb；`handleSync` 時若在此 TAB 一併重刷

---

## [1.57.14] - 2026-05-05

### Added
- **`mall-facility-inspection` 新增「每日巡檢表」TAB** — 後端新增 `GET /api/v1/mall-facility-inspection/daily-form?year=&month=&inspection_date=`（整合 `mall_daily_inspection_builder.build_mall_daily_inspection_table`）；前端插入第二 TAB（key=`daily-form`），直接複用 `MallDailyInspectionFormTab` 元件（獨立年/月/日期篩選、rowSpan 分組、異常列底色 #fff1f0）；`VALID_TABS` 新增 `daily-form`

---

## [1.57.13] - 2026-05-05

### Added
- **`mall-facility-inspection` Dashboard 新增月曆格** — 後端新增 `GET /api/v1/mall-facility-inspection/daily-calendar?year=&month=`（5 樓層 × 日期，依 `MallFIBatch` + `MallFIItem` 計算每日 completion_rate/abnormal/pending）；前端 `SummaryTabContent` 新增 `calRows/calMaxDay` state，`loadSummary` 改為 `Promise.all` 平行載入（calendar 失敗不阻斷主統計）；Dashboard 底部新增「商場工務每日巡檢狀況」月曆格 Card，`rowHeaderLabel="巡檢區域"`

---

## [1.57.12] - 2026-05-05

### Changed
- **`hotel/periodic-maintenance` 每月保養表 TAB 加獨立年/月篩選** — 移除舊的「月份跟隨 Dashboard」設計；TAB 頂部新增獨立年份 + 月份 Select 及「重新整理」按鈕；`loadFormItems` 改為先呼叫 `fetchPMBatches(year)` 找對應批次，再呼叫 `fetchPMBatchDetail`；空批次訊息改為顯示動態年月；同步 Ragic 時若在 form TAB 也一併重刷

---

## [1.57.11] - 2026-05-05

### Added
- **`hotel/periodic-maintenance` 新增 TAB「每月保養表」** — 在 Dashboard 後插入第二個 TAB；資料來源：現有 `fetchPMBatchDetail(batch_id, {currentMonthOnly: true})`；欄位：序號/類別（rowSpan 分組）/頻率/項目+區域/預估(分)/排定日期/排定人員/執行人員/狀態/備註；異常項目底色淺紅；月份跟隨 Dashboard 選擇器；空批次時顯示提示 Alert
- **`docs/DEV_PATTERNS.md` 新增「模組開發三必要條件」** — 每次開發新增模組/TAB 必須提供：中英文名稱+路徑、對應 Excel 表、TAB 順序（Dashboard→保養/巡檢表→統計→批次清單）；新增模組命名對照表（6 個現有模組）；TAB 順序規範章節

---

## [1.57.10] - 2026-05-05

### Added
- **`MonthlyCalendarGrid` 可重用 React 元件** — 抽取 `frontend/src/components/MonthlyCalendarGrid.tsx`；標準化月曆格介面（`CalendarRow / CalendarCellData`）；預設渲染：✓ 綠（100%）/ ⚠ 紅（異常或待處理）/ 百分比 藍（部分完成）/ — 灰（無資料）；今日深藍、週末紫色；圖例底部自動顯示；`hotel/daily-inspection` Dashboard 改用此元件
- **`hotel/periodic-maintenance` Dashboard 新增月曆格** — 後端新增 `GET /periodic-maintenance/calendar?year=&month=`（依類別 × 日期：水電/空調/機修/裝修/弱電 固定 5 類 + 其他）；前端 `fetchPMCalendar` API 函式 + `PMCalendarResponse` 型別；Dashboard `loadDashboard` 平行載入月曆資料；新增「飯店週期保養每日狀況」月曆格 Card（保養類別 × 日期，格內顯示完成率/逾期/進行中）
- **`mall/periodic-maintenance` Dashboard 新增月曆格** — 複用現有 `GET /mall-facility-inspection/daily-calendar` endpoint；Dashboard `loadDashboard` 平行載入；新增「商場工務每日巡檢狀況」月曆格 Card
- **`docs/DEV_PATTERNS.md` 開發規範** — 標準化「月曆格功能」開發 SOP：後端 endpoint 規格模板、Schema 範例、前端 API 型別定義、MonthlyCalendarGrid 整合步驟，含 checklist 與常見錯誤

---

## [1.57.9] - 2026-05-05

### Added
- **`mall/periodic-maintenance` 新增 TAB「每日巡檢表」** — 新增 `mall_daily_inspection_template.py`（41 列 5 樓層模板）+ `mall_daily_inspection_builder.py`（`build_mall_daily_inspection_table` 跨 Sheet 比對）+ 後端 `GET /daily-form` 及 `GET /daily-calendar` endpoint；前端新增 `MallDailyInspectionFormTab.tsx`（掛載自動載入當月、YYYY+M+DatePicker 篩選、rowSpan 合併、異常紅底、未巡檢黃底、底部顯示 早/晚班時間與 實際/標準 總巡檢時間）；TAB 插入 Dashboard 與每月維護之間；`mallFacilityInspection.ts` 新增完整型別定義與 fetch 函式

---

## [1.57.8] - 2026-05-05

### Fixed
- **每日巡檢表 TAB 自動載入當月資料** — 元件掛載時自動查詢（不再需要手動按「查詢」），`queried` 狀態移至 `finally` 保證必設
- **`時間(分)` 欄位改為計算值** — 後端 `daily_inspection_builder` 新增 `actual_minutes` 欄位（各 Sheet 所有 batch 的 start_time → end_time 加總），有實際巡檢資料時顯示計算時間；無資料時顯示模板標準時間；滑鼠移入顯示 tooltip 說明
- **底部總時標籤隨資料切換** — 有實際資料時顯示「實際總巡檢時間」，無資料時顯示「標準總巡檢時間」；去除錯誤的 Set 去重邏輯，改依 source_tab 去重加總實際時間
- **Dashboard 每日月曆格移除水平捲軸** — `table-layout: fixed` + `width: 100%` + 首欄 `12%` 寬；31 個日期欄自動分配剩餘寬度；僅在畫面真的不夠時才出現水平捲軸

---

## [1.57.7] - 2026-05-05

### Changed
- **`hotel/daily-inspection` Dashboard 改為純月份模式** — 移除「單日 / 全月」Segmented 切換，固定顯示當月彙整，並新增 1~31 日每日巡檢狀況月曆格（各 Sheet × 各日：完成率 / 異常數 / 待處理數）
  - 後端新增 `GET /daily-calendar?year=&month=` endpoint：回傳 `max_day` + `sheets[].daily{day_str: {has_record, completion_rate, abnormal_count, pending_count}}`
  - 後端 `GET /daily-form` endpoint：新增 `inspection_date` 選填參數（YYYY/MM/DD），填入時只取該日 batch；回傳 `has_data_today`（bool）
  - 後端 `daily_inspection_builder.py`：`build_daily_inspection_table()` 新增 `inspection_date` 參數
  - 前端 `index.tsx`：`SummaryTabContent` 改用 `Promise.all([fetchHotelDailyMonthlyDashboard, fetchHotelDailyCalendar])` 平行載入；新增 `MonthlyCalendar` 元件（純 HTML table，今日深藍、週末紫色、格內顯示 ✓/⚠/百分比/—）
  - 前端 `DailyInspectionFormTab.tsx`：新增 `DatePicker`（可選填，限制在已選年月內）；查詢單日無資料時顯示黃色 Alert；單日有資料時顯示綠色 Banner
  - 前端 `api/hotelDailyInspection.ts`：新增 `DailyCalendarDay / DailyCalendarSheet / DailyCalendarResponse` 型別 + `fetchHotelDailyCalendar()` 函式
  - TAB 順序調整：Dashboard → 每日巡檢表 → RF 巡檢 → 4F~10F 巡檢 → 4F 巡檢 → 2F 巡檢 → 1F 巡檢

---

## [1.57.6] - 2026-05-05

### Added
- **`hotel/daily-inspection` 新增 TAB：「每日巡檢表」** — 將 RF / 4F~10F / 4F / 2F / 1F 五個巡檢 TAB 資料彙整為標準表格（來源：`hoteldaily-inspection.xlsx`）
  - 後端新增 `app/services/daily_inspection_template.py`：78 列標準模板常數，涵蓋 RF/4~10F/4F/2F/1F 共 13 個設備項目，含 floor/item/check_content/result_options/minutes/source_tab/rowSpan 計算
  - 後端新增 `app/services/daily_inspection_builder.py`：`build_daily_inspection_table(year, month, db)` 從各 Sheet 比對資料，支援精確 + 模糊 item_name 比對、多 batch 合併（inspector 逗號分隔、異常說明帶日期前綴）
  - 後端 `hotel_daily_inspection.py`：新增 `GET /daily-form?year=&month=` endpoint，回傳帶比對結果的完整模板列清單
  - 前端新增 `HotelDailyInspection/DailyInspectionFormTab.tsx`：YYYY + M 篩選、rowSpan 合併欄（樓層/項目/時間）、異常列紅底、未巡檢列黃底、底部顯示早晚班巡檢時間
  - 前端 `HotelDailyInspection/index.tsx`：新增 TAB（key: `daily-form`，label: `每日巡檢表`），`VALID_TABS` 加入 `daily-form`
  - 前端 `api/hotelDailyInspection.ts`：新增 `DailyFormRow` / `DailyFormResponse` 型別 + `fetchHotelDailyForm()` API 函式
  - 三項設定確認已完備：menu-config（沿用 `/hotel/daily-inspection` 路由）、roles（`hotel_daily_inspection_view` 已涵蓋）、ragic-app-directory（items 215-219 已記錄）

---

## [1.57.5] - 2026-05-05

### Added
- **`mall/periodic-maintenance` 新增每月／每季／每年三個統計 TAB** — 與 `hotel/periodic-maintenance` 及 `mall/full-building-maintenance` 版型完全相同
  - 後端 `mall_periodic_maintenance.py`：新增 import（`calendar.monthrange`、`List`、`PMPeriodStats / PMSubPeriodBreakdown / PMIncompleteItem / PMYearMatrix / PMYearMatrixMonth`）
  - 後端新增 6 個輔助函式 + 2 個端點（`year-matrix` 在前）：`GET /period-stats/year-matrix`、`GET /period-stats`（period_type=month|quarter|year），使用 `MallPeriodicMaintenanceBatch/MallPeriodicMaintenanceItem`
  - 前端 `mallPeriodicMaintenance.ts`：新增 `fetchMallPMPeriodStats()` / `fetchMallPMYearMatrix()`
  - 前端 `MallPeriodicMaintenance/index.tsx`：新增 helper 元件（`fmtRate`、`PeriodKpiCards`、`SubBreakdownTable`、`IncompleteTable`、`QuarterSelectorCards`、`YearMatrixTable`）+ 三個 TAB；Tab 最終順序：Dashboard → 每月維護 → 每季維護 → 每年維護 → 批次清單

---

## [1.57.4] - 2026-05-05

### Added
- **`mall/full-building-maintenance` 新增每月／每季／每年三個統計 TAB** — 與 `hotel/periodic-maintenance` 版型完全相同
  - 後端 `full_building_maintenance.py`：新增 import（`calendar.monthrange`、`List`）+ 新增 schema import（`PMPeriodStats / PMSubPeriodBreakdown / PMIncompleteItem / PMYearMatrix / PMYearMatrixMonth`）
  - 後端新增 6 個輔助函式：`_MONTH_LABELS_ZH`、`_reconstruct_full_date()`、`_parse_end_date()`、`_get_period_bounds()`、`_calc_period_stats_core()`（使用 `FullBldgPMBatch/FullBldgPMItem`）、`_calc_sub_breakdown()`、`_calc_year_matrix()`
  - 後端新增 2 個端點（`year-matrix` 定義在 `period-stats` 之前以避免路由衝突）：`GET /period-stats/year-matrix`、`GET /period-stats`（period_type=month|quarter|year）
  - 前端 `fullBuildingMaintenance.ts`：新增 `fetchFullBldgPMPeriodStats()` / `fetchFullBldgPMYearMatrix()`
  - 前端 `FullBuildingMaintenance/index.tsx`：新增 `fmtRate`、`PeriodKpiCards`、`SubBreakdownTable`、`IncompleteTable`、`QuarterSelectorCards`、`YearMatrixTable` helper 元件；三個 TAB（每月維護 / 每季維護 / 每年維護）整合進 Tabs；Tab 最終順序：Dashboard → 每月維護 → 每季維護 → 每年維護 → 批次清單

---

## [1.57.3] - 2026-05-04

### Added
- **每月維護年度矩陣總表新增「合計」欄**
  - `frontend/src/pages/PeriodicMaintenance/index.tsx`：`YearMatrixTable` 在 12 個月欄右側固定一欄「合計」（`fixed: 'right'`，藍灰底色 `#f6f8fc` + 左側藍線分隔）
  - 數字指標（`prev_carry_over / prev_resolved_in_period / period_total / period_completed`）：12 個月加總
  - 完成率指標（`carry_over_rate / period_rate`）：從加總數重新計算（`resolved/carry_over`、`completed/total`），不做月平均；分母為 0 顯示 N/A
  - 備註欄（`incomplete_notes`）：顯示 `—`
  - 合計欄數字以粗體（`fontWeight: 600`）顯示；複用共用 `renderCell` 函式避免重複邏輯

---

## [1.57.2] - 2026-05-04

### Changed
- **每季維護 TAB 季度選擇改為視覺卡片（Q1/Q2/Q3/Q4）**
  - `frontend/src/pages/PeriodicMaintenance/index.tsx`：移除季度下拉選單，改以 4 欄 `QuarterSelectorCards` 呈現；每張卡片顯示 Q 標籤、3個月份、加總項目數 / 完成數 / 完成率；點擊卡片高亮（藍框 `2px solid #4BA8E8`）並觸發下方詳細統計載入
  - 新增 `QuarterSummary` interface + `deriveQuarterSummaries(matrix)` 函式：從 PMYearMatrix 加總對應 3 個月的 `period_total / period_completed`，動態計算完成率
  - 新增獨立 `quarterlyMatrixData / quarterlyMatrixLoading` state 與 `loadQuarterlyMatrix` callback，與每月矩陣資料相互獨立
  - Tab 最終順序：Dashboard → 每月維護 → 每季維護 → 每年維護 → 批次清單

---

## [1.57.1] - 2026-05-04

### Added
- **每月維護 TAB 新增年度矩陣總表（12個月橫軸 × 7指標縱軸）**
  - `backend/app/schemas/periodic_maintenance.py`：新增 `PMYearMatrixMonth`（單月指標）、`PMYearMatrix`（全年矩陣）schema
  - `backend/app/routers/periodic_maintenance.py`：新增 `_calc_year_matrix()`（一次 DB 查詢算完全年 12 個月，效率優於逐月呼叫）；新增端點 `GET /period-stats/year-matrix`（定義在 `/period-stats` 之前確保路由匹配優先）
  - `frontend/src/types/periodicMaintenance.ts`：新增 `PMYearMatrixMonth`、`PMYearMatrix` TypeScript interface
  - `frontend/src/api/periodicMaintenance.ts`：新增 `fetchPMYearMatrix(year?)` API 函式
  - `frontend/src/pages/PeriodicMaintenance/index.tsx`：新增 `MATRIX_METRICS` 指標定義陣列；新增 `YearMatrixTable` 元件（Ant Design Table 轉置呈現，完成率依閾值著色 ≥80%綠/≥50%橙/其他紅，未完成備註 Tooltip 展開）；MonthlyStatsTab 整合矩陣置頂（含載入狀態）+ Divider 分隔「單月鑽取」區塊；新增 `matrixData / matrixLoading` state 與 `loadYearMatrix` callback；`monthlyYear` 改變自動觸發矩陣重算

---

## [1.57.0] - 2026-05-04

### Added
- **`hotel/periodic-maintenance` 新增每月／每季／每年三個統計 TAB**
  - `backend/app/schemas/periodic_maintenance.py`：新增 `PMIncompleteItem`、`PMSubPeriodBreakdown`、`PMPeriodStats` schema
  - `backend/app/routers/periodic_maintenance.py`：新增共用計算輔助函式 `_reconstruct_full_date()`、`_parse_end_date()`、`_get_period_bounds()`、`_calc_period_stats_core()`、`_calc_sub_breakdown()`；新增端點 `GET /period-stats`（period_type=month|quarter|year，接受 year/month/quarter 參數）
  - `frontend/src/types/periodicMaintenance.ts`：新增 `PMIncompleteItem`、`PMSubPeriodBreakdown`、`PMPeriodStats` TypeScript interface
  - `frontend/src/api/periodicMaintenance.ts`：新增 `fetchPMPeriodStats()` API 函式
  - `frontend/src/pages/PeriodicMaintenance/index.tsx`：新增共用元件 `PeriodKpiCards`（六指標卡片）、`SubBreakdownTable`（子期間分布表）、`IncompleteTable`（未完成事項說明）；新增三個 Tab `MonthlyStatsTab`（每月）/ `QuarterlyStatsTab`（每季）/ `YearlyStatsTab`（每年）
- **統計公式**：上期累計未完成（表定日期 ≤ 上期末且截至上期末未完成）、累計完成率（本期結案 ÷ 上期未完成）、本期完成率（本期完成數 ÷ 本期項目數）；季 / 年完成率用總數計算，不做月均值；分母為 0 顯示 N/A
- **未完成事項說明**：僅列 `result_note` 非空的項目（備註為空不計算）

---

## [1.56.2] - 2026-05-04

### Removed
- **移除 `hotel/room-maintenance-detail` 在各 Dashboard / 分析模組的計算與呈現**
  - `backend/app/routers/hotel_overview.py`：移除 `RoomMaintenanceDetailRecord` import、`HOTEL_CATEGORIES` 中「客房保養管理」、daily/monthly/person 三支 API 的客房保養查詢區塊；來源由六項改為五項
  - `backend/app/routers/work_category_analysis.py`：移除 `RoomMaintenanceDetailRecord` import、`SOURCE_LABELS["hotel_room"]`、`_load_all()` 中房務保養查詢區塊、`_parse_sources("all")` 中的 `hotel_room`、`_build_kpi()` 中 source_breakdown 的 `hotel_room`、`_get_last_sync_at()` 中房務保養 synced_at 查詢；資料來源由四合一改為三合一
  - `frontend/src/pages/HotelMgmtDashboard/index.tsx`：移除 `fetchMaintenanceStats` import、`MaintenanceStatsResponse` 型別、`roomDetailStats` state、`adaptRoomDetail()` adapter、sources 陣列中 room_detail 項目；`SOURCE_COLORS` / `HOTEL_SOURCE_ICONS` / `HOTEL_SOURCE_ROUTES` 移除 room_detail key；PIE_COLORS 由 6 色調整為 5 色
  - `frontend/src/pages/ExecDashboard/index.tsx`：`SRC_OPTIONS` 移除 `{ value: 'hotel_room', label: '房務保養' }`
  - `frontend/src/pages/WorkCategoryAnalysis/index.tsx`：`SOURCE_OPTIONS` 移除 `{ value: 'hotel_room', label: '房務保養' }`
- **注意**：`hotel/room-maintenance-detail` 獨立頁面模組（Model / Router / Sync Service / 前端頁面）完整保留，僅移除其在跨模組彙整的顯示

---

## [1.56.1] - 2026-05-04

### Fixed
- **選單圖示「無圖示」設定不生效**（`MainLayout.tsx` `applyMenuConfig`）
  - `buildItem`：改為明確設 `icon: null`（原為省略 icon 屬性），確保 Ant Design Menu 真正隱藏圖示
  - Base L1 / L2（含 children）/ L2 leaf：統一改用 `icon: xxx !== undefined ? xxx : null` 覆寫 base icon
  - `movedHere` path：補上 `resolveIcon` 呼叫，原本完全未套用 DB icon_key 設定
  - `customL1` path：原本 icon 硬編碼為 `<FileTextOutlined />`，現改為讀取 `cfg.icon_key` 並套用 `resolveIcon`

---

## [1.56.0] - 2026-05-04

### Added
- **員工操作手冊知識包匯出**（`/settings/employee-manual-export`）
  - 後端 `services/employee_manual_export_service.py`：8 個模組的操作知識內容、7 種文件產生器（員工操作手冊 / 主管快速導覽 / FAQ / 教育訓練講稿 / 語音教學腳本 / 新人入門教學 / 異常狀況處理），全部純 Python 產生，不消耗 AI token
  - 後端 `routers/employee_manual_export.py`：4 個端點（模組清單 / 產生 / 狀態查詢 / ZIP 下載）
  - 後端 `schemas/employee_manual_export.py`：Request/Response 型別定義
  - 前端 `pages/Settings/EmployeeManualExport/index.tsx`：三步驟操作介面（選模組 → 選文件種類 → 下載 ZIP）+ NotebookLM 使用提示詞一鍵複製
  - 前端 `api/employeeManualExport.ts`、`types/employeeManualExport.ts`
  - 新增 3 個 permission key：`employee_manual_export_view`、`employee_manual_export_generate`、`employee_manual_export_admin`
  - 新增文件目錄 `docs/system_inventory/`：`feature_inventory.md`（功能模組清單）、`route_feature_map.md`（路由對照表）
  - 輸出路徑：`backend/exports/employee_manuals/{module_key}/`，可打包成 ZIP 下載上傳 NotebookLM

---

## [1.55.3] - 2026-05-04

### Changed
- **決策駕駛艙（DecisionCockpit）全模組術語統一**
  - 「大直工務部」→「飯店工務」；「樂群工務報修」→「商場工務」
  - 涉及 7 個檔案：`TabRepair.tsx`、`TabOverview.tsx`、`TabHotel.tsx`、`TabMall.tsx`、`TabRiskRadar.tsx`、`TabBriefing.tsx`、`TabDataQuality.tsx`

---

## [1.55.2] - 2026-05-03

### Added
- **知識庫 Graph View（路線 A — Portal 內建）**
  - 後端 `wiki_service.build_graph()`：計算 nodes（id / title / category / tags）+ edges（標籤重疊→虛線 / `[[連結]]`→實線）
  - 後端 `POST /api/v1/wiki/auto-link`：掃描所有文章，依標籤重疊與同分類自動在 body 加入「## 相關文章」`[[連結]]` 區塊（冪等，dry_run 預覽模式）
  - 後端 `GET /api/v1/wiki/graph`：回傳 `{ nodes, edges }` JSON
  - 前端 `api/wiki.ts`：新增 `fetchWikiGraph()`、`autoLinkArticles()` 及對應型別
  - 前端 `pages/Wiki/WikiGraph.tsx`：`@xyflow/react` 繪製力導向圖；自訂 `WikiArticleNode`（顏色區分 SOP / Dev、標籤 Tag、選取高亮）；SOP 左環形 / Dev 右環形佈局；`MiniMap`、`Controls`、圖例浮層；點節點 → 切回清單並開啟文章
  - 前端 `pages/Wiki/index.tsx`：Header 加 `Segmented`「清單 / 圖譜」切換；圖譜模式時搜尋列隱藏；同步 Dropdown 新增「自動補充 `[[連結]]`」選項

---

## [1.55.1] - 2026-05-03

### Added
- **知識庫 Obsidian 雙向同步**
  - 後端 `wiki_service.py`：`export_to_obsidian()`（DB → `docs/wiki/*.md`）、`import_from_obsidian()`（`.md` → DB）；以 `updated_at` 比較時間戳決定是否覆寫；import 時若 `.md` 無 `id` 則寫回新 id
  - 後端 `routers/wiki.py`：`POST /api/v1/wiki/export-obsidian`、`POST /api/v1/wiki/import-obsidian`
  - 前端 `api/wiki.ts`：`exportToObsidian()`、`importFromObsidian()`、`ObsidianSyncResult` interface
  - 前端 `pages/Wiki/index.tsx`：Header 加入「同步 Obsidian」Dropdown 按鈕（含 `ExportOutlined` / `ImportOutlined` 兩選項）；同步完成後顯示結果 Modal（新增/更新/跳過/錯誤明細）

### Fixed
- `wiki_service._wiki_dir()`：修正 `.parent` 呼叫次數（5 → 4），確保 `docs/wiki/` 路徑正確解析至 `portal/docs/wiki/`

---

## [1.55.0] - 2026-05-03

### Added
- **知識庫（LLM Wiki）— 全新功能 `/wiki`**
  - **後端**：
    - `backend/app/models/wiki.py`：`WikiArticle` ORM model（id / title / slug / body / summary / category / tags / author / is_published）
    - `backend/app/schemas/wiki.py`：Create / Update / Out / ListResponse / AskRequest / AskResponse Pydantic schemas
    - `backend/app/services/wiki_service.py`：CRUD + 關鍵字搜尋 + AI 問答（Anthropic Claude API）
    - `backend/app/routers/wiki.py`：`GET /api/v1/wiki/`（清單）、`GET /{id}`、`POST /`（新增）、`PATCH /{id}`（更新）、`DELETE /{id}`（刪除）、`POST /ask`（AI 問答）
    - `backend/app/services/wiki_seed.py`：首次啟動自動植入 15 篇範例文章（10 SOP + 5 Dev）
    - `backend/requirements.txt` 加入 `anthropic>=0.25.0`
    - `backend/.env` 加入 `ANTHROPIC_API_KEY=`（含說明註解）
    - `backend/app/core/config.py` 加入 `ANTHROPIC_API_KEY: str = ""`
  - **前端**：
    - `frontend/src/types/wiki.ts`：完整 TypeScript 型別定義
    - `frontend/src/api/wiki.ts`：fetchWikiArticles / fetchWikiArticle / createWikiArticle / updateWikiArticle / deleteWikiArticle / askWiki
    - `frontend/src/pages/Wiki/index.tsx`：三欄式 Layout（Header 分類 Tabs / 左側文章清單 / 右側 Markdown 瀏覽）+ 新增/編輯 Drawer + AI 問答浮動 Modal（對話紀錄 + 參考來源 Tag）+ 自製 `MarkdownRenderer`（支援標題、粗體、斜體、inline code、code block、列表、引用、分隔線）
    - Sidebar 新增「知識庫」選單項目（`ReadOutlined`）
    - Router 新增 `/wiki` 路由
    - `navLabels.ts` 新增 `wiki` 群組與 `wikiMain` 頁面常數

---

## [1.54.9] - 2026-05-03

### Added
- **決策駕駛艙 Phase 3~8 — 所有 TAB 完整實作**
  - **Phase 3 — B.飯店管理摘要 + C.商場管理摘要**
    - `TabHotel.tsx`：並行呼叫 6 來源 API；`SourceCard` 元件含完成率進度條 + 燈號 + 健康分數；飯店整體健康（6 來源等權平均）；部分計算支援
    - `TabMall.tsx`：4 工項 API + 2 灰燈（上級交辦 / 緊急事件）；商場整體健康分數；巡檢來源解析 `MallFIMonthlySheetSummary[]`
  - **Phase 4 — D.工務與報修 + E.人員工時與效率**
    - `TabRepair.tsx`：左右雙欄（大直 / 樂群）各含進度條 + KPI 格 + 12M 完成率折線圖（recharts）；工務整體健康（大直×0.60 + 樂群×0.40）
    - `TabPersonnel.tsx`：飯店 / 商場 Top-10 人員橫向 BarChart；飯店 / 商場月工時 12M 折線；明確標示「年度統計，不受月份篩選」
  - **Phase 5 — F.異常風險雷達 + G.趨勢分析**
    - `TabRiskRadar.tsx`：10 模組燈號矩陣 Table（完成率 / 逾期率 / 異常率 / 健康分數）；紅/黃/綠/灰燈統計摘要；行紅/黃底色；可排序
    - `TabTrend.tsx`：近 7/30 日巡檢完成率日度折線（Segmented 切換）+ 80% 目標參考線；飯店/商場月工時 LineChart + 當月標線
  - **Phase 6 — H.主管晨會摘要 + I.資料品質監控**
    - `TabBriefing.tsx`：規則式 5 章節文字生成（工務 / 客房保養 / 週期保養 / 商場維護 / 需關注事項）；`navigator.clipboard.writeText` 一鍵複製；`message.success` 反饋；資料來源就緒數 Tag
    - `TabDataQuality.tsx`：5 模組資料完整度 Table（總筆數 / 有狀態 / 有工時 / 完整度 Progress）；整體品質百分比大卡；完整度說明
  - **Phase 7 — 匯出報告**：移除 `disabled`；Tooltip 改為「列印 / 另存為 PDF」；onClick → `window.print()`
  - **Phase 8 — 後端權限**：`backend/app/routers/role_permissions.py` `PERMISSION_DEFINITIONS` 加入 `decision_cockpit_view`（「決策駕駛艙」，群組「一階選單」，置於首位）

---

## [1.54.1] - 2026-05-03

### Added
- **決策駕駛艙 Phase 2 — A. 決策總覽 實作**
  - `pages/DecisionCockpit/utils/healthScore.ts`：健康分數計算工具（`HEALTH_SCORE_WEIGHTS` / `HEALTH_THRESHOLDS` / `GROUP_WEIGHTS` / `REPAIR_WEIGHTS` 可調整常數；`calcHealthScore()` / `calcModuleHealth()` / `calcRepairHealth()` / `calcGroupHealth()` / `getTrafficLight()` 函式）
  - `tabs/TabOverview.tsx`：完整 Phase 2 UI — `Promise.allSettled` 並行呼叫 3 支 API（`/dashboard/kpi` / `/luqun-repair/dashboard` / `/dazhi-repair/dashboard`）；集團健康大圓 + 飯店（客房代理）/ 商場（灰燈 Phase 3）/ 工務三格子分數；工務 + 客房保養 KPI 彙整列（6 + 4 格）；規則式「主管最該注意的 5 件事」（逾期工務 / 待驗收 / 客房保養未完成 / 費用彙整 / 系統狀態）
  - 設計細節：`Promise.allSettled` 容錯（任一 API 失敗不影響其餘）；部分計算標示 `(部分計算)` Tooltip；灰燈模組顯示「資料準備中」；飯店 / 商場健康分數標示「Phase 3 接入」

---

## [1.54.0] - 2026-05-03

### Added
- **決策駕駛艙（Decision Cockpit）Phase 1 — 基礎框架建立**
  - 規劃文件：`docs/decision-cockpit/PLANNING.md`（模組架構/TAB 規格/API 清單/8 Phase 計劃）、`KPI_DATASOURCE_MAP.md`（各 KPI 來源對應表）、`HEALTH_SCORE_SPEC.md`（健康分數公式草案，含 configurable 常數）
  - `navLabels.ts`：新增 `decisionCockpit: '決策駕駛艙'`，維護紀錄補記
  - `MainLayout.tsx`：sidebar 新增「決策駕駛艙」一級選單（`RadarChartOutlined`，`permissionKey: 'decision_cockpit_view'`）
  - `router/index.tsx`：新增 `/decision-cockpit` 路由，以 `PermissionGuard(decision_cockpit_view)` 保護
  - `pages/DecisionCockpit/index.tsx`：主頁框架（月份選擇器 24 個月 / 重新整理按鈕 / 停用匯出按鈕 Phase 7 / 9 TAB 懶載入）
  - `pages/DecisionCockpit/tabs/Tab{Overview,Hotel,Mall,Repair,Personnel,RiskRadar,Trend,Briefing,DataQuality}.tsx`：9 個 TAB stub（佔位元件，標明各 TAB 計劃 Phase 與 API 來源）
  - 設計原則：不新增後端 API / 不使用 AI API / 無假資料 / tabProps `{ year, month, monthStr, refreshKey }` 統一介面

---

## [1.53.8] - 2026-05-03

### Changed
- **`mall/overview` Dashboard 版型對齊飯店版** — 年月 Select + 匯出 PowerPoint 按鈕移至頁面右上角 header Card；Tab A 篩選列簡化為僅保留「工務巡檢日期」DatePicker + 今日 + 全部重新整理

---

## [1.53.7] - 2026-05-03

### Added
- **`mall/overview` 匯出 PowerPoint** — 5 張投影片（封面/KPI 總覽/每日工時/每月工時/人員排名）
  - 後端 `mall_overview.py`：新增 Pydantic models `KpiSummaryIn / SourceCardIn / RepairCostsIn / MallPptxPayload`；`_build_mall_pptx()` 建立 5 張投影片（Slide 2 三層：5 KPI box / 2×4 來源卡 / 3 費用 box；Slide 3-5 自行查 DB）；`POST /mall/overview/export/pptx` endpoint；修復 `person-hours` 缺少 `person_totals` 欄位；修復檔尾字串截斷
  - 前端 `api/mallOverview.ts`：新增 `KpiSummaryPayload / SourceCardPayload / RepairCostsPayload / MallPptxPayload` 介面；新增 `exportMallOverviewPptx(year, month, payload)` POST + Blob 下載函式
  - 前端 `MallMgmtDashboard/index.tsx`：新增 `FilePptOutlined` 圖示；`exportLoading` 防重複點擊 state；匯出按鈕（月份為 0 時 disabled）；onClick 從 `summaryMap` + `kpi` 組裝完整 `MallPptxPayload`

---

## [1.53.6] - 2026-05-03

### Added
- **`hotel/overview` 匯出 PowerPoint — Slide 2 改為三層 KPI 總覽（方向 B）**
  - 後端 `hotel_overview.py`：新增 Pydantic models `KpiSummaryIn / SourceCardIn / RepairCostsIn / HotelPptxPayload`；新增 `_build_slide2_kpi()` 渲染三層：主管摘要（5 KPI box）/ 各來源本期狀態（2×4 來源卡含完成率 bar）/ 報修費用摘要（3 費用 box）；export endpoint 從 `GET` 改為 `POST`，接收前端 KPI payload；Slide 3–5 仍後端自行查 DB
  - 前端 `api/hotelOverview.ts`：新增 `KpiSummaryPayload / SourceCardPayload / RepairCostsPayload / HotelPptxPayload` 介面；`exportHotelOverviewPptx` 改為 POST + JSON body
  - 前端 `HotelMgmtDashboard/index.tsx`：按鈕 onClick 從 `sources` / `totalCases` / `dazhiData.kpi` 組裝完整 payload 後呼叫 export；新增 `FilePptOutlined` 圖示、`exportLoading` 防重複點擊

---

## [1.53.5] - 2026-05-03

### Added
- **飯店每日巡檢 Dashboard + 保全巡檢 Dashboard 加入「單日 / 全月」篩選模式** — Segmented 切換器讓使用者自由選擇查詢口徑
  - 前端 `HotelDailyInspection/index.tsx`：SummaryTabContent 新增 `viewMode` state；全月模式改呼叫既有 `fetchHotelDailyMonthlyDashboard`；KPI 標題「今日巡檢場次」→「本月巡檢場次」；Alert 訊息依模式切換
  - 前端 `SecurityDashboard/index.tsx`：DashboardContent 新增 Segmented 切換；全月模式呼叫 `fetchSecurityDashboardMonthlySummary` + issues（全月日期範圍）；近 7 日趨勢圖僅單日模式顯示；標題文字「今日」→「本月」隨模式切換
  - 前端 `api/securityPatrol.ts`：新增 `SecurityMonthlySummary` 型別 + `fetchSecurityDashboardMonthlySummary(year, month)` 函式

---

## [1.53.4] - 2026-05-03

### Fixed
- **`hotel/overview` KPI 各卡月份口徑全面修正** — 所有子模組統計改以選定年月為基準，消除「固定顯示今日 / 全年累計」問題
  - 後端 `room_maintenance_detail.py`：`/maintenance-stats` 新增 `year`/`month` Query params，統計基準改為傳入值（預設 today）
  - 後端 `ihg_room_maintenance.py`：`/stats` 新增 `month` 篩選；`total_scheduled` 改為 distinct `room_no` 計數；新增 `work_hours`（raw_json「工時計算」加總 ÷ 60）
  - 後端 `hotel_daily_inspection.py`：新增 `GET /dashboard/monthly-summary?year&month`（跨 Sheet 月份彙總）
  - 後端 `security_dashboard.py`：新增 `GET /monthly-summary?year&month`（跨 Sheet 月份彙總）
  - 前端 API 層：`fetchMaintenanceStats`/`fetchIHGStats` 加 year/month 參數；新增 `fetchHotelDailyMonthlyDashboard`/`fetchSecurityMonthlyDashboard`
  - 前端 `HotelMgmtDashboard/index.tsx`：所有 API 呼叫改傳 selectedYear/selectedMonth；每日巡檢 & 保全巡檢改用月份彙總端點；IHG 工時正確讀取；移除「整體完成率」圓餅卡；工務部「異常：」改為「未完成：」

---

## [1.53.3] - 2026-05-03

### Added
- **`hotel/periodic-maintenance` 同步 Ragic「工時計算」欄位，作為「保養時間」計算來源**
  - `periodic_maintenance.py` Model：新增 `ragic_work_minutes INTEGER NULLABLE`（對應 Ragic「工時計算」欄位）
  - `periodic_maintenance_sync.py`：新增 `CK_WORK_HOURS = "工時計算"`；`_ragic_item_to_model()` 讀取並存入 `ragic_work_minutes`；upsert 區塊同步更新此欄位
  - `periodic_maintenance.py` Router：`_calc_kpi()` 的 `actual_minutes` 改為優先使用 `ragic_work_minutes`，若 NULL 則 fallback 到 `_time_diff_minutes(start_time, end_time)`；`_item_to_out()` 補傳 `ragic_work_minutes`
  - `periodic_maintenance.py` Schema：`PMItemOut` 新增 `ragic_work_minutes: Optional[int] = None`
  - `main.py`：新增 `_migrate_pm_work_minutes()` 啟動時自動 ALTER TABLE

---

## [1.53.2] - 2026-05-03

### Added
- **`hotel/periodic-maintenance` Dashboard 新增「預估工時」和「保養時間」KPI 卡片**（比照 mall 模組）
  - 後端 `periodic_maintenance.py`：新增 `_TIME_FMTS` 常數與 `_time_diff_minutes()` 輔助函式；`_calc_kpi()` 補上 `actual_minutes` 計算（`start_time`~`end_time` 差值合計）
  - 前端 `PeriodicMaintenance/index.tsx`：KPI 卡片列改為 `Col flex={1}` 彈性排版；新增「預估工時（藍）」與「保養時間（綠）」兩張 Statistic 卡；移除進度條列的重複工時文字

---

## [1.53.1] - 2026-05-02

### Fixed
- **`dazhi-repair/dashboard` 計算口徑全面對齊 `luqun-repair/dashboard`**
  - `RepairCase` 新增 `occ_year`/`occ_month` 屬性（永遠等於 `occurred_at` 報修年月，供 Dashboard/報修統計專用）
  - `year`/`month` 改為正確統計口徑：已完成案件以 `completed_at` 年月為準，未完成以 `occurred_at` 年月為準（與 luqun 一致）
  - `_stat_year/_stat_month` 簡化：直接讀 `c.year/c.month`，移除重複的 `completed_at` 動態計算邏輯
  - `compute_dashboard`：`_this_month_new` 改用 `occ_year/occ_month` 避免跨月結案雙重計入
  - `compute_dashboard`：當月費用從 `this_month_cases`（含上月未結）改為獨立 `fee_month_cases`（`filter_cases` 口徑）
  - `compute_dashboard`：趨勢 `trend_12m` 改用 `occ_year/occ_month` 反映真實報修月份
  - `compute_repair_stats`：「截至上月底」/「截至本月底」累計基準改用 `occ_year/occ_month`；「本月報修項目數」改用 `occ_year/occ_month` 而非 `_stat_month`
  - `_str()` dict 處理修正 falsy 0 bug（`v.get("value") or ...` → `"value" in v and v["value"] is not None`）
- **`dazhi-repair` 前端移除畫面中的「大直」字眼**（Tab label、Breadcrumb、Page title、費用提示文字共 4 處）→ 改為「工務部」

---

## [1.53.0] - 2026-05-02

### Added
- **飯店管理 Dashboard — 來源卡片加入「預估工時 / 保養時間」雙行顯示（Option A）** — `HotelMgmtDashboard/index.tsx`：
  - `NormalizedSource` 介面新增 `actual_hours?: number` 選填欄位（保養時間 = actual_minutes / 60）
  - `adaptPeriodic()` 新增 `actual_hours: (kpi?.actual_minutes ?? 0) / 60`，對應飯店週期保養來源
  - SourceCard 工時區段改為條件渲染：有 `actual_hours` 的來源（週期保養）→ 顯示「預估工時（藍）/ 保養時間（綠）」雙行；其他來源維持「工時」單行
  - 兩行標籤各附 Tooltip 說明計算來源
  - ⚠️ 後端 `periodic_maintenance /stats` 目前未計算 `actual_minutes`（PMBatchKPI 欄位存在但值為 0）；待後端補上後，保養時間欄位自動生效
- **KPI 卡片「本期工時合計」加入 Tooltip** — 說明六項來源工時混合性質（實際/計劃/估算）

---

## [1.52.3] - 2026-05-01

### Added
- **三大監控模組 Dashboard 查詢月份功能**（hotel/daily-meter-readings、mall-facility-inspection、full-building-inspection）
  - 各模組 Dashboard Tab 頂部加入月份選擇器（`picker="month"` YYYY/MM 格式）
  - URL 支援 `?month=YYYY-MM` 參數，切換月份時同步更新 URL
  - KPI Card 統計（本月登錄筆數 / 缺漏天數 / 最近登錄日期 / 缺漏日期 / 近 7 天趨勢點）全部依查詢月份重新計算
  - 今日是否登錄 Badge：當月顯示「今日已/未登錄」，歷史月顯示「末日已/未登錄」
  - Dashboard 標題與統計文字顯示查詢月份（如「2026年5月統計」）
- **後端新增共用工具 `app/core/date_utils.py`** — `get_month_range(month)` / `to_ragic_year_month(month)` / `current_month_str()`
- **`hotel-meter-readings` dashboard/summary 端點**：新增 `month` query param（YYYY-MM），取代舊版 `target_date`（仍向後相容）；修正 `latest_record_date` 改為查詢月份內最近日期；修正 `trend_7d` 依查詢月份末日往前 7 天；缺漏天數統計改用 `get_month_range`
- **`mall-facility-inspection` 新端點 `GET /dashboard/monthly-summary?month=YYYY-MM`** — 各 Sheet 月份 KPI（登錄場次 / 缺漏天數 / 缺漏日期 / 最近場次日 / 近 7 天趨勢）
- **`full-building-inspection` 新端點 `GET /dashboard/monthly-summary?month=YYYY-MM`** — 標準月份 KPI 結構（目前回傳空值，待本地同步實作後填充）
- **前端新增 `api/fullBuildingInspection.ts`** — `fetchFullBuildingMonthlyDashboard(month?)` API 封裝
- **前端 `api/mallFacilityInspection.ts`** 新增 `fetchMallFacilityMonthlyDashboard(month?)` 及 `MallFIMonthlyDashboardSummary` / `MallFIMonthlySheetSummary` 型別
- **前端 `api/hotelMeterReadings.ts`** 更新 `fetchHotelMeterDashboardSummary` 參數改為 `{ month?, target_date? }`

---

## [1.52.6] - 2026-05-02

### Changed
- **`mall/overview` 全模組文字放大 2 級** — `MallMgmtDashboard/index.tsx` 內所有 `fontSize` 值統一 +2（共 89 處；9→11、10→12、11→13、12→14、13→15、14→16、15→17、16→18、18→20、20→22、22→24）

---

## [1.52.5] - 2026-05-02

### Changed
- **`mall/overview` 各來源卡依年月篩選重新計算** — 篩選列標籤由「商場報修篩選」改為「篩選年月」；年月變更同步觸發商場例行維護、全棟例行維護（PM stats year/month 參數）、商場工務巡檢（切換為 `/dashboard/monthly-summary` 月統計端點）、樂群工務報修四張卡重載；新增 `normalizeFacilityMonthly`（預期場次 = 已登 + 缺漏、完成率、缺漏天數為異常）；商場工務巡檢 summary 優先使用月統計，無資料時 fallback 日統計

---

## [1.52.4] - 2026-05-02

### Changed
- **`mall/overview` KPI 卡「工時」欄拆分為「預估工時」＋「保養時間」** — `NormalizedSummary` 新增 `actual_hours` 欄位；`normalizePM` 從 `kpi.actual_minutes` 提取實際保養時間（藍色「預估工時」/ 綠色「保養時間」並排顯示）；商場工務巡檢、報修等非 PM 來源 `actual_hours` 保持 0（不顯示）
- **`mall/overview` 例行維護工時來源改為實際保養時間** — `daily-hours`、`monthly-hours`、`person-hours` 三個端點的例行維護（商場週期保養＋全棟例行維護）工時計算，由 `estimated_minutes`（預估值）改為 `start_time`／`end_time` 差值（`_parse_minutes`），與每日巡檢邏輯一致；尚未完成（缺 `end_time`）的項目貢獻 0 小時

---

## [1.52.3] - 2026-05-02

### Added
- **商場週期保養 / 全棟例行維護 Dashboard KPI 新增「預估工時」卡** — 將原「保養時間」（實為 estimated_minutes 合計）正名為「預估工時」（藍色），並新增「保養時間」卡（綠色）= 所有已完成項目 end_time − start_time 差值合計（小時）
- **後端 PMBatchKPI schema 新增 `actual_minutes` 欄位** — `mall_periodic_maintenance` / `full_building_maintenance` 兩個 router 各加 `_time_diff_minutes()` helper 計算實際工時；schema 同步新增型別

---

## [1.52.2] - 2026-05-01

### Added
- **三大保養模組 Dashboard 年月篩選**（飯店週期保養、商場週期保養、全棟例行維護）— 主管儀表板頂部新增年份＋月份選擇器；篩選後 KPI 卡、完成率進度條、類別 BarChart、狀態 Donut、逾期清單、待執行清單全部依所選年月重新計算
- **後端三支 `/stats` 端點新增 `year`/`month` query params** — `periodic-maintenance`、`mall/periodic-maintenance`、`mall/full-building-maintenance`；預設維持當月；非當月時「待執行」改顯示該批次所有已排定項目（不再限制本週 7 天）

---

## [1.52.1] - 2026-05-01

### Fixed
- **mall/overview Tab B「例行維護」顯示 0 的問題** — 根本原因有二：①`period_month` 以 `==` 嚴格比對，若 Ragic 回傳無零填充格式（`"2026/4"`）則查無批次；②無 `scheduled_date`（未排定）的 PM 項目被 `if "/" in sched:` 條件跳過，導致其 `estimated_minutes` 全數漏算。修正：改以 LIKE 搜尋年份後在 Python 端過濾月份（同時相容 `"2026/04"` 與 `"2026/4"`）；無 `scheduled_date` 的項目落回第 1 天，確保合計與 `planned_minutes / 60`（Dashboard 顯示的 76.3 HR）一致

---

## [1.52.0] - 2026-04-30

### Fixed
- **飯店管理 Dashboard — 現場報修（大直工務部）每日/每月累計數值顯示空值** — `hotel_overview.py`：
  - 改用 `completed_at IS NOT NULL` 選案（不依賴 `is_completed` DB 欄位，更可靠）
  - 工時來源雙軌：① `work_hours > 0` 直接使用；② `work_hours = 0` 時以 `close_days`（結案天數）代入
  - 日期桶改為 `completed_at.day` / `completed_at.month`，對齊「4.2 結案時間」口徑
  - 移除「未完工案件以 occurred_at 累加」段落（原本 work_hours 也是 0，無效）
  - 同步修正 `/hotel/daily-hours` 與 `/hotel/monthly-hours` 兩個 endpoint
- **前端 Tab B/C 圖例加入「ⓘ 現場報修數值說明」Tooltip** — 說明 close_days 代入邏輯 `HotelMgmtDashboard/index.tsx`

---

## [1.51.0] - 2026-04-30

### Changed
- **飯店管理 Dashboard — Tab B「每日累計」新增篩選列與圖例** — `HotelMgmtDashboard/index.tsx`：
  - 新增篩選列（每日累計工時 (HR) 標題 + year Select + month Select + 重新整理按鈕 + 年月標籤），對齊 Tab C 版型
  - 新增類別圖例（五項 Tag + 模組建置中說明）
  - 重新整理按鈕直接重抓 `fetchHotelDailyHours(year, month)` 並清除 loadedTabs 快取

---

## [1.50.0] - 2026-04-30

### Changed
- **飯店管理 Dashboard — Tab C「每月累計」全面改版，對齊 Tab B 版型** — `HotelMgmtDashboard/index.tsx`：
  - 五項工作類別（現場報修/上級交辦/緊急事件/例行維護/每日巡檢）取代原六項來源；合併邏輯與 Tab B 一致
  - 欄位修正：「工項類別」/ 月份 1月~12月 左到右 / 「TOTAL」/ 「%」；Tag badge 渲染；數值 `.toFixed(1)` / 0 顯示 `-`；% 欄 ORANGE 加粗
  - 新增篩選列（年度工時彙總 + year Select + 重新整理按鈕 + 年份標籤）
  - 新增類別圖例列（五項 Tag + 模組建置中說明）
  - Card 包裝：標題「每月累計工時 (HR)」+ 右上「year 年」
  - 移除舊 subtitle div（「六大來源 × 每月工時」）
  - 不更動後端 API、不影響其他 Tab

---

## [1.49.1] - 2026-04-30

### Fixed
- **飯店管理 Dashboard — Tab B「現場報修」工時統計口徑對齊 dazhi-repair/dashboard** — `backend/app/routers/hotel_overview.py`：
  - 根本原因：舊版 `GET /hotel/daily-hours` 和 `GET /hotel/monthly-hours` 對「大直工務部」只按 `occurred_at`（報修月）篩選，導致「前月報修、本月完工」案件的工時被遺漏
  - 修正為對齊 `dazhi_repair_service._stat_month` 邏輯：**已完工案件**改以 `completed_at` 年月選案，按 `completed_at.day/month` 累加；**未完工案件**維持按 `occurred_at` 年月選案
  - 兩個端點（daily-hours / monthly-hours）均同步修正
  - 不更動前端、不新增 API、不影響其他五項來源

---

## [1.49.0] - 2026-04-30

### Changed
- **飯店管理 Dashboard — Tab B「每日累計」版型與計算邏輯全面修正** — `HotelMgmtDashboard/index.tsx`：
  - **五項工作類別**（現場報修 / 上級交辦 / 緊急事件 / 例行維護 / 每日巡檢）取代原六項來源；合併邏輯：現場報修=大直工務部、例行維護=客房保養管理+飯店週期保養+IHG客房保養、每日巡檢=飯店每日巡檢+保全巡檢；上級交辦/緊急事件固定 0（模組未開發）
  - **欄位修正**：工項類別欄標題由「來源」→「工項類別」；TOTAL 欄由「合計」→「TOTAL」
  - **Tag badge 渲染**：現場報修=blue / 上級交辦=green / 緊急事件=red / 例行維護=orange / 每日巡檢=purple；TOTAL 列顯示粗體
  - **數值格式**：每日欄位 `.toFixed(1)` 或 `-`；TOTAL 欄 `.toFixed(1)`；% 欄 ORANGE 加粗
  - **Card 包裝**：加入 `<Card>` 含標題「每日累計工時 (HR)」與右上 `year年 month月`；移除舊的 subtitle div
  - 新增常數：`HOTEL_5CATS`、`HOTEL_5CAT_TAG_COLORS`；無新增後端 API

---

## [1.48.0] - 2026-04-30

### Removed
- **飯店管理 Dashboard — 刪除三個 Tab（保養管理 / 巡檢管理 / 大直工務）** — `HotelMgmtDashboard/index.tsx`：
  - 從 `tabItems` 陣列移除 `key='maintenance'`、`key='inspection'`、`key='dazhi'` 三個 Tab 及其所有 JSX 內容
  - 同步刪除 8 個已無用的內嵌函式：`_placeholder_RoomTrendChart`、`SecurityTrendChart`、`HotelDICards`、`SecuritySheetCards`、`CompletionRateRow`、`DazhiSummary`、`PMSummary`、`IHGSummary`
  - 保留 `DazhiTrendChart`、`SourcePieChart`（仍在總覽 Tab 使用）
  - 保留所有 Icon / 狀態變數 / 型別（仍被其他模組引用）

---

## [1.47.0] - 2026-04-30

### Added
- **飯店管理 Dashboard — 新增三大區塊（對齊 mall/overview）** — `HotelMgmtDashboard/index.tsx`：
  - **篩選列** — 總覽 Tab 頂部新增 `Card` 篩選列：大直工務篩選（年/月 Select，支援「全年」）+ 巡檢日期 `DatePicker`（含今日按鈕）+ 全部重新整理；`targetDate` 改為 state；新增 `loadInspections(date)` 獨立重載巡檢資料
  - **報修費用摘要** — 新增 Divider + 3 張 KPI 卡片（委外+維修費用 / 扣款費用 / 本月費用合計），取自 `dazhiData.kpi` annual/month 費用欄位；無資料時顯示「數據準備中」
  - **決策分析圖表** — 新增橫向 BarChart（工項/案件數比較）+ 橫向 BarChart（各來源完成率%）；版型重構為 Row1（兩欄橫 Bar）+ Row2（lg=16 趨勢折線 + lg=8 Donut Pie），對齊 mall/overview；`SourcePieChart` 改為 donut（加 `innerRadius=40`）
  - 新增 import：`DatePicker`、`ReloadOutlined`、`QuestionCircleOutlined`；新增 `yearOptions`、`monthOptions`（含全年）、`ytdLabel`、`barData`、`rateBarData`；移除 `MONTHS` 常數、`Option` 解構、`todayStr` 常數

---

## [1.46.0] - 2026-04-30

### Changed
- **飯店管理 Dashboard — 全面對齊 mall/overview 版型（UI 重構）** — `HotelMgmtDashboard/index.tsx`：
  - `NormalizedSource` 新增 `completed_count` / `overdue_count` 欄位；6 個 adapter 函式同步更新
  - 新增常數 `HOTEL_SOURCE_ICONS` / `HOTEL_SOURCE_ROUTES`；新增計算值 `totalCompleted` / `overallRate` / `totalOverdue`
  - **主管摘要（KpiAggregate）** 完全重寫：移除 `size="small"`；卡片標題改 fontSize 11；6 張卡片對齊商場版型：本期總工項 / 已完成工項（含完成率）/ 整體完成率（圓形 Progress）/ 本期工時合計 / 異常未完成 / 逾期未完成
  - **各來源本期狀態（SourceCards）** 完全重寫：Card 加 `title`（圖示+色彩名稱）+ `extra`（詳情按鈕）；Body 改為雙欄 Statistic（工項數 + 已完成）+ 漸層 Progress（`from … to #52C41A`）+ 底部異常/逾期/工時列；佔位卡改為居中「數據準備中」
  - 新增 import：`React`、`useNavigate`（react-router-dom）、`RightOutlined`、`Button`

---

## [1.45.0] - 2026-04-30

### Added
- **飯店管理 Dashboard Tab B/C/D/人員排名（新功能）** — 新增後端 `GET /api/v1/hotel/daily-hours`（六來源 × 天數工時）、`GET /api/v1/hotel/monthly-hours`（六來源 × 12 月工時）、`GET /api/v1/hotel/person-hours`（Top-15 人員 × 六來源工時佔比 + person_totals）；新增 `backend/app/routers/hotel_overview.py`；在 `main.py` 掛載；前端新增 `api/hotelOverview.ts` + `HOTEL_CATEGORY_COLORS`；`HotelMgmtDashboard/index.tsx` 新增 4 個懶載入 Tab（B. 每日累計 / C. 每月累計 / D. 人員工時% / 人員排名）；人員排名以橫向工時 Bar + 各來源明細表呈現；格式與 mall/overview 完全一致

---

## [1.44.0] - 2026-04-30

### Added
- **飯店管理 Dashboard（新功能）** — 整合 6 來源（客房保養管理/飯店週期保養/IHG客房保養/飯店每日巡檢/保全巡檢/大直工務部）的跨模組總覽；前端 Normalize adapter 層統一欄位（source_name/case_count/work_hours/completion_rate/abnormal_count）；KPI 聚合卡片 + 各來源狀態卡 + 4 張分析圖表；4 個 Tab（總覽/保養管理/巡檢管理/大直工務）；route `/hotel/overview`；Menu「飯店管理 > ★ 飯店管理 Dashboard」（置頂，permissionKey=`hotel_view`）
- 新增頁面檔：`frontend/src/pages/HotelMgmtDashboard/index.tsx`
- 更新：`frontend/src/router/index.tsx`、`frontend/src/components/Layout/MainLayout.tsx`、`frontend/src/constants/navLabels.ts`

---

## [1.43.5] - 2026-04-30

### Changed
- **商場管理 Dashboard Tab D「人員工時%」完整重寫** — 後端新增 `GET /api/v1/mall/person-hours`，彙整五項工作類別 Top-15 人員工時佔比（現場報修=acceptor、例行維護=executor_name 多人平分、每日巡檢=inspector_name）；前端新增 `MallPersonHoursData/MallPersonRow` 型別 + `fetchMallPersonHours` API；Tab D 改為工項類別（固定左欄）× 人員（動態欄）交叉表，%色彩編碼比照 WCA（≥30% 紅、≥15% 橙、>0% 綠）；獨立年份選擇器（不與 A/B/C Tab 連動）
- **後端新端點 `GET /api/v1/mall/monthly-hours`** — 同步補入（與 daily-hours 同 router，月份聚合）
- **移除舊 Tab D 邏輯** — 移除 `personHoursPctData` useMemo、`personPctCols`、`pctColor`（component-level）、Pie Chart、集中度分析；Tab E（人員排名）保留不變，`pctColor` 移至 Tab E 區域

---

## [1.43.4] - 2026-04-30

### Changed
- **商場管理 Dashboard Tab C「每月累計」完整重寫** — 移除舊完成率矩陣（PM 批次完成率 + 折線圖），改為五工項 × 12 月工時交叉表；後端新增 `GET /api/v1/mall/monthly-hours`（資料來源與 daily-hours 一致，改以月份聚合）；前端新增 `MallMonthlyHoursData` 型別 + `fetchMallMonthlyHours` API；格式與 work-category-analysis Tab C 完全一致（未來月份顯示 —、TOTAL 列底色、% 欄）
- **移除 Tab C 對 PM 批次 API 的依賴** — 不再呼叫 `fetchMallPMBatches` / `fetchFullBldgPMBatches`；相關 state（`mallPmBatches`、`fullBldgPmBatches`）、helper（`buildPMMonthMap`、`luqunMonthMap`）、useMemo（`monthlyRows`）全數移除

---

## [1.43.3] - 2026-04-30

### Added
- **商場管理 Dashboard Tab B「每日累計」完整重寫** — 後端新增 `GET /api/v1/mall/daily-hours` 彙整五項工作類別每日工時；前端新增 `frontend/src/api/mallOverview.ts`（型別定義 + API 封裝），Tab B 改為五工項 × 每日 HR 交叉表（含 TOTAL 合計列 + % 欄），格式與 work-category-analysis 模組一致
- **新後端端點 `GET /api/v1/mall/daily-hours`** — 資料來源：現場報修（luqun_repair_cases）、例行維護（mall/full_bldg PM batch+item、estimated_minutes/60）、每日巡檢（mall_facility + rf_inspection batch、HH:MM 時間差計算）；上級交辦/緊急事件模組尚未開發固定為 0
- **後端新 router `app/routers/mall_overview.py`** — 含 `_parse_minutes()` 工具函式，回傳格式與 WCA `_build_daily()` 完全相容

---

## [1.43.2] - 2026-04-30

### Fixed
- **luqun 扣款費用口徑統一** — Dashboard `month_deduction_fee` 與 YTD `annual_deduction_fee` 加入 `is_completed + deduction_counter_name` 篩選，與扣款專櫃 `total_counter_fee` 口徑一致；修正前兩者會計入有扣款費用但無專櫃名稱案件（資料缺漏）導致數字偏大的問題
- **金額統計 Tab `deduction_fee` 欄位** — `compute_fee_stats` 月份迴圈中 `deduction_fee` 列同步加入相同篩選；明細展開清單（`deduction_fee` 與 `deduction_counter` 統一使用相同條件）

---

## [1.43.1] - 2026-04-30

### Changed
- **保全巡檢 Dashboard 重新設計（一頁式）** — 移除今日統計/異常清單/趨勢分析三個子 Tab；改為一頁式綜合 Dashboard：全局 KPI 卡 + 7 Sheet 狀態 mini-cards（點擊直跳 Tab）+ 今日統計表（前往按鈕切換 Tab）+ 今日異常清單 + 近7日趨勢圖；三個資料源並行載入（`Promise.all`）
- **各巡檢 Sheet TAB 簡化** — 移除「主管儀表板」內層 Tab；直接呈現巡檢紀錄清單（月份篩選 + 批次表格 + 明細連結）；`SecurityPatrolContent` 精簡，移除 `fetchPatrolStats` 相關邏輯

---

## [1.43.0] - 2026-04-30

### Changed
- **保全巡檢模組整合** — 將原本 8 個獨立選單項目（Dashboard + 7 張巡檢 Sheet）整合為單一入口「保全巡檢」
  - 主路由 `/security/dashboard` 新增外層 TAB（type="card"）：Dashboard + B1F~B4F + 1F~3F + 5F~10F + 4F + 1F飯店大廳 + 1F閉店巡檢 + 1F開店準備
  - `SecurityPatrolContent` 元件拆分：接受 `sheetKey` prop，原路由包裝層保留（舊路由 `/security/patrol/:sheetKey` 仍可直接存取）
  - MainLayout 保全選單簡化為單一 `/security/dashboard` 直連（原 8 items → 1 item）
  - `NAV_GROUP.security` 從「保全管理」改為「保全巡檢」
  - `RagicAppDirectory.tsx` `PORTAL_DEFAULTS` items 5~18 portalName 同步更新為「保全巡檢」
  - 新增 `backend/scripts/seed_security_app_directory.py` — 後端停機時補充 DB 記錄的工具腳本
  - 規劃文件：`docs/integration-security-tabs.md`
  - 後端零改動；所有既有 API / Service / Router / Schema / Permission 不受影響

---

## [1.42.0] - 2026-04-30

### Added
- **每日數值登錄表模組（飯店管理）** — 整合 4 張 Ragic Sheet（全棟電錶 /11、商場空調箱電錶 /12、專櫃電錶 /14、專櫃水錶 /15），route `/hotel/daily-meter-readings`
  - Dashboard Tab：今日登錄狀態、本月缺漏天數、近 7 天趨勢、4 張表格各自統計卡片
  - 各 Sheet Tab：月份篩選 + 關鍵字搜尋 + 登錄清單 + 連回 Ragic 原始資料
  - 後端：`HotelMRBatch` + `HotelMRReading` ORM（動態欄位 Pivot 架構）
  - 同步服務：`hotel_meter_readings_sync.py`（動態欄位偵測，排除 metadata 後所有欄位均視為讀數）
  - API：`GET /api/v1/hotel-meter-readings/dashboard/summary`、`/{sheet_key}/batches`、`/sync/all`
  - 권限：`hotel_meter_readings_view`（已加入 `PERMISSION_DEFINITIONS`）
  - Menu：飯店管理 > 每日數值登錄表（`DatabaseOutlined` 圖示）
  - 自動排程同步：已加入 `_auto_sync` 每 30 分鐘執行

---

## [1.41.7] - 2026-04-29

### Added
- **商場管理 Dashboard — 商場報修費用摘要區塊** — Dashboard Tab 新增「商場報修費用摘要」3 欄 KPI 卡片，位於各來源狀態卡下方：①委外+維修費用（含下方細分金額，Tooltip 顯示個別數字）②扣款費用 ③扣款專櫃家數（Tooltip 顯示店家名稱）+ 扣款合計；全部來自 `luqunData.kpi` 已載入資料，無需額外 API；顯示 `ytdLabel`（月份選定→「累計至M月」，全年→「全年」）

### Changed
- **商場管理 Dashboard — 標籤文字更新** — 篩選列「大直工務篩選」→「商場報修篩選」；趨勢圖「大直工務報修 — 12 個月案件趨勢」→「商場報修 — 12 個月案件趨勢」

---

## [1.41.6] - 2026-04-29

### Fixed
- **商場管理 Dashboard — Tab B 每日累計無資料問題修正** — 原本呼叫 `fetchLuqunDetail(page_size=500)` 觸發後端上限 `le=200` 驗證錯誤導致空白；改為呼叫 `fetchLuqunDash(year, month)` 直接取得 `kpi_total_detail`（含當月全部案件），不受 page_size 限制
- **商場管理 Dashboard — Tab B 標籤文字修正** — 「大直工務報修 日別統計」改為「商場報修 日別統計」；說明文字同步更新為「樂群工務報修」

---

## [1.41.5] - 2026-04-29

### Changed
- **商場管理 Dashboard — 工務報修來源改用樂群** — KPI 第二列「大直工務報修」更名為「樂群工務報修」，資料來源由 `/api/v1/dazhi-repair/*` 改為 `/api/v1/luqun-repair/*`（`fetchLuqunDash`）；types 改用 `@/types/luqunRepair`；route 連結改為 `/luqun-repair/dashboard`

---

## [1.41.4] - 2026-04-29

### Fixed
- **樂群報修 Dashboard — 計算邏輯與標籤對齊重構**
  - 扣款專櫃 Modal 三處硬編碼「全年」改用動態 `ytdLabel`（月份選定時顯示「累計至 M 月」，全年檢視顯示「全年」）
  - `luqunRepair.ts` 型別註解更新：`annual_*` 欄位說明改為 YTD 累計語義，與費用 KPI 卡片邏輯一致
  - 確認後端 `luqun_repair_service.py` 已完整對齊：以 `is_completed(status)` 為唯一完工判準、三類互斥（completed / pending_verify / uncompleted）、YTD 費用按月份篩選累計（1~M 月或全年）

---

## [1.41.3] - 2026-04-29

### Fixed
- **角色管理權限設定補齊「一階選單」群組** — `PERMISSION_DEFINITIONS` 新增「一階選單」分類，將 `exec_dashboard_view`（高階主管 Dashboard）、`work_category_analysis_view`（工項類別分析）、`calendar_view`（行事曆）從原本的「財務」/「工務報修」/「協作工具」移出，集中顯示；角色管理頁面現在能直接在最頂端看到這三個獨立一階選單的權限設定

---

## [1.41.2] - 2026-04-29

### Fixed
- **一階選單項目補齊 permissionKey** — `MainLayout.tsx` 的 `menuItems` 中，所有一階（父層群組 + 獨立一階）與其子項目補上對應 `permissionKey`，使「角色管理」頁面的權限勾選能實際控制側欄顯示/隱藏
  - 獨立一階：`/exec-dashboard`（exec_dashboard_view）、`/work-category-analysis`（work_category_analysis_view）、`/calendar`（calendar_view）
  - 群組父層：budget、hotel、mall、luqun-repair、dazhi-repair、security、approvals、memos 各補上對應 permissionKey
  - 子項目細粒度控制：飯店（4項）、商場（5項）、保全（dashboard + 7條巡檢路線）、預算（view/manage/admin 三級）、簽核/公告（view/manage 兩級）各自對應精確 permission_key

---

## [1.41.1] - 2026-04-29

### Fixed
- **人員管理角色下拉選單支援自訂角色** — `Users.tsx` 原本使用 `ROLE_OPTIONS`（硬編碼 4 個內建角色），改為在頁面載入時呼叫 `GET /api/v1/roles` 動態取得所有角色（含自訂）；自訂角色在選單中標示「（自訂）」；Table 角色 Tag 顯示邏輯同步更新（fallback 至識別碼顯示，顏色改用 geekblue）

---

## [1.41.0] - 2026-04-29

### Added
- **自訂角色 CRUD（角色管理 v2）** — 可在「角色管理」頁面新增/刪除自訂角色（如 hotel_manager、mall_manager），並分別指派不同 permission_key
  - 新增後端 `POST /api/v1/roles`：建立自訂角色（名稱限小寫英文+底線，不可與內建角色同名）
  - 新增後端 `DELETE /api/v1/roles/{id}`：刪除自訂角色（cascade 清除 role_permissions 與 user_roles）
  - 內建角色（system_admin / tenant_admin / module_manager / viewer）受保護，不可刪除
  - 新增前端 `src/api/roles.ts`：封裝 fetchRoles / createRole / deleteRole
  - 完全改寫 `Roles.tsx` 為動態架構：從後端取得角色清單（含 `is_builtin` 欄位）
  - 「角色清單」Tab：統一顯示內建 + 自訂角色，自訂角色有 Popconfirm 刪除按鈕，右上角「新增自訂角色」Button
  - 「新增自訂角色」Modal：name / description 表單，含格式驗證與說明提示
  - 「權限設定」Tab：左側角色清單動態顯示所有角色，內建與自訂以 Divider 分隔，可為任意自訂角色設定 permission_key
  - 重構 `backend/app/main.py`：移除 inline `/roles` GET endpoint，改為 include `roles.router`

---

## [1.40.0] - 2026-04-29

### Added
- **Menu 權限管控機制（RBAC）** — 三層防護：sidebar 過濾 → 前端 PermissionGuard → 後端 API require_permission
  - 新增 `role_permissions` 資料表，多對多關聯角色與 permission_key
  - 新增 `menu_configs.permission_key` 欄位，可在 MenuConfig 頁面 UI 設定
  - 新增後端 `get_user_permissions()`、`require_permission()` dependency 工廠
  - 擴充 `GET /auth/me` 回應加入 `permissions: list[str]`（system_admin 回傳 ["*"]）
  - 新增 `GET/PUT /api/v1/role-permissions/{role_id}` API，供 Roles 頁面管理角色權限
  - 新增 `GET /api/v1/role-permissions/keys` API，回傳所有已知 permission_key 定義
  - 新增 `GET /api/v1/roles` API，回傳角色清單（含 id）
  - 前端 `authStore` 加入 `permissions` + `hasPermission()` 方法
  - 前端 `MainLayout` 加入 `filterMenuByPermissions()`（DB permission_key 優先於靜態預設）
  - 前端 `PermissionGuard` 元件，無權限顯示 🔒 403 提示頁
  - `Roles.tsx` 新增「權限設定」Tab，以 Checkbox 群組管理各角色的 permission_key
  - `MenuConfig` 頁面編輯模式加入 permission_key 輸入欄
  - 新增開發規格書：`docs/PERMISSION_SPEC.md`（含新模組開發期使用 system_admin_only 的流程）
  - **新模組預設規則**：開發期間 `permissionKey: 'system_admin_only'`，測試完成後透過角色管理手工授予

---

## [1.39.46] - 2026-04-29

### Fixed
- **樂群 扣款專櫃計算邏輯修正（兩處 bug）**
  - **當月金額 扣款專櫃家數/金額** — 原用 `this_month_cases`（本月相關案件，含上期累計未結），導致 1 月尚未結案但已設扣款的案件會出現在 3 月的「當月金額」欄；改為 `fee_month_cases`（`_stat_month == 選定月`，與金額統計 tab 完全一致）
  - **YTD/全年 扣款專櫃（Dashboard KPI 卡 + 彈窗）** — 原包含 `status = 待辦驗` 等未結案件，其 `c.month = occurred_at.month`，使得選定 3 月時 1 月的未結案件（`completed_at` 可能為 4 月）錯誤出現在 popup；加上 `is_completed(c.status)` gate，確保計入的案件 `c.month = completed_at.month`，ytd 過濾 `_stat_month <= month` 才能精確排除超出期間的案件
  - 同步修正 `compute_fee_stats` 的 `deduction_counter` 逐月家數計算及全年去重計算，加 `is_completed` gate，使金額統計 tab 與 Dashboard 口徑完全一致
  - 修改範圍：`backend/app/services/luqun_repair_service.py`（大直無 `deduction_counter` 欄位，無需變動）

---

## [1.39.45] - 2026-04-29

### Fixed
- **樂群 報修清單總表「報修詳情」缺少附圖問題** — `DetailTab` 原用內嵌 `<Drawer>` + `<Descriptions>` 顯示詳情，缺少圖片區塊；改為統一呼叫共用 `<CaseDetailDrawer>` 元件（與 4.1 報修 Tab 點擊「詳情→報修詳情」完全一致），自動支援 DB 圖片優先、Ragic lazy-fetch 備援之圖片顯示邏輯
  - 修改範圍：`frontend/src/pages/LuqunRepair/index.tsx`（大直 DetailTab 原本已有圖片處理，無需變動）

---

## [1.39.44] - 2026-04-29

### Fixed
- **樂群／大直 Dashboard KPI 計算邏輯修正（稽核報告 P1/P2/P3）**
  - `is_completed_flag` 改以 `status`（處理狀況）為唯一判斷依據，移除 `completed_at IS NOT NULL` 的條件；`completed_at` 欄位保留供 `close_days` 計算與查閱，不再影響完成判定
  - `_prev_uncompleted`（上期未結）改用 `not is_completed(c.status)` 判斷，與 `completed` 邏輯一致
  - `未完成件數 = 總數 - 已完成 - 待辦驗`（三類互斥），修正原本 `total - completed` 導致待辦驗重複計入未完成的錯誤（樂群 2026/04：24 → 17）
  - `kpi_uncompleted_detail` 明細清單同步排除 `status == "待辦驗"` 案件，與卡片數字對齊
  - `pending_verify_cases` 計算移至 KPI 區段（completed 之後），確保 `uncompleted` 計算可直接引用
  - `trend_12m` completed、`top_uncompleted` 均改用 `is_completed(c.status)` 判斷
  - 修改範圍：`backend/app/services/luqun_repair_service.py`、`backend/app/services/dazhi_repair_service.py`
- **費用 KPI 前三張卡改為 YTD（累計至選定月）口徑**
  - 後端：`compute_dashboard` 中 `year_cases`（全年）改為 `ytd_cases`（1月~M月），`annual_fee`/`annual_deduction_fee`/`annual_counter_*` 及對應明細清單全部跟進；全年檢視（month=0）維持原全年邏輯
  - 前端：`LuqunRepair` / `DazhiRepair` Dashboard Tab 加入 `ytdLabel` 衍生字串（月份選定時 `累計至M月`，全年時 `全年`）；費用卡片副標題、Modal 標題、Empty 訊息全部套用
- **4.1/4.2/4.3 其他 Tab 同步修正**
  - `_completed_by`/`_completed_in`（luqun 內層、dazhi 模組級）加上 `is_completed(c.status)` 前提，status 非完成的案件即使有 `completed_at` 也不計為完成
  - `_closed_in`（4.2 結案時間統計）同步加 status gate（dazhi 委派給 `_completed_in`，luqun 直接修改）
  - `_stat_year`/`_stat_month`：luqun 簡化為直接讀 `c.year`/`c.month`（`__init__` 已依 status 正確計算）；dazhi 加 `is_completed(status)` gate 再讀 `completed_at`（dazhi `c.year`/`c.month` 永遠是報修月）

---

## [1.39.43] - 2026-04-29

### Changed
- **樂群／大直 Dashboard「本月相關案件」口徑調整** — 由「完工月＋未完成報修月」改為「① 上月累計未完成 + ⑤ 本月報修」，與 4.1 報修統計 Tab 口徑完全對齊；KPI 完成數／未完成數、明細清單、avg_close_days 同步調整（全年 month=0 檢視保持舊邏輯）
  - `backend/app/services/luqun_repair_service.py` — 新增 `_db_completed_by`/`_db_completed_in` 模組函式，更新 `compute_dashboard`
  - `backend/app/services/dazhi_repair_service.py` — 更新 `compute_dashboard`（使用既有模組層級 `_completed_by`/`_completed_in`）

---

## [1.39.42] - 2026-04-29

### Added
- **飯店每日巡檢模組（新功能）** — 仿照春大直商場工務巡檢架構，新增飯店 5 個區域巡檢整合頁，route `/hotel/daily-inspection`：
  - Ragic 來源：RF（Sheet 17）/ 4F-10F（Sheet 18）/ 4F（Sheet 19）/ 2F（Sheet 20）/ 1F（Sheet 21）
  - 後端 ORM：`hotel_di_inspection_batch` + `hotel_di_inspection_item` 雙表（寬表格 Pivot 架構）
  - 後端 Sync Service：`hotel_daily_inspection_sync.py`（動態欄位偵測、5 張 Sheet 同步）
  - 後端 Router：`/api/v1/hotel-daily-inspection`（sheets / sync / stats / batches / dashboard/summary）
  - 前端常數：`constants/hotelDailyInspection.ts`（5 Sheet 設定）
  - 前端 API：`api/hotelDailyInspection.ts`（axios 封裝函式）
  - 前端頁面：`pages/HotelDailyInspection/index.tsx`（6-Tab：Dashboard + RF/4F-10F/4F/2F/1F，懶載入 + URL ?tab=）
  - Menu：飯店管理 → 飯店每日巡檢（SafetyOutlined 圖示）
  - APScheduler 自動同步：納入 `_auto_sync` 排程

---

## [1.39.41] - 2026-04-28

### Changed
- **商場管理 Dashboard — KPI 來源卡片版型調整**：
  - 第一列（4 欄）：商場例行維護 / 全棟例行維護 / 商場工務巡檢 / 整棟巡檢
  - 第二列（3 欄）：大直工務報修 / 商場主管交辦（數據準備中）/ 商場緊急事件（數據準備中）
  - 無資料狀態文字改為「數據準備中」（原「資料建置中」）

---

## [1.39.40] - 2026-04-28

### Added
- **商場管理 Dashboard（新功能）** — 整合 5 個既有模組資料的總覽 Dashboard，route `/mall/overview`：
  - 資料來源：商場例行維護（`fetchMallPMStats`）、全棟例行維護（`fetchFullBldgPMStats`）、商場工務巡檢（`fetchMallFacilityDashboardSummary`）、大直工務報修（`fetchDashboard`）；整棟巡檢（API 建置中，佔位顯示）
  - 前端 Normalize adapter：各模組回傳格式統一轉為 `SourceSummary`（`work_hours`/`case_count`/`completed_count`/`completion_rate`/`abnormal_count`/`overdue_count`）
  - KPI 卡片：本期總工項、已完成工項、整體完成率（圓形進度）、工時合計、異常件數、逾期未保養
  - 各來源狀態卡片（5 張，各含工項數、完成率 Progress bar、異常/逾期/工時）
  - 圖表：各來源工項數比較橫條圖、各來源完成率比較橫條圖、大直報修 12 個月案件趨勢折線圖、各來源工時占比圓餅圖
  - 篩選：大直工務年/月篩選；工務巡檢日期篩選；例行維護顯示當期批次（不受篩選影響）
  - 新增 `frontend/src/pages/MallMgmtDashboard/index.tsx`
  - 更新 `router/index.tsx`（新增 `/mall/overview` 路由）、`MainLayout.tsx`（商場管理群組頂部新增 Dashboard 入口）、`navLabels.ts`（新增 `mallMgmtDashboard`）

---

## [1.39.40] - 2026-05-10

### Fixed
- **角色管理 > 儲存權限失敗** — `role_permissions.py` 的 `save_role_permissions` endpoint 實作不完整（`valid_keys` 之後無後續邏輯），FastAPI 回傳 `None` 導致序列化失敗。補完：驗證 key 合法性 → 刪除舊紀錄 → 批次插入新紀錄 → 回傳結果

---

## [1.39.39] - 2026-04-28

### Security
- **系統設定 RBAC 管控** — `系統設定` 選單及 `/settings/*` 路由現在僅限 `system_admin` 角色可見與進入：
  - `authStore`：新增 `decodeUserFromToken()`，頁面重整時從 JWT 還原 `user.roles`，避免 guard 誤判
  - `MainLayout`：依 `user.roles` 過濾 `settings` 選單群組；`useState` 初始值同步由 JWT 決定，避免閃現
  - `router/index.tsx`：新增 `SettingsGuard`，直接輸入 `/settings/*` URL 時若無 `system_admin` 角色一律 redirect 至 `/dashboard`
  - 後端 `menu_config.py`：`PUT /`（儲存設定）與 `GET /history` 改為 `is_system_admin`（`GET /` 保持開放供所有已登入使用者載入側欄動態選單）
  - 後端 `ragic.py`：`GET /connections`、`GET /connections/{id}/logs`、`GET /snapshots/{id}/latest`、`GET /scheduler/status`、`GET /scheduler/module-interval`、`GET /sync-logs/recent`、`GET /app-directory/annotations` 全部改為 `is_system_admin`

---

## [1.39.38] - 2026-04-28

### Changed
- **mall/periodic-maintenance & mall/full-building-maintenance Dashboard** — TAB 名稱由「主管儀表板」改為「Dashboard」；新增第 5 個 KPI 卡片「保養時間」（`planned_minutes` 轉換為小時，藍色 `ClockCircleOutlined`）；原進度條旁的「預估工時」移除（資訊已整合至 KPI 卡）；KPI 卡欄寬由 `lg={6}` 調整為 `lg={4}` 以容納 5 欄

---

## [1.39.42] - 2026-05-03

### Added
- **選單圖示自訂功能** — `settings/menu-config` 每個選單項目右側新增「換圖示」按鈕（`AppstoreOutlined`），點擊展開 Dropdown 圖示選擇器：
  - **預設**：恢復使用 base 結構的原始圖示
  - **無圖示**：側邊欄不顯示圖示（適合收合時隱藏的子項目）
  - **45 種圖示**：依「統計/儀表、建築/設施、維護/系統、行事/文件、人員/安全、商業/財務、其他」七大分類排列
  - 儲存後 sidebar 立即套用；`icon_key` 以字串形式儲存於 DB（`null`=預設、`'none'`=隱藏、字串=圖示名稱）
- **後端 DB 欄位**：`menu_configs` 資料表新增 `icon_key TEXT`（`main.py` lifespan 自動 ALTER TABLE），`MenuConfigItem` schema 同步更新
- **新增 `src/constants/iconMap.tsx`**：`ICON_MAP`、`ICON_GROUPS`、`resolveIcon()` — sidebar 與 MenuConfig 共用，避免重複定義

---

## [1.39.41] - 2026-05-03

### Fixed
- **登入後未跳轉首頁設定** — `Login/index.tsx` 登入成功後改為讀取 `localStorage('portal_home_page_route')` 決定跳轉目標，fallback `/dashboard`；原本固定跳轉 `/dashboard` 導致 menu-config 設定的首頁無效

---

## [1.39.40] - 2026-05-03

### Added
- **選單管理首頁設定** — `settings/menu-config` 新增「設為首頁」功能：每個以 `/` 開頭的真實路由旁顯示 🏠 圖示按鈕，點擊即設為系統首頁；目前首頁顯示綠色「首頁」Tag；設定存入 `localStorage`（key: `portal_home_page_route`）。`router/index.tsx` index route 改為讀取 localStorage 並重定向，fallback 為 `/dashboard`

---

## [1.39.39] - 2026-04-30

### Added
- **Base L1 → L2 降階移動支援** — `applyMenuConfig`（sidebar）與 `buildWorkItems`（MenuConfig UI）新增對「base L1 被移為其他 L1 之 L2 子項目」的完整支援：
  - `applyMenuConfig`：新增 `reparentedBaseL1` Map 偵測，base traversal 過濾已降階項目（防止仍顯示為 L1），`customL2Here` 允許 reparented L1 通過（限定指向目標 L1）；`buildItem` 自動展開其 DB 子項目為 L3
  - `buildWorkItems`：step ① 新增 reparentedBaseL1 偵測；step ② .filter() 排除已降階的 L1；新增 step ⑥ 將 base L1 連同 base 子項目插入新父層，維持 MenuConfig UI reload 後的正確位置
  - 例：「保全管理」可被移到「飯店管理」下成為二階，其八個巡檢子項目自動升格為三階

---

## [1.39.38] - 2026-04-30

### Fixed
- **MenuConfig 新增二/三階選單後儲存失敗** — `handleAddConfirm` 建立新 `WorkItem` 時漏掉 `permissionKey: ''` 欄位，導致 `flattenWorkItems` 呼叫 `undefined.trim()` 拋出 TypeError 被 catch 後顯示「儲存失敗，請再試一次」；補齊一階與子階 new item 的 `permissionKey: ''` 初始值即修復

---

## [1.39.37] - 2026-04-28

### Fixed
- **側欄跨群組移動後重複顯示** — `applyMenuConfig` 的 `customL2Here` 過濾器改用全域 `baseL2Keys`（所有群組的 L2 keys），而非只有當前 L1 群組的 `baseL2KeysForParent`；修正跨群組移動的 base L2 項目（如 `/dazhi-repair/dashboard` 移至 `mall`）同時出現在 `movedHere` 與 `customL2Here`，造成側欄重複顯示的問題

---

## [1.39.36] - 2026-04-28

### Added
- **RagicAppDirectory 選單位置欄** — `settings/ragic-app-directory` 新增「選單位置」欄，從 `menuItems` 自動推導 `portalUrl` 對應的階層（一階/二階/三階）與選單名稱，Tag 顯示階層（藍=一階、綠=二階、橘=三階），下方顯示對應選單項目名稱；支援篩選與排序；新增 `buildPortalInfoMap()` 工具函式，選單結構異動時自動同步

---

## [1.39.35] - 2026-04-28

### Fixed
- **Menu 三層架構顯示錯誤** — 修正 `applyMenuConfig` 對 L2 群組（有 base children 的項目如 `mall-pm-group`）的處理：改為 merge 而非覆寫，確保 `/mall/dashboard`、`/mall/periodic-maintenance`、`/mall/full-building-maintenance` 三個子項目正確顯示於「商場例行維護」群組下
- **商場管理選單重複「商場例行維護」** — `main.py` 啟動時自動隱藏舊 `custom_1777348120465`（DB 中殘留的舊商場例行維護群組），消除側邊欄兩個同名 L2 群組並存的問題
- **Settings/MenuConfig 未顯示三階子項** — `DEFAULT_MENU_STRUCTURE` 擴充為三層（L1→L2→L3）；`buildWorkItems` 步驟② 處理 grandchildren；`itemMap` 步驟③ 納入 L3 keys；`全棟例行維護` 等三階系統模組現可在選單管理頁面正常顯示與設定

---

## [1.39.34] - 2026-04-28

### Added
- **全棟例行維護模組（新功能）** — Ragic Sheet 21（`periodic-maintenance/21`）同步；後端新增 `full_bldg_pm_batch` + `full_bldg_pm_batch_item` 資料表、`full_building_maintenance_sync.py`（子表格 A/B/C/D 四模式解析）、`full_building_maintenance.py` Router（`/api/v1/mall/full-building-maintenance`）；前端新增 `FullBuildingMaintenance` 頁面（主管儀表板 + 批次清單 + 批次明細 + ItemHistoryDrawer）、`fullBuildingMaintenance.ts` API client；`_auto_sync()` 納入全棟例行維護排程
- **Menu 三層架構重構（商場管理）** — `mall` 群組下新增 `mall-pm-group`（商場例行維護）L2 中間層，整合「商場週期保養（/mall/dashboard）」、「商場例行維護（/mall/periodic-maintenance）」、「全棟例行維護（/mall/full-building-maintenance）」為三層 sidebar；navLabels.ts 補 `mallPmGroup`、`fullBuildingMaintenance` 標籤

---

## [1.39.34] - 2026-04-28

### Fixed
- **三階項目跨 L2 移動失敗（mall-pm-group 類舊版 key）** — `buildWorkItems` Phase ④ 的 `extra` 過濾器移除 `c.menu_key.startsWith('custom_')` 限制，改為只排除 `structureKeys` 中的 base 項目；早期未帶 `custom_` 前綴的使用者建立項目（如 `mall-pm-group`）現可正確加入 itemMap，Phase ⑤ 才能找到父層並插入 reparented 項目
- **sidebar 同步修正** — `applyMenuConfig` 的 `customL2Here` 過濾條件同步調整，移除 `custom_` 前綴限制，改為排除 `baseL2KeysForParent`（當前 L1 的 base 子項）與 `baseL1Keys`，確保舊版 key 的 L2 項目也出現在側邊欄

---

## [1.39.33] - 2026-04-28

### Added
- **自訂選單「數據準備中」佔位頁** — 點擊 `custom_*` key 的選單項目（尚未對應實際模組）時，導向 `/data-preparing` 顯示旋轉圖示 + 「數據準備中 / 此功能模組正在建置」訊息；MainLayout Menu onClick 攔截 `custom_` 前綴，Router 新增對應路由

---

## [1.39.32] - 2026-04-28

### Changed
- **高階主管 Dashboard / ★工項類別分析 提升為一階** — `/exec-dashboard` 與 `/work-category-analysis` 從 `luqun-repair`、`dazhi-repair` 兩個群組的子項移除，改為獨立一階選單項目，位置緊接在 Dashboard 之後；兩個工務群組各自僅保留自身 Dashboard 子項

---

## [1.39.31] - 2026-04-28

### Fixed
- **base 模組掛到三階時顯示路由 key（如 `/mall/dashboard`）** — `applyMenuConfig` 的 `buildItem` 新增 `baseItemInfo` 查找表（遍歷 base L1/L2），label 優先序改為 `custom_label > base 原始 label > menu_key`，icon 同步取用 base 圖示

### Added
- **MenuConfig 刪除功能** — `custom_` 前綴項目右側新增紅色垃圾桶按鈕，搭配 `Popconfirm` 確認；若內含系統模組子項目，刪除時自動退回上一父層（`handleDeleteItem`）；pure custom 子項目則一併遞迴刪除

---

## [1.39.29] - 2026-04-28

### Fixed
- **新增 custom L2 不出現在側邊欄** — `applyMenuConfig` 在每個 base L1 的 children 中補入 `customL2Here`：從 `childrenByParent.get(parent.key)` 取出 `custom_` 前綴且 is_visible 的項目，以 `buildItem` 渲染（FileTextOutlined icon）後加入 children 並按 sort_order 排序
- **custom L2 移為 L3 後側邊欄可正確顯示** — base L2 的 grandchildren 注入邏輯原本就允許 custom_ 孫項目通過 filter，確認邏輯無誤

---

## [1.39.28] - 2026-04-28

### Changed
- **MenuConfig ↔ sidebar 同步架構重構** — 抽出 `computeReparentedL2()` 共用函式（export from MainLayout），`applyMenuConfig` 與 `buildWorkItems` 都呼叫同一份「哪個 L2 被換了父層」的判斷邏輯，不再各自維護，無法漂移
- **儲存後 MenuConfig 立即從 DB 重拉** — `handleSave` 在 `saveMenuConfig` 成功後呼叫 `fetchMenuConfig` 重建 items state，確保 MenuConfig 顯示與 DB 完全一致；同時發送 `menuConfigSaved` 事件讓 sidebar 同步

---

## [1.39.27] - 2026-04-28

### Fixed
- **MenuConfig 重新載入後移動過的項目回到原位** — `buildWorkItems` 新增 `reparentedL2` 邏輯：先掃 DB 找出 `parent_key` 與 base 結構不符的 L2 項目，建樹時從原 L1 排除，待 custom_ 項目注入後再插入新父層；解決「大直工務部 Dashboard / 樂群工務報修 Dashboard 移走後仍顯示在原群組」問題

---

## [1.39.26] - 2026-04-28

### Fixed
- **跨 L1 移動 base L2 項目後側邊欄不反映** — `applyMenuConfig` 新增 `reparentedBaseL2` 追蹤被換父層的 base L2 項目：
  - 原 L1 的 children 過濾時排除已移走的項目（避免在舊位置殘留）
  - 新 L1 的 children 注入被移來的項目（保留原始 icon 與 label）

---

## [1.39.25] - 2026-04-28

### Fixed
- **「移動到」按鈕完全無反應** — 根本原因：Select 的 `key` prop 包含 `moveOpen`，導致每次點擊時 key 變化觸發 remount，useState 重置，dropdown 永遠打不開。改用 Ant Design `Dropdown` + `Button` 取代 Select 偽裝按鈕，行為正確穩定；同時移除不再需要的 `moveOpen` state

---

## [1.39.24] - 2026-04-28

### Changed
- **選單管理結構同步機制重構** — `DEFAULT_MENU_STRUCTURE` 改為直接從 `MainLayout.menuItems` 派生（strip icon），不再手動維護第二份清單；sidebar 新增/移除路由後 MenuConfig 自動同步，「整棟巡檢」、「春大直商場工務巡檢」等已整合的舊 L1 群組不再出現

### Fixed
- `mall-facility-inspection`、`full-building-inspection` L1 群組殘留問題：因現在直接讀 menuItems，這兩個已不在 sidebar 的 L1 群組自然消失

---

## [1.39.23] - 2026-04-28

### Fixed
- **「移動到」按鈕不一定出現** — 移除一階項目「必須無子項目才顯示移動選項」的限制；一階項目現在永遠可選擇移到其他群組下（子項目一併跟著成為三階）
- **「移動到」重複選同一選項無反應** — Select 改用 `value={undefined}` 並加 `key` prop，確保每次開啟都重置選中狀態

---

## [1.39.22] - 2026-04-28

### Fixed
- **選單管理模組顯示已整合的舊路由** — 從 `DEFAULT_MENU_STRUCTURE` 的 `mall` 群組移除已整合為 Tab 的舊子路由（`/mall/b4f-inspection`、`/mall/rf-inspection`、`/mall/b2f-inspection`、`/mall/b1f-inspection`）
- **DB 殘留項目死而復生** — `buildWorkItems` 的 extra DB 注入邏輯改為只插入 `custom_` 前綴項目，非 custom 的 DB 殘留紀錄不再被撿回；使用者下次儲存後 DB 將自動清除舊紀錄

---

## [1.39.21] - 2026-04-28

### Fixed
- **側邊欄與選單管理模組不同步** — 儲存後立即透過 `menuConfigSaved` 自訂事件通知 `MainLayout` 重新載入，無需手動重新整理頁面
- **側邊欄多出基底項目（附圖二）** — `customL1` 注入邏輯改為只注入 `custom_` 前綴的使用者自建項目，防止 `mall-facility-inspection`、`full-building-inspection` 等基底 key 被錯誤注入為文件圖示獨立選單

---

## [1.39.20] - 2026-04-28

### Changed
- **春大直商場工務巡檢整合（商場管理）** — 將「春大直商場工務巡檢」獨立群組（原含 Dashboard + 4F/3F/1F~3F/1F/B1F~B4F 五個子頁面）整合為商場管理群組下的單一「春大直工務巡檢」入口
  - `MallFacilityInspection/index.tsx` 全面重寫：新增 `type="card"` 六 Tab 架構（統計總覽 / 4F / 3F / 1F~3F / 1F / B1F~B4F 巡檢紀錄）
  - 各樓層 Tab 共用 `FloorListTab` 元件；使用真實 API（`fetchMallFacilityBatches` + `syncMallFacilityFromRagic`）；懶載入，首次切入才掛載
  - 統計總覽 Tab 保留原有真實 API 呼叫（`fetchMallFacilityDashboardSummary` + `syncMallFacilityAllFromRagic`）
  - `MainLayout` 側邊欄「春大直商場工務巡檢」獨立群組移除；改於「商場管理」群組下新增 `/mall-facility-inspection/dashboard` 子項目（第三個，排於整棟巡檢之後）
  - `navLabels.ts` `mallFacilityDashboard` 改名為「春大直工務巡檢」
  - Breadcrumb 更新為「商場管理 › 春大直工務巡檢」
  - URL query param `?tab=summary|4f|3f|1f-3f|1f|b1f-b4f` 支援直接導航至指定 Tab

---

## [1.39.19] - 2026-04-28

### Changed
- **整棟巡檢整合（商場管理）** — 將「整棟巡檢」群組（原含 Dashboard + RF/B4F/B2F/B1F 四個獨立子頁面）整合為商場管理群組下的單一「整棟巡檢」入口
  - `FullBuildingInspection/index.tsx` 全面重寫：新增 `type="card"` 五 Tab 架構（統計總覽 / RF 巡檢 / B4F 巡檢 / B2F 巡檢 / B1F 巡檢）
  - 各樓層 Tab 共用 `FloorInspectionListTab` 元件（月份篩選、重新整理、同步 Ragic、場次列表）；懶載入，首次切入才掛載
  - `MainLayout` 側邊欄「整棟巡檢」獨立群組移除；改於「商場管理」群組下新增 `/full-building-inspection/dashboard` 子項目
  - `navLabels.ts` `fullBuildingDashboard` 改名為「整棟巡檢」（去除「Dashboard」後綴）
  - Breadcrumb 從原「整棟巡檢群組」更新為「商場管理 › 整棟巡檢」
  - URL query param `?tab=summary|rf|b4f|b2f|b1f` 支援直接導航至指定 Tab

---

## [1.39.18] - 2026-04-28

### Changed
- **商場管理整合（商場週期保養）** — 將「商場管理」群組原有的六個獨立子頁面（商場週期保養、B4F / RF / B2F / B1F 巡檢紀錄、Dashboard）整合為單一「商場週期保養」頁面
  - `MallDashboard/index.tsx` 全面重寫：新增 `type="card"` 六 Tab 架構（統計總覽 / 週期保養 / B4F 巡檢 / RF 巡檢 / B2F 巡檢 / B1F 巡檢）
  - 各巡檢 Tab 支援月份篩選、重新整理、同步 Ragic；切換 Tab 時懶載入資料（首次切入才呼叫 API）
  - `MainLayout` 側邊欄「商場管理」群組簡化為單一入口 `/mall/dashboard`，移除五個個別子選單
  - `navLabels.ts` `mallDashboard` 改名為「商場週期保養」
  - Detail 路由（`/:batchId`）與後端 API 不變，各模組明細頁保持原有功能

---

## [1.39.17] - 2026-04-28

### Added
- **選單管理（系統設定 → 選單管理）**
  - 新增 `menu_configs` / `menu_config_history` 資料表與後端 Router（`GET/PUT /api/v1/settings/menu-config`、`GET /api/v1/settings/menu-config/history`）
  - 前端新增 `/settings/menu-config` 頁面：拖拉調整一級群組與各子選單順序（`@dnd-kit/sortable`）、雙擊或點擊鉛筆 inline 改名、DragOverlay 懸浮預覽
  - 儲存時自動記錄變更差異（diff_json）與全量快照（snapshot_json），保留最近 5 筆歷史；右側 Drawer 顯示操作者、時間與詳細 diff
  - `MainLayout` 啟動時靜默拉取設定，動態合併自訂 label 與排序；拉取失敗時 fallback 至預設值不影響使用
  - 安裝 `@dnd-kit/core` v6、`@dnd-kit/sortable` v10、`@dnd-kit/utilities` v3
  - **新增選單**：「新增一階選單」按鈕（Header）與各群組內「新增子選單」按鈕，自動產生 `custom_${timestamp}` key，輸入顯示名稱即可建立
  - **隱藏/顯示**：每列新增眼睛圖示（`EyeOutlined`/`EyeInvisibleOutlined`）；隱藏父層時子層一併隱藏；隱藏項目以刪除線 + 灰底 + "已隱藏" Tag 標示；`MainLayout` 同步過濾 `is_visible: false` 項目不顯示於側邊欄
  - **跨層移動**：子項目可升為一階選單或移到其他父層下；無子項目的一階選單可降為任一父層的子選單；使用 `ArrowsAltOutlined` 圖示 + Ant Design `Select` Dropdown 操作
  - **三層結構支援**：選單管理與側邊欄均支援三層結構（一階群組 → 二階子選單 → 三階孫選單）；每個二階列新增「新增子選單」按鈕；移動選項涵蓋三層間任意升降；`MainLayout.applyMenuConfig` 及 `openKeys` 同步更新支援三層展開
  - **UI 整理**：新增圖示說明列（拖拉/改名/顯隱/移動）、各行顯示一/二/三階色票 Tag、新增按鈕依階層配色（藍/綠/橘）、Modal 標題顯示目標階層與父層名稱、修正更名 Bug（移除 onBlur 衝突、InputRef 型別、custom_ 項目清空邏輯）

---

## [1.39.16] - 2026-04-28

### Fixed
- **RagicAppDirectory（Ragic 應用程式對應表）**
  - 搜尋邏輯補入 `url` 欄位，現在可用 Ragic URL 路徑（如 `luqun-public-works-repair-reporting-system/6`）在 Search 框直接查到對應項目
  - Ragic URL 欄由純圖示改為「圖示 + 路徑文字（截斷）」，Tooltip 顯示完整 URL；欄寬 80 → 220px
  - 搜尋框 placeholder 補充提示「Ragic URL」可搜
  - `scroll.x` 1320 → 1460 配合欄寬調整

---

## [1.39.15] - 2026-04-27

### Added
- **共用元件 `src/components/ExecMetrics/index.tsx`**
  - 匯出 `HeroKpi`（單張 KPI 卡）、`ExecHeroLayer`（6 KPI 卡網格）、`ExecSourceCards`（來源小卡列）、`SOURCE_PIE_COLORS`
  - 預設匯出 `ExecMetricsCard`：自帶資料的主管指標摘要卡，沿用 `@/api/workCategoryAnalysis` fetchStats，不新增任何 API

### Changed
- **Dashboard（集團管理總覽）**
  - 原「預算管理」區塊暫時隱藏（`HIDDEN_BUDGET` 註解保留，程式碼與 API 路由不刪除）
  - 插入 `ExecMetricsCard` 至原預算管理位置（最上方）
- **ExecDashboard（高階主管 Dashboard）**
  - `HeroKpi`、`SOURCE_PIE_COLORS`、`HeroLayer`、`SourceCards` 改用共用元件，消除重複定義
  - 頁面顯示與行為與重構前完全一致

### Fixed
- `@/api/workCategoryAnalysis` `CategoryStats.meta` 型別補上 `last_sync_at?: string`，消除 ExecDashboard TS2339 錯誤

---

## [1.39.16] - 2026-04-26

### Added
- **dazhi + luqun 4.1 報修統計 — 新增「上月累計完成數（① - ②）」列**
  - 公式：上月累計未完成 - 上月未完成本月結案數 = 本月後仍滾存的未結案件數
  - 位置：插入在①（上月累計未完成）和②（本月結案數）之間
  - 可點擊展開明細：顯示從上月累計未完成中，本月未結案的案件清單

---

## [1.39.15] - 2026-04-26

### Fixed
- **大直工務部 — 本月工時統計 KPI 永遠顯示 0.00 hr**
  - 根因：`dazhi_repair_service.py` 讀工時欄位用 `raw.get("維修天數", "")` ，但 Ragic 實際欄位名為 `"維修天數(天)"`（含括號），導致永遠讀不到值
  - 修正：改為 `raw.get("維修天數(天)") or raw.get("維修天數", "")` 兼容兩種名稱
  - 修復後需執行一次手動同步（Settings → 同步大直工務部）讓 DB `work_hours` 欄位更新

---

## [1.39.14] - 2026-04-26

### Changed
- **dazhi + luqun Dashboard — 高工時/高費用 Top 10 加結案狀態圖示**
  - 每筆案件標題右側加小圖示：✅ 綠色 `CheckCircleOutlined`（已結案）/ 🕐 橘色 `ClockCircleOutlined`（未結案）
  - 滑鼠 hover 顯示 tooltip（「已結案」/「未結案」）
  - 不拆分清單，不動版型與其他模組

---

## [1.39.13] - 2026-04-26

### Fixed
- **大直工務部 明細 Tab — 報修詳情 Drawer 新增「維修圖片」顯示**
  - 找出根本原因：`DetailTab` 內的 inline Drawer（第 1704 行）從未包含「維修圖片」欄，先前修改均針對錯誤的 `CaseDetailDrawer` 函式元件
  - 在 `DetailTab` 新增 `drawerImages` / `drawerImgLoading` state + `useEffect` 呼叫 `fetchCaseImages`（DB-first）
  - inline Drawer 末尾新增「維修圖片」`Descriptions.Item`，支援縮圖預覽（`Image.PreviewGroup`）

---

## [1.39.12] - 2026-04-26

### Fixed
- **dazhi + luqun 報修詳情 Drawer — 維修圖片顯示邏輯修正**
  - 修正渲染順序：圖片優先顯示（`images.length > 0` 先判斷），loading spinner 只在「DB 無圖且正在抓 Ragic」時才出現
  - dazhi Drawer `useEffect`：若 `caseData.images` 已有資料則跳過 Ragic lazy-fetch；優先用 DB 圖片（`dbImages > liveImages`）
  - luqun Drawer 同步修正渲染順序（邏輯原已正確，統一調整呈現優先順序）

---

## [1.39.11] - 2026-04-26

### Fixed
- **Session 過期自動跳轉登入頁**
  - `PrivateRoute`：新增 JWT 過期主動偵測（掛載時、每 60 秒、切回分頁時），過期立即 `logout()` + 導向 `/login`
  - `apiClient`：401 攔截器改呼叫 `useAuthStore.getState().logout()` 同步清除 store；加入 `_redirecting` flag 避免同批次多次跳轉
  - `main.py`：靜態檔案服務改 SPA 模式，未知路徑一律回傳 `index.html`，修正直接存取前端路由（如 `/dazhi-repair/dashboard`）會 404 的問題

---

## [1.39.11] - 2026-04-26

### Fixed
- **大直工務部 `dazhi_repair_case` — 完整建置 images_json 鏈路**
  - Model：新增 `images_json TEXT` 欄位、`_parse_images_json()` 方法、`to_dict()` 加入 `"images"` 欄位
  - Sync：`dazhi_repair_sync.py` UPDATE & INSERT 路徑均寫入 `images_json = json.dumps(case.images)`
  - Migration：`main.py` 新增 `_migrate_dazhi_repair_images()`，啟動時自動為舊 DB 補欄位
  - Drawer 圖片顯示路徑：`caseData.images`（DB 同步值）→ lazy-fetch `/images/{ragic_id}`（即時 fallback）

---

## [1.39.10] - 2026-04-26

### Fixed
- **樂群報修詳情 Drawer — 維修圖片（三次修正）：改呼叫正確的 Ragic sheet**
  - 根本原因：圖片 attachment 欄位在 `lequn-public-works/8`（form view），不在清單 sheet `luqun-public-works-repair-reporting-system/6`；原端點呼叫 `/6`，永遠取不到圖片
  - 新增 `RAGIC_LUQUN_REPAIR_IMAGE_PATH=lequn-public-works/8`（.env + config.py）
  - 端點 `/case-images/{ragic_id}` 改用新的 `img_adapter`（指向 `/8`），邏輯與大直 `/images/{ragic_id}` 完全一致：Step1 找 numeric_id → Step2 fetch detail → Step3 解析圖片欄位
  - 搜尋欄位清單：`["上傳圖片", "上傳圖片.1", "維修照上傳", "維修照", "圖片"]`
  - 無圖時仍回傳 `raw_keys` + `img_like_fields` + `raw_data` 供診斷

---

## [1.39.9] - 2026-04-26

### Fixed
- **樂群報修詳情 Drawer — 維修圖片（二次修正）：lazy-fetch 直接向 Ragic 抓**
  - 根本原因：Ragic 圖片欄位在 main list 不保證存在，sync 時有可能抓不到
  - 後端：新增 `GET /api/v1/luqun-repair/case-images/{ragic_id}` 端點，直接呼叫 `adapter.fetch_one()` 解析圖片，不依賴 DB 或 cache
  - 前端 `CaseDetailDrawer`：`useEffect` 監控 `ragic_id`，若 `caseData.images` 為空則自動呼叫新端點；圖片載入中顯示 Spin；載入完顯示縮圖；「維修圖片」欄位始終顯示（改為固定 row）
  - `api/luqunRepair.ts`：新增 `fetchCaseImages()` 封裝函式

---

## [1.39.8] - 2026-04-26

### Added
- **KPI Tooltip — 各儀表板 KPI 卡新增「?」說明圖示**
  - 新增獨立說明檔：`constants/kpiDesc/luqunRepair.ts`、`dazhiRepair.ts`、`securityDashboard.ts`、`mallDashboard.ts`
  - 樂群、大直 `KpiCard` 元件加入 `desc` prop + `QuestionCircleOutlined` Tooltip；保全巡檢、商場管理同步套用
  - 完全不改動版型、顏色、欄位，僅在標題旁附加說明圖示
- **照片縮圖 + Modal — 樂群 / 大直報修 Drawer 圖片改為縮圖預覽**
  - 從文字連結（`<a>` 📷）升級為 72×72 縮圖（`antd Image`）+ `Image.PreviewGroup` 輪播放大
  - 大直保留 `imgLoading` loading 狀態，僅替換渲染方式

---

## [1.39.8] - 2026-04-26

### Fixed
- **樂群報修詳情 Drawer — 維修圖片不顯示（images 永遠空陣列）**
  - 根本原因：`LuqunRepairCase` ORM 的 `to_dict()` 回傳 `"images": []`，images 資料從未同步至 SQLite
  - `luqun_repair.py`：新增 `images_json` (Text, nullable) 欄位；`to_dict()` 改從 `_parse_images_json()` 讀取；`_parse_images_json()` 安全 JSON 解析，例外時回傳 `[]`
  - `main.py`：新增 `_migrate_luqun_repair_images()` — ALTER TABLE 補欄位，startup 自動執行
  - `luqun_repair_sync.py`：sync 時將 `case.images` 序列化為 JSON 存入 `images_json`（existing + insert 兩段均補上）

---

## [1.39.7] - 2026-04-26

### Fixed
- **樂群 金額統計 Tab — 扣款專櫃改為家數統計、排除月份小計**
  - 後端 `compute_fee_stats`：`deduction_counter` 從「費用加總」改為「當月唯一專櫃家數（整數）」；全年小計跨月去重；`month_totals` / `grand_total` 僅加三個金額欄位（委外/維修/扣款費用）
  - 前端 月份格顯示「N 家」、全年小計欄顯示「N 家」；月份小計行不含此欄（後端已排除）；drilldown Modal Tag 改顯示家數

---

## [1.39.6] - 2026-04-26

### Fixed
- **樂群 Dashboard — 扣款專櫃 KPI 卡改為全年統計**
  - `luqun_repair_service.py` 新增 `annual_counter_fee`、`annual_counter_store_names` 欄位（對應既有 `annual_deduction_counter` 年度邏輯）
  - `DashboardKpi` 介面（`types/luqunRepair.ts`）補上 `annual_counter_stores`、`annual_counter_fee`、`annual_counter_store_names` 型別宣告
  - 前端 KPI 卡、Modal 標題/Tag/dataSource 全部切換至全年欄位；「當月金額」摘要卡仍保留月度 `total_counter_stores`（語義正確）

---

## [1.39.5] - 2026-04-26

### Changed
- **工項類別分析 + 主管 Dashboard — 納入 IHG 客房保養工時**
  - `work_category_analysis.py` 新增第 4 個資料來源 `ihg_room`（`IHGRoomMaintenanceMaster`），零前端改動
  - 工時取自 `raw_json["工時計算"]`（分鐘 ÷ 60），與 IHG `/matrix` 端點同一計算邏輯
  - 類別固定為「例行維護」；日期優先取 `maint_date`，無效則以年/月第 1 日為 fallback
  - `SOURCE_LABELS` 新增 `ihg_room: "IHG客房保養"`
  - `_parse_sources("all")` / `_build_kpi()` / `_build_source_breakdown()` / `get_years()` 同步更新
  - `ExecDashboard` 與 `WorkCategoryAnalysis` 共用同一 `/stats` API，**無需前端修改，自動取得新數據**
  - 若 IHG API 回傳空值（無工時記錄），Dashboard 視為 0.00 hr，不影響其他分類統計

---

## [1.39.4] - 2026-04-26

### Added
- **IHG 客房保養 — 季度視角（`?view=quarter`）**
  - 前端 `useMemo` 對 `/matrix` 資料做季度聚合，無需新 API；每季彙總 `normal/done/maint/unchecked` 計數與工時
  - 新增 `QuarterCellComp`：88×66px 格子，顯示季度計數＋工時（hr）＋所涵蓋月份；狀態顏色與月份視角一致
  - 篩選列新增 **月份 ｜ 季度** `Segmented` 切換，更新 URL 參數 `?view=quarter`
  - 季度 Table header 顯示 Q1–Q4 及各季工時合計（hr）
  - 點擊季度格開啟**季度彙整 Drawer**：顯示合計統計摘要，各月份明細表含狀態 Tag、各計數、工時，「查看」按鈕穿透至月份明細 Drawer
  - Card 標題同步顯示「月份視角 / 季度視角」文字提示

---

## [1.39.6] - 2026-04-26

### Added
- **KPI 卡說明 Tooltip（樂群 & 大直工務報修 Dashboard）**
  - 每張 KPI 卡標題右側新增 `?` 圖示，hover 顯示說明文字，不影響原有版型與樣式
  - 說明文字獨立維護於 `frontend/src/constants/kpiDesc/luqunRepair.ts` 及 `dazhiRepair.ts`，方便各模組獨立調整
  - 涵蓋 6 張 KPI 卡：本月相關案件、已完成件數、未完成件數、平均結案天數、本月工時統計、客房報修件數

### Fixed
- IHG 保養表季度視角：確認已實作（`?view=quarter` URL 參數，前端聚合，不需新 API）；於 FEATURE_MAP 標記完成

---

## [1.39.3] - 2026-04-26

### Fixed
- **前端 API client 統一**：`securityPatrol.ts`、`mallFacilityInspection.ts` 改用 `apiClient`（帶 JWT interceptor），不再直接用裸 `axios`，確保 API 請求正確帶 `Authorization: Bearer` header
- **DEV bypass token 修正**：`Login/index.tsx` 的 `devLogin()` 改呼叫真實後端 `admin/admin1234`，不再寫入無效 `'dev-token'` 造成後續所有 API 返回 401
- **商場巡檢 0/0 = 0% 顯示修正**：
  - 後端 `FloorInspectionStats` schema 新增 `has_data: bool` 欄位，`_floor_stats_for_date()` 依 `len(batches) > 0` 設定
  - 前端 `FloorInspectionStats` 型別同步補上 `has_data: boolean`
  - 商場 Dashboard 樓層卡片：`has_data=false` 時改顯示「尚無資料」而非進度條 0%
  - KPI「已完成巡檢」sub-label：無資料時顯示「尚無巡檢資料」而非「完成率 0%」

## [1.39.2] - 2026-04-26

### Security
- **全域 API 身份驗證補強（安全性修正）**
  - 19 個業務 router 補上 `APIRouter(dependencies=[Depends(get_current_user)])`，未登入無法讀取任何業務資料
  - 受保護 router 清單：luqun_repair、dazhi_repair、ihg_room_maintenance、b1f/b2f/b4f/rf_inspection、periodic_maintenance、mall_periodic_maintenance、room_maintenance、room_maintenance_detail、security_patrol、security_dashboard、mall_dashboard、mall_facility_inspection、inventory、calendar、work_category_analysis、full_building_inspection
  - 30 個 sync/debug endpoint（`POST /sync`、`GET /debug-raw`、`GET /debug/ragic-raw`、`GET /raw-fields`、`GET /ping`、`GET /sync` 診斷版等）加上 `require_roles("system_admin", "module_manager")`，防止一般使用者觸發 Ragic 同步或讀取診斷資料

---

## [1.39.1] - 2026-04-24

### Changed
- **IHG 客房保養 — 矩陣格顯示優化與異常狀態**
  - 後端 `/matrix` endpoint：解析每筆記錄 `raw_json`，統計值為「正常」/「當時維護完成」/「等待維護(待料中)」的欄位數量，回傳 `normal_count`/`done_count`/`maint_count`
  - 若任一欄位 = 「等待維護(待料中)」（`maint_count > 0`），格子狀態覆蓋為 `abnormal`（橘色區隔，獨立於逾期紅）
  - 前端矩陣格由「圖示＋日期」改為顯示「正常 X / 完成 Y / 維護 Z ＋日期」計數摘要；維護數 > 0 時以橘色加粗顯示
  - 新增 `STATUS_CFG.abnormal`：bg `#fff7e6`、text `#d46b08`、tagColor `warning`
  - 明細 Drawer：有「等待維護(待料中)」欄位時，在 Ragic 原始欄位區塊上方顯示「維護異常項目」表格，異常列以橘色加粗標示

---

## [1.39.0] - 2026-04-24

### Added
- **IHG 客房保養模組（新功能）**
  - 後端 ORM：`ihg_rm_master`（保養主表）+ `ihg_rm_detail`（子表格明細），對應 Ragic `periodic-maintenance/4`
  - 同步服務：`ihg_room_maintenance_sync.py`，支援 Master + Detail 兩段同步，upsert 策略避免重複寫入
  - API Router：`/api/v1/ihg-room-maintenance`，端點：`/matrix`、`/stats`、`/records`、`/sync`、`/debug-raw`、`/{ragic_id}`
  - 前端頁面：`/hotel/ihg-room-maintenance`，年度保養矩陣表（房號×月份），KPI 統計卡，狀態顏色（已完成/逾期/本月應保養/未完成），點擊格子顯示明細 Modal
  - 篩選功能：年度 / 樓層 / 狀態
  - 同步按鈕：手動觸發 Ragic 同步，自動排程每 30 分鐘執行
  - 新增 `config.py`：`RAGIC_IHG_RM_SERVER_URL/ACCOUNT/SHEET_PATH`
  - Menu 位置：飯店管理 → 1. 飯店週期保養表 → **2. IHG客房保養**（緊接其後）
  - Ragic App Directory 更新：item 204 (`periodic-maintenance/4`) → 對應 `ihg_rm_master + ihg_rm_detail`

---

## [1.38.9] - 2026-04-25

### Changed
- **4.3 報修類型 Tab — 類別定義與說明文字同步更新（樂群 & 大直）**
  - `REPAIR_TYPE_ORDER`：新增 5 個類別（凍&藏類設備、內裝、廚房&吧台設備、會議設備、瓦斯類設備），插入於「專櫃」之後、「公區」之前
  - `REPAIR_TYPE_EXAMPLES`：所有類別內容依規格書 Markdown 表格全面更新（建築/衛廁/消防/機電/給排水/排煙/弱電/照明/公區/後勤空間 均有補充）
  - 前端欄位標題「內容舉例」→「MD內容」（LuqunRepair & DazhiRepair 皆更新）

## [1.38.8] - 2026-04-25

### Fixed
- **樂群工務報修 — 所有明細彈跳視窗統一加入「詳情」功能**
  - 委外+維修費用明細（全年）：寬度 900→1100、加詳情欄、加狀態欄、改分頁顯示、加 scroll
  - 扣款費用明細（全年）：寬度 760→1050、加詳情欄、加狀態欄、改分頁顯示、加 scroll
  - 費用明細（金額統計 drilldown）：寬度 800→1100、加詳情欄、加 scroll、新增 CaseDetailDrawer
  - CaseListModal：`scroll={{ x: 880 }}` 改為 `scroll={{ x: 'max-content' }}` 避免固定寬截斷

## [1.38.7] - 2026-04-25

### Fixed
- **報修詳情 — 管理單位回應 HTML 正確渲染**
  - `luqun_repair_service.py` 新增 `_ragic_html()` 函式：將 Ragic 以方括號儲存的 HTML tag（如 `[br]`、`[table]`、`[/td]`）還原為正常 HTML
  - `LuqunRepair/index.tsx` 詳情 Modal 與 Drawer 的「管理單位回應」欄位：改用 `dangerouslySetInnerHTML` 渲染，顯示格式化的 HTML 內容而非原始 tag 字串

## [1.38.6] - 2026-04-24

### Fixed
- **工項類別分析 / 高階主管 Dashboard — 時間規則與筆數對齊 luqun/dazhi dashboard**
  - `work_category_analysis.py` 新增 `_stat_dt_for(c)` 輔助函式
  - `_load_all` luqun / dazhi 段：year/month/day 改以 stat-month 為準（`completed_at` 優先，未完成用 `occurred_at`），與 luqun-repair/dazhi-repair dashboard 統計規則一致
  - `WorkCategoryAnalysis/index.tsx` 每月累計表（Tab C）：未來月份顯示 `—`
  - `ExecDashboard/index.tsx` 每月累計工時表：未來月份顯示 `—`

## [1.38.5] - 2026-04-24

### Fixed
- **大直工務部（dazhi-repair）時間規則修正，與樂群保持一致**
  - `dazhi_repair_service.py` 新增 `_completed_by` / `_completed_in` / `_closed_in` 輔助函式
  - `compute_repair_stats`：改以 `completed_at` 時間戳判斷完成，不再用 `is_completed_flag`（當前狀態）；跨月完工案件正確歸屬至完工月
  - `compute_closing_time`：改以 `_closed_in(c, y, m)` 判斷結案月，不再用 `filter_cases + is_completed_flag`
  - `query_detail`：年月篩選改用 `_stat_year/_stat_month`（完工月＋未完成報修月），與 Dashboard 邏輯一致
  - `DazhiRepair/index.tsx` Tab 4.1：未來月份欄位顯示 `—`，不顯示不合理數字
  - `DazhiRepair/index.tsx` Tab 4.2：小型／中大型表格未來月份欄位顯示 `—`

## [1.38.4] - 2026-04-23

### Fixed
- **大直工務部（lequn-public-works/8）欄位對應全面修正**
  - 依附圖「工程維修單 房務部查閱用」確認實際 Ragic 欄位
  - `dazhi_repair_service.py` 工時計算：改以 `維修天數`（天 ×24）為主欄位，`花費工時` 降為備用
    - 原邏輯：`花費工時` 優先 → `維修天數` 備用（但該 Ragic Sheet 無「花費工時」欄位，導致工時全部為 0）
  - `work_category_analysis.py` 大直人員：`c.responsible_unit`（反應單位=部門）→ `c.closer`（維修人員=執行人）
    - 原因：反應單位為「房務部」等部門名稱，維修人員才是「吳友仁」等個人姓名
  - `RagicAppDirectory.tsx` 對應表修正：
    - `LOCAL_TABLE_MAP`：新增 `88: 'dazhi_repair_case'`（lequn-public-works/8 為實際同步來源）
    - `PORTAL_DEFAULTS`：itemNo 87、88 改為「大直工務部 / /dazhi-repair/dashboard」（原錯標為樂群工務報修）

## [1.38.3] - 2026-04-23

### Fixed
- **工項類別分析 — 工時計算邏輯統一修正**
  - 工時來源改為：① `花費工時`（HR，直接用）→ ② `工務處理天數`（天 ×24）
  - 人員來源維持：`responsible_unit`（= Ragic `處理工務`）
  - `luqun_repair_service.py`：
    - `RK_WORK_HOURS = "花費工時"`（主欄位）；`__init__` 手動 fallback `工務處理天數 ×24`
  - `dazhi_repair_service.py`：
    - `RK_WORK_HOURS = "花費工時"`（主欄位）；`__init__` 手動 fallback `工務處理天數 / 維修天數 ×24`
    - 恢復 ×24 換算邏輯（上版錯誤移除，天數直存導致數值偏低）
  - `work_category_analysis.py`（Router）：aggregation 邏輯不變，僅更新注解

## [1.38.2] - 2026-04-23

### Fixed
- **工項類別分析 / 高階主管 Dashboard — 人員與工時欄位映射修正**
  - **原錯誤欄位**：人員 = `reporter_name`（報修同仁）；工時 = `花費工時`（luqun）/ `維修天數 × 24`（dazhi）
  - **現正確欄位**：人員 = `responsible_unit`（= Ragic `處理工務`）；工時 = `work_hours`（= Ragic `工務處理天數`）
  - `luqun_repair_service.py`：
    - `RK_WORK_HOURS` 改為 `"工務處理天數"`（原 `"花費工時"`），alias fallback 保留
    - `RK_RESPONSIBLE` alias 已含 `"處理工務"`（首位），無需改動
  - `dazhi_repair_service.py`：
    - `RK_WORK_HOURS` 改為 `"工務處理天數"`（原 `"維修天數"`），移除 `× 24` 轉換
    - `RK_RESPONSIBLE` alias 補入 `"處理工務"` 為首位（原首位 `"反應單位"` 降為備用）
  - `work_category_analysis.py`（Router）：
    - 樂群、大直 `_load_all` 中 `person` 改為 `c.responsible_unit`（原 `c.reporter_name`）
  - hotel_room（房務保養）來源不受影響（仍用 `staff_name`）

## [1.38.1] - 2026-04-23

### Changed
- **高階主管 Dashboard UI 調整**
  - 名稱：「◆ 工項工時 董事長 Dashboard」→「高階主管 Dashboard」
  - 主題：黑金深色背景 → Portal 標準風格（依 PROTECTED.md：白卡、`#1B3A5C` 主色、`#f0f4f8` 頁面背景）
  - 移除全域深色 CSS 覆寫（`.exec-db` 前綴），改用 Ant Design 標準 Card / Table / Collapse
  - 所有內容邏輯（KPI、圖表、表格、決策提示、篩選列）完全保留

## [1.38.0] - 2026-04-23

### Added
- **◆ 董事長簡報 Dashboard（全新獨立功能）**  route: `/exec-dashboard`
  - 既有 `★工項類別分析`（`/work-category-analysis`）完全保留，未修改任何邏輯
  - 資料層：直接沿用現有 `workCategoryAnalysis` API，零後端改動
  - 黑金駕駛艙三層設計：
    - 第一層 Hero KPI：本期總工時（48px 超大字）、人均工時、最高類別、最高人員、最高來源、MoM 環比（紅/綠箭頭）
    - 第二層 2×3 圖表：工項趨勢折線、類別 Donut、人員 Top10 橫柱（依來源著色）、類別×人員 Stacked、來源 Donut+快速卡、集中度進度條
    - 第三層 明細表格（Collapse 可收合）：每日累計、每月累計、人員工時%、人員排名詳細表（支援排序）
    - 自動決策提示：集中度 > 70% 🔴、現場報修 > 40% 🟡、環比 ±25% 🟡、分布正常 🟢
    - 五維篩選工具列（年/月/來源/類別/人員）
    - 全域 CSS 覆寫（深色表格 / Collapse / Select）僅作用於 `.exec-db` 前綴，不影響其他頁面

## [1.37.0] - 2026-04-23

### Changed / Added
- **★工項類別分析 → 升級為主管決策 Dashboard（v2）**
  - 架構原則：單一路由 `/work-category-analysis`，樂群/大直選單共用同一 page
  - 資料整合：三來源合一（樂群工務 + 大直工務 + 房務保養 `RoomMaintenanceDetailRecord`）
    - 房務保養 work_hours 單位為分鐘，自動 ÷60 轉小時；日期從 `maintain_date` string 解析
    - 工項類別：房務保養固定歸入「每日巡檢」；工務報修依 title/repair_type 關鍵字分類
  - 後端 Router 升級：`/stats` 回傳 7 大資料塊
    - `kpi`：總工時、案件數、人員數、平均人工時、最高類別、最高人員、來源占比、環比%
    - `chart_data`：5 類別趨勢折線（月份/日）
    - `category_breakdown`：類別占比（圓餅圖）
    - `person_ranking`：整合三來源人員排名（Top 20）
    - `category_person_matrix`：類別×人員交叉（Stacked Bar，Top 12 人）
    - `source_breakdown`：樂群/大直/房務各自工時、占比、案件數、人員數
    - `concentration`：前3/5/10人佔比、集中度風險警示
    - 表格資料支援 `sources`/`category`/`person` 複合篩選
  - 前端 Dashboard 三層版型：
    - 第一層（KPI Cards）：總工時+環比、案件數、平均人工時、最高類別、最高人員、集中度警示
    - 第二層（Charts）：趨勢圖、圓餅圖、人員排名橫柱圖、類別×人員 stacked bar、來源分析、集中度
    - 第三層（Tables）：每日累計、每月累計、人員工時%、人員排名詳細表
  - 篩選列：年度、月份、來源別、類別、人員（五維篩選）

## [1.36.0] - 2026-04-23

### Added
- **★工項類別分析 新功能模組**
  - 新增後端 `/api/v1/work-category-analysis/`（Router：`work_category_analysis.py`）
    - `GET /years`：整合樂群+大直有資料的年份清單
    - `GET /persons`：依總工時降冪排序的人員清單
    - `GET /stats`：主統計端點，回傳曲線圖/日累計/月累計/人員%四組資料
  - 工項類別分類邏輯：依 title/repair_type 關鍵字歸類為 現場報修／上級交辦／緊急事件／例行維護／每日巡檢；無匹配預設「現場報修」
  - 新增前端頁面 `WorkCategoryAnalysis`（`/work-category-analysis`）
    - A. Dashboard：5 類別折線圖（全年=月份趨勢；選月=日趨勢）
    - B. 每日累計工時表（1~30 日＋星期行＋TOTAL＋%）
    - C. 每月累計工時表（1~12 月＋TOTAL＋%）
    - D. 每月累計工時人員%表（動態人員清單）
  - Menu 掛載：分別加入「樂群工務報修」與「大直工務部」子選單，路由共用同一頁面

## [1.35.14] - 2026-04-24

### Fixed / Added — 樂群工務報修「扣款專櫃」全面修正

**問題根源：** `扣款專櫃` 欄位存放的是**專櫃名稱**（如"牪肉舖"），不是金額。
原程式 `_float("牪肉舖") = 0`，導致 Dashboard 永遠顯示 `$0`。

**後端 `luqun_repair_service.py`：**
- 新增 `RK_MGMT_RESPONSE = "管理單位回應"`
- 新增 `_parse_counter_stores()` helper：解析"多櫃"→讀管理單位回應逐行取店名
- `RepairCase` 新增 3 個欄位：`deduction_counter_name`、`counter_stores`、`mgmt_response`
- `deduction_counter` 保持 0（介面相容），不再錯誤轉換名稱為 float
- `compute_dashboard` 改為計算本月**有扣款的專櫃家數**（`total_counter_stores`）及列表
- `annual_counter_detail` 改用 `deduction_fee > 0 AND deduction_counter_name` 篩選

**前端 `luqunRepair.ts`：** 新增型別 `deduction_counter_name`、`counter_stores`、`mgmt_response`、`total_counter_stores`、`counter_store_names`、`kpi_counter_stores_detail`

**前端 `LuqunRepair/index.tsx`：**
- Dashboard 扣款專櫃卡片：顯示「X 家」（本月有扣款專櫃數）+ 前 2 家名稱
- 扣款專櫃明細彈窗：顯示店名 Tag + 管理單位回應 + 扣款費用
- `CASE_LIST_COLS`：新增「扣款專櫃」欄位（出現在所有 CaseListModal）
- `CaseDetailDrawer`：新增扣款專櫃、各專櫃（多櫃展開）、管理單位回應

## [1.35.13] - 2026-04-24

### Added / Fixed — 大直工務部 Dashboard 邏輯對齊樂群

**Excel 驗算（2026/04）：**
- 舊邏輯（occ月）：138筆，已完成 86，未完成 52
- 新邏輯（完工月）：142筆，已完成 **107**，未完成 **35**，跨月21筆，灰色地帶17筆

**後端 `dazhi_repair_service.py`：**
- `is_completed_flag`：移到 `completed_at` 解析之後，改為 `(completed_at is not None) or is_completed(status)`
- `filter_cases`：新增 `_stat_year/_stat_month` helper，直接讀 `completed_at`，繞過 ORM 舊 year/month 欄位

**後端 `dazhi_repair.py` ORM：**
- `is_completed_flag` property：改為 `(completed_at is not None) or is_completed`
- `to_dict()` `pending_days` 條件：改為 `completed_at is None`

**前端 `DazhiRepair/index.tsx`：**
- `CaseListModal`：新增 `extraColumns` / `tableSummary` 兩個 optional props（與樂群對齊）
- KPI「本月報修件數」→「本月相關案件」，加副標「完工月＋未完成報修月」
- KPI「已完成件數」副標加「依完工時間」；「未完成件數」加「無完工時間的案件」
- KPI「本月工時統計」副標改為「{X.XX} 天（維修天數×24 ÷24）」
- 「已完成案件」彈窗：加說明 Tag ＋「完工時間」額外欄位
- 「未完成案件」彈窗：加說明「完工時間為空的案件」

## [1.35.12] - 2026-04-24

### Fixed
- **樂群 Dashboard 本月工時統計 — 計算邏輯統一為 Σ花費工時**
  - 移除 `_work_metric`（混合「結案天數(天)」和「花費工時(hr)」，單位不一致）
  - 新邏輯：`total_work_hours = Σ(c.work_hours for c in this_month_cases)`，單位純 hr
  - `花費工時 ≈ 工務處理天數 × 24`，÷24 即可換算天數
  - 2026/04 預期值：**10990.15 hr（= 457.92 天）**，含 47 筆（38完成 + 9未完成）
  - KPI 副標改為「{X.XX} 天（花費工時 ÷24）」
  - 工時明細彈窗小計改為純 hr ＋換算天數雙行顯示
  - 「工時指標」extra column 改為「結案天數」（供對照驗算）

## [1.35.11] - 2026-04-24

### Fixed
- **樂群 Dashboard 未完成件數仍顯示 17 的根本原因修正**
  - 問題：Dashboard 讀 SQLite ORM（`load_cases_from_db`），ORM 的 `is_completed`欄位在舊 sync 時存的是 `False`（灰色地帶8筆）
  - 修正 1 — `luqun_repair.py` ORM `is_completed_flag` property：
    改為 `(self.completed_at is not None) or self.is_completed`，不再依賴儲存的 bool 欄位
  - 修正 2 — `luqun_repair_service.py` `filter_cases`：
    新增 `_stat_year/_stat_month` helper，直接從 `completed_at` 計算統計月份，
    繞過 ORM 物件中因舊 sync 導致的 `year/month` 欄位錯誤（跨月灰色地帶案件）
  - 修正 3 — ORM `to_dict()` `pending_days` 條件：改用 `completed_at is None`
  - 效果：2026/04 已完成 20→**38**，未完成 17→**9**，無需重新 sync 即生效

## [1.35.10] - 2026-04-24

### Changed
- **樂群 Dashboard 前端標籤與彈窗說明更新（對應新完工邏輯）**
  - KPI 卡片：「本月報修件數」→「本月相關案件」，副標「完工月＋未完成報修月」
  - KPI 卡片：「未完成件數」加副標「無完工時間的案件」
  - KPI 卡片：「已完成件數」副標加「依完工時間」
  - KPI 卡片：「本月工時統計」副標改為「Σ結案天數＋花費工時（擇一）」
  - 彈窗「本月相關案件」加口徑說明 Tag
  - 彈窗「已完成案件」加說明 Tag + 新增「完工時間」欄位（方便看跨月案件）
  - 彈窗「未完成案件」加說明 Tag「完工時間為空的案件」
  - 彈窗「結案天數明細」加說明「完工時間 − 報修日期」

## [1.35.9] - 2026-04-24

### Fixed
- **樂群工務報修 — 完工判定邏輯修正（灰色地帶問題）**
  - 原邏輯：`is_completed_flag = is_completed(status)`，只看狀態字串，「處理中/待辦驗」即使有完工時間也算未完成
  - 新邏輯：`is_completed_flag = (completed_at is not None) or is_completed(status)`
    - 有「完工時間」→ 無論處理狀況，一律算已完工
    - 狀態為「已辦驗/結案…」但無完工時間 → 仍算已完工（備用）
  - 2026/04 驗算：已完成 20→**38** 筆（+18，含跨月及灰色地帶），未完成 17→**9** 筆
  - 影響：`stat_year/stat_month`、`close_days`、`pending_days`、`top_uncompleted` 全部連動正確

- **樂群工務報修 Dashboard — `this_month_cases` 口徑修正**
  - 改用 `filter_cases(year, month)`（stat 完工月口徑），取代舊的 `occ_year/occ_month`
  - 已完成案件依「完工月份」歸屬，跨月完工案件正確計入

## [1.35.8] - 2026-04-23

### Fixed
- **樂群工務報修 Dashboard — 本月工時統計計算邏輯修正**
  - 原邏輯：`Σ(c.work_hours)` 其中 `work_hours` 可能 = 工務處理天數 × 24（天變小時，導致數字膨脹）
  - 新邏輯：有結案天數（`close_days >= 0`）→ 直接用結案天數；否則用花費工時（`work_hours`）
  - 公式：`本月工時統計 = Σ(close_days if close_days≥0 else work_hours)`，避免 × 24 重複膨脹

### Added
- **樂群工務報修 Dashboard — 工時明細彈窗新增欄位與小計**
  - 新增「花費工時(hr)」欄：顯示 Ragic「花費工時」欄位原始值
  - 新增「工時指標」欄：🔵 顯示結案天數（用於計算）／🟢 顯示花費工時（結案天數為空時）
  - 每頁底部自動顯示「本頁小計」
  - 最後一頁同時顯示「總計」（與 KPI 卡片數字一致可對帳）

## [1.35.7] - 2026-04-23

### Added
- **統一 Ragic 資料存取層 `ragic_data_service.py`**
  - `get_merged_records()`: 主表 + detail merge，採 stale-while-revalidate 快取策略
  - 主表快取 TTL 30s，完整合併快取 TTL 120s
  - `asyncio.Semaphore(10)` 限制並發；背景 `asyncio.create_task` 更新 detail
  - `parse_images()`: 解析 Ragic 附件欄位（HTML img/a tag / list / URL）
  - `safe_work_days_to_hours()`: 工作天數轉小時，上限 365 天防誤植
- **圖片欄位整合（Ragic → Portal）**
  - 大直/樂群 RepairCase 新增 `images` 欄位（`[{url, filename}]`）
  - Drawer 詳情頁：有圖片時顯示「📷 查看圖片」連結，點擊開新分頁
  - 無圖片時不顯示，不影響版型

### Fixed
- **花費工時異常（48624 hr）根本修正**
  - 原因：Ragic「工務處理天數」欄位回傳年份 2026 → 2026 × 24 = 48624 hr
  - 修正：`safe_work_days_to_hours()` 加上限 365 天，超過視為無效，改讀「花費工時」
- **luqun/dazhi `fetch_all_cases()` 改用 merged records**
  - 新增 `invalidate_cache()` 讓 sync 後可清快取

## [1.35.6] - 2026-04-23

### Fixed
- **大直工務部 — `completed_at` 欄位優先順序修正**
  - `RK_COMPLETED_AT` alias 鏈開頭加入 `"完工時間"`：`["完工時間", "維修日期", "結案時間", "完成時間"]`
  - 原來讀「維修日期」，現在優先讀 Ragic「完工時間」欄，找不到才回落「維修日期」
  - 影響模組：`/dazhi-repair/dashboard`、`/work-category-analysis`

- **樂群工務報修 — `occurred_at` 欄位優先順序修正**
  - `RK_OCCURRED_AT` alias 鏈開頭加入 `"報修日期"`：`["報修日期", "發生時間", "實際報修時間", ...]`
  - 原來讀「發生時間」，現在優先讀 Ragic「報修日期」欄，找不到才回落「發生時間」
  - 影響模組：`/luqun-repair/dashboard`、`/work-category-analysis`

- `/exec-dashboard` 不使用樂群/大直報修資料，不受影響

## [1.35.5] - 2026-04-23

### Fixed
- **大直/樂群工務報修 Dashboard — 未完成案件 Top 10 篩選邏輯修正**
  - 原邏輯：`not is_completed_flag`（狀態判斷），可能把有 `completed_at` 但狀態非結案的案件列入
  - 修正：改為 `completed_at is None`（只要有完工日期就排除），符合實際完工事實
  - `pending_days`（已等天數）同步修正：條件改為 `completed_at is None`，有完工時間的案件不再計算等待天數
  - 兩系統後端各 2 處（篩選 + pending_days），共 4 處最小修改

## [1.35.4] - 2026-04-23

### Fixed
- **樂群工務報修 Dashboard — 當月金額卡片數字與「金額統計」Tab 不一致**
  - 根本原因：`compute_dashboard` 的月份費用用 `occ_year/occ_month`（報修日期），但金額統計 Tab 用 `filter_cases(year, month)`（結案案件以結案月份為準），口徑不同
  - 修正：`month_outsource_fee` 等 5 個欄位改用 `filter_cases(all_cases, year, month)` 計算，與金額統計 Tab 完全一致
  - 大直工務部無此問題（`this_month_cases` 原本已用 `filter_cases`，不需修改）

## [1.35.3] - 2026-04-23

### Added
- **大直/樂群工務報修 Dashboard — 新增「當月金額」欄**
  - 保留原有年度費用卡片（大直 2 欄、樂群 3 欄）不變
  - 新增第 4 欄「當月金額」：在同一卡片內緊湊顯示 4 行（委外+維修 / 扣款費用 / 扣款專櫃 / 當月小計）
  - 依 Dashboard 查詢條件（年+月）即時篩選；無資料顯示 `-`
  - 數字來源與「金額統計」Tab 一致（`month_*` 欄位由後端 `compute_dashboard` 提供）
- **後端：`dazhi_repair_service` / `luqun_repair_service`**
  - `compute_dashboard` 新增 5 個當月費用欄位：`month_outsource_fee`、`month_maintenance_fee`、`month_deduction_fee`、`month_deduction_counter`、`month_total_fee`
- **前端型別：`DashboardKpi` 新增 5 個 `month_*` 欄位（兩個系統）**

## [1.35.2] - 2026-04-22

### Fixed
- **大直/樂群工務報修 — 所有彈跳視窗寬度調整，消除橫向捲動**
  - 委外+維修費用明細（全年）：760 → 900px，移除 `scroll={{ x: 600 }}`
  - 扣款費用明細（全年）：700 → 760px，移除 `scroll={{ x: 560 }}`
  - 扣款專櫃明細（全年，樂群）：移除 `scroll={{ x: 560 }}`（700px 本身已足）
  - 金額統計月份明細：720 → 800px，移除 `scroll={{ x: 560 }}`
  - 同步修復兩個檔案尾端殘留 null bytes（`TS1127` Invalid character 錯誤）

## [1.35.1] - 2026-04-22

### Fixed
- **大直工務部 Dashboard — TypeScript 編譯錯誤修復**
  - `types/dazhiRepair.ts`：檔案截斷修復，補全 `DetailQueryParams` / `DetailResult` / `FilterOptions` / `FeeKey` / `FeeMonthRow` / `FeeTotals` / `FeeStatsData` 型別匯出
  - `DazhiRepair/index.tsx`：`FeeStatsTab` 內 `FeeMonthRow` / `FeeTotals` 轉型由 `as Record<string, number>` 改為 `as unknown as Record<string, number>`（解決 TS2352 overlap 錯誤）
  - `npx tsc --noEmit` 確認零錯誤

## [1.35.0] - 2026-04-22

### Fixed
- **大直/樂群工務報修 — 「取消」案件污染統計數字根本修復**
  - 根本原因：「取消」放在 `COMPLETED_STATUSES`，導致 3 月開單 4 月取消的案件，在 3 月的 ⑤ 完成數被多計，且 4 月的 ① 上月未完成少算
  - 新增 `EXCLUDED_STATUSES = {"取消"}` 與 `is_excluded()` 函式，分離「中止」與「完成」語意
  - 從大直 `COMPLETED_STATUSES` 移除 `"取消"`
  - `RepairCase` 新增 `is_excluded_flag` 屬性，加入 `to_dict()` 供前端判斷
  - 所有統計 compute 函式（Dashboard / 4.1 / 4.2 / 4.3 / 4.4 / 金額統計）最前端加一行過濾：`all_cases = [c for c in all_cases if not c.is_excluded_flag]`
  - `query_detail` 明細總表不過濾，保留完整記錄（取消案件仍可查閱）
  - 大直、樂群兩個系統同步更新

## [1.34.9] - 2026-04-22

### Added
- **大直工務部 — 新增「金額統計」Tab（與樂群工務報修介面一致）**
  - 後端 `dazhi_repair_service.py`：新增 `compute_fee_stats()` 函式（委外費用/維修費用/扣款費用 × 12 個月交叉表 + 明細清單）
  - 後端 `dazhi_repair.py`：新增 `GET /stats/fee` 端點
  - 前端 `types/dazhiRepair.ts`：新增 `FeeStatsData` / `FeeMonthRow` / `FeeTotals` / `FeeKey` 型別
  - 前端 `api/dazhiRepair.ts`：新增 `fetchFeeStats()` 函式
  - 前端 `DazhiRepair/index.tsx`：新增 `FeeStatsTab` 元件（點擊格子展開月份明細 Modal）；Tab 由 6 個增為 7 個
  - 說明：大直工務部 Ragic Sheet 目前無費用欄位，金額均顯示為 0；待 Ragic 補上欄位後將自動顯示數據

## [1.34.8] - 2026-04-22

### Added
- **大直/樂群工務報修 4.1 報修統計 — 新增 ⑥ 本月未完成數欄位**
  - 公式：④ 本月報修項目數 − ⑤ 本月報修項目完成數
  - 原 ⑥ 本月報修項目完成率（%）改為 ⑦
  - 後端兩個 service 的 `compute_repair_stats()` 均加入 `this_month_uncompleted`
  - 前端 `MonthRepairStat` TypeScript 介面同步新增欄位
  - 兩個系統（大直/樂群）同步更新

## [1.34.7] - 2026-04-22

### Fixed
- **樂群工務報修 Dashboard KPI 與 Tab 4.1 數字不一致（統計口徑不同）**
  - 根本原因：`compute_dashboard()` 用 `filter_cases()`（完成案件以「結案月份」分類），Tab 4.1 `compute_repair_stats()` 用 `occ_year/occ_month`（永遠以「報修月份」分類）
  - 修正：`compute_dashboard()` 及近 12 月趨勢圖改用 `occ_year/occ_month` 篩選，口徑與 Tab 4.1 一致（「本月報修件數」= 該月份報修的案件，無論結案月份）
  - 修正前：Dashboard 4 月顯示 36 筆（含 4 筆 3 月報修、4 月結案）；修正後：32 筆（=Tab 4.1 ④）
- **樂群工務報修 4.4 客房報修表 Drawer 欄位空白**
  - 同大直工務部 v1.34.3 修復：`compute_room_repair_table()` 矩陣格子改存 `case.to_dict()`，而非僅 `{ragic_id, title, status}` 3 欄

## [1.34.6] - 2026-04-22

### Fixed
- **客房保養明細 CORS + 404 根本修復（307 redirect 繞過 Vite proxy）**
  - `main.py`：`FastAPI()` 加入 `redirect_slashes=False`，防止 FastAPI 對無尾斜線路徑發出 307，讓瀏覽器直接打後端觸發 CORS 封鎖
  - `.env`：`CORS_ORIGINS` 加入 `http://127.0.0.1:5173` 與 `http://127.0.0.1:4173`，確保即使直連後端仍可通過 CORS
  - `room_maintenance_detail.py`：根路由改為同時註冊 `GET ""` 與 `GET "/"`，解決 `redirect_slashes=False` 後 404 問題

## [1.34.5] - 2026-04-22

### Fixed
- **SQLite + OneDrive 鎖定衝突修復（「載入明細資料失敗」根本原因）**
  - `database.py`：SQLite 連線加入 `timeout=30` 及 `pool_pre_ping=True`，DB 被 OneDrive 短暫鎖定時等待而非立即失敗
  - `main.py` lifespan：啟動時明確執行 `PRAGMA journal_mode=WAL; busy_timeout=30000; synchronous=NORMAL`，確保讀寫不互鎖
  - `vite.config.ts`：proxy target 從 `http://localhost:8000` 改為 `http://127.0.0.1:8000`，避免 Windows 11 將 `localhost` 解析成 IPv6 `::1`
- **前端 catch block 加入 `console.error` 輸出**（便於瀏覽器 DevTools 診斷）
- **新增「重新載入」按鈕**（讀取本地 DB，不觸發 Ragic 同步）

## [1.34.4] - 2026-04-22

### Fixed
- **1.1 客房保養明細 — 移除啟動時自動同步 Ragic（根本修復「載入明細資料失敗」）**
  - 原 `main.py` 在 `lifespan` 啟動時執行 `await _auto_sync()`，阻塞伺服器就緒前的請求，導致前端進入頁面時 API 呼叫失敗
  - 移除啟動時立即同步，伺服器啟動後直接從本地 SQLite DB 回傳資料
  - 保留排程同步（每 30 分鐘）與手動「同步資料」按鈕，行為符合規格：進入系統先讀本地 DB，只有手動或排程才同步 Ragic

## [1.34.3] - 2026-04-21

### Fixed
- **大直工務部 4.4 本月客房報修表 — Drawer 資料全空根本修復**
  - 後端 `compute_room_repair_table`：矩陣格子由儲存 `{ragic_id, title, status}` 3 欄改為儲存 `case.to_dict()` 完整欄位，Drawer 才能顯示報修人、樓層、時間等所有資訊
  - 前端：`RoomCategoryEntry` 型別改為 `RepairCase` 別名；移除 `as any` 強轉
  - 前端：多筆案件格子（原本僅顯示 badge 無法點擊）改為逐筆列出並各自可點開 Drawer

## [1.34.2] - 2026-04-21

### Fixed
- **大直工務部 — Ragic 來源 Sheet 路徑修正（根本原因）**
  - `.env` / `config.py` / service 說明：`lequn-public-works/4` → `lequn-public-works/8`（PAGEID=fV8 不變）
  - 原本 Sheet 4 的欄位比 Sheet 8 少，導致同步回來的資料幾乎全空（只有標題、處理狀況）
- **Vite Preview Proxy 修正**
  - `vite.config.ts` 新增 `preview.proxy`（與 `server.proxy` 相同）
  - 修正前：`vite preview`（port 4173）的 `/api` 請求打到靜態檔案伺服器而非後端（port 8000）→ API 全部 404
  - 修正後：preview build 的 API 呼叫正確轉發至 FastAPI 後端

## [1.34.1] - 2026-04-21

### Fixed
- **大直工務部 — 狀態映射修正**
  - 後端：`COMPLETED_STATUSES` 新增 `"已辦驗"`（500 筆，21.5%）與 `"取消"`；原本這些案件被誤算為「未完成」，導致 Dashboard KPI 及完成率統計偏低
  - 前端：`STATUS_COLOR` / `STATUS_TAG_COLOR` 補入 9 個實際出現的狀態（`已辦驗`/`待修中`/`待料中`/`取消`/`委外處理`/`待辦驗`/`辦驗未通過`/`進行中`/`待確認`），避免狀態 Tag 顯示無色

## [1.34.0] - 2026-04-20

### Added
- **Dashboard 主管視角優化（P1）**
  - **P1-E 預算管理摘要卡（首頁最上方）**：從 `getBudgetDashboard()` 讀取年度總預算/總實績/餘額/執行率/超支件數/即將超支件數/資料品質異常，以獨立摘要卡置於 Dashboard 頂端；含執行率進度條、警示 Tag（超支/即將超支/資料異常）、一句話結論、快速入口（預算 Dashboard / 預算比較報表 / 費用交易明細）
  - **P1-C 今日重點摘要區塊**：動態聚合全域待關注、最低完成率群組、工務最久未結案天數、預算超支風險等 3-5 條重點，不需新 API；含紅/黃/綠三色層級顯示
  - **P1-D 全域待關注加入工務+預算子項**：`totalAlerts` 計算新增 `repairPending`（樂群+大直未結案）與 `budgetAlert`（超支+即將超支）；「全域待關注」KPI 卡新增「工務 N」/ 「預算 N」Tag
  - **P1-B 各群組卡一句話結論**：飯店/商場/保全管理三張群組卡各依資料動態產生一句結論（完成率/逾期/異常判讀）；樂群/大直工務報修摘要卡亦補上一句結論
- **P1-A Login 頁正式感優化**：
  - 頁面背景改為品牌漸層色（`#f0f4f8` → `#dce6f0`）
  - 新增集團 Logo 圓角方塊（品牌漸層 `#1B3A5C` → `#4BA8E8`）
  - 加入副標「維春集團內部作業與管理平台」
  - DEV / UAT 環境標示（`import.meta.env.MODE` 判斷）
  - 登入按鈕加入 `loading` 狀態（防重複提交）
  - 錯誤訊息改為 `duration: 4` 不自動快消
  - 開發模式登入按鈕改為 `import.meta.env.DEV` 條件顯示，正式/UAT 環境完全不可見

## [1.33.7] - 2026-04-20

### Added
- **商場工務每日巡檢本地 DB 化**
  - 新增 `MallFIBatch` / `MallFIItem` ORM 模型（`mall_fi_inspection_batch` / `mall_fi_inspection_item` 資料表）；`sheet_key` 欄位區分 5 張樓層 Sheet
  - 新增 `services/mall_facility_inspection_sync.py`：動態欄位偵測 Pivot 同步，支援 5 張 Sheet（4F/3F/1F~3F/1F/B1F~B4F）
  - `routers/mall_facility_inspection.py` 新增端點：
    - `POST /{sheet_key}/sync` — 指定樓層背景同步
    - `POST /sync/all` — 全部 5 張背景同步
    - `GET /{sheet_key}/stats` — 樓層 Dashboard 統計（最新場次 KPI + 異常清單 + 7 日趨勢）
    - `GET /{sheet_key}/batches` — 月份篩選場次清單（含 KPI）
    - `GET /dashboard/summary` — 跨 Sheet 統計（index.tsx Dashboard 用）
  - `main.py` 新增 `mall_fi_inspection` 模型 import + `_auto_sync()` 加入「商場工務巡檢」排程
  - 前端新增 `api/mallFacilityInspection.ts` API 封裝（5 個函式）
  - `InspectionFloorPage.tsx` 替換 3 個 TODO stub：`loadDashboard` / `loadBatches` / `handleSync` 全部接上真實 API；KPI 卡、完成率進度條、異常/待處理清單均顯示真實資料
  - `index.tsx` Dashboard 替換 `loadSummary` / `handleSync` TODO stub；跨 Sheet 統計合併靜態清單呈現
  - `RagicAppDirectory.tsx` `LOCAL_TABLE_MAP` 新增 item 51~55 對應 `mall_fi_inspection_batch` / `mall_fi_inspection_item`

## [1.33.6] - 2026-04-20

### Added
- **Ragic 對應表（系統設定 → Ragic 對應表）**
  - 新增 `RagicAppPortalAnnotation` SQLAlchemy 模型（`ragic_app_portal_annotations` 表）：以 `item_no`（序號 1~219）為主鍵，存放 `portal_name` / `portal_url` 兩個可編輯欄位
  - 後端 `routers/ragic.py` 新增兩支 endpoint：
    - `GET /api/v1/ragic/app-directory/annotations` — 取得所有 Portal 標註（鍵值格式）
    - `PUT /api/v1/ragic/app-directory/annotations/{item_no}` — 新增或更新單筆 Portal 標註（限 system_admin）
  - 前端新增 `pages/Settings/RagicAppDirectory.tsx`：嵌入 219 筆靜態清單；前兩欄可編輯 Portal 標註；已標註列藍底高亮；支援搜尋/類型/模組篩選
  - `router/index.tsx` 新增路由 `/settings/ragic-app-directory`
  - `MainLayout.tsx` 側欄「系統設定」群組新增「Ragic 對應表」（角色管理下方）
  - `navLabels.ts` 新增 `ragicAppDirectory: 'Ragic 對應表'`

## [1.33.9] - 2026-04-20

### Fixed
- **台灣時區統一（系統全面修正）**
  - 新增 `app/core/time.py`：定義 `TW_TZ = timezone(timedelta(hours=8))` 與 `twnow()` helper，所有後端時間戳記統一由此產生
  - 全面替換 34 個檔案中的 `datetime.now(timezone.utc).replace(tzinfo=None)` 與 `datetime.utcnow` → `twnow()`，涵蓋所有 sync services、ORM model `default=` 欄位、routers 的 `generated_at` 等
  - `ragic.py` `GET /sync-logs/recent` 的 `since` 過濾條件改用 `twnow()`，確保 24 小時篩選基準正確
  - 例外：`app/core/security.py` 的 JWT exp 繼續使用 UTC（PyJWT 標準規範）
  - 前端 `RagicConnections.tsx` `fmtTime()` 改為直接 regex 解析 ISO 字串（`MM/DD HH:MM`），不透過 `new Date()` 以避免 browser 將無 tz suffix 的 ISO string 當 UTC 解讀
  - `TECH_SPEC.md` 新增「Taiwan Time Policy」時區政策規格章節，含後端/前端正確與錯誤範例

## [1.33.6] - 2026-04-19

### Fixed
- **同步排程對齊整點（CronTrigger）**
  - `scheduler.py` 新增 `make_cron_trigger(minutes)` helper：< 60 分鐘用 `CronTrigger(minute='0,30',...)`；≥ 60 分鐘用 `CronTrigger(hour='*/N', minute='0')`，確保觸發時刻對齊時鐘整點
  - `main.py` / `scheduler.py` 的 `module_auto_sync` 與 `register_connection_job` 均改用 `make_cron_trigger`，移除 `IntervalTrigger` 依賴
  - `RagicConnections.tsx` Alert 說明更新：顯示各間隔對應的整點時刻範例

### Added
- **同步紀錄頁新增「立即同步」按鈕**
  - 後端新增 `POST /api/v1/ragic/sync-logs/trigger`：背景觸發一次所有硬編碼模組的完整同步，並寫入 `module_sync_log` 紀錄
  - 前端 `api/ragic.ts` 新增 `triggerAllModulesSync()` 函式
  - `RagicConnections.tsx` 同步紀錄卡片右上角新增「立即同步」按鈕；載入失敗改為顯示 warning message 而非靜默失敗

## [1.33.5] - 2026-04-19

### Added
- **同步排程設定頁 — 24 小時同步紀錄**
  - 新增 `ModuleSyncLog` ORM 表（`module_sync_log`）：記錄每次排程/手動同步的模組名稱、狀態、fetched/upserted 筆數、耗時、錯誤訊息、觸發方式
  - `main.py` 加入 `_run_and_log()` helper：任何 sync coroutine 執行後自動寫入 `module_sync_log`
  - `_auto_sync()` 重構：12 個模組全部改用 `await _run_and_log(模組名, coro())`，消除重複的 try/except 樣板
  - 後端新增 `GET /api/v1/ragic/sync-logs/recent?hours=24`：返回最近 N 小時內所有模組同步紀錄，依時間降序
  - 前端 `api/ragic.ts` 新增 `ModuleSyncLogOut` 型別 + `getRecentSyncLogs()` 函式
  - `RagicConnections.tsx` 頁面最下方新增「24 小時同步紀錄」Table：依 started_at 降序排列；欄位含模組名稱、狀態 Tag/Badge、開始時間、耗時、撈取/寫入筆數、錯誤數（Tooltip 顯示訊息）、觸發方式；支援狀態篩選、「重新整理」按鈕

## [1.33.4] - 2026-04-19

### Added
- **預算管理模組 Phase 1 補強**
  - **主檔停用/啟用 UI**：部門 / 會計科目 / 預算項目三個主檔維護頁各新增「停用/啟用」Popconfirm 按鈕；呼叫現有 PUT endpoint 設 `is_active=0/1`；表格新增「狀態」欄顯示啟用/停用 Tag
    - `AccountCodeUpdate` / `BudgetItemUpdate` Pydantic schema 新增 `is_active` 選填欄位（若 DB 尚無欄位須執行 `ALTER TABLE ... ADD COLUMN is_active INTEGER DEFAULT 1`）
  - **交易明細 Excel 匯出**：後端新增 `GET /budget/transactions/export`（pandas + openpyxl，自動欄寬，帶入目前篩選條件）；前端「費用交易明細」頁右上角新增「匯出 Excel」按鈕（含 loading 狀態）
  - **預算主表作廢 / 刪除**：後端新增 `DELETE /budget/plans/{plan_id}`（draft → 硬刪除含所有明細；open/closed/imported → 軟刪除 status='void'）；前端操作欄新增「刪除/作廢」Popconfirm 按鈕（void 狀態行禁用編輯 / 明細 / 作廢按鈕）；篩選下拉補上「已作廢」選項；PUT 合法 status 集合補上 `void`

## [1.33.3] - 2026-04-19

### Added / Fixed
- **Phase 2：Scheduler 橋接 + RagicConnections UI**
  - **後端 bug fix**：`ragic_adapter.py` 新增 `compute_checksum()` 靜態方法（SHA-256）；`sync_service.py` 修正 `RagicAdapter` 建構參數（`server_url` / 解密 `api_key_enc`）、改為 `async def`、加入 `triggered_by` 參數
  - **新增 `app/core/scheduler.py`**：全域 `AsyncIOScheduler` 單例 + `register_connection_job` / `deregister_connection_job` / `list_connection_jobs` helpers
  - **`main.py`**：移除本地 `_scheduler = AsyncIOScheduler()` 改從 `core.scheduler` import；加入 `_init_ragic_connection_jobs()` 於 lifespan startup 掃描所有 active RagicConnection 並建立各自排程任務；硬編碼模組 job ID 由 `room_maintenance_sync` 改為 `module_auto_sync`
  - **`routers/ragic.py` 擴充**：新增 `DELETE /connections/{id}`（軟刪除）、`PATCH /connections/{id}/active`（啟停切換）、`GET /scheduler/status`（列出已排程 jobs）；CREATE / UPDATE / DELETE / TOGGLE 操作後自動呼叫 `register_connection_job` / `deregister_connection_job`
  - **`schemas/ragic.py`**：新增 `RagicConnectionUpdate`（api_key 選填）
  - **新增 `frontend/src/api/ragic.ts`**：封裝所有 9 個 Ragic API endpoints 的 TypeScript 客戶端函式
  - **完整實作 `RagicConnections.tsx`**：取代佔位頁面；連線列表 Table + 新增/編輯 Modal（含 API Key 加密 + 選填更新）+ 軟刪除確認 + 啟停 Switch + 手動同步按鈕 + 同步日誌 Drawer（Timeline 時間軸）

---

## [1.33.2] - 2026-04-19

### Added
- **Phase 3：大直/樂群工務報修建立本地 DB** — 落實開發規則「所有 Ragic 同步必須持久化到本地 SQLite」
  - 新增 ORM 模型：`app/models/dazhi_repair.py`（`DazhiRepairCase` 表）、`app/models/luqun_repair.py`（`LuqunRepairCase` 表，含 `deduction_counter`/`occ_year`/`occ_month` 樂群專用欄位）
  - 兩張表均在 `app/main.py` lifespan 中透過 `Base.metadata.create_all()` 自動建立
  - 新增同步服務：`app/services/dazhi_repair_sync.py`、`app/services/luqun_repair_sync.py`（Ragic → SQLite upsert）
  - **大直/樂群 router 所有資料端點改讀本地 DB**（`/years`、`/filter-options`、`/dashboard`、`/stats/*`、`/detail`、`/export`），從 `async def + await svc.fetch_all_cases()` 改為 `def + load_cases_from_db(db)`
  - 兩個 router 各新增 `POST /sync`（背景觸發 Ragic→DB 同步）；原 `GET /sync` 保留為 Ragic 直連診斷端點
  - `_auto_sync()` 排程加入大直/樂群報修同步（每 30 分鐘）
  - ORM 模型加入 `is_completed_flag` property，確保現有統計函式無需修改即可讀取

---

## [1.33.1] - 2026-04-19

### Changed
- **Phase 1：所有模組手動同步改為背景執行** — 10 個模組 router 的 `POST /sync` endpoint 全部從 `await sync_from_ragic()` 改為 `BackgroundTasks.add_task(sync_from_ragic)`，API 立即回傳 `{"success": true, "message": "同步已在背景啟動"}`，不再阻塞畫面
  - 異動檔案：`room_maintenance`、`inventory`、`periodic_maintenance`、`mall_periodic_maintenance`、`security_patrol`、`room_maintenance_detail`、`b1f/b2f/b4f/rf_inspection`（共 10 個 router）
  - `room_maintenance` 的 `create_record` / `update_record` 寫入 Ragic 後觸發的 sync 亦改為背景執行
  - 前端同步按鍵行為不變（點按 → loading → 收到 200 即解鎖）
  - `/api/v1/ragic/connections/{id}/sync` 原已正確使用 BackgroundTasks，不動

---

## [1.33.0] - 2026-04-19

### Added
- **預算管理模組（Phase 1）** — 完整掛入 Portal 左側 Menu（Dashboard 下方）
  - **後端**：獨立 SQLite 連線模組 `budget_database.py`；預算 router 含 24 個 API endpoints
    - `GET /budget/dashboard` — 年度 KPI：總預算 / 實績 / 餘額 / 執行率 / 超支清單 / 部門摘要
    - `GET/POST/PUT /budget/plans` — 預算主表 CRUD（含狀態管理 draft/open/closed）
    - `GET/POST/PUT/DELETE /budget/plans/{id}/details` — 預算明細編列（12 個月欄位）
    - `GET/PUT /budget/transactions` — 交易明細查詢與修正（579 筆既有資料）
    - `GET/POST/PUT /budget/masters/departments` — 部門主檔 CRUD
    - `GET/POST/PUT /budget/masters/account-codes` — 會計科目主檔 CRUD
    - `GET/POST/PUT /budget/masters/budget-items` — 預算項目主檔 CRUD
    - `GET/POST/PUT/DELETE /budget/mappings` — 對照規則維護 CRUD
    - `GET /budget/reports/budget-vs-actual` — 預算比較報表（讀取 view，年度 / 月別模式）
    - `GET /budget/reports/data-quality` — 資料品質問題清單（#REF! / 金額缺漏 / 未對應明細）
  - **前端**：10 個頁面（Dashboard / Plans / Plan Detail / Transactions / BudgetVsActual / Departments / AccountCodes / BudgetItems / Mappings）
  - **權限**：`budget_view`（查詢）/ `budget_manage`（維護）/ `budget_admin`（管理）架構已建立
  - **資料**：使用 `budget_system_v1.sqlite`（2026 年度 579 筆交易 + 預算明細 133 筆）

---

## [1.32.2] - 2026-04-17

### Added
- **首頁 Dashboard — 工務報修主管摘要區（樂群 + 大直）**
  - 新增 ROW 1.5，位於 KPI 總覽與群組摘要之間，兩欄並排
  - 每欄顯示本月 6 大 KPI：報修總數、已結案、未結案、結案率（含色碼進度條）、平均結案天數、工時
  - 最高報修類型 Tag（`↑ 類型 N 件`）
  - 逾期警示 Tag：最久未結案件天數（≥14 天紅、≥7 天橘）
  - 點擊右上角「查看詳情」可直接跳轉各模組
  - 沿用 `/luqun-repair/dashboard` 及 `/dazhi-repair/dashboard` API，year=本年 month=本月
  - 最小侵入修改：僅新增 state、API 呼叫、`RepairSummaryCard` 元件，不影響既有任何元件

---

## [1.32.1] - 2026-04-17

### Fixed
- **樂群工務報修 — 統計月份歸屬修正（結案月份制）**
  - 原邏輯：所有案件的 `year / month` 均來自 `occurred_at`（報修月份）
  - 新邏輯：`is_completed=true AND completed_at ≠ null` 的案件改以 `completed_at`（結案月份）為準；未結案仍沿用 `occurred_at`
  - 新增 `occ_year / occ_month` 欄位（永遠來自 `occurred_at`），供 4.1 報修統計的「本月報修項目數」專用，確保報修量統計不受此規則影響
  - `compute_repair_stats` 中 `cases_up_to_prev / cases_up_to_this / this_month_cases` 改用 `occ_year / occ_month` 過濾，保持 4.1 報修統計的正確性
  - 具體案例 202604-032：occurred_at=2026/01/18、completed_at=2026/04/10 → 統計月份由 1 月改為 4 月（close_days=82 天，total_fee=17,955）
- **規格書更新**：新增 §3.5「統計月份歸屬規則」及案例說明；已知問題表加入本次修正記錄

---

## [1.32.0] - 2026-04-17

### Fixed
- **樂群工務報修 — 4.2 結案時間 統計數依規格書重新驗證**
  - 確認 `completed_at` 瀑布優先順序（完工時間→結案時間→結案日期→驗收時間→前端驗收時間→驗收日期）
  - 確認 `close_days = (completed_at − occurred_at) ÷ 86400`，需 `is_completed=true AND` 兩端日期均有值
  - 4.2 分類標準更新為：小型=`total_fee=0`；中大型=`total_fee>10000`（`is_large_repair()` 函式）

### Added
- **樂群工務報修 — 全模組統計數字可點擊查看明細**
  - Dashboard KPI 卡片（本月報修件數/已完成/未完成/平均結案天數/工時/客房）全部可點擊展開 `CaseListModal`
  - 4.1 報修統計表：①②④⑤ 格子均可點擊，展開對應案件清單
  - 4.2 結案時間：摘要卡三個指標（件數/天數/平均）可點擊；月份表所有非零格子可點擊
  - 4.3 報修類型：各月份格子、合計欄、月份合計列均可點擊
  - 新增 `CaseListModal` 共用元件（支援分頁、點選個別案件開啟詳情 Drawer）
- **Backend 各 compute 函式加入 cases 明細**
  - `compute_closing_time` — `stats_block` 加入 `cases` 欄位
  - `compute_repair_stats` — 各月加入 4 個 `*_detail` 欄位
  - `compute_type_stats` — 各類型加入 `monthly_detail` 欄位
  - `compute_dashboard` — 加入 6 個 `kpi_*_detail` 欄位

---

## [1.31.9] - 2026-04-17

### Fixed
- **樂群工務報修 — 結案判斷 Bug 修正**
  - 將 `已辦驗` 加入 `COMPLETED_STATUSES`，修正實際已結案案件被判定為未完成的問題
  - 根因：Ragic 資料中「處理狀況=已辦驗 + 驗收=結案」為完成狀態，但原集合缺少「已辦驗」，導致 `close_days` 全部回傳 null
  - 以 4 月 Excel 匯出資料驗證：修正後 6 筆結案案件平均結案天數 24.04 天（最短 2.98 天，最長 81.95 天）

### Added
- **樂群工務報修 — 功能規格書**（`樂群工務報修_功能規格書.docx`）
  - 涵蓋：Ragic 欄位映射、時間欄位計算規格（occurred_at / completed_at / is_completed / close_days）、金額計算規格（_float() / total_fee 公式）、API 端點清單、前端頁面規格、已知問題修正紀錄

---

## [1.31.8] - 2026-04-16

### Added
- **樂群工務報修 — 新增「金額統計」Tab**
  - 以交叉表格呈現 4 項費用（委外費用 / 維修費用 / 扣款費用 / 扣款專櫃）× 12 個月，以及項目全年小計、月份橫向小計、全年總計
  - 有金額的格子可點擊，彈出明細 Modal 顯示該費用類型在該月的所有案件（案號、標題、樓層、日期、狀態、費用金額）
  - 後端新增 `compute_fee_stats()` service 函數與 `GET /api/v1/luqun-repair/stats/fee` 端點，回傳 monthly_totals / fee_totals / month_totals / grand_total / monthly_detail
  - 前端新增 `FeeStatsData` TypeScript 型別、`fetchFeeStats()` API 函數、`FeeStatsTab` 元件

---

## [1.31.7] - 2026-04-16

### Fixed / Improved
- **樂群工務報修 Dashboard — 費用 KPI 改為全年累計**
  - 原本費用卡片使用「當月」資料，導致只有當月有費用的案件才計入（例如 4 月扣款費用 $0，但全年實際有 $17,955）
  - 改為使用**選定年度的全年合計**（不受月份篩選影響），與 Ragic 同步摘要的數字一致
  - 委外+維修費用卡片同時顯示委外費用與維修費用各自小計
  - 後端新增 `annual_fee`、`annual_outsource_fee`、`annual_maintenance_fee`、`annual_deduction_fee`、`annual_deduction_counter` 至 KPI 回應
- **樂群工務報修 Dashboard — 費用卡片點擊查看明細**
  - 三張費用卡片均可點擊，彈出 Ant Design Table Modal 顯示對應明細
  - 委外+維修費用明細：案件列表 + 委外費用、維修費用、總計三欄
  - 扣款費用明細：案件列表 + 扣款事項、扣款費用
  - 扣款專櫃明細：案件列表 + 扣款專櫃金額
  - 後端各類明細最多回傳 Top 20 筆

---

## [1.31.6] - 2026-04-16

### Fixed
- **樂群工務報修 — `_float()` 貨幣解析強化**：舊版只剝除 `$`/`,`/空白，遇到 `NT$440,509`、`TWD 440,509`、`440,509元` 等含非數字前後綴的值一律回傳 0，導致委外費用/維修費用/扣款費用等欄位全部計算為 $0
  - 改用 regex 萃取第一段合法數字（支援負號、千分位、小數點），完全忽略貨幣代碼前綴與單位後綴
  - 修正 `"扣款專櫃": []`（空陣列）不再拋出錯誤，正確回傳 0.0
  - 13 個單元測試全數通過（包含 NT$、TWD、元後綴、空 list/dict、負數、小數）
- **樂群工務報修 — Ragic 欄位別名更新**（依 record #533 實測值校正）
  - `RK_REPORTER` 首位別名改為 `報修同仁`（舊：報修人姓名）
  - `RK_OCCURRED_AT` 補充 `實際報修時間`
  - `RK_RESPONSIBLE` 補充 `處理工務`、`交辦主管`
  - `RK_STATUS` 補充 `問題狀態`（實測欄位名稱）
  - `RK_ACCEPT_STATUS` 首位別名改為 `驗收回應`
  - `RK_COMPLETED_AT` 首位別名改為 `完工時間`（實測欄位名稱）
  - `RK_ACCEPT_DATE` 首位別名改為 `驗收時間`、補充 `前端驗收時間`

---

## [1.31.5] - 2026-04-16

### Added
- **樂群工務報修 Dashboard — 費用明細 KPI 列**
  - Dashboard 新增第二 KPI 行（3 欄一排）：委外+維修費用 / 扣款費用 / 扣款專櫃
  - 後端 `compute_dashboard` 新增 `total_deduction_fee`、`total_deduction_counter` 欄位
  - 後端 `RepairCase` 新增 `deduction_counter`（扣款專櫃）欄位，對應 Ragic 欄位 `"扣款專櫃"`
  - TypeScript `DashboardKpi` 與 `RepairCase` 介面同步新增對應欄位
  - 原第一 KPI 行移除「費用總額」卡（已由第二行費用明細列取代，版面更清晰）

---

## [1.31.4] - 2026-04-16

### Added
- **樂群工務報修 — 功能與大直工務部對齊**
  - 頁面右上角新增「連線測試」（藍色）與「同步 Ragic」（紫色漸層）按鈕
  - 「連線測試」彈出 Ping Modal：顯示 Ragic URL、API Key 前綴、HTTP 狀態/耗時/記錄數，並以完整欄位表格呈現第一筆原始 JSON，方便比對欄位名稱
  - 「同步 Ragic」彈出 Sync Modal：顯示總筆數、無日期數、年份分布 Tags、最近 3 筆案件表、Ragic 欄位名稱 Tag 雲
  - 後端 `luqun_repair.py` 的 `/ping` 與 `/sync` 端點在前一版本已新增，本版將前端整合完成
- **樂群工務報修 4.4 本月客房報修表**
  - 樓層篩選改為 Button Pills（點選切換 primary/default，視覺更直覺）
  - 新增統計列：總報修數 / 涉及房間數 / 涉及樓層數
  - 表格 cell 可點擊，彈出 CaseDetailDrawer 檢視案件詳情

---

## [1.31.3] - 2026-04-16

### Fixed
- **大直工務部 — 全面修正 Ragic 欄位對應**（依 /ping 端點實測 record #2315 校正）
  - `報修單編號`（舊：報修編號）、`(備註/詳細說明)`（舊：標題）、`報修人`（舊：報修人姓名）
  - `維修地點`（舊：發生樓層）、`報修日期`（舊：發生時間）、`反應單位`（舊：負責單位）
  - `類型`（舊：報修類型，值為 JSON array）、`處理狀態`（舊：處理狀況）
  - `維修天數`（舊：花費工時，×24 轉為小時）、`維修日期`（舊：結案時間）
  - `維修人員`（舊：結案人）、`驗收人員`（舊：驗收者）、`處理說明`（舊：財務備註）
- 新增 `RK_ALIASES` 首位 alias = 實際欄位名，確保優先命中
- `COMPLETED_STATUSES` 補充「結案」為已確認的大直工務部完成狀態
- `REPAIR_TYPE_MAPPING` 補充蓮蓬頭、浴缸、花灑、水龍頭、面盆等衛廁類型

---

## [1.31.2] - 2026-04-16

### Added
- **大直工務部 — 同步 Ragic 按鈕**：頁面右上角新增「同步 Ragic」按鈕，點擊後即時從 Ragic 抓取全部資料並彈出診斷 Modal，顯示：抓取筆數、日期解析失敗數、年份分布、最近 3 筆案件、Ragic 實際欄位名稱清單，便於診斷欄位對應問題
- **後端** `dazhi_repair.py`：新增 `GET /api/v1/dazhi-repair/sync` 診斷端點

### Fixed
- **樂群工務報修 Dashboard**：KPI 7 張卡片同樣改用 flex 布局，修正 `md={24/7}` 非整數導致第 7 張換行的問題

---

## [1.31.1] - 2026-04-16

### Fixed
- **大直工務部** — Ragic 資料來源 PAGEID 修正：`uIw` → `fV8`（更新 `.env`、`config.py`、`dazhi_repair_service.py`，`fetch_all_cases` 和 `fetch_raw_fields` 均已傳遞 `PAGEID=fV8`）
- **大直工務部 Dashboard** — KPI 卡片 7 張改用 flex 布局（原 `Col md={24/7}` 為非整數導致第 7 張換行），現在確保所有統計卡片排在同一列

---

## [1.31.0] - 2026-04-15

### Added
- **大直工務部模組** — 完整新模組正式納入 Portal，左側 Menu 新增於「樂群工務報修」之後
  - 後端新增 `app/services/dazhi_repair_service.py`（Ragic 資料抓取、欄位清洗、狀態標準化、類型 mapping、房號解析、4.1~4.4 統計公式、Dashboard 統計）
  - 後端新增 `app/routers/dazhi_repair.py`（10 支 API：`/raw-fields`、`/years`、`/filter-options`、`/dashboard`、`/stats/repair`、`/stats/closing`、`/stats/type`、`/stats/room`、`/detail`、`/export`）
  - 後端更新 `app/main.py`：掛載 `dazhi_repair` router（prefix `/api/v1/dazhi-repair`）
  - 後端更新 `app/core/config.py`：新增 `RAGIC_DAZHI_REPAIR_*` 三個設定項
  - 後端更新 `.env`：新增 Ragic 大直工務部連線設定（ap12.ragic.com / soutlet001 / lequn-public-works/4）
  - 前端新增 `types/dazhiRepair.ts`（完整 TypeScript 型別定義）
  - 前端新增 `api/dazhiRepair.ts`（全部 API 封裝，含匯出 Excel URL 建構）
  - 前端新增 `pages/DazhiRepair/index.tsx`（主頁面，含 6 個 Tab：Dashboard / 4.1 / 4.2 / 4.3 / 4.4 / 大直工務部明細）
  - 前端更新 `constants/navLabels.ts`：新增 `dazhi_repair` 群組 + `dazhiRepairDashboard` 頁面標籤
  - 前端更新 `components/Layout/MainLayout.tsx`：左側 Menu 新增「大直工務部」群組
  - 前端更新 `router/index.tsx`：新增 `/dazhi-repair/dashboard` 路由
  - 資料來源：`https://ap12.ragic.com/soutlet001/lequn-public-works/4`

---

## [1.30.0] - 2026-04-15

### Added
- **樂群工務報修模組** — 完整新模組正式納入 Portal，左側 Menu 新增於「商場管理」之後
  - 後端新增 `app/services/luqun_repair_service.py`（Ragic 資料抓取、欄位清洗、狀態標準化、類型 mapping、房號解析、4.1~4.4 統計公式、Dashboard 統計）
  - 後端新增 `app/routers/luqun_repair.py`（8 支 API：`/years`、`/filter-options`、`/dashboard`、`/stats/repair`、`/stats/closing`、`/stats/type`、`/stats/room`、`/detail`、`/export`）
  - 後端更新 `app/main.py`：掛載 `luqun_repair` router（prefix `/api/v1/luqun-repair`）
  - 後端更新 `app/core/config.py`：新增 `RAGIC_LUQUN_REPAIR_*` 三個設定項
  - 後端更新 `.env`：新增 Ragic 樂群工務報修連線設定（ap12.ragic.com / soutlet001 / luqun-public-works-repair-reporting-system/6）
  - 前端新增 `types/luqunRepair.ts`（完整 TypeScript 型別定義）
  - 前端新增 `api/luqunRepair.ts`（全部 API 封裝，含匯出 Excel URL 建構）
  - 前端新增 `pages/LuqunRepair/index.tsx`（主頁面，含 6 個 Tab：Dashboard / 4.1 / 4.2 / 4.3 / 4.4 / 明細總表）
  - 前端更新 `constants/navLabels.ts`：新增 `luqun_repair` 群組 + `luqunRepairDashboard` 頁面標籤
  - 前端更新 `components/Layout/MainLayout.tsx`：左側 Menu 新增「樂群工務報修」群組
  - 前端更新 `router/index.tsx`：新增 `/luqun-repair/dashboard` 路由

---

## [1.29.0] - 2026-04-15

### Added
- **Dashboard 趨勢折線圖** — 後端新增 `GET /api/v1/dashboard/trend`（近 3~30 日，回傳商場巡檢/保全巡檢/客房保養三條完成率折線資料）；前端使用 recharts `LineChart` 呈現，支援 7 日 / 30 日切換（ROW 4）；無資料的日期點自動 null 斷線，不影響其他日期的連線
- **Dashboard 結案率追蹤** — 後端新增 `GET /api/v1/dashboard/closure-stats`（客房保養結案漏斗 + 商場/保全近 30 日異常數 + 簽核流程結案率）；前端新增 ROW 5，四欄卡片顯示「異常 → 已處理 → 已結案」進度與百分比
- `dashboard.ts` 新增 `TrendPoint`, `DashboardTrend`, `ClosureStats` 等型別與 `dashboardApi.trend()`, `dashboardApi.closureStats()` API 函數

---

## [1.28.1] - 2026-04-15

### Fixed
- **GraphView 新增春大直商場工務巡檢、整棟巡檢節點** — 後端 `/graph` 新增 `mall_facility`、`full_building` 2 個巡檢節點（Ragic 直連作業，alert=0）；新增 2 條 anomaly 邊連至對應保養節點；前端 `NODE_POSITIONS` 補上兩節點座標（y=515/615），GraphView 容器高度由 540px 升為 720px；節點總數 11→13、邊總數 8→10

---

## [1.28.0] - 2026-04-15

### Added
- **整棟巡檢** — 新增完整功能模組，整合 4 個樓層巡檢 Ragic 表單（RF / B4F / B2F / B1F）
  - 前端新增 `constants/fullBuildingInspection.ts`（4 個 Sheet 設定常數 + Ragic URL）
  - 前端新增 `pages/FullBuildingInspection/index.tsx`（模組 Dashboard：4 KPI 卡 + 樓層統計表 + Tabs）
  - 前端新增 `pages/FullBuildingInspection/InspectionFloorPage.tsx`（共用樓層元件：主管儀表板 + 巡檢紀錄 Tabs）
  - 前端新增 4 個樓層頁面：`RF.tsx` / `B4F.tsx` / `B2F.tsx` / `B1F.tsx`
  - 前端更新 `constants/navLabels.ts`：新增 `full_building_inspection` 群組 + 5 個頁面標籤
  - 前端更新 `MainLayout.tsx`：左側 Menu 新增群組（春大直商場工務巡檢之後、保全管理之前）
  - 前端更新 `router/index.tsx`：新增 `/full-building-inspection/*` 5 條路由
  - 前端更新 `pages/Dashboard/index.tsx`：ROW 2 新增整棟巡檢快速入口群組卡片
  - 後端新增 `routers/full_building_inspection.py`（`GET /sheets`，回傳 4 個 Sheet 設定）
  - 後端更新 `main.py`：掛載新 router

---

## [1.27.0] - 2026-04-15

### Added
- **春大直商場工務巡檢** — 新增完整功能模組，整合 5 個樓層巡檢 Ragic 表單
  - 前端新增 `constants/mallFacilityInspection.ts`（5 個 Sheet 設定常數 + Ragic URL）
  - 前端新增 `pages/MallFacilityInspection/index.tsx`（模組 Dashboard：樓層快速入口 + 摘要預留區）
  - 前端新增 `pages/MallFacilityInspection/InspectionFloorPage.tsx`（共用樓層巡檢頁元件，支援 iframe 內嵌 Ragic + 展開收合）
  - 前端新增 5 個樓層頁面：`4F.tsx` / `3F.tsx` / `1F3F.tsx` / `1F.tsx` / `B1FB4F.tsx`
  - 前端更新 `constants/navLabels.ts`：新增 `mall_facility_inspection` 群組 + 6 個頁面標籤
  - 前端更新 `MainLayout.tsx`：左側 Menu 新增群組（商場管理之後、保全管理之前）
  - 前端更新 `router/index.tsx`：新增 `/mall-facility-inspection/*` 6 條路由
  - 前端更新 `pages/Dashboard/index.tsx`：ROW 2.5 新增工務巡檢模組入口卡片
  - 後端新增 `routers/mall_facility_inspection.py`（`GET /sheets`，回傳 5 個 Sheet 設定）
  - 後端更新 `main.py`：掛載新 router

---

## [1.26.0] - 2026-04-15

### Changed
- **GraphView 全面升級為操作流程圖（Flow Diagram）**：從 Hub-Spoke 改為「巡檢→保養→簽核→公告」流程鏈
  - 改用 `@xyflow/react` v12（react-flow）套件，取代純 SVG 實作
  - 節點從 6 個擴展為 11 個（B1F/B2F/RF/B4F/保全/客房保養/飯店PM/商場PM/簽核/公告）
  - 邊從 hub-spoke 改為 8 條語意化關係邊，含 DB 直接關聯（Approval→Memo）與業務邏輯邊
  - 邊類型三種：`anomaly`（紅色虛線）、`escalation`（橙色虛線）、`workflow`（紫色實線+動畫）
  - 後端 `/graph` 端點完整重設計：個別計算各巡檢模組異常數、保養逾期/異常數、公告來源數
  - 新增 `MallPeriodicMaintenanceItem`、`SecurityPatrolItem` 到 dashboard.py 聚合查詢
  - 前端節點支援 hover 放大、alert badge、副標籤（逾期/異常分項）、點擊跳轉
  - 右下 MiniMap、左下縮放控制、左上圖例 Panel

---

## [1.25.0] - 2026-04-15

### Added
- **Dashboard 關聯圖譜（GraphView）**：Hub-Spoke SVG 視覺化，呈現各模組異常 / 待辦連結狀態
  - 後端新增 `GET /api/v1/dashboard/graph`（聚合 6 大模組待辦 / 異常計數，無新資料表）
  - 前端新增 `frontend/src/api/dashboardGraph.ts`（API 型別封裝）
  - 前端新增 `frontend/src/components/GraphView/index.tsx`（純 SVG Hub-Spoke，無外部套件）
  - `frontend/src/pages/Dashboard/index.tsx` 新增 ROW 4「模組關聯圖譜」區塊
  - 節點：客房保養、週期保養、商場巡檢、工務巡檢、簽核待辦、近期公告
  - 連線粗細 = alert 數量；節點色 = 狀態（normal/warning/danger）
  - 點擊節點可直接跳轉對應模組；每 60 秒自動刷新

---

## [1.24.0] - 2026-04-15

### Added
- **行事曆（Command Calendar）超級行事曆模組**：Portal 跨模組事件總覽中心，放置於左側 Menu `Dashboard` 之後
  - 後端新增 `backend/app/models/calendar_event.py`（自訂事件資料表 `calendar_custom_events`）
  - 後端新增 `backend/app/schemas/calendar.py`（Pydantic 型別定義）
  - 後端新增 `backend/app/routers/calendar.py`（聚合 API：`/api/v1/calendar/events`、`/today`、`/custom` CRUD）
  - 前端安裝 `@fullcalendar/react` v6.1.20（月/週/日/清單四種視圖）
  - 前端新增 `frontend/src/types/calendar.ts`、`frontend/src/api/calendar.ts`
  - 前端新增 `frontend/src/pages/Calendar/index.tsx`（主頁面：KPI 摘要列、篩選器、FullCalendar 視圖）
  - 前端新增 `frontend/src/pages/Calendar/components/TodayPanel.tsx`（今日重點側邊面板）
  - 前端新增 `frontend/src/pages/Calendar/components/EventDrawer.tsx`（事件詳情抽屜 + 深連結）
  - 整合六大事件來源：飯店週期保養、商場週期保養、保全巡檢、工務巡檢、簽核管理、公告牆
  - 支援自訂事件新增 / 編輯 / 刪除（`calendar_custom_events` 表）
  - `navLabels.ts` 新增 `calendar` 群組與 `calendarMain` 頁面常數
  - `MainLayout.tsx` 新增行事曆 Menu 項目（`CalendarOutlined` 圖示）
  - `router/index.tsx` 新增 `/calendar` 路由
  - `main.py` 新增 `calendar` router 註冊 + `calendar_event` model import

---

## [1.23.0] - 2026-04-14

### Changed
- **Portal 首頁 Dashboard 全面重組**：將 `/dashboard` 從「飯店 + 庫存」單一視角，升級為集團三群組（飯店 / 商場 / 保全）管理總覽首頁
  - `pages/Dashboard/index.tsx`：全新版面，零後端改動
    - **ROW 1 KPI 卡**：新增「商場巡檢完成率」、「保全巡檢完成率」KPI 卡，保留「客房保養完成率」；新增「全域待關注」彙總 Card（商場異常 + PM 逾期 + 保全異常 + 客房未完成合計）
    - **ROW 2 群組摘要卡**：飯店 / 商場 / 保全各一卡；商場卡含 B1F / B2F / RF 各樓層今日完成率 + 本月 PM 完成/逾期；保全卡含今日完成率 + 場次/異常件數 + 有問題 Sheet 列表（最多 3 筆）
    - **ROW 3 系統資訊**：近期同步紀錄（保留原有）+ 倉庫庫存概況（從 Bar Chart 縮為 Statistic + 前 4 類別列表）
    - 每個群組卡均附快速入口 QuickLink，直達各子模組
    - 3 支 API 以 `Promise.allSettled` 平行呼叫（`/dashboard/kpi`、`/mall/dashboard/summary`、`/security/dashboard/summary`），任一失敗不影響其他群組顯示
    - 完整遵守 PROTECTED.md：4 欄 KPI Row、`size="small"`、Breadcrumb 保留、品牌色 #1B3A5C / #4BA8E8、狀態色映射不變

---

## [1.22.2] - 2026-04-14

### Fixed
- **保全巡檢「異常說明%」欄位處理**：Ragic 的「異常說明」、「異常說明2」等欄位為文字備註，應顯示但不計入巡檢評分統計
  - `models/security_patrol.py`：`SecurityPatrolItem` 新增 `is_note BOOLEAN DEFAULT 0`
  - `services/security_patrol_sync.py`：`sync_sheet` 偵測 `item_name` 含「異常說明」→ `is_note=True`、`result_status='note'`、`abnormal_flag=False`，儲存原始文字
  - `routers/security_patrol.py`：`_calc_kpi` 改為僅計算 `is_note=False` 的評分項目；`get_stats` 中 `status_dist`、`recent_abnormal`、`recent_pending`、`abnormal_trend` 均加入 `is_note=False` 過濾
  - `routers/security_dashboard.py`：`_sheet_stats`、`get_issues`、`get_trend` 三處查詢全部加入 `is_note=False` 過濾
  - `schemas/security_patrol.py`：`PatrolItemOut` 新增 `is_note: bool = False`
  - `main.py`：新增 `_migrate_security_patrol_is_note()` 啟動遷移，自動新增欄位並回填現有異常說明記錄，無需重新同步
  - `types/securityPatrol.ts`：`PatrolItem` 新增 `is_note?: boolean`，`result_status` 聯集加入 `'note'`
  - `pages/SecurityPatrol/Detail.tsx`：備註項目以藍色文字 + 備註 Tag 顯示；新增篩選選項「備註說明」；頁腳顯示評分項與備註項分計數

---

## [1.22.1] - 2026-04-14

### Fixed
- **保全巡檢拍照欄位誤判為異常**：Ragic 的「拍照」、「拍照2」、「拍照3」等上傳欄位屬於表單必填項目，非巡檢評分點，空白時會被誤計為「異常」
  - `services/security_patrol_sync.py`：`_extract_check_items` 新增 `if "拍照" in str(key): continue` 過濾，未來同步自動排除所有拍照類欄位
  - `main.py`：新增 `_cleanup_security_patrol_photo_items()` 啟動遷移，刪除 `security_patrol_item` 中現有的拍照欄位記錄（271 筆）；下次重啟後立即生效，無需手動重新同步
  - 修正後各 Sheet 統計（`/stats`）及 Dashboard 摘要（`/dashboard/summary`、`/issues`、`/trend`）均自動套用正確計算

---

## [1.22.0] - 2026-04-14

### Added
- **保全巡檢功能**（Security Patrol）：支援 7 張 Ragic Sheet（security-patrol/1、2、3、4、5、6、9），統一模型架構
  - 後端模型：`models/security_patrol.py`（SecurityPatrolBatch + SecurityPatrolItem，以 sheet_key 區分 7 種 Sheet）
  - 同步服務：`services/security_patrol_sync.py`（動態欄位偵測 Pivot 架構，支援逐 Sheet 或全部同步）
  - Pydantic Schemas：`schemas/security_patrol.py`、`schemas/security_dashboard.py`
  - API Router（巡檢）：`routers/security_patrol.py`，prefix `/api/v1/security/patrol`
    - POST `/sync`：同步全部或指定 Sheet
    - GET `/sheets`：取得所有 Sheet 設定
    - GET `/{sheet_key}/batches`：場次清單（月份/日期篩選）
    - GET `/{sheet_key}/batches/{batch_id}`：場次明細（含 KPI + 項目清單）
    - GET `/{sheet_key}/stats`：全站統計（Dashboard 用）
    - GET `/{sheet_key}/items/item-history`：巡檢點近 N 日歷史
  - API Router（Dashboard）：`routers/security_dashboard.py`，prefix `/api/v1/security/dashboard`
    - GET `/summary`：今日各 Sheet KPI 摘要
    - GET `/issues`：異常/未完成清單（支援 Sheet 篩選）
    - GET `/trend`：近 N 日趨勢資料
  - `config.py`：新增 `RAGIC_SP_SERVER_URL`、`RAGIC_SP_ACCOUNT`
  - `main.py`：新增 router 註冊、model import、auto-sync 任務
  - 前端型別：`types/securityPatrol.ts`
  - 前端 API 封裝：`api/securityPatrol.ts`
  - 前端常數：`constants/securitySheets.ts`（7 張 Sheet 設定）
  - 前端 Dashboard 頁（`pages/SecurityDashboard/index.tsx`）：今日統計 + 異常清單 + 7日趨勢
  - 前端巡檢清單頁（`pages/SecurityPatrol/index.tsx`）：通用元件，依 sheetKey 顯示對應 Sheet
  - 前端巡檢明細頁（`pages/SecurityPatrol/Detail.tsx`）：場次 KPI + 巡檢點清單（篩選/搜尋）
  - 路由：新增 `/security/dashboard`、`/security/patrol/:sheetKey`、`/security/patrol/:sheetKey/:batchId`
  - Sidebar：新增「保全管理」群組（Dashboard + 7 子選單）
  - `navLabels.ts`：新增 `NAV_GROUP.security` + 8 個 `NAV_PAGE` 保全相關項目

---

## [1.21.0] - 2026-04-14

### Added
- **商場管理統計 Dashboard**（Mall Operations Monitoring Dashboard）：整合 B1F / B2F / RF 每日巡檢 + 商場週期保養資料，提供主管管理決策視圖
  - 後端 Schemas：`schemas/mall_dashboard.py`（DashboardSummary、FloorInspectionStats、InspectionSummary、PMSummary、IssueItem、TrendPoint 等）
  - API Router：`routers/mall_dashboard.py`，prefix `/api/v1/mall/dashboard`
    - GET `/summary`：今日巡檢 KPI（各樓層分析）+ 本月週期保養 KPI
    - GET `/issues`：異常 / 未完成 / 逾期項目清單（可依類型、樓層、狀態篩選）
    - GET `/trend`：近 7 / 30 日巡檢趨勢資料
  - 前端型別：`types/mallDashboard.ts`
  - 前端 API 封裝：`api/mallDashboard.ts`
  - 前端 Dashboard 頁（`pages/MallDashboard/index.tsx`）：
    - 8 張 KPI 卡（4 巡檢 + 4 保養，可點擊跳至對應清單）
    - 整體完成率進度條
    - 各樓層執行比較圖（完成率橫條圖 + 異常/未巡檢堆疊橫條圖）
    - 各樓層摘要卡（含快速連結）
    - 今日巡檢狀態圓餅圖
    - 本月保養狀態摘要
    - 近 7 / 30 日完成率折線趨勢圖
    - 每日異常件數長條趨勢圖
    - 重點追蹤清單（Tabs：全部 / 異常 / 未完成 / 逾期保養；含明細深連結）
  - 導覽：`NAV_PAGE.mallDashboard`，路由 `/mall/dashboard`，位於商場管理選單第一項（整棟工務每日巡檢 - B1F 之前）

---

## [1.20.0] - 2026-04-14

### Added
- **整棟工務每日巡檢 B1F**：串接 Ragic Sheet 4（`soutlet001/full-building-inspection/4`），置於「商場管理」群組
  - 後端 ORM 模型：`b1f_inspection_batch` / `b1f_inspection_item`（`models/b1f_inspection.py`）
  - Pydantic Schemas：`B1FInspectionBatchOut`、`B1FInspectionItemOut`、`B1FInspectionBatchKPI`、`B1FInspectionStats` 等（`schemas/b1f_inspection.py`）
  - 同步服務：`services/b1f_inspection_sync.py`（動態欄位偵測，Sheet 4 欄位自動 pivot）
  - API Router：`/api/v1/mall/b1f-inspection`（8 個端點，同 RF/B2F 規格）
  - APScheduler：每 30 分鐘自動同步 B1F 資料
  - 前端型別：`types/b1fInspection.ts`
  - 前端 API 封裝：`api/b1fInspection.ts`
  - 前端儀表板（`pages/B1FInspection/index.tsx`）：4 KPI 卡 + 完成率進度條 + 7 日異常趨勢 + 狀態圓餅 + 預警清單 + 最新場次入口
  - 前端明細頁（`pages/B1FInspection/Detail.tsx`）：場次資訊卡 + 4 欄巡檢表格 + 狀態 Tab + 30 日歷史 Drawer
  - 導覽：`NAV_PAGE.b1fInspection`，路由 `/mall/b1f-inspection` 及 `/mall/b1f-inspection/:batchId`，MainLayout 商場管理群組新增項目

---

## [1.19.0] - 2026-04-14

### Added
- **整棟工務每日巡檢 B2F**：串接 Ragic Sheet 3（`soutlet001/full-building-inspection/3`），置於「商場管理」群組
  - 後端 ORM 模型：`b2f_inspection_batch` / `b2f_inspection_item`（`models/b2f_inspection.py`）
  - Pydantic Schemas：`B2FInspectionBatchOut`、`B2FInspectionItemOut`、`B2FInspectionBatchKPI`、`B2FInspectionStats` 等（`schemas/b2f_inspection.py`）
  - 同步服務：`services/b2f_inspection_sync.py`（動態欄位偵測，Sheet 3 欄位自動 pivot）
  - API Router：`/api/v1/mall/b2f-inspection`（8 個端點，同 RF 規格）
  - APScheduler：每 30 分鐘自動同步 B2F 資料
  - 前端型別：`types/b2fInspection.ts`
  - 前端 API 封裝：`api/b2fInspection.ts`
  - 前端儀表板（`pages/B2FInspection/index.tsx`）：4 KPI 卡 + 完成率進度條 + 7 日異常趨勢 + 狀態圓餅 + 預警清單 + 最新場次入口
  - 前端明細頁（`pages/B2FInspection/Detail.tsx`）：場次資訊卡 + 4 欄巡檢表格 + 狀態 Tab + 30 日歷史 Drawer
  - 導覽：`NAV_PAGE.b2fInspection`，路由 `/mall/b2f-inspection` 及 `/mall/b2f-inspection/:batchId`，MainLayout 商場管理群組新增項目

---

## [1.18.0] - 2026-04-14

### Added
- **整棟工務每日巡檢 RF**：串接 Ragic Sheet 1（`soutlet001/full-building-inspection/1`），置於「商場管理」群組
  - 後端 ORM 模型：`rf_inspection_batch` / `rf_inspection_item`（`models/rf_inspection.py`）
  - Pydantic Schemas：`RFInspectionBatchOut`、`RFInspectionItemOut`、`RFInspectionBatchKPI`、`RFInspectionStats` 等（`schemas/rf_inspection.py`）
  - 同步服務：`services/rf_inspection_sync.py`（**動態欄位偵測**：自動掃描 Ragic Row 欄位，排除場次 metadata 後全數 pivot 為巡檢項目，無需預定義欄位清單）
  - API Router：`/api/v1/mall/rf-inspection`（sync / batches / batches/{id} / batches/{id}/kpi / items / stats / items/item-history / debug/ragic-raw）
  - APScheduler：每次自動同步加入 RF 場次，log 顯示 `check_item_count`（本次偵測到欄位數）
  - 前端型別：`types/rfInspection.ts`（`RFInspectionResultStatus` + 8 個 interface）
  - 前端 API 封裝：`api/rfInspection.ts`（fetchRFBatches / fetchRFBatchDetail / fetchRFStats / syncRFFromRagic / fetchRFItemHistory）
  - 前端儀表板（`pages/RFInspection/index.tsx`）：4 KPI 卡 + 完成率進度條 + 7 日異常趨勢折線圖 + 狀態分布圓餅 + 異常/待處理 Alert 表格 + 最新場次速覽
  - 前端明細頁（`pages/RFInspection/Detail.tsx`）：場次資訊卡 + 4 欄巡檢表格 + 狀態 Tab + 項目歷史 Drawer（30 日月曆）
  - 導覽：`NAV_PAGE.rfInspection`，路由 `/mall/rf-inspection` 及 `/mall/rf-inspection/:batchId`，MainLayout 商場管理群組新增項目

---

## [1.17.0] - 2026-04-14

### Added
- **整棟工務每日巡檢 B4F**：串接 Ragic Sheet 2（`soutlet001/full-building-inspection/2`），置於「商場管理」群組

### Changed
- **B4F 架構重構（寬表格 Pivot v3）**：Ragic Sheet 2 為寬表格格式（一 Row = 一場次 + 35 設備欄位），改以 Pivot 方式同步
  - 後端 ORM：`b4f_inspection_batch`（ragic_id PK, start_time, end_time, work_hours）、`b4f_inspection_item`（`{batch_ragic_id}_{seq_no}` PK, item_name, result_status）
  - 同步服務：`CHECK_ITEMS` 清單定義 35 個設備欄位名稱，每欄 pivot 成一筆 item 記錄
  - Migration：`_migrate_b4f_flatten()` 自動識別並刪除舊版（v1 子表格 / v2 扁平）schema
  - `batch_id = ragic_id`（Ragic Row ID），移除 `batch_key`、`shift`、`zone`、`category` 等舊欄位
  - 前端 `Detail.tsx`：簡化為 4 欄（項次、巡檢項目、結果、原始值）+ 場次資訊卡（start_time/end_time/work_hours）
  - 前端 `api/b4fInspection.ts`：`fetchB4FBatchDetail` 改為 `status`/`search` 參數（移除舊 zone/category）
  - 導覽：`NAV_PAGE.b4fInspection`，路由 `/mall/b4f-inspection` 及 `/mall/b4f-inspection/:batchId`，MainLayout 商場管理群組新增 `SafetyOutlined` 選單項目

---

## [1.16.0] - 2026-04-14

### Added
- **商場週期保養表（1.2）**：仿照「飯店週期保養表」完整功能，串接 Ragic Sheet 18（`soutlet001/periodic-maintenance/18`）
  - 後端 ORM 模型：`mall_pm_batch` / `mall_pm_batch_item`（`models/mall_periodic_maintenance.py`）
  - 同步服務：`services/mall_periodic_maintenance_sync.py`（支援 A/B/C/D 四種子表格解析模式）
  - API Router：`/api/v1/mall/periodic-maintenance`（sync / batches / stats / items / task-history / debug）
  - `config.py`：新增 `RAGIC_MALL_PM_*` 四個設定常數（server/account/journal/items path）
  - 前端 API 封裝：`api/mallPeriodicMaintenance.ts`
  - 前端頁面：`pages/MallPeriodicMaintenance/index.tsx`（主管儀表板 + 批次清單 Tabs）、`Detail.tsx`（工單明細 + 進階篩選 + 歷史 Drawer）
  - 導覽：新增「商場管理」群組（`NAV_GROUP.mall`）、`NAV_PAGE.mallPeriodicMaintenance`，路由 `/mall/periodic-maintenance`

---

## [1.15.0] - 2026-04-13

### Added
- **富文字編輯器（圖文並茂）**：引入 `react-quill-new@3.8.3`（React 18 相容的 Quill.js fork），建立共用 `RichTextEditor` 元件（`frontend/src/components/Editor/RichTextEditor.tsx`）
- **圖片上傳 API**：新增後端 `POST /api/v1/upload/image` 端點，儲存至 `uploads/images/`，回傳 URL 供 Quill 插入；`GET /api/v1/upload/image/{filename}` 提供圖片服務
- **新增簽核單（Approvals/New）升級**：「說明」與「機敏資訊」欄位改為富文字編輯器，支援圖文混排
- **新增公告（Memos/New）升級**：「內文」改為富文字編輯器；新增「附件」上傳區塊，可一次選取多個檔案隨公告一起送出
- **公告附件系統**：新增 `MemoFile` ORM 表（`memo_file`）、`POST /api/v1/memos/{id}/files` 上傳端點、`GET /api/v1/memos/{id}/files/{file_id}` 下載端點；附件儲存至 `uploads/memo_files/`
- **公告詳情（Memos/Detail）升級**：附件清單顯示（檔名/大小/下載按鈕）；作者可在詳情頁追加附件；編輯 Modal 升級為富文字編輯器

---

## [1.14.6] - 2026-04-13

### Fixed
- **儀表板三處統計一致化**：KPI「已完成」、完成率、狀態分布圓餅圖，全部統一以「保養時間啟+迄均有值」為「完成」定義（含非本月項目）
  - `_calc_kpi.completed` = 全部項目中有啟+迄的數量（含非本月）
  - `_calc_kpi.completion_rate` = completed / total（全部項目）
  - `get_stats` status_distribution：非本月且有啟+迄的項目歸入「已完成」桶；非本月且無完成時間的項目不顯示
  - 前端進度條分母改為 `kpi.total`；批次清單標籤改為「已完成/全部」
  - `deriveBatchStatus` 批次完成判斷改用 `completed === total`

## [1.14.5] - 2026-04-12

### Fixed
- **週期保養表「已完成」統計錯誤修正**：`_calc_status()` 的「已完成」判斷從「只要 `end_time` 有值」改為「`start_time` AND `end_time` 均有值」，與 Detail 表格「完成」欄（`is_completed`）定義完全一致；此修正同步影響 KPI、完成率進度條、類別統計圖表、批次狀態判斷
- **`is_completed` DB 回填**：`migration` 函式加入 UPDATE 語句，啟動時自動將舊資料中「啟+迄均非空但 `is_completed=0`」的記錄補正為 `is_completed=1`
- **`_item_to_out` 動態計算**：`is_completed` 不再依賴 DB 存的舊值，改為每次動態從 `start_time AND end_time` 推導，確保 API 回傳值永遠正確

---

## [1.14.4] - 2026-04-12

### Changed
- **週期保養表 — Portal 改為純唯讀視圖**：移除工單回填 Drawer、編輯按鈕、PATCH endpoint；資料全部由 Ragic 同步提供，Portal 不再有任何覆寫能力
- **狀態判斷邏輯明確化**（純 Ragic 欄位，無 Portal 覆寫）：
  1. 非本月 — `exec_months_json` 有值且當月不在清單
  2. 已完成 — `保養時間迄`（end_time）有值
  3. 進行中 — `保養時間啟`（start_time）有值但無迄
  4. 逾期   — `排定日期` 有值且已過今天
  5. 已排定 — `排定日期` 有值
  6. 未排定 — 以上皆無
- **同步服務移除 portal_edited_at 保護**：每次同步全部以 Ragic 資料為準
- **is_completed 改為純唯讀顯示欄位**（sync 自動計算：start_time AND end_time 均有值），不再允許 Portal 手動設定
- 停用 `PMItemUpdate` Schema 及 `updatePMItem` API 函式

---

## [1.14.3] - 2026-04-12

### Added
- **週期保養表 — `is_completed` 完成標記欄位**：`pm_batch_item` 新增 `is_completed BOOLEAN DEFAULT 0` 欄位；Ragic 同步時自動計算（保養時間啟 + 保養時間迄均有值 → `True`）；Portal 回填 Drawer 亦可手動切換完成/未完成；表格新增「完成」圖示欄
- **DB 輕量移轉**：`main.py` 啟動時透過 `ALTER TABLE ADD COLUMN` 安全補丁現有 SQLite 表格（若欄位不存在才執行）
- **狀態計算改版**：`_calc_status()` 改以 `is_completed` 欄位判斷已完成狀態（兼容舊資料：`end_time` 有值亦視為完成）
- **`PMItemUpdate` Schema** 新增 `is_completed` 可選欄位；前端 `PMItem` 型別亦同步

---

## [1.14.2] - 2026-04-12

### Fixed
- **週期保養表 sync 根本修正**：子表格 key `_subtable_1011397` 以底線開頭，舊程式碼所有解析路徑均以 `startswith("_")` 跳過 → 新增方式D 專門處理 `_subtable_*` key，正確提取 `{"1":{row},"2":{row}...}` 子列；同步診斷 log 亦修正，不再略過 `_` 前綴 key

### Added
- **週期保養表明細 — 多重狀態篩選**：篩選列新增「狀態篩選（可複選）」Select，支援同時選取非本月、未排定等多個狀態；獨立「有排定日期」Checkbox 供跨狀態 cross-filter（例：非本月 + 有排定日期）；Tabs 新增「非本月」快速切換頁；多選啟用時顯示「複選篩選中」虛擬 Tab
- **週期保養表明細 — 保養項目歷史 Drawer**：點擊保養項目名稱 → 跨批次查詢近 12 個月執行歷史；12 格月曆（已完成=綠/異常=橙/逾期=紅/當月未排=黃/無批次=灰）；KPI 卡（完成次數/完成率/異常次數）；點選月格展開該月執行詳情（人員/時間/備註/狀態）
- **後端新端點** `GET /api/v1/periodic-maintenance/items/task-history?task_name=X&months=12`：依項目名稱跨批次查詢執行歷史，回傳月曆摘要 + 統計
- **前端型別** `PMItemHistorySummary`、`PMTaskHistoryStats`、`PMTaskHistory`；API 函式 `fetchPMTaskHistory`

---

## [1.14.1] - 2026-04-12

### Fixed
- **週期保養表 sync 重大修正**：Sheet 8 結構為「批次記錄含嵌入子表格列」，而非平表 item 列表；重寫 `sync_items_from_ragic()` 解析數字 key 子列（"1","2","3"…），item.ragic_id 改為 `"{batch_id}_{row_key}"` 格式（如 "5_1"）；移除舊 `_get_parent_id()` 函式；新增 `CK_NOTE="備註"` 欄位映射；舊格式空白記錄自動清除
- 後端 debug 端點：`GET /api/v1/periodic-maintenance/debug/ragic-raw` 方便確認 Ragic 回傳 key 結構

---

## [1.14.0] - 2026-04-12

### Added
- **週期保養表** 功能全面上線（Phase 1 + 2 + 3）
  - 後端 DB 模型：`pm_batch`（批次主表）+ `pm_batch_item`（項目明細），含 `portal_edited_at` 同步保護欄位
  - 後端 Pydantic Schemas：`PMBatchOut`, `PMItemOut`, `PMBatchKPI`, `PMBatchDetail`, `PMStats`, `PMItemUpdate`
  - 後端 Router（`/api/v1/periodic-maintenance`）：POST /sync、GET /batches、GET /batches/:id、GET /batches/:id/kpi、GET /items、GET /stats、PATCH /items/:id
  - 後端 `periodic_maintenance_sync.py`：Ragic ap12 Sheet 6（批次）+ Sheet 8（項目）同步；執行月份解析（"2月 5月 8月 11月" → [2,5,8,11]）；portal_edited_at 同步保護
  - 後端 `config.py` 新增 `RAGIC_PM_SERVER_URL`、`RAGIC_PM_JOURNAL_PATH`、`RAGIC_PM_ITEMS_PATH` 設定
  - `main.py` 整合週期保養自動同步（每 30 分鐘）
  - 前端型別定義：`periodicMaintenance.ts`（PMBatch, PMItem, PMItemStatus, PMBatchKPI, PMBatchDetail, PMStats, PMItemUpdate）
  - 前端 API 封裝：`periodicMaintenance.ts`（fetchPMBatches, fetchPMBatchDetail, fetchPMStats, updatePMItem, syncPMFromRagic）
  - 前端主頁 `pages/PeriodicMaintenance/index.tsx`：主管儀表板（KPI 4卡、完成率進度條、類別 BarChart、狀態 PieChart、逾期 Top10、本週即將到期）+ 批次清單 Tab
  - 前端明細頁 `pages/PeriodicMaintenance/Detail.tsx`：工單式頁面，KPI 6卡 + 完成率進度條、狀態 Tab 篩選（7 個）、類別/關鍵字篩選、色碼表格（未排定紅底、非本月灰底）、600px 右側 Drawer 回填（排程 + 執行記錄 + 異常旗標）
  - 前端路由：`/hotel/periodic-maintenance`、`/hotel/periodic-maintenance/:batchId`
  - Sidebar 新增「週期保養表」選單項目
  - `navLabels.ts` 新增 `periodicMaintenance` 常數

---

## [1.13.0] - 2026-04-11

### Added
- 「保養統計」Tab（Tab 5）：完整 Phase 1 + Phase 2 + Phase 3 統計分析功能
  - **Phase 1 — 完成率趨勢 + 高風險房間**
    - 近12月完成率 × 異常率雙軸折線趨勢圖（Recharts LineChart 雙 Y 軸）
    - KPI 六卡：當月完成率、12月均值趨勢、當月異常率、連續未保養房間數、全正常房間數、重複異常房間數
    - 高風險房間三子 Tab：連續未保養（≥2月）/ 重複異常（同項目連續2月X）/ 全正常（最近3筆均全V）
  - **Phase 2 — 異常項目分析**
    - 12 個檢查項目累計 X 次數水平橫條圖，依嚴重度色彩分層（紅/橙/黃/藍）
    - 右側明細排行表：項目名稱 + X次數 + 異常率%
  - **Phase 3 — 樓層分析 + 月份對比**
    - 各樓層當月完成率 vs 全期異常次數雙柱圖
    - 當月 / 上月 / 去年同月三期對比圖 + 明細列
- 後端新增 `GET /api/v1/room-maintenance-detail/maintenance-stats` 端點
  - 一次回傳所有統計資料（monthly_trend / check_item_stats / floor_stats / risk_rooms / comparison / kpi）
  - 支援 `months` 參數（1~36，預設 12）
- 前端新增 TypeScript Interface：`MaintenanceStatsResponse`、`MonthlyTrend`、`CheckItemStat`、`FloorStat`、`ConsecutiveMissedRoom`、`RepeatedAbnormalRoom`、`FullyOkRoom`、`MonthComparison`
- 前端新增 API 函式：`fetchMaintenanceStats(months)`
- 產出設計規格書：`保養統計功能設計規格書_v1.13.0.docx`

---

## [1.12.0] - 2026-04-11

### Added
- 導覽文字 SSOT：新增 `frontend/src/constants/navLabels.ts` 作為 Menu / Breadcrumb / 頁面 Title 的唯一真相來源
  - `SITE_TITLE`、`NAV_GROUP`、`NAV_PAGE` 三個常數物件涵蓋全站導覽文字
  - 修改任一文字只需改 `navLabels.ts`，三處自動同步，不需分別修改
  - `MainLayout.tsx` 已接入：Sidebar 標題、所有選單群組與頁面文字
  - `RoomMaintenanceDetail/index.tsx` 已接入：Breadcrumb 與頁面 Title
  - `docs/TECH_SPEC.md` 新增「導覽文字維護指南」章節，說明修改方法與維護紀錄

### Changed
- 「客房保養明細」顯示名稱 → 「保養管理」（路由 `/hotel/room-maintenance-detail` 不變）

---

## [1.11.0] - 2026-04-11

### Added
- 人員工時表統計：新增月份選擇器（YYYY/MM），可切換任意月份重新計算所有統計數字
  - 預設顯示最新月，選單由新到舊排列，最新月加