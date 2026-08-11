"""
角色權限管理 Router
GET  /api/v1/role-permissions/{role_id}   取得角色的 permission_key 清單
PUT  /api/v1/role-permissions/{role_id}   覆寫角色的 permission_key 清單
GET  /api/v1/role-permissions/keys        取得系統所有已知的 permission_key 定義

僅限 system_admin 操作。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.dependencies import is_system_admin
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User

router = APIRouter()


PERMISSION_DEFINITIONS = [
    {"key": "decision_cockpit_view",      "label": "決策駕駛艙",         "group": "一階選單"},
    {"key": "exec_dashboard_view",        "label": "高階主管 Dashboard",  "group": "一階選單"},
    {"key": "exec_work_dashboard_view",   "label": "集團決策 Dashboard",  "group": "一階選單"},
    {"key": "work_category_analysis_view","label": "工項類別分析",        "group": "一階選單"},
    {"key": "calendar_view",              "label": "行事曆",             "group": "一階選單"},
    {"key": "tutorial_videos_view",       "label": "影音教學：查看",      "group": "一階選單"},
    {"key": "tutorial_videos_manage",     "label": "影音教學：上傳/管理", "group": "一階選單"},
    # 2026-08-11 新增：/wiki 原本在 MainLayout.menuItems 沒有 permissionKey，
    # 而 filterMenuByPermissions 的規則是「沒設 = 公開」，導致知識庫對所有角色顯示。
    {"key": "wiki_view",                  "label": "知識庫",             "group": "一階選單"},
    {"key": "settings_users_manage",    "label": "人員管理",   "group": "系統設定"},
    {"key": "settings_roles_manage",    "label": "角色管理",   "group": "系統設定"},
    {"key": "settings_menu_manage",     "label": "選單管理",   "group": "系統設定"},
    {"key": "settings_ragic_manage",    "label": "Ragic 設定", "group": "系統設定"},
    {"key": "hotel_view",                        "label": "飯店模組",         "group": "飯店管理"},
    {"key": "hotel_room_maintenance_view",        "label": "客房保養",         "group": "飯店管理"},
    {"key": "hotel_periodic_maintenance_view",    "label": "飯店週期保養",     "group": "飯店管理"},
    {"key": "hotel_ihg_room_maintenance_view",    "label": "IHG 客房保養",     "group": "飯店管理"},
    {"key": "hotel_daily_inspection_view",        "label": "飯店每日巡檢",     "group": "飯店管理"},
    {"key": "hotel_meter_readings_view",          "label": "每日數值登錄表",   "group": "飯店管理"},
    {"key": "hotel_other_tasks_view",             "label": "主管交辦／緊急事件","group": "飯店管理"},
    # 2026-07-14：hotel_routine_pm 安全下線（與 hotel_periodic_maintenance_view 重複，
    # 使用者確認後者為正式模組），從權限管理清單移除，路由已同步停用。
    # {"key": "hotel_routine_pm_view",              "label": "飯店例行維護",      "group": "飯店管理"},
    {"key": "hotel_calendar_view",                "label": "飯店行事曆",         "group": "飯店管理"},
    {"key": "mall_view",                          "label": "商場模組",          "group": "商場管理"},
    {"key": "mall_overview_view",                 "label": "商場管理 Dashboard","group": "商場管理"},
    {"key": "mall_dashboard_view",                "label": "商場例行維護統計",  "group": "商場管理"},
    {"key": "mall_periodic_maintenance_view",      "label": "商場週期保養",      "group": "商場管理"},
    {"key": "mall_full_building_maintenance_view", "label": "全棟例行維護",      "group": "商場管理"},
    {"key": "mall_facility_inspection_view",       "label": "商場工務巡檢",      "group": "商場管理"},
    {"key": "mall_full_building_inspection_view",  "label": "整棟巡檢",          "group": "商場管理"},
    {"key": "mall_other_tasks_view",               "label": "主管交辦／緊急事件","group": "商場管理"},
    {"key": "mall_calendar_view",                  "label": "商場行事曆",         "group": "商場管理"},
    {"key": "luqun_repair_view",        "label": "商場工務報修",  "group": "工務報修"},
    {"key": "dazhi_repair_view",        "label": "大直工務部",    "group": "工務報修"},
    {"key": "security_view",            "label": "保全模組",      "group": "保全管理"},
    {"key": "security_dashboard_view",  "label": "保全巡檢統計",  "group": "保全管理"},
    {"key": "security_patrol_view",     "label": "保全巡檢記錄",  "group": "保全管理"},
    {"key": "schedule_view",            "label": "查看班表",               "group": "班表管理"},
    {"key": "schedule_manage",          "label": "管理班表（匯入/編輯）",   "group": "班表管理"},
    {"key": "schedule_admin",           "label": "班表管理員（人員/班別）", "group": "班表管理"},
    {"key": "approvals_view",           "label": "簽核查看",      "group": "協作工具"},
    {"key": "approvals_manage",         "label": "簽核新增/管理", "group": "協作工具"},
    {"key": "memos_view",               "label": "公告查看",      "group": "協作工具"},
    {"key": "memos_manage",             "label": "公告新增/管理", "group": "協作工具"},
    {"key": "budget_view",              "label": "預算查看",      "group": "財務"},
    {"key": "budget_manage",            "label": "預算管理",      "group": "財務"},
    {"key": "budget_admin",             "label": "預算設定",      "group": "財務"},
    {"key": "employee_manual_export_view",     "label": "員工操作手冊：查看",   "group": "系統設定"},
    {"key": "employee_manual_export_generate", "label": "員工操作手冊：產生",   "group": "系統設定"},
    {"key": "employee_manual_export_admin",    "label": "員工操作手冊：管理員", "group": "系統設定"},
    {"key": "purchase_report_view",   "label": "請購單報表：查看",   "group": "採購管理"},
    {"key": "purchase_report_manage", "label": "請購單報表：管理",   "group": "採購管理"},
    {"key": "claim_report_view",      "label": "請款單報表：查看",   "group": "採購管理"},
    {"key": "claim_report_manage",    "label": "請款單報表：管理",   "group": "採購管理"},
    {"key": "nichiyo_purchase.view",   "label": "日曜請購月報表：查看",   "group": "採購管理"},
    {"key": "nichiyo_purchase.export", "label": "日曜請購月報表：匯出",   "group": "採購管理"},
    {"key": "nichiyo_purchase.admin",  "label": "日曜請購月報表：管理員", "group": "採購管理"},
    {"key": "nichiyo_claim.view",      "label": "日曜請款月報表：查看",   "group": "採購管理"},
    {"key": "nichiyo_claim.export",    "label": "日曜請款月報表：匯出",   "group": "採購管理"},
    {"key": "nichiyo_claim.admin",     "label": "日曜請款月報表：管理員", "group": "採購管理"},
    {"key": "ragic_field_audit_view",   "label": "Ragic 欄位比對：查看",     "group": "系統設定"},
    {"key": "ragic_field_audit_manage", "label": "Ragic 欄位比對：執行/標記","group": "系統設定"},
    {"key": "ragic_field_audit_admin",  "label": "Ragic 欄位比對：管理員",   "group": "系統設定"},
    {"key": "repair_unfinished_report_view",   "label": "報修未完成報表",         "group": "系統設定"},
    {"key": "repair_unfinished_report_manage", "label": "報修未完成報表：管理",   "group": "系統設定"},
    {"key": "repair_unfinished_report_admin",  "label": "報修未完成報表：管理員", "group": "系統設定"},
    {"key": "hotel_overview_ppt_export", "label": "飯店 Dashboard 匯出 PowerPoint", "group": "飯店管理"},
    {"key": "hotel_overview_ppt_config", "label": "飯店 Dashboard PPT 匯出設定",    "group": "飯店管理"},
    {"key": "contract_view",          "label": "合約清單",       "group": "合約管理"},
    {"key": "contract_create_edit",   "label": "合約新增/編輯", "group": "合約管理"},
    {"key": "contract_vendor_manage", "label": "廠商管理",       "group": "合約管理"},
    {"key": "contract_admin",         "label": "合約設定",       "group": "合約管理"},
    {"key": "contract_expiring_view", "label": "到期預警",       "group": "合約管理"},
    {"key": "contract_claims_view",   "label": "請款管理",       "group": "合約管理"},
    # 2026-07-21：「續約管理」（contract_renewals_view）已隨「續約申請」功能隱藏而移除，
    # 改為「原合約複製續約」（沿用 contract_create_edit 權限，無需獨立權限）。
    {"key": "contract_approve",       "label": "合約審核",       "group": "合約管理"},
    # ── 週期採購（獨立資料庫 cycle-purchase.db，2026-07-10 新增）──────────────
    {"key": "cycle_purchase_view",     "label": "週期採購管理",       "group": "週期採購"},
    {"key": "cycle_purchase_request",  "label": "週期採購請購",       "group": "週期採購"},
    # 2026-07-17：拿掉送出／簽核流程，cycle_purchase_approve 停用，改成獨立的
    # 「關閉」權限（關閉當月請購單、重新開啟已關閉的請購單）。
    {"key": "cycle_purchase_close",    "label": "週期採購請購關閉",   "group": "週期採購"},
    {"key": "cycle_purchase_buyer",    "label": "週期採購彙整／採購", "group": "週期採購"},
    {"key": "cycle_purchase_receive",  "label": "週期採購驗收",       "group": "週期採購"},
    {"key": "cycle_purchase_finance",  "label": "週期採購請款",       "group": "週期採購"},
    {"key": "cycle_purchase_report",   "label": "週期採購報表",       "group": "週期採購"},
    {"key": "cycle_purchase_admin",    "label": "週期採購管理設定",   "group": "週期採購"},
    # ── AI 助理 ──────────────────────────────────────────────────────────────
    # 開發期間預設不分配給任何角色（需手動在「角色管理→權限設定」中開放）
    # 注意：擁有 dazhi_repair_view 或 luqun_repair_view 的角色也可查詢對應地點
    {"key": "ai_workorder_view", "label": "AI 工單查詢助理", "group": "AI 功能"},
    # ── 營運分析（OPERA，2026-08-04 新增）──────────────────────────────────────
    # Portal 首個「檔案上傳型」資料模組：資料來自人工上傳的 OPERA TXT，非 Ragic 同步。
    # ⚠️ 下列 label 必須與 frontend/src/constants/navLabels.ts 的 NAV_PAGE 完全一致，
    #    否則管理員在「權限設定」看到的名稱會與側邊欄不同（CLAUDE.md label 一致性規則）。
    {"key": "opera_view",         "label": "★ 營運分析 Dashboard", "group": "營運分析"},
    {"key": "opera_revenue_view", "label": "營收分析",             "group": "營運分析"},
    {"key": "opera_guest_view",   "label": "住客與通路分析",       "group": "營運分析"},
    {"key": "opera_import",       "label": "資料匯入",             "group": "營運分析"},
    {"key": "opera_admin",        "label": "分析門檻設定",         "group": "營運分析"},
    # ── 房價預測（2026-08-05 新增）────────────────────────────────────────────
    # 「歷史同期查詢」刻意不另開 key，共用 opera_view：它是純查歷史事實的唯讀頁，
    # 與 Dashboard 同性質，另開 key 只會讓權限清單變長而沒有實質區隔。
    # 「事件月曆」則另開 key（不共用 opera_admin），因為權限清單是管理員唯一看得到
    # 「自己在授權什麼」的地方，掛在「分析門檻設定」底下會授權到名不符實的頁面。
    # 註：估算／覆寫模型係數仍歸 opera_admin（與門檻設定同屬模型參數維護）。
    {"key": "opera_forecast_view", "label": "房價預測",             "group": "營運分析"},
    # 市場區隔／房型趨勢（2026-08-07）：另開 key 而不共用 opera_revenue_view，
    # 因為這一頁的**資料來源是 OHIP API 落地**、不是 TXT 上傳，兩者口徑尚未完全對齊。
    # 共用 key 會讓管理員以為授權的是同一份資料。
    # ⚠️ label 必須與 navLabels.ts 的 operaSegments 完全一致（CLAUDE.md §3）。
    {"key": "opera_segment_view",  "label": "市場區隔分析",         "group": "營運分析"},
    # 訂房分析（2026-08-07）：另開 key 而不共用 opera_guest_view，
    # 因為**分析母體不同** —— 這裡是所有訂房（含未來、含取消），
    # 那裡是已離店的住客。共用會讓管理員以為授權的是同一份資料。
    # ⚠️ label 必須與 navLabels.ts 的 operaReservations 完全一致（CLAUDE.md §3）。
    {"key": "opera_reservation_view", "label": "訂房分析",           "group": "營運分析"},
    # 2026-08-05 起「事件月曆」是房價預測頁的一個 TAB，不再是獨立頁面。
    # 此 key 仍然有效，控管的是 TAB 內的新增／修改／刪除／學習係數（API 層強制），
    # 清單本身唯讀，有 opera_forecast_view 就看得到。
    {"key": "opera_event_admin",   "label": "事件月曆",             "group": "營運分析"},
    # ── 即時營運（2026-08-06 新增）────────────────────────────────────────────
    # 資料直接來自 OPERA Cloud（OHIP）REST API，**不是**上傳的 TXT。
    # 刻意獨立成一級選單與獨立權限群組：兩者資料時點不同，共用權限會讓管理員
    # 以為授權的是同一份資料。規格書：docs/SPEC_realtime_operations.md §10.1
    # ⚠️ 下列 label 必須與 frontend/src/constants/navLabels.ts 的 NAV_PAGE 完全一致。
    # ⚠️ 每次查詢都會實際呼叫 OHIP（按量計費），預設不給任何既有角色，需逐一開放。
    {"key": "realtime_view",      "label": "即時營運看板",         "group": "即時營運"},
    # 營收另開 key：走非同步 API，延遲高、會切段，用量比即時房況大。
    {"key": "realtime_revenue",   "label": "營收與結構分析",       "group": "即時營運"},
    # 比對另開 key：不走快取，每次實際呼叫兩支 API。
    {"key": "realtime_compare",   "label": "與營運分析比對",       "group": "即時營運"},
    # ── 金旭分析（2026-08-05 新增）────────────────────────────────────────────
    # Portal 第二個「檔案上傳型」資料模組：資料來自人工上傳的金旭 xlsx
    # （FCR02 客帳帳目明細表 + 訂房狀況表），非 Ragic 同步。
    # 路由前綴 /jinxu/*，與 /opera/* 完全獨立，不共用端點或資料表（業主指定）。
    # ⚠️ 下列 label 必須與 frontend/src/constants/navLabels.ts 的 NAV_PAGE 完全一致。
    # ⚠️ 金額與房價屬財務敏感資料，這些 key 預設不給任何既有角色，需管理員逐一開放。
    {"key": "jinxu_view",         "label": "★ 金旭分析 Dashboard", "group": "金旭分析"},
    {"key": "jinxu_resv_view",    "label": "訂房與通路分析",       "group": "金旭分析"},
    {"key": "jinxu_revenue_view", "label": "收入結構分析",         "group": "金旭分析"},
    {"key": "jinxu_payment_view", "label": "付款方式分析",         "group": "金旭分析"},
    {"key": "jinxu_deposit_view", "label": "預收訂金追蹤",         "group": "金旭分析"},
    {"key": "jinxu_import",       "label": "資料匯入",             "group": "金旭分析"},
    {"key": "jinxu_admin",        "label": "科目與門檻設定",       "group": "金旭分析"},
    # 取消分析與訂價落差另立 key —— 這兩者暴露「業務績效」與「價格執行」資訊，
    # 敏感度高於一般訂房統計。它對應的是 /jinxu/reservation 頁的兩個 TAB 而非獨立
    # 路由，因此 MainLayout.tsx 不會出現這個 permissionKey，但仍必須登錄於此，
    # 否則管理員無從授權（CLAUDE.md permissionKey 一致性規則的反向情況）。
    {"key": "jinxu_cancel_view",  "label": "取消與訂價落差分析",   "group": "金旭分析"},
]


class PermissionKeyDef(BaseModel):
    key: str
    label: str
    group: str


class RolePermissionsOut(BaseModel):
    role_id: str
    role_name: str
    permissions: list[str]


class RolePermissionsSaveRequest(BaseModel):
    permissions: list[str]


class RoleOut(BaseModel):
    id: str
    name: str
    scope: Optional[str] = None
    description: Optional[str] = None


@router.get("/keys", response_model=list[PermissionKeyDef])
def list_permission_keys(
    _: User = Depends(is_system_admin),
):
    """取得系統所有已知的 permission_key 定義（用於 Roles 頁面 checkbox 清單）"""
    return [PermissionKeyDef(**d) for d in PERMISSION_DEFINITIONS]


@router.get("/{role_id}", response_model=RolePermissionsOut)
def get_role_permissions(
    role_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(is_system_admin),
):
    """取得指定角色的 permission_key 清單"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    perms = (
        db.query(RolePermission.permission_key)
        .filter(RolePermission.role_id == role_id)
        .all()
    )
    return RolePermissionsOut(
        role_id=role_id,
        role_name=role.name,
        permissions=[p[0] for p in perms],
    )


@router.put("/{role_id}", response_model=RolePermissionsOut)
def save_role_permissions(
    role_id: str,
    payload: RolePermissionsSaveRequest,
    db: Session = Depends(get_db),
    _: User = Depends(is_system_admin),
):
    """
    覆寫指定角色的 permission_key 清單（完全取代）。
    system_admin 角色固定為萬用符（*），不允許個別設定。
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    if role.name == "system_admin":
        raise HTTPException(
            status_code=400,
            detail="system_admin 擁有所有權限，無需個別設定",
        )

    valid_keys = {d["key"] for d in PERMISSION_DEFINITIONS}
    invalid = [k for k in payload.permissions if k not in valid_keys]
    if invalid:
        joined = ", ".join(invalid)
        raise HTTPException(
            status_code=422,
            detail=f"無效的 permission_key：{joined}",
        )

    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
    for key in set(payload.permissions):
        db.add(RolePermission(role_id=role_id, permission_key=key))
    db.commit()

    perms = (
        db.query(RolePermission.permission_key)
        .filter(RolePermission.role_id == role_id)
        .all()
    )
    return RolePermissionsOut(
        role_id=role_id,
        role_name=role.name,
        permissions=[p[0] for p in perms],
    )
