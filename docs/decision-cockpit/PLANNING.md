# 決策駕駛艙（Decision Cockpit）— 完整規劃文件

> 版本：v1.0 | 建立日期：2026-05-03 | 狀態：Phase 1 開發中

---

## 一、模組定位

| 項目 | 內容 |
|------|------|
| 中文名稱 | 決策駕駛艙 |
| 英文名稱 | Decision Cockpit |
| 路由 | `/decision-cockpit` |
| Menu 位置 | 第一層主選單（/dashboard 之後） |
| Menu 顯示名稱 | 決策駕駛艙 |
| active_key | `/decision-cockpit` |
| permission_key | `decision_cockpit_view` |
| 定位 | 高階主管一打開就能掌握集團整體狀況、異常告警、工時分析的決策入口 |

**⚠️ 重要聲明：**
- 本模組**不修改**既有 dashboard / exec-dashboard / hotel/overview / mall/overview
- 完全沿用現有後端 API，不新增後端端點
- 資料未接入者一律顯示「資料準備中」，不使用假資料
- 不使用 AI API，所有摘要均為規則式計算

---

## 二、TAB 架構

```
決策駕駛艙 /decision-cockpit
│
├── 頁頭操作列
│   ├── 查詢月份選擇器（YearMonth Picker）
│   ├── 重新整理按鈕
│   └── 匯出按鈕（PPTX / Excel）
│
├── TAB A：決策總覽         ← 預設開啟
├── TAB B：飯店管理摘要
├── TAB C：商場管理摘要
├── TAB D：工務與報修摘要
├── TAB E：人員工時與效率
├── TAB F：異常與風險雷達
├── TAB G：趨勢分析
├── TAB H：主管晨會摘要
└── TAB I：資料品質監控
```

### TAB A 內部佈局（三區）

```
第一區（4 格 KPI Row）
  └─ 集團健康分數 | 飯店健康分數 | 商場健康分數 | 工務維護健康分數

第二區（6 格 KPI Row）
  └─ 本月總案件 | 完成件數 | 未完成件數 | 待驗件數 | 總工時(HR) | 高風險數

第三區（2 欄）
  左：主管最該注意的 5 件事（規則式條列）
  右：各模組燈號摘要（紅/黃/綠/灰）
```

---

## 三、權限規劃

| 權限 Key | 說明 | 建議角色 |
|---------|------|---------|
| `decision_cockpit_view` | 查看決策駕駛艙 | system_admin、高階主管、部門主管 |
| `decision_cockpit_export` | 匯出 PPTX / Excel | system_admin、高階主管 |
| `decision_cockpit_admin` | 保留（未來公式調整用） | system_admin |

---

## 四、需修改的既有檔案

| 檔案 | 修改內容 |
|------|---------|
| `frontend/src/constants/navLabels.ts` | 新增 `NAV_PAGE.decisionCockpit = '決策駕駛艙'` |
| `frontend/src/components/Layout/MainLayout.tsx` | 新增第一層 menu item（`/decision-cockpit`） |
| `frontend/src/router/index.tsx` | 新增 Route + import |
| `docs/CHANGELOG.md` | 新增版本記錄 |
| `docs/TECH_SPEC.md` | 新增模組說明 |
| `README.md` | 更新最後更新日期 |

---

## 五、需新增的檔案

```
frontend/src/pages/DecisionCockpit/
├── index.tsx                    # 主頁：頁頭操作列 + 月份選擇器 + TAB 框架
├── tabs/
│   ├── TabOverview.tsx          # A. 決策總覽
│   ├── TabHotel.tsx             # B. 飯店管理摘要（Phase 3）
│   ├── TabMall.tsx              # C. 商場管理摘要（Phase 3）
│   ├── TabRepair.tsx            # D. 工務與報修摘要（Phase 4）
│   ├── TabPersonnel.tsx         # E. 人員工時與效率（Phase 4）
│   ├── TabRiskRadar.tsx         # F. 異常與風險雷達（Phase 5）
│   ├── TabTrend.tsx             # G. 趨勢分析（Phase 5）
│   ├── TabBriefing.tsx          # H. 主管晨會摘要（Phase 6）
│   └── TabDataQuality.tsx       # I. 資料品質監控（Phase 6）
├── components/
│   ├── HealthScoreCard.tsx      # 健康分數卡片（Phase 2）
│   ├── RiskRadarList.tsx        # 風險雷達清單（Phase 5）
│   ├── Top5PersonTable.tsx      # 人員工時 Top 5（Phase 4）
│   └── BriefingTextBlock.tsx    # 晨會摘要文字區塊（Phase 6）
└── utils/
    ├── healthScore.ts           # 健康分數計算邏輯（Phase 2）
    ├── riskDetector.ts          # 風險燈號判斷（Phase 5）
    ├── briefingTemplate.ts      # 晨會摘要規則式模板（Phase 6）
    └── dataQuality.ts           # 資料品質計算（Phase 6）

docs/decision-cockpit/
├── PLANNING.md                  # 本文件
├── KPI_DATASOURCE_MAP.md        # KPI 資料來源對照表
└── HEALTH_SCORE_SPEC.md         # 健康分數公式規格（待業主確認）
```

---

## 六、沿用的後端 API（完整清單，零修改）

```
GET  /api/v1/dashboard/kpi
GET  /api/v1/dashboard/graph
GET  /api/v1/dashboard/trend?days=N
GET  /api/v1/dashboard/closure-stats
GET  /api/v1/hotel/daily-hours?year=&month=
GET  /api/v1/hotel/monthly-hours?year=
GET  /api/v1/hotel/person-hours?year=
POST /api/v1/hotel/overview/export/pptx
GET  /api/v1/mall/daily-hours?year=&month=
GET  /api/v1/mall/monthly-hours?year=
GET  /api/v1/mall/person-hours?year=
POST /api/v1/mall/overview/export/pptx
GET  /api/v1/dazhi-repair/dashboard?year=&month=
GET  /api/v1/luqun-repair/dashboard?year=&month=
GET  /api/v1/periodic-maintenance/stats?year=&month=
GET  /api/v1/mall-periodic-maintenance/stats?year=&month=
GET  /api/v1/full-building-maintenance/stats?year=&month=
GET  /api/v1/room-maintenance-detail/maintenance-stats
GET  /api/v1/ihg-room-maintenance/stats?year=&month=
GET  /api/v1/hotel-daily-inspection/dashboard/summary
GET  /api/v1/security/dashboard/summary
GET  /api/v1/mall-facility-inspection/dashboard/summary
```

---

## 七、三大確認點（Coding 前已採用預設值）

| # | 確認項目 | 採用預設值 | 說明 |
|---|---------|-----------|------|
| C1 | 健康分數公式 | 完成率×40% + 逾期控制×25% + 異常管理×20% + 資料完整度×15% | 見 HEALTH_SCORE_SPEC.md；以 configurable constants 實作，業主確認後可調整 |
| C2 | 人員工時月份口徑 | 接受年度口徑 | person-hours API 無月份過濾；UI 顯示「※ 人員工時為全年統計」說明 |
| C3 | 主管最該注意的 5 件事規則 | 優先順序：紅燈模組 → 逾期超量 → 完成率過低 → 工時集中 → 資料缺漏 | 以 `riskDetector.ts` 實作，規則清楚標注可調整 |

---

## 八、開發 Phase 計劃

| Phase | 內容 | 預估工時 | 狀態 |
|-------|------|---------|------|
| Phase 1 | 基礎框架：navLabels + Menu + Router + 空白頁框架 | 2~3 hr | ✅ 進行中 |
| Phase 2 | TAB A 決策總覽：健康分數 + KPI 卡 + 主管 5 件事 | 4~6 hr | 🔜 待辦 |
| Phase 3 | TAB B 飯店摘要 + TAB C 商場摘要 | 3~4 hr | 🔜 待辦 |
| Phase 4 | TAB D 工務報修 + TAB E 人員工時 | 2~3 hr | 🔜 待辦 |
| Phase 5 | TAB F 風險雷達 + TAB G 趨勢分析 | 3~4 hr | 🔜 待辦 |
| Phase 6 | TAB H 晨會摘要 + TAB I 資料品質監控 | 2~3 hr | 🔜 待辦 |
| Phase 7 | 匯出功能（PPTX + Excel） | 2~3 hr | 🔜 待辦 |
| Phase 8 | 測試驗證 + 文件更新 | 1~2 hr | 🔜 待辦 |

---

## 九、關聯文件

- [KPI 資料來源對照表](./KPI_DATASOURCE_MAP.md)
- [健康分數公式規格](./HEALTH_SCORE_SPEC.md)
- [受保護元素規格](../PROTECTED.md)
- [CHANGELOG](../CHANGELOG.md)
- [TECH_SPEC](../TECH_SPEC.md)
