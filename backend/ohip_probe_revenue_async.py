"""
OHIP 營收探測（第二輪）— Inventory **Asynchronous** API 的 revenueInventoryStatistics

⚠️ 這支推翻了 2026-08-06 第一輪的結論
────────────────────────────────────────────────────────────────────────────
第一輪只試了**同步版** `/inv/v1/.../inventoryStatistics` 的四個 reportCode，
結論寫成「營收拿不到」。那個結論**只對同步版成立**。

GitHub 全文搜尋 `repo:oracle/hospitality-api-docs revenue` 後發現，
**非同步版** `invasync.json` 有一支專門的營收端點：

    POST /inv/async/v1/externalSystems/{extSystemCode}/hotels/{hotelId}/revenueInventoryStatistics

回傳型別 `revenueInventoryStatisticsType` 共 16 個欄位，含
`roomRevenue`、`foodRevenue`、`totalRevenue`、`cancelledRooms`、`noShowRooms`，
而且可以 `groupBy` MarketCode / RoomType / GuaranteeType。

教訓：**翻 spec 目錄不如全文搜尋**。同步與非同步是兩份 spec 檔，
只看 `inv.json` 永遠不會發現 `invasync.json` 裡有營收。

Async 三段式流程（官方描述）
────────────────────────────────────────────────────────────────────────────
1. `POST`  啟動 → 回應的 **Location header** 帶 requestId
2. `HEAD`  輪詢該 Location 取得處理狀態
3. 完成後 `GET` 同一路徑取結果

其他限制
────────
・日期區間上限 **94 天**（比同步版的 62 天寬）
・路徑上的 `extSystemCode` 是「外部系統代碼」，spec 沒說預設值，
  **本腳本會依序試幾個候選**，找出可用的那一個。

用法
────
    cd backend
    python ohip_probe_revenue_async.py                        # 預設過去 7 天
    python ohip_probe_revenue_async.py 2026-06-01 2026-06-30
    python ohip_probe_revenue_async.py 2026-06-01 2026-06-30 MYCODE   # 指定 extSystemCode

⚠️ 本腳本會發 POST —— 但那個 POST 只是「啟動一個查詢工作」，**不寫入任何業務資料**。
   這是 OHIP async 讀取模式的必要步驟，與新增／修改訂房無關。
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
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
POLL_INTERVAL = 3
POLL_MAX = 20          # 最多等 60 秒

# extSystemCode 候選 —— spec 沒給預設值，實測找出可用的那個
EXT_CANDIDATES = [
    os.getenv("OHIP_EXT_SYSTEM_CODE", "") or None,
    "PORTAL",
    "HANNS",
    ENTERPRISE_ID,      # GLORYS
    HOTEL_ID,           # SUMMER
    "OHIP",
    "EXTERNALSYSTEM",
]


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
            "enterpriseId": ENTERPRISE_ID,
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials", "scope": SCOPE},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _headers(token: str, json_body: bool = False) -> dict:
    h = {
        "Authorization": f"Bearer {token}",
        "x-app-key": APP_KEY,
        "x-hotelid": HOTEL_ID,
        "Accept": "application/json",
    }
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def start_process(token: str, ext: str, start: date, end: date) -> tuple[int, str, str]:
    """POST 啟動查詢。回傳 (status_code, location, body 摘要)"""
    url = (f"{GATEWAY}/inv/async/v1/externalSystems/{ext}"
           f"/hotels/{HOTEL_ID}/revenueInventoryStatistics")
    body = {
        "dateRangeStart": start.isoformat(),
        "dateRangeEnd": end.isoformat(),
        # groupBy 可選 MarketCode / RoomType / GuaranteeType；
        # 先不分組，拿全館合計最好與 TXT 對照
        "groupBy": [],
    }
    try:
        r = requests.post(url, headers=_headers(token, json_body=True),
                          json=body, timeout=TIMEOUT)
    except Exception as e:
        return 0, "", f"連線失敗 {type(e).__name__}"

    loc = r.headers.get("Location") or r.headers.get("location") or ""
    snippet = (r.text or "").strip().replace("\n", " ")[:120]
    return r.status_code, loc, snippet


def poll_and_fetch(token: str, location: str) -> dict | None:
    """HEAD 輪詢直到完成，再 GET 取結果"""
    url = location if location.startswith("http") else f"{GATEWAY}{location}"

    for i in range(POLL_MAX):
        try:
            h = requests.head(url, headers=_headers(token), timeout=TIMEOUT)
        except Exception as e:
            print(f"      HEAD 失敗：{type(e).__name__}")
            return None

        print(f"      輪詢 {i + 1}/{POLL_MAX}｜HTTP {h.status_code}"
              f"｜Location={h.headers.get('Location', '—')[:60]}")

        # 依官方描述：完成後 HEAD 會在 Location 回傳取結果的 URL
        if h.status_code in (200, 201, 303):
            result_url = h.headers.get("Location") or url
            if not result_url.startswith("http"):
                result_url = f"{GATEWAY}{result_url}"
            g = requests.get(result_url, headers=_headers(token), timeout=TIMEOUT)
            if g.status_code == 200:
                return g.json()
            print(f"      取結果失敗 HTTP {g.status_code}｜{g.text[:150]}")
            return None

        if h.status_code >= 400:
            print(f"      輪詢中止 HTTP {h.status_code}")
            return None

        time.sleep(POLL_INTERVAL)

    print("      逾時：工作在 60 秒內未完成")
    return None


def summarize(payload: dict) -> None:
    out = Path(__file__).parent / "ohip_revenue_async_sample.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n      完整內容已存到：{out.name}")

    stats = []
    if isinstance(payload, dict):
        stats = (payload.get("revInvStats")
                 or (payload.get("revenueInventoryStatisticsDetails") or {}).get("revInvStats")
                 or [])
    if not stats:
        print("      ⚠️ 找不到 revInvStats 陣列，請直接打開 sample json 看結構")
        return

    print(f"      共 {len(stats)} 筆\n")
    cols = ["occupancyDate", "roomsSold", "roomRevenue", "foodRevenue",
            "totalRevenue", "cancelledRooms", "noShowRooms", "physicalRooms", "ooRooms"]
    print("      " + "".join(c.ljust(16) for c in cols))
    for row in stats[:15]:
        print("      " + "".join(str(row.get(c, "—")).ljust(16) for c in cols))

    has_rev = any(
        row.get("roomRevenue") not in (None, "", "0", 0)
        for row in stats
    )
    print()
    if has_rev:
        print("      ✅ **roomRevenue 有實際數值 —— 營收拿得到！**")
        print("         → 可以算 ADR = roomRevenue ÷ roomsSold")
        print("         → 可以算 RevPAR = roomRevenue ÷ (physicalRooms − ooRooms)")
    else:
        print("      ⚠️ roomRevenue 全為 0 或空 —— 換一個更早的歷史區間再試一次")


def main() -> None:
    args = [a for a in sys.argv[1:]]
    forced_ext = None
    if len(args) >= 2:
        start = date.fromisoformat(args[0])
        end = date.fromisoformat(args[1])
        if len(args) >= 3:
            forced_ext = args[2]
    else:
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=6)

    if (end - start).days + 1 > 94:
        print("❌ 日期區間超過 94 天（async 版上限），請縮短")
        return

    print("=" * 78)
    print("OHIP 營收探測（第二輪）— Inventory Asynchronous API")
    print(f"Hotel : {HOTEL_ID}｜區間 {start} ~ {end}（上限 94 天）")
    print("=" * 78)

    if not all([GATEWAY, APP_KEY, CLIENT_ID, CLIENT_SECRET, HOTEL_ID, ENTERPRISE_ID]):
        print("❌ backend/.env 的 OHIP_* 尚未填齊")
        return

    if not preflight():
        return

    token = get_token()
    print("Token ✅\n")

    candidates = [forced_ext] if forced_ext else [c for c in EXT_CANDIDATES if c]
    # 去重但保留順序
    seen, ordered = set(), []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            ordered.append(c)

    print(f"[1] 找出可用的 extSystemCode（依序試 {len(ordered)} 個候選）")
    location = ""
    used_ext = ""
    for ext in ordered:
        code, loc, snippet = start_process(token, ext, start, end)
        mark = "✅" if code in (200, 201, 202) else "  "
        print(f"  {mark} extSystemCode={ext!r:<18} HTTP {code}｜{snippet}")
        if code in (200, 201, 202):
            location = loc
            used_ext = ext
            print(f"      Location: {loc or '（未回傳，可能結果直接在 body）'}")
            break

    if not used_ext:
        print("""
  ❌ 所有候選都失敗。可能原因：

     403 → Application 沒有訂閱 **Inventory Asynchronous**（invasync）。
            到 Developer Portal → Applications → HANNS-Portal-Analytics
            → Subscriptions 確認 Hospitality Property 群組已訂閱（應該有）。
     404 → extSystemCode 必須是 OPERA 端**已設定的外部系統代碼**。
            請向 OPERA 管理員索取，再用：
              python ohip_probe_revenue_async.py 2026-06-01 2026-06-30 <代碼>
     400 → 日期區間或 body 格式問題，看上面的錯誤訊息。
""")
        return

    if not location:
        print("\n  ⚠️ POST 成功但沒有 Location header —— 請看 sample 或改用回傳 body")
        return

    print(f"\n[2] 輪詢工作狀態（每 {POLL_INTERVAL} 秒，最多 {POLL_MAX} 次）")
    payload = poll_and_fetch(token, location)
    if payload is None:
        return

    print("\n[3] 檢查營收欄位")
    summarize(payload)

    print("\n" + "=" * 78)
    print(f"可用的 extSystemCode = {used_ext!r}")
    print("若成功，請把結論與該代碼寫回 docs/OHIP_INTEGRATION.md §4.3.1")
    print("=" * 78)


if __name__ == "__main__":
    main()
