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

── 比對優先序（2026-09-01 改版，見下方「欄位權責」的背景）─────────────────
  1. source_department_id 已連結 → 直接比對到該筆
  2. **部門名稱**在週採未連結列中**唯一命中** → 視為同一筆，回填
     source_department_id（同名部門跨公司存在時不自動連結，記 warning，
     請在部門主檔頁面手動「連結主檔部門」）
  3. 都比對不到 → 新增

  ⚠ 2026-09-01 前第 2 層是「公司＋部門名稱」比對。改版原因：company 改為
    週採自行輸入（見下），公司字串刻意與主檔不同，舊比對永遠對不上。

── 欄位權責（2026-09-01 Samuel 裁示改版）────────────────────────────────────
  同步覆蓋：dept_name（← RefDepartment.name）
  絕不覆蓋：company／dept_code／owner_user_id／is_active（週採自維護）

  ⚠ **company 從「同步覆蓋」改為「週採自維護」**：公司對「公司名稱」並不
    統一，週採要用的公司字串不一定等於主檔的 Company.name（company 是
    週採多處業務流程的字串鍵：彙整單「週期+公司+核准月份」、週期設定的
    公司篩選、請購單快照）。新增鏡像列時帶 Company.name 當**初始值**，
    之後同步絕不再碰。後端 update_department 同日起放行編輯 company
    （鏡像列亦可），dept_name 仍鎖定。

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
        # ⚠️ 2026-09-01 使用者裁示：週採的 company 改為**自行輸入**（公司對名稱
        #    本來就不統一，主檔的公司名不一定是週採要用的字串），因此：
        #    ① company 從「同步覆蓋」改為「週採自維護」——只在新增鏡像列時帶
        #       Company.name 當初始值，之後同步**絕不再碰**。
        #    ② 第二層名稱比對不能再用 (company, dept_name)（公司字串刻意不同，
        #       永遠對不上），改為 **dept_name 單獨比對、且全表唯一命中才收編**；
        #       同名部門跨公司存在時跳過並記 warning（重名的請在
        #       cycle-purchase/masters/departments 用「連結主檔部門」手動連結）。
        #    「唯一命中」是**兩邊都要唯一**：週採未連結端同名（不知道收編哪筆）
        #    或主檔端同名（兩家公司都有「工程部」，收給誰都是用猜的）都不自動連。
        _unlinked = [r for r in all_rows if not r.source_department_id]
        by_dept_name: dict = {}
        _dup_names = set()
        for r in _unlinked:
            if r.dept_name in by_dept_name:
                _dup_names.add(r.dept_name)
            by_dept_name[r.dept_name] = r
        _src_name_count: dict = {}
        for s in sources:
            if s["dept_name"]:
                _src_name_count[s["dept_name"]] = _src_name_count.get(s["dept_name"], 0) + 1
        _dup_names |= {n for n, c in _src_name_count.items() if c > 1}
        for n in _dup_names:
            by_dept_name.pop(n, None)   # 重名 → 不自動連結，只能手動

        for src in sources:
            source_id = src["source_department_id"]
            company = src["company"]
            dept_name = src["dept_name"]

            if not company or not dept_name:
                skipped += 1
                continue  # 來源端理論上不該有空值（NOT NULL），防呆略過

            try:
                # ── 比對優先序：source_department_id → 部門名稱唯一命中 ──
                row = by_source.get(source_id)
                auto_adopt = False
                if row is None:
                    if dept_name in _dup_names:
                        warnings.append(
                            f"{company}／{dept_name}（來源 id={source_id}）：部門名稱重複"
                            f"（主檔端或週採未連結端有多筆同名），無法自動判定對應，"
                            f"本筆不自動連結。請在 週期採購 → 部門主檔 手動「連結主檔部門」"
                        )
                    else:
                        row = by_dept_name.get(dept_name)
                        auto_adopt = row is not None

                if row is not None:
                    old_name = row.dept_name
                    changed = (
                        row.dept_name != dept_name
                        or row.source_department_id != source_id
                    )
                    # company **不碰**（週採自維護）；只在收編當下 company 還是
                    # 空字串的防呆情況補上主檔值
                    if not row.company:
                        row.company = company
                        changed = True
                    row.dept_name = dept_name
                    row.source_department_id = source_id
                    if auto_adopt:
                        by_dept_name.pop(old_name, None)
                        logger.info(
                            f"[CP Department Sync] 依部門名稱唯一命中，自動收編："
                            f"週採 id={row.id}「{row.company}／{old_name}」← 主檔 "
                            f"{company}／{dept_name}（id={source_id}）"
                        )
                    if changed:
                        updated += 1
                    else:
                        unchanged += 1
                else:
                    # ── 新增：dept_code 沒有天然來源，先帶佔位值；company 帶
                    #    主檔的 Company.name 當**初始值**（之後由週採自行維護，
                    #    同步不再覆蓋——2026-09-01 裁示）──────────────────────
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
