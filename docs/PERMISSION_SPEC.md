# Portal 權限管控規格書

> 版本：1.0.0 | 建立日期：2026-04-29 | 作者：系統架構

---

## 一、設計原則

Portal 採用「**角色 → 權限 key → 菜單/頁面/API 三層控制**」的輕量 RBAC 模型。

| 層級 | 控制點 | 說明 |
|------|--------|------|
| 菜單層 | `filterMenuByPermissions()` | 前端 sidebar 根據使用者 permissions 過濾 |
| 頁面層 | `PermissionGuard` component | 前端路由守衛，無權限顯示 403 提示 |
| API 層 | `require_permission(key)` | FastAPI dependency，無權限回傳 HTTP 403 |

**核心資料流：**

```
使用者登入 → POST /auth/login
  → 後端回傳 UserInfo（含 permissions: string[]）
  → authStore.user.permissions 存入記憶體
  → sidebar filterMenuByPermissions 過濾選單
  → PermissionGuard 保護頁面路由
  → require_permission() 保護 API 端點
```

---

## 二、Permission Key 命名規則

格式：`<module>_<action>`

| Action | 用途 |
|--------|------|
| `view` | 查看頁面、讀取資料 |
| `manage` | 新增、修改、同步、匯入 |
| `admin` | 刪除、系統設定、管理級操作 |

**範例：**

```
settings_users_manage     → 人員管理
settings_roles_manage     → 角色管理
settings_menu_manage      → 選單管理
settings_ragic_manage     → Ragic 設定
mall_dashboard_view       → 商場統計查看
hotel_periodic_maintenance_view → 飯店週期保養查看
budget_admin              → 預算系統設定（含刪除）
```

---

## 三、新模組開發流程（重要）

### 🚧 開發期間

1. **前端 `menuItems` 設定 `permissionKey: 'system_admin_only'`**
   - 此 key 不會被加入任何角色的 `role_permissions` 表
   - 效果：只有 `system_admin`（permissions=["*"]）可見

2. **後端 API 使用 `Depends(is_system_admin)` 保護**（開發期暫用）

3. **在 `PERMISSION_DEFINITIONS`（`role_permissions.py`）加入新 key 定義**，但先不授予任何角色

```typescript
// 前端 MainLayout.tsx menuItems 範例（開發期）
{ key: '/new-module', label: '新模組', permissionKey: 'system_admin_only' }
```

```python
# 後端 API 範例（開發期）
@router.get("/", dependencies=[Depends(is_system_admin)])
```

### ✅ 測試完成後（上線前）

1. **確認 permission_key 命名**，加入 `PERMISSION_DEFINITIONS` 清單

2. **前端 `menuItems` 改為正確的 permission_key**：
   ```typescript
   { key: '/new-module', label: '新模組', permissionKey: 'new_module_view' }
   ```

3. **後端 API 改為 `Depends(require_permission('new_module_view'))`**

4. **透過角色管理頁面**（Settings → 角色管理 → 權限設定 Tab）：
   - 手工勾選要授予此模組的角色
   - 點擊「儲存權限」
   - 相關使用者重新登入（或等 JWT 過期）後即生效

5. **更新 `docs/CHANGELOG.md` 與 `README.md`**

---

## 四、DB Schema

### `role_permissions` 表（新增）

```sql
CREATE TABLE role_permissions (
    id           VARCHAR(36) PRIMARY KEY,
    role_id      VARCHAR(36) NOT NULL,
    permission_key VARCHAR(100) NOT NULL,
    UNIQUE (role_id, permission_key)
);
CREATE INDEX ix_role_permissions_role_id ON role_permissions(role_id);
```

### `menu_configs` 表（新增欄位）

```sql
ALTER TABLE menu_configs ADD COLUMN permission_key TEXT;
-- NULL = 公開顯示；有值 = 需具備對應 permission_key
```

---

## 五、後端 API

### `get_user_permissions(user_id, db) → list[str]`

- 位置：`backend/app/dependencies.py`
- system_admin 回傳 `["*"]`（萬用符）
- 其他角色回傳 `role_permissions` 聯集結果

### `require_permission(key) → FastAPI Dependency 工廠`

```python
# 使用方式
@router.get("/endpoint")
def endpoint(
    _: User = Depends(require_permission("settings_users_manage"))
):
    ...
```

### `GET /api/v1/role-permissions/keys`

回傳系統所有已知的 permission_key 定義（用於 Roles 頁面 checkbox）

### `GET /api/v1/role-permissions/{role_id}`

取得指定角色的 permission_key 清單

### `PUT /api/v1/role-permissions/{role_id}`

覆寫指定角色的 permission_key 清單

### `GET /api/v1/roles`

取得所有角色清單（含 id，供前端 Roles 頁面使用）

### `GET /api/v1/auth/me`（擴充）

回應新增 `permissions: list[str]` 欄位

---

## 六、前端架構

### `authStore.ts`

- 新增 `permissions?: string[]` 欄位
- 新增 `hasPermission(key: string): boolean` 方法
- system_admin → `permissions=["*"]` → `hasPermission()` 永遠回傳 true
- 登入後由 `/auth/login` 回應帶入；刷新後由 `/auth/me` 補回

### `MainLayout.tsx` — `menuItems` 型別

```typescript
interface MenuItem {
  key: string
  permissionKey?: string | null  // null = 公開；有值 = 需要此 key
  children?: MenuItem[]
}
```

### `filterMenuByPermissions(items, permissions, dbPermMap)`

- `dbPermMap`：`menu_configs` 的 DB 設定（DB 優先於靜態預設）
- 父層若所有子項都被過濾，父層本身也不顯示
- 執行順序：`applyMenuConfig()` → `filterMenuByPermissions()`

### `PermissionGuard` component

```tsx
<PermissionGuard permissionKey="settings_users_manage">
  <UsersPage />
</PermissionGuard>
```

無權限時顯示 🔒 403 提示頁（不跳轉）

---

## 七、system_admin 特殊處理

`system_admin` 角色在整個系統中享有特殊待遇：

- 後端 `get_user_permissions()` 回傳 `["*"]`
- 前端 `hasPermission()` 遇到 `"*"` 永遠回傳 `true`
- `role_permissions` 表中**不存入** system_admin 的記錄（不需要）
- `Roles.tsx` 的「權限設定」Tab 中，system_admin 行為 disabled 且顯示說明

---

## 八、現有模組權限一覽表

| 模組 | permission_key | 目前授予狀態 |
|------|----------------|------------|
| 系統設定 - 人員管理 | `settings_users_manage` | 需手工授予 |
| 系統設定 - 角色管理 | `settings_roles_manage` | 需手工授予 |
| 系統設定 - 選單管理 | `settings_menu_manage` | 需手工授予 |
| 系統設定 - Ragic | `settings_ragic_manage` | 需手工授予 |
| 飯店模組各頁面 | `hotel_*_view` | 公開（null，預設不限制） |
| 商場模組各頁面 | `mall_*_view` | 公開（null，預設不限制） |
| 保全模組各頁面 | `security_*_view` | 公開（null，預設不限制） |
| 預算模組各頁面 | `budget_*` | 公開（null，預設不限制） |

> 現有模組 `permissionKey` 預設為 `null`（向後相容，不影響現有使用者）。
> 如需啟用限制，在 MenuConfig 頁面或 `menuItems` 靜態常數設定 permission_key 即可。

---

## 九、驗收測試清單

- [ ] `system_admin` 可看到所有 Menu，可進入所有設定頁面
- [ ] 無權限的使用者無法在 sidebar 看到受保護的 menu item
- [ ] 無權限的使用者直接輸入 `/settings/users` → 顯示 🔒 403 提示頁
- [ ] 無權限的使用者呼叫 `PUT /settings/menu-config` → HTTP 403
- [ ] 在 Roles.tsx 勾選權限後儲存，目標角色的使用者重登後 menu 更新
- [ ] MenuConfig 頁面可設定/清除每個 menu item 的 permission_key
- [ ] 不影響既有模組的資料顯示（dashboard、維護、巡檢、報修等）

---

## 十、回復方式

若需回滾此功能：

1. **後端**：移除 `role_permissions.py` router 在 `main.py` 的 include，停用 `require_permission` 保護
2. **DB**：`DROP TABLE role_permissions;` + `ALTER TABLE menu_configs DROP COLUMN permission_key;`（SQLite 不支援 DROP COLUMN，可直接忽略此欄）
3. **前端**：還原 `authStore.ts`、`MainLayout.tsx`（移除 filter）、`router/index.tsx`（移除 PermissionGuard）

由於所有 DB 變更均為 nullable 欄位或新表，不影響現有資料。
