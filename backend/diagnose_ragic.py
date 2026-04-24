"""
Ragic 連線診斷工具 v2
在 backend 資料夾執行：python diagnose_ragic.py
"""
import asyncio, base64, json, os, sys

try:
    import httpx
except ImportError:
    print("請先安裝：pip install httpx"); sys.exit(1)

# ── 讀取 .env ────────────────────────────────────────────────────────────────
def load_env(path=".env"):
    env = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"')
    except FileNotFoundError:
        print(f"找不到 {path}，請在 backend 目錄執行"); sys.exit(1)
    return env

env = load_env()
API_KEY      = env.get("RAGIC_API_KEY", "")
ENC_KEY      = env.get("ENCRYPTION_KEY", "")
SERVER       = env.get("RAGIC_SERVER", "ap16")
ACCOUNT      = env.get("RAGIC_ACCOUNT_NAME") or env.get("RAGIC_ACCOUNT", "")

print("=" * 65)
print("Ragic 連線診斷 v2")
print("=" * 65)
print(f"  SERVER  : {SERVER}.ragic.com")
print(f"  ACCOUNT : {ACCOUNT}")
print(f"  API_KEY : {API_KEY[:30]}...")
print()

# ── 嘗試解密 API Key（若它是 Fernet 加密的）────────────────────────────────
KEYS_TO_TRY: list[tuple[str, str]] = []

# 1) 直接使用原始值
KEYS_TO_TRY.append(("raw", API_KEY))

# 2) 嘗試 Fernet 解密
if ENC_KEY:
    try:
        from cryptography.fernet import Fernet
        f = Fernet(ENC_KEY.encode())
        decrypted = f.decrypt(API_KEY.encode()).decode()
        KEYS_TO_TRY.append(("fernet_decrypted", decrypted))
        print(f"✅ Fernet 解密成功，解密後 key: {decrypted[:30]}...")
    except Exception as e:
        print(f"ℹ️  Fernet 解密失敗（API Key 可能本來就是明文）: {e}")

# 3) 嘗試 base64 decode 後再用
try:
    decoded = base64.b64decode(API_KEY).decode("utf-8", errors="ignore")
    if decoded and decoded.isprintable() and len(decoded) > 10:
        KEYS_TO_TRY.append(("base64_decoded", decoded))
        print(f"ℹ️  Base64 解碼後: {decoded[:30]}...")
except Exception:
    pass

print()

# ── 建立 Basic auth header ────────────────────────────────────────────────────
def make_headers(key: str) -> dict:
    token = base64.b64encode(f"{key}:".encode()).decode()
    return {"Authorization": f"Basic {token}"}

# ── 測試函式 ──────────────────────────────────────────────────────────────────
async def probe(client, tab, idx, key, pageid=None):
    params = "v=3&api&limit=3"
    if pageid:
        params += f"&PAGEID={pageid}"
    url = f"https://{SERVER}.ragic.com/{ACCOUNT}/{tab}/{idx}?{params}"
    try:
        r = await client.get(url, headers=make_headers(key), timeout=10)
        if r.status_code == 200:
            try:
                data = r.json()
                records = {k: v for k, v in data.items() if k.lstrip("-").isdigit()}
                return r.status_code, records, data
            except Exception:
                return r.status_code, {}, {}
        return r.status_code, {}, {}
    except Exception as e:
        return 0, {}, str(e)

async def main():
    async with httpx.AsyncClient(verify=True, trust_env=False) as client:

        # ── Step 1：找出有效的 API Key ────────────────────────────────────────
        print("Step 1: 測試 API Key 格式")
        print("-" * 65)
        working_key = None
        for label, key in KEYS_TO_TRY:
            status, records, raw = await probe(client, "ragicsales-order-management", 1, key)
            print(f"  [{label:20s}]  status={status}  records={len(records)}")
            if status == 200 and working_key is None:
                working_key = (label, key)

        if not working_key:
            print("❌ 所有 API Key 格式都失敗")
            return
        key_label, key = working_key
        print(f"\n✅ 使用 key 格式: {key_label}")

        # ── Step 2：確認 Sales Order URL 帶 PAGEID 是否有資料 ────────────────
        print()
        print("Step 2: 確認 Sales Order（ragicsales-order-management/1, PAGEID=mBN）")
        print("-" * 65)
        for pageid in [None, "mBN"]:
            status, records, raw = await probe(client, "ragicsales-order-management", 1, key, pageid)
            pageid_str = f"PAGEID={pageid}" if pageid else "無 PAGEID"
            print(f"  {pageid_str:15s}  status={status}  records={len(records)}")
            if records:
                first = next(iter(records.values()))
                print(f"    ➜ 第一筆 keys: {list(first.keys())[:8]}")
                for fid, val in list(first.items())[:5]:
                    if not fid.startswith("_"):
                        print(f"       {fid} = {str(val)[:60]}")

        # ── Step 3：掃描含資料的 sheet ────────────────────────────────────────
        print()
        print("Step 3: 掃描所有可能路徑（含 PAGEID 變體）")
        print("-" * 65)

        tab_candidates = [
            "ragicsales-order-management",
            "hotel-ops", "hotel", "housekeeping", "room-maintenance",
            "ragichotel", "hotel-management", "facility", "maintenance",
            "ragic-hotel", "room", "cleaning", "inspect",
        ]
        found = []
        forbidden_tabs = []   # 403 的 tab（存在但 Key 無權限）

        for tab in tab_candidates:
            for idx in [1, 2, 3, 4, 5]:
                status, records, raw = await probe(client, tab, idx, key)
                path = f"{tab}/{idx}"
                if status == 200 and records:
                    first = next(iter(records.values()))
                    vals = str(list(first.values())[:4])
                    hotel_kw = ["房", "客", "保養", "檢查", "浴", "修", "housekeep"]
                    mark = "🏨" if any(k in vals for k in hotel_kw) else "  "
                    print(f"  {mark} {path:35s} ✅ {len(records)} 筆  {vals[:70]}")
                    found.append((path, records, raw))
                elif status == 403:
                    print(f"  🔒 {path:35s} 403 （Tab 存在但 API Key 無讀取權限）")
                    forbidden_tabs.append(path)
                elif status not in (200, 404, 0):
                    print(f"     {path:35s} {status}")

        # ── 結果 ─────────────────────────────────────────────────────────────
        print()
        print("=" * 65)
        if forbidden_tabs:
            print()
            print("🔒 發現以下 Tab 存在但 API Key 無讀取權限：")
            for p in forbidden_tabs:
                print(f"     {p}")
            print()
            print("👉 修正步驟：")
            print("  1. 登入 Ragic → 右上角帳號名稱 → 帳號設定")
            print("  2. 找到「API Key 設定」（或 Integrations → API）")
            print("  3. 確認目前使用的 API Key 有勾選上述 Tab 的讀取權限")
            print("  4. 或產生一支有全域讀取權的新 API Key，更新 .env 中的 RAGIC_API_KEY")
            print()
            print("  ── 同時請確認客房保養的完整網址（瀏覽器網址列）──")
            print(f"  預期格式：https://{SERVER}.ragic.com/{ACCOUNT}/inspect/數字?PAGEID=xxx")
            print(f"         或：https://{SERVER}.ragic.com/{ACCOUNT}/cleaning/數字?PAGEID=xxx")

        if not found:
            if not forbidden_tabs:
                print("❌ 所有 sheet 均為空表單（0 筆資料）")
                print()
                print("  → 請在瀏覽器開啟客房保養表單，將完整網址（含 PAGEID）貼給我")
        else:
            print("✅ 找到含資料的 sheet：")
            for path, records, _ in found:
                print(f"\n  RAGIC_ROOM_MAINTENANCE_PATH={path}")
                first = next(iter(records.values()))
                print("  Field ID 對照（前 10 個欄位）：")
                for fid, val in list(first.items())[:10]:
                    if not fid.startswith("_"):
                        print(f"    {fid:12s} = {str(val)[:60]}")

asyncio.run(main())
