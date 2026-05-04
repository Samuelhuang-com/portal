---
id: 04dbf2ca-c71f-43e6-8c3e-4ab211efa3bd
title: SQLite WAL 模式與 OneDrive 環境注意事項
slug: sqlite-wal-模式與-onedrive-環境注意事項
category: dev
tags:
- SQLite
- 資料庫
- 部署
- 除錯
author: 系統預設
author_id: system
is_published: true
created_at: '2026-05-03T22:26:39.799607'
updated_at: '2026-05-03T22:26:39.799607'
---

# SQLite WAL 模式與 OneDrive 環境注意事項

## 背景
Portal 的 SQLite 資料庫放在 OneDrive 同步資料夾中，這會導致：
- 多個行程同時讀寫時發生鎖定衝突
- OneDrive 的檔案系統監視器干擾 WAL 檔案

## WAL 模式設定（啟動時執行）

```python
# main.py lifespan
with engine.connect() as conn:
    conn.execute(text("PRAGMA journal_mode=WAL"))
    conn.execute(text("PRAGMA busy_timeout=30000"))   # 30 秒等待鎖
    conn.execute(text("PRAGMA synchronous=NORMAL"))
    conn.commit()
```

## 關鍵 WAL 檔案
SQLite WAL 模式會產生兩個額外檔案：
- `portal.db-wal`：Write-Ahead Log
- `portal.db-shm`：Shared Memory

> ⚠️ 這兩個檔案是正常的，**不要刪除**

## 常見問題

### 問題：`database is locked`
**原因**：busy_timeout 太短，或另一個行程持有鎖太久

**解法**：
```python
PRAGMA busy_timeout=30000  # 提高到 30 秒
```

### 問題：OneDrive 自動備份衝突
**原因**：OneDrive 在備份 .db 時會鎖定檔案

**解法**：在 OneDrive 排除同步 `*.db-wal` 和 `*.db-shm` 檔案

### 問題：同步模式 vs 異步模式
本專案使用**同步 SQLAlchemy**（非 async），原因：
- `aiosqlite` 在 WAL 模式 + OneDrive 環境下不穩定
- APScheduler 的同步任務較易整合

> ❌ 禁止將同步模式改回 async（CLAUDE.md 規則）

