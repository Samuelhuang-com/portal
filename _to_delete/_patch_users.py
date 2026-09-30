import io
def rw(path, pairs):
    s = io.open(path, encoding='utf-8', newline='').read()
    assert '\r\n' not in s, path+' has CRLF'
    n0 = len(s)
    for old, new in pairs:
        c = s.count(old)
        assert c == 1, (path, old[:60], c)
        s = s.replace(old, new)
    io.open(path, 'w', encoding='utf-8', newline='\n').write(s)
    print(path, n0, '->', len(s))

# ---------- backend ----------
be = 'backend/app/routers/users.py'
rw(be, [(
'''def _assert_can_manage_target(current_user: User, target: User, db: Session) -> None:''',
'''def _grantable_role_names(current_user: User, db: Session) -> list[str]:
    """
    呼叫者「可以指派」的角色清單 —— 與 _assert_can_grant_roles 同一套規則，
    供前端「新增／編輯使用者」的角色下拉只列出可選項（2026-09-30）。
    """
    roles = db.query(Role).order_by(Role.name).all()
    my_perms = set(get_user_permissions(current_user.id, db))
    if "*" in my_perms:
        return [r.name for r in roles]
    out: list[str] = []
    for role in roles:
        if role.name == "system_admin":
            continue
        role_perms = {
            p[0]
            for p in db.query(RolePermission.permission_key)
            .filter(RolePermission.role_id == role.id)
            .all()
        }
        if role_perms <= my_perms:
            out.append(role.name)
    return out


def _assert_can_manage_target(current_user: User, target: User, db: Session) -> None:'''),
(
'''@router.post("", response_model=UserOut)''',
'''@router.get("/grantable-roles", response_model=list[str])
def list_grantable_roles(
    current_user: User = Depends(_USER_MANAGE),
    db: Session = Depends(get_db),
):
    """
    目前登入者可指派的角色名稱（2026-09-30）。
    非系統管理員看不到 system_admin，也看不到含有自己未擁有權限的角色；
    規則與 create_user / update_user 的 _assert_can_grant_roles 相同。
    """
    return _grantable_role_names(current_user, db)


@router.post("", response_model=UserOut)'''),
])

# ---------- frontend api ----------
rw('frontend/src/api/users.ts', [(
'''  /** 取得啟用中使用者名稱清單，供 manager/reviewer 下拉使用（任何登入者可呼叫） */
  options: () =>''',
'''  /** 目前登入者可指派的角色名稱（非系統管理員不含 system_admin 與超出自身權限的角色） */
  grantableRoles: () =>
    client.get<string[]>('/users/grantable-roles'),
  /** 取得啟用中使用者名稱清單，供 manager/reviewer 下拉使用（任何登入者可呼叫） */
  options: () =>'''),
])

# ---------- frontend page ----------
fe = 'frontend/src/pages/Settings/Users.tsx'
rw(fe, [(
'''  const [allRoles, setAllRoles] = useState<RoleData[]>([]);
''',
'''  const [allRoles, setAllRoles] = useState<RoleData[]>([]);
  // 可指派角色（後端 /users/grantable-roles）；null＝尚未載入或端點失敗
  const [grantable, setGrantable] = useState<string[] | null>(null);
  // 目前登入者是否為系統管理員（permissions 含 * 或持有 system_admin 角色）
  const isSuperAdmin = (me?.permissions?.includes('*') ?? false)
    || (me?.roles?.includes('system_admin') ?? false);
'''),
(
'''    fetchRoles().then(setAllRoles).catch(() => {});
''',
'''    fetchRoles().then(setAllRoles).catch(() => {});
    usersApi.grantableRoles().then(r => setGrantable(r.data)).catch(() => setGrantable(null));
'''),
(
'''    form.setFieldValue('role_names', ['viewer']);''',
'''    // 預設「一般使用者」；若目前登入者無權指派 viewer 就不預帶
    if (!grantable || grantable.includes('viewer')) {
      form.setFieldValue('role_names', ['viewer']);
    }'''),
(
'''              options={allRoles.map(r => ({
                value: r.name,
                label: getRoleLabel(r.name),
              }))}''',
'''              options={roleOptions}'''),
(
'''  const openCreate = () => {''',
'''  // 角色下拉：只列出目前登入者可指派的角色（2026-09-30）
  //  - 非系統管理員看不到「系統管理員」，也看不到含有自己沒有權限的角色（後端同規則會回 403）
  //  - 編輯時對方已持有、但我無權指派的角色仍顯示為 disabled，避免 Tag 變成英文代碼
  //  - grantable 端點失敗（例如後端未重啟）時退回最低限度規則：非系統管理員隱藏 system_admin
  const roleOptions = React.useMemo(() => {
    const canGrant = (name: string) =>
      grantable ? grantable.includes(name) : (isSuperAdmin || name !== 'system_admin');
    const current: string[] = editUser?.roles ?? [];
    return allRoles
      .filter(r => canGrant(r.name) || current.includes(r.name))
      .map(r => ({
        value: r.name,
        label: getRoleLabel(r.name),
        disabled: !canGrant(r.name),
      }));
  }, [allRoles, grantable, isSuperAdmin, editUser]);

  const openCreate = () => {'''),
])
