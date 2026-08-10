#!/usr/bin/env python3
"""
Portal API 快速測試工具
用法：python api_test.py "GET /mall/full-building-maintenance/period-stats?period_type=month&year=2026&month=6&frequency_type=monthly"
或直接修改下方 URL 再執行
"""
import sys
import json
import urllib.request
import urllib.parse
import urllib.error

# ── 設定 ──────────────────────────────────────────────────────────────────────
BASE     = "http://127.0.0.1:8000/api/v1"
USERNAME = "admin"
PASSWORD = "Admin@2026"

# ── 預設查詢（改這裡或從命令列傳入）────────────────────────────────────────
DEFAULT_URL = "GET /mall/full-building-maintenance/period-stats?period_type=month&year=2026&month=6&frequency_type=monthly"

# ── 登入取 token ──────────────────────────────────────────────────────────────
def get_token():
    data = json.dumps({"identifier": USERNAME, "password": PASSWORD}).encode()
    req  = urllib.request.Request(
        f"{BASE}/auth/login",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]

# ── 打 API ────────────────────────────────────────────────────────────────────
def call(method_and_path: str, token: str):
    parts  = method_and_path.strip().split(" ", 1)
    method = parts[0].upper() if len(parts) == 2 else "GET"
    path   = parts[1] if len(parts) == 2 else parts[0]
    url    = BASE + path

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "Cache-Control": "no-cache",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": json.loads(e.read())}

# ── 主程式 ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    url = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_URL

    print(f"\n>>> {url}")
    print("-" * 60)

    try:
        token = get_token()
        print("Login OK\n")
        result = call(url, token)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}")
