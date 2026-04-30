# 每日數值登錄表模組 — 開發規劃書

**建立日期：** 2026-04-30  
**負責人：** Samuel  
**狀態：** 🟡 開發中  
**路由前綴：** `/hotel/daily-meter-readings`  
**API 前綴：** `/api/v1/hotel-meter-readings`

---

## 一、模組目標

新增「每日數值登錄表」模組，整合以下 4 張 Ragic 表單，提供 Dashboard 與各表單資料檢視功能。

| Tab | 名稱 | Ragic Sheet |
|-----|------|------------|
| 1 | Dashboard（總覽） | — 跨 4 Sheet 整合統計 — |
| 2 | 全棟電錶 | `hotel-routine-inspection/11` |
| 3 | 商場空調箱電錶 | `hotel-routine-inspection/12` |
| 4 | 專櫃電錶 | `hotel-routine-inspection/14` |
| 5 | 專櫃水錶 | `hotel-routine-inspection/15` |

> 注意：Sheet 13 不存在（跳號），直接從 12 跳到 14。

---

## 二、參考模組

**完全跟隨：** `hotel/daily-inspection`

| 參考面向 | 說明 |
|---------|------|
| Router 寫法 | `APIRouter(dependencies=[Depends(get_current_user)])` |
| Service 寫法 | `RagicAdapter` + 動態欄位偵測 + upsert |
| Model 設計 | Batch（場次）+ Reading（讀數 Pivot）雙表架構 |
| Frontend Tab 切換 | `useSearchParams` + `openedTabs` Set 懶載入 |
| Dashboard 統計 | 跨 Sheet `/dashboard/summary` 端點 |
| 錯誤處理 | API catch → 空陣列 + Alert 提示 |
| Menu 設定 | `MainLayout.tsx` `hotel` 群組 + `navLabels.ts` |

---

## 三、新增檔案清單

### Backend（3 個新檔）

```
backend/app/models/hotel_meter_readings.py
  └─ HotelMRBatch    # hotel_mr_batch 資料表：一筆 = 一次登錄（一個 Ragic Row）
  └─ HotelMRReading  # hotel_mr_reading 資料表：一筆 = 一個儀表讀數（動態 Pivot）

backend/app/services/hotel_meter_readings_sync.py
  └─ sync_sheet(sheet_key)  # 同步單張 Sheet
  └─ sync_all()             # 同步全部 4 張
  └─ _extract_meter_fields  # 動態欄位偵測（排除 metadata 欄位）

backend/app/routers/hotel_meter_readings.py
  └─ GET  /sheets                     # 4 張 Sheet 設定
  └─ POST /{sheet_key}/sync           # 背景同步單張
  └─ POST /sync/all                   # 背景同步全部
  └─ GET  /{sheet_key}/batches        # 月份篩選資料列表
  └─ GET  /dashboard/summary          # 跨 Sheet Dashboard 統計
```

### Frontend（3 個新檔）

```
frontend/src/constants/hotelMeterReadings.ts
  └─ HOTEL_METER_READINGS_SHEETS      # 4 張 Sheet 靜態設定
  └─ HOTEL_METER_READINGS_SHEET_LIST  # 陣列版本

frontend/src/api/hotelMeterReadings.ts
  └─ fetchHotelMeterDashboardSummary  # /dashboard/summary
  └─ fetchHotelMeterBatches           # /{sheet_key}/batches
  └─ syncHotelMeterFromRagic          # POST /{sheet_key}/sync
  └─ syncHotelMeterAllFromRagic       # POST /sync/all

frontend/src/pages/HotelMeterReadings/index.tsx
  └─ Tab 1: DashboardTab              # 跨 Sheet 統計（今日登錄、缺漏、趨勢）
  └─ Tab 2-5: MeterListTab            # 各 Sheet 月份篩選清單（共用元件）
```

---

## 四、修改檔案清單

### Backend（2 個修改）

| 檔案 | 修改內容 |
|------|---------|
| `backend/app/main.py` | import `hotel_meter_readings`；`app.include_router(...)` 加入 tags=["每日數值登錄表"] |
| `backend/app/routers/role_permissions.py` | 在「飯店管理」群組加入 `hotel_meter_readings_view` |

### Frontend（3 個修改）

| 檔案 | 修改內容 |
|------|---------|
| `frontend/src/constants/navLabels.ts` | 加入 `hotelMeterReadings: '每日數值登錄表'`；更新維護紀錄 |
| `frontend/src/components/Layout/MainLayout.tsx` | hotel 群組 children 加入 menu item |
| `frontend/src/router/index.tsx` | import HotelMeterReadings；加入 `<Route path="daily-meter-readings" ...>` |

### 文件（2 個修改）

| 檔案 | 修改內容 |
|------|---------|
| `docs/CHANGELOG.md` | 加入本次模組新增紀錄 |
| `README.md` | 更新「最後更新」日期與「最近變更」區塊 |

---

## 五、DB 資料表設計

### `hotel_mr_batch`（登錄場次主表）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `ragic_id` | String(80) PK | `{sheet_key}_{ragic_row_id}` 複合主鍵 |
| `sheet_key` | String(40) | `building-electric` / `mall-ac-electric` / `tenant-electric` / `tenant-water` |
| `sheet_name` | String(100) | 中文名稱（全棟電錶 etc.） |
| `record_date` | String(20) | 登錄日期 YYYY/MM/DD |
| `recorder_name` | String(100) | 登錄人員（動態偵測欄位） |
| `synced_at` | DateTime | 最後同步時間 |

### `hotel_mr_reading`（儀表讀數明細，Pivot 展開）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `ragic_id` | String(120) PK | `{batch_ragic_id}_{seq_no}` |
| `batch_ragic_id` | String(80) | 所屬 batch |
| `sheet_key` | String(40) | 冗餘欄位，方便跨表查詢 |
| `seq_no` | Integer | 欄位順序 |
| `meter_name` | String(200) | 儀表名稱（Ragic 欄位名） |
| `reading_value` | String(100) | 原始讀數值（保留 String 彈性） |
| `synced_at` | DateTime | 同步時間 |

---

## 六、Ragic Sheet 對應設定

### Backend SHEET_CONFIGS

```python
# backend/app/services/hotel_meter_readings_sync.py
SHEET_CONFIGS: dict[str, dict] = {
    "building-electric": {
        "path": "hotel-routine-inspection/11",
        "name": "全棟電錶",
    },
    "mall-ac-electric": {
        "path": "hotel-routine-inspection/12",
        "name": "商場空調箱電錶",
    },
    "tenant-electric": {
        "path": "hotel-routine-inspection/14",
        "name": "專櫃電錶",
    },
    "tenant-water": {
        "path": "hotel-routine-inspection/15",
        "name": "專櫃水錶",
    },
}
```

> 注意：Ragic App 為 `hotel-routine-inspection`（與 daily-inspection 使用的 `main-project-inspection` 不同）。

### 前端 HOTEL_METER_READINGS_SHEETS

```typescript
// frontend/src/constants/hotelMeterReadings.ts
{
  'building-electric': { key: 'building-electric', title: '全棟電錶',       color: '#1B3A5C' },
  'mall-ac-electric':  { key: 'mall-ac-electric',  title: '商場空調箱電錶', color: '#4BA8E8' },
  'tenant-electric':   { key: 'tenant-electric',   title: '專櫃電錶',       color: '#52C41A' },
  'tenant-water':      { key: 'tenant-water',       title: '專櫃水錶',       color: '#1890ff' },
}
```

---

## 七、Menu 設定

### 位置：`MainLayout.tsx` hotel 群組

```tsx
{
  key: 'hotel',
  children: [
    // ... 既有項目 ...
    {
      key: '/hotel/daily-meter-readings',
      icon: <ReadOutlined />,
      label: NAV_PAGE.hotelMeterReadings,          // '每日數值登錄表'
      permissionKey: 'hotel_meter_readings_view',
    },
  ]
}
```

### 權限 Key（`role_permissions.py`）

```python
{"key": "hotel_meter_readings_view", "label": "每日數值登錄表", "group": "飯店管理"},
```

> 開發完成後，管理員需到「角色管理」頁面手動授予對應角色。

---

## 八、Dashboard 統計邏輯

### 端點：`GET /api/v1/hotel-meter-readings/dashboard/summary`

```json
{
  "target_date": "2026/04/30",
  "sheets": [
    {
      "key": "building-electric",
      "title": "全棟電錶",
      "has_data": true,
      "total_batches_this_month": 28,
      "latest_record_date": "2026/04/30",
      "total_readings": 15,
      "missing_days": []
    },
    ...
  ]
}
```

### 統計項目

| 指標 | 計算方式 |
|------|---------|
| 今日是否登錄 | 查詢 `record_date == today` 的 batch 是否存在 |
| 本月登錄筆數 | `COUNT(batch)` WHERE `record_date LIKE 'YYYY/MM/%'` |
| 最近登錄日期 | `MAX(record_date)` |
| 缺漏日期 | 本月 1 日到今日，找出無 batch 的日期 |
| 各 Sheet 讀數筆數 | `COUNT(reading)` JOIN batch |
| 最近 7 天趨勢 | 每天是否有 batch 紀錄（`has_record: bool`） |

---

## 九、待確認欄位（Ragic 端）

以下欄位需實際查看 Ragic 表單後確認，Sync Service 內以 `# TODO` 標記：

| 欄位用途 | 候選名稱 | 確認狀態 |
|---------|---------|---------|
| 登錄日期 | `登錄日期`、`日期`、`記錄日期` | ⏳ 未確認 |
| 登錄人員 | `登錄人員`、`記錄人員`、`人員` | ⏳ 未確認 |
| 儀表讀數是否含單位 | — | ⏳ 未確認 |
| 是否有「上期讀數」欄 | — | ⏳ 未確認 |

> 欄位名稱不影響同步功能（動態偵測），但影響 Dashboard 顯示名稱精確度。

---

## 十、路由清單

| 路由 | 說明 |
|------|------|
| `/hotel/daily-meter-readings` | 主頁（預設重導至 Dashboard Tab） |
| `/hotel/daily-meter-readings?tab=dashboard` | Dashboard 總覽 |
| `/hotel/daily-meter-readings?tab=building-electric` | 全棟電錶 |
| `/hotel/daily-meter-readings?tab=mall-ac-electric` | 商場空調箱電錶 |
| `/hotel/daily-meter-readings?tab=tenant-electric` | 專櫃電錶 |
| `/hotel/daily-meter-readings?tab=tenant-water` | 專櫃水錶 |

---

## 十一、測試檢查清單

開發完成後請逐項確認：

- [ ] `/hotel/daily-meter-readings` 可正常開啟
- [ ] Dashboard Tab 顯示 4 個 Sheet 統計卡片
- [ ] 4 個資料 Tab 可切換
- [ ] 每個 Tab 月份篩選可正常篩選
- [ ] 搜尋欄位可過濾資料
- [ ] Sync 按鈕可觸發同步（背景執行，有 message 提示）
- [ ] 空資料時顯示友善提示
- [ ] API 錯誤時顯示 Alert（不 crash）
- [ ] Menu 出現在「飯店管理 > 每日數值登錄表」
- [ ] active_menu 正確高亮
- [ ] `settings/menu-config` 可看到此路由（系統管理員）
- [ ] `settings/roles` 的「飯店管理」群組有 `hotel_meter_readings_view`
- [ ] Ragic URL 點擊可連回對應 Ragic 表單

---

## 十二、開發限制提醒

1. ❌ 不改動 daily-inspection 任何功能
2. ❌ 不新增不必要 API
3. ✅ 完全沿用 daily-inspection 的 service / template 模式
4. ✅ UI 跟 portal 既有風格一致（Ant Design 5）
5. ✅ 受保護顏色：`#1B3A5C`、`#4BA8E8`、sidebar `#111827`
6. ✅ API 前綴統一 `/api/v1/`
7. ✅ Ragic Auth：`Authorization: Basic {API_KEY}`（不做 base64）
