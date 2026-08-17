"""
cycle_purchase_department_sync.py — 部門主檔鏡像同步：系統設定（公司/部門管理）→ 週期採購

2026-08-17 Samuel 確認之決策：**公司/部門關聯的唯一真實來源是**
`reference_data.py` 的 `Company`/`RefDepartment`（portal.db，「系統設定 →
公司/部門管理」頁面維護），週期採購的 `cycle_purchase_departments` 退化成
它在 cycle-purchase.db 的鏡像副本。往後 Portal 任何模組要用到「公司」
「部門」都應該走這條鏈，不要各自另建一份主檔：

    系統設定 → 公司/部門管理（reference_data.py Company/RefDepartment）
        └─ 本檔 ─────────────────────▶ cycle-purchase.db  cycle_purchase_departments

因此本檔在 sync_tool.py MODULES / main.py _auto_sync 中，應排在跟
「週期採購供應商」同一批次（都是「非 Ragic、來源是 portal.db」的鏡像同步，
彼此沒有先後相依）。

── 為什麼不直接跨庫關聯 ──────────────────────────────────────────────────────
1. 跨 SQLite 檔案不能建 FK，本專案也明訂不做 ATTACH DATABASE
   （見 app/core/cycle_purchase_database.py 開頭）。
2. cycle_purchase_departments.id（Integer）已被 cost_centers.department_id
   （RESTRICT）等多處外鍵綁住，改成對接 RefDepartment.id 要動既有資料，
   風險過高。→ 保留 id 與 FK 完全不動，只加 source_department_id 當跨庫
   對照鍵（比照 cycle_purchase_vendor_sync.py 的 source_vendor_id 模式）。

── 比對優先序（比照 cycle_purchase_vendor_sync.py 的既有慣例）────────────────
  1. source_department_id 已連結 → 直接比對到該筆
  2. 公司＋部門名稱完全相同 → 視為同一筆，回填 source_department_id
     （這一層負責把週採原本手動建的部門一次性合併進來）
  3. 都比對不到 → 新增

── 欄位權責 ──────────────────────────────────────────────────────────────────
  同步覆蓋：company（← Company.name）／dept_name（← RefDepartment.name）
  絕不覆蓋：dept_code／owner_user_id／is_active（週採自維護，前端仍可編輯）

  ⚠ 來源端的 Company.name／RefDepartment.name 兩者都是 NOT NULL，不像
  vendor_sync 那樣需要處理「來源端沒填就別洗掉」的情況——這兩個欄位一律
  無條件覆蓋，因為來源一定有值。

  dept_code 沒有天然的來源可以沿用（RefDepartment 沒有代碼欄位），新增時
  自動帶 `DEPT-{來源RefDepartment.id}` 佔位，同步之後不再去動它，使用者
  可在「週期採購 → 部門主檔」頁面自行改成有意義的代碼（與 Samuel 確認）。

── 刻意不做的事 ──────────────────────────────────────────────────────────────
  來源端刪除公司/部門時，本檔**不會**刪除或停用週採端對應資料。理由：
  `cost_centers.department_id` 是 RESTRICT，硬刪會直接失敗；而 is_active
  屬於週採自維護欄位，同步不該代為關掉。孤兒資料只在回傳的 orphans 計數
  中呈現。
"""
import logging
from typing import Optional

from app.core.cycle_purchase_database import CyclePurchaseSessionLocal
from app.core.database import SessionLocal
from app.models.reference_data import Company, RefDepartment
from app.models.cycle_purchase_reference import CyclePurchaseDepartment
from app.services.sync_dispatcher import register

logger = logging.getLogger(__name__)


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@register("cycle_purchase_department")
async def sync_from_reference() -> dict:
    """
    portal.db Company/RefDepartment → cycle-purchase.db cycle_purchase_departments
    單向鏡像同步。回傳 { fetched, upserted, created, updated, unchanged, skipped,
    orphans, warnings, errors }（標準格式，比照 cycle_purchase_vendor_sync.py）。
    """
    logger.info("[CP Department Sync] 開始自系統設定公司/部門主檔同步...")

    # ── 1. 讀來源（portal.db，唯讀）────────────────────────────────────────
    src_db = SessionLocal()
    try:
        rows = (
            src_db.query(RefDepartment, Company)
            .join(Company, RefDepartment.company_id == Company.id)
            .all()
        )
        sources = [
            {
                "source_department_id": str(dept.id),
                "company": _clean(company.name),
                "dept_name": _clean(dept.name),
            }
            for dept, company in rows
        ]
    except Exception as exc:
        logger.error(f"[CP Department Sync] 讀取 portal.db Company/RefDepartment 失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "created": 0, "updated": 0,
                "unchanged": 0, "skipped": 0, "orphans": 0,
                "warnings": [], "errors": [str(exc)]}
    finally:
        src_db.close()

    fetched = len(sources)
    created = updated = unchanged = skipped = 0
    warnings: list = []
    errors: list = []

    # ── 2. 寫入目標（cycle-purchase.db）───────────────────────────────────
    db = CyclePurchaseSessionLocal()
    try:
        all_rows = db.query(CyclePurchaseDepartment).all()
        by_source = {r.source_department_id: r for r in all_rows if r.source_department_id}
        by_name = {(r.company, r.dept_name): r for r in all_rows}

        for src in sources:
            source_id = src["source_department_id"]
            company = src["company"]
            dept_name = src["dept_name"]

            if not company or not dept_name:
                skipped += 1
                continue  # 來源端理論上不該有空值（NOT NULL），防呆略過

            try:
                # ── 比對優先序：source_department_id → 公司+部門名稱 ──────
                row = by_source.get(source_id)
                if row is None:
                    row = by_name.get((company, dept_name))

                # 比對到的那筆已經是「別家來源」的鏡像 → 不搶佔
                if row is not None and row.source_department_id and row.source_department_id != source_id:
                    warnings.append(
                        f"{company}／{dept_name}（來源 id={source_id}）比對到的週採部門 "
                        f"id={row.id} 已連結至來源 id={row.source_department_id}，本筆略過"
                        f"（通常代表系統設定端有兩個公司/部門的公司+名稱組合恰好重複，"
                        f"但這在 RefDepartment 有 UniqueConstraint(name, company_id) 保護下"
                        f"理論上不會發生）"
                    )
                    skipped += 1
                    continue

                if row is not None:
                    # 舊 key 先從索引移除，理由同 vendor_sync：避免改名後舊 key
                    # 還指向這一列，下一筆來源可能誤比對到它
                    old_key = (row.company, row.dept_name)
                    if by_name.get(old_key) is row:
                        by_name.pop(old_key, None)

                    changed = (
                        row.company != company
                        or row.dept_name != dept_name
                        or row.source_department_id != source_id
                    )
                    row.company = company
                    row.dept_name = dept_name
                    row.source_department_id = source_id
                    if changed:
                        updated += 1
                    else:
                        unchanged += 1
                else:
                    # ── 新增：dept_code 沒有天然來源，先帶佔位值 ───────────
                    row = CyclePurchaseDepartment(
                        company=company,
                        dept_code=f"DEPT-{source_id}",
                        dept_name=dept_name,
                        is_active=True,
                        source_department_id=source_id,
                    )
                    db.add(row)
                    created += 1

                by_source[source_id] = row
                by_name[(company, dept_name)] = row

            except Exception as exc:
                errors.append(f"{company}／{dept_name}：{exc}")
                logger.warning(f"[CP Department Sync] {company}／{dept_name} 失敗：{exc}")

        db.commit()

        # 孤兒＝週採端有、系統設定端已無對應（僅計數示警，不刪不停用）
        source_ids = {s["source_department_id"] for s in sources}
        orphans = sum(
            1 for r in db.query(CyclePurchaseDepartment).all()
            if r.source_department_id and r.source_department_id not in source_ids
        )

        logger.info(
            f"[CP Department Sync] 完成：新增 {created} 筆，更新 {updated} 筆，"
            f"無異動 {unchanged} 筆，略過 {skipped} 筆，孤兒 {orphans} 筆，"
            f"警告 {len(warnings)} 筆，錯誤 {len(errors)} 筆"
        )
        for w in warnings:
            logger.warning(f"[CP Department Sync] {w}")
    except Exception as exc:
        db.rollback()
        logger.error(f"[CP Department Sync] DB 寫入失敗：{exc}")
        return {"fetched": fetched, "upserted": 0, "created": 0, "updated": 0,
                "unchanged": 0, "skipped": skipped, "orphans": 0,
                "warnings": warnings, "errors": errors + [str(exc)]}
    finally:
        db.close()

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
