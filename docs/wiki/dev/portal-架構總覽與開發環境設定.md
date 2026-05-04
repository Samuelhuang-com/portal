---
id: 584bf743-41f6-4b09-9e73-6864919d9d98
title: Portal 架構總覽與開發環境設定
slug: portal-架構總覽與開發環境設定
category: dev
tags:
- 架構
- FastAPI
- React
- 環境設定
author: 系統預設
author_id: system
is_published: true
created_at: '2026-05-03T22:26:39.799607'
updated_at: '2026-05-03T22:26:39.799607'
---

# Portal 架構總覽與開發環境設定

## 技術棧

| 層次 | 技術 | 版本 |
|------|------|------|
| 後端 | FastAPI | 0.111 |
| ORM | SQLAlchemy | 2.0（同步模式） |
| 資料庫 | SQLite（WAL 模式） | 3.x |
| 前端 | React + TypeScript | 18 + 5 |
| UI 元件 | Ant Design | 5 |
| 狀態管理 | Zustand（auth only）+ useState | — |
| 外部資料 | Ragic API（Basic Auth） | — |

## 啟動開發環境

```bash
# 後端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端（另開終端）
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## 專案結構速查

```
portal/
├── backend/app/
│   ├── core/          # config, database, security, scheduler
│   ├── models/        # SQLAlchemy ORM 資料表
│   ├── routers/       # FastAPI 路由（每個模組一個檔案）
│   ├── schemas/       # Pydantic request/response 型別
│   ├── services/      # 業務邏輯（從 router 拆出）
│   └── main.py        # App 入口 + lifespan + router 掛載
└── frontend/src/
    ├── api/           # axios 封裝（每個模組一個檔案）
    ├── pages/         # React 頁面元件
    ├── components/    # 共用元件（Layout 等）
    ├── router/        # React Router v6 定義
    ├── stores/        # Zustand（只有 authStore）
    └── types/         # TypeScript 型別定義
```

## 重要規則（CLAUDE.md 摘要）
- API prefix 統一用 `/api/v1/`
- Ragic Basic Auth：直接用 API key，**不做 base64**
- 前端 API 呼叫：統一用 `@/api/` 下的封裝，**不在元件內直接用 axios**
- DB Session：永遠用 `Depends(get_db)`

