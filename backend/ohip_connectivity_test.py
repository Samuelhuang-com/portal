"""
OHIP（OPERA Cloud API）連線驗證腳本 — Phase 0

規劃文件：docs/OHIP_INTEGRATION.md

用途
────
在寫任何正式模組之前，先確認四件事：
  1. Client Credentials 能不能換到 token
  2. x-app-key 是否有效
  3. hotelId 是否正確、Application 是否訂閱了 Inventory API
  4. ⚠️ ADR / RevPAR 到底有沒有回值（規劃文件 §4.3 的已知缺口）

安全限制
────────
本腳本**只發 GET**。環境為 Production，任何寫入操作一律不做。

使用方式
────────
    cd backend
    python ohip_connectivity_test.py                 # 預設查未來 7 天
    python ohip_connectivity_test.py 2026-08-01 2026-08-31

先在 backend/.env 補上：
    OHIP_GATEWAY_URL=https://mtca2pr.hospitality-api.ap-singapore-1.ocs.oraclecloud.com
    OHIP_APP_KEY=...
    OHIP_CLIENT_ID=cc96a30edb8e48c3ab65f2951a03c62b
    OHIP_CLIENT_SECRET=...
    OHIP_HOTEL_ID=...
    OHIP_SCOPE=urn:opc:hgbu:ws:__myscopes__
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
    print("[warn] 未安裝 python-dotenv，改讀系統環境變數")


# ── 設定 ──────────────────────────────────────────────────────────────────────
GATEWAY = os.getenv("OHIP_GATEWAY_URL", "").rstrip("/")
APP_KEY = os.getenv("OHIP_APP_KEY", "")
CLIENT_ID = os.getenv("OHIP_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("OHIP_CLIENT_SECRET", "")
HOTEL_ID = os.getenv("OHIP_HOTEL_ID", "")
ENTERPRISE_ID = os.getenv("OHIP_ENTERPRISE_ID", "")
SCOPE = os.getenv("OHIP_SCOPE", "urn:opc:hgbu:ws:__myscopes__")

TIMEOUT = 60

# 想驗證的指標（對應 docs/OHIP_INTEGRATION.md §4.2）
#
# ⚠️ 2026-08-06 實測：`parameterName` 必須與 `parameterValue` **成對**送出，
#    只送 name 的話 API 回 200 但 inventory 裡只有 SequenceId，沒有任何指標值。
#    依據：inv.json spec 中 parameterName / parameterValue 是兩個平行的 multi array。
#    名稱以 YN 結尾者，值送 "Y"。
PARAMETERS = [
    "HouseInventoryRoomsYN",        # 總房數
    "HouseAvailRoomsYN",            # 可售房
    "HouseOOOYN",                   # OOO 房
    "HouseRoomsSoldYN",             # 售出房
    "HouseOccPercYN",               # 住房率
    "HouseArrRoomsYN",              # 到達房數
    "HouseDepRoomsYN",              # 離店房數
    "HousePeopleInHouseYN",         # 在店人數
    "HouseCompRoomsYN",             # 招待房
    "HouseHouseUseRoomsYN",         # 自用房
    "HouseDayUseRoomYN",            # Day use
    "HouseAverageDailyRateYN",      # ⚠️ ADR — 重點驗證項
    "HouseRevPARYN",                # ⚠️ RevPAR — 重點驗證項
]

# 可用的 reportCode（inv.json enum）。預設用房況彙總；查不到指標時可換另一個試。
REPORT_CODE = os.getenv("OHIP_REPORT_CODE", "RoomsAvailabilitySummary")


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


def _fail(msg: str) -> None:
    print(f"\n❌ {msg}")
    sys.exit(1)


def check_config() -> None:
    missing = [
        name for name, val in [
            ("OHIP_GATEWAY_URL", GATEWAY),
            ("OHIP_APP_KEY", APP_KEY),
            ("OHIP_CLIENT_ID", CLIENT_ID),
            ("OHIP_CLIENT_SECRET", CLIENT_SECRET),
            ("OHIP_HOTEL_ID", HOTEL_ID),
            ("OHIP_ENTERPRISE_ID", ENTERPRISE_ID),
        ] if not val
    ]
    if missing:
        _fail(
            "backend/.env 缺少以下設定：\n    "
            + "\n    ".join(missing)
            + "\n\n取得方式見 docs/OHIP_INTEGRATION.md §2"
        )


def get_token() -> str:
    """Client Credentials 換 token。

    兩個容易踩的點（都已在 2026-08-06 實測踩過）：
      1. OHIP 的 Basic auth **需要真的做 base64**（與 Ragic 的規則相反）
      2. OCIM 環境走 client_credentials 時，**必須帶 `enterpriseId` header**，
         漏掉會回 401 "Failed to authenticate application"（訊息完全誤導人）
         依據：oauth.json spec 的 `parameters.enterpriseId`（in: header）
    """
    url = f"{GATEWAY}/oauth/v1/tokens"
    basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    print(f"[1/3] 取 token → POST {url}")
    resp = requests.post(
        url,
        headers={
            "x-app-key": APP_KEY,
            "enterpriseId": ENTERPRISE_ID,
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials", "scope": SCOPE},
        timeout=TIMEOUT,
    )

    if resp.status_code != 200:
        print(f"      HTTP {resp.status_code}")
        print(f"      {resp.text[:1000]}")
        _fail(
            "換 token 失敗。常見原因：\n"
            "  401 'Failed to authenticate application'\n"
            "       → 最常見是**漏帶 enterpriseId header**（本腳本已帶）\n"
            "       → 其次才是 client_id / client_secret 錯\n"
            "  403 invalid_grant_type_or_scope → scope 沒帶或值不對\n"
            "  400 'Enterprise ID is required'  → enterpriseId header 空的\n"
            "  404 → Gateway URL 錯"
        )

    data = resp.json()
    print(f"      ✅ OK，expires_in = {data.get('expires_in')} 秒")
    return data["access_token"]


def get_inventory_statistics(token: str, start: date, end: date) -> dict:
    """GET /inv/v1/hotels/{hotelId}/inventoryStatistics — 唯讀"""
    url = f"{GATEWAY}/inv/v1/hotels/{HOTEL_ID}/inventoryStatistics"
    params = [
        ("dateRangeStart", start.isoformat()),
        ("dateRangeEnd", end.isoformat()),
        ("reportCode", REPORT_CODE),
    ]
    # name / value 必須成對，且順序對應
    for p in PARAMETERS:
        params.append(("parameterName", p))
        params.append(("parameterValue", "Y" if p.endswith("YN") else ""))

    print(f"[2/3] 查房況統計 → GET {url}")
    print(f"      reportCode = {REPORT_CODE}")
    print(f"      區間 {start} ~ {end}（{(end - start).days + 1} 天，上限 62 天）")
    resp = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "x-app-key": APP_KEY,
            "x-hotelid": HOTEL_ID,
            "Accept": "application/json",
        },
        params=params,
        timeout=TIMEOUT,
    )

    if resp.status_code != 200:
        print(f"      HTTP {resp.status_code}")
        print(f"      {resp.text[:2000]}")
        _fail(
            "查詢失敗。常見原因：\n"
            "  400 → 日期區間超過 62 天，或 reportCode / parameterName 拼錯\n"
            "  401 → token 過期\n"
            "  403 → Application 沒訂閱 Inventory API，或 hotelId 無權限\n"
            "  404 → hotelId 不存在"
        )

    print("      ✅ OK")
    return resp.json()


def inspect(payload) -> None:
    """把巢狀回傳攤平成逐日表格，並判斷 ADR / RevPAR 是否真的有值（規劃文件 §4.3）

    實測回傳結構（2026-08-06）：
        [ { "statistics": [
              { "statCategoryCode": "HotelCode",     "statCode": "SUMMER",
                "statisticDate": [ { "statisticDate": "...", "inventory": [ {code,value} ] } ] },
              { "statCategoryCode": "HotelRoomCode", "statCode": "CK", "description": "Camping King",
                "statisticDate": [ ... ] },
              ...
        ] } ]
    """
    print("[3/3] 檢查回傳內容")

    raw = json.dumps(payload, ensure_ascii=False)
    print(f"      回傳大小：{len(raw):,} bytes")

    out = Path(__file__).parent / "ohip_inventory_stats_sample.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      完整內容已存到：{out.name}")

    # ── 攤平 ────────────────────────────────────────────────────────────────
    blocks = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                blocks.extend(item.get("statistics") or [])
    elif isinstance(payload, dict):
        blocks.extend(payload.get("statistics") or [])

    if not blocks:
        print("      ⚠️ 找不到 statistics 區塊，結構可能與預期不同，請直接看 sample json")
        return

    print(f"\n      共 {len(blocks)} 個統計區塊：")
    for b in blocks:
        cat = b.get("statCategoryCode")
        code = b.get("statCode")
        desc = b.get("description") or ""
        print(f"        - {cat:<16} {code:<8} {desc}")

    # 全館層級（HotelCode）才是我們要的每日營運統計
    house = next((b for b in blocks if b.get("statCategoryCode") == "HotelCode"), None)
    if house is None:
        print("\n      ⚠️ 沒有 HotelCode 層級的區塊 —— 回傳只有房型層級")
        house = blocks[0]

    rows = house.get("statisticDate") or []
    all_codes: list[str] = []
    table: dict[str, dict[str, object]] = {}
    for r in rows:
        d = r.get("statisticDate")
        vals = {i.get("code"): i.get("value") for i in (r.get("inventory") or [])}
        table[d] = vals
        for c in vals:
            if c not in all_codes:
                all_codes.append(c)

    real = [c for c in all_codes if c != "SequenceId"]

    print(f"\n      {house.get('statCategoryCode')} = {house.get('statCode')} 逐日指標：")
    if not real:
        print("""
      ❌ inventory 裡只有 SequenceId，沒有任何實際指標值。

         這代表 parameterName / parameterValue 沒有被正確接受。檢查方向：
           1. name 與 value 是否成對送出（本腳本已成對）
           2. 換一個 reportCode 再試：
                set OHIP_REPORT_CODE=DetailedAvailabiltySummary
                python ohip_connectivity_test.py
              可選值：RoomsAvailabilitySummary / DetailedAvailabiltySummary
                      RoomCalendarStatistics / SellLimitSummary
""")
        return

    w = max(len(c) for c in real) + 2
    print("        " + "日期".ljust(12) + "".join(c.ljust(w) for c in real))
    for d in sorted(table):
        line = "        " + str(d).ljust(12)
        for c in real:
            v = table[d].get(c)
            line += ("—" if v is None else str(v)).ljust(w)
        print(line)

    # ── ADR / RevPAR 結論 ──────────────────────────────────────────────────
    print("\n      §4.3 缺口驗證：")
    for label, needle in [("ADR（平均房價）", "AverageDailyRate"), ("RevPAR", "RevPAR")]:
        hits = [c for c in real if needle.lower() in c.lower()]
        if not hits:
            print(f"        ❌ {label}：回傳中沒有這個欄位")
            continue
        vals = [table[d].get(h) for d in table for h in hits]
        nonzero = [v for v in vals if v not in (None, 0, "0", "", "0.00")]
        if nonzero:
            print(f"        ✅ {label}：{hits} 有實際數值（例：{nonzero[0]}）")
        else:
            print(f"        ⚠️  {label}：{hits} 存在但全為 0／null")

    print("\n      → 請把結論寫回 docs/OHIP_INTEGRATION.md §4.3")


def main() -> None:
    if len(sys.argv) == 3:
        start = date.fromisoformat(sys.argv[1])
        end = date.fromisoformat(sys.argv[2])
    else:
        start = date.today()
        end = start + timedelta(days=6)

    if (end - start).days + 1 > 62:
        _fail("日期區間超過 62 天，OHIP 會拒絕。請分段查詢。")

    print("=" * 70)
    print("OHIP 連線驗證（唯讀，只發 GET）")
    print(f"Gateway : {GATEWAY}")
    print(f"Hotel   : {HOTEL_ID}")
    print("=" * 70)

    check_config()
    if not preflight():
        sys.exit(1)
    token = get_token()
    payload = get_inventory_statistics(token, start, end)
    inspect(payload)

    print("\n" + "=" * 70)
    print("✅ 連線驗證完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
