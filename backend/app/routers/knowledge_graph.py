"""
knowledge_graph.py
──────────────────
專案知識圖譜 Router

GET  /api/v1/knowledge-graph/status    查詢圖譜狀態（idle / generating / ready）
POST /api/v1/knowledge-graph/generate  觸發 graphify 分析（BackgroundTask）
GET  /api/v1/knowledge-graph/result    直接下載 graph.html（驗證後存取）

靜態檔案另由 main.py 掛載 /kg-files/ → backend/static/knowledge_graph/
前端 iframe 指向 /kg-files/graph.html（無需 auth header）

權限：system_admin only
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from app.dependencies import require_roles
from app.models.user import User
import app.services.graphify_runner as runner

router = APIRouter()

# 僅限 system_admin 存取（沿用既有 require_roles 工廠函式）
_require_admin = require_roles("system_admin")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status")
def get_status(current_user: User = Depends(_require_admin)):
    """
    回傳目前圖譜狀態。

    Response:
      {
        "status": "idle" | "generating" | "ready",
        "generated_at": "2026-05-10T14:30:00" | null,
        "html_exists": true | false,
        "error": "錯誤訊息" | null
      }
    """
    return runner.get_status()


@router.post("/generate")
def generate(
    bg: BackgroundTasks,
    current_user: User = Depends(_require_admin),
):
    """
    觸發 graphify 分析整個 portal 專案並產生知識圖譜。
    若已在執行中，回傳 400。
    前端應輪詢 /status 每 3 秒確認進度。
    """
    st = runner.get_status()
    if st["status"] == "generating":
        raise HTTPException(status_code=400, detail="圖譜產生中，請稍候完成再重試")

    bg.add_task(runner.run_graphify_sync)
    return {"message": "已開始產生知識圖譜，請輪詢 /status 查看進度"}


@router.get("/result")
def get_result(current_user: User = Depends(_require_admin)):
    """
    直接回傳 graph.html（驗證後存取）。
    若圖譜尚未產生，回傳 404。
    """
    html_file = runner._find_html()
    if html_file is None:
        raise HTTPException(
            status_code=404,
            detail="尚未產生圖譜，請先點選「產生圖譜」按鈕",
        )
    return FileResponse(str(html_file), media_type="text/html")
