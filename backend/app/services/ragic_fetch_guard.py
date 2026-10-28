"""
Ragic 抓取防呆（2026-10-25，v2.10.156）

適用範圍：整棟巡檢 B1F／B2F／B4F／RF，以及商場工務巡檢（5 支）。
（共用的 RagicAdapter.fetch_all() 未修改，其他模組行為不變。）

與 RagicAdapter.fetch_all() 的差異：
  1. 不跟隨轉址：遇到 3xx 直接丟出 RagicFetchError，並附上 Location，
     讓同步紀錄能看出是表單改名／搬移，或 API 金鑰無權限導致轉到登入頁。
  2. 回應格式不符（HTML 登入頁、非 JSON、非 dict、dict 內沒有記錄 key）
     → 丟出例外，不再默默回傳 {}（商場工務巡檢先前就是這樣被誤判為「成功」）。
  3. 暫時性錯誤（HTTP 429、5xx、逾時、連線錯誤）→ 有限次數退避重試。
  4. 0 筆：本模組不視為例外，但呼叫端會把 ZERO_RECORD_WARNING 放進 errors，
     讓同步狀態變成「部分」（黃燈），而不是「成功」。
"""
import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PAGE_LIMIT     = 200
MAX_RETRIES    = 2
BACKOFF_SECONDS = (2, 5)

ZERO_RECORD_WARNING = "⚠ Ragic 回傳 0 筆，請確認表單路徑與 API 權限（若表單確實無資料可忽略）"


class RagicFetchError(Exception):
    """Ragic 抓取失敗，訊息已整理成可直接給人看的原因。"""


def _snippet(text: str, limit: int = 160) -> str:
    return " ".join((text or "").split())[:limit]


async def _get_with_retry(client: httpx.AsyncClient, adapter, params: dict) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = await client.get(adapter.base_url, headers=adapter.auth_header, params=params)
        except httpx.TransportError as exc:          # 含 TimeoutException
            last_exc = RagicFetchError(f"連線失敗（{type(exc).__name__}）：{exc}")
        else:
            if 300 <= resp.status_code < 400:
                # 不跟隨轉址：這通常代表表單改名／搬移，或金鑰無權限被導到登入頁
                location = resp.headers.get("location", "(無 Location 標頭)")
                raise RagicFetchError(
                    f"Ragic 轉址 HTTP {resp.status_code} → {location}"
                    "（表單可能改名或搬移，或 API 金鑰無權限）"
                )
            if resp.status_code == 429 or resp.status_code >= 500:
                last_exc = RagicFetchError(f"Ragic 暫時性錯誤 HTTP {resp.status_code}")
            elif resp.status_code >= 400:
                raise RagicFetchError(f"Ragic HTTP {resp.status_code}：{_snippet(resp.text)}")
            else:
                return resp
        if attempt < MAX_RETRIES:
            wait = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
            logger.warning(f"[RagicGuard] {last_exc}，{wait} 秒後重試（第 {attempt + 1} 次）")
            await asyncio.sleep(wait)
    raise last_exc  # type: ignore[misc]


async def fetch_all_guarded(adapter) -> dict[str, Any]:
    """
    分頁拉取 Ragic 記錄，回傳 { record_id: {field_id: value} }。
    失敗時丟出 RagicFetchError（或 httpx 例外），由呼叫端照舊轉成 errors。
    """
    all_data: dict[str, Any] = {}
    offset = 0
    async with httpx.AsyncClient(
        timeout=30.0, verify=adapter.verify_ssl, follow_redirects=False,
    ) as client:
        while True:
            params = adapter._base_params({"limit": PAGE_LIMIT, "offset": offset})
            resp = await _get_with_retry(client, adapter, params)

            if "text/html" in resp.headers.get("content-type", ""):
                raise RagicFetchError("Ragic 回傳 HTML（疑似登入頁或權限不足）")
            try:
                batch = resp.json()
            except ValueError:
                raise RagicFetchError(f"Ragic 回傳非 JSON：{_snippet(resp.text)}")
            if not isinstance(batch, dict):
                raise RagicFetchError(f"Ragic 回傳格式非 dict（{type(batch).__name__}）")

            records = {k: v for k, v in batch.items() if str(k).lstrip("-").isdigit()}
            if not records:
                if batch and offset == 0:
                    # 有內容卻沒有任何記錄 key → 多半是 Ragic 錯誤訊息
                    msg = batch.get("msg") or batch.get("message") or ""
                    detail = f"：{_snippet(str(msg))}" if msg else f"（前幾個 key：{list(batch)[:5]}）"
                    raise RagicFetchError(f"Ragic 回應沒有記錄資料{detail}")
                break

            all_data.update(records)
            if len(records) < PAGE_LIMIT:
                break
            offset += PAGE_LIMIT

    return all_data
