"""
核准請購單 — 行銷部 / 財務部 detail_path 候選欄位比較腳本
執行方式：
  cd portal/backend
  python verify_dept_paths.py
"""
import json
import urllib.request
import urllib.error
from pathlib import Path

env_path = Path(__file__).parent / ".env"
env = {}
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")

API_KEY = env.get("RAGIC_API_KEY", "")
SERVER  = "ap12.ragic.com"
ACCOUNT = "soutlet001"

def fetch_detail(path: str, record_id: str) -> dict | None:
    url = f"https://{SERVER}/{ACCOUNT}/{path}/{record_id}?api=&version=2025-01-01"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception:
        return None

def inspect(dept: str, candidates: list[tuple[str, str, str]]):
    """
    candidates: list of (sheet_path, record_id, label)
    印出每個候選的欄位名稱，供人工判斷哪個是請購單 form view
    """
    print(f"\n{'='*60}")
    print(f"【{dept}】候選 detail_path 欄位比較")
    for path, rid, label in candidates:
        print(f"\n  --- {label} ({path}/{rid}) ---")
        data = fetch_detail(path, rid)
        if not data:
            print("    (無回應)")
            continue
        keys = list(data.keys())
        # 主表欄位（非數字、非底線開頭）
        main_fields = [k for k in keys if not k.lstrip("-").isdigit() and not k.startswith("_")]
        # 子表格行數
        subtable_rows = [k for k in keys if k.lstrip("-").isdigit() and isinstance(data[k], dict)]
        print(f"    主表欄位({len(main_fields)}): {main_fields}")
        print(f"    子表格行數: {len(subtable_rows)}")
        if subtable_rows:
            # 印出第一行子表格的 key
            first_row = data[subtable_rows[0]]
            sub_keys = [k for k in first_row if not k.startswith("_")]
            print(f"    子表格欄位: {sub_keys}")

def main():
    # ── 行銷部：候選 /2 vs /6，record_ids 來自 list 9,8,7 ─────────────────
    inspect("行銷部", [
        ("lequn-marketing-department/2", "9", "候選/2"),
        ("lequn-marketing-department/6", "9", "候選/6"),
        ("lequn-marketing-department/2", "8", "候選/2 rec8"),
        ("lequn-marketing-department/6", "8", "候選/6 rec8"),
    ])

    # ── 財務部：候選 /5,/6,/7,/10,/11，record_ids 來自 list 2,1 ───────────
    inspect("財務部", [
        ("lequn-finance-department/5",  "2", "候選/5"),
        ("lequn-finance-department/6",  "2", "候選/6"),
        ("lequn-finance-department/7",  "2", "候選/7"),
        ("lequn-finance-department/10", "2", "候選/10"),
        ("lequn-finance-department/11", "2", "候選/11"),
    ])

    # ── 資訊部確認：joy-group-it-department/12，record_ids 25,24 ──────────
    inspect("資訊部確認", [
        ("joy-group-it-department/12", "25", "候選/12"),
        ("joy-group-it-department/12", "24", "候選/12 rec24"),
    ])

    # ── 工務部確認：/2，record_ids 60,59 ──────────────────────────────────
    inspect("工務部確認", [
        ("lequn-public-works-department/2", "60", "候選/2"),
        ("lequn-public-works-department/2", "59", "候選/2 rec59"),
    ])

    # ── 專案確認：/1，record_ids 39,38 ────────────────────────────────────
    inspect("專案確認", [
        ("happy-group-project/1", "39", "候選/1"),
        ("happy-group-project/1", "38", "候選/1 rec38"),
    ])

if __name__ == "__main__":
    main()
