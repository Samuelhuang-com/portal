# 集團 Portal 系統

> 跨據點統一管理平台 — FastAPI + React + TypeScript

**最後更新：2026-04-24（v1.39.0）**

## 最近變更
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
