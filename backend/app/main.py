"""
集團 Portal — FastAPI Application Entry Point
"""

import asyncio
import logging
import pathlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from datetime import datetime

# ── 檔案 Log（每次啟動建立一個新檔，檔名為啟動時間）────────────────────────────
def _setup_file_logging() -> None:
    """
    在 portal/logs/ 目錄下建立以啟動時間命名的 log 檔案。
    格式：YYYYMMDD_HHMMSS.log（台灣時間）
    """
    from app.core.time import twnow

    log_dir = pathlib.Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_filename = twnow().strftime("%Y%m%d_%H%M%S") + ".log"
    log_path = log_dir / log_filename

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger = logging.getLogger()
    if root_logger.level == logging.NOTSET:
        root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    # 確保 SQLAlchemy SQL 語句（INSERT/UPDATE/DELETE/SELECT）寫入 log 檔
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

    print(f"[Portal] Log 檔案：{log_path}")


_setup_file_logging()

from app.core.config import settings
from app.core.database import Base, engine
from app.core.scheduler import make_cron_trigger, scheduler as _scheduler, register_connection_job
from app.core.time import twnow
from app.routers import (
    approvals,
    claim_report,
    combined_report,
    purchase_report,
    schedule,
    mall_schedule,
    auth,
    budget,
    b4f_inspection,
    rf_inspection,
    b2f_inspection,
    b1f_inspection,
    calendar,
    dazhi_repair,
    hotel_daily_inspection,
    hotel_meter_readings,
    hotel_overview,
    ihg_room_maintenance,
    knowledge_graph,
    mall_dashboard,
    mall_facility_inspection,
    full_building_inspection,
    mall_periodic_maintenance,
    full_building_maintenance,
    menu_config,
    memos,
    uploads,
    dashboard,
    inventory,
    luqun_repair,
    periodic_maintenance,
    # 2026-07-14：hotel_routine_pm 安全下線（與 hotel/periodic-maintenance 為重複模組，
    # 使用者確認 hotel/periodic-maintenance 才是正式模組）。import 保留，僅下方
    # include_router／排程註冊被停用，程式檔案與 DB 表格未刪除，可隨時回溯。
    hotel_routine_pm,
    ragic,
    role_permissions,
    site_config,
    roles,
    room_maintenance,
    room_maintenance_detail,
    security_patrol,
    security_dashboard,
    tenants,
    users,
    work_category_analysis,
    mall_overview,
    wiki,
    employee_manual_export,
    work_journal,
    nichiyo_purchase_report,
    nichiyo_claim_report,
    ragic_sheet_config,
    ragic_field_audit,
    static_pages,
    other_tasks,
    repair_report,
    usage_stats,
    hotel_ppt_export,
    repair_ppt_export,
    contract,
    reference_data,
    tutorial_videos,
    opera_import,
    opera_revenue,
    opera_guest,
    opera_forecast,
    opera_segment,
    opera_reservation,
    opera_pace,
    realtime,
    jinxu_import,
    jinxu_revenue,
    jinxu_payment,
    jinxu_deposit,
    jinxu_reservation,
    jinxu_settings,
    # OTA 口碑分析（2026-08-21）：外部網站擷取型模組，非 Ragic、非上傳型。
    # ⚠️ 只加下方的 include_router 而漏掉這裡會直接 NameError。
    ota_reviews,
    ota_stats,
    ota_admin,
    cycle_purchase_masters,
    cycle_purchase_items,
    cycle_purchase_cycles,
    cycle_purchase_requests,
    cycle_purchase_summary,
    cycle_purchase_po,
    cycle_purchase_receiving,
    cycle_purchase_payment,
    cycle_purchase_audit,
    version,
)


# ⚠️⚠️ **不要再新增 `_migrate_*` 函式。**（2026-08-28 Phase 0 起）
#    schema 變更一律走 Alembic：
#        1. 改 app/models/*.py
#        2. cd backend && alembic revision --autogenerate -m "說明"
#           （週期採購庫加 -c alembic_cp.ini）
#        3. 檢查產出的版本檔內容
#        4. alembic upgrade head
#    原本這裡有 30 個手寫的 `_migrate_*`（863 行、33 處 PRAGMA table_info），
#    已於 2026-08-28 移除。它們全部是給「既有資料庫」補欄位的 patch，
#    而那些欄位本來就宣告在 Model 裡 —— 全新資料庫用 create_all() /
#    alembic upgrade head 直接就是正確結構。
#    需要看舊實作：git show <commit>:backend/app/main.py
#
#    ⚠️ 本函式**保留**，因為 _seed_* / _cleanup_* / create_all 仍在用它。


def _run_startup_migration(name: str, fn) -> None:
    """
    執行單一啟動時 migration，遇到 SQLite "database is locked" 時重試而非讓整個
    應用程式啟動失敗。

    2026-07-14 新增：使用者回報 sync_tool.py 手動觸發同步進行中時，若同時重啟
    後端，啟動時 migration 的回填 UPDATE 會因 SQLite 寫入鎖定逾時
    （已設定 60s busy_timeout，仍可能因 sync 本身是長交易而超過）直接拋出
    OperationalError，導致 lifespan() 啟動失敗、整台後端無法啟動（見
    "Application startup failed. Exiting."）。單一 migration 的暫時性鎖定
    不應該讓整個服務起不來，因此所有啟動時 migration 一律透過本函式呼叫，
    遇到鎖定就短暫等待後重試；重試多次仍失敗則記錄警告、略過本次啟動的
    這一項 migration（皆為自我修復型 schema/回填 patch，下次啟動仍會再檢查
    一次，並非只有一次機會）。
    """
    import time
    from sqlalchemy.exc import OperationalError

    retries = 5
    delay   = 3.0
    for attempt in range(1, retries + 1):
        try:
            fn()
            return
        except OperationalError as exc:
            if "locked" not in str(exc).lower():
                raise
            if attempt >= retries:
                print(
                    f"[Migration] {name} 因資料庫鎖定重試 {retries} 次仍失敗，"
                    f"略過本次啟動的這項 migration（下次啟動會再檢查一次）：{exc}"
                )
                return
            print(
                f"[Migration] {name} 遇到資料庫鎖定（可能有 sync_tool.py 或排程同步"
                f"正在寫入），{delay}s 後重試（第 {attempt}/{retries} 次）..."
            )
            time.sleep(delay)


def _cleanup_security_patrol_photo_items():
    """
    一次性清除 security_patrol_item 中 item_name 含「拍照」的記錄。
    這些是 Ragic 必填的上傳欄位，非巡檢評分項目，不應計入統計。
    sync 服務已在 _extract_check_items 中排除此類欄位，
    此函式清除歷史遺留資料，重新同步後即永久生效。
    """
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(
            text("DELETE FROM security_patrol_item WHERE item_name LIKE '%拍照%'")
        )
        if result.rowcount > 0:
            conn.commit()
            print(f"[Migration] 保全巡檢拍照項目已清除 {result.rowcount} 筆")


def _seed_builtin_roles():
    """
    確保四個系統內建角色存在於 roles 表（idempotent）。
    採 INSERT OR IGNORE 方式，不覆蓋已有記錄。
    """
    from sqlalchemy import text
    import uuid

    BUILTIN = [
        ("system_admin",    "system", "系統管理員，擁有全部權限"),
        ("tenant_admin",    "tenant", "租戶管理員"),
        ("module_manager",  "tenant", "模組管理員"),
        ("viewer",          "tenant", "一般查看"),
    ]
    with engine.connect() as conn:
        for name, scope, desc in BUILTIN:
            existing = conn.execute(
                text("SELECT id FROM roles WHERE name = :name"), {"name": name}
            ).fetchone()
            if not existing:
                conn.execute(
                    text(
                        "INSERT INTO roles (id, name, scope, description, created_at) "
                        "VALUES (:id, :name, :scope, :desc, datetime('now'))"
                    ),
                    {"id": str(uuid.uuid4()), "name": name, "scope": scope, "desc": desc},
                )
                print(f"[Portal] Built-in role '{name}' created.")
        conn.commit()
    print("[Portal] Built-in roles seed checked.")


def _seed_admin_user():
    """
    確保預設的 admin 用戶存在於資料庫（idempotent）。
    建立流程：
    1. 確保預設 Tenant（code="default"）存在
    2. 確保 admin 用戶存在（email="admin", password="admin1234"）
    3. 確保 admin 用戶擁有 system_admin 角色
    """
    from sqlalchemy import text
    import uuid
    from app.core.security import hash_password

    with engine.connect() as conn:
        # ── 1. 確保預設 Tenant 存在 ───────────────────────────────────────────
        tenant_id = None
        existing_tenant = conn.execute(
            text("SELECT id FROM tenants WHERE code = 'default'")
        ).fetchone()
        if existing_tenant:
            tenant_id = existing_tenant[0]
        else:
            tenant_id = str(uuid.uuid4())
            conn.execute(
                text(
                    "INSERT INTO tenants (id, code, name, type, is_active, created_at, updated_at) "
                    "VALUES (:id, 'default', 'Default Tenant', 'system', 1, datetime('now'), datetime('now'))"
                ),
                {"id": tenant_id},
            )
            print("[Portal] Default tenant created.")

        # ── 2. 確保 admin 用戶存在 ───────────────────────────────────────────
        user_id = None
        existing_user = conn.execute(
            text("SELECT id FROM users WHERE email = 'admin'")
        ).fetchone()
        if existing_user:
            user_id = existing_user[0]
        else:
            user_id = str(uuid.uuid4())
            hashed_password = hash_password("admin1234")
            conn.execute(
                text(
                    "INSERT INTO users (id, tenant_id, email, full_name, hashed_password, is_active, must_change_password, created_at, updated_at) "
                    "VALUES (:id, :tenant_id, 'admin', 'Administrator', :hashed_pwd, 1, 0, datetime('now'), datetime('now'))"
                ),
                {"id": user_id, "tenant_id": tenant_id, "hashed_pwd": hashed_password},
            )
            print("[Portal] Default admin user created.")

        # ── 3. 確保 admin 用戶擁有 system_admin 角色 ──────────────────────────
        existing_role = conn.execute(
            text(
                "SELECT user_roles.id FROM user_roles "
                "JOIN roles ON user_roles.role_id = roles.id "
                "WHERE user_roles.user_id = :user_id AND roles.name = 'system_admin'"
            ),
            {"user_id": user_id},
        ).fetchone()
        if not existing_role:
            role_id = conn.execute(
                text("SELECT id FROM roles WHERE name = 'system_admin'")
            ).fetchone()[0]
            conn.execute(
                text(
                    "INSERT INTO user_roles (id, user_id, role_id, tenant_id, granted_at) "
                    "VALUES (:id, :user_id, :role_id, :tenant_id, datetime('now'))"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "role_id": role_id,
                    "tenant_id": tenant_id,
                },
            )
            print("[Portal] system_admin role assigned to default admin user.")

        conn.commit()
    print("[Portal] Admin user seed checked.")


def _seed_menu_config_mall_pm_group():
    """
    選單設定補丁（2026-04-28）：
    1. 隱藏舊的 custom_1777348120465（商場例行維護舊群組），改由 base mall-pm-group 取代
    2. 為 mall-pm-group 的三個子頁面補齊 DB 記錄（若不存在或 parent_key 有誤）：
       - /mall/dashboard            → sort_order 10
       - /mall/periodic-maintenance → sort_order 20
       - /mall/full-building-maintenance → sort_order 30
    操作冪等：重複執行不會造成重複或錯誤。
    """
    from sqlalchemy import text

    CHILDREN = [
        ("/mall/dashboard",                 10),
        ("/mall/periodic-maintenance",      20),
        ("/mall/full-building-maintenance", 30),
    ]

    with engine.connect() as conn:
        # ── 1. 隱藏舊的 custom_ 群組（商場例行維護舊入口）──────────────────────
        conn.execute(
            text(
                "UPDATE menu_configs SET is_visible = 0 "
                "WHERE menu_key = 'custom_1777348120465' AND is_visible = 1"
            )
        )

        # ── 2. 確保 mall-pm-group 本身有 DB 記錄且為可見 ──────────────────────
        row = conn.execute(
            text("SELECT menu_key FROM menu_configs WHERE menu_key = 'mall-pm-group'")
        ).fetchone()
        if row is None:
            conn.execute(
                text(
                    "INSERT INTO menu_configs (menu_key, parent_key, custom_label, sort_order, is_visible, updated_at, updated_by) "
                    "VALUES ('mall-pm-group', 'mall', NULL, 10, 1, datetime('now'), 'system-seed')"
                )
            )

        # ── 3. 補齊三個子頁面的 DB 記錄（parent_key = mall-pm-group）─────────
        for menu_key, sort_order in CHILDREN:
            existing = conn.execute(
                text("SELECT menu_key, parent_key FROM menu_configs WHERE menu_key = :k"),
                {"k": menu_key},
            ).fetchone()
            if existing is None:
                conn.execute(
                    text(
                        "INSERT INTO menu_configs (menu_key, parent_key, custom_label, sort_order, is_visible, updated_at, updated_by) "
                        "VALUES (:k, 'mall-pm-group', NULL, :o, 1, datetime('now'), 'system-seed')"
                    ),
                    {"k": menu_key, "o": sort_order},
                )
            elif existing[1] != "mall-pm-group":
                # parent_key 不對（可能掛在舊群組下），修正
                conn.execute(
                    text(
                        "UPDATE menu_configs SET parent_key = 'mall-pm-group', sort_order = :o "
                        "WHERE menu_key = :k"
                    ),
                    {"k": menu_key, "o": sort_order},
                )

        conn.commit()
        print("[Portal] menu_config mall-pm-group seed checked.")


def _seed_menu_config_nichiyo_purchase():
    """
    選單設定補丁（2026-05-14）：
    確保 nichiyo-purchase-report 群組及其子頁面在 menu_configs 中有 DB 記錄。
    permission_key = 'nichiyo_purchase.view'（無此權限不顯示）
    操作冪等：重複執行不會造成重複或錯誤。
    """
    from sqlalchemy import text

    CHILDREN = [
        ("/nichiyo-purchase-report/monthly", 10),
    ]

    with engine.connect() as conn:
        # ── 1. 確保父群組有 DB 記錄 ─────────────────────────────────────────
        row = conn.execute(
            text("SELECT menu_key FROM menu_configs WHERE menu_key = 'nichiyo-purchase-report'")
        ).fetchone()
        if row is None:
            conn.execute(
                text(
                    "INSERT INTO menu_configs "
                    "(menu_key, parent_key, custom_label, sort_order, is_visible, permission_key, updated_at, updated_by) "
                    "VALUES ('nichiyo-purchase-report', NULL, NULL, 80, 1, 'nichiyo_purchase.view', datetime('now'), 'system-seed')"
                )
            )

        # ── 2. 補齊子頁面的 DB 記錄 ─────────────────────────────────────────
        for menu_key, sort_order in CHILDREN:
            existing = conn.execute(
                text("SELECT menu_key FROM menu_configs WHERE menu_key = :k"),
                {"k": menu_key},
            ).fetchone()
            if existing is None:
                conn.execute(
                    text(
                        "INSERT INTO menu_configs "
                        "(menu_key, parent_key, custom_label, sort_order, is_visible, permission_key, updated_at, updated_by) "
                        "VALUES (:k, 'nichiyo-purchase-report', NULL, :o, 1, 'nichiyo_purchase.view', datetime('now'), 'system-seed')"
                    ),
                    {"k": menu_key, "o": sort_order},
                )

        conn.commit()
        print("[Portal] menu_config nichiyo-purchase-report seed checked.")


def _seed_menu_config_nichiyo_claim():
    """
    選單設定補丁（2026-05-14）：
    確保 nichiyo-claim-report 群組及其子頁面在 menu_configs 中有 DB 記錄。
    permission_key = 'nichiyo_claim.view'（無此權限不顯示）
    操作冪等：重複執行不會造成重複或錯誤。
    """
    from sqlalchemy import text

    CHILDREN = [
        ("/nichiyo-claim-report/monthly", 10),
    ]

    with engine.connect() as conn:
        # ── 1. 確保父群組有 DB 記錄 ─────────────────────────────────────────
        row = conn.execute(
            text("SELECT menu_key FROM menu_configs WHERE menu_key = 'nichiyo-claim-report'")
        ).fetchone()
        if row is None:
            conn.execute(
                text(
                    "INSERT INTO menu_configs "
                    "(menu_key, parent_key, custom_label, sort_order, is_visible, permission_key, updated_at, updated_by) "
                    "VALUES ('nichiyo-claim-report', NULL, NULL, 85, 1, 'nichiyo_claim.view', datetime('now'), 'system-seed')"
                )
            )

        # ── 2. 補齊子頁面的 DB 記錄 ─────────────────────────────────────────
        for menu_key, sort_order in CHILDREN:
            existing = conn.execute(
                text("SELECT menu_key FROM menu_configs WHERE menu_key = :k"),
                {"k": menu_key},
            ).fetchone()
            if existing is None:
                conn.execute(
                    text(
                        "INSERT INTO menu_configs "
                        "(menu_key, parent_key, custom_label, sort_order, is_visible, permission_key, updated_at, updated_by) "
                        "VALUES (:k, 'nichiyo-claim-report', NULL, :o, 1, 'nichiyo_claim.view', datetime('now'), 'system-seed')"
                    ),
                    {"k": menu_key, "o": sort_order},
                )

        conn.commit()
        print("[Portal] menu_config nichiyo-claim-report seed checked.")


def _reap_ota_stale_running():
    """
    啟動時回收孤兒 `running`（2026-08-24）。

    ⚠️ **不是「把所有 running 都標成 failed」** —— 那是第一直覺，而且是錯的。
       回補是用 `ota_scraper_cli` 跑的，那是獨立行程；後端重啟一次就會把
       一個**正在跑**的 CLI 同步誤判成死掉。
       `reap_stale_running()` 只收「本機 + pid 確實不在」或「超過 90 分鐘」的。
    """
    from app.core.database import SessionLocal
    from app.services.ota_sync_recovery import reap_stale_running

    db = SessionLocal()
    try:
        reaped = reap_stale_running(db)
        if reaped:
            db.commit()
            for r in reaped:
                print(f"[Portal] OTA 回收孤兒同步紀錄 #{r.log_id}"
                      f"（來源 #{r.source_id}）：{r.reason}")
    finally:
        db.close()


def _seed_jinxu():
    """金旭 PMS 分析 — 科目分類對照表與分析門檻種子（冪等）。

    規格書：docs/SPEC_jinxu_analytics.md 附錄 C、§7.9
    """
    from app.core.database import SessionLocal
    from app.services.jinxu_seed import ensure_jinxu_seed

    db = SessionLocal()
    try:
        result = ensure_jinxu_seed(db)
        if result["subjects"] or result["settings"]:
            print(f"[Seed] jinxu: subjects +{result['subjects']}, settings +{result['settings']}")
    finally:
        db.close()


def _seed_reference_data():
    """F1 — 首次啟動時植入公司別 / 部門別初始資料（冪等：若已有資料則跳過）。"""
    from app.models.reference_data import Company  # noqa: F401 (unused — seed uses raw SQL)
    with engine.connect() as conn:
        from sqlalchemy import text
        # ── 公司別 ──────────────────────────────────────────────────────────
        count = conn.execute(text("SELECT COUNT(*) FROM companies")).scalar()
        if count == 0:
            company_names = ["大直", "樂群", "台中", "自由", "總公司"]
            for name in company_names:
                conn.execute(
                    text("INSERT INTO companies (name, is_active, created_at) VALUES (:name, 1, CURRENT_TIMESTAMP)"),
                    {"name": name},
                )
            conn.commit()
            print(f"[Seed] companies: inserted {len(company_names)} records")

        # ── SLA 指標類型（K2）─────────────────────────────────────────────────
        try:
            sla_count = conn.execute(text("SELECT COUNT(*) FROM sla_metric_types")).scalar()
            if sla_count == 0:
                default_types = [
                    ("可用率",   "以百分比衡量服務系統的可用程度（如 99.9%）"),
                    ("回應時間", "系統或服務的平均回應時間"),
                    ("解決時間", "問題從通報到解決所需時間"),
                    ("準時率",   "服務依約準時完成的百分比"),
                    ("自訂",     "其他自訂指標"),
                ]
                for sname, sdesc in default_types:
                    conn.execute(
                        text("INSERT INTO sla_metric_types (name, description, is_active, created_at) "
                             "VALUES (:name, :desc, 1, CURRENT_TIMESTAMP)"),
                        {"name": sname, "desc": sdesc},
                    )
                conn.commit()
                print(f"[Seed] sla_metric_types: inserted {len(default_types)} records")
        except Exception:
            pass  # 資料表尚未建立時靜默跳過（create_all 後再 seed）

        # ── 部門別 ──────────────────────────────────────────────────────────
        dept_count = conn.execute(text("SELECT COUNT(*) FROM departments")).scalar()
        if dept_count == 0:
            dept_names = [
                "管理部", "資訊部", "工程部", "工務部", "財務部",
                "營業部", "採購部", "房務部", "商場部", "客房部",
                "餐飲部", "客服部", "安全部",
            ]
            companies = conn.execute(text("SELECT id FROM companies")).fetchall()
            for company_row in companies:
                cid = company_row[0]
                for dname in dept_names:
                    conn.execute(
                        text(
                            "INSERT INTO departments (name, company_id, is_active, created_at) "
                            "VALUES (:name, :cid, 1, CURRENT_TIMESTAMP)"
                        ),
                        {"name": dname, "cid": cid},
                    )
            conn.commit()
            print(f"[Seed] departments: inserted {len(dept_names)} × {len(companies)} records")


def _utcnow() -> datetime:
    """台灣時間（UTC+8）——名稱保留供現有呼叫端相容，實際回傳台灣時間。"""
    return twnow()


def _parse_sync_result(result: dict) -> tuple[int, int, list[str]]:
    """
    將各 sync_service 不同格式的回傳值統一解析為 (fetched, upserted, errors)。
    支援：
      標準格式    { fetched, upserted, errors }
      巡檢格式    { fetched, upserted, item_rows, errors }
      週期保養    { batches: {fetched, upserted, errors}, items: {...} }
      保全巡檢    { sheet_key: {fetched, upserted, item_rows, errors}, ... }
    """
    if not isinstance(result, dict):
        return 0, 0, []

    # 標準格式
    if "fetched" in result:
        return (
            result.get("fetched", 0),
            result.get("upserted", 0),
            result.get("errors", []),
        )

    # 週期保養格式：{ batches: {...}, items: {...} }
    if "batches" in result and "items" in result:
        b, i = result["batches"], result["items"]
        return (
            b.get("fetched", 0) + i.get("fetched", 0),
            b.get("upserted", 0) + i.get("upserted", 0),
            b.get("errors", []) + i.get("errors", []),
        )

    # IHG 客房保養格式：{ master: {...}, detail: {...} }
    if "master" in result and "detail" in result:
        m, d = result["master"], result["detail"]
        return (
            m.get("fetched", 0) + d.get("fetched", 0),
            m.get("upserted", 0) + d.get("upserted", 0),
            m.get("errors", []) + d.get("errors", []),
        )

    # 保全巡檢格式：{ sheet_key: {...}, ... }
    total_f = sum(v.get("fetched", 0) for v in result.values() if isinstance(v, dict))
    total_u = sum(v.get("upserted", 0) for v in result.values() if isinstance(v, dict))
    errors = [
        e for v in result.values() if isinstance(v, dict) for e in v.get("errors", [])
    ]
    return total_f, total_u, errors


async def _run_and_log(
    module_name: str,
    coro,
    triggered_by: str = "scheduler",
    retry_count: int = 0,
    parent_log_id: int | None = None,
) -> tuple:
    """
    執行 sync coroutine 並將結果寫入 module_sync_log。
    不論成功或失敗都會寫入，確保紀錄完整。

    回傳 (result, log_id, fetched, status)，供 _run_loop() 做驗證決策。
    """
    from app.models.module_sync_log import ModuleSyncLog
    from app.core.database import SessionLocal
    from app.core.sync_lock import async_sync_lock

    started = _utcnow()
    result = None
    exc_str = None

    try:
        # 2026-07-15：跨行程鎖，避免 sync_tool.py 與這裡的排程同時寫入 portal.db
        async with async_sync_lock(module_name):
            result = await coro
    except Exception as exc:
        exc_str = str(exc)

    finished = _utcnow()
    duration = round((finished - started).total_seconds(), 2)

    if exc_str:
        fetched, upserted, errors = 0, 0, [exc_str]
        status = "error"
    else:
        fetched, upserted, errors = _parse_sync_result(result or {})
        status = "success" if not errors else "partial"

    log_id = None
    db = SessionLocal()
    try:
        log = ModuleSyncLog(
            module_name=module_name,
            started_at=started,
            finished_at=finished,
            duration_sec=duration,
            status=status,
            fetched=fetched,
            upserted=upserted,
            errors_count=len(errors),
            error_msg="; ".join(str(e) for e in errors[:3]) if errors else None,
            triggered_by=triggered_by,
            retry_count=retry_count,
            parent_log_id=parent_log_id,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        log_id = log.id
    except Exception as log_exc:
        print(f"[AutoSync][Log] 寫入失敗：{log_exc}")
    finally:
        db.close()

    return result, log_id, fetched, status


# ── Loop Engineering ───────────────────────────────────────────────────────────

_LOOP_MAX_RETRIES = 2
_LOOP_RETRY_DELAYS = [30, 120]   # 秒：第1次重試等30s，第2次等2min
_ANOMALY_MIN_HISTORY = 3         # 至少要有 N 筆歷史才做異常判斷
_ANOMALY_FETCH_THRESHOLD = 5     # 歷史平均 fetched > 此值，現在 fetched=0 才算異常


async def _verify_anomaly(module_name: str, log_id: int, fetched: int) -> None:
    """
    Loop 驗證階段：若本次 fetched=0，但過去 N 次成功同步都有穩定資料量，
    將此筆 log 標記 is_anomaly=True，方便健康監控發現資料消失的問題。
    """
    if fetched > 0 or log_id is None:
        return

    from app.models.module_sync_log import ModuleSyncLog
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        recent = (
            db.query(ModuleSyncLog)
            .filter(
                ModuleSyncLog.module_name == module_name,
                ModuleSyncLog.status == "success",
                ModuleSyncLog.retry_count == 0,   # 只看原始首次嘗試，排除重試
                ModuleSyncLog.id != log_id,
            )
            .order_by(ModuleSyncLog.started_at.desc())
            .limit(_ANOMALY_MIN_HISTORY)
            .all()
        )
        if len(recent) >= _ANOMALY_MIN_HISTORY and all(
            r.fetched > _ANOMALY_FETCH_THRESHOLD for r in recent
        ):
            avg = sum(r.fetched for r in recent) // len(recent)
            log = db.get(ModuleSyncLog, log_id)
            if log:
                log.is_anomaly = True
                db.commit()
                print(
                    f"[Loop][Anomaly] ⚠️  {module_name}：本次 fetched=0，"
                    f"過去 {len(recent)} 次平均 {avg} 筆，標記異常。"
                )
    except Exception as e:
        print(f"[Loop][Anomaly] 異常偵測失敗（{module_name}）：{e}")
    finally:
        db.close()


async def _run_loop(module_name: str, sync_fn, triggered_by: str = "scheduler"):
    """
    Loop Engineering 核心：執行同步並在失敗時自動重試，成功後執行驗證。

    Loop 五階段：
      1. State Check  — 依 retry_count 判斷這是第幾次嘗試
      2. Decision     — 上次失敗才重試，成功直接結束
      3. Execution    — 呼叫 sync_fn() 執行同步
      4. Feedback     — 解析 fetched / status / errors
      5. Verification — 成功時做異常偵測；失敗且未超限則進入下一輪

    sync_fn 必須是可呼叫的 async 函數（不是已經建立的 coroutine），
    因為重試時需要重新呼叫來建立新的 coroutine。
    """
    parent_id: int | None = None

    for attempt in range(_LOOP_MAX_RETRIES + 1):
        # Stage 3: Execution
        _, log_id, fetched, status = await _run_and_log(
            module_name,
            sync_fn(),
            triggered_by,
            retry_count=attempt,
            parent_log_id=parent_id if attempt > 0 else None,
        )

        # 首次嘗試記錄 parent_id，後續重試都指向它
        if attempt == 0:
            parent_id = log_id

        # Stage 5: Verification
        if status == "success":
            await _verify_anomaly(module_name, log_id, fetched)
            break   # 成功，離開 Loop

        # Stage 2: Decision — 是否還有重試額度？
        if attempt < _LOOP_MAX_RETRIES:
            delay = _LOOP_RETRY_DELAYS[attempt]
            print(
                f"[Loop] {module_name} 第 {attempt + 1} 次失敗（{status}），"
                f"{delay}s 後重試…"
            )
            await asyncio.sleep(delay)
        else:
            print(
                f"[Loop] {module_name} 已達最大重試次數（{_LOOP_MAX_RETRIES}），放棄。"
            )


def _init_ragic_connection_jobs() -> None:
    """
    啟動時掃描所有 is_active=True 的 RagicConnection，
    依各自 sync_interval 建立獨立排程任務。
    """
    from app.core.database import SessionLocal
    from app.models.ragic_connection import RagicConnection

    db = SessionLocal()
    try:
        conns = (
            db.query(RagicConnection).filter(RagicConnection.is_active == True).all()
        )
        for conn in conns:
            register_connection_job(conn.id, conn.sync_interval)
        if conns:
            print(
                f"[Portal] RagicConnection scheduler jobs registered: {len(conns)} connections."
            )
    except Exception as exc:
        print(f"[Portal] RagicConnection job init error: {exc}")
    finally:
        db.close()


async def _auto_sync():
    """定時同步任務：Ragic → SQLite（所有硬編碼模組，透過 Loop 自動重試）"""
    from app.services.room_maintenance_sync import sync_from_ragic as sync_rm
    from app.services.inventory_sync import sync_from_ragic as sync_inv
    from app.services.room_maintenance_detail_sync import sync_from_ragic as sync_rmd
    from app.services.periodic_maintenance_sync import sync_from_ragic as sync_pm
    from app.services.b4f_inspection_sync import sync_from_ragic as sync_b4f
    from app.services.rf_inspection_sync import sync_from_ragic as sync_rf
    from app.services.b2f_inspection_sync import sync_from_ragic as sync_b2f
    from app.services.b1f_inspection_sync import sync_from_ragic as sync_b1f
    from app.services.mall_periodic_maintenance_sync import (
        sync_from_ragic as sync_mall_pm,
    )
    from app.services.full_building_maintenance_sync import (
        sync_from_ragic as sync_full_bldg_pm,
    )
    from app.services.dazhi_repair_sync import sync_from_ragic as sync_dazhi
    from app.services.luqun_repair_sync import sync_from_ragic as sync_luqun
    from app.services.security_patrol_sync import sync_all as sync_security
    from app.services.mall_facility_inspection_sync import sync_all as sync_mfi
    from app.services.hotel_daily_inspection_sync import sync_all as sync_hdi
    from app.services.hotel_meter_readings_sync import sync_all as sync_hmr
    from app.services.ihg_room_maintenance_sync import sync_from_ragic as sync_ihg_rm
    from app.services.other_tasks_sync import sync_from_ragic as sync_other_tasks
    from app.services.vendor_sync import sync_from_ragic as sync_vendor
    from app.services.cycle_purchase_vendor_sync import (
        sync_from_contract as sync_cp_vendor,
    )
    from app.services.cycle_purchase_department_sync import (
        sync_from_reference as sync_cp_department,
    )
    from app.services.purchase_request_sync import sync_list_only as sync_purchase_list
    from app.services.claim_request_sync import sync_list_only as sync_claim_list
    from app.services.nichiyo_purchase_request_sync import sync_list_only as sync_nichiyo_purchase_list
    from app.services.nichiyo_claim_request_sync import sync_list_only as sync_nichiyo_claim_list
    # 透過 _run_loop() 執行：失敗自動重試 + 驗證異常偵測
    await _run_loop("客房保養",           sync_rm)
    await _run_loop("倉庫庫存",           sync_inv)
    await _run_loop("客房保養明細",        sync_rmd)
    await _run_loop("飯店週期保養",        sync_pm)
    await _run_loop("B4F巡檢",            sync_b4f)
    await _run_loop("RF巡檢",             sync_rf)
    await _run_loop("B2F巡檢",            sync_b2f)
    await _run_loop("B1F巡檢",            sync_b1f)
    await _run_loop("商場週期保養",        sync_mall_pm)
    await _run_loop("全棟例行維護",        sync_full_bldg_pm)
    await _run_loop("大直工務報修",        sync_dazhi)
    await _run_loop("商場工務報修",        sync_luqun)
    await _run_loop("保全巡檢",           sync_security)
    await _run_loop("商場工務巡檢",        sync_mfi)
    await _run_loop("飯店每日巡檢",        sync_hdi)
    await _run_loop("每日數值登錄",        sync_hmr)
    await _run_loop("IHG客房保養",        sync_ihg_rm)
    await _run_loop("主管交辦／緊急事件",  sync_other_tasks)
    await _run_loop("廠商資料",           sync_vendor)
    # ⚠ 順序相依：來源是 portal.db vendors（上一行剛同步完），不可提前
    await _run_loop("週期採購供應商",      sync_cp_vendor)
    # 來源是 portal.db Company/RefDepartment（系統設定 → 公司/部門管理，非
    # Ragic），跟「週期採購供應商」互不相依，同一批次即可
    await _run_loop("週期採購部門",        sync_cp_department)
    # 請購單 / 請款單：清單同步（Detail API 由獨立排程補全）
    await _run_loop("核准請購單清單",      sync_purchase_list)
    await _run_loop("核准請款單清單",      sync_claim_list)
    await _run_loop("日曜核准請購單清單",  sync_nichiyo_purchase_list)
    await _run_loop("日曜核准請款單清單",  sync_nichiyo_claim_list)


async def _manual_sync():
    """
    「立即同步」專用入口：為本次手動同步建立獨立 log 檔，
    格式 YYYYMMDD_HHMMSS_manual.log，存至 portal/logs/。
    同步完成後自動移除 FileHandler，不影響常駐 log 檔。
    """
    from app.core.time import twnow

    log_dir = pathlib.Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_filename = twnow().strftime("%Y%m%d_%H%M%S") + "_manual.log"
    log_path = log_dir / log_filename

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    # 確保 SQLAlchemy SQL 語句（INSERT/UPDATE/DELETE）寫入此次手動同步 log
    sa_logger = logging.getLogger("sqlalchemy.engine")
    prev_sa_level = sa_logger.level
    sa_logger.setLevel(logging.INFO)

    print(f"[Portal] 立即同步 log 檔：{log_path}")

    try:
        await _auto_sync()
    finally:
        root_logger.removeHandler(handler)
        handler.close()
        # 還原 SQLAlchemy logger level（避免影響後續排程 log）
        sa_logger.setLevel(prev_sa_level)


# ── 請購單專屬排程 ──────────────────────────────────────────────────────────────
# ── 單一模組立即同步 ─────────────────────────────────────────────────────────
_SINGLE_MODULE_MAP: dict[str, tuple[str, str]] = {
    "客房保養":          ("app.services.room_maintenance_sync",         "sync_from_ragic"),
    "倉庫庫存":          ("app.services.inventory_sync",                "sync_from_ragic"),
    "客房保養明細":       ("app.services.room_maintenance_detail_sync",  "sync_from_ragic"),
    "飯店週期保養":       ("app.services.periodic_maintenance_sync",     "sync_from_ragic"),
    "B4F巡檢":          ("app.services.b4f_inspection_sync",            "sync_from_ragic"),
    "RF巡檢":           ("app.services.rf_inspection_sync",             "sync_from_ragic"),
    "B2F巡檢":          ("app.services.b2f_inspection_sync",            "sync_from_ragic"),
    "B1F巡檢":          ("app.services.b1f_inspection_sync",            "sync_from_ragic"),
    "商場週期保養":       ("app.services.mall_periodic_maintenance_sync","sync_from_ragic"),
    "全棟例行維護":       ("app.services.full_building_maintenance_sync","sync_from_ragic"),
    "大直工務報修":       ("app.services.dazhi_repair_sync",             "sync_from_ragic"),
    "商場工務報修":       ("app.services.luqun_repair_sync",             "sync_from_ragic"),
    "保全巡檢":          ("app.services.security_patrol_sync",          "sync_all"),
    "商場工務巡檢":       ("app.services.mall_facility_inspection_sync", "sync_all"),
    "飯店每日巡檢":       ("app.services.hotel_daily_inspection_sync",   "sync_all"),
    "每日數值登錄":       ("app.services.hotel_meter_readings_sync",     "sync_all"),
    "IHG客房保養":       ("app.services.ihg_room_maintenance_sync",     "sync_from_ragic"),
    "核准請購單清單":     ("app.services.purchase_request_sync",         "sync_list_only"),
    "核准請款單清單":     ("app.services.claim_request_sync",            "sync_list_only"),
    "日曜核准請購單清單": ("app.services.nichiyo_purchase_request_sync", "sync_list_only"),
    "日曜核准請款單清單": ("app.services.nichiyo_claim_request_sync",    "sync_list_only"),
    "主管交辦／緊急事件": ("app.services.other_tasks_sync",              "sync_from_ragic"),
    "廠商資料":          ("app.services.vendor_sync",                   "sync_from_ragic"),
    "週期採購供應商":     ("app.services.cycle_purchase_vendor_sync",    "sync_from_contract"),
    "週期採購部門":       ("app.services.cycle_purchase_department_sync", "sync_from_reference"),
}

def list_syncable_modules() -> list[str]:
    return list(_SINGLE_MODULE_MAP.keys())

async def _single_module_sync(module_name: str) -> None:
    import importlib
    entry = _SINGLE_MODULE_MAP.get(module_name)
    if entry is None:
        print(f"[SingleSync] unknown: {module_name}")
        return
    svc, fn_name = entry
    try:
        mod = importlib.import_module(svc)
        await _run_and_log(module_name, getattr(mod, fn_name)(), triggered_by="manual")
    except Exception as exc:
        print(f"[SingleSync] {module_name} failed: {exc}")


async def _purchase_list_sync():
    """請購單清單同步（每 15 分鐘：僅清單 API + subtable 品項）"""
    from app.services.purchase_request_sync import sync_list_only
    await _run_and_log("核准請購單清單", sync_list_only())


async def _purchase_full_sync():
    """請購單完整同步（每 45 分鐘：清單 + Detail API 品項補全）"""
    from app.services.purchase_request_sync import sync_from_ragic as sync_purchase
    await _run_and_log("核准請購單", sync_purchase())


# ── 請款單專屬排程 ──────────────────────────────────────────────────────────────
async def _claim_list_sync():
    """請款單清單同步（每 15 分鐘：僅清單 API + subtable 品項）"""
    from app.services.claim_request_sync import sync_list_only
    await _run_and_log("核准請款單清單", sync_list_only())


async def _claim_full_sync():
    """請款單完整同步（每 45 分鐘：清單 + Detail API 品項補全）"""
    from app.services.claim_request_sync import sync_from_ragic as sync_claim
    await _run_and_log("核准請款單", sync_claim())


# ── 日曜請購單專屬排程 ──────────────────────────────────────────────────────────
async def _nichiyo_purchase_list_sync():
    """日曜請購單清單同步（每 15 分鐘：僅清單 API）"""
    from app.services.nichiyo_purchase_request_sync import sync_list_only
    await _run_and_log("日曜核准請購單清單", sync_list_only())


async def _nichiyo_purchase_full_sync():
    """日曜請購單完整同步（每 45 分鐘：清單 + Detail API 品項補全）"""
    from app.services.nichiyo_purchase_request_sync import sync_all as sync_nichiyo
    await _run_and_log("日曜核准請購單", sync_nichiyo())


# ── 日曜請款單專屬排程 ──────────────────────────────────────────────────────────
async def _nichiyo_claim_list_sync():
    """日曜請款單清單同步（每 15 分鐘：僅清單 API）"""
    from app.services.nichiyo_claim_request_sync import sync_list_only
    await _run_and_log("日曜核准請款單清單", sync_list_only())


async def _nichiyo_claim_full_sync():
    """日曜請款單完整同步（每 45 分鐘：清單 + Detail API 品項補全）"""
    from app.services.nichiyo_claim_request_sync import sync_all as sync_nichiyo_claim
    await _run_and_log("日曜核准請款單", sync_nichiyo_claim())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup / shutdown hooks."""
    # ── Startup ──────────────────────────────────────────────────────────────
    print(f"[Portal] Starting — environment: {settings.ENV}")

    # 確保所有 ORM model 已被 import，讓 Base.metadata 知道所有表格
    import app.models.system_setting  # noqa: F401  站台基本設定（key-value）
    import app.models.room_maintenance  # noqa: F401
    import app.models.inventory  # noqa: F401
    import app.models.room_maintenance_detail  # noqa: F401
    import app.models.room  # noqa: F401
    import app.models.periodic_maintenance  # noqa: F401
    import app.models.pm_schedule  # noqa: F401
    import app.models.mall_pm_schedule  # noqa: F401
    import app.models.mall_periodic_maintenance  # noqa: F401
    import app.models.full_building_maintenance  # noqa: F401
    import app.models.full_bldg_pm_schedule  # noqa: F401
    import app.models.b4f_inspection  # noqa: F401
    import app.models.rf_inspection  # noqa: F401
    import app.models.b2f_inspection  # noqa: F401
    import app.models.b1f_inspection  # noqa: F401
    import app.models.security_patrol  # noqa: F401
    import app.models.approval  # noqa: F401
    import app.models.memo  # noqa: F401
    import app.models.memo_file  # noqa: F401
    import app.models.calendar_event  # noqa: F401
    import app.models.dazhi_repair  # noqa: F401
    import app.models.luqun_repair  # noqa: F401
    import app.models.module_sync_log  # noqa: F401
    import app.models.repair_report  # noqa: F401
    import app.models.ragic_app_directory  # noqa: F401
    import app.models.mall_facility_inspection  # noqa: F401
    import app.models.hotel_daily_inspection  # noqa: F401
    import app.models.hotel_meter_readings   # noqa: F401
    import app.models.ihg_room_maintenance   # noqa: F401
    import app.models.menu_config  # noqa: F401
    import app.models.role_permission  # noqa: F401
    import app.models.wiki  # noqa: F401
    import app.models.purchase_request  # noqa: F401
    import app.models.claim_request     # noqa: F401
    import app.models.nichiyo_purchase_request  # noqa: F401
    import app.models.nichiyo_claim_request     # noqa: F401
    import app.models.ragic_sheet_config        # noqa: F401
    import app.models.other_tasks               # noqa: F401
    import app.models.pm_plan                   # noqa: F401  週期保養預排（主管排定 Sheet /7 /13 /20）
    import app.models.schedule                  # noqa: F401  飯店班表模組（本地 SQLite，不對接 Ragic）
    import app.models.mall_schedule             # noqa: F401  商場班表模組（本地 SQLite，不對接 Ragic）
    import app.models.api_access_log            # noqa: F401  使用監控日誌
    import app.models.ppt_export_config        # noqa: F401  PPT 匯出設定
    import app.models.ppt_export_history       # noqa: F401  PPT 匯出歷史紀錄
    import app.models.contract                 # noqa: F401  合約管理（含 ContractClaim + H1~H4 新表）
    import app.models.hotel_routine_pm         # noqa: F401  飯店例行維護（Sheet 11 平表，含維修工時）
    import app.models.hotel_routine_pm_schedule  # noqa: F401  飯店例行維護排程
    import app.models.tutorial_video_module    # noqa: F401  影音教學模組主檔（本地模組，不對接 Ragic）
    import app.models.tutorial_video           # noqa: F401  影音教學單集（本地模組，不對接 Ragic）
    # OPERA 營運分析（2026-08-04）：資料來自人工上傳的 OPERA TXT，非 Ragic 同步，
    # 因此不需登錄 sync_tool.py 的 MODULES／_ensure_db_schema()。
    # 索引另由專案根目錄的 add_opera_tables.sql 建立（create_all 不會產生複合索引）。
    import app.models.opera_import             # noqa: F401  匯入批次與錯誤紀錄
    import app.models.opera_departure          # noqa: F401  Departure 原始層 + 住宿事實表
    import app.models.opera_revenue            # noqa: F401  History/Forecast 原始層 + 每日營收 + 門檻設定
    # 房價預測（2026-08-05）：索引另由 add_opera_forecast_tables.sql 建立。
    import app.models.opera_forecast           # noqa: F401  事件月曆 + 係數 + 預測快照
    # 市場區隔／房型別歷史營收（2026-08-07）：⚠️ 資料來源是 **OHIP API 落地**，
    # 不是 TXT 上傳。放在 opera_* 命名下是因為頁面歸屬「營運分析」，
    # 但**不與 `opera_revenue_daily` 共用任何欄位**（粒度、來源、口徑都不同）。
    # 複合索引寫在 Model `__table_args__`，create_all 一併建立，不需手動跑 SQL。
    import app.models.opera_segment           # noqa: F401  ohip_revenue_history + 同步紀錄
    # 訂房分析（2026-08-07）：來源 OHIP rsvasync／blkasync。
    # ⚠️ 母體與 opera_departure（TXT）**不同** —— 這裡是所有訂房（含未來、含取消），
    #    那裡是已離店的住客。同維度數字不同是正常的，不是 bug。
    import app.models.opera_reservation       # noqa: F401  訂房＋逐日＋團體 block
    # 即時營運（2026-08-06）：只存 OHIP 呼叫日誌與 API 回應快取，**不存業務資料**。
    # 2026-08-07 新增 `ohip_async_cache`：非同步端點的回應快取。Oracle 規定相同參數的
    # async 請求最短間隔 30 分鐘，記憶體快取擋不住（重啟即失效），必須落地。
    # 刪光這張表只會多打一次 API，不會遺失任何事實，因此不牴觸「不存業務資料」原則。
    # 2026-08-07 再新增三張**每日快照**表（`ohip_snapshot_run` / `ohip_inventory_snapshot`
    # / `ohip_revenue_snapshot`）。⚠️ 這三張與上面兩張性質不同：
    # 上面兩張刪光只會多打一次 API，**這三張刪掉就是永久遺失、無法重建**，
    # 因為 OHIP 沒有「回到過去」的參數。備份策略要涵蓋它們。
    # 複合索引已寫在 Model 的 `__table_args__`，create_all 會一併建立，**不需要手動跑 SQL**。
    import app.models.realtime                 # noqa: F401  OHIP 呼叫日誌 + async 快取 + 每日快照
    # 金旭 PMS 分析（2026-08-05）：Portal 第二個檔案上傳型模組，資料來自人工上傳的
    # 金旭 xlsx（FCR02 客帳帳目明細表 + 訂房狀況表），非 Ragic 同步，因此同樣不需
    # 登錄 sync_tool.py 的 MODULES／_ensure_db_schema()。
    # 索引另由專案根目錄的 add_jinxu_tables.sql 建立（create_all 不會產生複合索引）。
    import app.models.jinxu_import             # noqa: F401  匯入批次與錯誤紀錄
    import app.models.jinxu_ledger             # noqa: F401  FCR02 原始層 + 交易分錄 + 科目對照
    import app.models.jinxu_reservation        # noqa: F401  訂房原始層 + 訂房事實表 + 住宿明細段
    import app.models.jinxu_setting            # noqa: F401  分析門檻設定

    # OTA 口碑分析（2026-08-21）：資料來自 Booking／Expedia／Tripadvisor 的公開評論頁。
    # 規格書 docs/SPEC_ota_reviews.md；建表 SQL docs/add_ota_tables.sql（供既有 DB 補建）。
    # ⚠️ 本模組**有排程**（P2 起），因此與純上傳型的 opera_import／jinxu_* 不同，
    #    必須登錄 sync_tool.py 的 MODULES 與 _ensure_db_schema()（規格書 §10.0）。
    #    否則 SCHEDULER_ENABLED=false 的機器上等於從未執行 —— 2026-08-13 OHIP
    #    那四個排程就是這樣停在 6/24 沒人發現的。
    import app.models.ota_review               # noqa: F401  來源／評論／同步紀錄／主題字典／AI 快取


    # 建立尚未存在的資料表（不影響已有表格）
    # 2026-07-16：套用 _run_startup_migration 重試保護（見該函式 docstring）——
    # 避免後端啟動時剛好撞上 sync_tool.py 寫入中的 SQLite 鎖定，就讓整個服務起不來。
    _run_startup_migration("_create_all_tables", lambda: Base.metadata.create_all(bind=engine))
    print("[Portal] Database tables ensured.")

    _run_startup_migration("_reap_ota_stale_running", _reap_ota_stale_running)

    # ── 週期採購（獨立資料庫 cycle-purchase.db，2026-07-10 決策：不與 portal.db 共用）──
    from app.core.cycle_purchase_database import CyclePurchaseBase, cycle_purchase_engine
    import app.models.cycle_purchase_vendor      # noqa: F401
    import app.models.cycle_purchase_reference   # noqa: F401
    import app.models.cycle_purchase_item        # noqa: F401
    import app.models.cycle_purchase_category    # noqa: F401
    import app.models.cycle_purchase_cycle       # noqa: F401
    import app.models.cycle_purchase_request     # noqa: F401
    import app.models.cycle_purchase_summary     # noqa: F401
    import app.models.cycle_purchase_po          # noqa: F401
    import app.models.cycle_purchase_receiving   # noqa: F401
    import app.models.cycle_purchase_payment      # noqa: F401
    import app.models.cycle_purchase_audit        # noqa: F401
    # 2026-07-16：同樣套用重試保護，理由同上（_create_all_tables）。
    _run_startup_migration(
        "_create_cycle_purchase_tables",
        lambda: CyclePurchaseBase.metadata.create_all(bind=cycle_purchase_engine),
    )
    print("[Portal] Cycle-purchase database tables ensured (cycle-purchase.db).")


    # 週期採購：系統自動關閉「期別已過」的請購單（2026-08-07，與 Samuel 確認）。
    # 啟動時先跑一次，之後由下方 SCHEDULER_ENABLED 區塊的每日排程接手。
    # 這支是冪等的（同月份共用一個 CPAUTO 批次號、跳過已關閉與被人工重新開啟的單），
    # 重複執行不會有副作用，所以啟動與排程各跑一次是安全的。
    # 用 _run_startup_migration 包起來的理由與上面建表相同：SQLite 暫時性鎖定時
    # 可以重試，不會讓整個服務起不來。
    def _auto_close_expired_cp_requests():
        from app.core.cycle_purchase_database import CyclePurchaseSessionLocal
        from app.services import cycle_purchase_request_service as _cp_req_svc

        db = CyclePurchaseSessionLocal()
        try:
            closed = _cp_req_svc.auto_close_expired_requests(db)
            db.commit()
            if closed:
                print(f"[Portal] Cycle-purchase: auto-closed {len(closed)} expired request(s).")
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    _run_startup_migration("_auto_close_expired_cp_requests", _auto_close_expired_cp_requests)

    # 影音教學 Migration：舊版 tutorial_videos 直接存 category/module_name/module_route，
    # 新版改為獨立的 tutorial_video_modules 主檔（module_id 關聯），此處把既有資料搬過去
    from sqlalchemy import text as _tv_text
    import uuid as _tv_uuid


    # PPT 匯出設定 Migration：為已存在的 ppt_export_configs 表補充新欄位
    from sqlalchemy import text as _ppt_text


    # users 表：補充忘記密碼 / OTP 欄位（2026-05-25）
    from sqlalchemy import text as _user_text


    # module_sync_log 表：補充 Loop Engineering 欄位（2026-06-17）
    from sqlalchemy import text as _loop_text


    # 報修未完成報表：確保預設排程設定存在（is_enabled=False，不會自動寄信）
    from app.core.database import SessionLocal as _RepairSessionLocal
    from app.services.repair_report_service import ensure_default_schedule as _ensure_repair_sched

    def _check_repair_report_schedule():
        with _RepairSessionLocal() as _repair_db:
            _ensure_repair_sched(_repair_db)

    _run_startup_migration("_check_repair_report_schedule", _check_repair_report_schedule)
    print("[Portal] Repair report schedule settings checked.")

    # 內建角色 seed（system_admin / tenant_admin / module_manager / viewer）
    _run_startup_migration("_seed_builtin_roles", _seed_builtin_roles)

    # 預設 admin 用戶 seed（email: admin, password: admin1234）
    _run_startup_migration("_seed_admin_user", _seed_admin_user)

    # Ragic Sheet 設定 seed（各模組各部門的 list_path / detail_path）
    from app.services.ragic_sheet_config_service import seed_ragic_sheet_config
    _run_startup_migration("seed_ragic_sheet_config", seed_ragic_sheet_config)

    # SQLite WAL 模式：讓讀取與寫入可同時進行（OneDrive 環境必要）
    from sqlalchemy import text as _sql_text
    try:
        with engine.connect() as _c:
            _c.execute(_sql_text("PRAGMA journal_mode=WAL"))
            _c.execute(_sql_text("PRAGMA busy_timeout=30000"))   # 30 秒等待鎖
            _c.execute(_sql_text("PRAGMA synchronous=NORMAL"))
            _c.commit()
        print("[Portal] SQLite WAL mode enabled.")
    except Exception as _e:
        print(f"[Portal] WAL mode setup skipped: {_e}")


    # 清除保全巡檢中的拍照欄位 item（Ragic 必填但不屬於巡檢評分項目）
    # 2026-07-16：這是這次「Application startup failed」出包的元凶——原本沒有
    # 套用 _run_startup_migration 重試保護，遇到 sync_tool.py 寫入中造成的
    # database is locked 就直接讓整個後端啟動失敗。改用同樣的保護機制。
    _run_startup_migration("_cleanup_security_patrol_photo_items", _cleanup_security_patrol_photo_items)
    print("[Portal] Security patrol photo items cleanup checked.")


    # contract_attachments 資料表已由 app.models.contract import + create_all 自動建立

    # F1（2026-06-01）：基礎參考資料種子（公司別 / 部門別 / 計價規格）
    import app.models.reference_data  # noqa: F401 — 確保 create_all 建立資料表
    _run_startup_migration("_seed_reference_data", _seed_reference_data)
    print("[Portal] reference_data seed checked.")

    # 金旭 PMS 分析（2026-08-05）：科目分類對照表 35 筆 + 分析門檻 6 筆。
    # 冪等——已存在的 subject_code 不覆蓋（管理員可能已在設定頁調整過分類）。
    # ⚠️ 必須在此 seed，否則首次匯入時 40,706 筆分錄會全部被歸為「未分類」。
    _run_startup_migration("_seed_jinxu", _seed_jinxu)
    print("[Portal] jinxu subject map & settings seed checked.")

    # F3（2026-06-01）：contracts 新欄位 + contract_cost_allocations 資料表
    import app.models.contract  # noqa: F401 — ContractCostAllocation 已在其中


    # 選單設定補丁（2026-04-28）：隱藏舊 custom_1777348120465，補齊 mall-pm-group 子項 DB 記錄
    _run_startup_migration("_seed_menu_config_mall_pm_group", _seed_menu_config_mall_pm_group)

    # 選單設定補丁（2026-05-14）：確保 nichiyo-purchase-report 選單有 DB 記錄
    _run_startup_migration("_seed_menu_config_nichiyo_purchase", _seed_menu_config_nichiyo_purchase)

    # 選單設定補丁（2026-05-14）：確保 nichiyo-claim-report 選單有 DB 記錄
    _run_startup_migration("_seed_menu_config_nichiyo_claim", _seed_menu_config_nichiyo_claim)

    # 客房主檔 seed（若 rooms 表為空，自動填入樓層 × 房號資料）
    from app.services.room_seed import seed_rooms

    _run_startup_migration("seed_rooms", seed_rooms)
    print("[Portal] Room seed checked.")

    # 知識庫範例資料植入（首次啟動時若 wiki_articles 為空）
    from app.services.wiki_seed import seed_wiki_articles
    _run_startup_migration("seed_wiki_articles", seed_wiki_articles)

    # 飯店班表模組種子（部門 + 班別）
    from app.services.schedule_seed import run_all_seeds as _schedule_seed
    from app.core.database import SessionLocal as _SessionLocal

    def _run_schedule_seed():
        with _SessionLocal() as _seed_db:
            _schedule_seed(_seed_db)

    _run_startup_migration("_run_schedule_seed", _run_schedule_seed)
    print("[Portal] Schedule seed checked.")

    # 商場班表模組種子（部門 + 班別）— 與飯店班表各自獨立的主檔
    from app.services.mall_schedule_seed import run_all_seeds as _mall_schedule_seed

    def _run_mall_schedule_seed():
        with _SessionLocal() as _seed_db:
            _mall_schedule_seed(_seed_db)

    _run_startup_migration("_run_mall_schedule_seed", _run_mall_schedule_seed)
    print("[Portal] Mall schedule seed checked.")

    # ── 排程同步（可透過 .env SCHEDULER_ENABLED=False 完全關閉）────────────────
    # DEV 模式請設 SCHEDULER_ENABLED=False，改用 sync_tool.py 手動同步。
    # PROD 模式（NSSM 服務）維持 True，排程對齊整點自動執行。
    if settings.SCHEDULER_ENABLED:
        # 排程對齊整點自動同步（預設 30 分鐘 → :00/:30）；啟動時不再立即同步，
        # 以確保伺服器能立即接受請求並從本地 DB 回傳資料。
        # 若需立即同步，請在前端點擊「同步資料」按鈕。
        _scheduler.add_job(
            _auto_sync,
            trigger=make_cron_trigger(30),   # CronTrigger：整點對齊，預設 :00 / :30
            id="module_auto_sync",
            replace_existing=True,
        )

        # 週期採購請購單「期別已過自動關閉」：每天 00:05（2026-08-07 新增）
        # 為什麼是每天而不是每小時：這件事只在跨月的那一刻會有變化，
        # 每小時跑只是白白增加 cycle-purchase.db 的寫入鎖競爭。
        # 挑 00:05 而不是 00:00，是為了避開整點大量排程同時觸發。
        # CronTrigger 在本檔沒有模組層 import（既有的 ppt_auto_export 也是就地
        # import），沿用同樣寫法。
        from apscheduler.triggers.cron import CronTrigger as _CpCloseCronTrigger
        _scheduler.add_job(
            _auto_close_expired_cp_requests,
            trigger=_CpCloseCronTrigger(hour=0, minute=5),
            id="cycle_purchase_auto_close",
            replace_existing=True,
            misfire_grace_time=3600,   # 服務重啟錯過了，一小時內補跑
        )

        # 請購單清單同步：每 15 分鐘（:00/:15/:30/:45）
        _scheduler.add_job(
            _purchase_list_sync,
            trigger=make_cron_trigger(15),
            id="purchase_list_sync",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # 請購單完整同步（含 Detail API 品項補全）：每 45 分鐘（:00/:45）
        _scheduler.add_job(
            _purchase_full_sync,
            trigger=make_cron_trigger(45),
            id="purchase_full_sync",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # 請款單清單同步：每 15 分鐘（:00/:15/:30/:45）
        _scheduler.add_job(
            _claim_list_sync,
            trigger=make_cron_trigger(15),
            id="claim_list_sync",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # 請款單完整同步（含 Detail API 品項補全）：每 45 分鐘（:00/:45）
        _scheduler.add_job(
            _claim_full_sync,
            trigger=make_cron_trigger(45),
            id="claim_full_sync",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # 日曜請購單清單同步：每 15 分鐘（:00/:15/:30/:45）
        _scheduler.add_job(
            _nichiyo_purchase_list_sync,
            trigger=make_cron_trigger(15),
            id="nichiyo_purchase_list_sync",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # 日曜請購單完整同步（含 Detail API 品項補全）：每 45 分鐘（:00/:45）
        _scheduler.add_job(
            _nichiyo_purchase_full_sync,
            trigger=make_cron_trigger(45),
            id="nichiyo_purchase_full_sync",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # 日曜請款單清單同步：每 15 分鐘（:00/:15/:30/:45）
        _scheduler.add_job(
            _nichiyo_claim_list_sync,
            trigger=make_cron_trigger(15),
            id="nichiyo_claim_list_sync",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # 日曜請款單完整同步（含 Detail API 品項補全）：每 45 分鐘（:00/:45）
        _scheduler.add_job(
            _nichiyo_claim_full_sync,
            trigger=make_cron_trigger(45),
            id="nichiyo_claim_full_sync",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # 依各 RagicConnection 的 sync_interval 建立個別排程任務
        _init_ragic_connection_jobs()

        # C-4：PPT 自動匯出（每月固定日期，預設 5 日 08:00）
        from app.services.ppt_auto_export import (
            run_auto_export as _ppt_auto_export,
            AUTO_EXPORT_DAY, AUTO_EXPORT_HOUR,
        )
        from apscheduler.triggers.cron import CronTrigger as _CronTrigger
        _scheduler.add_job(
            _ppt_auto_export,
            trigger=_CronTrigger(day=AUTO_EXPORT_DAY, hour=AUTO_EXPORT_HOUR, minute=0),
            id="ppt_auto_export",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        print(f"[Portal] PPT auto-export scheduled: every month day {AUTO_EXPORT_DAY} at {AUTO_EXPORT_HOUR:02d}:00")

        # E3：合約到期自動通知（每日 09:00）
        from app.services.contract_expiry_notify import notify_expiring_contracts as _contract_expiry_notify
        _scheduler.add_job(
            _contract_expiry_notify,
            trigger=_CronTrigger(hour=9, minute=0),
            id="contract_expiry_notify",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        print("[Portal] Contract expiry notification scheduled: daily at 09:00")

        # G1：合約預算使用率警示（每日 09:30）
        from app.services.contract_budget_alert import check_budget_alerts as _budget_alert
        _scheduler.add_job(
            _budget_alert,
            trigger=_CronTrigger(hour=9, minute=30),
            id="contract_budget_alert",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        print("[Portal] Contract budget alert scheduled: daily at 09:30")

        # G4：合約到期自動終止（每日 01:00）
        from app.services.contract_auto_close import auto_close_expired_contracts as _auto_close
        _scheduler.add_job(
            _auto_close,
            trigger=_CronTrigger(hour=1, minute=0),
            id="contract_auto_close",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        print("[Portal] Contract auto-close scheduled: daily at 01:00")

        # H3：分期付款逾期提醒（每日 09:45）
        from app.services.contract_payment_alert import notify_overdue_payment_schedules as _payment_alert
        _scheduler.add_job(
            _payment_alert,
            trigger=_CronTrigger(hour=9, minute=45),
            id="contract_payment_alert",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        print("[Portal] Contract payment alert scheduled: daily at 09:45")

        # I3：保證金退還提醒（每日 10:00）
        from app.services.contract_deposit_alert import notify_expiring_deposits as _deposit_alert
        _scheduler.add_job(
            _deposit_alert,
            trigger=_CronTrigger(hour=10, minute=0),
            id="contract_deposit_alert",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        print("[Portal] Contract deposit alert scheduled: daily at 10:00")

        # 2026-07-14：hotel_routine_pm 排程自動產生工作已隨模組安全下線一併停用
        # （模組與 hotel/periodic-maintenance 重複，使用者確認保留後者為正式模組）。
        # 函式與 add_job 呼叫整段註解保留，未刪除，供日後回溯／復原。
        # async def _auto_generate_hotel_routine_pm_schedule():
        #     from app.core.database import SessionLocal
        #     from app.routers.hotel_routine_pm import _do_generate_hotel_routine_pm
        #     today = __import__("datetime").date.today()
        #     db = SessionLocal()
        #     try:
        #         result = _do_generate_hotel_routine_pm(today.year, today.month, db)
        #         print(
        #             f"[Portal] auto-generate hotel_routine_pm {today.year}/{today.month:02d}: "
        #             f"generated={result.generated}, updated={result.updated}, errors={result.errors}"
        #         )
        #     except Exception as exc:
        #         print(f"[Portal] auto-generate hotel_routine_pm failed: {exc}")
        #     finally:
        #         db.close()
        #
        # _scheduler.add_job(
        #     _auto_generate_hotel_routine_pm_schedule,
        #     trigger=_CronTrigger(day=1, hour=2, minute=0),
        #     id="auto_generate_hotel_routine_pm",
        #     replace_existing=True,
        #     misfire_grace_time=3600,
        # )
        # print("[Portal] hotel_routine_pm auto-generate scheduled: monthly day=1 at 02:00")

        # 方案 A：每月 1 日 02:10 自動產生全棟例行維護排程
        async def _auto_generate_full_bldg_pm_schedule():
            from app.core.database import SessionLocal
            from app.routers.full_building_maintenance import _do_generate_full_bldg_pm
            today = __import__("datetime").date.today()
            db = SessionLocal()
            try:
                result = _do_generate_full_bldg_pm(today.year, today.month, db)
                print(
                    f"[Portal] auto-generate full_bldg_pm {today.year}/{today.month:02d}: "
                    f"generated={result.generated}, updated={result.updated}, errors={result.errors}"
                )
            except Exception as exc:
                print(f"[Portal] auto-generate full_bldg_pm failed: {exc}")
            finally:
                db.close()

        _scheduler.add_job(
            _auto_generate_full_bldg_pm_schedule,
            trigger=_CronTrigger(day=1, hour=2, minute=10),
            id="auto_generate_full_bldg_pm",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        print("[Portal] full_bldg_pm auto-generate scheduled: monthly day=1 at 02:10")

        # 方案 A：每月 1 日 02:20 自動產生飯店週期保養排程
        async def _auto_generate_hotel_periodic_pm_schedule():
            from app.core.database import SessionLocal
            from app.routers.periodic_maintenance import _do_generate_hotel_periodic_pm
            today = __import__("datetime").date.today()
            db = SessionLocal()
            try:
                result = _do_generate_hotel_periodic_pm(today.year, today.month, db)
                print(
                    f"[Portal] auto-generate hotel_periodic_pm {today.year}/{today.month:02d}: "
                    f"generated={result.generated}, updated={result.updated}, errors={result.errors}"
                )
            except Exception as exc:
                print(f"[Portal] auto-generate hotel_periodic_pm failed: {exc}")
            finally:
                db.close()

        _scheduler.add_job(
            _auto_generate_hotel_periodic_pm_schedule,
            trigger=_CronTrigger(day=1, hour=2, minute=20),
            id="auto_generate_hotel_periodic_pm",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        print("[Portal] hotel_periodic_pm auto-generate scheduled: monthly day=1 at 02:20")

        # ═══════════════════════════════════════════════════════════════════
        # 每日 06:00 OHIP 快照（2026-08-07）
        # ═══════════════════════════════════════════════════════════════════
        # ⚠️ 這裡刻意用**同步 `def`** 而不是本檔其他排程慣用的 `async def`。
        #    APScheduler 兩者都支援，但 `async def` 裡跑同步的 `db.query()` 會卡住
        #    event loop —— 這正是 2026-07-15 修掉 12 個 router 的那個問題
        #    （單 worker 下整站無回應）。快照要跑約 20 秒、打 7 次 API，
        #    用 async def 等於讓整個 Portal 卡 20 秒。其他排程沿用舊寫法未動。
        #
        # ⚠️ `misfire_grace_time` 只給 600 秒（10 分鐘），比本檔其他排程的 3600 短很多。
        #    這是刻意的：pickup 曲線的 X 軸是「提前幾天」，
        #    若某天延後一小時才跑，該點與前後點的實際間隔就不是 24 小時，曲線會失真。
        #    **寧可跳過那一天（缺一個點看得出來），也不要補一個時間錯位的點。**
        def _daily_ohip_snapshot():
            from app.core.database import SessionLocal
            from app.services.ohip_snapshot_service import run_snapshot
            db = SessionLocal()
            try:
                r = run_snapshot(db, triggered_by="scheduler")
                print(
                    f"[Portal] OHIP snapshot {r.get('snapshot_date')}: "
                    f"status={r.get('status')} house={r.get('house_rows')} "
                    f"roomtype={r.get('room_type_rows')} revenue={r.get('revenue_rows')} "
                    f"calls={r.get('api_calls')} elapsed={r.get('elapsed_ms')}ms"
                )
                for w in r.get("warnings") or []:
                    print(f"[Portal] OHIP snapshot warning: {w}")
                if r.get("error"):
                    print(f"[Portal] OHIP snapshot error: {r['error']}")
            except Exception as exc:
                print(f"[Portal] OHIP snapshot failed: {exc}")
            finally:
                db.close()

        _scheduler.add_job(
            _daily_ohip_snapshot,
            trigger=_CronTrigger(hour=6, minute=0),
            id="ohip_daily_snapshot",
            replace_existing=True,
            misfire_grace_time=600,
        )
        print("[Portal] OHIP daily snapshot scheduled: daily at 06:00 "
              "(lookback 7 days + horizon 180 days)")

        # ── 每日 06:30 市場區隔歷史營收增量（2026-08-07）─────────────────────
        # ⚠️ 排在快照（06:00）之後，兩者不會搶同一個時間點。
        # ⚠️ 同樣刻意用同步 `def`（理由同上方快照排程）。
        # ⚠️ grace 用 3600（與本檔多數排程一致）而**不是**快照那個 600：
        #    這裡抓的是「已完成日期的最終結果」，晚幾小時跑數字完全一樣，
        #    沒有快照那種「時點錯位會讓曲線失真」的問題。
        def _daily_segment_incremental():
            from app.core.database import SessionLocal
            from app.services.opera_segment_sync import sync_incremental
            db = SessionLocal()
            try:
                r = sync_incremental(db, triggered_by="scheduler")
                print(
                    f"[Portal] segment revenue incremental {r.get('date_start')}~{r.get('date_end')}: "
                    f"status={r.get('status')} rows={r.get('rows_written')} "
                    f"calls={r.get('api_calls')} elapsed={r.get('elapsed_ms')}ms"
                )
                for w in r.get("warnings") or []:
                    print(f"[Portal] segment revenue warning: {w}")
                if r.get("error"):
                    print(f"[Portal] segment revenue error: {r['error']}")
            except Exception as exc:
                print(f"[Portal] segment revenue incremental failed: {exc}")
            finally:
                db.close()

        _scheduler.add_job(
            _daily_segment_incremental,
            trigger=_CronTrigger(hour=6, minute=30),
            id="opera_segment_incremental",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        print("[Portal] segment revenue incremental scheduled: daily at 06:30 (last 14 days)")

        # ── 每日 07:00 訂房與團體增量（2026-08-07）───────────────────────────
        # ⚠️ 排在 06:30 的營收增量之後，避免同時打 OHIP。
        # ⚠️ 同樣刻意用同步 `def`（async def 裡跑同步 DB 會卡住 event loop）。
        # ⚠️ 增量區間**含未來 180 天** —— 在手訂房分析需要未來資料，
        #    只抓過去會讓那一頁永遠是空的。
        def _daily_reservation_incremental():
            from app.core.database import SessionLocal
            from app.services.opera_reservation_sync import sync_incremental
            db = SessionLocal()
            try:
                out = sync_incremental(db, triggered_by="scheduler")
                for name, r in out.items():
                    print(
                        f"[Portal] {name} incremental {r.get('date_start')}~{r.get('date_end')}: "
                        f"status={r.get('status')} parent={r.get('parent_rows')} "
                        f"child={r.get('child_rows')} calls={r.get('api_calls')} "
                        f"elapsed={r.get('elapsed_ms')}ms"
                    )
                    for w in r.get("warnings") or []:
                        print(f"[Portal] {name} warning: {w}")
                    if r.get("error"):
                        print(f"[Portal] {name} error: {r['error']}")
            except Exception as exc:
                print(f"[Portal] reservation incremental failed: {exc}")
            finally:
                db.close()

        _scheduler.add_job(
            _daily_reservation_incremental,
            trigger=_CronTrigger(hour=7, minute=0),
            id="opera_reservation_incremental",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        print("[Portal] reservation+block incremental scheduled: daily at 07:00 "
              "(last 14 days + next 180 days)")

        # ── 每日 03:05 OTA 評論擷取（2026-08-22）────────────────────────────
        # 規格書：docs/SPEC_ota_reviews.md §11
        #
        # ⚠️ 為什麼是 03:05 而不是 03:00：整點是全天最擁擠的時段 ——
        #    module_auto_sync 加上 8 支請購／請款同步共 9 支會同時觸發。
        #    爬蟲會長時間佔用 DB 寫入，撞上去就是 database is locked。
        #    比照 cycle_purchase_auto_close 挑 00:05 避開整點的既有作法。
        #
        # ⚠️ 同樣刻意用同步 `def` 而非 async def（理由同上方各排程）。
        #
        # ⚠️ 這條路徑**沒有外層鎖**，所以呼叫 run_scheduled_sync()（內含 sync_lock）
        #    而不是 sync_all_enabled()（那支是給 sync_tool.py 用的，外層已加鎖，
        #    兩邊都加會自我死鎖）。
        #
        # ⚠️ 本模組同時登錄於 sync_tool.py MODULES。有排程的非 Ragic 模組
        #    只掛這裡是不夠的 —— SCHEDULER_ENABLED=false 的機器上等於從未執行
        #    （2026-08-13 那四個 OHIP 排程就是這樣停擺的）。
        def _daily_ota_sync():
            from app.services.ota_scraper_service import run_scheduled_sync
            try:
                r = run_scheduled_sync()
                print(
                    f"[Portal] OTA review sync: {r.get('success')}/{r.get('attempted')} sources ok "
                    f"(skipped={r.get('skipped')}) "
                    f"inserted={r.get('inserted')} updated={r.get('updated')} "
                    f"dup={r.get('marked_duplicate')}"
                )
                # ⚠️ warning 用 warning 印、error 用 error 印，不要混在一起。
                #    「某幾筆略過」與「整個來源失敗」在畫面上是不同顏色。
                for w in (r.get("warnings") or [])[:20]:
                    print(f"[Portal] OTA review warning: {w}")
                for e in r.get("errors") or []:
                    print(f"[Portal] OTA review error: {e}")
            except Exception as exc:
                print(f"[Portal] OTA review sync failed: {exc}")

        _scheduler.add_job(
            _daily_ota_sync,
            trigger=_CronTrigger(hour=3, minute=5),
            id="ota_review_sync",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        print("[Portal] OTA review sync scheduled: daily at 03:05 "
              "(enabled sources, once per day)")

        # ── 每日 03:40 OTA 情緒與主題分析（2026-08-22，P4）──────────────
        # 規格書：docs/SPEC_ota_reviews.md §7、§11
        #
        # ⚠️ 排在擷取（03:05）之後 —— 先有資料才有東西可分析。
        #    間隔 35 分鐘是給擷取留餘裕（四個來源 × 翻頁，最久可能 20 分鐘）。
        #    真的撞上也不會壞：分析只挑 analyzed_at IS NULL 的，
        #    這一輪沒分析到的下一輪會補。
        #
        # ⚠️ 同樣刻意用同步 def。
        # ⚠️ 這條路徑沒有外層鎖，所以自己包 sync_lock
        #    （run_scheduled_analyze() 內部不加，那支也給 sync_tool.py 用）。
        def _daily_ota_analyze():
            from app.core.sync_lock import sync_lock
            from app.services.ota_analysis_service import run_scheduled_analyze
            try:
                with sync_lock("OTA 情緒分析"):
                    r = run_scheduled_analyze()
                print(
                    f"[Portal] OTA analyze: total={r.get('total')} "
                    f"rule={r.get('rule_count')} ai={r.get('ai_count')} "
                    f"cache={r.get('cache_hit')} alert={r.get('alert_count')}"
                )
                for w in (r.get("warnings") or [])[:20]:
                    print(f"[Portal] OTA analyze warning: {w}")
            except Exception as exc:
                print(f"[Portal] OTA analyze failed: {exc}")

        _scheduler.add_job(
            _daily_ota_analyze,
            trigger=_CronTrigger(hour=3, minute=40),
            id="ota_sentiment_analyze",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        print("[Portal] OTA sentiment analyze scheduled: daily at 03:40")

        _scheduler.start()
        print("[Portal] AutoSync scheduler started (cron-aligned, default every 30 minutes).")
    else:
        print("[Portal] AutoSync scheduler DISABLED (SCHEDULER_ENABLED=False). Use sync_tool.py to sync manually.")

    # 報修未完成報表排程寄信已移至 sync_tool.py 管理（per-module 排程設定）
    print("[Portal] Repair report daily send: managed by sync_tool.py (not backend scheduler).")

    yield
    # ── Shutdown ──────────────────────────────────────────────────────────────
    # APScheduler asyncio shutdown 在 uvicorn --reload 時 event loop 已消失，
    # 用 try/except 靜默處理，避免 AttributeError 汙染 log。
    try:
        if _scheduler.running:
            _scheduler.shutdown(wait=False)
    except Exception:
        pass
    print("[Portal] Shutting down.")


# ── API 文件：僅在 development 環境開放，production 自動關閉 ─────────────────
# 生產環境請在 .env 設 APP_ENV=production 或 ENV=production
_is_dev = settings.APP_ENV.lower() in ("development", "dev") or \
          settings.ENV.lower() in ("development", "dev")

app = FastAPI(
    title="集團 Portal API",
    version="1.0.0",
    description="Hotel/Mall 集團管理 Portal — 後端 API",
    lifespan=lifespan,
    redirect_slashes=False,   # 防止 307 繞過 Vite proxy 觸發 CORS
    docs_url="/api/docs"         if _is_dev else None,
    redoc_url="/api/redoc"       if _is_dev else None,
    openapi_url="/api/openapi.json" if _is_dev else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 使用監控 Middleware（CORS 之後掛載，才能正確讀到 Authorization header）──
from app.middleware.audit_middleware import AuditMiddleware
app.add_middleware(AuditMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

# 既有模組
app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["認證"])
app.include_router(users.router, prefix=f"{API_PREFIX}/users", tags=["使用者"])
app.include_router(tenants.router, prefix=f"{API_PREFIX}/tenants", tags=["據點"])
app.include_router(ragic.router, prefix=f"{API_PREFIX}/ragic", tags=["Ragic"])
# 2026-07-22 新增：公開版本資訊端點，供正式區/測試區比對 git commit（唯一無需登入的端點，見 version.py 檔頭說明）
app.include_router(version.router, prefix=f"{API_PREFIX}/version", tags=["系統資訊"])
# 2026-08-11 新增：站台基本設定（品牌名稱）。GET 為公開端點（登入頁未認證就要顯示站台名稱），
# PUT 仍需 system_admin。必須註冊在檔案最下方的 spa_fallback catch-all 之前，
# 否則 /api/v1/site-config 會拿到 200 + index.html（見 site_config.py 檔頭）。
app.include_router(site_config.router, prefix=f"{API_PREFIX}/site-config", tags=["系統資訊"])
app.include_router(
    dashboard.router, prefix=f"{API_PREFIX}/dashboard", tags=["Dashboard"]
)

# ── 新增：客房保養 ──────────────────────────────────────────────────────────────
app.include_router(
    room_maintenance.router,
    prefix=f"{API_PREFIX}/room-maintenance",
    tags=["客房保養"],
)

# ── 新增：倉庫庫存 ──────────────────────────────────────────────────────────────
app.include_router(
    inventory.router,
    prefix=f"{API_PREFIX}/inventory",
    tags=["倉庫庫存"],
)

# ── 新增：客房保養明細 ───────────────────────────────────────────────────────────
app.include_router(
    room_maintenance_detail.router,
    prefix=f"{API_PREFIX}/room-maintenance-detail",
    tags=["客房保養明細"],
)

# ── 新增：飯店週期保養表 ─────────────────────────────────────────────────────────────
app.include_router(
    periodic_maintenance.router,
    prefix=f"{API_PREFIX}/periodic-maintenance",
    tags=["週期保養表"],
)

# 2026-07-14：hotel_routine_pm 安全下線 — 與 hotel/periodic-maintenance（Sheet 11
# 遷移後）為重複模組，使用者確認後者才是正式模組。路由整段停用（不註冊即無法
# 從外部存取，等同下線），router 檔案／DB 表格保留未刪，可隨時取消註解復原。
# app.include_router(
#     hotel_routine_pm.router,
#     prefix=f"{API_PREFIX}/hotel/routine-maintenance",
#     tags=["飯店例行維護"],
# )

# ── 新增：IHG 客房保養（年度矩陣保養計畫）────────────────────────────────────
app.include_router(
    ihg_room_maintenance.router,
    prefix=f"{API_PREFIX}/ihg-room-maintenance",
    tags=["IHG客房保養"],
)

# ── 新增：商場週期保養表 ──────────────────────────────────────────────────────────
app.include_router(
    mall_periodic_maintenance.router,
    prefix=f"{API_PREFIX}/mall/periodic-maintenance",
    tags=["商場週期保養表"],
)

# ── 新增：全棟例行維護 ──────────────────────────────────────────────────────────
app.include_router(
    full_building_maintenance.router,
    prefix=f"{API_PREFIX}/mall/full-building-maintenance",
    tags=["全棟例行維護"],
)

# ── 新增：整棟工務每日巡檢 B4F ────────────────────────────────────────────────
app.include_router(
    b4f_inspection.router,
    prefix=f"{API_PREFIX}/mall/b4f-inspection",
    tags=["整棟工務每日巡檢 B4F"],
)

# ── 新增：整棟工務每日巡檢 RF ─────────────────────────────────────────────────
app.include_router(
    rf_inspection.router,
    prefix=f"{API_PREFIX}/mall/rf-inspection",
    tags=["整棟工務每日巡檢 RF"],
)

# ── 新增：整棟工務每日巡檢 B2F ────────────────────────────────────────────────
app.include_router(
    b2f_inspection.router,
    prefix=f"{API_PREFIX}/mall/b2f-inspection",
    tags=["整棟工務每日巡檢 B2F"],
)

# ── 新增：整棟工務每日巡檢 B1F ────────────────────────────────────────────────
app.include_router(
    b1f_inspection.router,
    prefix=f"{API_PREFIX}/mall/b1f-inspection",
    tags=["整棟工務每日巡檢 B1F"],
)

# ── 新增：商場管理 Overview — 跨模組彙整（daily-hours 等）────────────────────
app.include_router(
    mall_overview.router,
    prefix=f"{API_PREFIX}",
    tags=["商場管理 Dashboard"],
)

# ── 新增：飯店管理 Overview — 跨模組彙整（daily/monthly/person-hours）────────
app.include_router(
    hotel_overview.router,
    prefix=f"{API_PREFIX}",
    tags=["飯店管理 Dashboard"],
)

# ── 新增：飯店每日巡檢 ────────────────────────────────────────────────────────
app.include_router(
    hotel_daily_inspection.router,
    prefix=f"{API_PREFIX}/hotel-daily-inspection",
    tags=["飯店每日巡檢"],
)

# ── 新增：每日數值登錄表 ──────────────────────────────────────────────────────
app.include_router(
    hotel_meter_readings.router,
    prefix=f"{API_PREFIX}/hotel-meter-readings",
    tags=["每日數值登錄表"],
)

# ── 新增：商場管理統計 Dashboard ──────────────────────────────────────────────
app.include_router(
    mall_dashboard.router,
    prefix=f"{API_PREFIX}/mall/dashboard",
    tags=["商場管理統計 Dashboard"],
)

# ── 新增：春大直商場工務巡檢（Ragic 連結導覽模組）────────────────────────────
app.include_router(
    mall_facility_inspection.router,
    prefix=f"{API_PREFIX}/mall-facility-inspection",
    tags=["春大直商場工務巡檢"],
)

# ── 新增：整棟巡檢（Ragic 連結導覽模組）──────────────────────────────────────
app.include_router(
    full_building_inspection.router,
    prefix=f"{API_PREFIX}/full-building-inspection",
    tags=["整棟巡檢"],
)

# ── 新增：保全巡檢（7 張 Sheet 統一路由）──────────────────────────────────────
app.include_router(
    security_patrol.router,
    prefix=f"{API_PREFIX}/security/patrol",
    tags=["保全巡檢"],
)

# ── 新增：保全巡檢統計 Dashboard ───────────────────────────────────────────────
app.include_router(
    security_dashboard.router,
    prefix=f"{API_PREFIX}/security/dashboard",
    tags=["保全巡檢統計 Dashboard"],
)


# ── 新增：簽核系統 ────────────────────────────────────────────────────────────
app.include_router(
    approvals.router,
    prefix=f"{API_PREFIX}/approvals",
    tags=["簽核系統"],
)

# ── 新增：公告系統 ────────────────────────────────────────────────────────────
app.include_router(
    memos.router,
    prefix=f"{API_PREFIX}/memos",
    tags=["公告系統"],
)

# ── 新增：影音教學（本地模組，不對接 Ragic）───────────────────────────────────
app.include_router(
    tutorial_videos.router,
    prefix=f"{API_PREFIX}/tutorial-videos",
    tags=["影音教學"],
)

# ── 新增：行事曆聚合系統 ──────────────────────────────────────────────────────
app.include_router(
    calendar.router,
    prefix=f"{API_PREFIX}/calendar",
    tags=["行事曆"],
)

# ── 新增：通用上傳（Rich Editor 圖片）────────────────────────────────────────
app.include_router(
    uploads.router,
    prefix=f"{API_PREFIX}/upload",
    tags=["上傳"],
)

# ── 新增：商場工務報修 ────────────────────────────────────────────────────────
app.include_router(
    luqun_repair.router,
    prefix=f"{API_PREFIX}/luqun-repair",
    tags=["商場工務報修"],
)
# export_router 單獨掛載（不帶 router-level auth，用 query token 自驗）
app.include_router(
    luqun_repair.export_router,
    prefix=f"{API_PREFIX}/luqun-repair",
    tags=["商場工務報修"],
)

# ── 新增：大直工務部 ──────────────────────────────────────────────────────────
app.include_router(
    dazhi_repair.router,
    prefix=f"{API_PREFIX}/dazhi-repair",
    tags=["大直工務部"],
)
# export_router 單獨掛載（不帶 router-level auth，用 query token 自驗）
app.include_router(
    dazhi_repair.export_router,
    prefix=f"{API_PREFIX}/dazhi-repair",
    tags=["大直工務部"],
)

# ── 新增：主管交辦／緊急事件 ────────────────────────────────────────────────
app.include_router(
    other_tasks.router,
    prefix=f"{API_PREFIX}/other-tasks",
    tags=["主管交辦／緊急事件"],
)

# ── 新增：★工項類別分析（整合商場+大直）────────────────────────────────────
app.include_router(
    work_category_analysis.router,
    prefix=f"{API_PREFIX}/work-category-analysis",
    tags=["工項類別分析"],
)

# ── 新增：核准請購單月報表 ───────────────────────────────────────────────────────
app.include_router(
    purchase_report.router,
    prefix=f"{API_PREFIX}/purchase-report",
    tags=["核准請購單月報表"],
)

# ── 新增：核准請款單月報表 ───────────────────────────────────────────────────────
app.include_router(
    claim_report.router,
    prefix=f"{API_PREFIX}/claim-report",
    tags=["核准請款單月報表"],
)

# ── 新增：請購請款整合總表 ────────────────────────────────────────────────────────
app.include_router(
    combined_report.router,
    prefix=f"{API_PREFIX}/combined-report",
    tags=["請購請款整合總表"],
)

# ── 新增：工作日誌（10 模組聚合）─────────────────────────────────────────────
app.include_router(
    work_journal.router,
    prefix=f"{API_PREFIX}/work-journal",
    tags=["工作日誌"],
)

# ── 新增：日曜核准請購單月報表 ──────────────────────────────────────────────────
app.include_router(
    nichiyo_purchase_report.router,
    prefix=f"{API_PREFIX}/nichiyo-purchase-report",
    tags=["日曜請購月報表"],
)

# ── 新增：日曜核准請款單月報表 ──────────────────────────────────────────────────
app.include_router(
    nichiyo_claim_report.router,
    prefix=f"{API_PREFIX}/nichiyo-claim-report",
    tags=["日曜請款月報表"],
)

# ── Ragic Sheet 設定管理 ─────────────────────────────────────────────────────
app.include_router(
    ragic_sheet_config.router,
    prefix=f"{API_PREFIX}/settings/ragic-sheet-config",
    tags=["Ragic Sheet 設定"],
)

# ── Ragic 與 Portal 欄位比對稽核 ─────────────────────────────────────────────
app.include_router(
    ragic_field_audit.router,
    prefix=f"{API_PREFIX}/settings/ragic-field-audit",
    tags=["Ragic 欄位比對"],
)

# ── 員工操作手冊匯出 ──────────────────────────────────────────────────────────
app.include_router(
    employee_manual_export.router,
    prefix=f"{API_PREFIX}/employee-manual-export",
    tags=["員工操作手冊"],
)

# ── 選單設定 ──────────────────────────────────────────────────────────────────
app.include_router(
    menu_config.router,
    prefix=f"{API_PREFIX}/settings/menu-config",
    tags=["選單設定"],
)

# ── 靜態頁面清單 ──────────────────────────────────────────────────────────────
app.include_router(
    static_pages.router,
    prefix=f"{API_PREFIX}/settings",
    tags=["靜態頁面"],
)
# ── 角色管理 ──────────────────────────────────────────────────────────────────
app.include_router(
    roles.router,
    prefix=f"{API_PREFIX}/roles",
    tags=["角色管理"],
)

# ── 角色權限設定 ───────────────────────────────────────────────────────────────
app.include_router(
    role_permissions.router,
    prefix=f"{API_PREFIX}/role-permissions",
    tags=["角色權限設定"],
)

# ── 知識庫（LLM Wiki）────────────────────────────────────────────────────────
# ⚠️ 2026-08-11 補回：此兩支 include_router 在 commit a4a48ae（2026-05-15 的
#    main.py 大重整）被連同相鄰區塊一起刪除且未補回，導致 /api/v1/wiki 與
#    /api/v1/knowledge-graph 落入最下方的 SPA catch-all，回傳 index.html（HTTP 200）。
#    前端拿到的不是 JSON，`res.items` 為 undefined → 知識庫頁「載入失敗」且整頁崩潰。
#    module import、models 建表、seed_wiki_articles 啟動植入一直都在，屬漏接而非下線。
app.include_router(
    wiki.router,
    prefix=f"{API_PREFIX}/wiki",
    tags=["知識庫"],
)

# ── 專案知識圖譜（graphify 整合）──────────────────────────────────────────────
app.include_router(
    knowledge_graph.router,
    prefix=f"{API_PREFIX}/knowledge-graph",
    tags=["專案知識圖譜"],
)

# ── 班表模組（本地 SQLite，不對接 Ragic）────────────────────────────────────
# 飯店與商場為完全獨立的兩套：資料、班別主檔、部門主檔、人員主檔皆不互通。
app.include_router(
    schedule.router,
    prefix=f"{API_PREFIX}/schedule",
    tags=["飯店班表"],
)
app.include_router(
    mall_schedule.router,
    prefix=f"{API_PREFIX}/mall/schedule",
    tags=["商場班表"],
)

# ── 新增：報修未完成報表 ──────────────────────────────────────────────────────
app.include_router(
    repair_report.router,
    prefix=f"{API_PREFIX}/repair-report",
    tags=["報修未完成報表"],
)

# ── 使用監控統計（system_admin only）─────────────────────────────────────────
app.include_router(
    usage_stats.router,
    prefix=f"{API_PREFIX}/usage",
    tags=["使用監控"],
)

# ── 飯店 Dashboard PPT 匯出設定（Section Registry 架構）──────────────────────
# 注意：router 本身已設 prefix="/hotel/ppt-export"，此處只加 API_PREFIX 即可
app.include_router(
    hotel_ppt_export.router,
    prefix=f"{API_PREFIX}",
    tags=["飯店 Dashboard PPT 匯出"],
)

# ── 報修模組 PPT 匯出 ─────────────────────────────────────────────────────────
app.include_router(
    repair_ppt_export.router,
    prefix=f"{API_PREFIX}",
    tags=["報修 PPT 匯出"],
)

# ── 合約管理系統 ─────────────────────────────────────────────────────────────
app.include_router(
    contract.router,
    prefix=f"{API_PREFIX}/contract",
    tags=["合約管理"],
)

# ── F1：基礎參考資料（公司別 / 部門別 / 計價規格）─────────────────────────
app.include_router(
    reference_data.router,
    prefix=f"{API_PREFIX}/settings",
    tags=["基礎參考資料"],
)

# ── 週期採購（獨立資料庫 cycle-purchase.db，第一期：基礎設定/料號/週期/批次）──
app.include_router(
    cycle_purchase_masters.router,
    prefix=f"{API_PREFIX}/cycle-purchase/masters",
    tags=["週期採購"],
)
app.include_router(
    cycle_purchase_items.router,
    prefix=f"{API_PREFIX}/cycle-purchase",
    tags=["週期採購"],
)
app.include_router(
    cycle_purchase_cycles.router,
    prefix=f"{API_PREFIX}/cycle-purchase",
    tags=["週期採購"],
)
app.include_router(
    cycle_purchase_requests.router,
    prefix=f"{API_PREFIX}/cycle-purchase",
    tags=["週期採購"],
)
app.include_router(
    cycle_purchase_summary.router,
    prefix=f"{API_PREFIX}/cycle-purchase",
    tags=["週期採購"],
)
app.include_router(
    cycle_purchase_po.router,
    prefix=f"{API_PREFIX}/cycle-purchase",
    tags=["週期採購"],
)
app.include_router(
    cycle_purchase_receiving.router,
    prefix=f"{API_PREFIX}/cycle-purchase",
    tags=["週期採購"],
)
app.include_router(
    cycle_purchase_payment.router,
    prefix=f"{API_PREFIX}/cycle-purchase",
    tags=["週期採購"],
)
app.include_router(
    cycle_purchase_audit.router,
    prefix=f"{API_PREFIX}/cycle-purchase",
    tags=["週期採購"],
)

# ── 營運分析（OPERA）：檔案上傳型模組，資料來自人工上傳的 OPERA TXT ──────────
app.include_router(
    opera_import.router,
    prefix=f"{API_PREFIX}/opera/import",
    tags=["營運分析"],
)
app.include_router(
    opera_revenue.router,
    prefix=f"{API_PREFIX}/opera/revenue",
    tags=["營運分析"],
)
app.include_router(
    opera_guest.router,
    prefix=f"{API_PREFIX}/opera/guest",
    tags=["營運分析"],
)
app.include_router(
    opera_forecast.router,
    prefix=f"{API_PREFIX}/opera/forecast",
    tags=["營運分析"],
)
# ⚠️ 本組端點雖然掛在 /opera/* 底下，但**資料來源是 OHIP API 落地，不是 TXT 上傳**。
#    放這裡是因為時間語意一致（都是落地的歷史資料），主管看月報不必跨模組跳。
#    代價是同一個模組混了兩種來源 —— 畫面上必須標示，service 的 `source.note` 已強制帶出。
app.include_router(
    opera_segment.router,
    prefix=f"{API_PREFIX}/opera/segments",
    tags=["營運分析"],
)
# 訂房分析（2026-08-07）：⚠️ 與 /opera/guest 分析母體不同（所有訂房 vs 已離店住客），
#    每個回應的 source.population 都會把這句話帶到畫面上。
app.include_router(
    opera_reservation.router,
    prefix=f"{API_PREFIX}/opera/reservations",
    tags=["營運分析"],
)
# 訂房 Pace／Pickup（2026-08-13）：讀 ohip_reservation(_night)，**不新增資料表**。
#    ⚠️ 歷史進度是以訂房日「回推」得出（sync 是整列覆寫、無版本），
#       已含後續改期與取消的結果 —— source.population 會把這句話帶到畫面上。
#    ⚠️ 與 /opera/reservations 的差別：那邊看「現在」，這邊多一個 as_of 觀察時點。
app.include_router(
    opera_pace.router,
    prefix=f"{API_PREFIX}/opera/pace",
    tags=["營運分析"],
)

# ── OTA 口碑分析（2026-08-21）：Booking／Expedia／Tripadvisor 公開評論 ──────────
#    規格書 docs/SPEC_ota_reviews.md。
#    ⚠️ 與 /opera/*、/jinxu/* 完全獨立：那兩個是 PMS 營收資料（權限敏感群組），
#       本模組是公開評論，權限另開「口碑分析」group，不受 §11.1 那條紅線約束。
#    ⚠️ 所有統計一律用 score_10（統一 10 分制）—— Booking 10 分制與 Tripadvisor
#       5 分制混在一起平均出來的數字是錯的。
app.include_router(
    ota_reviews.router,
    prefix=f"{API_PREFIX}/ota/reviews",
    tags=["口碑分析"],
)
app.include_router(
    ota_stats.router,
    prefix=f"{API_PREFIX}/ota/stats",
    tags=["口碑分析"],
)
app.include_router(
    ota_admin.router,
    prefix=f"{API_PREFIX}/ota/admin",
    tags=["口碑分析"],
)

# ── 即時營運：直接向 OPERA Cloud（OHIP）取數，不落地、不共用 opera_* 表 ────────
#    唯讀＋記憶體快取；規格書 docs/SPEC_realtime_operations.md。
#    ⚠️ 與 /opera/*（人工上傳 TXT）完全獨立：資料時點不同，不共用端點或資料表。
app.include_router(
    realtime.router,
    prefix=f"{API_PREFIX}/realtime",
    tags=["即時營運"],
)

# ── 金旭 PMS 分析：檔案上傳型模組，資料來自人工上傳的金旭 xlsx ────────────────
#    路由前綴 /jinxu/*，與 /opera/* 完全獨立，不共用任何端點或資料表。
app.include_router(
    jinxu_import.router,
    prefix=f"{API_PREFIX}/jinxu/import",
    tags=["金旭分析"],
)
app.include_router(
    jinxu_revenue.router,
    prefix=f"{API_PREFIX}/jinxu/revenue",
    tags=["金旭分析"],
)
app.include_router(
    jinxu_payment.router,
    prefix=f"{API_PREFIX}/jinxu/payment",
    tags=["金旭分析"],
)
app.include_router(
    jinxu_deposit.router,
    prefix=f"{API_PREFIX}/jinxu/deposit",
    tags=["金旭分析"],
)
app.include_router(
    jinxu_reservation.router,
    prefix=f"{API_PREFIX}/jinxu/reservation",
    tags=["金旭分析"],
)
app.include_router(
    jinxu_settings.router,
    prefix=f"{API_PREFIX}/jinxu/settings",
    tags=["金旭分析"],
)

# ── AI 工單查詢助理（AI_ENABLED=true 才掛載，正式環境可保持 false）────────────
if settings.AI_ENABLED:
    from app.routers import ai as ai_router
    app.include_router(
        ai_router.router,
        prefix=f"{API_PREFIX}/ai",
        tags=["AI 助理"],
    )

# ── 靜態說明文件（docs-static）──────────────────────────────────────────────
# 供 settings/static-pages 的 iframe 預覽使用
# 路徑：/docs-static/<filename>  →  portal/docs/<filename>
_DOCS_DIR = pathlib.Path(__file__).parent.parent.parent / "docs"
if _DOCS_DIR.exists():
    app.mount(
        "/docs-static",
        StaticFiles(directory=_DOCS_DIR),
        name="docs-static",
    )

# ── 前端靜態檔（SPA catch-all）────────────────────────────────────────────
# dist/ 位於 portal/frontend/dist，由 npm run build 產生
_FRONTEND_DIST = pathlib.Path(__file__).parent.parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=_FRONTEND_DIST / "assets"),
        name="frontend-assets",
    )

    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon():
        return FileResponse(_FRONTEND_DIST / "favicon.svg")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # 若 dist 中存在對應的實體檔案（例如靜態 HTML 頁面），直接回傳；
        # 否則一律回傳 index.html 讓前端 Router 處理（SPA 模式）
        candidate = _FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
