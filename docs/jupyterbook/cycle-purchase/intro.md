# 週期採購（週採）技術文件

本書是 Portal「週期採購」模組（`/cycle-purchase/*`）的完整技術文件，內容**直接盤點自專案原始碼**，
非依賴既有規劃文件轉述。

```{admonition} 內容基準
:class: note

- 盤點日期：**2026-08-20**
- 程式碼來源：`backend/app/{models,routers,services}/cycle_purchase_*.py`、
  `frontend/src/pages/CyclePurchase/**`、`backend/app/main.py`、`backend/app/routers/role_permissions.py`
- 既有文件交叉比對：`docs/CYCLE_PURCHASE_TODO.md`、`docs/SPEC_cycle_purchase_dept_scope.md`、
  `frontend/src/pages/CyclePurchase/Manual/content.ts`（站內使用手冊 v2.1）
```

## 這本書怎麼讀

| 你是誰 | 建議路徑 |
|--------|---------|
| 第一次接觸週採 | 一 → 二（流程 → 使用手冊） |
| 要接手開發／改功能 | 一 → 三（資料模型 → API → 權限） |
| 要查某個數字怎麼算的 | 三（資料模型）→ 四（資料分析） |
| 要評估還缺什麼 | 附錄「待辦與已知缺口」 |

## 一分鐘看懂週採

各部門填**請購單** → 月底**關閉** → 採購把各部門的量**彙整**成一張表 →
依供應商開**採購單** → 貨到了做**驗收** → 財務憑發票**請款**並分攤回各部門。

```{mermaid}
flowchart LR
    A[請購單<br/>PR] --> B[關閉]
    B --> C[彙整單<br/>Summary]
    C --> D[採購單<br/>PO]
    D --> E[驗收單<br/>RC]
    E --> F[請款單<br/>PAY]
    F --> G[費用分攤<br/>部門/成本中心/會計科目]
    C -. 拋轉 stub .-> H[(Ragic 匯總請購單)]
```

```{admonition} 週採與 Portal 其他模組最大的不同
:class: important

週採用**獨立的 SQLite 檔案** `cycle-purchase.db`，而且是 Portal 裡少數**原生填寫、非 Ragic 唯讀同步**的模組。
它的部門、成本中心、會計科目、供應商都是自己的一套主檔。
唯二的外部連動是**供應商鏡像自合約模組**、**部門鏡像自參考資料**（見〈整合與同步〉）。
```


```{admonition} 檢視需求
:class: note

流程圖使用 Mermaid，由 CDN（`cdn.jsdelivr.net`）載入。**第一次開啟需要連得上網際網路**，
否則圖的位置會是空白（文字內容不受影響）。
```

## 建置方式

```bash
cd docs/jupyterbook/cycle-purchase
pip install "jupyter-book<2" sphinxcontrib-mermaid matplotlib pandas
jupyter-book build .
# 產出：_build/html/index.html
```

要讓〈資料分析〉章節跑真實數字，建置前指定資料庫路徑：

```bash
set CP_DB=C:\portal_data\cycle-purchase.db
jupyter-book build . --all
```
