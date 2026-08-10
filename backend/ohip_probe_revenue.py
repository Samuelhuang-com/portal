"""
OHIP 營收資料探測 — ADR / RevPAR / Revenue 到底拿不拿得到？

背景
────
2026-08-06 用 `reportCode=RoomsAvailabilitySummary` 實測，帶上
`HouseAverageDailyRateYN` / `HouseRevPARYN` 後**回傳中完全沒有對應欄位**。
但 `inv.json` 的 enum 確實列了這兩個值，且 `reportCode` 還有另外三個沒試過。

在說「拿不到」之前，先把剩下的可能性一次試完 —— 用實測結論，不用猜。

探測範圍
────────
A. `inventoryStatistics` 的 4 個 reportCode × 營收類 parameterName
B. `getBusinessDate`（順帶確認營業日可用）

⚠️ 全程只發 GET。Production 環境，不做任何寫入。
⚠️ 每組會實際計一次 API 呼叫（OHIP 按量計費），本腳本共約 5 次。

用法
────
    cd backend
    python ohip_probe_revenue.py
    python ohip_probe_revenue.py 2026-07-01 2026-07-07   # 指定區間（歷史日期更可能有營收）
"""
from __future__ import annotations

import base64
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

GATEWAY = os.getenv("OHIP_GATEWAY_URL", "").rstrip("/")
APP_KEY = os.getenv("OHIP_APP_KEY", "")
CLIENT_ID = os.getenv("OHIP_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("OHIP_CLIENT_SECRET", "")
HOTEL_ID = os.getenv("OHIP_HOTEL_ID", "")
ENTERPRISE_ID = os.getenv("OHIP_ENTERPRISE_ID", "")
SCOPE = os.getenv("OHIP_SCOPE", "urn:opc:hgbu:ws:__myscopes__")

TIMEOUT = 60

REPORT_CODES = [
    "RoomsAvailabilitySummary",     # 已知：只給房況
    "DetailedAvailabiltySummary",   # ⚠️ Oracle 自己拼錯，enum 值就是這樣
    "RoomCalendarStatistics",
    "SellLimitSummary",
]

# 營收類參數 —— 這次探測的重點
REVENUE_PARAMS = [
    "HouseAverageDailyRateYN",
    "HouseRevPARYN",
]

# 一併帶上基本房況，確認該 reportCode 至少是通的
BASE_PARAMS = [
    "HouseInventoryRoomsYN",
    "HouseRoomsSoldYN",
]

# 回傳中只要出現這些字樣就算命中
REVENUE_NEEDLES = ["revenue", "averagedailyrate", "adr", "revpar", "rate", "amount"]


# ── 連線前置檢查 ─────────────────────────────────────────────────────────────
# 2026-08-06 實測踩到：同一台機器前幾分鐘還能通，之後 DNS 解析失敗噴滿頁 traceback。
# 那是網路層問題（斷線／VPN／DNS），不是程式或憑證問題，但原始 traceback 完全看不出來。

def preflight() -> bool:
    """先確認 gateway 的網域解析得到，解析不到就直接給人話。"""
    import socket
    from urllib.parse import urlparse

    host = urlparse(GATEWAY).hostname
    if not host:
        print(f"❌ OHIP_GATEWAY_URL 格式不正確：{GATEWAY!r}")
        return False
    try:
        socket.getaddrinfo(host, 443)
        return True
    except socket.gaierror:
        print(f"""
❌ 連不到 OHIP：DNS 解析失敗（無法解析 {host}）

   這是**網路層**問題，與憑證、程式無關。依序檢查：

   1. 網路是否斷線 —— 開瀏覽器隨便連一個網站試試
   2. VPN 是否斷開 —— 若公司網路需要 VPN 才能連外，重新連線
   3. DNS 是否正常 —— 在 cmd 執行：
          nslookup {host}
      解析不到就是 DNS 或防火牆的問題，找 IT 確認
   4. 公司防火牆是否擋掉 *.oraclecloud.com

   確認網路恢復後重跑本腳本即可，不需要改任何設定。
""")
        return False
    except Exception as e:
        print(f"❌ 網域檢查失敗：{type(e).__name__}: {e}")
        return False


def get_token() -> str:
    basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    r = requests.post(
        f"{GATEWAY}/oauth/v1/tokens",
        headers={
            "x-app-key": APP_KEY,
            "enterpriseId": ENTERPRISE_ID,      # ⚠️ 漏掉會 401 且訊息誤導
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials", "scope": SCOPE},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "x-app-key": APP_KEY,
        "x-hotelid": HOTEL_ID,
        "Accept": "application/json",
    }


def collect_codes(payload) -> set[str]:
    """把回傳中所有 inventory code 撈出來"""
    found: set[str] = set()

    def walk(o):
        if isinstance(o, dict):
            if "code" in o and "value" in o:
                found.add(str(o["code"]))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(payload)
    return found


def probe_report_code(token: str, rc: str, start: date, end: date) -> None:
    params: list[tuple[str, str]] = [
        ("dateRangeStart", start.isoformat()),
        ("dateRangeEnd", end.isoformat()),
        ("reportCode", rc),
    ]
    for p in BASE_PARAMS + REVENUE_PARAMS:
        params.append(("parameterName", p))
        params.append(("parameterValue", "Y"))

    url = f"{GATEWAY}/inv/v1/hotels/{HOTEL_ID}/inventoryStatistics"
    try:
        r = requests.get(url, headers=_headers(token), params=params, timeout=TIMEOUT)
    except Exception as e:
        print(f"  ❌ {rc:<28} 連線失敗 {type(e).__name__}")
        return

    if r.status_code != 200:
        body = (r.text or "").strip().replace("\n", " ")[:100]
        print(f"  ⚠️  {rc:<28} HTTP {r.status_code}｜{body}")
        return

    payload = r.json()
    codes = collect_codes(payload) - {"SequenceId"}
    hits = sorted(c for c in codes
                  if any(n in c.lower() for n in REVENUE_NEEDLES))

    out = Path(__file__).parent / f"ohip_probe_{rc}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  ✅ {rc:<28} 回傳 {len(codes):>2} 個指標")
    print(f"      指標：{', '.join(sorted(codes)) if codes else '（無）'}")
    if hits:
        print(f"      🎯 **疑似營收欄位：{hits}** ← 打開 {out.name} 確認是否有實際數值")
    else:
        print("      —— 沒有任何營收類欄位")


def probe_business_date(token: str) -> None:
    url = f"{GATEWAY}/bof/v1/hotels/{HOTEL_ID}/businessDate"
    try:
        r = requests.get(url, headers=_headers(token), timeout=TIMEOUT)
    except Exception as e:
        print(f"  ❌ businessDate 連線失敗 {type(e).__name__}")
        return
    if r.status_code != 200:
        print(f"  ⚠️  businessDate HTTP {r.status_code}")
        return
    hotels = (r.json() or {}).get("hotels") or []
    bd = hotels[0].get("businessDate") if hotels else None
    print(f"  ✅ businessDate = {bd}")


def main() -> None:
    if len(sys.argv) == 3:
        start = date.fromisoformat(sys.argv[1])
        end = date.fromisoformat(sys.argv[2])
    else:
        # 預設抓過去 7 天 —— 歷史日期比未來日期更可能帶有實際營收
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=6)

    print("=" * 78)
    print("OHIP 營收資料探測（唯讀，只發 GET）")
    print(f"Hotel : {HOTEL_ID}｜區間 {start} ~ {end}")
    print("=" * 78)

    if not all([GATEWAY, APP_KEY, CLIENT_ID, CLIENT_SECRET, HOTEL_ID, ENTERPRISE_ID]):
        print("❌ backend/.env 的 OHIP_* 尚未填齊")
        return

    if not preflight():
        return

    token = get_token()
    print("Token ✅\n")

    print("[A] inventoryStatistics × 4 個 reportCode")
    for rc in REPORT_CODES:
        probe_report_code(token, rc, start, end)

    print("\n[B] Back Office 營業日")
    probe_business_date(token)

    print("\n" + "=" * 78)
    print("""怎麼讀這份結果

  ・任何一組出現 🎯 → 打開對應的 ohip_probe_*.json，確認那個欄位**有實際數值**
       而不是 null／0。有值就代表營收拿得到，Portal 可以改吃 API。

  ・四組都沒有營收欄位 → 這支 API 確定拿不到營收，剩下的路徑只有：
       ① Business Events / Streaming（本環境已 Streaming Enabled）—— 交易事件推播，
          需要另建接收端，架構複雜度高
       ② csh 的 getCashierTransactions —— 逐筆帳務自行加總，口徑要另外對過
       ③ 維持現行 TXT 上傳（成本最低）

  ・注意日期：**未來日期本來就不會有已實現營收**。若預設區間查不到，
       試試更早的歷史區間：python ohip_probe_revenue.py 2026-06-01 2026-06-07
""")


if __name__ == "__main__":
    main()
