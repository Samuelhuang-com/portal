"""
OHIP（Oracle Hospitality Integration Platform）統一 HTTP 客戶端

規劃文件：docs/OHIP_INTEGRATION.md

設計原則
────────────────────────────────────────────────────────────────────────────
1. **只允許 GET**。目前串接的是 OPERA Cloud 的 **Production** 環境，
   Portal 只做讀取。非 GET 方法在本模組直接擋掉，不靠呼叫端自律。

2. **Token 必須快取**。OHIP 按呼叫量計費，且換 token 本身也算一次呼叫。
   實測 `expires_in` 為 28800 秒（8 小時），但**一律以回傳值為準、不寫死**
   （文件寫 3600，與實測不符）。到期前 120 秒主動換新（Oracle 建議）。

3. **跨執行緒安全**。APScheduler 與 API request 可能同時觸發換 token，
   用 `threading.Lock` 確保只換一次。這與既有 `sync_lock.py` 的思路一致。

4. **每次呼叫都回傳 metadata**。畫面上要標示「這筆數字是幾點幾分從 API 抓的」，
   所以 `get()` 回傳 `(payload, meta)`，meta 含耗時、狀態碼、x-request-id、
   是否命中快取 —— 呼叫端不需要自己量時間。

三個實測踩過的坑（2026-08-06，詳見規劃文件 §3.1、§4.1）
────────────────────────────────────────────────────────────────────────────
① 換 token **必須帶 `enterpriseId` header**（不是 body）。漏掉會回
   401 "Failed to authenticate application" —— 訊息指向 application，
   完全誤導；且 app-key 故意填錯也是同一句，沒有鑑別度。
② OHIP 的 Basic auth **要真的做 base64**。CLAUDE.md 中「Ragic 不做 base64」
   的規則只適用 Ragic，兩者不可互套。
③ Property API 的回傳最外層是 **list 不是 dict**。
"""
from __future__ import annotations

import base64
import threading
import time
import uuid
from typing import Any

import requests

from app.core.config import settings


# ── Token 快取（模組層，跨 request 共用）──────────────────────────────────────
_token_lock = threading.Lock()
_token_value: str | None = None
_token_expires_at: float = 0.0          # epoch 秒
_token_renew_margin = 120               # 到期前多久換新

DEFAULT_TIMEOUT = 45


class OhipError(RuntimeError):
    """OHIP 呼叫失敗。訊息已整理成可直接顯示給使用者的中文。"""

    def __init__(self, message: str, status_code: int | None = None,
                 request_id: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


def is_configured() -> bool:
    """憑證是否齊全。未設定時整個即時功能應優雅降級，而不是噴 500。"""
    return all([
        settings.OHIP_GATEWAY_URL,
        settings.OHIP_APP_KEY,
        settings.OHIP_CLIENT_ID,
        settings.OHIP_CLIENT_SECRET,
        settings.OHIP_ENTERPRISE_ID,
    ])


def missing_settings() -> list[str]:
    return [
        name for name, val in [
            ("OHIP_GATEWAY_URL", settings.OHIP_GATEWAY_URL),
            ("OHIP_APP_KEY", settings.OHIP_APP_KEY),
            ("OHIP_CLIENT_ID", settings.OHIP_CLIENT_ID),
            ("OHIP_CLIENT_SECRET", settings.OHIP_CLIENT_SECRET),
            ("OHIP_ENTERPRISE_ID", settings.OHIP_ENTERPRISE_ID),
            ("OHIP_HOTEL_ID", settings.OHIP_HOTEL_ID),
        ] if not val
    ]


def _gateway() -> str:
    return settings.OHIP_GATEWAY_URL.rstrip("/")


# ── Token ────────────────────────────────────────────────────────────────────

def _fetch_token() -> tuple[str, int]:
    """實際打 OHIP 換 token。回傳 (token, expires_in 秒)。"""
    url = f"{_gateway()}/oauth/v1/tokens"
    basic = base64.b64encode(
        f"{settings.OHIP_CLIENT_ID}:{settings.OHIP_CLIENT_SECRET}".encode()
    ).decode()

    try:
        resp = requests.post(
            url,
            headers={
                "x-app-key": settings.OHIP_APP_KEY,
                # ⚠️ 坑 ①：OCIM + client_credentials 必須帶這個 header
                "enterpriseId": settings.OHIP_ENTERPRISE_ID,
                "Authorization": f"Basic {basic}",   # ⚠️ 坑 ②：要真的 base64
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": settings.OHIP_SCOPE,
            },
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException as e:
        raise OhipError(f"連線 OHIP 失敗：{type(e).__name__}") from e

    if resp.status_code != 200:
        hint = {
            400: "enterpriseId 未帶或格式錯誤",
            401: "憑證驗證失敗（優先檢查 enterpriseId header，其次 client_id / client_secret）",
            403: "scope 不正確，或 Application 未訂閱",
            404: "Gateway URL 錯誤",
        }.get(resp.status_code, "")
        raise OhipError(
            f"OHIP 換 token 失敗（HTTP {resp.status_code}）{'：' + hint if hint else ''}",
            status_code=resp.status_code,
            request_id=resp.headers.get("X-Request-Id"),
        )

    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise OhipError("OHIP 回應中沒有 access_token")
    return token, int(data.get("expires_in") or 3600)


def get_token(force: bool = False) -> str:
    """取得（必要時更新）access token。執行緒安全。"""
    global _token_value, _token_expires_at

    now = time.time()
    if not force and _token_value and now < _token_expires_at:
        return _token_value

    with _token_lock:
        # double-check：等鎖期間可能已被別的執行緒換好了
        now = time.time()
        if not force and _token_value and now < _token_expires_at:
            return _token_value

        token, expires_in = _fetch_token()
        _token_value = token
        # ⚠️ 以回傳的 expires_in 為準，不寫死；到期前 120 秒就換
        _token_expires_at = time.time() + max(expires_in - _token_renew_margin, 60)
        return token


def token_status() -> dict[str, Any]:
    """給診斷端點看的 token 狀態（不外洩 token 本身）。"""
    if not _token_value:
        return {"cached": False, "expires_in_seconds": 0}
    return {
        "cached": True,
        "expires_in_seconds": max(int(_token_expires_at - time.time()), 0),
    }


def reset_token_cache() -> None:
    """測試或憑證變更後強制清空。"""
    global _token_value, _token_expires_at
    with _token_lock:
        _token_value = None
        _token_expires_at = 0.0


# ── GET ──────────────────────────────────────────────────────────────────────

def get(path: str, params: list[tuple[str, str]] | dict | None = None,
        hotel_id: str | None = None,
        timeout: int = DEFAULT_TIMEOUT) -> tuple[Any, dict[str, Any]]:
    """對 OHIP 發一次 GET。

    Args:
        path:     以 / 開頭的路徑，例如 `/inv/v1/hotels/SUMMER/inventoryStatistics`
        params:   query。**若同一個 key 要重複出現（如 parameterName），
                  必須傳 list of tuple，不能用 dict。**
        hotel_id: 送 `x-hotelid`；省略則用 settings.OHIP_HOTEL_ID

    Returns:
        (payload, meta)。meta 含 `elapsed_ms` / `status_code` / `request_id`
        / `endpoint` / `called_at_epoch`，供畫面標示與日誌使用。

    Raises:
        OhipError：憑證未設定、非 GET、HTTP 非 200、或連線失敗。
    """
    if not is_configured():
        raise OhipError(
            "OHIP 尚未設定完成，缺少：" + "、".join(missing_settings())
        )

    if not path.startswith("/"):
        path = "/" + path

    token = get_token()
    request_id = str(uuid.uuid4())
    url = f"{_gateway()}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-app-key": settings.OHIP_APP_KEY,
        "x-hotelid": hotel_id or settings.OHIP_HOTEL_ID,
        "x-request-id": request_id,
        "Accept": "application/json",
    }

    started = time.perf_counter()
    called_at = time.time()
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
    except requests.RequestException as e:
        raise OhipError(f"呼叫 OHIP 失敗：{type(e).__name__}") from e

    # token 剛好在這一刻過期 → 強制換一次再重試（只重試一次）
    if resp.status_code == 401:
        token = get_token(force=True)
        headers["Authorization"] = f"Bearer {token}"
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        except requests.RequestException as e:
            raise OhipError(f"呼叫 OHIP 失敗（重試）：{type(e).__name__}") from e

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    meta = {
        "endpoint": path,
        "status_code": resp.status_code,
        "elapsed_ms": elapsed_ms,
        "request_id": resp.headers.get("X-Request-Id") or request_id,
        "called_at_epoch": called_at,
    }

    if resp.status_code != 200:
        hint = {
            400: "參數錯誤（日期區間可能超過 62 天，或 parameterName/parameterValue 未成對）",
            401: "token 失效",
            403: "Application 未訂閱該 API，或此 hotelId 無權限",
            404: "hotelId 不存在或路徑錯誤",
            429: "呼叫頻率超過限制",
        }.get(resp.status_code, "")
        raise OhipError(
            f"OHIP 回應 HTTP {resp.status_code}{'：' + hint if hint else ''}",
            status_code=resp.status_code,
            request_id=meta["request_id"],
        )

    return resp.json(), meta


# ── 非同步唯讀（async read）────────────────────────────────────────────────────
#
# ⚠️ 為什麼這裡會有 POST，卻不違反「唯讀」原則
# ────────────────────────────────────────────────────────────────────────────
# OHIP 的營收統計只存在於**非同步版** API，它的讀取流程規定是三段式：
#     POST 啟動查詢工作 → HEAD 輪詢狀態 → GET 取結果
# 那個 POST **不寫入任何業務資料**，body 只有查詢條件（日期區間、groupBy），
# 它是「讀」的一部分，不是「寫」。
#
# 但為了不讓這個例外變成後門，這裡**不開放通用的 post()**，
# 而是只允許白名單內的 async 讀取路徑。任何其他路徑一律拒絕。

# 只有這些 path suffix 允許用 async 讀取啟動
# ⚠️ 加入前提：**該端點必須已經實測確認可用**。
#    2026-08-07 先用獨立探測腳本（`ohip_probe_reservations.py`）確認
#    rsvasync／blkasync 的路徑與 body 之後才放進白名單，
#    刻意不在「還在猜」的階段先放寬 —— 白名單一旦鬆掉就很難再收緊。
_ASYNC_READ_ALLOWED = (
    "/revenueInventoryStatistics",
    "/inventoryStatistics",
    # 逐筆訂房（2026-08-07 實測：2 個月 2375 筆）
    "/reservations/dailySummary",
    # 團體 block 配房與 pickup（2026-08-07 實測可用）
    "/blocks/allocationSummary",
)

ASYNC_POLL_INTERVAL = 2.0      # 秒
ASYNC_POLL_MAX = 15            # 最多等 30 秒

# ── 2 MB 靜默截斷（2026-08-07 新增，同日下修為「僅供參考」）──────────────────
# Oracle 官方：「Responses exceeding 2 MB are automatically truncated by the API.」
#
# ⚠️ **但實測與這句話矛盾。** 2026-08-07 用 rsvasync 查兩個月的訂房，
#    拿到 **5,685,994 bytes**（2 MB 的 284%）且能完整解析出 2375 筆 ——
#    也就是說**沒有**在 2 MB 被截斷。
#    可能的解釋：那句話只適用部分端點／指的是壓縮後大小／官方文件過時。
#    **無法確認，所以不改變行為**：本模組仍然只「量大小並示警」，
#    不會因此丟棄或改動任何資料。
#    → 但這也代表 `truncation_risk=True` **不等於資料真的不完整**，
#      呼叫端不應該把它當成錯誤，只能當成「值得用縮小區間比對筆數來驗證」的提示。
# ⚠️ 官方**沒有說**截斷時會不會給任何訊號（header／欄位／狀態碼都沒提），
#    也就是說我們很可能拿到一份「看起來正常但其實不完整」的資料 ——
#    這比直接報錯危險得多。
# ⚠️ 「2 MB」是 2,000,000 還是 2 MiB（2,097,152）官方沒有明確定義。
#    這裡取**較小**的 2,000,000 當基準，寧可早一點示警。
#    → 本模組只負責「量出大小並示警」，不自作主張改變回傳內容。
#      判斷資料是否真的被截斷（例如比對筆數）是呼叫端的責任。
ASYNC_TRUNCATE_LIMIT_BYTES = 2_000_000
ASYNC_TRUNCATE_WARN_RATIO = 0.9        # 達 90% 就示警，不必等真的截斷


def _assert_async_read_allowed(path: str) -> None:
    if not any(path.endswith(sfx) for sfx in _ASYNC_READ_ALLOWED):
        raise OhipError(
            f"async 讀取不允許此路徑：{path}"
            f"（白名單：{'、'.join(_ASYNC_READ_ALLOWED)}）"
        )


def async_read(path: str, body: dict, hotel_id: str | None = None,
               timeout: int = DEFAULT_TIMEOUT) -> tuple[Any, dict[str, Any]]:
    """非同步唯讀：POST 啟動 → HEAD 輪詢 → GET 取結果。

    Args:
        path: 以 / 開頭，且必須落在 `_ASYNC_READ_ALLOWED` 白名單內
        body: 查詢條件（如 dateRangeStart／dateRangeEnd／groupBy）

    Returns:
        (payload, meta)。meta 額外含 `poll_count`，供觀察 OPERA 端的處理時間。

    Raises:
        OhipError：路徑不在白名單、憑證未設定、HTTP 失敗、或輪詢逾時。
    """
    if not is_configured():
        raise OhipError("OHIP 尚未設定完成，缺少：" + "、".join(missing_settings()))

    if not path.startswith("/"):
        path = "/" + path
    _assert_async_read_allowed(path)

    token = get_token()
    request_id = str(uuid.uuid4())
    hid = hotel_id or settings.OHIP_HOTEL_ID
    headers = {
        "Authorization": f"Bearer {token}",
        "x-app-key": settings.OHIP_APP_KEY,
        "x-hotelid": hid,
        "x-request-id": request_id,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    started = time.perf_counter()
    called_at = time.time()

    # ── 1. POST 啟動 ──────────────────────────────────────────────────────────
    try:
        resp = requests.post(f"{_gateway()}{path}", headers=headers,
                             json=body, timeout=timeout)
    except requests.RequestException as e:
        raise OhipError(f"啟動 OHIP 非同步查詢失敗：{type(e).__name__}") from e

    if resp.status_code not in (200, 201, 202):
        # ⚠️ Oracle 規定相同參數的 async 請求最短間隔 30 分鐘，
        #    但**官方文件沒有寫違規時回哪個狀態碼**。因此 400 與 429 的提示
        #    都把「可能是 30 分鐘限制」列進去，不去猜是哪一個。
        #    正常情況下 Portal 會在本地先擋（見 ohip_async_cache.CooldownActive），
        #    會走到這裡代表本地紀錄與 OPERA 端不同步（例如快取被清掉）。
        hint = {
            400: ("查詢條件錯誤（日期區間可能超過上限），"
                  "亦可能是相同條件距上次查詢未滿 30 分鐘"),
            403: "Application 未訂閱該 Asynchronous API，或 hotelId 無權限",
            404: "extSystemCode 或 hotelId 不存在",
            429: "呼叫頻率超過限制（相同條件的非同步查詢最短間隔 30 分鐘）",
        }.get(resp.status_code, "")
        raise OhipError(
            f"OHIP 非同步查詢啟動失敗（HTTP {resp.status_code}）"
            f"{'：' + hint if hint else ''}",
            status_code=resp.status_code,
            request_id=resp.headers.get("X-Request-Id") or request_id,
        )

    location = resp.headers.get("Location") or resp.headers.get("location") or ""
    if not location:
        raise OhipError("OHIP 未回傳 Location header，無法輪詢結果")
    if not location.startswith("http"):
        location = f"{_gateway()}{location}"

    # ── 2. HEAD 輪詢 ──────────────────────────────────────────────────────────
    #
    # ⚠️ **2026-08-07 修正的 bug：HTTP 200 不代表完成。**
    #
    # 原本的條件是 `if head.status_code in (200, 201, 303)`，把 200 當成完成。
    # 實測（`ohip_probe_reservations.py` 第三輪）確認 OPERA 的實際協定是：
    #
    #     HEAD → **200** + `Retry-After` header   → **處理中**（Retry-After 是倒數秒數）
    #     HEAD → **201** + `Location` header      → **完成**，去 Location 取結果
    #
    # 把 200 當完成，就會在工作還沒跑完時去 GET，結果拿到 **404**。
    # 之前沒踩到，是因為營收查詢都在 3 秒內完成、第一次 HEAD 就回 201；
    # 但**區間一拉長就必然踩到**（實測 2 個月的訂房查詢要輪詢 4 次、約 12 秒）。
    #
    # 判定改為：**必須拿到 Location header 才算完成**，這比看狀態碼可靠 ——
    # 不論對方用 201 還是 303，有 Location 就是有結果可取。
    poll_headers = {k: v for k, v in headers.items() if k != "Content-Type"}
    result_url = ""
    poll_count = 0
    last_status = 0

    for _ in range(ASYNC_POLL_MAX):
        poll_count += 1
        try:
            head = requests.head(location, headers=poll_headers, timeout=timeout)
        except requests.RequestException as e:
            raise OhipError(f"輪詢 OHIP 非同步結果失敗：{type(e).__name__}") from e

        last_status = head.status_code
        if head.status_code >= 400:
            raise OhipError(
                f"OHIP 非同步工作失敗（輪詢回 HTTP {head.status_code}）",
                status_code=head.status_code,
            )

        loc = head.headers.get("Location") or head.headers.get("location")
        if loc:
            # 有 Location = 工作完成，結果在那裡
            result_url = loc if loc.startswith("http") else f"{_gateway()}{loc}"
            break

        # 沒有 Location = 還在跑。OPERA 會用 Retry-After 告訴我們還要等多久，
        # 但那個值是「整個工作的剩餘上限」（實測從 300 開始遞減），
        # 不是「下次該隔多久再問」，所以**不能**拿來當 sleep 秒數。
        time.sleep(ASYNC_POLL_INTERVAL)

    if not result_url:
        raise OhipError(
            f"OHIP 非同步查詢逾時（{ASYNC_POLL_MAX} 次輪詢、"
            f"約 {int(ASYNC_POLL_MAX * ASYNC_POLL_INTERVAL)} 秒仍未完成，"
            f"最後一次 HEAD 回 {last_status}）。請縮短查詢區間再試。"
        )

    # ── 3. GET 取結果 ─────────────────────────────────────────────────────────
    try:
        got = requests.get(result_url, headers=poll_headers, timeout=timeout)
    except requests.RequestException as e:
        raise OhipError(f"取得 OHIP 非同步結果失敗：{type(e).__name__}") from e

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    # ⚠️ 2 MB 靜默截斷偵測：只量大小、只示警，不改資料（見上方常數說明）
    response_bytes = len(got.content or b"")
    truncation_risk = response_bytes >= int(
        ASYNC_TRUNCATE_LIMIT_BYTES * ASYNC_TRUNCATE_WARN_RATIO)

    meta = {
        "endpoint": path,
        "status_code": got.status_code,
        "elapsed_ms": elapsed_ms,
        "request_id": got.headers.get("X-Request-Id") or request_id,
        "called_at_epoch": called_at,
        "poll_count": poll_count,
        "response_bytes": response_bytes,
        "truncate_limit_bytes": ASYNC_TRUNCATE_LIMIT_BYTES,
        # True 代表「這次回應已逼近或超過 2 MB，資料可能不完整」，
        # **不代表已確認被截斷** —— 確認需要呼叫端做筆數合理性檢查。
        "truncation_risk": truncation_risk,
    }

    if got.status_code != 200:
        raise OhipError(
            f"OHIP 非同步結果回 HTTP {got.status_code}",
            status_code=got.status_code,
            request_id=meta["request_id"],
        )

    return got.json(), meta


# 明確不提供通用的 post / put / delete —— Production 環境，Portal 一律唯讀。
# 上面的 async_read 是唯一的 POST，且被白名單封死在讀取用途上。
