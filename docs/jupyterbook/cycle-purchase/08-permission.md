# 權限

## 8 個權限 key

定義於 `backend/app/routers/role_permissions.py` 的 `PERMISSION_DEFINITIONS`，group 為「週期採購」。

| key | label | 給誰 |
|-----|-------|------|
| `cycle_purchase_view` | 週期採購管理 | 全模組可見（含已關閉單據） |
| `cycle_purchase_request` | 週期採購請購 | 各部門填單人 |
| `cycle_purchase_close` | 週期採購請購關閉 | 關閉／重新開啟請購單 |
| `cycle_purchase_buyer` | 週期採購彙整／採購 | 採購人員 |
| `cycle_purchase_receive` | 週期採購驗收 | 收貨單位 |
| `cycle_purchase_finance` | 週期採購請款 | 財務 |
| `cycle_purchase_report` | 週期採購報表 | 進貨數量報表 |
| `cycle_purchase_admin` | 週期採購管理設定 | 主檔、週期設定、稽核紀錄 |

```{admonition} cycle_purchase_approve 已停用
:class: note

2026-07-17 拿掉送出／簽核流程後，`cycle_purchase_approve` 不再使用，
改成獨立的 `cycle_purchase_close`。舊角色若仍掛著 approve，不會有任何效果。
```

## 端點守衛統計

盤點自 9 個 router 的 `Depends(...)`：

| 守衛 | 次數 |
|------|------|
| `require_permission("cycle_purchase_admin")` | 20 |
| `require_permission("cycle_purchase_buyer")` | 17 |
| `require_permission("cycle_purchase_view")` | 13 |
| `require_permission("cycle_purchase_finance")` | 6 |
| `require_permission("cycle_purchase_request")` | 6 |
| `require_permission("cycle_purchase_receive")` | 5 |
| `require_permission("cycle_purchase_close")` | 4 |
| `require_permission("cycle_purchase_report")` | 1 |
| `require_any_permission("cycle_purchase_view", "cycle_purchase_buyer")` | 4 |
| `require_any_permission("cycle_purchase_view", "cycle_purchase_request")` | 4 |
| `require_any_permission("cycle_purchase_view", "cycle_purchase_finance")` | 2 |
| `require_any_permission("cycle_purchase_view", "cycle_purchase_receive")` | 2 |

```{admonition} 週採的後端守衛是齊的
:class: important

CLAUDE.md §11.6 列出 14 個「GET 端點只掛 `get_current_user`、後端不擋」的模組——
**週採不在其中**。週採每一支端點都有明確的權限守衛，前端藏選單只是第二層。
```

## 資料層的額外過濾

權限之外還有兩層資料範圍限制：

1. **`_can_see_closed()`**（請購單清單）
   持有 `*` / `cycle_purchase_close` / `cycle_purchase_view` 才看得到已關閉的單。

2. **`_ensure_own_department()`**（請購單編輯）
   只勾 `cycle_purchase_request` 的人，只能動**自己部門**的單。
   「自己部門」是靠 `cycle_purchase_departments.owner_user_id` 對到登入者判斷的。

```{admonition} owner_user_id 沒設 = 填單人動不了自己的單
:class: caution

這是最常見的「權限開了還是不能用」原因。部門主檔的承辦人沒設，
Dashboard 的「我的待辦」會是空的，編輯請購單也會被 `_ensure_own_department()` 擋下。
```

## 與 §11 防提權規則的關係

週採的 8 個 key **不屬於**敏感權限群組（那 20 個是 `opera_` / `jinxu_` / `realtime_` 前綴的 PMS 營收資料）。
但 CLAUDE.md §11.2 的三條規則仍適用於管理這些 key 的人：

1. 不得授予自己沒有的權限
2. 只看得到自己擁有的 key
3. 不得變更／重設密碼給持有你無權管理之角色的使用者
