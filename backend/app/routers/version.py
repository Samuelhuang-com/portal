"""
系統版本資訊端點。

用途：正式區與測試區有時會因為部署（git pull）沒有成功套用而出現程式碼版本不一致，
但站上目前沒有任何方式可以快速比對兩邊實際跑的是哪個 commit。此端點回傳目前後端
執行程式碼所在 git repo 的 commit hash / 日期 / 訊息，方便直接用瀏覽器或 curl 打
`/api/v1/version` 比對正式區與測試區是否為同一版本。

2026-07-22 新增。刻意不加 Depends(get_current_user)：
- 此端點只回傳 git commit 資訊（非機敏資料），且目的就是要能不登入、快速從瀏覽器
  或 curl 直接檢查，因此經使用者確認後設計為公開端點。
- 這是目前唯一的公開端點，其餘所有端點仍維持原本的登入 / 權限驗證規則，未來新增
  端點請勿比照本檔案省略 Depends。
"""

import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter

router = APIRouter()

# backend/app/routers/version.py -> parents[2] = backend/
# git 指令會自動往上層找到 repo 根目錄的 .git，不需要手動組出 repo root 路徑。
_BACKEND_DIR = Path(__file__).resolve().parents[2]


def _run_git(args: list[str]) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=_BACKEND_DIR,
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.strip()
        return output or None
    except Exception:
        return None


@router.get("")
def get_version():
    """回傳目前後端程式碼的 git commit 資訊，供正式區/測試區版本比對使用。"""
    commit_hash = _run_git(["rev-parse", "HEAD"])
    return {
        "app": "集團 Portal API",
        "git": {
            "commit_hash": commit_hash,
            "commit_short": commit_hash[:7] if commit_hash else None,
            "commit_date": _run_git(["log", "-1", "--format=%cI"]),
            "commit_message": _run_git(["log", "-1", "--format=%s"]),
            "branch": _run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
        },
    }
