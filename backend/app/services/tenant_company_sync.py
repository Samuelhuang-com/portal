"""
tenant_company_sync.py — 據點主檔鏡像同步：系統設定（公司/部門管理）→ 人員管理所屬據點

2026-09-01 Samuel 裁示：**人員管理「新增使用者 → 所屬據點」的下拉選項，
必須等於「系統設定 → 公司/部門管理」維護的公司名稱清單。**
因此 `tenants` 退化成 `reference_data.Company` 的鏡像副本：

    系統設定 → 公司/部門管理（reference_data.Company）← 唯一真實來源
        └─ 本檔 ─────────────────────▶ portal.db  tenants
                                          └─▶ GET /api/v1/tenants（只回 is_active）
                                                └─▶ Users.tsx「所屬據點」下拉

本檔在 sync_tool.py MODULES / main.py _auto_sync / RagicConnections.tsx
ALL_MODULES 中，與「週期採購部門」同一批次（同樣是「非 Ragic、來源是
portal.db Company」的鏡像同步，彼此沒有先後相依）。

── 為什麼不直接把 users.tenant_id 改成指向 companies.id ────────────────────
1. `tenants.id` 是 String(36) UUID，`companies.id` 是 Integer，型別不同。
2. `users.tenant_id`／`user_roles.tenant_id`／`ragic_connections.tenant_id`
   三處外鍵都綁著 `tenants.id`，另外 `audit_logs` 也帶 tenant_id。
   → 保留 id 與 FK 完全不動，只加 `source_company_id` 當跨主檔對照鍵
     （比照 cycle_purchase_vendor_sync.py 的 source_vendor_id 模式）。

── 比對優先序（比照 cycle_purchase_* 兩支鏡像同步的既有慣例）───────────────
  1. source_company_id 已連結 → 直接比對到該筆
  2. 據點名稱與公司名稱完全相同 → 視為同一筆，回填 source_company_id
     （這一層負責把原本手動建的據點一次性合併進來，不需另寫 backfill）
  3. 都比對不到 → 新增

── 欄位權責 ────────────────────────────────────────────────────────────────
  同步覆蓋：name（← Company.name）／is_active（← Company.is_active）
  新增時帶：code = `CMP-{來源Company.id}`（Company 沒有代碼欄位，先帶佔位值；
                                            String(20) 容得下）
            type = "company"
  絕不覆蓋：既有列的 code／type（可能已被其他地方引用，且無來源可對應）

  ⚠ Company.name 是 NOT NULL，不像 vendor_sync 需要處理「來源端沒填就別洗掉」。

  ⚠ is_active 這裡**是**同步欄位（跟 cycle_purchase 兩支相反）：據點下拉直接
    吃 `GET /tenants` 的 `is_active == True`，公司停用後若不跟著停用，停用的
    公司仍會出現在下拉，就達不到使用者要的「下拉＝公司清單」。

── 刻意不做的事 ────────────────────────────────────────────────────────────
1. **不主動停用／刪除 source_company_id IS NULL 的列**（＝本地自建的舊據點）。
   §9 規則 2。⚠️ 唯一的例外是上面比對優先序的第 2 層：名稱剛好與某家公司
   完全相同的 NULL 列會被**收編**成該公司的鏡像（回填 source_company_id）——
   那正是 §9 規則 3 要的效果（把既有手動建檔一次性合併進來）。
   除此之外同步不會去動它們。舊據點的一次性停用與使用者改掛，由
   `backend/scripts/migrate_tenants_to_companies.py` 執行，不放在同步裡
   ——否則每輪同步都會去改業務資料，且永遠不能再手動新增據點。
2. **來源端刪公司時不刪也不停用鏡像**（§9 規則 6）。`users.tenant_id` 是
   NOT NULL 外鍵，硬刪必失敗；停用會讓該據點底下的使用者變成指向停用據點。
   孤兒只在回傳的 orphans 計數中呈現。
3. 「比對不到／略過」記進 `warnings` 而**不是** `errors`（§9 規則 8）：
   main.py 只要 errors 非空就把同步標成 partial（黃燈），來源端只要有一次
   名稱重複就會永遠黃燈。
"""
import logging
from typing import Optional

from app.core.database import SessionLocal
from app.models.reference_data import Company
from app.models.tenant import Tenant
from app.services.sync_dispatcher import register

logger = logging.getLogger(__name__)


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def sync_companies_to_tenants(db) -> dict:
    """
    portal.db Company → portal.db tenants 單向鏡像同步（**同步版**，吃現成 Session）。

    ⚠️ 拆成同步版的理由：`reference_data.py` 的公司新增／改名／停用三個端點是
    一般 `def` 路由，需要在 commit 之後立刻把據點清單推平（否則使用者剛在
    公司/部門管理新增一家公司，回到人員管理下拉還看不到，要等排程 45 分鐘）。
    從同步路由裡叫 async 函式得 `asyncio.run()`，在 FastAPI 的 threadpool 裡
    做這件事既難看又容易踩到 event loop，不如把邏輯本體寫成同步的。

    本函式**會 commit**，但**不 close** 傳入的 Session（由呼叫端負責）。
    """
    logger.info("[Tenant Sync] 開始自系統設定公司主檔同步據點...")

    fetched = 0
    created = updated = unchanged = skipped = 0
    orphans = 0
    warnings: list = []
    errors: list = []

    try:
        companies = db.query(Company).order_by(Company.id).all()
        fetched = len(companies)

        all_tenants = db.query(Tenant).all()
        by_source = {t.source_company_id: t for t in all_tenants if t.source_company_id}
        by_name = {t.name: t for t in all_tenants}

        for company in companies:
            source_id = str(company.id)
            name = _clean(company.name)

            if not name:
                skipped += 1
                continue  # 來源端 NOT NULL，理論上不會發生；防呆略過

            try:
                # ── 比對優先序：source_company_id → 名稱 ──────────────────
                row = by_source.get(source_id)
                if row is None:
                    row = by_name.get(name)

                # 比對到的那筆已經是「別家公司」的鏡像 → 不搶佔
                if row is not None and row.source_company_id and row.source_company_id != source_id:
                    warnings.append(
                        f"公司「{name}」（來源 id={source_id}）比對到的據點 "
                        f"id={row.id} 已連結至來源 id={row.source_company_id}，本筆略過"
                        f"（Company.name 有 unique 保護，理論上不會發生）"
                    )
                    skipped += 1
                    continue

                if row is not None:
                    # 舊 key 先從索引移除，理由同 cycle_purchase 兩支：避免改名後
                    # 舊 key 還指向這一列，下一筆來源可能誤比對到它
                    if by_name.get(row.name) is row:
                        by_name.pop(row.name, None)

                    changed = (
                        row.name != name
                        or row.is_active != company.is_active
                        or row.source_company_id != source_id
                    )
                    row.name = name
                    row.is_active = company.is_active
                    row.source_company_id = source_id
                    # code／type 刻意不覆蓋：既有列的 code 可能已被引用，
                    # 且 Company 沒有對應來源欄位。
                    if changed:
                        updated += 1
                    else:
                        unchanged += 1
                else:
                    # ── 新增：code 沒有天然來源，帶 CMP-{id} 佔位 ──────────
                    code = f"CMP-{source_id}"
                    if db.query(Tenant).filter(Tenant.code == code).first():
                        warnings.append(
                            f"公司「{name}」要新增的據點代碼 {code} 已被其他據點佔用，本筆略過"
                        )
                        skipped += 1
                        continue
                    row = Tenant(
                        code=code,
                        name=name,
                        type="company",
                        is_active=company.is_active,
                        source_company_id=source_id,
                    )
                    db.add(row)
                    created += 1

                by_source[source_id] = row
                by_name[name] = row

            except Exception as exc:
                errors.append(f"公司「{name}」：{exc}")
                logger.warning(f"[Tenant Sync] 公司「{name}」失敗：{exc}")

        db.commit()

        # 孤兒＝據點端有鏡像、來源端公司已被刪除（僅計數示警，不刪不停用）
        source_ids = {str(c.id) for c in companies}
        orphans = sum(
            1 for t in db.query(Tenant).all()
            if t.source_company_id and t.source_company_id not in source_ids
        )

        logger.info(
            f"[Tenant Sync] 完成：新增 {created} 筆，更新 {updated} 筆，"
            f"無異動 {unchanged} 筆，略過 {skipped} 筆，孤兒 {orphans} 筆，"
            f"警告 {len(warnings)} 筆，錯誤 {len(errors)} 筆"
        )
        for w in warnings:
            logger.warning(f"[Tenant Sync] {w}")
    except Exception as exc:
        db.rollback()
        logger.error(f"[Tenant Sync] DB 寫入失敗：{exc}")
        return {"fetched": fetched, "upserted": 0, "created": 0, "updated": 0,
                "unchanged": 0, "skipped": skipped, "orphans": 0,
                "warnings": warnings, "errors": errors + [str(exc)]}

    return {
        "fetched": fetched,
        "upserted": created + updated,
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "skipped": skipped,
        "orphans": orphans,
        "warnings": warnings,
        "errors": errors,
    }


@register("tenant_company")
async def sync_from_reference() -> dict:
    """
    sync_tool.py MODULES／main.py _auto_sync 的進入點（async wrapper）。
    自行開關 Session，實際邏輯全在 `sync_companies_to_tenants()`。
    """
    db = SessionLocal()
    try:
        return sync_companies_to_tenants(db)
    finally:
        db.close()
