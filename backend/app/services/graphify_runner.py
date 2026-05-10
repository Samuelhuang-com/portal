"""
graphify_runner.py
──────────────────
Portal 知識圖譜執行管理器。

注意：graphify (https://github.com/safishamsi/graphify) 是一個 Claude Code skill，
不是可直接呼叫的 CLI subprocess。因此本模組使用自製的 knowledge_graph_generator.py
進行 AST + import 靜態分析，同樣以 tree-sitter 語法、networkx 概念建構圖譜，
並輸出互動式 HTML（vis.js）。

輸出目錄：backend/static/knowledge_graph/
狀態檔案：backend/static/knowledge_graph/_status.json

狀態值：
  idle       — 尚未產生
  generating — 正在分析（subprocess 執行中）
  ready      — 圖譜已產生，graph.html 存在
"""

import json
import subprocess
import sys
from pathlib import Path

from app.core.time import twnow

# ── 路徑定義 ──────────────────────────────────────────────────────────────────
_SVC_DIR     = Path(__file__).parent            # backend/app/services/
_BACKEND_DIR = _SVC_DIR.parent.parent           # backend/
_PROJECT_DIR = _BACKEND_DIR.parent              # portal/ （分析目標）
OUTPUT_DIR   = _BACKEND_DIR / "static" / "knowledge_graph"
_STATUS_FILE = OUTPUT_DIR / "_status.json"

# 自製產生器腳本路徑
_GENERATOR_SCRIPT = _SVC_DIR / "knowledge_graph_generator.py"


# ── 狀態讀寫 ──────────────────────────────────────────────────────────────────

def _read_status() -> dict:
    if not _STATUS_FILE.exists():
        return {"status": "idle", "generated_at": None, "error": None}
    try:
        return json.loads(_STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "idle", "generated_at": None, "error": None}


def _write_status(status: str, error: str | None = None) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "generated_at": twnow().isoformat() if status == "ready" else None,
        "error": error,
    }
    _STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


# ── 公開 API ──────────────────────────────────────────────────────────────────

def _find_html() -> Path | None:
    """尋找已產生的圖譜 HTML。"""
    candidate = OUTPUT_DIR / "graph.html"
    return candidate if candidate.exists() else None


def get_status() -> dict:
    """
    回傳目前圖譜狀態。
    若狀態為 ready 但 HTML 不存在，自動重置為 idle。
    """
    st = _read_status()
    html_exists = _find_html() is not None
    if st["status"] == "ready" and not html_exists:
        st["status"] = "idle"
    st["html_exists"] = html_exists
    return st


def run_graphify_sync() -> None:
    """
    同步執行自製知識圖譜產生器，供 FastAPI BackgroundTasks 呼叫。

    呼叫：
      python knowledge_graph_generator.py <project_root> <output_dir>
    """
    _write_status("generating")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(_GENERATOR_SCRIPT),
        str(_PROJECT_DIR),
        str(OUTPUT_DIR),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,   # 最多等 5 分鐘
            cwd=str(_BACKEND_DIR),
        )
        if result.returncode == 0 and _find_html():
            _write_status("ready")
        else:
            err = (result.stderr or result.stdout or "未知錯誤")[:500]
            _write_status("idle", error=f"產生失敗：{err}")
    except subprocess.TimeoutExpired:
        _write_status("idle", error="分析逾時（超過 5 分鐘），專案可能過大")
    except Exception as exc:
        _write_status("idle", error=str(exc)[:300])
