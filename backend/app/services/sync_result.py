"""
同步結果彙總（2026-10-30）

sync_tool.py／main.py 只讀取回傳 dict 的頂層 fetched／upserted／errors。
多頁籤模組（sync_all）若只回傳「依頁籤分組的巢狀結果」，工具會顯示 fetched=0、
且看不到內部錯誤。aggregate_sync_results 把各頁籤加總到頂層，並保留 by_sheet 明細。
"""
from __future__ import annotations

from typing import Any


def aggregate_sync_results(results: dict[str, Any]) -> dict[str, Any]:
    totals: dict[str, Any] = {"fetched": 0, "upserted": 0, "item_rows": 0, "errors": []}
    for key, res in results.items():
        if not isinstance(res, dict):
            continue
        for f in ("fetched", "upserted", "item_rows"):
            totals[f] += int(res.get(f, 0) or 0)
        errs = res.get("errors", [])
        if isinstance(errs, int):
            if errs:
                totals["errors"].append(f"{key}: {errs} 筆錯誤")
        else:
            totals["errors"].extend(f"{key}: {e}" for e in errs)
    totals["by_sheet"] = results
    return totals
