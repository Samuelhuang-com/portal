"""
import_vendors_from_ragic.py
────────────────────────────────────────────────────────────────────────────────
從 Ragic 廠商資料表抓取資料，insert 到 Portal vendors 表。

使用方式（在 backend/ 目錄下執行）：
    python scripts/import_vendors_from_ragic.py [--dry-run] [--clear]

    --dry-run   只印出將要 insert 的資料，不寫入 DB
    --clear     清空 vendors 前（注意：contracts 有 FK 到 vendors，需先清 contracts）

範例：
    cd backend
    python scripts/import_vendors_from_ragic.py --dry-run
    python scripts/import_vendors_from_ragic.py
"""

import sys, os, argparse, json, requests
from datetime import datetime

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.contract import Vendor

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true", help="只印出資料，不寫入 DB")
parser.add_argument("--clear",   action="store_true", help="insert 前清空 vendors（危險）")
args = parser.parse_args()

# ── Ragic 設定 ────────────────────────────────────────────────────────────────
RAGIC_API_KEY = settings.RAGIC_API_KEY
RAGIC_URL     = "https://ap12.ragic.com/soutlet001/community-management-department/15"
HEADERS       = {"Authorization": f"Basic {RAGIC_API_KEY}"}

# ── DB ────────────────────────────────────────────────────────────────────────
_url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
engine  = create_engine(_url, connect_args={"check_same_thread": False} if "sqlite" in _url else {})
Session = sessionmaker(bind=engine)

# ── 抓 Ragic 資料 ──────────────────────────────────────────────────────────────
print(f"\n📡  從 Ragic 抓取廠商資料…")
try:
    resp = requests.get(RAGIC_URL, headers=HEADERS,
                        params={"api": "", "limit": 500, "naming": "true"},
                        timeout=30)
    resp.raise_for_status()
    raw: dict = resp.json()
except Exception as e:
    print(f"❌  Ragic 請求失敗：{e}")
    sys.exit(1)

print(f"✓  共 {len(raw)} 筆原始資料")

# ── 印出第一筆欄位（debug 用）────────────────────────────────────────────────
if raw:
    first_key = next(iter(raw))
    first_row = raw[first_key]
    print("\n📋  第一筆欄位預覽：")
    for k, v in first_row.items():
        if not isinstance(v, dict):   # 跳過子表物件
            print(f"    {repr(k):40s} → {repr(str(v)[:60])}")

# ── 欄位對應（根據實際欄位名稱調整）─────────────────────────────────────────
def safe(row, *keys) -> str:
    """依序嘗試多個 key，回傳第一個有值的字串"""
    for k in keys:
        v = row.get(k, "")
        if v and str(v).strip() not in ("", "N/A", "-"):
            return str(v).strip()
    return ""

def map_row(ragic_id: str, row: dict) -> dict | None:
    """將 Ragic 一筆記錄對應為 vendors 欄位 dict，回傳 None 表示跳過"""
    # 實際欄位：名稱（非「廠商名稱」）
    name = safe(row, "名稱", "廠商名稱", "公司名稱")
    if not name:
        return None   # 沒有名稱跳過

    # 廠商編號使用 Ragic 格式（V-00136），無則用 _ragicId fallback
    vid = safe(row, "廠商編號") or f"V-{ragic_id.zfill(5)}"

    return {
        "vendor_id":        vid,
        "vendor_name":      name,
        "tax_id":           safe(row, "統一編號"),
        "contact_person":   safe(row, "聯絡窗口", "聯絡人"),
        "phone":            safe(row, "電話", "電話號碼"),
        "email":            safe(row, "E-mail", "Email"),
        "address":          safe(row, "地址"),
        "payment_terms":    None,   # Ragic 無此欄
        "bank_name":        safe(row, "受款銀行"),
        "bank_account":     safe(row, "銀行帳號"),
        "vendor_type":      None,   # Ragic 無此欄
        "risk_level":       "低",
        "is_critical":      False,
        "managing_company": None,
    }

# ── 轉換所有筆數 ──────────────────────────────────────────────────────────────
mapped = []
skipped_no_name = 0
for rid, row in raw.items():
    m = map_row(rid, row)
    if m is None:
        skipped_no_name += 1
    else:
        mapped.append(m)

print(f"\n✓  有效廠商：{len(mapped)} 筆 | 跳過（無名稱）：{skipped_no_name} 筆")

if args.dry_run:
    print("\n── Dry-run 預覽（前 10 筆）──────────────────────────────────────")
    for m in mapped[:10]:
        print(f"  {m['vendor_id']:15s}  {m['vendor_name']:30s}  稅號:{m['tax_id']:10s}  聯絡:{m['contact_person']}")
    print("\n⚠️   Dry-run 模式，未寫入 DB")
    sys.exit(0)

# ── 寫入 DB ───────────────────────────────────────────────────────────────────
with Session() as db:
    if args.clear:
        # FK 順序：先把 contracts.vendor_id 清空（設為 ""），再刪 vendors
        db.execute(text("UPDATE contracts SET vendor_id = ''"))
        db.execute(text("DELETE FROM vendors"))
        db.commit()
        print("🗑️   已清空 vendors（contracts.vendor_id 已重設為空）")

    existing_names = {r[0] for r in db.execute(text("SELECT vendor_name FROM vendors"))}
    existing_ids   = {r[0] for r in db.execute(text("SELECT vendor_id   FROM vendors"))}

    now = datetime.now()
    inserted = skipped_dup = error_count = 0

    for m in mapped:
        if m["vendor_name"] in existing_names:
            skipped_dup += 1
            continue

        # 確保 vendor_id 不衝突
        vid = m["vendor_id"]
        if vid in existing_ids:
            # 加後綴避免衝突
            vid = vid + "-" + m["vendor_name"][:4]
        m["vendor_id"] = vid

        try:
            db.add(Vendor(
                vendor_id       = m["vendor_id"],
                vendor_name     = m["vendor_name"],
                tax_id          = m["tax_id"],
                contact_person  = m["contact_person"] or None,
                phone           = m["phone"] or None,
                email           = m["email"] or None,
                address         = m["address"] or None,
                payment_terms   = m["payment_terms"] or None,
                bank_name       = m["bank_name"] or None,
                bank_account    = m["bank_account"] or None,
                vendor_type     = m["vendor_type"] or None,
                risk_level      = m["risk_level"] or None,
                is_critical     = m["is_critical"],
                managing_company= m["managing_company"] or None,
                created_at      = now,
                updated_at      = now,
            ))
            existing_names.add(m["vendor_name"])
            existing_ids.add(m["vendor_id"])
            inserted += 1
        except Exception as e:
            print(f"  ⚠️  {m['vendor_name']} 失敗：{e}")
            db.rollback()
            error_count += 1

    db.commit()

print(f"\n✅  插入：{inserted} | 跳過（已存在）：{skipped_dup} | 錯誤：{error_count}")
print("🎉  完成\n")
