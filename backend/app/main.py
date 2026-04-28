"""
集團 Portal — FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime

from app.core.config import settings
from app.core.database import Base, engine
from app.core.scheduler import make_cron_trigger, scheduler as _scheduler, register_connection_job
from app.core.time import twnow
from app.routers import (
    approvals,
    auth,
    budget,
    b4f_inspection,
    rf_inspection,
    b2f_inspection,
    b1f_inspection,
    calendar,
    dazhi_repair,
    hotel_daily_inspection,
    ihg_room_maintenance,
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
    ragic,
    room_maintenance,
    room_maintenance_detail,
    security_patrol,
    security_dashboard,
    tenants,
    users,
    work_category_analysis,
)


def _migrate_b4f_flatten():
    """
    B4F 架構遷移（寬表格 Pivot 架構 v3）：
    1. b4f_inspection_batch：若存在但缺少 start_time 欄位（舊版格式），刪除重建
    2. b4f_inspection_item ：若存在但有 batch_key 欄位（v2 扁平格式）或缺少 item_name
                             （v1 子表格格式），刪除重建
    """
    from sqlalchemy import text

    with engine.connect() as conn:
        # ── 1. 檢查 b4f_inspection_batch ────────────────────────────────────
        try:
            result = conn.execute(text("PRAGMA table_info(b4f_inspection_batch)"))
            batch_cols = {row[1] for row in result.fetchall()}
            if batch_cols and "start_time" not in batch_cols:
                conn.execute(text("DROP TABLE IF EXISTS b4f_inspection_batch"))
                conn.commit()
                print("[Migration] b4f_inspection_batch（舊版格式）已刪除，等待重建")
        except Exception:
            pass

        # ── 2. 檢查 b4f_inspection_item ─────────────────────────────────────
        try:
            result = conn.execute(text("PRAGMA table_info(b4f_inspection_item)"))
            item_cols = {row[1] for row in result.fetchall()}
            needs_rebuild = item_cols and (
                "batch_key" in item_cols  # v2 扁平格式
                or "item_name" not in item_cols  # v1 子表格格式
                or "batch_ragic_id" not in item_cols
            )
            if needs_rebuild:
                conn.execute(text("DROP TABLE IF EXISTS b4f_inspection_item"))
                conn.commit()
                print("[Migration] b4f_inspection_item（舊版格式）已刪除，等待重建")
        except Exception:
            pass


def _migrate_pm_batch_item():
    """
    輕量欄位補丁：
    1. 若 is_completed 欄位不存在則 ALTER TABLE 新增
    2. 回填現有資料：start_time AND end_time 均有值 → is_completed = 1
       （解決 migration 後舊資料全為 0 的問題）
    """
    from sqlalchemy import text

    with engine.connect() as conn:
        # ── 1. 加欄位（若不存在）──────────────────────────────────────────────
        result = conn.execute(text("PRAGMA table_info(pm_batch_item)"))
        existing = {row[1] for row in result.fetchall()}
        if "is_completed" not in existing:
            conn.execute(
                text(
                    "ALTER TABLE pm_batch_item ADD COLUMN is_completed BOOLEAN NOT NULL DEFAULT 0"
                )
            )
            conn.commit()
            print("[Migration] pm_batch_item.is_completed 欄位已新增")

        # ── 2. 回填舊資料（start_time AND end_time 均非空 → is_completed=1）──
        backfill = conn.execute(
            text(
                "UPDATE pm_batch_item "
                "SET is_completed = 1 "
                "WHERE start_time != '' AND end_time != '' AND is_completed = 0"
            )
        )
        if backfill.rowcount > 0:
            conn.commit()
            print(f"[Migration] is_completed 回填 {backfill.rowcount} 筆")


def _migrate_luqun_repair_images():
    """
    輕量欄位補丁：為 luqun_repair_case 加入 images_json 欄位（若尚未存在）。
    儲存 parse_images() 結果的 JSON 序列化字串，供 Drawer 顯示圖片。
    """
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(luqun_repair_case)"))
        existing = {row[1] for row in result.fetchall()}
        if "images_json" not in existing:
            conn.execute(text("ALTER TABLE luqun_repair_case ADD COLUMN images_json TEXT"))
            conn.commit()
            print("[Migration] luqun_repair_case.images_json 欄位已新增")


def _migrate_dazhi_repair_images():
    """
    輕量欄位補丁：為 dazhi_repair_case 加入 images_json 欄位（若尚未存在）。
    """
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(dazhi_repair_case)"))
        existing = {row[1] for row in result.fetchall()}
        if "images_json" not in existing:
            conn.execute(text("ALTER TABLE dazhi_repair_case ADD COLUMN images_json TEXT"))
            conn.commit()
            print("[Migration] dazhi_repair_case.images_json 欄位已新增")


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


def _migrate_luqun_counter_name():
    """
    為 luqun_repair_case 新增 deduction_counter_name 和 mgmt_response 欄位。
    扣款專櫃欄位原本被錯誤存為 float（結果為 0），現在改存店名字串。
    """
    from sqlalchemy import text
    new_cols = [
        ("deduction_counter_name", "TEXT NOT NULL DEFAULT ''"),
        ("mgmt_response",          "TEXT NOT NULL DEFAULT ''"),
    ]
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(luqun_repair_case)"))
        existing = {row[1] for row in result.fetchall()}
        for col, typedef in new_cols:
            if col not in existing:
                conn.execute(text(f"ALTER TABLE luqun_repair_case ADD COLUMN {col} {typedef}"))
                conn.commit()
                print(f"[Migration] luqun_repair_case.{col} 欄位已新增")


def _migrate_security_patrol_is_note():
    """
    欄位遷移 + 回填：
    1. 若 is_note 欄位不存在，ALTER TABLE 新增（BOOLEAN DEFAULT 0）
    2. 將 item_name 含「異常說明」的現有記錄回填為
         is_note=1, result_status='note', abnormal_flag=0
       使歷史資料與新 sync 邏輯一致，不需重新同步。
    """
    from sqlalchemy import text

    with engine.connect() as conn:
        # ── 1. 加欄位（若不存在）────────────────────────────────────────────────
        result = conn.execute(text("PRAGMA table_info(security_patrol_item)"))
        existing = {row[1] for row in result.fetchall()}
        if "is_note" not in existing:
            conn.execute(
                text(
                    "ALTER TABLE security_patrol_item ADD COLUMN is_note BOOLEAN NOT NULL DEFAULT 0"
                )
            )
            conn.commit()
            print("[Migration] security_patrol_item.is_note 欄位已新增")

        # ── 2. 回填「異常說明」類記錄 ────────────────────────────────────────────
        backfill = conn.execute(
            text(
                "UPDATE security_patrol_item "
                "SET is_note=1, result_status='note', abnormal_flag=0 "
                "WHERE item_name LIKE '%異常說明%' AND is_note=0"
            )
        )
        if backfill.rowcount > 0:
            conn.commit()
            print(
                f"[Migration] 異常說明項目已回填 is_note=True，共 {backfill.rowcount} 筆"
            )


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


async def _run_and_log(module_name: str, coro, triggered_by: str = "scheduler"):
    """
    執行 sync coroutine 並將結果寫入 module_sync_log。
    不論成功或失敗都會寫入，確保紀錄完整。
    """
    from app.models.module_sync_log import ModuleSyncLog
    from app.core.database import SessionLocal

    started = _utcnow()
    result = None
    exc_str = None

    try:
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

    db = SessionLocal()
    try:
        db.add(
            ModuleSyncLog(
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
            )
        )
        db.commit()
    except Exception as log_exc:
        print(f"[AutoSync][Log] 寫入失敗：{log_exc}")
    finally:
        db.close()

    return result


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
    """定時同步任務：Ragic → SQLite（所有硬編碼模組）"""
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
    from app.services.ihg_room_maintenance_sync import sync_from_ragic as sync_ihg_rm

    await _run_and_log("客房保養", sync_rm())
    await _run_and_log("倉庫庫存", sync_inv())
    await _run_and_log("客房保養明細", sync_rmd())
    await _run_and_log("飯店週期保養", sync_pm())
    await _run_and_log("B4F巡檢", sync_b4f())
    await _run_and_log("RF巡檢", sync_rf())
    await _run_and_log("B2F巡檢", sync_b2f())
    await _run_and_log("B1F巡檢", sync_b1f())
    await _run_and_log("商場週期保養", sync_mall_pm())
    await _run_and_log("全棟例行維護", sync_full_bldg_pm())
    await _run_and_log("大直工務報修", sync_dazhi())
    await _run_and_log("樂群工務報修", sync_luqun())
    await _run_and_log("保全巡檢", sync_security())
    await _run_and_log("商場工務巡檢", sync_mfi())
    await _run_and_log("飯店每日巡檢", sync_hdi())
    await _run_and_log("IHG客房保養", sync_ihg_rm())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup / shutdown hooks."""
    # ── Startup ──────────────────────────────────────────────────────────────
    print(f"[Portal] Starting — environment: {settings.ENV}")

    # 確保所有 ORM model 已被 import，讓 Base.metadata 知道所有表格
    import app.models.room_maintenance  # noqa: F401
    import app.models.inventory  # noqa: F401
    import app.models.room_maintenance_detail  # noqa: F401
    import app.models.room  # noqa: F401
    import app.models.periodic_maintenance  # noqa: F401
    import app.models.mall_periodic_maintenance  # noqa: F401
    import app.models.full_building_maintenance  # noqa: F401
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
    import app.models.ragic_app_directory  # noqa: F401
    import app.models.mall_facility_inspection  # noqa: F401
    import app.models.hotel_daily_inspection  # noqa: F401
    import app.models.ihg_room_maintenance  # noqa: F401
    import app.models.menu_config  # noqa: F401

    # B4F 扁平化遷移：刪除舊 batch 表 + 檢查 item 表欄位（必須在 create_all 之前）
    _migrate_b4f_flatten()
    print("[Portal] B4F flatten migration checked.")

    # 建立尚未存在的資料表（不影響已有表格）
    Base.metadata.create_all(bind=engine)
    print("[Portal] Database tables ensured.")

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

    # 輕量欄位補丁：為現有 pm_batch_item 加入新欄位（若尚未存在）
    _migrate_pm_batch_item()
    print("[Portal] PM batch_item migration checked.")

    # 輕量欄位補丁：為 luqun_repair_case 加入 images_json（若尚未存在）
    _migrate_luqun_repair_images()
    print("[Portal] luqun_repair_case images_json migration checked.")

    # 輕量欄位補丁：為 dazhi_repair_case 加入 images_json（若尚未存在）
    _migrate_dazhi_repair_images()
    print("[Portal] dazhi_repair_case images_json migration checked.")

    # 清除保全巡檢中的拍照欄位 item（Ragic 必填但不屬於巡檢評分項目）
    _cleanup_security_patrol_photo_items()
    print("[Portal] Security patrol photo items cleanup checked.")

    # 保全巡檢 is_note 欄位遷移 + 回填異常說明項目
    _migrate_security_patrol_is_note()
    print("[Portal] Security patrol is_note migration checked.")

    # 樂群扣款專櫃欄位補丁（2026-04-24）
    _migrate_luqun_counter_name()
    print("[Portal] Luqun deduction_counter_name migration checked.")

    # 選單設定補丁（2026-04-28）：隱藏舊 custom_1777348120465，補齊 mall-pm-group 子項 DB 記錄
    _seed_menu_config_mall_pm_group()

    # 客房主檔 seed（若 rooms 表為空，自動填入樓層 × 房號資料）
    from app.services.room_seed import seed_rooms

    seed_rooms()
    print("[Portal] Room seed checked.")

    # 排程對齊整點自動同步（預設 30 分鐘 → :00/:30）；啟動時不再立即同步，
    # 以確保伺服器能立即接受請求並從本地 DB 回傳資料。
    # 若需立即同步，請在前端點擊「同步資料」按鈕。
    _scheduler.add_job(
        _auto_sync,
        trigger=make_cron_trigger(30),   # CronTrigger：整點對齊，預設 :00 / :30
        id="module_auto_sync",
        replace_existing=True,
    )

    # 依各 RagicConnection 的 sync_interval 建立個別排程任務
    _init_ragic_connection_jobs()

    _scheduler.start()
    print("[Portal] AutoSync scheduler started (cron-aligned, default every 30 minutes).")

    yield
    # ── Shutdown ──────────────────────────────────────────────────────────────
    _scheduler.shutdown(wait=False)
    print("[Portal] Shutting down.")


app = FastAPI(
    title="集團 Portal API",
    version="1.0.0",
    description="Hotel/Mall 集團管理 Portal — 後端 API",
    lifespan=lifespan,
    redirect_slashes=False,   # 防止 307 繞過 Vite proxy 觸發 CORS
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

# 既有模組
app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["認證"])
app.include_router(users.router, prefix=f"{API_PREFIX}/users", tags=["使用者"])
app.include_router(tenants.router, prefix=f"{API_PREFIX}/tenants", tags=["據點"])
app.include_router(ragic.router, prefix=f"{API_PREFIX}/ragic", tags=["Ragic"])
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

# ── 新增：樂群工務報修 ────────────────────────────────────────────────────────
app.include_router(
    luqun_repair.router,
    prefix=f"{API_PREFIX}/luqun-repair",
    tags=["樂群工務報修"],
)

# ── 新增：大直工務部 ──────────────────────────────────────────────────────────
app.include_router(
    dazhi_repair.router,
    prefix=f"{API_PREFIX}/dazhi-repair",
    tags=["大直工務部"],
)

# ── 新增：★工項類別分析（整合樂群+大直）────────────────────────────────────
app.include_router(
    work_category_analysis.router,
    prefix=f"{API_PREFIX}/work-category-analysis",
    tags=["工項類別分析"],
)

# ── 新增：預算管理 ─────────────────────────────────────────────────────────────
app.include_router(
    budget.router,
    prefix=f"{API_PREFIX}/budget",
    tags=["預算管理"],
)

# ── 新增：飯店每日巡檢 ───────────────────────────────────────────────────────
app.include_router(
    hotel_daily_inspection.router,
    prefix=f"{API_PREFIX}/hotel-daily-inspection",
    tags=["飯店每日巡檢"],
)

# ── 新增：選單設定（改名 + 排序 + 歷史）──────────────────────────────────────
app.include_router(
    menu_config.router,
    prefix=f"{API_PREFIX}/settings/menu-config",
    tags=["選單設定"],
)

# ── 前端靜態檔案（SPA 模式，放在所有路由之後）────────────────────────────
import os as _os
import mimetypes as _mimetypes
from fastapi.staticfiles import StaticFiles as _StaticFiles
from fastapi.responses import FileResponse as _FileResponse

_frontend_dist = _os.path.join(_os.path.dirname(__file__), "..", "..", "frontend", "dist")
if _os.path.isdir(_frontend_dist):
    # /assets 靜態資源用 StaticFiles（有 ETag/快取標頭）
    _assets_dir = _os.path.join(_frontend_dist, "assets")
    if _os.path.isdir(_assets_dir):
        app.mount("/assets", _StaticFiles(directory=_assets_dir), name="assets")

    # SPA 萬用路由：所有未匹配路徑回傳 index.html，讓 React Router 處理
    # 注意：此路由必須在所有 include_router 之後宣告，否則會遮蔽 API 路由
    @app.get("/{full_path:path}", include_in_schema=False)
    async def _serve_spa(full_path: str):
        # 根目錄下的真實靜態檔（favicon.ico、robots.txt 等）
        candidate = _os.path.join(_frontend_dist, full_path)
        if full_path and _os.path.isfile(candidate):
            media_type, _ = _mimetypes.guess_type(candidate)
            return _FileResponse(candidate, media_type=media_type or "application/octet-stream")
        # SPA fallback：交由前端 React Router 路由
        return _FileResponse(
            _os.path.join(_frontend_dist, "index.html"),
            media_type="text/html",
        )

    print(f"[Portal] Frontend static files (SPA mode) served from: {_frontend_dist}")