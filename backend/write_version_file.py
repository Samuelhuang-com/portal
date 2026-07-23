"""
部署時產生 version_info.json，供 GET /api/v1/version 讀取。

背景：正式區 PortalBackend 用 NSSM 註冊成 Windows 服務執行，服務帳號的 PATH 環境
變數裡沒有 git.exe，導致 version.py 執行期呼叫 `subprocess.run(["git", ...])` 一律
失敗（回傳 None），/api/v1/version 端點全部欄位變成 null，無法用來比對正式區/測試區
版本。

解法：改在部署當下（prod-update.bat，PATH 環境跟手動開的終端機相同、git 可用）執行
本腳本，把 commit 資訊寫成靜態檔案 backend/version_info.json；version.py 改成優先讀
這個檔案，讀不到才 fallback 呼叫 git 指令（本機開發環境行為不受影響）。

用法：cd 到 backend/ 目錄後執行 `py -3.12 write_version_file.py`
（需在 git repo 內執行，會自動往上層找 .git）。
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent
_OUTPUT_PATH = _BACKEND_DIR / "version_info.json"


def _run_git(args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=_BACKEND_DIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip()
        return output or None
    except Exception:
        return None


def main() -> int:
    commit_hash = _run_git(["rev-parse", "HEAD"])
    if not commit_hash:
        print("[ERROR] 無法取得 git commit hash，version_info.json 未寫入。"
              "請確認在 git repo 內執行本腳本，且目前環境有 git 指令可用。")
        return 1

    info = {
        "commit_hash":    commit_hash,
        "commit_short":   commit_hash[:7],
        "commit_date":    _run_git(["log", "-1", "--format=%cI"]),
        "commit_message": _run_git(["log", "-1", "--format=%s"]),
        "branch":         _run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "generated_at":   datetime.now().astimezone().isoformat(),
    }

    _OUTPUT_PATH.write_text(
        json.dumps(info, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[OK] version_info.json 已寫入：{_OUTPUT_PATH}")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
