# 週期採購（週採）技術文件 — Jupyter Book

## 直接看

開啟 `_build/html/index.html`。

> 流程圖走 Mermaid CDN，第一次開啟需要網路。

## 重新建置

```bash
pip install "jupyter-book<2" sphinxcontrib-mermaid matplotlib pandas
cd docs/jupyterbook/cycle-purchase
jupyter-book build .
```

## 讓〈資料分析〉跑真實數字

該章節預設依序找：環境變數 `CP_DB` → `C:/portal_data/cycle-purchase.db` → `backend/cycle-purchase.db`。
找不到就用示範資料，並在圖上打「示範資料」浮水印。

```bash
set CP_DB=C:\portal_data\cycle-purchase.db
jupyter-book build . --all
```

## 檔案

| 檔案 | 內容 |
|------|------|
| `_config.yml` / `_toc.yml` | Jupyter Book 設定與目錄 |
| `intro.md` | 首頁 |
| `01-overview.md` ~ `02-architecture.md` | 模組總覽、架構 |
| `03-flow.md` / `04-manual.md` | 流程狀態機、使用手冊 |
| `05-data-model.md` ~ `09-integration.md` | 開發者參考 |
| `10-analysis.ipynb` | 資料分析（可連實際 DB） |
| `90-todo.md` / `91-glossary.md` | 待辦、名詞對照 |

## 注意

- `_build/` 是產出物，不需要進版控。
- 專案 `.gitignore` 第 42 行忽略 `*.md`，本資料夾的 md 檔預設不在版控中。
