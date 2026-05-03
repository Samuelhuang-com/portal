# 健康分數公式規格 — 決策駕駛艙

> ⚠️ 本規格為初始草案，需業主確認後才能固化。
> 程式碼以 configurable constants 實作（`HEALTH_SCORE_WEIGHTS`），確認後無需大規模修改。

---

## 一、健康分數定義

健康分數（Health Score）是將各模組的完成率、逾期率、異常率、資料完整度整合為單一 0~100 分的指標，讓主管一眼判斷各管理面向的狀況。

---

## 二、計算公式（草案）

```
健康分數 = 
  完成率(%) × W1
  + (100 - 逾期率(%)) × W2
  + (100 - 異常率(%)) × W3
  + 資料完整度(%) × W4

其中（草案權重）：
  W1 = 0.40   // 完成率：主要績效指標
  W2 = 0.25   // 逾期控制：逾期率越低越好（反向）
  W3 = 0.20   // 異常管理：異常率越低越好（反向）
  W4 = 0.15   // 資料品質：有負責人且有工時且有狀態的比例
```

### 各維度計算說明

| 維度 | 公式 | 說明 |
|------|------|------|
| 完成率 | `completed_count / total_count × 100` | 本月已完成案件占總案件 % |
| 逾期率 | `overdue_count / total_count × 100` | 本月逾期未完成占總案件 % |
| 異常率 | `abnormal_count / total_count × 100` | 異常標記案件占總案件 % |
| 資料完整度 | `(有負責人 ∩ 有工時 ∩ 有狀態) / total × 100` | 欄位完整的筆數占比 |

---

## 三、四個健康分數的計算來源

### 集團整體健康分數
```
集團健康 = 飯店健康 × 0.40 + 商場健康 × 0.40 + 工務健康 × 0.20
```

### 飯店管理健康分數
六個來源各計算 sub_score，再依工時比例加權平均：
1. 客房保養管理（`/room-maintenance-detail/maintenance-stats`）
2. 飯店週期保養（`/periodic-maintenance/stats`）
3. IHG 客房保養（`/ihg-room-maintenance/stats`）
4. 飯店每日巡檢（`/hotel-daily-inspection/dashboard/summary`）
5. 保全巡檢（`/security/dashboard/summary`）
6. 大直工務部（`/dazhi-repair/dashboard`）

### 商場管理健康分數
五個工項各計算 sub_score，上級交辦/緊急事件標記「資料不足」不納入計算：
1. 商場例行維護（`/mall-periodic-maintenance/stats`）
2. 全棟例行維護（`/full-building-maintenance/stats`）
3. 商場每日巡檢（`/mall-facility-inspection/dashboard/summary`）
4. 現場報修（`/luqun-repair/dashboard`）
5. 上級交辦 → 灰燈（資料準備中，不計算）
6. 緊急事件 → 灰燈（資料準備中，不計算）

### 工務維護健康分數
```
工務健康 = 大直工務健康 × 0.60 + 樂群報修健康 × 0.40
```

---

## 四、燈號閾值

| 燈號 | 分數範圍 | 顏色 |
|------|---------|------|
| 🟢 正常 | ≥ 80 | `#52c41a` |
| 🟡 需注意 | 60 ~ 79 | `#faad14` |
| 🔴 警告 | < 60 | `#ff4d4f` |
| ⚫ 資料不足 | 無資料 | `#8c8c8c` |

---

## 五、程式碼常數定義（方便業主確認後調整）

```typescript
// frontend/src/pages/DecisionCockpit/utils/healthScore.ts

export const HEALTH_SCORE_WEIGHTS = {
  completion_rate:   0.40,   // 完成率權重
  overdue_control:   0.25,   // 逾期控制權重（反向）
  anomaly_control:   0.20,   // 異常管理權重（反向）
  data_completeness: 0.15,   // 資料完整度權重
} as const

export const HEALTH_THRESHOLDS = {
  green:  80,   // ≥ 80 → 綠燈
  yellow: 60,   // 60~79 → 黃燈
                // < 60 → 紅燈
} as const

export const GROUP_WEIGHTS = {
  hotel:  0.40,   // 飯店管理占集團健康
  mall:   0.40,   // 商場管理占集團健康
  repair: 0.20,   // 工務維護占集團健康
} as const

export const REPAIR_WEIGHTS = {
  dazhi:  0.60,   // 大直工務占工務健康
  luqun:  0.40,   // 樂群報修占工務健康
} as const
```

---

## 六、確認事項（業主請確認後方可固化）

- [ ] 四個維度的權重（40/25/20/15）是否合適？
- [ ] 集團健康的飯店/商場/工務比例（40/40/20）是否合適？
- [ ] 工務健康的大直/樂群比例（60/40）是否合適？
- [ ] 綠/黃/紅燈閾值（80/60）是否合適？
- [ ] 資料完整度的「有負責人 ∩ 有工時 ∩ 有狀態」定義是否正確？

> 請業主在上方 checkbox 確認後，通知開發團隊固化常數。
