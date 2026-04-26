# Claude AI 開發標準化作業 (SOP)

> 本文件定義與 Claude AI 協作開發 Portal 專案的標準提示詞範本。
> 三種情境：① 新對話繼續開發、② 新增功能、③ 修改現有功能。

---

## 情境一：開啟新對話，繼續上次的開發

```
繼續開發 portal 專案。

請先讀以下三個文件再回應：
1. docs/DEV_LOG.md       → 了解上次做到哪裡、有什麼待釐清問題
2. docs/FEATURE_MAP.md   → 了解系統架構，避免重新掃描
3. CLAUDE.md             → 專案規則（你已知道，快速確認即可）

讀完後告訴我：
- 上次未完成的項目是什麼
- 有哪些待釐清的問題
然後等我說要做什麼。
```

---

## 情境二：新增功能

```
繼續開發 portal 專案，現在要新增「＿＿＿＿功能」。

背景說明：
- 對應會議/決議：＿＿＿（例：04-23 整合會議 §事件單）
- 功能描述：＿＿＿
- 預計影響範圍：後端 model + router / 前端頁面 / 兩者都有

請先讀：
1. docs/FEATURE_MAP.md   → 確認涉及的現有檔案
2. docs/DEV_LOG.md       → 確認沒有衝突的進行中項目
3. CLAUDE.md             → 確認規則（特別是受保護元素與禁止行為）

讀完後：
1. 告訴我你的開發計劃（涉及哪些檔案、做什麼改動）
2. 等我確認後再動手
3. 完成後更新 docs/DEV_LOG.md、docs/CHANGELOG.md、README.md
```

---

## 情境三：修改現有功能（附上 diff 或說明）

### 方式 A：貼 git diff（最精準）
```
繼續開發 portal 專案，我剛做了以下修改，請幫我：
① 確認改法是否符合 04-23 整合會議的決議要求
② 檢查有沒有遺漏的地方
③ 更新 docs/DEV_LOG.md

修改內容（git diff）：
--- a/backend/app/models/luqun_repair.py
+++ b/backend/app/models/luqun_repair.py
[貼上 diff 內容]
```

### 方式 B：用自然語言描述
```
繼續開發 portal 專案，我剛完成以下修改：

【修改的檔案】
- backend/app/models/luqun_repair.py：新增 case_progress 欄位（待辦/結案/作廢）
- backend/app/services/luqun_repair_sync.py：sync 時自動填入 case_progress

【對應會議決議】
04-23 整合會議 §案件雙欄位

【請幫我做】
1. 確認這個改法是否符合決議要求
2. 檢查 dazhi_repair.py 是否也需要同步修改（應該是要的）
3. 更新 docs/DEV_LOG.md 記錄今天的進度
```

---

## 情境四：會議記錄 vs 系統差異分析（快速版）

```
請根據附件「YYYY-MM-DD 會議.docx」，對照 docs/FEATURE_MAP.md，
做「會議決議 vs 系統現況」差異分析。

限制：
- 只分析，不修改程式
- 依 FEATURE_MAP.md 定位涉及檔案，不需要全程式掃描
- 如果 FEATURE_MAP 沒有的功能，再局部 grep

輸出：Excel 差異分析表（格式同上次 04-23整合會議_差異分析.xlsx）
```

---

## 情境五：Debug / 修 Bug

```
繼續開發 portal 專案，遇到以下問題：

【錯誤訊息/現象】
＿＿＿（貼上 log 最後 20 行 或 描述現象）

【我認為涉及的檔案】（參考 FEATURE_MAP）
- ＿＿＿

【已嘗試過】
- ＿＿＿

請先讀 docs/FEATURE_MAP.md 確認涉及範圍，再協助 debug。
完成後記得更新 docs/DEV_LOG.md。
```

---

## DEV_LOG 快速更新（每次開發結束）

完成一個功能後，請對 Claude 說：

```
今天的開發結束了，請更新 docs/DEV_LOG.md：

完成：
- ＿＿＿（檔案 + 一行說明 + 對應決議）

進行中（明天繼續）：
- ＿＿＿

待釐清：
- ＿＿＿（等誰確認）
```

---

## 注意事項

1. **每次新對話都要讓 Claude 讀 DEV_LOG + FEATURE_MAP**，否則它沒有上下文
2. **FEATURE_MAP 要跟著程式一起維護**：新增模組時順手補一行
3. **貼 git diff 比自然語言描述更精準**，但兩種方式都可以
4. **會議記錄分析**：上傳 .docx 後，Claude 會自動讀 FEATURE_MAP 定位檔案，不需要全掃描
