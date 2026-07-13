"""
ragic_client.py v1.0
Ragic API 客戶端 — 支援 GET / POST / UPDATE
API Key 從 .env 讀取，預設 dry_run=True
"""
import os
import json
import logging
from dotenv import load_dotenv

try:
    import requests
except ImportError:
    raise ImportError("請先安裝 requests：pip install requests")

load_dotenv()

VERSION = "v1.0"
ICON = "🌐"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

RAGIC_API_KEY = os.getenv("RAGIC_API_KEY", "")
RAGIC_BASE_URL = os.getenv("RAGIC_BASE_URL", "https://ap12.ragic.com/soutlet001")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"


class RagicClient:
    """Ragic REST API 封裝。所有寫入操作預設 dry_run=True。"""

    def __init__(self, api_key: str = RAGIC_API_KEY, base_url: str = RAGIC_BASE_URL, dry_run: bool = DRY_RUN):
        if not api_key:
            raise ValueError(f"{ICON} [{VERSION}] RAGIC_API_KEY 未設定，請檢查 .env 檔案。")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.dry_run = dry_run
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Basic {self.api_key}",
            "Content-Type": "application/json",
        })
        logger.info(f"{ICON} [{VERSION}] RagicClient 初始化完成 | base_url={self.base_url} | dry_run={self.dry_run}")

    def _url(self, form_path: str, record_id: str = "") -> str:
        path = form_path.lstrip("/")
        if record_id:
            return f"{self.base_url}/{path}/{record_id}"
        return f"{self.base_url}/{path}"

    def get_records(self, form_path: str, filters: dict = None) -> list:
        """取得表單記錄列表，支援簡單過濾條件。"""
        url = self._url(form_path)
        params = {}
        if filters:
            for k, v in filters.items():
                params[k] = v
        logger.info(f"{ICON} GET {url} | filters={filters}")
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        records = list(data.values()) if isinstance(data, dict) else data
        logger.info(f"{ICON} 取得 {len(records)} 筆記錄")
        return records

    def get_record(self, form_path: str, record_id: str) -> dict:
        """取得單筆記錄。"""
        url = self._url(form_path, record_id)
        logger.info(f"{ICON} GET {url}")
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def create_record(self, form_path: str, data: dict) -> dict:
        """新增記錄。dry_run=True 時僅印出不實際寫入。"""
        url = self._url(form_path)
        if self.dry_run:
            logger.info(f"{ICON} [DRY-RUN] POST {url} | data={json.dumps(data, ensure_ascii=False)}")
            return {"_dry_run": True, "data": data}
        logger.info(f"{ICON} POST {url}")
        resp = self.session.post(url, json=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"{ICON} 新增成功：{result}")
        return result

    def update_record(self, form_path: str, record_id: str, data: dict) -> dict:
        """更新記錄。dry_run=True 時僅印出不實際寫入。"""
        url = self._url(form_path, record_id)
        if self.dry_run:
            logger.info(f"{ICON} [DRY-RUN] POST {url} | data={json.dumps(data, ensure_ascii=False)}")
            return {"_dry_run": True, "record_id": record_id, "data": data}
        logger.info(f"{ICON} POST {url} (update)")
        resp = self.session.post(url, json=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        logger.info(f"{ICON} 更新成功：{result}")
        return result


def main():
    client = RagicClient()
    logger.info(f"{ICON} [{VERSION}] 連線測試：取得週期採購批次清單")
    records = client.get_records("cycle-purchase/batches")
    logger.info(f"{ICON} 共取得 {len(records)} 筆批次記錄")


if __name__ == "__main__":
    main()
