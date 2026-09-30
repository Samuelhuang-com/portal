import io
def rw(path, pairs):
    s = io.open(path, encoding='utf-8', newline='').read()
    assert '\r\n' not in s, path+' has CRLF'
    n0 = len(s)
    for old, new in pairs:
        c = s.count(old); assert c == 1, (path, old[:70], c)
        s = s.replace(old, new)
    io.open(path, 'w', encoding='utf-8', newline='\n').write(s)
    print(path, n0, '->', len(s))

rw('backend/app/dependencies.py', [(
'''    role_ids = [r[0] for r in role_rows]
    perm_rows = (
        db.query(RolePermission.permission_key)
        .filter(RolePermission.role_id.in_(role_ids))
        .all()
    )
    return list({r[0] for r in perm_rows})
''',
'''    role_ids = [r[0] for r in role_rows]
    perm_rows = (
        db.query(RolePermission.permission_key)
        .filter(RolePermission.role_id.in_(role_ids))
        .all()
    )
    perms = {r[0] for r in perm_rows}
    # 2026-09-30：「限系統管理員」鎖定的模組群組，對非系統管理員一律扣除
    # （角色設定原樣保留，解除鎖定即恢復）。見 app/core/permission_locks.py
    from app.core.permission_locks import get_locked_keys
    perms -= get_locked_keys(db)
    return list(perms)
''')])

rw('backend/app/routers/users.py', [
('''    my_perms = set(get_user_permissions(current_user.id, db))
    if "*" in my_perms:
        return

    for role_name in role_names:''',
'''    my_perms = set(get_user_permissions(current_user.id, db))
    if "*" in my_perms:
        return
    # 被「限系統管理員」鎖定的 key 對非系統管理員無效，不計入比對
    locked_keys = get_locked_keys(db)

    for role_name in role_names:'''),
('''        missing = sorted(role_perms - my_perms)''',
'''        missing = sorted(role_perms - locked_keys - my_perms)'''),
('''    out: list[str] = []
    for role in roles:''',
'''    locked_keys = get_locked_keys(db)
    out: list[str] = []
    for role in roles:'''),
('''        if role_perms <= my_perms:''',
'''        if (role_perms - locked_keys) <= my_perms:'''),
('''from app.core.time import twnow
''',
'''from app.core.time import twnow
from app.core.permission_locks import get_locked_keys
'''),
])

rw('backend/app/routers/role_permissions.py', [
('''from app.dependencies import get_current_user, get_user_permissions, require_permission
''',
'''from app.dependencies import get_current_user, get_user_permissions, require_permission, is_system_admin
'''),
('''@router.get("/{role_id}", response_model=RolePermissionsOut)''',
'''# ── 模組群組「限系統管理員」鎖定（2026-09-30）────────────────────────────────
# ⚠️ 必須宣告在 /{role_id} 之前，否則 "locked-groups" 會被當成 role_id。
class LockedGroupsPayload(BaseModel):
    groups: list[str]


@router.get("/locked-groups", response_model=list[str])
def list_locked_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(_MANAGE),
):
    """目前被鎖定為「限系統管理員」的模組群組名稱。"""
    from app.core.permission_locks import get_locked_groups
    return get_locked_groups(db)


@router.put("/locked-groups", response_model=list[str])
def save_locked_groups(
    payload: LockedGroupsPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(is_system_admin),
):
    """
    整批取代鎖定群組清單（僅系統管理員）。
    鎖定後，群組內所有 key 對非系統管理員失效；角色原本的勾選不會被刪。
    """
    from app.core.permission_locks import all_groups, set_locked_groups
    unknown = [g for g in payload.groups if g not in set(all_groups())]
    if unknown:
        raise HTTPException(status_code=422, detail=f"未知的權限群組：{', '.join(unknown)}")
    return set_locked_groups(db, payload.groups, current_user.email)


@router.get("/{role_id}", response_model=RolePermissionsOut)'''),
])

rw('frontend/src/api/rolePermissions.ts', [(
'''/** 取得指定角色的 permission_key 清單 */''',
'''/** 取得被鎖定為「限系統管理員」的模組群組（2026-09-30） */
export async function fetchLockedGroups(): Promise<string[]> {
  const res = await apiClient.get<string[]>('/role-permissions/locked-groups')
  return Array.isArray(res.data) ? res.data : []
}

/** 整批取代鎖定群組清單（僅系統管理員） */
export async function saveLockedGroups(groups: string[]): Promise<string[]> {
  const res = await apiClient.put<string[]>('/role-permissions/locked-groups', { groups })
  return res.data
}

/** 取得指定角色的 permission_key 清單 */'''),
])

fe = 'frontend/src/pages/Settings/Roles.tsx'
rw(fe, [
('''  saveRolePermissions,
  PermissionKeyDef,
} from '@/api/rolePermissions';''',
'''  saveRolePermissions,
  fetchLockedGroups,
  saveLockedGroups,
  PermissionKeyDef,
} from '@/api/rolePermissions';
import { useAuthStore } from '@/stores/authStore';'''),
('''  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // 取得所有 permission key 定義''',
'''  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // ── 模組群組「限系統管理員」鎖定（2026-09-30）──────────────────────────────
  // V 只給系統管理員操作；鎖定後該群組對其他所有角色都不可見（後端 get_user_permissions 扣除）
  const { user: me } = useAuthStore();
  const meIsSuperAdmin = (me?.permissions?.includes('*') ?? false)
    || (me?.roles?.includes('system_admin') ?? false);
  const [lockedGroups, setLockedGroups] = useState<Set<string>>(new Set());
  const [lockSaving, setLockSaving] = useState<string | null>(null);

  useEffect(() => {
    fetchLockedGroups()
      .then((g) => setLockedGroups(new Set(g)))
      .catch(() => {});
  }, []);

  const applyGroupLock = async (group: string, lock: boolean) => {
    const next = new Set(lockedGroups);
    if (lock) next.add(group); else next.delete(group);
    setLockSaving(group);
    try {
      const saved = await saveLockedGroups(Array.from(next));
      setLockedGroups(new Set(saved));
      message.success(lock
        ? `「${group}」已鎖定：僅系統管理員可見`
        : `「${group}」已解除鎖定，各角色依原本勾選恢復`);
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '更新鎖定設定失敗');
    } finally {
      setLockSaving(null);
    }
  };

  const toggleGroupLock = (group: string, lock: boolean) => {
    if (!lock) { applyGroupLock(group, false); return; }
    Modal.confirm({
      title: `將「${group}」設為限系統管理員？`,
      icon: <ExclamationCircleOutlined />,
      content: '鎖定後，除系統管理員外的所有角色都看不到這個模組（選單、頁面、API 一併擋下）。各角色原本的勾選會保留，解除鎖定後即恢復。',
      okText: '鎖定',
      cancelText: '取消',
      onOk: () => applyGroupLock(group, true),
    });
  };

  // 取得所有 permission key 定義'''),
('''                const someChecked = groupKeys.some((k) => checkedKeys.has(k));

                return (
                  <div key={group} style={{ marginBottom: 20 }}>
                    <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>''',
'''                const someChecked = groupKeys.some((k) => checkedKeys.has(k));
                const groupLocked = lockedGroups.has(group);

                return (
                  <div key={group} style={{ marginBottom: 20, opacity: groupLocked ? 0.75 : 1 }}>
                    <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>'''),
('''                        <span style={{ fontWeight: 600, color: '#1B3A5C' }}>{group}</span>
                      </Checkbox>
                    </div>''',
'''                        <span style={{ fontWeight: 600, color: '#1B3A5C' }}>{group}</span>
                      </Checkbox>
                      {groupLocked && (
                        <Tag icon={<LockOutlined />} color="blue" style={{ marginLeft: 4 }}>
                          限系統管理員
                        </Tag>
                      )}
                      {meIsSuperAdmin && (
                        <div style={{ marginLeft: 'auto' }}>
                          <Tooltip title="勾選 V：此模組只有系統管理員看得到，其他角色的勾選暫不生效（全域設定，不分角色）">
                            <Checkbox
                              checked={groupLocked}
                              disabled={lockSaving !== null}
                              onChange={(e) => toggleGroupLock(group, e.target.checked)}
                            >
                              <span style={{ fontSize: 12, color: '#64748b' }}>V 限系統管理員</span>
                            </Checkbox>
                          </Tooltip>
                        </div>
                      )}
                    </div>
                    {groupLocked && (
                      <div style={{ paddingLeft: 24, marginBottom: 6, fontSize: 12, color: '#94a3b8' }}>
                        此模組已鎖定為限系統管理員；下方勾選會保留，但在解除鎖定前對此角色不生效。
                      </div>
                    )}'''),
])
