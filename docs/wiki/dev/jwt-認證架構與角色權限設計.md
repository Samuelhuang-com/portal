---
id: 37db5789-7dc8-4473-8317-94a279a75933
title: JWT 認證架構與角色權限設計
slug: jwt-認證架構與角色權限設計
category: dev
tags:
- JWT
- 認證
- API設計
- 架構
author: 系統預設
author_id: system
is_published: true
created_at: '2026-05-03T22:26:39.799607'
updated_at: '2026-05-03T22:26:39.799607'
---

# JWT 認證架構與角色權限設計

## Token 結構

```python
# security.py
def create_access_token(subject: str, extra_claims: dict = {}) -> str:
    # ⚠️ subject 必須是純 UUID 字串（user.id）
    payload = {
        "sub": subject,           # user.id（UUID 字串）
        "email": extra_claims.get("email"),
        "roles": extra_claims.get("roles", []),
        "permissions": extra_claims.get("permissions", []),
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
```

## 角色系統

| 角色 | 說明 | 特殊行為 |
|------|------|---------|
| `system_admin` | 最高管理員 | permissions=["*"]，全部通過 |
| 自訂角色 | 由管理員建立 | 需明確設定 permission_keys |

## 前端 Permission Guard

```tsx
// 細粒度權限守衛
function PermissionGuard({ permissionKey, children }) {
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.roles?.includes('system_admin')
  const hasPermission = isAdmin ||
    user?.permissions?.includes('*') ||
    user?.permissions?.includes(permissionKey)

  return hasPermission ? children : <Forbidden403 />
}
```

## 後端 Dependency

```python
# dependencies.py
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    # 解碼 JWT → 取 sub（user.id）→ 查 DB
    ...

def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)):
        if not any(r in user.role_names for r in roles):
            raise HTTPException(403, "權限不足")
        return user
    return dependency
```

## Token 刷新策略
- Access Token 有效期：30 分鐘
- Refresh Token 有效期：7 天
- 前端：每次 API 請求前檢查 Token 是否快過期（< 5 分鐘），自動刷新

## 常見錯誤
- `401 Unauthorized`：Token 過期或無效，前端會自動跳轉登入頁
- `403 Forbidden`：已登入但無對應 permission_key，前端顯示 403 提示頁

