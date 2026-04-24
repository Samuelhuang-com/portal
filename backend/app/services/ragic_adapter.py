"""
Ragic API Adapter
封裝所有對 Ragic Cloud 的 HTTP 呼叫，使用 httpx async client。

重要：Ragic API Key 直接放在 Authorization header，不需要再做 base64 編碼。
格式：Authorization: Basic {API_KEY}（原始程式 ragic_client.py 的做法）
"""
import hashlib
import json
from typing import Any

import httpx

from app.core.config import settings


class RagicAdapter:
    """
    Generic adapter for any Ragic sheet.
    sheet_path format: "{tab_folder}/{sheet_index}"  e.g. "ragicsales-order-management/1"
    """

    def __init__(
        self,
        sheet_path: str | None = None,
        api_key: str | None = None,
        server_url: str | None = None,
        account: str | None = None,
    ):
        self.api_key   = api_key    or settings.RAGIC_API_KEY
        self.server_url = server_url or settings.RAGIC_SERVER_URL   # e.g. "ap16.ragic.com"
        self.account   = account    or settings.ragic_account
        self.sheet_path = sheet_path or ""
        self.verify_ssl = settings.RAGIC_VERIFY_SSL

    # ── Internals ─────────────────────────────────────────────────────────────

    @property
    def base_url(self) -> str:
        return f"https://{self.server_url}/{self.account}/{self.sheet_path}"

    @property
    def auth_header(self) -> dict:
        # API Key 直接放在 Basic 後面，不再做 base64 編碼
        # （與原始 ragic_client.py 保持一致）
        return {
            "Authorization": f"Basic {self.api_key}",
            "Accept": "application/json",
        }

    def _base_params(self, extra: dict | None = None) -> dict:
        """共用 query params，與原始程式一致"""
        params: dict = {
            "api":     "",
            "version": settings.RAGIC_API_VERSION,
            "naming":  settings.RAGIC_NAMING,
        }
        if extra:
            params.update(extra)
        return params

    # ── Public methods ────────────────────────────────────────────────────────

    async def fetch_all(
        self,
        limit: int = 200,
        extra_params: dict | None = None,
    ) -> dict[str, Any]:
        """
        分頁拉取所有資料，回傳合併後的 dict { record_id: {field_id: value} }
        """
        all_data: dict[str, Any] = {}
        offset = 0

        async with httpx.AsyncClient(timeout=30.0, verify=self.verify_ssl) as client:
            while True:
                params = self._base_params({"limit": limit, "offset": offset})
                if extra_params:
                    params.update(extra_params)

                resp = await client.get(
                    self.base_url,
                    headers=self.auth_header,
                    params=params,
                )
                resp.raise_for_status()
                batch: dict = resp.json()

                if not isinstance(batch, dict):
                    break

                # 只保留數字 key（Ragic record ID）
                records = {k: v for k, v in batch.items() if k.lstrip("-").isdigit()}
                if not records:
                    break

                all_data.update(records)

                if len(records) < limit:
                    break
                offset += limit

        return all_data

    async def fetch_one(self, record_id: int | str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0, verify=self.verify_ssl) as client:
            resp = await client.get(
                f"{self.base_url}/{record_id}",
                headers=self.auth_header,
                params=self._base_params(),
            )
            resp.raise_for_status()
            return resp.json()

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0, verify=self.verify_ssl) as client:
            resp = await client.post(
                self.base_url,
                headers={**self.auth_header, "Content-Type": "application/json"},
                params=self._base_params(),
                json=data,
            )
            resp.raise_for_status()
            return resp.json()

    async def update(self, record_id: int | str, data: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0, verify=self.verify_ssl) as client:
            resp = await client.post(
                f"{self.base_url}/{record_id}",
                headers={**self.auth_header, "Content-Type": "application/json"},
                params=self._base_params(),
                json=data,
            )
            resp.raise_for_status()
            return resp.json()

    async def delete(self, record_id: int | str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0, verify=self.verify_ssl) as client:
            resp = await client.delete(
                f"{self.base_url}/{record_id}",
                headers=self.auth_header,
                params=self._base_params(),
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def compute_checksum(data: dict) -> str:
        """計算資料的 SHA-256 checksum，用於判斷資料是否變更。"""
        serialized = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()
