---
id: 00b93ce2-8d06-4ad7-9619-92bcce3b48df
title: Ragic API 整合設計筆記
slug: ragic-api-整合設計筆記
category: dev
tags:
- Ragic
- API設計
- 資料庫
- 同步
author: 系統預設
author_id: system
is_published: true
created_at: '2026-05-03T22:26:39.799607'
updated_at: '2026-05-03T22:26:39.799607'
---

# Ragic API 整合設計筆記

## 認證方式

```python
# ⚠️ 重要：不做 base64，直接用 API key
headers = {"Authorization": f"Basic {settings.RAGIC_API_KEY}"}
```

## 標準 Ragic fetch 模式

```python
import httpx
from app.core.config import settings

async def fetch_ragic_sheet(path: str, server_url: str = None, account: str = None) -> dict:
    base_url = f"https://{server_url or settings.RAGIC_SERVER_URL}/{account or settings.RAGIC_ACCOUNT}"
    url = f"{base_url}/{path}"
    headers = {"Authorization": f"Basic {settings.RAGIC_API_KEY}"}

    async with httpx.AsyncClient(verify=settings.RAGIC_VERIFY_SSL, timeout=30) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
```

## 資料同步架構

```
APScheduler（每30分鐘）
    └─ _auto_sync()
        └─ sync_from_ragic()  ← 每個模組的 sync service
            ├─ fetch_ragic_sheet()  ← 抓 Ragic 資料
            ├─ upsert 到 SQLite      ← 比對 ragic_id
            └─ 回傳 {fetched, upserted, errors}
```

## 多 Server / Account 設定
部分 Sheet 在不同的 Ragic 帳號（`soutlet001` vs `intraragicapp`）：

```python
# config.py 設定
RAGIC_PM_SERVER_URL: str = "ap12.ragic.com"   # 不同 server
RAGIC_PM_JOURNAL_PATH: str = "periodic-maintenance/6"

# sync service 中使用
result = await fetch_ragic_sheet(
    path=settings.RAGIC_PM_JOURNAL_PATH,
    server_url=settings.RAGIC_PM_SERVER_URL,
    account=settings.RAGIC_PM_ACCOUNT,
)
```

## 常見踩坑

### 問題 1：Ragic 回傳 -1 key
Ragic 有時會在 JSON 中加入 `-1` key 作為 metadata，需要過濾：
```python
data = {k: v for k, v in raw.items() if k != "-1"}
```

### 問題 2：子表格欄位
Ragic 子表格（subtable）是巢狀 JSON，需要遞迴解析：
```python
subtable = record.get("1000123", {})  # 子表格 field id
for row in subtable.values():
    item_name = row.get("1000124", "")
```

