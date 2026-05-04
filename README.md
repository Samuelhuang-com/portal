# 集團 Portal 系統

> 跨據點統一管理平台 — FastAPI + React + TypeScript

**最後更新：2026-05-03（v1.55.2）**

## 最近變更
- v1.55.2：**知識庫 Graph View** — Portal 內建圖譜視圖（`@xyflow/react`）；`GET /api/v1/wiki/graph`（標籤重疊邊 + `[[連結]]`邊）；`POST /auto-link`（自動補充相關文章連結）；Header 清單/圖譜 Segmented 切換；SOP 左環 / Dev 右環佈局；MiniMap + 圖例；點節點跳轉文章
- v1.55.1：**知識庫 Obsidian 雙向同步** — `POST /api/v1/wiki/export-obsidian`（DB→.md）、`POST /api/v1/wiki/import-obsidian`（.md→DB）；前端 Header「同步 Obsidian」Dropdown；同步結果 Modal（新增/更新/跳過/錯誤）；修正 `_wiki_dir()` parent 計數錯誤
- v1.55.0：**知識庫（LLM Wiki）** — 新功能 `/wiki`；員工 SOP 知識庫 + 開發者技術 Wiki 雙分類；Markdown 渲染；AI 問答助手（Claude API，ANTHROPIC_API_KEY）；10 篇 SOP 範例 + 5 篇開發者 Wiki 自動植入；後端 `/api/v1/wiki/` CRUD + `/ask` endpoint；`anthropic>=0.25.0` 加入 requirements.txt
- v1.54.9：**決策駕駛艙 Phase 3~8 全部完成** — B.飯店(6來源SourceCard) / C.商場(4工項+2灰燈) / D.工務(雙欄+12M折線) / E.人員工時(Top10 Bar) / F.風險雷達(10模組燈號矩陣) / G.趨勢(日度+月工時LineChart) / H.晨會摘要(規則式文字+複製) / I.資料品質(完整度Table) / Phase7 window.print / Phase8 後端 decision_cockpit_view
- v1.54.1：**決策駕駛艙 Phase 2 — A.決策總覽** — `healthScore.ts` 計算工具（4 維度權重、燈號判斷、群組加權）；`TabOverview.tsx` 健康分數矩陣大圓 + 三子分數 + 工務/客房 KPI 彙整列 + 規則式 5 件事
- v1.54.0：**決策駕駛艙 Phase 1** — 新一級選單 `/decision-cockpit`（PermissionGuard: `decision_cockpit_view`）；9 TAB 懶載入框架；月份選擇器（24 個月）；3 份規劃 MD（PLANNING / KPI_DATASOURCE_MAP / HEALTH_SCORE_SPEC）；9 個 TAB stub 元件
- v1.53.8：**`mall/overview` 版型對齊飯店版** — 年月 Select + 匯出按鈕移至右上角 header Card；Tab A 篩選列簡化
- v1.53.7：**`mall/overview` 匯出 PowerPoint（5 張投影片）** — 後端 `mall_overview.py` POST endpoint + `_build_mall_pptx()` 三層 KPI Slide；前端 `mallOverview.ts` 新增 Payload 型別 + `exportMallOverviewPptx`；MallMgmtDashboard 加入匯出按鈕（月份為 0 時 disabled）
- v1.53.6：**`hotel/overview` 匯出 PowerPoint — Slide 2 三層 KPI 總覽（方向 B）** — POST endpoint 接收前端 KPI payload（主管摘要/各來源狀態/費用）；Slide 2 渲染 5 KPI box + 2×4 來源卡 + 3 費用 box；Slide 3-5 後端自行查 DB；前端組裝 payload 後 POST 下載
- v1.53.5：**飯店每日巡檢 & 保全巡檢 Dashboard 全月篩選** — Segmented「單日/全月」切換；全月模式呼叫 monthly-summary 端點；保全新增 `fetchSecurityDashboardMonthlySummary`；趨勢圖僅單日顯示
- v1.53.4：**`hotel/overview` KPI 月份口徑全面修正** — room_maintenance_detail / IHG stats / hotel_daily_inspection / security_dashboard 全部改傳 year/month；每日巡檢 & 保全改用月份彙總新端點；IHG 改 distinct room_no + work_hours；移除整體完成率圓餅；工務部「異常」→「未完成」
- v1.53.3：**`hotel/periodic-maintenance` 同步 Ragic「工時計算」欄位** — Model 新增 `ragic_work_minutes`；sync service 讀取「工時計算」；KPI `actual_minutes` 優先用 Ragic 欄位，NULL 則 fallback end−start；startup 自動 ALTER TABLE migration
- v1.53.2：**`hotel/periodic-maintenance` Dashboard 新增「預估工時」和「保養時間」KPI 卡片** — 後端補 `_time_diff_minutes()` + `actual_minutes` 計算；前端新增兩張 Statistic 卡（比照 mall 模組）
- v1.53.1：**`dazhi-repair/dashboard` 計算口徑對齊 luqun** — 新增 occ_year/occ_month；修正 this_month_new 雙重計入、fee_month_cases 口徑、trend_12m 報修月基準、_str() falsy-0 bug；移除畫面「大直」文字（4 處）
- v1.53.0：**`hotel/overview` 來源卡片加入「預估工時 / 保養時間」雙行（Option A）** — NormalizedSource 新增 actual_hours?；飯店週期保養 SourceCard 顯示計劃工時（藍）與保養時間（綠）
- v1.52.6：**`mall/overview` 全模組文字放大 2 級** — 89 處 fontSize 統一 +2（11→13、12→14、13→15 ... 22→24）
- v1.52.5：**`mall/overview` 各來源卡依年月篩選重算** — 年月變更同步觸發商場/全棟例行維護（PM stats year/month）、商場工務巡檢（monthly-summary 月統計）、樂群報修四卡重載；新增 `normalizeFacilityMonthly`
- v1.52.4：**`mall/overview` KPI 卡工時拆分「預估工時（藍）＋保養時間（綠）」** — `NormalizedSummary.actual_hours`；`normalizePM` 讀 `kpi.actual_minutes`；`daily/monthly/person-hours` 例行維護改用 `start_time`/`end_time` 實際差值
- v1.52.3：**三大監控模組 Dashboard 查詢月份功能**（每日數值登錄 / 商場工務巡檢 / 整棟巡檢）— 月份選擇器 + URL `?month=YYYY-MM` + KPI 依月份重算 + 今/末日 Badge + 共用 `date_utils.get_month_range`
- v1.52.3：**商場 / 全棟保養 Dashboard 新增「預估工時」KPI 卡**；「保養時間」改為實際 end−start 差值合計；後端 PMBatchKPI 加 actual_minutes
- v1.52.2：**三大保養模組 Dashboard 年月篩選**（飯店週期保養 / 商場週期保養 / 全棟例行維護）— 各模組 Dashboard 頂部加年月 Select；KPI/圖表/預警清單隨選月份同步重算；三支後端 `/stats` 均加 `year`/`month` query params
- v1.52.1：**mall/overview Tab B「例行維護」0 值修正** — period_month 改用 LIKE + Python 月份過濾（相容零填充/非零填充格式）；無 scheduled_date 的未排定項目落回第 1 天，確保合計與 planned_minutes / 60 一致
- v1.49.1：**飯店管理 Dashboard Tab B「現場報修」工時口徑修正** — `hotel_overview.py` 大直工務部選案邏輯由 occurred_at 月改為對齊 dashboard：已完工案件按 completed_at 月、未完工按 occurred_at 月（daily/monthly 兩端點同步修正）
- v1.49.0：**飯店管理 Dashboard Tab B「每日累計」版型修正** — 五項工作類別（現場報修/上級交辦/緊急事件/例行維護/每日巡檢）取代六項來源；Tag badge 渲染；Card 包裝（標題+year月）；欄位「工項類別」/「TOTAL」/「%」格式；後端 API 不變
- v1.48.0：**飯店管理 Dashboard 移除三個 Tab（保養管理/巡檢管理/大直工務）** — 刪除 3 個 Tab 項目及 8 個對應內嵌函式（SecurityTrendChart / HotelDICards / SecuritySheetCards / CompletionRateRow / DazhiSummary / PMSummary / IHGSummary 等）；保留 DazhiTrendChart / SourcePieChart（總覽 Tab 仍使用）
- v1.47.0：**飯店管理 Dashboard 新增三大區塊** — 總覽 Tab 加入篩選列（大直工務年月+巡檢日期 DatePicker+今日）；報修費用摘要（委外+維修/扣款/本月費用 3 卡）；決策分析圖表（橫向案件數比較+完成率比較 BarChart，Donut Pie+趨勢折線）
- v1.46.0：**飯店管理 Dashboard 版型全面對齊 mall/overview** — KpiAggregate 重構（6 標準卡：總工項/已完成/整體完成率圓餅/工時/異常/逾期，移除 size=small，fontSize 11）；SourceCards 重構（Card title+icon+色彩+詳情按鈕，雙欄 Statistic+漸層 Progress+底部異常/逾期/工時）；NormalizedSource 新增 completed_count/overdue_count
- v1.45.0：**飯店管理 Dashboard Tab B/C/D/人員排名** — 後端 3 支新 API（`/hotel/daily-hours` / `/hotel/monthly-hours` / `/hotel/person-hours`），`hotel_overview.py` + `main.py` 掛載；前端 `api/hotelOverview.ts` + 4 個懶載入 Tab（每日累計/每月累計/人員工時%/人員排名）；人員排名橫向 Bar + 明細表
- v1.44.0：**飯店管理 Dashboard（新功能）** — 整合 6 來源（客房保養管理/飯店週期保養/IHG客房保養/飯店每日巡檢/保全巡檢/大直工務部）跨模組總覽；前端 Normalize adapter 層；KPI 卡 + 各來源狀態卡 + 4 張圖表；route `/hotel/overview`；Menu 飯店管理群組置頂
- v1.43.5：**商場管理 Dashboard Tab D 重寫** — 後端新增 `GET /api/v1/mall/person-hours`（Top-15 人員 × 5 工項）；Tab D 改為 WCA 格式工項×人員交叉表（%色彩編碼）；移除舊 Pie chart、集中度分析
- v1.43.4：**商場管理 Dashboard Tab C 重寫** — 移除舊 PM 完成率矩陣；後端新增 `GET /api/v1/mall/monthly-hours`；Tab C 改為五工項 × 12 月工時交叉表，格式與 work-category-analysis Tab C 一致
- v1.43.3：**商場管理 Dashboard Tab B 重寫** — 後端新增 `GET /api/v1/mall/daily-hours`，彙整五項工作類別（現場報修/上級交辦/緊急事件/例行維護/每日巡檢）每日 HR；前端新增 `api/mallOverview.ts`；Tab B 改為五工項 × 日期交叉表，格式與 work-category-analysis 一致
- v1.43.2：**樂群 扣款費用口徑統一** — `month_deduction_fee`、`annual_deduction_fee`、`compute_fee_stats` 扣款費用欄全數加入 `is_completed + deduction_counter_name` 篩選，與扣款專櫃完全同口徑；消除有扣款費但無專櫃名稱案件（資料缺漏）造成的金額差異
- v1.43.0：**保全巡檢模組整合** — 8 個獨立選單整合為單一入口 `/security/dashboard`；外層 TAB（Dashboard + 7 張 Sheet）；SecurityPatrolContent prop 拆分；Menu 簡化；後端零改動
- v1.42.0：**每日數值登錄表模組（新功能）** — 4 張 Ragic Sheet（全棟電錶/商場空調箱電錶/專櫃電錶/專櫃水錶）整合；Dashboard + 各 Sheet 列表；route `/hotel/daily-meter-readings`；Menu「飯店管理 > 每日數值登錄表」；权限 `hotel_meter_readings_view`
- v1.41.4：**樂群報修 Dashboard 計算標籤對齊** — 扣款專櫃 Modal 三處「全年」改用動態 `ytdLabel`；確認後端三類互斥邏輯（completed / pending_verify / uncompleted）與 YTD 費用累計已全數到位
- v1.41.0：**自訂角色 CRUD** — 「角色管理」頁可新增（Modal 表單）/刪除自訂角色（Popconfirm 確認），內建角色受保護；後端 POST/DELETE `/api/v1/roles`，cascade 清除 role_permissions 與 user_roles；Roles.tsx 完全改寫為動態架構，「權限設定」Tab 支援所有角色（含自訂）
- v1.40.0：**Menu 權限管控機制（RBAC）** — 三層防護（sidebar 過濾 → PermissionGuard → API require_permission）；新增 `role_permissions` 表；`/auth/me` 回傳 `permissions`；Roles.tsx 加「權限設定」Tab；MenuConfig 加 permission_key 欄；新模組開發規則：permissionKey='system_admin_only'，測試完成後手工授予
- v1.39.46：**樂群 扣款專櫃計算邏輯修正** — 當月金額改用 `fee_month_cases`（與金額統計 tab 口徑對齊）；YTD/全年加 `is_completed` gate，排除待辦驗案件的 `completed_at` 跨月汙染
- v1.39.45：**樂群 報修清單總表「報修詳情」補附圖顯示** — `DetailTab` 內嵌 Drawer 改為共用 `<CaseDetailDrawer>`，統一顯示維修圖片（DB 圖片優先、Ragic lazy-fetch 備援）
- v1.39.44：**樂群／大直 Dashboard KPI 邏輯修正** — `is_completed_flag` 改以 `status`（處理狀況）為唯一依據；`未完成 = 總數 - 已完成 - 待辦驗`（三類互斥）；`_prev_uncompleted`、`kpi_uncompleted_detail`、`trend_12m`、`top_uncompleted` 全數同步改用 status 判斷
- v1.39.42：**飯店每日巡檢模組（新功能）** — 5 張 Ragic Sheet（RF/4F-10F/4F/2F/1F）同步至本地 DB；6-Tab 整合頁（Dashboard + 各區域巡檢紀錄）；route `/hotel/daily-inspection`；menu 掛於「飯店管理」下
- v1.39.41：**商場管理 Dashboard — KPI 卡片版型調整** — 兩列 KPI（商場例行維護/全棟例行維護/商場工務巡檢/整棟巡檢 + 大直報修/交辦/緊急事件）
- v1.39.40：**商場管理 Dashboard（新功能）** — 整合 5 來源（商場例行維護/全棟例行維護/商場工務巡檢/整棟巡檢/大直工務報修）的總覽 Dashboard；前端 Normalize adapter；KPI 卡片 + 各來源狀態卡 + 4 張圖表；route `/mall/overview`
- v1.39.39：**系統設定 RBAC** — `系統設定` 選單及 `/settings/*` 路由僅限 `system_admin` 可見；前端 `SettingsGuard` + `MainLayout` 過濾 + `authStore` JWT decode；後端 `menu_config` / `ragic` GET endpoints 補 `is_system_admin` 保護
- v1.39.34：**全棟例行維護（新功能）** — Ragic Sheet 21 同步；`full_bldg_pm_batch` + `full_bldg_pm_batch_item` 雙表；`/api/v1/mall/full-building-maintenance` API；前端 `FullBuildingMaintenance` 儀表板 + 批次清單 + 批次明細 + ItemHistoryDrawer；商場管理 menu 重構為三層（`mall-pm-group` → 商場週期保養 / 商場例行維護 / 全棟例行維護）
- v1.39.20：**春大直商場工務巡檢整合** — 獨立群組移至「商場管理」下；六 Tab 整合頁（統計總覽 + 4F/3F/1F~3F/1F/B1F~B4F 巡檢紀錄），真實 API 保留，懶載入 + URL ?tab= 支援；側邊欄簡化
- v1.39.19：**整棟巡檢整合** — 「整棟巡檢」獨立群組移至「商場管理」下；五 Tab 整合頁（統計總覽 / RF / B4F / B2F / B1F 巡檢紀錄），懶載入 + URL ?tab= 支援；側邊欄簡化
- v1.39.18：**商場管理整合** — 「商場管理」群組六個子頁面合併為單一「商場週期保養」頁；新增六 Tab（統計總覽 / 週期保養 / B4F / RF / B2F / B1F 巡檢紀錄），各 Tab 懶載入 + 同步 Ragic；側邊欄簡化為單一入口
- v1.39.17：**選單管理（新功能）** — 系統設定新增「選單管理」頁；支援拖拉調整一級群組與子選單順序（@dnd-kit）、雙擊 inline 改名、最近 5 筆變更歷史記錄（diff + 快照）；MainLayout 啟動時動態套用設定，失敗時 fallback 至預設
- v1.39.15：**ExecMetrics 共用元件** — 抽取 `src/components/ExecMetrics/index.tsx`（`HeroKpi`/`ExecHeroLayer`/`ExecSourceCards`/`ExecMetricsCard`）；Dashboard 頂部以 `ExecMetricsCard` 取代隱藏的 `BudgetSummaryCard`；ExecDashboard 重構使用共用元件，顯示行為不變
- v1.39.11：**Session 過期自動跳轉登入** — `PrivateRoute` 加 JWT 到期主動偵測（掛載/60s/visibilitychange）；apiClient 401 攔截器加 `_redirecting` flag；後端 SPA catch-all 路由修正前端路由 404 問題
- v1.39.10（原）：**樂群 Drawer 圖片 lazy-fetch（終極修正）** — 新增 `GET /case-images/{ragic_id}` 端點直接呼叫 Ragic detail；Drawer 開啟時若 DB 無圖則自動抓，顯示 Spin → 縮圖，不再依賴 sync 時機
- v1.39.10：**樂群報修詳情 Drawer — 維修圖片修正** — ORM 補 `images_json` 欄位；startup migration；sync 時儲存；`to_dict()` 解析還原，Drawer 現在能顯示 Ragic 圖片
- v1.39.9：**照片縮圖 + KPI Tooltip 全模組完成** — 樂群/大直報修 Drawer 圖片改 72×72 縮圖（`Image.PreviewGroup`）；保全巡檢、商場管理 Dashboard KPI 卡同步補 `?` 說明 Tooltip；說明檔共 4 個（`constants/kpiDesc/`）
- v1.39.8：**樂群 金額統計 Tab — 扣款專櫃改家數、排除月份小計** — 後端改計唯一專櫃家數（整數）、全年跨月去重；月份小計 / grand_total 只含金額欄位；前端顯示「N 家」
- v1.39.7：**樂群 Dashboard — 扣款專櫃 KPI 卡改全年統計** — 後端新增 `annual_counter_fee` / `annual_counter_store_names`；`DashboardKpi` 補型別宣告；KPI 卡與 Modal 切換至全年欄位
- v1.39.6：**KPI 卡說明 Tooltip** — 樂群 & 大直工務 Dashboard 各 KPI 卡標題加 `?` 說明圖示；說明文字獨立維護於 `constants/kpiDesc/` 目錄，各模組一個檔案
- v1.39.5：**工項類別分析 + 主管 Dashboard — 納入 IHG 客房保養工時** — `work_category_analysis.py` 新增第 4 來源 `ihg_room`（IHGRoomMaintenanceMaster），工時取 `raw_json["工時計算"]`÷60，類別=「例行維護」；ExecDashboard + WorkCategoryAnalysis 自動納入，零前端改動
- v1.39.4：**IHG 客房保養 — 季度視角（`?view=quarter`）** — 前端 useMemo 聚合季度統計、QuarterCellComp（88×66格）、月份/季度切換 Segmented、季度彙整 Drawer（含各月「查看」穿透明細）；FEATURE_MAP / DEV_LOG / CHANGELOG 同步更新
- v1.39.3：**前端安全補強 + 商場巡檢顯示修正** — `securityPatrol.ts`/`mallFacilityInspection.ts` 改用 `apiClient`（JWT interceptor）；DEV bypass 改呼叫真實登入；商場巡檢無資料時顯示「尚無資料」而非進度條 0%
- v1.39.2：**全域 API 身份驗證補強（安全性）** — 19 個業務 router 補 `get_current_user`；30 個 sync/debug endpoint 補 `require_roles(system_admin, module_manager)`；未登入無法存取任何業務資料，非授權角色無法觸發 Ragic 同步
- v1.39.0：**IHG 客房保養模組（新功能）** — 年度保養矩陣表（房號×月份）；KPI 統計卡（全年/已完成/未完成/逾期/完成率）；Ragic Sheet 4 同步（Master+Detail）；同步按鈕；狀態顏色（已完成/逾期/本月應保養/未完成）；點擊格子 Modal 明細；篩選（年度/樓層/狀態）；Menu：飯店管理→2.IHG客房保養
- v1.38.7：**樂群完工判定修正** — `is_completed_flag` 改為「有完工時間即算完工」，灰色地帶（處理中/待辦驗有完工時間）正確歸入已完成；2026/04驗算：已完成 20→38筆，未完成 17→9筆
- v1.38.6：**統一 Ragic 資料存取層 + 花費工時 48624hr 修正 + 圖片整合** — `ragic_data_service.py`（merge+cache）；`safe_work_days_to_hours` 上限 365 天；Drawer 新增 📷 圖片連結
- v1.38.5：**大直/樂群 Ragic 欄位優先順序修正** — 大直 `completed_at` 改優先讀「完工時間」；樂群 `occurred_at` 改優先讀「報修日期」；`/work-category-analysis` 自動生效
- v1.38.0：**◆ 董事長簡報 Dashboard 新功能** — 黑金三層駕駛艙設計（Hero KPI 超大數字 / 2×3 圖表卡片 / 可收合表格）；自動決策提示；五維篩選；route `/exec-dashboard`；既有 `★工項類別分析` 完全保留
- v1.37.0：**★工項類別分析 升級主管決策 Dashboard** — 三來源整合（樂群+大直+房務保養）；KPI卡片層（總工時/環比/集中度警示）+圖表分析層（趨勢/圓餅/人員排名/交叉矩陣/來源分析）+五維篩選；單一路由共用設計
- v1.36.0：**★工項類別分析 新功能** — 整合樂群+大直資料，5 大工項類別（現場報修/上級交辦/緊急事件/例行維護/每日巡檢）× 曲線圖/每日累計表/每月累計表/人員%表；後端新 Router + 前端新頁面；掛載於樂群/大直子選單
- v1.35.5：**大直/樂群 Dashboard 未完成案件 Top 10 修正** — 篩選改用 `completed_at is None`（有完工日期就排除），`pending_days` 同步修正；原用狀態欄位判斷可能誤列已完工案件
- v1.35.4：**樂群 Dashboard 當月金額與金額統計 Tab 數字不一致修復** — 月份費用改用 `filter_cases(year, month)`，結案以結案月份為準，口徑統一
- v1.35.3：**大直/樂群 Dashboard 新增「當月金額」欄** — 保留原有年度費用卡片，新增第 4 欄同框顯示委外+維修／扣款費用／扣款專櫃／當月小計（依年+月篩選）
- v1.35.2：**大直/樂群所有費用彈跳視窗寬度調整** — 委外+維修明細 900px、扣款明細 760px、月份明細 800px；移除所有多餘的橫向 scroll 設定
- v1.35.1：**大直工務部 TypeScript 編譯錯誤修復** — `dazhiRepair.ts` 截斷修復（補全 7 個型別匯出）；`FeeStatsTab` 雙重型別轉型（`as unknown as Record<string,number>`）；`tsc --noEmit` 零錯誤確認
- v1.35.0：**大直/樂群「取消」案件污染統計根本修復** — 新增 `EXCLUDED_STATUSES`；從 `COMPLETED_STATUSES` 移除「取消」；所有統計 compute 函式開頭過濾排除案件；明細總表保留完整記錄
- v1.34.9：**大直工務部新增「金額統計」Tab** — 與樂群工務報修介面完全一致（費用×月份交叉表 + 點擊明細）；後端/API/型別/元件全套新增；Ragic 補欄位後數字自動顯示
- v1.34.8：**大直/樂群 4.1 報修統計 — 新增 ⑥ 本月未完成數**（= ④ − ⑤），原 ⑥ 完成率改為 ⑦；後端/型別/前端同步更新
- v1.34.7：**樂群工務報修 Dashboard 與 Tab 4.1 數字不一致修復** — `compute_dashboard()` 改以 `occ_year/occ_month`（報修月份）篩選，口徑與 Tab 4.1 一致；同步修正 4.4 客房報修矩陣改存 `case.to_dict()` 完整欄位（與 v1.34.3 大直同款 bug）
- v1.34.6：**客房保養明細 CORS 根本修復** — `main.py` 加 `redirect_slashes=False`（防止 307 繞過 Vite proxy）；`.env` `CORS_ORIGINS` 補入 `127.0.0.1:5173/4173`
- v1.34.5：**SQLite+OneDrive 鎖定衝突修復** — `database.py` 加 `timeout=30`/`pool_pre_ping`；啟動時執行 WAL+busy_timeout PRAGMA；Vite proxy 改 `127.0.0.1`；新增「重新載入」按鈕；catch block 加 `console.error`
- v1.34.4：**客房保養明細「載入失敗」根本修復** — 移除 `main.py` 啟動時的 `await _auto_sync()`；伺服器啟動後直接從本地 DB 回傳資料，手動或排程才同步 Ragic
- v1.34.3：**大直工務部 4.4 Drawer 資料空白根本修復** — 後端矩陣格子改存完整 `case.to_dict()`；前端 `RoomCategoryEntry` 升為 `RepairCase` 型別；多筆案件格子改為逐筆可點擊
- v1.34.2：**大直工務部資料空白根本修正** — Ragic sheet 路徑從 `/4` 改為 `/8`（PAGEID=fV8 不變）；`vite.config.ts` 補上 `preview.proxy`，修正 port 4173 的 API 請求無法到達後端的問題
- v1.34.1：**大直工務部狀態修正** — 後端 `COMPLETED_STATUSES` 補入「已辦驗」/「取消」（修正 500 筆案件被誤算為未完成）；前端補入 9 個缺漏狀態的顏色映射（已辦驗/待修中/待料中/取消/委外處理/待辦驗/辦驗未通過/進行中/待確認）
- v1.34.0：**Dashboard 主管視角優化（P1）** — 預算管理摘要卡置於首頁最上方（執行率/超支/資料品質/一句話結論）；今日重點摘要區塊（動態聚合全域風險 3-5 條）；全域待關注加入工務+預算子項；各群組卡補一句話結論（飯店/商場/保全/工務）；Login 頁正式感優化（Logo 圓塊、副標、環境標示、loading 狀態、dev 登入僅 DEV 環境顯示）
- v1.33.9：**台灣時區統一** — 新增 `app/core/time.py`（`twnow()` helper）；34 個服務/模型/路由全面替換 `datetime.now(timezone.utc)` → `twnow()`；前端 `fmtTime()` 改為 regex 解析字串（不經 Date UTC 轉換）；`TECH_SPEC.md` 新增時區政策規格
- v1.33.8：**同步排程整點對齊修正** — `scheduler.py` 新增 `make_cron_trigger()`，所有模組排程改用 `CronTrigger`（15min → :00/:15/:30/:45，30min → :00/:30，60min → 整點）；同步紀錄頁新增「立即同步」按鈕（`POST /sync-logs/trigger`）；載入失敗顯示 warning 訊息
- v1.33.7：**商場工務每日巡檢本地 DB 化** — 5 張樓層 Sheet（4F/3F/1F~3F/1F/B1F~B4F）從直連 Ragic 改為全量同步至 `mall_fi_inspection_batch` / `mall_fi_inspection_item`；動態欄位偵測 Pivot；新增 stats/batches/sync/dashboard.summary 端點；前端 `InspectionFloorPage.tsx` / `index.tsx` 所有 TODO stub 接上真實 API；`RagicAppDirectory` 本地表欄位更新
- v1.33.6：**Ragic 對應表** — 新增「系統設定 → Ragic 對應表」頁（`/settings/ragic-app-directory`）；嵌入 219 筆靜態 Ragic 應用程式資料；前兩欄「Portal 名稱」/「Portal 超連結」可行內編輯並持久化（後端新增 `ragic_app_portal_annotations` 資料表 + PUT/GET endpoint）；已標註的列以藍底高亮；支援名稱/模組/Portal 搜尋及類型篩選
- v1.33.5：**同步紀錄 UI** — `ModuleSyncLog` ORM 表記錄每次排程/手動同步結果；`_auto_sync()` 重構為 `_run_and_log()` 統一寫入；新增 `GET /ragic/sync-logs/recent`；`RagicConnections.tsx` 底部新增 24 小時同步紀錄 Table（狀態篩選 + 錯誤 Tooltip + 重新整理按鈕）
- v1.33.4：**預算管理補強** — 主檔停用/啟用 UI（部門/科目/項目 Popconfirm 按鈕）；交易明細 Excel 匯出（`GET /transactions/export`）；預算主表作廢/刪除（`DELETE /plans/{id}`，draft→硬刪，其他→void）
- v1.33.3：**Phase 2 Scheduler 橋接 + RagicConnections UI** — 修復 `sync_service.py` 多個 bug；新增 `core/scheduler.py` 單例；每個 RagicConnection 依 `sync_interval` 獨立排程；router 加入 DELETE / PATCH active / GET scheduler/status；前端 `RagicConnections.tsx` 完整實作（CRUD + 日誌 Drawer）
- v1.33.2：**Phase 3 大直/樂群工務報修本地 DB 化** — 新增 `DazhiRepairCase` / `LuqunRepairCase` ORM 模型 + 同步服務；兩個 router 所有資料端點改讀本地 SQLite；各新增 `POST /sync` 背景同步端點；`_auto_sync()` 排程加入兩模組
- v1.33.1：**Phase 1 同步背景化** — 10 個模組 `POST /sync` endpoint 全部改為 BackgroundTasks；手動同步不再阻塞畫面；`room_maintenance` create/update 後觸發的 sync 亦改為背景執行
- v1.33.0：**預算管理模組 Phase 1** — 完整掛入 Portal；Dashboard / 預算主表 / 明細編列 / 交易明細 / 四大主檔維護 / 預算比較報表 / 資料品質；24 個後端 API + 10 個前端頁面；使用獨立 SQLite `budget_system_v1.sqlite`（2026 年度 579 筆交易）
- v1.32.2：**首頁 Dashboard — 工務報修主管摘要** — 新增 ROW 1.5（樂群 + 大直）；6 KPI 數字、結案率進度條、最高報修類型、逾期警示，不影響既有版面
- v1.32.1：**樂群工務報修 — 統計月份歸屬修正** — 結案案件改以 completed_at 月份為統計歸屬；新增 occ_year/occ_month 保持 4.1 報修統計正確；規格書加入 §3.5 說明及案例 202604-032
- v1.30.0：**樂群工務報修模組** — 完整新模組，資料來源 Ragic 春大直報修清單總表（ap12 / soutlet001 / sheet 6）；6 個 Tab（Dashboard / 4.1 報修 / 4.2 結案時間 / 4.3 報修類型 / 4.4 客房報修表 / 明細總表）；後端共用 service 統一清洗 + 統計 + 匯出 Excel；左側 Menu 置於「商場管理」之後
- v1.29.0：**Dashboard 趨勢折線圖 + 結案率追蹤** — 後端新增 `/dashboard/trend`（三模組近 N 日完成率）與 `/dashboard/closure-stats`（異常→已處理→已結案漏斗）；前端 Dashboard ROW 4 recharts 折線圖（7D/30D 切換）+ ROW 5 四欄結案率卡片
- v1.28.1：**GraphView 新增春大直商場工務巡檢、整棟巡檢節點** — 後端 `/graph` 補上 2 個 Ragic 直連巡檢節點（`mall_facility`/`full_building`）+ 2 條 anomaly 邊；前端 `NODE_POSITIONS` 補座標、容器高 540→720px；節點 11→13、邊 8→10
- v1.28.0：**整棟巡檢** — 新模組正式納入 portal；模組 Dashboard + 4 個樓層頁（RF/B4F/B2F/B1F）；SecurityDashboard 風格 Tabs 儀表板 + B1FInspection 風格樓層頁；左側 Menu 新增群組（春大直商場工務巡檢↔保全管理之間）；主 Dashboard 新增快速入口群組卡片
- v1.27.0：**春大直商場工務巡檢** — 新模組正式納入 portal；模組 Dashboard + 5 個樓層頁（4F/3F/1F~3F/1F/B1F~B4F）；Ragic 表單快速入口 + iframe 內嵌；主 Dashboard ROW 2.5 樓層快速點擊標籤；左側 Menu 新增群組（商場管理↔保全管理之間）
- v1.26.0：**GraphView 升級為操作流程圖** — 從 hub-spoke 改為「巡檢→保養→簽核→公告」流程鏈；改用 `@xyflow/react` v12（react-flow）；11 節點 + 8 語意化關係邊（含 DB 直接關聯 Approval→Memo）；三群組分區 + 邊類型視覺差異化（紅虛線/橙虛線/紫實線動畫）
- v1.25.0：**Dashboard 關聯圖譜（GraphView）** — Hub-Spoke SVG 視覺化呈現各模組異常/待辦；後端新增 `GET /api/v1/dashboard/graph`（聚合 6 模組計數）；前端純 SVG 組件（無外部套件）；Dashboard ROW 4 嵌入；節點點擊跳轉對應模組；60 秒自動刷新
- v1.24.0：**超級行事曆（Command Calendar）** — Portal 跨模組事件總覽中心；整合六大事件來源（飯店保養/商場保養/保全巡檢/工務巡檢/簽核/公告）；月/週/日/清單四種 FullCalendar 視圖；今日 KPI 摘要 + 今日重點面板 + 事件詳情抽屜 + 深連結跳轉；自訂事件 CRUD（`calendar_custom_events` 表）；左側 Menu 新增「行事曆」群組
- v1.23.0：Portal 首頁 Dashboard 全面重組 — 升級為集團三群組（飯店/商場/保全）管理總覽；4 KPI 卡（商場巡檢/保全巡檢/客房保養/全域待關注）+ 三群組摘要卡（各含 Progress + 快速入口）+ 系統資訊；零後端改動，`Promise.allSettled` 平行呼叫 3 支現有 API
- v1.22.2：保全巡檢「異常說明%」欄位改為備註模式 — is_note 欄位 + 啟動遷移回填；統計/Dashboard 全面排除備註項；Detail 頁備註欄位以藍色另行呈現，不計入評分
- v1.22.1：修正保全巡檢「拍照%」欄位誤計為異常 — `_extract_check_items` 新增拍照欄過濾；啟動遷移自動清除 271 筆歷史拍照記錄；統計/Dashboard 即時正確
- v1.22.0：新增「保全巡檢」功能 — 7 張 Ragic Sheet 統一模型架構（security-patrol/1~9）；後端 SecurityPatrolBatch/Item 模型 + 動態欄位 Pivot 同步服務 + security/patrol 與 security/dashboard API；前端新增「保全管理」Sidebar 群組（Dashboard + 7 子頁）；路由 `/security/dashboard`、`/security/patrol/:sheetKey`
- v1.21.0：新增「商場管理統計 Dashboard」— 整合 B1F/B2F/RF 巡檢 + 商場週期保養 8 KPI 卡 + 樓層比較圖 + 狀態圓餅 + 趨勢折線 + 重點追蹤清單；商場管理選單新增 `/mall/dashboard` 路由（置於最前）
- v1.20.0：新增「整棟工務每日巡檢 B1F」— Ragic Sheet 4 同步（動態欄位偵測 Pivot）+ 儀表板 + 批次明細 + 30日歷史 Drawer；商場管理選單新增 `/mall/b1f-inspection` 路由
- v1.19.0：新增「整棟工務每日巡檢 B2F」— Ragic Sheet 3 同步（動態欄位偵測 Pivot）+ 儀表板 + 批次明細 + 30日歷史 Drawer；商場管理選單新增 `/mall/b2f-inspection` 路由
- v1.18.0：新增「整棟工務每日巡檢 RF」— Ragic Sheet 1 同步（**動態欄位偵測**，自動 pivot 所有設備欄）+ 儀表板（7日趨勢 + 狀態圓餅 + 異常/待處理清單）+ 批次明細 + 30日歷史 Drawer；商場管理選單新增 `/mall/rf-inspection` 路由
- v1.17.0：新增「整棟工務每日巡檢 B4F」— Ragic Sheet 2 同步（normal/abnormal/pending/unchecked 狀態模型）+ 儀表板（7日趨勢折線 + 區域長條 + 狀態圓餅）+ 批次清單 + 巡檢明細 + 30日歷史 Drawer；商場管理選單新增 `/mall/b4f-inspection` 路由
- v1.16.0：新增「1.2 商場週期保養表」— 仿照飯店 PM 全功能（Ragic Sheet 18 同步 + 主管儀表板 + 批次清單 + 工單明細 + 歷史 Drawer）；新增「商場管理」選單群組，路由 `/mall/periodic-maintenance`
- v1.15.0：富文字編輯器（react-quill-new）全面升級 — 新增簽核單/公告均支援「圖文並茂」；公告新增附件上傳/下載機制（MemoFile 表 + `/upload` API + `/memos/{id}/files` API）
- v1.14.6：儀表板三處統計（KPI 已完成、完成率、狀態分布圓餅）全部統一定義為「保養時間啟+迄均有值=完成」，含非本月項目；完成率改為 completed/total
- v1.14.5：修正「已完成」統計錯誤 — `_calc_status` 改為「保養時間啟+迄均有值」才算完成，與「完成」欄 `is_completed` 定義一致；DB 回填舊資料；KPI/圖表/完成率同步正確
- v1.14.4：週期保養表改為**純唯讀視圖** — 移除 Portal 編輯功能；狀態由 Ragic 欄位（保養時間啟/迄/排定日期/執行月份）直接推導；同步服務移除 portal_edited_at 保護，每次全量以 Ragic 為準
- v1.14.3：週期保養表 `is_completed` 完成標記 — 同步時自動由「保養時間啟+迄」計算，Portal 可手動覆寫；表格新增完成圖示欄；DB 輕量移轉（ALTER TABLE 補丁）
- v1.14.2：週期保養表明細強化 — ①多重狀態複選篩選（含非本月、有排定日期 cross-filter）②保養項目點擊 → 近 12 個月執行歷史 Drawer（月曆格 + KPI + 明細）③修正 sync `_subtable_*` key 解析問題（根本修正）
- v1.14.1：修正週期保養表 sync — Sheet 8 子表格解析（數字 key 子列）、ragic_id 改為 `{batch_id}_{row_key}` 格式、備註欄映射、舊記錄清除
- v1.14.0：週期保養表全功能上線（Phase 1+2+3）— 後端 Ragic ap12 同步 + portal_edited_at 保護、主管儀表板、批次清單、工單式明細 + Drawer 回填
- v1.13.0：保養統計 Tab（Phase 1+2+3）— 完成率趨勢雙軸圖、異常項目排行、樓層分析、月份對比、高風險房間三分類；同步產出設計規格書
- v1.12.0：導覽文字 SSOT（navLabels.ts）；人員工時表統計月份選擇器
- v1.9：人員工時表 — 主管總覽 KPI + 趨勢/排名雙圖 + 異常分析 + 搜尋/排序/匯出/個人 Drawer
- v1.8：客房保養明細 — 新增 Tab「人員工時表」（近 12 月 pivot，分鐘→小時，月合計列）
- v1.7：客房保養明細 — 歷史 Drawer 月曆格可點擊，展開該月保養人員/工時/12 項 X‑V 明細
- v1.6：客房保養明細 — 房間保養歷史追蹤 Drawer（月曆摘要 × 連續未保養月數 × 記錄時間軸），房號可點擊
- v1.5：客房保養明細強化 — Room 主檔（5F–10F 共 170 間）、日期區間聚合、工時合計、未保養灰底、KPI 可點擊篩選
- v1.4：新增客房保養明細模組（ap12.ragic.com/soutlet001/report2/2）— 明細列表 + 總表（12 項 X/V 聚合）
- v1.3：Dashboard 正式上線 — KPI 卡片、工作狀態圓餅圖、庫存類別長條圖、重點房間 & 同步紀錄表
- v1.2：新增倉庫庫存模組（Ragic `ragicinventory/20008` → SQLite 同步）、KPI 卡 + 篩選表格頁面
- v1.1：客房保養同步架構（Ragic → SQLite）、圖表儀表板、未檢查項目附表
- 詳見 [CHANGELOG](docs/CHANGELOG.md)

## 架構

```
portal/
├── backend/    # FastAPI + SQLAlchemy + Casbin
└── frontend/   # React 18 + TypeScript + Ant Design 5
```

## 快速啟動（開發模式）

### 1. 後端

```bash
cd backend

# 安裝依賴
pip install -r requirements.txt

# 初始化資料庫 + 種子資料
python init_db.py

# 啟動開發伺服器
uvicorn app.main:app --reload --port 8000
```

API 文件：http://localhost:8000/docs

### 2. 前端

```bash
cd frontend

# 安裝依賴
npm install

# 啟動開發伺服器
npm run dev
```

入口：http://localhost:5173

---

## 初始帳號

| 帳號 | 密碼 | 角色 |
|------|------|------|
| `admin` 或 `admin@portal.local` | `Admin@2026` | 系統管理員 |
| `samuel.huang` 或 `samuel.huang@portal.local` | `Samuel@2026` | 系統管理員 |

> 帳號不區分大小寫，資料庫統一存小寫

---

## 環境變數

後端 `.env` 重要設定：

```bash
DATABASE_URL=sqlite+aiosqlite:///./portal.db    # 開發用 SQLite
JWT_SECRET_KEY=your-long-secret-key             # 務必更換
ENCRYPTION_KEY=                                 # Fernet key（留空自動生成）
```

---

## Docker 部署

```bash
# 全套啟動（PostgreSQL + 後端 + 前端）
docker-compose up -d

# 初始化資料庫
docker-compose exec backend python init_db.py
```

---

## 技術規格

| 層 | 技術 |
|----|------|
| 前端 | React 18 · TypeScript · Ant Design 5 · Zustand |
| 後端 | FastAPI · SQLAlchemy 2.0 · Pydantic v2 |
| 資料庫 | SQLite（開發）/ PostgreSQL（正式）|
| 認證 | JWT · bcrypt |
| 同步 | httpx · APScheduler |
| 報表 | pandas · openpyxl |

---

## Phase 1 功能清單

- [x] 多據點管理（HQ / 飯店A/B / 商場A/B）
- [x] JWT 身份驗證（登入 / 登出 / me）
- [x] RBAC 角色權限（system_admin / tenant_admin / module_manager / viewer）
- [x] 人員管理 CRUD（新增 / 編輯 / 停用 / 刪除）
- [x] Ragic API Adapter（分頁拉取 / 加密金鑰）
- [x] 同步排程（APScheduler）
- [x] 資料快照（DataSnapshot）
- [x] 稽核日誌（AuditLog）
- [x] Dashboard 概覽
- [ ] 跨據點報表（Phase 2）
- [ ] AI 分析模組（Phase 2）
