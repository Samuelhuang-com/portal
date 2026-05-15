"""
scan_claim_fields.py — 掃描各部門請款單 Ragic 欄位定義

用途：列出各部門「編號/單號」相關欄位的實際 Ragic key 與範例值，
      確認 claim_request_sync.py LIST_FIELD_CANDIDATES 是否完整。

執行：
    cd portal/backend
    python scripts/scan_claim_fields.py

    # 加 --reparse 旗標同時修正 DB 現有 null 記錄
    python scripts/scan_claim_fields.py --reparse
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

# ── 讀取 .env ─────────────────────────────────────────────────────────────────
env: dict[str, str] = {}
env_path = Path(__file__).parent.parent / ".env"
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()

API_KEY = env["RAGIC_API_KEY"]
SERVER  = env.get("RAGIC_SERVER", "ap16")
ACCOUNT = env.get("RAGIC_ACCOUNT", "intraragicapp")

# claim_request_sync.py 目前仍硬碼 ap12 / soutlet001
# 若 .env 與硬碼不同，以下都會嘗試
SERVERS = [
    (SERVER, ACCOUNT),
    ("ap12.ragic.com", "soutlet001"),
    (f"{SERVER}.ragic.com", ACCOUNT),
]

HEADERS = {"Authorization": f"Basic {API_KEY}"}

DEPT_SHEETS = [
    ("執董室",  "lequn-executive-office/9"),
    ("營業部",  "new-tab/8"),
    ("行銷部",  "lequn-marketing-department/12"),
    ("財務部",  "lequn-finance-department/6"),
    ("停管部",  "lequn-traffic-management/5"),
    ("管理部",  "community-management-department/24"),
    ("資訊部",  "joy-group-it-department/14"),
    ("工務部",  "lequn-public-works-department/2"),
    ("專案",    "happy-group-project/1"),
]

CURRENT_CANDIDATES = [
    "編號", "請款單號", "單號",
    "管請編號", "財請編號", "工請編號", "專請編號",
    "客請編號", "營請編號", "資請編號", "停請編號",
    "職請編號", "執董請編號",
    "樂行購編號",
    "樂執請編號", "樂管請編號", "樂財請編號", "樂工請編號",
    "樂專請編號", "樂客請編號", "樂營請編號", "樂資請編號", "樂停請編號",
]


def fetch_first_record(path: str) -> dict | None:
    for srv, acc in SERVERS:
        if not srv.startswith("http"):
            srv = f"https://{srv}"
        url = f"{srv}/{acc}/{path}?api&limit=3&status=1"
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode())
            records = {k: v for k, v in data.items() if k.lstrip("-").isdigit()}
            if records:
                return next(iter(records.values()))
        except Exception:
            continue
    return None


def main() -> None:
    do_reparse = "--reparse" in sys.argv

    print("=" * 70)
    print("各部門 Ragic 請款單欄位掃描")
    print("=" * 70)

    missing: dict[str, list[str]] = {}  # dept → list of unknown field names

    for dept, path in DEPT_SHEETS:
        print(f"\n【{dept}】", end=" ", flush=True)
        record = fetch_first_record(path)
        if record is None:
            print("⚠️  無法取得資料（網路/帳號問題）")
            continue

        # 找所有含「號」的欄位
        no_keys = {
            k: v for k, v in record.items()
            if isinstance(v, str) and v
            and ("編號" in str(k) or "單號" in str(k)
                 or (str(k).endswith("號") and len(str(k)) <= 10))
        }

        hits    = [(c, record[c]) for c in CURRENT_CANDIDATES if c in record and record[c]]
        unknown = [(k, v) for k, v in no_keys.items() if k not in CURRENT_CANDIDATES]

        print()
        if hits:
            for k, v in hits:
                print(f"  ✅ {k} = {v}")
        if unknown:
            for k, v in unknown:
                print(f"  ❓ {k} = {v}  ← 未在候選清單！")
            missing[dept] = [k for k, _ in unknown]
        if not hits and not unknown:
            print(f"  ⚠️  找不到任何「編號/單號」欄位")
            print(f"     全部欄位: {list(record.keys())[:25]}")

        time.sleep(0.3)

    # ── 彙總建議 ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    if missing:
        print("⚠️  以下欄位未在 LIST_FIELD_CANDIDATES 候選清單，需補入：")
        for dept, keys in missing.items():
            print(f"  【{dept}】: {keys}")
        print("\n在 claim_request_sync.py LIST_FIELD_CANDIDATES 的")
        print("request_no / department_request_no 清單中加入上述 key 後，")
        print("執行 reparse 端點修正現有記錄：")
        print("  POST http://localhost:8000/api/v1/claim-report/admin/reparse-request-no")
    else:
        print("✅ 所有部門「編號」欄位均已涵蓋在候選清單中")

    # ── Reparse ───────────────────────────────────────────────────────────────
    if do_reparse:
        print("\n── 執行 reparse ─────────────────────────────────────────────────")
        import sqlite3

        db_url = env.get("DATABASE_URL", "")
        db_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
        if not db_path or not Path(db_path).exists():
            print(f"找不到 DB 路徑：{db_path}")
            return

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.services.claim_request_sync import _pick, LIST_FIELD_CANDIDATES

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, raw_data_json FROM approved_claim_requests "
            "WHERE (request_no IS NULL OR request_no = '') AND raw_data_json IS NOT NULL"
        )
        rows = cur.fetchall()
        print(f"待修正記錄：{len(rows)} 筆")

        updated = 0
        for row_id, raw in rows:
            try:
                data = json.loads(raw)
                new_no = _pick(data, LIST_FIELD_CANDIDATES["request_no"])
                if new_no:
                    cur.execute(
                        "UPDATE approved_claim_requests SET request_no=? WHERE id=?",
                        (new_no, row_id)
                    )
                    updated += 1
            except Exception as e:
                print(f"  id={row_id} 錯誤: {e}")

        conn.commit()
        conn.close()
        print(f"已更新：{updated} / {len(rows)} 筆")


if __name__ == "__main__":
    main()
