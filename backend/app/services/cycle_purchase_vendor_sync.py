"""
cycle_purchase_vendor_sync.py — 廠商主檔鏡像同步：合約模組 → 週期採購

2026-08-10 Samuel 確認之決策：**廠商資料的唯一真實來源是合約模組的 vendors**
（portal.db），週期採購的 cycle_purchase_vendors 退化成它在 cycle-purchase.db
的鏡像副本。往後 Portal 任何模組要用到「廠商」資料，一律沿用這條鏈：

    Ragic 廠商資料表 Sheet 15
        └─ vendor_sync.py ────────────────▶ portal.db  vendors           （主檔）
              └─ 本檔 ─────────────────────▶ cycle-purchase.db  cycle_purchase_vendors

因此本檔在 sync_tool.py MODULES / main.py _auto_sync 中，**必須排在「廠商資料」
之後**，否則同步到的會是上一輪的舊資料。

── 為什麼不直接跨庫關聯 ──────────────────────────────────────────────────────
1. 跨 SQLite 檔案不能建 FK，本專案也明訂不做 ATTACH DATABASE
   （見 app/core/cycle_purchase_database.py 開頭）。
2. cycle_purchase_vendors.id（Integer）已被三處外鍵綁住：
   cycle_purchase_pos.vendor_id（RESTRICT, NOT NULL）、
   cycle_purchase_summaries.vendor_id、cycle_purchase_item_mappings.vendor_id。
   改成合約端的 VND-NNNN 字串鍵要動三張表既有資料，風險過高。
   → 保留 id 與 FK 完全不動，只加 source_vendor_id 當跨庫對照鍵。

── 比對優先序（比照 vendor_sync.py 的既有慣例）────────────────────────────────
  1. source_vendor_id 已連結 → 直接比對到該筆
  2. 統一編號（tax_id）非空且完全相同 → 視為同一筆，回填 source_vendor_id
  3. 供應商名稱（vendor_name）完全相同 → 視為同一筆，回填 source_vendor_id
     （這一層負責把週採原本手動建的資料一次性合併進來）
  4. 都比對不到 → 新增，vendor_code 直接沿用合約端的 VND-NNNN

── 欄位權責 ──────────────────────────────────────────────────────────────────
  同步覆蓋：vendor_name / tax_id / contact_name(←contact_person) / contact_phone(←phone)
  絕不覆蓋：payment_terms / notes / is_active（週採自維護，前端仍可編輯）

  ⚠ 除了 vendor_name（必填）以外，其餘三欄一律「**來源端有值才覆蓋**」，比照
  vendor_sync.py:124 的既有寫法。若無條件覆蓋，合約端沒填統編的廠商會把週採端
  本來手動維護的統編洗成空——而統編一旦被清空，下次同步的第 2 層比對也跟著
  失效，錯誤會擴散。

── 刻意不做的事 ──────────────────────────────────────────────────────────────
  合約端刪除廠商時，本檔**不會**刪除或停用週採端對應資料。理由：
  cycle_purchase_pos.vendor_id 是 RESTRICT，硬刪會直接失敗；而 is_active 屬於
  週採自維護欄位，同步不該代為關掉。孤兒資料只在回傳的 orphans 計數中呈現。
"""
import logging
from typing import Optional

from app.core.cycle_purchase_database import CyclePurchaseSessionLocal
from app.core.database import SessionLocal
from app.core.time import twnow
from app.models.contract import Vendor
from app.models.cycle_purchase_vendor import CyclePurchaseVendor
from app.services.sync_dispatcher import register

logger = logging.getLogger(__name__)


def _clean(value: Optional[str]) -> Optional[str]:
    """去除空白；空字串／N/A／- 一律視為無值回 None"""
    if value is None:
        return None
    text = str(value).strip()
    if text in ("", "N/A", "-"):
        return None
    return text


def _unique_vendor_code(preferred: str, used_codes: set) -> str:
    """
    vendor_code 在 cycle_purchase_vendors 是 unique NOT NULL。
    優先直接沿用合約端的 VND-NNNN；萬一該代碼已被週採本地自建資料占用，
    退而加 -2、-3 後綴。

    注意：unique 衝突是在 db.commit() 才會爆 IntegrityError，屆時整批 rollback
    （本檔是 all-or-nothing，逐筆 try/except 攔不到）。所以這裡是「事前避免衝突
    發生」，不是「事後容錯」。
    """
    if preferred not in used_codes:
        return preferred
    n = 2
    while f"{preferred}-{n}" in used_codes:
        n += 1
    return f"{preferred}-{n}"


@register("cycle_purchase_vendor")
async def sync_from_contract() -> dict:
    """
    portal.db vendors → cycle-purchase.db cycle_purchase_vendors 單向鏡像同步。
    回傳 { fetched, upserted, created, updated, unchanged, skipped, orphans,
           warnings, errors }
    （fetched/upserted/errors 為 main.py _run_loop / sync_tool.py 共用的標準格式）

    ⚠ 「略過」歸類在 warnings 不是 errors：main.py:1078 只要 errors 非空就把
    同步結果標成 partial（黃燈）。合約端只要存在同名／同統編的重複廠商就會有
    略過，若記進 errors，這個模組會永遠停在黃燈，久了就沒人看了。
    """
    logger.info("[CP Vendor Sync] 開始自合約模組廠商主檔同步...")

    # ── 1. 讀來源（portal.db，唯讀）────────────────────────────────────────
    src_db = SessionLocal()
    try:
        sources = [
            {
                "vendor_id": v.vendor_id,
                "vendor_name": _clean(v.vendor_name),
                "tax_id": _clean(v.tax_id),
                "contact_name": _clean(v.contact_person),
                "contact_phone": _clean(v.phone),
            }
            for v in src_db.query(Vendor).all()
        ]
    except Exception as exc:
        logger.error(f"[CP Vendor Sync] 讀取 portal.db vendors 失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "created": 0, "updated": 0,
                "unchanged": 0, "skipped": 0, "orphans": 0,
                "warnings": [], "errors": [str(exc)]}
    finally:
        src_db.close()

    fetched = len(sources)
    created = updated = unchanged = skipped = 0
    warnings: list = []
    errors: list = []
    now = twnow()

    # ── 2. 寫入目標（cycle-purchase.db）───────────────────────────────────
    db = CyclePurchaseSessionLocal()
    try:
        all_rows = db.query(CyclePurchaseVendor).all()
        by_source = {r.source_vendor_id: r for r in all_rows if r.source_vendor_id}
        by_tax = {r.tax_id: r for r in all_rows if r.tax_id}
        by_name = {r.vendor_name: r for r in all_rows if r.vendor_name}
        used_codes = {r.vendor_code for r in all_rows if r.vendor_code}

        for src in sources:
            name = src["vendor_name"]
            if not name:
                skipped += 1
                continue  # 沒有名稱的來源資料跳過（比照 vendor_sync.py 行為）

            vendor_id = src["vendor_id"]
            tax_id = src["tax_id"]

            try:
                # ── 比對優先序：source_vendor_id → 統一編號 → 名稱 ──────────
                row = by_source.get(vendor_id)
                if row is None and tax_id:
                    row = by_tax.get(tax_id)
                if row is None:
                    row = by_name.get(name)

                # 比對到的那筆已經是「別家來源」的鏡像 → 不搶佔（避免 unique 衝突）
                if row is not None and row.source_vendor_id and row.source_vendor_id != vendor_id:
                    warnings.append(
                        f"{vendor_id}（{name}）比對到的週採供應商 id={row.id} "
                        f"已連結至 {row.source_vendor_id}，本筆略過"
                        f"（合約端 vendor_name 有 unique 約束，所以這通常代表"
                        f"合約端有兩家廠商填了相同的統一編號）"
                    )
                    skipped += 1
                    continue

                if row is not None:
                    # ── 更新：只覆蓋受控欄位 ────────────────────────────────
                    # 舊 key 先從索引移除，否則合約端改名／改統編後，舊 key 仍
                    # 指向這一列，下一筆來源可能誤比對到它而被當成「已連結別家」
                    # 略過（只會多略過不會寫錯，但錯誤訊息會讓人看不懂）。
                    if row.tax_id and by_tax.get(row.tax_id) is row:
                        by_tax.pop(row.tax_id, None)
                    if row.vendor_name and by_name.get(row.vendor_name) is row:
                        by_name.pop(row.vendor_name, None)

                    changed = (
                        row.vendor_name != name
                        or (tax_id is not None and row.tax_id != tax_id)
                        or (src["contact_name"] is not None
                            and row.contact_name != src["contact_name"])
                        or (src["contact_phone"] is not None
                            and row.contact_phone != src["contact_phone"])
                        or row.source_vendor_id != vendor_id
                    )
                    row.vendor_name = name
                    # 以下三欄「來源端有值才覆蓋」，理由見檔頭「欄位權責」
                    if tax_id is not None:
                        row.tax_id = tax_id
                    if src["contact_name"] is not None:
                        row.contact_name = src["contact_name"]
                    if src["contact_phone"] is not None:
                        row.contact_phone = src["contact_phone"]
                    row.source_vendor_id = vendor_id
                    row.synced_at = now
                    if changed:
                        updated += 1
                    else:
                        unchanged += 1
                else:
                    # ── 新增：vendor_code 沿用合約端 VND-NNNN ───────────────
                    code = _unique_vendor_code(vendor_id, used_codes)
                    used_codes.add(code)
                    row = CyclePurchaseVendor(
                        vendor_code=code,
                        vendor_name=name,
                        tax_id=tax_id,
                        contact_name=src["contact_name"],
                        contact_phone=src["contact_phone"],
                        is_active=True,
                        source_vendor_id=vendor_id,
                        synced_at=now,
                    )
                    db.add(row)
                    created += 1

                # 索引即時更新，避免同一批次內重複比對到同一筆
                by_source[vendor_id] = row
                if tax_id:
                    by_tax[tax_id] = row
                by_name[name] = row

            except Exception as exc:
                errors.append(f"{vendor_id}（{name}）：{exc}")
                logger.warning(f"[CP Vendor Sync] {vendor_id} 失敗：{exc}")

        db.commit()

        # 孤兒＝週採端有、合約端已無對應（僅計數示警，不刪不停用，理由見檔頭）
        source_ids = {s["vendor_id"] for s in sources}
        orphans = sum(
            1 for r in db.query(CyclePurchaseVendor).all()
            if r.source_vendor_id and r.source_vendor_id not in source_ids
        )

        logger.info(
            f"[CP Vendor Sync] 完成：新增 {created} 筆，更新 {updated} 筆，"
            f"無異動 {unchanged} 筆，略過 {skipped} 筆，孤兒 {orphans} 筆，"
            f"警告 {len(warnings)} 筆，錯誤 {len(errors)} 筆"
        )
        for w in warnings:
            logger.warning(f"[CP Vendor Sync] {w}")
    except Exception as exc:
        db.rollback()
        logger.error(f"[CP Vendor Sync] DB 寫入失敗：{exc}")
        # commit 失敗會整批 rollback，但前面逐筆收集到的 errors 仍有診斷價值，
        # 不要被這一句 SQLite 訊息蓋掉。
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
