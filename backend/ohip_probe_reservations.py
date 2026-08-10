"""
OHIP 探測 — Reservation **Asynchronous** API 的 getReservationsDailySummary

建立日期：2026-08-07
評估文件：`docs/EVAL_ohip_strategic_data.md` §4.1（順位 3）

═══════════════════════════════════════════════════════════════════════════
這支腳本要回答什麼
═══════════════════════════════════════════════════════════════════════════
`ANALYSIS_opera_realtime_matrix.md` §2.4 曾判定「住客與通路分析 17 個端點全滅」，
理由是「`inv` 與 `invasync` 都只給日彙總，拿不到任何一筆訂房」。

**那個判定漏查了 `rsvasync`。** 官方文件載明它有 `getReservationsDailySummary`，
是**逐筆訂房**層級，回應包含 profile 區塊、net room rate、會員卡號、external reference。

如果為真，這些原本判死的功能全部可以翻案：
    通路統計、Rate Code 統計、公司統計、回訪住客、LOS 分桶、客群結構…

⚠️ **本腳本的唯一目的是「印出實際回傳了哪些欄位」，不是寫 parser。**
   2026-08-06 已經學過一次：spec 寫有 ≠ 實作有
   （`HouseAverageDailyRateYN` 列在 enum 卻沒實作）。
   先看到真實欄位，再決定要不要做模組。

═══════════════════════════════════════════════════════════════════════════
✅ 2026-08-07 第一輪實測結果：路徑已確認，body 欄位名仍未知
═══════════════════════════════════════════════════════════════════════════
四組路徑候選中，三組回 404，**第四組回 HTTP 400**：

    路徑：/rsv/async/v1/externalSystems/{ext}/hotels/{hotel}/reservations/dailySummary
    回應：400 {"detail":"Unknown property: startDate.","o:errorCode":"OPERAWS-GEN01242"}

**400 而不是 404 或 403，代表三件事同時成立：**
  ① 路徑存在（404 才是路徑錯）
  ② **Application 已訂閱 Reservation Async**（403 才是沒訂閱）
  ③ 只有 request body 的欄位名不對

⚠️ 注意命名形狀：是 `reservations/dailySummary`（斜線分段），
   **不是** `invasync` 那種 `revenueInventoryStatistics`（駝峰單段）。
   `blkasync` 先前猜的 `blockAllocationSummary` 回 404，
   很可能同理要改成 `blocks/allocationSummary`。

═══════════════════════════════════════════════════════════════════════════
✅ 2026-08-07 第二輪實測結果
═══════════════════════════════════════════════════════════════════════════
**① blkasync 完全可用（順位 4 前置解決）**

    /blk/async/v1/externalSystems/{ext}/hotels/{hotel}/blocks/allocationSummary
    + body {"startDate": ..., "endDate": ...}   → **HTTP 202**

    202 不只是「路徑對」，是**工作已經啟動**。命名形狀的推論得到印證：
    斜線分段（`blocks/allocationSummary`），不是駝峰單段。

**② rsvasync 的 body 是巢狀的 `criteria`**

    22 個頂層候選中只有 `criteria` 被認得，且 `{"criteria": {}}` 回：

        "Request should contain either Time Span or Last Modified Date"

    → body 形狀是 `{"criteria": {...}}`，裡面要放 Time Span 或 Last Modified Date。
    **前兩輪把所有候選平放在頂層，所以全滅** —— 這是本次最大的教訓：
    欄位反推必須**逐層下探**，不能只掃頂層。

═══════════════════════════════════════════════════════════════════════════
反推 schema 的方法（逐層下探）
═══════════════════════════════════════════════════════════════════════════
`Unknown property: X.` 這個訊息**會指名第一個不認得的欄位**。
所以一次只送一個候選欄位，就能分辨：

    回 "Unknown property: X"  → 這個欄位**不存在**
    回別的訊息（或成功）      → 這個欄位**存在**（只是還缺其他必填欄位）

⚠️ **關鍵：要逐層下探。** 找到 `criteria` 之後，接著探 `{"criteria": {X: ...}}`，
   再接著探 `{"criteria": {"timeSpan": {X: ...}}}`。
   只掃頂層會得到「22 個候選只中 1 個」這種看似失敗的結果。

先送空 body，錯誤訊息通常會指出**必填**欄位是什麼。

⚠️ 這比「一直猜整組 body」有效率得多，而且每次探測都會得到明確的是／否，
   不會出現「試了十組都失敗但不知道為什麼」的狀況。

═══════════════════════════════════════════════════════════════════════════
⚠️ 個資
═══════════════════════════════════════════════════════════════════════════
這支端點會回傳**住客姓名與會員卡號**。本腳本預設**遮罩**所有疑似個資的值，
只顯示欄位名稱、型別與出現次數 —— 那才是我們要的資訊。
真的需要看原值時加 `--raw`，但請不要把輸出貼到任何外部工具。

═══════════════════════════════════════════════════════════════════════════
用法
═══════════════════════════════════════════════════════════════════════════
    cd backend
    python ohip_probe_reservations.py                    # 預設過去 7 天
    python ohip_probe_reservations.py 2026-07-01 2026-07-07
    python ohip_probe_reservations.py --raw              # 不遮罩（謹慎使用）
    python ohip_probe_reservations.py --save             # 另存原始 JSON 供後續分析

⚠️ 本腳本會發 POST —— 但那個 POST 只是「啟動一個查詢工作」，**不寫入任何業務資料**。
   這是 OHIP async 讀取模式的必要步驟，與新增／修改訂房無關。
⚠️ 本腳本**不經過** `app/services/ohip_client.py`。
   那支客戶端有 async 路徑白名單，在這個端點被證實可用之前，不應該先放寬白名單。
"""
from __future__ import annotations

import base64
import json
import os
import re
import socket
import sys
import time
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

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
EXT_CODE = os.getenv("OHIP_EXT_SYSTEM_CODE", "") or "PORTAL"
SCOPE = os.getenv("OHIP_SCOPE", "urn:opc:hgbu:ws:__myscopes__")

TIMEOUT = 90
POLL_INTERVAL = 3
POLL_MAX = 30            # 最多等 90 秒（逐筆訂房比營收慢）

TRUNCATE_LIMIT = 2_000_000     # Oracle：超過 2 MB 會被**靜默**截斷

# ✅ 2026-08-07 實測確認的路徑（回 400 而非 404/403 → 路徑對、已訂閱、只是 body 錯）
CONFIRMED_PATH = "/rsv/async/v1/externalSystems/{ext}/hotels/{hotel}/reservations/dailySummary"

# 其餘候選保留，供日後 OPERA 改版時重新確認用（第一輪全部回 404）
PATH_CANDIDATES = [
    CONFIRMED_PATH,
    "/rsv/async/v1/externalSystems/{ext}/hotels/{hotel}/reservationsDailySummary",
    "/rsv/async/v1/externalSystems/{ext}/hotels/{hotel}/reservationDailySummary",
    "/rsv/async/v1/hotels/{hotel}/reservationsDailySummary",
]

# ⚠️ body 欄位名未經查證（見檔頭 ②）
def body_candidates(start: date, end: date) -> list[tuple[str, dict]]:
    return [
        ("startDate/endDate",
         {"startDate": start.isoformat(), "endDate": end.isoformat()}),
        ("dateRangeStart/dateRangeEnd",
         {"dateRangeStart": start.isoformat(), "dateRangeEnd": end.isoformat()}),
        ("startDate/endDate + hotelIds",
         {"startDate": start.isoformat(), "endDate": end.isoformat(),
          "hotelIds": [HOTEL_ID]}),
    ]

# 順位 4（blkasync）順便一起確認訂閱狀態 —— 只做路徑探測，不做欄位普查。
# ⚠️ 第一輪 `blockAllocationSummary`（駝峰單段）回 404。既然 rsv 實際是
#    `reservations/dailySummary`（斜線分段），這裡把同樣形狀的候選補進來。
BLOCK_PATHS = [
    "/blk/async/v1/externalSystems/{ext}/hotels/{hotel}/blocks/allocationSummary",
    "/blk/async/v1/externalSystems/{ext}/hotels/{hotel}/blockAllocationSummary",
    "/blk/async/v1/externalSystems/{ext}/hotels/{hotel}/blocks/summary",
    "/blk/async/v1/hotels/{hotel}/blocks/allocationSummary",
]

# ── schema 反推用的候選欄位（一次只送一個）────────────────────────────────────
# ⚠️ 值本身不重要 —— 我們只看 OPERA 認不認得這個「欄位名」。
def schema_candidates(start: date, end: date) -> list[tuple[str, object]]:
    s_, e_ = start.isoformat(), end.isoformat()
    return [
        # 官方文件明確提到的兩組
        ("startDate", s_), ("endDate", e_),
        ("startLastModifiedDate", s_), ("endLastModifiedDate", e_),
        # invasync 的形狀
        ("dateRangeStart", s_), ("dateRangeEnd", e_),
        # 其他常見命名
        ("arrivalStartDate", s_), ("arrivalEndDate", e_),
        ("stayDateRangeStart", s_), ("departureStartDate", s_),
        ("reservationStartDate", s_), ("businessDateStart", s_),
        ("fromDate", s_), ("toDate", e_),
        # 非日期類：看看 body 還吃哪些東西
        ("hotelIds", [HOTEL_ID]), ("hotelId", HOTEL_ID),
        ("criteria", {}), ("fetchInstructions", ["Reservation"]),
        ("limit", 10), ("offset", 0),
        ("includeInactive", False), ("reservationStatus", ["RESERVED"]),
    ]


# 第 2 層：`criteria` 裡面吃什麼
# ⚠️ 實測訊息「Request should contain either Time Span or Last Modified Date」
#    直接點名了兩個容器，所以這兩個排最前面。
def criteria_candidates(start: date, end: date) -> list[tuple[str, object]]:
    s_, e_ = start.isoformat(), end.isoformat()
    span = {"startDate": s_, "endDate": e_}
    return [
        ("timeSpan", span), ("timespan", span), ("stayTimeSpan", span),
        ("lastModifiedDate", span), ("lastModifiedDateSpan", span),
        ("dateRange", span), ("stayDateRange", span),
        ("hotelIds", [HOTEL_ID]), ("hotelId", HOTEL_ID),
        ("propertyIds", [HOTEL_ID]),
        ("startDate", s_), ("endDate", e_),
        ("reservationStatus", ["RESERVED"]), ("includeInactive", False),
        ("fetchInstructions", ["Reservation"]),
        ("limit", 10), ("offset", 0),
    ]


# 第 3 層：日期容器裡面的欄位名
def span_candidates(start: date, end: date) -> list[tuple[str, object]]:
    s_, e_ = start.isoformat(), end.isoformat()
    return [
        ("startDate", s_), ("endDate", e_),
        ("start", s_), ("end", e_),
        ("from", s_), ("to", e_),
        ("startDateTime", s_ + "T00:00:00"), ("endDateTime", e_ + "T23:59:59"),
        ("dateRangeStart", s_), ("dateRangeEnd", e_),
    ]


# ── 前置檢查 ─────────────────────────────────────────────────────────────────

def preflight() -> bool:
    missing = [n for n, v in [
        ("OHIP_GATEWAY_URL", GATEWAY), ("OHIP_APP_KEY", APP_KEY),
        ("OHIP_CLIENT_ID", CLIENT_ID), ("OHIP_CLIENT_SECRET", CLIENT_SECRET),
        ("OHIP_HOTEL_ID", HOTEL_ID), ("OHIP_ENTERPRISE_ID", ENTERPRISE_ID),
    ] if not v]
    if missing:
        print(f"❌ backend/.env 缺少：{'、'.join(missing)}")
        return False

    host = urlparse(GATEWAY).hostname
    try:
        socket.getaddrinfo(host, 443)
        return True
    except socket.gaierror:
        print(f"""
❌ 連不到 OHIP：DNS 解析失敗（無法解析 {host}）

   這是**網路層**問題，與憑證、程式無關。依序檢查：
   1. 網路是否斷線
   2. VPN 是否斷開（公司網路可能需要 VPN 才能連外）
   3. 在 cmd 執行 `nslookup {host}`，解析不到就找 IT
   4. 防火牆是否擋掉 *.oraclecloud.com
""")
        return False


def get_token() -> str:
    basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    r = requests.post(
        f"{GATEWAY}/oauth/v1/tokens",
        headers={
            "x-app-key": APP_KEY,
            "enterpriseId": ENTERPRISE_ID,        # ⚠️ 必須是 header，不是 body
            "Authorization": f"Basic {basic}",    # ⚠️ OHIP 要真的做 base64
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials", "scope": SCOPE},
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        print(f"❌ 換 token 失敗 HTTP {r.status_code}：{r.text[:300]}")
        print("   401 時優先檢查 enterpriseId header（訊息會誤導成 application 問題）")
        sys.exit(1)
    data = r.json()
    print(f"✅ token OK（expires_in={data.get('expires_in')} 秒）")
    return data["access_token"]


def _headers(token: str, with_json: bool = False) -> dict:
    h = {
        "Authorization": f"Bearer {token}",
        "x-app-key": APP_KEY,
        "x-hotelid": HOTEL_ID,
        "Accept": "application/json",
    }
    if with_json:
        h["Content-Type"] = "application/json"
    return h


# ── 訂閱檢查 ─────────────────────────────────────────────────────────────────

def check_subscription(token: str, label: str, path: str, body: dict) -> str:
    """發一次 POST，只看狀態碼判斷「有沒有訂閱／路徑對不對」。

    回傳 'ok' / 'not_subscribed' / 'not_found' / 'other'
    """
    url = GATEWAY + path.format(ext=EXT_CODE, hotel=HOTEL_ID)
    try:
        r = requests.post(url, headers=_headers(token, True), json=body, timeout=TIMEOUT)
    except requests.RequestException as e:
        print(f"   {label}: 連線失敗 {type(e).__name__}")
        return "other"

    snippet = (r.text or "")[:200].replace("\n", " ")
    if r.status_code in (200, 201, 202):
        print(f"   ✅ {label}: HTTP {r.status_code} —— 可用")
        return "ok"
    if r.status_code == 403:
        print(f"   ⛔ {label}: HTTP 403 —— **Application 未訂閱此 API**（或此 hotelId 無權限）")
        print(f"      → 到 dev portal 的 HANNS-Portal-Analytics 頁面把該 API 加入訂閱")
        return "not_subscribed"
    if r.status_code == 404:
        print(f"   ❓ {label}: HTTP 404 —— 路徑不存在（本腳本的路徑是類推的，見檔頭）")
        return "not_found"
    print(f"   ⚠️ {label}: HTTP {r.status_code} —— {snippet}")
    return "other"


# ── schema 反推（第二輪的核心）───────────────────────────────────────────────

UNKNOWN_PROP = re.compile(r"Unknown property:\s*([A-Za-z0-9_]+)")


def _post_raw(token: str, path: str, body: dict):
    url = GATEWAY + path.format(ext=EXT_CODE, hotel=HOTEL_ID)
    return requests.post(url, headers=_headers(token, True), json=body, timeout=TIMEOUT)


def _detail(r) -> str:
    try:
        j = r.json()
        return j.get("detail") or j.get("title") or (r.text or "")[:200]
    except Exception:
        return (r.text or "")[:200]


def _wrap(parents: list[str], leaf: dict) -> dict:
    """把 leaf 包進 parents 指定的層級。`_wrap(['criteria'], {'x':1})` → `{'criteria':{'x':1}}`"""
    body: dict = leaf
    for k in reversed(parents):
        body = {k: body}
    return body


def _probe_level(token: str, path: str, parents: list[str],
                 candidates: list[tuple[str, object]], label: str
                 ) -> tuple[list[str], dict | None]:
    """探測某一層有哪些合法欄位。

    Returns:
        (認得的欄位名清單, 成功送出的完整 body 或 None)

    ⚠️ 一次只送**一個**欄位，OPERA 回報的「第一個不認得的欄位」就一定是它，
       判定沒有歧義。
    """
    where = ".".join(parents) or "（頂層）"
    print(f"\n   探測層級：{where}   —— {label}")

    # 先送這一層的空物件，看它抱怨什麼（通常會點名必填欄位）
    r = _post_raw(token, path, _wrap(parents, {}))
    print(f"      空物件 → HTTP {r.status_code}：{_detail(r)[:110]}")

    accepted: list[str] = []
    winner: dict | None = None
    for name, val in candidates:
        body = _wrap(parents, {name: val})
        r = _post_raw(token, path, body)
        det = _detail(r)
        m = UNKNOWN_PROP.search(det)

        if r.status_code in (200, 201, 202):
            print(f"      🎯 {name:22s} **被接受且整個請求成功**（HTTP {r.status_code}）")
            accepted.append(name)
            winner = body
            break                      # 找到可用 body 就不必再試
        if m and m.group(1).split(".")[-1] == name:
            print(f"      ✗  {name:22s} 不存在")
        else:
            print(f"      ✅ {name:22s} 存在 → {det[:80]}")
            accepted.append(name)
        time.sleep(0.4)                # 對 Production 客氣一點

    return accepted, winner


def _pick_container(names: list[str]) -> str | None:
    """從認得的欄位裡挑出最像「日期容器」的那個。"""
    for pat in (r"timespan", r"lastmodified", r"daterange"):
        for n in names:
            if re.search(pat, n, re.I):
                return n
    return names[0] if names else None


def discover_schema(token: str, path: str, start: date, end: date) -> dict | None:
    """逐層下探反推 request body。回傳可用的完整 body（找不到回 None）。

    ⚠️ **必須逐層下探。** 2026-08-07 第二輪只掃頂層，22 個候選只中 `criteria` 一個，
       看起來像失敗；實際上是 body 本來就是巢狀的。
    """
    print(f"\n{'─' * 74}")
    print("步驟 3：逐層反推 request body 的欄位（一次送一個）")
    print(f"{'─' * 74}")

    # 第 1 層
    top, win = _probe_level(token, path, [], schema_candidates(start, end),
                            "頂層有哪些欄位")
    if win:
        return win
    container = _pick_container([n for n in top if n == "criteria"] or top)
    if not container:
        print("\n   ⚠️ 頂層沒有任何認得的欄位，無法往下探。")
        return None

    # 第 2 層
    lvl2, win = _probe_level(token, path, [container],
                             criteria_candidates(start, end),
                             f"`{container}` 裡面有哪些欄位")
    if win:
        return win
    span = _pick_container(lvl2)
    if not span:
        print(f"\n   ⚠️ `{container}` 裡沒有任何認得的欄位。")
        return None

    # 第 3 層
    lvl3, win = _probe_level(token, path, [container, span],
                             span_candidates(start, end),
                             f"`{container}.{span}` 裡面有哪些欄位")
    if win:
        return win

    # 第 3 層沒有單欄位就成功 → 用該層認得的欄位組合起來試一次
    if lvl3:
        combo = {}
        for name, val in span_candidates(start, end):
            if name in lvl3:
                combo[name] = val
        body = _wrap([container, span], combo)
        r = _post_raw(token, path, body)
        print(f"\n   組合 {container}.{span} 的 {list(combo)} → HTTP {r.status_code}")
        print(f"      {_detail(r)[:140]}")
        if r.status_code in (200, 201, 202):
            print("      🎯 成功！")
            return body
    return None


def probe_block_paths(token: str, body: dict) -> str | None:
    """順位 4 前置：找出 blkasync 的正確路徑。回傳可用的路徑。

    狀態碼判讀：404=路徑錯、403=未訂閱、400=路徑對且已訂閱（body 錯）、
    **202=完全可用（工作已啟動）**。

    ⚠️ 第二輪的顯示有 bug：202 落進 else 分支被印成「⚠️」，
       但 202 其實是**最好**的結果，差點被當成異常忽略。
    """
    print(f"\n{'─' * 74}\n步驟 2：Block Async 路徑探測（順位 4 前置）\n")
    usable = None
    for bp in BLOCK_PATHS:
        tail = bp.rsplit("/hotels/", 1)[-1].split("/", 1)[-1]
        r = _post_raw(token, bp, body)
        if r.status_code in (200, 201, 202):
            print(f"   🎯 …/{tail:26s} {r.status_code} **完全可用**（工作已啟動）")
            usable = usable or bp
        elif r.status_code == 404:
            print(f"   ✗  …/{tail:26s} 404 路徑不存在")
        elif r.status_code == 403:
            print(f"   ⛔ …/{tail:26s} 403 **未訂閱 Block Async**")
        elif r.status_code == 400:
            print(f"   ✅ …/{tail:26s} 400 路徑正確且已訂閱（只是 body 錯）")
            print(f"      {_detail(r)[:140]}")
        else:
            print(f"   ⚠️ …/{tail:26s} {r.status_code} {_detail(r)[:100]}")
        time.sleep(0.4)
    return usable


# ── async 三段式讀取 ─────────────────────────────────────────────────────────

def async_read(token: str, path: str, body: dict) -> tuple[object, int] | None:
    """POST 啟動 → HEAD 輪詢 → GET 取結果。回傳 (payload, bytes)。"""
    url = GATEWAY + path.format(ext=EXT_CODE, hotel=HOTEL_ID)
    r = requests.post(url, headers=_headers(token, True), json=body, timeout=TIMEOUT)
    if r.status_code not in (200, 201, 202):
        print(f"❌ 啟動失敗 HTTP {r.status_code}：{r.text[:300]}")
        return None

    loc = r.headers.get("Location") or r.headers.get("location") or ""
    if not loc:
        print("❌ 沒有 Location header，無法輪詢")
        return None
    if not loc.startswith("http"):
        loc = GATEWAY + loc
    print(f"   已啟動，輪詢 {loc.rsplit('/', 1)[-1]} …")

    # ⚠️ 2026-08-07 第三輪發現：HEAD 回 200 之後 GET 卻回 404（rsv），
    #    但同一段程式在 blk 是成功的。
    #    → 推測 OPERA 用 **200 表示「處理中」、303 才是「完成」**，
    #      我們把 200 當完成就會太早去 GET。
    #    **這只是推測**，官方文件沒寫，所以這裡改成「把每次 HEAD 的狀態碼與
    #    headers 都印出來」，讓實際協定自己顯現，而不是繼續猜。
    #    同時 GET 404 不再直接放棄，而是回頭繼續輪詢。
    result_url = ""
    interesting = ("location", "retry-after", "x-request-id", "content-length")

    for i in range(POLL_MAX):
        h = requests.head(loc, headers=_headers(token), timeout=TIMEOUT)
        hdrs = {k: v for k, v in h.headers.items() if k.lower() in interesting}
        print(f"      HEAD #{i + 1} → {h.status_code}  {hdrs or ''}")

        if h.status_code >= 400:
            print(f"❌ 輪詢回 HTTP {h.status_code}")
            return None

        if h.status_code in (200, 201, 303):
            nxt = h.headers.get("Location") or loc
            candidate = nxt if nxt.startswith("http") else GATEWAY + nxt
            g = requests.get(candidate, headers=_headers(token), timeout=TIMEOUT)
            if g.status_code == 200:
                print(f"   完成（輪詢 {i + 1} 次，約 {(i + 1) * POLL_INTERVAL} 秒）")
                return g.json(), len(g.content or b"")
            if g.status_code == 404:
                # 還沒好 —— 繼續輪詢，不要當成失敗
                print(f"      GET → 404（工作尚未完成，繼續輪詢）")
            else:
                print(f"❌ 取結果失敗 HTTP {g.status_code}：{g.text[:300]}")
                return None

        time.sleep(POLL_INTERVAL)

    print(f"❌ 輪詢逾時（{POLL_MAX * POLL_INTERVAL} 秒仍未取得結果）。")
    print("   若 HEAD 一直回 200 但 GET 一直 404，代表 200 不是「完成」的訊號，")
    print("   請把上面的 HEAD 狀態碼序列貼回來，據此修正判斷條件。")
    return None


# ── 欄位普查（本腳本的重點）──────────────────────────────────────────────────

# ⚠️ 只遮**自然人**的識別資訊。
#    刻意**不遮** companyName / travelAgentName / groupName 這類**法人／團體**名稱 ——
#    「哪些公司貢獻最多」正是這次探測要回答的問題之一，遮掉就白跑一趟。
#    （第一版把它們一起遮了，因為 regex 的 `name` 會命中 `companyName`。）
BUSINESS_NAME = re.compile(
    r"company|corporate|travelagent|agent|group|block|market|source|rate|"
    r"roomtype|channel|segment", re.I)
PERSONAL = re.compile(
    r"guest|given|surname|lastname|firstname|fullname|middlename|"
    r"profile|member|card|email|phone|mobile|address|passport|birth|"
    r"nationality|gender|vip", re.I)


def is_sensitive(key: str) -> bool:
    """法人／業務名稱優先判定，避免 `companyName` 被 `name` 誤判成個資。"""
    if BUSINESS_NAME.search(key):
        return False
    return bool(PERSONAL.search(key))


def mask(key: str, value, raw: bool) -> str:
    """⚠️ 預設遮罩疑似**個人**資料。我們要的是「有沒有這個欄位」，不是值本身。"""
    if isinstance(value, (dict, list)):
        return f"<{type(value).__name__} len={len(value)}>"
    s = str(value)
    if not raw and is_sensitive(key):
        return f"<已遮罩 len={len(s)}>"
    return s[:60] + ("…" if len(s) > 60 else "")


def census(payload, raw: bool) -> None:
    """把回應攤平，統計每個欄位路徑出現在幾筆紀錄裡。

    ⚠️ **出現次數才是重點**，不是「有沒有出現過」——
       OHIP **值為 0／空的欄位會被整個省略**，所以一個欄位若只出現在
       3/200 筆裡，代表它「存在但多數情況沒值」，做成模組時要當缺值處理。
    """
    # 先找出「一筆紀錄」的陣列在哪一層
    records = _find_records(payload)
    print(f"\n{'═' * 74}")
    print(f"欄位普查：找到 {len(records)} 筆紀錄")
    print(f"{'═' * 74}")
    if not records:
        print("⚠️ 找不到可辨識的紀錄陣列。原始結構的最外層鍵：")
        print("   ", _top_keys(payload))
        return

    seen: Counter[str] = Counter()
    types: dict[str, set] = defaultdict(set)
    samples: dict[str, str] = {}

    for rec in records:
        for path, val in _walk(rec):
            seen[path] += 1
            types[path].add(type(val).__name__)
            if path not in samples:
                samples[path] = mask(path, val, raw)

    n = len(records)
    print(f"\n{'欄位路徑':<44}{'出現':>10}  {'型別':<16}範例")
    print("-" * 108)
    for path, cnt in sorted(seen.items(), key=lambda kv: (-kv[1], kv[0])):
        pct = f"{cnt}/{n}"
        flag = "" if cnt == n else "  ⚠️部分"
        tp = "/".join(sorted(types[path]))
        print(f"{path:<44}{pct:>10}  {tp:<16}{samples[path]}{flag}")

    nested = _nested_arrays(records)
    if nested:
        print(f"\n巢狀子表（第一筆紀錄裡的陣列）：")
        for path, cnt in nested:
            print(f"   {path:<40} {cnt} 筆")
        print("   ⚠️ 普查只看每個陣列的**第一個元素**的結構，筆數請以上表為準")

    print(f"\n{'─' * 74}")
    print("判讀提示：")
    print("  ・「出現 3/200」代表該欄位存在但多數紀錄沒值 —— OHIP 會省略 0/空值")
    print("  ・找不到 marketCode / sourceCode / rateCode 就代表通路分析做不了")
    print("  ・有 profile 相關欄位 → 回訪客分析可行，但要先決定個資落地政策")
    print("  ・companyName / travelAgentName 等法人名稱**刻意不遮罩** ——")
    print("    「哪些公司貢獻最多」正是要回答的問題，遮掉就白跑一趟")


def _find_records(payload) -> list:
    """找出「一筆紀錄」的陣列 —— 取**最外層**的 dict 陣列（BFS，最淺的那個）。

    ⚠️ 第一版取「元素最多」的陣列，結果在 blkasync 上選到巢狀的 `allocationDates`
       （2 筆），**漏掉只有 1 筆的最外層 block**，於是 blockCode／marketCode／
       cutOffDays／blockProfiles 這些**最重要的欄位全部沒出現在普查表裡**。
       正確做法是取最外層 —— `_walk()` 本來就會往下鑽進巢狀結構，
       所以從最外層開始才會涵蓋完整。
    """
    queue = [payload]
    while queue:
        node = queue.pop(0)
        if isinstance(node, list):
            if node and isinstance(node[0], dict):
                return node
            queue.extend(node)
        elif isinstance(node, dict):
            queue.extend(node.values())
    return []


def _nested_arrays(records: list) -> list[tuple[str, int]]:
    """列出紀錄裡的巢狀陣列與長度 —— 提醒使用者「這一層還有子表」。"""
    out: list[tuple[str, int]] = []
    if not records:
        return out
    def rec(node, prefix=""):
        if isinstance(node, dict):
            for k, v in node.items():
                p = f"{prefix}.{k}" if prefix else k
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    out.append((p, len(v)))
                    rec(v[0], p + "[]")
                elif isinstance(v, dict):
                    rec(v, p)
    rec(records[0])
    return out


def _walk(node, prefix: str = ""):
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (dict, list)):
                yield p, v
                yield from _walk(v, p)
            else:
                yield p, v
    elif isinstance(node, list):
        for x in node[:1]:      # 陣列只看第一個元素的結構就夠了
            yield from _walk(x, prefix + "[]")


def _top_keys(payload) -> object:
    if isinstance(payload, list):
        return f"list(len={len(payload)}) → " + (
            str(list(payload[0].keys())) if payload and isinstance(payload[0], dict) else "?")
    if isinstance(payload, dict):
        return list(payload.keys())
    return type(payload).__name__


# ── 主流程 ───────────────────────────────────────────────────────────────────

def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    raw = "--raw" in sys.argv
    save = "--save" in sys.argv

    end = date.fromisoformat(args[1]) if len(args) > 1 else date.today() - timedelta(days=1)
    start = date.fromisoformat(args[0]) if args else end - timedelta(days=6)

    print("=" * 74)
    print("OHIP 探測 — Reservation Async（getReservationsDailySummary）")
    print("=" * 74)
    print(f"hotelId={HOTEL_ID}  extSystemCode={EXT_CODE}  區間={start} ～ {end}")
    print(f"個資遮罩：{'關閉（--raw）' if raw else '開啟'}")
    print()

    if not preflight():
        sys.exit(1)
    token = get_token()

    bodies = body_candidates(start, end)

    # ── 步驟 1：找出可用的 path × body 組合 ──────────────────────────────────
    print(f"\n{'─' * 74}\n步驟 1：找出可用的路徑與 body 組合")
    print("⚠️ 路徑與 body 欄位名都是從 invasync 類推的，未經查證（見檔頭）\n")

    found = None
    for path in PATH_CANDIDATES:
        for bname, body in bodies:
            # ⚠️ 顯示完整路徑尾段。第一輪用 split('/hotels/')[0] 導致三個不同路徑
            #    印出完全一樣的字串，看起來像「同一個路徑試了九次」，非常誤導。
            label = f"…/{path.rsplit('/hotels/', 1)[-1].split('/', 1)[-1]} + {bname}"
            st = check_subscription(token, label, path, body)
            if st == "ok":
                found = (path, bname, body)
                break
            if st == "not_subscribed":
                # 未訂閱時換 body 也沒用，直接換下一個路徑
                break
        if found:
            break

    # ── 步驟 2：blkasync 路徑探測（順位 4 前置）────────────────────────────
    blk_body = {"startDate": start.isoformat(), "endDate": end.isoformat()}
    blk_path = probe_block_paths(token, blk_body)

    # ── 步驟 3：逐層反推 rsv 的 request body ────────────────────────────────
    if not found:
        win = discover_schema(token, CONFIRMED_PATH, start, end)
        if win:
            print(f"\n🎯 找到可用的 rsv body：\n{json.dumps(win, ensure_ascii=False)}")
            found = (CONFIRMED_PATH, "反推所得", win)

    # ── 步驟 5：blkasync 取數並普查（順位 4 —— 既然可用就一次做完）──────────
    if blk_path:
        print(f"\n{'─' * 74}\n步驟 5：Block Async 取數並普查欄位（順位 4）\n")
        got = async_read(token, blk_path, blk_body)
        if got:
            payload, nbytes = got
            print(f"\n回應大小：{nbytes:,} bytes"
                  f"（2 MB 上限的 {nbytes / TRUNCATE_LIMIT:.0%}）")
            print(f"最外層結構：{_top_keys(payload)}")
            census(payload, raw)
            if save:
                out = Path(__file__).parent / f"ohip_blocks_sample_{start}_{end}.json"
                out.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                               encoding="utf-8")
                print(f"\n💾 Block 原始 JSON 已存到 {out.name}")

    if not found:
        print(f"""
{'═' * 74}
結論：**沒有找到可用的組合**
{'═' * 74}
請把**步驟 2、3、5 的完整輸出**回報。判讀方向：

  ・步驟 3 列出「OPERA 認得的欄位」→ 貼回來，我用那些欄位組完整 body
  ・步驟 3 全部不存在              → 到 dev portal 的 API 文件頁找
                                     startReservationsDailySummaryProcess 的
                                     request body schema，把欄位名貼回來（不必再猜）
  ・步驟 2 有一行是 400            → 那就是 blkasync 的正確路徑，順位 4 可以往下

⚠️ 2026-08-07 已確認：`…/reservations/dailySummary` 回 400 而非 404/403，
   代表**路徑正確且 Application 已訂閱 Reservation Async**，
   卡住的只有 request body 的欄位名。

⚠️ 在確認可用之前，**不要**放寬 `ohip_client.py` 的 async 路徑白名單。
""")
        sys.exit(2)

    path, bname, body = found
    print(f"\n✅ 可用組合：{path}\n   body 形式：{bname}")

    # ── 步驟 4：rsv 實際取數並做欄位普查 ────────────────────────────────────
    print(f"\n{'─' * 74}\n步驟 4：Reservation 取數並普查實際回傳的欄位\n")
    got = async_read(token, path, body)
    if not got:
        sys.exit(3)
    payload, nbytes = got

    print(f"\n回應大小：{nbytes:,} bytes"
          f"（2 MB 上限的 {nbytes / TRUNCATE_LIMIT:.0%}）")
    if nbytes >= TRUNCATE_LIMIT * 0.9:
        print("⚠️ 已逼近 2 MB —— Oracle 會**靜默截斷**（不報錯）。"
              "縮短區間再跑一次，比對兩次的筆數是否一致。")

    print(f"最外層結構：{_top_keys(payload)}")
    census(payload, raw)

    if save:
        # ⚠️ 含個資，存檔前提醒
        out = Path(__file__).parent / f"ohip_reservations_sample_{start}_{end}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n💾 原始 JSON 已存到 {out.name}")
        print("⚠️ 這個檔案含住客姓名與會員卡號，**不要進 git、不要外傳**，看完請刪除。")

    print(f"""
{'═' * 74}
下一步
{'═' * 74}
把上面的「欄位普查」表格貼回來，我會據此更新
`docs/EVAL_ohip_strategic_data.md` §4.1 與
`docs/ANALYSIS_opera_realtime_matrix.md` §2.4，
並判斷「住客與通路分析」哪幾項真的可以翻案。

⚠️ 在看到真實欄位之前，不要開始寫 parser 或建資料表 ——
   2026-08-06 已經因為「spec 寫有就當作有」錯過一次。
""")


if __name__ == "__main__":
    main()
