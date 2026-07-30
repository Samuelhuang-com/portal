"""
vendor_sync.py — 廠商資料表同步服務：Ragic → SQLite

Ragic Sheet：community-management-department/15（廠商資料表）
DB Table  ：vendors（backend/app/models/contract.py 的 Vendor）
Portal 路由：/contract/vendors

比對優先序（2026-07-30 使用者確認，AskUserQuestion）：
  1. ragic_id 已連結 → 直接比對到該筆（重複同步、Ragic 端改名都不會建立新廠商）
  2. 統一編號（tax_id）非空且與現有廠商完全相同 → 視為同一筆，回填 ragic_id
  3. 廠商名稱（vendor_name）完全相同 → 視為同一筆，回填 ragic_id（相容既有手動建立/
     Excel 匯入的廠商，沿用 import_vendors_from_ragic.py 原本的比對邏輯）
  4. 都比對不到 → 新增廠商，vendor_id 沿用 Portal 既有 VND-NNNN 自動編號規則
     （與「新增廠商」表單、Excel 匯入格式一致，不直接套用 Ragic 的「廠商編號」欄位）

只回填/更新 Ragic 有提供的欄位（廠商名稱／統一編號／聯絡人／電話／Email／地址／銀行資訊）。
vendor_type、risk_level、is_critical、payment_terms、managing_company 是 Portal 自維護欄位，
Ragic 廠商資料表無對應資料，同步時不覆蓋既有值。
"""
import logging
import re

import requests

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.time import twnow
from app.models.contract import Vendor
from app.services.sync_dispatcher import register

logger = logging.getLogger(__name__)

RAGIC_VENDOR_URL = "https://ap12.ragic.com/soutlet001/community-management-department/15"

_VND_PATTERN = re.compile(r"^VND-(\d{4,})$")


def _safe(row: dict, *keys: str) -> str:
    """依序嘗試多個 key，回傳第一個有值的字串（子表物件直接跳過）"""
    for k in keys:
        v = row.get(k, "")
        if isinstance(v, dict):
            continue
        if v and str(v).strip() not in ("", "N/A", "-"):
            return str(v).strip()
    return ""


def _next_vendor_id(existing_ids: set) -> str:
    """依 Portal 既有 VND-NNNN 規則，找出下一個未使用的廠商編號"""
    max_n = 0
    for vid in existing_ids:
        m = _VND_PATTERN.match(vid or "")
        if m:
            max_n = max(max_n, int(m.group(1)))
    n = max_n + 1
    candidate = f"VND-{n:04d}"
    while candidate in existing_ids:
        n += 1
        candidate = f"VND-{n:04d}"
    return candidate


@register("vendor")
async def sync_from_ragic() -> dict:
    """
    從 Ragic 廠商資料表抓取所有記錄，Upsert 到 Portal vendors 表。
    回傳 { fetched, upserted, created, updated, errors }
    （fetched/upserted/errors 為 main.py _run_loop / sync_tool.py 共用的標準格式）
    """
    logger.info("[Vendor Sync] 開始從 Ragic 拉取廠商資料...")
    try:
        resp = requests.get(
            RAGIC_VENDOR_URL,
            headers={"Authorization": f"Basic {settings.RAGIC_API_KEY}"},
            params={"api": "", "limit": 1000, "naming": "true"},
            timeout=30,
        )
        resp.raise_for_status()
        raw: dict = resp.json()
    except Exception as exc:
        logger.error(f"[Vendor Sync] Ragic 請求失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "created": 0, "updated": 0, "errors": [str(exc)]}

    fetched = len(raw)
    created = updated = 0
    errors: list = []
    now = twnow()

    db = SessionLocal()
    try:
        all_vendors = db.query(Vendor).all()
        by_ragic_id = {v.ragic_id: v for v in all_vendors if v.ragic_id}
        by_tax_id = {v.tax_id: v for v in all_vendors if v.tax_id}
        by_name = {v.vendor_name: v for v in all_vendors if v.vendor_name}
        existing_ids = {v.vendor_id for v in all_vendors}

        for ragic_id, row in raw.items():
            if not isinstance(row, dict):
                continue
            try:
                name = _safe(row, "名稱", "廠商名稱", "公司名稱")
                if not name:
                    continue  # 沒有名稱跳過（沿用 import_vendors_from_ragic.py 原本行為）

                tax_id = _safe(row, "統一編號")
                contact_person = _safe(row, "聯絡窗口", "聯絡人") or None
                phone = _safe(row, "電話", "電話號碼") or None
                email = _safe(row, "E-mail", "Email") or None
                address = _safe(row, "地址") or None
                bank_name = _safe(row, "受款銀行") or None
                bank_account = _safe(row, "銀行帳號") or None

                # ── 比對優先序：ragic_id → 統一編號 → 廠商名稱 ──────────────
                existing = by_ragic_id.get(ragic_id)
                if existing is None and tax_id:
                    existing = by_tax_id.get(tax_id)
                if existing is None:
                    existing = by_name.get(name)

                if existing:
                    existing.vendor_name = name
                    if tax_id:
                        existing.tax_id = tax_id
                    existing.contact_person = contact_person
                    existing.phone = phone
                    existing.email = email
                    existing.address = address
                    existing.bank_name = bank_name
                    existing.bank_account = bank_account
                    existing.ragic_id = ragic_id
                    existing.updated_at = now
                    updated += 1
                    by_ragic_id[ragic_id] = existing
                    if tax_id:
                        by_tax_id[tax_id] = existing
                    by_name[name] = existing
                else:
                    new_id = _next_vendor_id(existing_ids)
                    existing_ids.add(new_id)
                    vendor = Vendor(
                        vendor_id=new_id,
                        vendor_name=name,
                        tax_id=tax_id,
                        contact_person=contact_person,
                        phone=phone,
                        email=email,
                        address=address,
                        bank_name=bank_name,
                        bank_account=bank_account,
                        ragic_id=ragic_id,
                        is_critical=False,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(vendor)
                    created += 1
                    by_ragic_id[ragic_id] = vendor
                    if tax_id:
                        by_tax_id[tax_id] = vendor
                    by_name[name] = vendor

            except Exception as exc:
                errors.append(f"ragic_id={ragic_id}: {exc}")
                logger.warning(f"[Vendor Sync] 記錄 {ragic_id} 失敗：{exc}")

        db.commit()
        logger.info(
            f"[Vendor Sync] 完成：新增 {created} 筆，更新 {updated} 筆，錯誤 {len(errors)} 筆"
        )
    except Exception as exc:
        db.rollback()
        logger.error(f"[Vendor Sync] DB 寫入失敗：{exc}")
        return {"fetched": fetched, "upserted": 0, "created": 0, "updated": 0, "errors": [str(exc)]}
    finally:
        db.close()

    return {
        "fetched": fetched,
        "upserted": created + updated,
        "created": created,
        "updated": updated,
        "errors": errors,
    }
