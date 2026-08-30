#!/usr/bin/env python3
"""
Portal 服務主控台
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
獨立 Python GUI 程式，管理 Portal「開發／測試機」的 Web Server 啟停與健康檢查

2026-07-18：套用 Oracle Hospitality OPERA Fiscal Integration Solution 風格的
淺色版型（Samuel 先用 portal_console_mockup.py 確認方向後套用到本檔）：
• 頂部圖示分頁列（🌐 服務控制 / 📋 Health Check / 🔗 開啟同步工具）
• 每個服務一張卡片：Start/Stop/Restart/Refresh 工具列 + 圓角狀態徽章
  + 內嵌終端機（stdout/stderr 即時顯示，不跳出 cmd 視窗）
• Toast 通知（操作結果，例如「服務已成功啟動。」，3 秒後自動消失）
• 新增「🔗 開啟同步工具」：另開一個獨立視窗執行 sync_tool.py
  （用 CREATE_NO_WINDOW 隱藏 python.exe 的主控台視窗，只留 sync_tool.py
  自己的 tkinter 視窗；兩者是完全獨立的行程，互不影響）

2026-07-18 追加：偵測到 Backend port 由 NSSM 服務（PortalBackend）管理時，
Start/Stop/Restart 自動改用 `net start`/`net stop`，不再對 NSSM 監控的
行程用 taskkill —— 否則 NSSM 的 crash-recovery 會把它當成意外中止並自動
重啟，導致按 Stop 看起來沒有反應。內嵌終端機也會改成 tail NSSM 設定的
stdout/stderr log 檔案。

⚠️ 開發／測試機（沒有 NSSM 服務）沿用原本的 taskkill 方式，行為不變。
   `net start`/`net stop` 操作 Windows 服務需要系統管理員權限，若本工具
   未以系統管理員身分執行，Start/Stop/Restart 會失敗並在 Toast 顯示原因
   （實測會噴「系統發生 5 錯誤，存取被拒」）。正式區請改用
   `run_console_admin.bat` 啟動（見下方「執行方式」），會自動跳 UAC
   確認視窗以系統管理員身分執行；開發／測試機沒有 NSSM 服務，用這支
   啟動器或直接 `python portal_console.py` 皆可，行為相同。

執行方式：
  一般（開發／測試機，或不需要控制 NSSM 服務時）：
    cd portal
    python portal_console.py

  正式區（需要用 Start/Stop/Restart 控制 NSSM 服務 PortalBackend 時）：
    雙擊 run_console_admin.bat（會自動判斷並跳 UAC 視窗要求系統管理員權限）
"""

# ── Python 環境自動修正（必須在所有其他 import 之前）────────────────────────
# 若以系統 Python 執行且 sqlalchemy 不可用，自動找到安裝有套件的 Python
# （venv312 優先）並重新啟動本腳本。做法與 sync_tool.py 相同，維持一致性。
import os as _os
import sys as _sys
import pathlib as _pathlib


def _check_and_relaunch():
    """若 sqlalchemy 不可用，找到正確 Python 後用 os.execv 重新啟動。"""
    try:
        import importlib.util as _ilu
        if _ilu.find_spec("sqlalchemy") is not None:
            return  # 已可用，不需處理
    except Exception:
        pass

    _script = _pathlib.Path(__file__).resolve()
    _portal = _script.parent
    _backend = _portal / "backend"

    _candidates = [
        _backend / "venv312" / "Scripts" / "python.exe",
        _portal / "backend" / "venv312" / "Scripts" / "python.exe",
        _backend / "venv311" / "Scripts" / "python.exe",
        _backend / "venv" / "Scripts" / "python.exe",
        _backend / ".venv" / "Scripts" / "python.exe",
        _pathlib.Path(r"C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe"),
        _pathlib.Path(r"C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe"),
        _pathlib.Path(r"C:\Python312\python.exe"),
        _pathlib.Path(r"C:\Python311\python.exe"),
    ]

    for _vd in sorted(_backend.glob("venv3*"), reverse=True):
        _p = _vd / "Scripts" / "python.exe"
        if _p not in _candidates:
            _candidates.insert(2, _p)

    for _py in _candidates:
        if not _pathlib.Path(_py).exists():
            continue
        import subprocess as _sp
        _r = _sp.run([str(_py), "-c", "import sqlalchemy"], capture_output=True)
        if _r.returncode == 0:
            print(f"[Console] 自動切換 Python：{_py}")
            _os.execv(str(_py), [str(_py)] + _sys.argv)

    print("[Console] ⚠ 找不到含 sqlalchemy 的 Python！請確認 venv312 已建立並安裝套件。")
    print(f"[Console]   目前 Python：{_sys.executable}")


_check_and_relaunch()
# ─────────────────────────────────────────────────────────────────────────────

import json
import logging
import queue
import re
import shutil
import socket
import subprocess
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime, timedelta
from tkinter import scrolledtext

# ── 路徑設定：讓 app.* 可以被 import（供 DB / Ragic 設定讀取用）─────────────
_HERE = _pathlib.Path(__file__).resolve().parent          # portal/ 絕對路徑
_BACKEND = _HERE / "backend"                               # portal/backend/
_FRONTEND = _HERE / "frontend"                              # portal/frontend/
_LOG_DIR = _HERE / "logs"                                   # portal/logs/
_SYNC_TOOL = _HERE / "sync_tool.py"                          # portal/sync_tool.py

# ⚠️ 必須在 import 任何 app.* 之前切換 CWD 到 backend/
#    原因與 sync_tool.py 相同：app.core.config 的 env_file=".env" 是
#    相對於 CWD 的路徑，必須與 uvicorn 啟動位置一致。
_os.chdir(_BACKEND)

# ⚠️ 關掉 SQLAlchemy 的 engine INFO log。
#    後端的 .env 把 echo 打開時，每一次健康檢查（`SHOW data_directory`、
#    `SELECT version()`…）都會把完整 SQL 連同參數印進 Console 視窗，
#    真正的訊息會被沖掉。`pg_verify_live.py` / `pg_fix_sequences.py` 都有設，
#    只有這支漏了。設 WARNING 而不是 ERROR —— 連線警告仍要看得到。
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def _inject_site_packages():
    """注入 venv 的 site-packages 到 sys.path（做法與 sync_tool.py 相同）。"""
    search_roots = [_BACKEND, _BACKEND.parent]
    explicit_names = ("venv312", "venv311", "venv310", "venv", ".venv", "env")
    for root in search_roots:
        for venv_name in explicit_names:
            site_pkgs = root / venv_name / "Lib" / "site-packages"
            if site_pkgs.exists():
                if str(site_pkgs) not in _sys.path:
                    _sys.path.insert(0, str(site_pkgs))
                return str(site_pkgs)
        for venv_dir in sorted(root.glob("venv3*"), reverse=True):
            if not venv_dir.is_dir():
                continue
            site_pkgs = venv_dir / "Lib" / "site-packages"
            if site_pkgs.exists():
                if str(site_pkgs) not in _sys.path:
                    _sys.path.insert(0, str(site_pkgs))
                return str(site_pkgs)

    py_exe = _pathlib.Path(_sys.executable)
    candidate = py_exe.parent.parent / "Lib" / "site-packages"
    if candidate.exists() and (candidate / "sqlalchemy").exists():
        if str(candidate) not in _sys.path:
            _sys.path.insert(0, str(candidate))
        return str(candidate)

    fallbacks = [
        _pathlib.Path(r"C:\Users\admin\AppData\Local\Programs\Python\Python312\Lib\site-packages"),
        _pathlib.Path(r"C:\Users\admin\AppData\Local\Programs\Python\Python311\Lib\site-packages"),
        _pathlib.Path(r"C:\Python312\Lib\site-packages"),
        _pathlib.Path(r"C:\Python311\Lib\site-packages"),
    ]
    for fallback in fallbacks:
        if fallback.exists() and (fallback / "sqlalchemy").exists():
            if str(fallback) not in _sys.path:
                _sys.path.insert(0, str(fallback))
            return str(fallback)
    return None


_venv_path = _inject_site_packages()
if _venv_path:
    print(f"[Console] site-packages 注入：{_venv_path}")
else:
    print(f"[Console] ⚠ 未找到 site-packages，使用系統 Python：{_sys.executable}")

if str(_BACKEND) not in _sys.path:
    _sys.path.insert(0, str(_BACKEND))

_LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── 色系：OPERA 風格淺色版型（沿用 Portal 品牌色 + 既有受保護頁面背景色）───────
C_TAB_BG = "#1B3A5C"         # 品牌主色（分頁列背景）
C_TAB_ACTIVE_FG = "#ffffff"
C_TAB_INACTIVE_FG = "#9db3c9"
C_TAB_UNDERLINE = "#4BA8E8"  # 品牌輔色

C_PAGE_BG = "#f0f4f8"        # 沿用 Portal 網頁版「頁面背景」受保護色碼
C_CARD_BG = "#ffffff"
C_BORDER = "#e2e8f0"
C_TEXT = "#1f2937"
C_TEXT_DIM = "#6b7280"

C_BTN_TEXT = "#374151"

C_RUNNING_BG = "#e6f4ea"
C_RUNNING_FG = "#1e7e34"
C_STOPPED_BG = "#f4e6e6"
C_STOPPED_FG = "#b3261e"

C_OK_TEXT = "#1e7e34"
C_ERR_TEXT = "#b3261e"
C_WARN_TEXT = "#92590b"

C_TOAST_SUCCESS_BG = "#e8f5e9"
C_TOAST_SUCCESS_FG = "#256029"
C_TOAST_SUCCESS_BORDER = "#a5d6a7"
C_TOAST_ERROR_BG = "#fdecea"
C_TOAST_ERROR_FG = "#8c2f26"
C_TOAST_ERROR_BORDER = "#f2b8b0"

# 內嵌終端機維持深色（跟淺色外觀無關，log/終端機慣例上都用深色比較好讀）
C_TERM_BG = "#0c0c0c"
C_TERM_FG = "#d4d4d4"

FONT_NAME = "Microsoft JhengHei UI"

# 2026-07-18 新增：畫面版本顯示（右下角footer）。跟 docs/CHANGELOG.md 用
# 同一組版號，不另外發明一套編號——每次修改 portal_console.py 且有加
# CHANGELOG 條目時，記得同步把這裡改成當次的版本號，兩邊才不會對不上。
CONSOLE_VERSION = "1.96.40"

BACKEND_PORT = 8000


def _detect_frontend_dev_port() -> int:
    """從 frontend/vite.config.ts 讀取實際的開發伺服器 port。

    2026-07-18 修復：先前寫死 5173（Vite 官方預設值），但本專案
    vite.config.ts 的 server.port 實際設定為 5300，導致狀態偵測永遠
    顯示 Stopped、「開啟網頁」按鈕連到錯誤的 port。改為讀取設定檔，
    找不到才 fallback 回 5173。
    """
    try:
        cfg_path = _FRONTEND / "vite.config.ts"
        cfg = cfg_path.read_text(encoding="utf-8")
        # 只在 server: { ... } 區塊內找 port，避免誤抓 preview: { port: 4173 }
        m = re.search(r"server\s*:\s*\{.*?port\s*:\s*(\d+)", cfg, re.S)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return 5173  # fallback：Vite 官方預設值


FRONTEND_PORT = _detect_frontend_dev_port()

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


# ── 共用工具函式 ─────────────────────────────────────────────────────────────
def check_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """檢查某 port 是否有服務在監聽（TCP connect 成功即視為 running）。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def get_pid_by_port(port: int):
    """用 netstat 找出佔用某 port 的 PID（Windows only）。找不到回傳 None。"""
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            text=True,
            encoding="mbcs",
            errors="ignore",
            creationflags=_CREATE_NO_WINDOW,
        )
    except Exception:
        return None
    for line in out.splitlines():
        if f":{port} " in line and "LISTENING" in line:
            parts = line.split()
            if parts:
                try:
                    return int(parts[-1])
                except ValueError:
                    continue
    return None


def kill_pid_tree(pid: int) -> bool:
    """taskkill /F /T：連同子行程一起砍掉（uvicorn --reload 會有 reloader 子行程）。"""
    try:
        r = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            text=True,
        )
        return r.returncode == 0
    except Exception:
        return False


def detect_nssm_service(candidates: list[str]) -> str | None:
    """偵測某個 port 對應的行程是否為 NSSM 管理的 Windows 服務。

    2026-07-18 新增背景：正式區（D:\\portal）用 `nssm install PortalBackend
    ...` 把 uvicorn 包成 Windows 服務常駐（見 deploy.bat）。若沿用開發機
    的 taskkill 方式砍掉這個行程，NSSM 會把它視為「服務意外中止」並自動
    重啟（NSSM 內建 crash-recovery），造成使用者點「Stop」看起來完全沒有
    反應。這裡用 `sc qc <name>` 確認：①服務存在 ②BINARY_PATH_NAME 指向
    nssm.exe（雙重確認是 NSSM 包出來的服務，不是隨便一個同名的一般服務）。

    candidates 依序嘗試，找到第一個「存在且為 NSSM」的服務名稱就回傳；
    在開發／測試機上這些服務通常都不存在，回傳 None，行為完全不變
    （沿用原本的 taskkill 方式）。
    """
    for svc_name in candidates:
        try:
            r = subprocess.run(
                ["sc", "qc", svc_name],
                capture_output=True,
                text=True,
                encoding="mbcs",
                errors="ignore",
                creationflags=_CREATE_NO_WINDOW,
            )
        except Exception:
            continue
        if r.returncode == 0 and "nssm.exe" in r.stdout.lower():
            return svc_name
    return None


# Backend 在正式區用 NSSM 包成的服務名稱（見 deploy.bat 的 `nssm install PortalBackend`）。
# 保留 "portal" 當備用候選名稱，避免未來有人重新用舊名稱安裝服務時偵測不到。
NSSM_BACKEND_CANDIDATES = ["PortalBackend", "portal"]

# NSSM 設定的 stdout/stderr log 檔案（見 deploy.bat 的 `nssm set PortalBackend AppStdout/AppStderr`），
# 用來讓內嵌終端機在「服務由 NSSM 管理」時仍然有真實輸出可看（tail -f 效果）。
NSSM_BACKEND_LOG_FILES = ["portal_stdout.log", "portal_stderr.log"]


# ── 執行環境偵測（2026-08-29）─────────────────────────────────────────────────
# 已知安裝點：D:\portal（舊正式區，見 deploy.bat／prod-update.bat）、
#             C:\portal（新 Server，見 prod-update-newserver.bat）、
#             OneDrive 底下（開發／測試機，也就是這個 repo 本身）。
PROD_INSTALL_ROOTS = [r"D:\portal", r"C:\portal"]

ENV_PROD = "production"
ENV_TEST = "test"
ENV_UNKNOWN = "unknown"
ENV_LABEL = {ENV_PROD: "正式區", ENV_TEST: "測試／開發區", ENV_UNKNOWN: "無法判定"}


def _read_env_file(path: _pathlib.Path) -> dict:
    """讀 KEY=VALUE 形式的 .env。找不到或讀不開就回空 dict（呼叫端自行處理）。"""
    out: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return out


def detect_environment() -> dict:
    """用**三道互相獨立**的依據判斷這台機器是正式區還是測試區。

    ⚠️⚠️ 三道不一致時**不猜**，回傳 conflict=True 讓畫面顯示紅燈要求人工確認。
       這正是這個功能存在的理由：`APP_ENV` 是手動維護的一行字，複製一份程式
       到正式區卻忘了改，判斷就會全錯 —— 而且不會有任何警訊。多一道路徑、
       多一道服務，就是為了讓「忘了改」變成看得見的衝突，而不是靜默的錯誤。

    三道依據：
      ① .env 的 APP_ENV        production → 正式；development/其他 → 測試
      ② 安裝路徑               在 PROD_INSTALL_ROOTS 底下 → 正式；
                               路徑含 OneDrive → 測試（雲端同步資料夾不會是正式區）
      ③ NSSM 服務是否存在      存在 → 正式

    ⚠️ 第 ③ 道是**單向證據**：服務存在幾乎必然是正式區，但**服務不存在不能反推
       成測試區** —— 新 Server（C:\\portal）的 prod-update-newserver.bat 是用
       taskkill + uvicorn 直接跑，根本沒有裝 NSSM 服務。所以這道只投「正式」票，
       不存在時棄權（回 None），否則新 Server 會被永遠誤判成測試區。

    回傳 dict：
        env       最終判定（ENV_PROD / ENV_TEST / ENV_UNKNOWN）
        conflict  三道是否互相矛盾
        signals   [(名稱, 投票結果 or None, 說明文字), ...]
    """
    signals = []

    # ① .env 的 APP_ENV
    env_file = _BACKEND / ".env"
    cfg = _read_env_file(env_file)
    app_env = (cfg.get("APP_ENV") or "").strip().lower()
    if not app_env:
        vote1, desc1 = None, "APP_ENV 未設定"
    elif app_env == "production":
        vote1, desc1 = ENV_PROD, "APP_ENV=production"
    else:
        vote1, desc1 = ENV_TEST, f"APP_ENV={app_env}"
    signals.append(("設定檔（.env）", vote1, desc1))

    # ② 安裝路徑
    here = str(_HERE)
    here_l = here.lower()
    for root in PROD_INSTALL_ROOTS:
        if here_l == root.lower() or here_l.startswith(root.lower() + _os.sep):
            vote2, desc2 = ENV_PROD, f"安裝於 {here}（已知正式區路徑）"
            break
    else:
        if "onedrive" in here_l:
            vote2, desc2 = ENV_TEST, f"安裝於 {here}（OneDrive 同步資料夾）"
        else:
            vote2, desc2 = None, f"安裝於 {here}（不在已知清單中）"
    signals.append(("安裝路徑", vote2, desc2))

    # ③ NSSM 服務（單向證據：存在才投票，不存在棄權）
    svc = detect_nssm_service(NSSM_BACKEND_CANDIDATES)
    if svc:
        vote3, desc3 = ENV_PROD, f"NSSM 服務 {svc} 存在"
    else:
        vote3, desc3 = None, "沒有 NSSM 服務（新 Server 用 uvicorn 直跑，故不列入判定）"
    signals.append(("Windows 服務", vote3, desc3))

    votes = {v for _, v, _ in signals if v is not None}
    conflict = len(votes) > 1
    if conflict:
        env = ENV_UNKNOWN
    elif votes:
        env = votes.pop()
    else:
        env = ENV_UNKNOWN

    return {"env": env, "conflict": conflict, "signals": signals}


def suggest_backup_dir() -> str:
    """依安裝所在磁碟建議備份目錄：`<安裝磁碟>\\portal_backup\\pg`。

    ⚠️ 這只是**建議值**，不會寫進 .env（見 CLAUDE.md §5：不可自行修改 .env）。
       實際採用的路徑一律以 .env 的 PG_BACKUP_DIR 為準；沒設定時 pg_backup.py
       會用它自己的 DEFAULT_DIR（D:\\portal_backup\\pg）。
    ⚠️ 這個規則會讓備份與資料庫落在**同一顆磁碟**，而 pg_backup.py 檔頭明講
       「備份放在同一台機器上不是真備份」。所以畫面上偵測到同磁碟時要提示。
    """
    drive = _os.path.splitdrive(str(_HERE))[0] or "C:"
    return _os.path.join(drive + _os.sep, "portal_backup", "pg")


def rounded_rect(canvas: tk.Canvas, x1, y1, x2, y2, r, **kwargs):
    """在 Canvas 上畫一個圓角矩形（tkinter 沒有原生圓角圖形，用弧形+矩形拼出來）。"""
    canvas.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r, start=90, extent=90, style=tk.PIESLICE, **kwargs)
    canvas.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r, start=0, extent=90, style=tk.PIESLICE, **kwargs)
    canvas.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2, start=180, extent=90, style=tk.PIESLICE, **kwargs)
    canvas.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2, start=270, extent=90, style=tk.PIESLICE, **kwargs)
    canvas.create_rectangle(x1 + r, y1, x2 - r, y2, **kwargs)
    canvas.create_rectangle(x1, y1 + r, x2, y2 - r, **kwargs)


class StatusPill(tk.Canvas):
    """圓角狀態徽章（Running / Stopped），仿 OPERA 右上角「Stopped」灰底徽章。"""

    def __init__(self, parent, width=100, height=26):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0)
        # 注意：不能叫 self._w / self._h —— tkinter.Widget 內部已經用 self._w
        # 存放這個元件自己的 Tcl widget path，蓋掉會導致之後所有畫布操作
        # 噴出 "invalid command name ..." 這種難以理解的錯誤（mockup 階段踩過雷）。
        self._pill_w, self._pill_h = width, height
        self.set_state(False, None)

    def set_state(self, running: bool, pid):
        self.delete("all")
        bg = C_RUNNING_BG if running else C_STOPPED_BG
        fg = C_RUNNING_FG if running else C_STOPPED_FG
        if running:
            text = "● Running" + (f" ({pid})" if pid else "")
        else:
            text = "● Stopped"
        rounded_rect(self, 1, 1, self._pill_w - 1, self._pill_h - 1,
                     r=(self._pill_h - 2) // 2, fill=bg, outline=bg)
        self.create_text(
            self._pill_w / 2, self._pill_h / 2, text=text, fill=fg,
            font=(FONT_NAME, 9, "bold"),
        )


class Toast(tk.Frame):
    """暫時性通知條（仿 OPERA 底部「Service was successfully stopped.」提示）。"""

    def __init__(self, parent):
        super().__init__(parent, bg=C_TOAST_SUCCESS_BG, highlightbackground=C_TOAST_SUCCESS_BORDER,
                          highlightthickness=1, bd=0)
        self._label = tk.Label(
            self, bg=C_TOAST_SUCCESS_BG, fg=C_TOAST_SUCCESS_FG,
            font=(FONT_NAME, 10), padx=14, pady=10,
        )
        self._label.pack()
        self._hide_job = None

    def show(self, message: str, kind: str = "success", ms: int = 3500):
        if kind == "error":
            bg, fg, border, icon = C_TOAST_ERROR_BG, C_TOAST_ERROR_FG, C_TOAST_ERROR_BORDER, "⚠"
        else:
            bg, fg, border, icon = C_TOAST_SUCCESS_BG, C_TOAST_SUCCESS_FG, C_TOAST_SUCCESS_BORDER, "✅"
        self.configure(bg=bg, highlightbackground=border)
        self._label.configure(bg=bg, fg=fg, text=f"{icon}  {message}")
        self.place(relx=0.98, rely=0.96, anchor="se")
        self.lift()
        if self._hide_job:
            self.after_cancel(self._hide_job)
        self._hide_job = self.after(ms, self.place_forget)


# ── 主視窗 ───────────────────────────────────────────────────────────────────
class PortalConsole(tk.Tk):
    TABS = [
        ("🌐", "服務控制"),
        ("📋", "Health Check"),
        ("💾", "備份"),
    ]

    # 備份分頁的內嵌終端機在 _log_queues / _log_widgets 裡的 key。
    # 這兩個 dict 原本用 port（int）當 key，但迴圈只是 .get(key)，用字串沒問題，
    # 而且刻意不用假的 port 數字——備份不是一個服務，硬塞 port 會誤導。
    BACKUP_LOG_KEY = "backup"

    def __init__(self):
        super().__init__()
        self.title("Portal 服務主控台（開發／測試機）")
        self.geometry("1000x860")
        self.configure(bg=C_PAGE_BG)
        self.minsize(920, 720)

        # 內嵌終端機狀態：port → Popen / Queue[str] / Text widget
        # （只有透過本程式啟動的服務才會有對應項目；外部已啟動的服務仍可用
        #  netstat 偵測狀態／停止，但沒有即時輸出可看）
        self._processes: dict[int, subprocess.Popen] = {}
        self._log_queues: dict[int, "queue.Queue[str]"] = {}
        self._log_widgets: dict[int, tk.Text] = {}
        self._sync_tool_proc: subprocess.Popen | None = None
        self._frontend_build_proc: subprocess.Popen | None = None

        # 2026-07-18 新增：偵測 Backend port 是否由 NSSM 服務管理（正式區）。
        # 只做一次（啟動時，`sc qc` 一次頂多幾百毫秒），偵測不到就是 None，
        # 開發／測試機行為完全不變。目前只有 Backend 有對應的 NSSM 服務
        # （見 deploy.bat，Frontend 在正式區是由 Backend 一併輸出 dist 靜態檔，
        # 沒有獨立服務）。
        self._nssm_service: dict[int, str | None] = {
            BACKEND_PORT: detect_nssm_service(NSSM_BACKEND_CANDIDATES),
        }

        self._active_tab = 0
        self._build_tab_bar()
        self._build_footer()
        self._build_content_area()

        self._page_service = tk.Frame(self._content, bg=C_PAGE_BG)
        self._page_health = tk.Frame(self._content, bg=C_PAGE_BG)
        self._page_backup = tk.Frame(self._content, bg=C_PAGE_BG)
        # 順序必須與 TABS 一致（_switch_tab 直接用索引取用）
        self._pages = [self._page_service, self._page_health, self._page_backup]
        self._build_service_page(self._page_service)
        self._build_health_page(self._page_health)
        self._build_backup_page(self._page_backup)
        self._page_service.pack(fill=tk.BOTH, expand=True)

        self._toast = Toast(self)

        # 每 3 秒自動刷新服務控制頁的 port 狀態（輕量，不含 DB/Ragic）
        self._refresh_service_status()
        # 每 150ms 把內嵌終端機的輸出佇列搬到畫面上
        self._drain_log_queues()

    # ── 分頁列（圖示＋文字，仿 Adapter / BE Gateway / Configuration…）──────────
    # 前兩個是真正的頁面切換分頁；「🔗 開啟同步工具」是動作項目（仿 OPERA
    # 的「Check for Updates」——點下去是觸發動作，不是切換到另一個設定頁）。
    def _build_tab_bar(self):
        bar = tk.Frame(self, bg=C_TAB_BG, height=54)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)

        self._tab_widgets = []
        for i, (icon, label) in enumerate(self.TABS):
            cell = tk.Frame(bar, bg=C_TAB_BG)
            cell.pack(side=tk.LEFT, padx=(20 if i == 0 else 0, 0))

            btn = tk.Label(
                cell, text=f"{icon}  {label}", bg=C_TAB_BG,
                fg=C_TAB_ACTIVE_FG if i == 0 else C_TAB_INACTIVE_FG,
                font=(FONT_NAME, 11, "bold" if i == 0 else "normal"),
                padx=16, pady=14, cursor="hand2",
            )
            btn.pack(side=tk.TOP)
            underline = tk.Frame(cell, bg=C_TAB_UNDERLINE if i == 0 else C_TAB_BG, height=3)
            underline.pack(fill=tk.X, side=tk.BOTTOM)

            btn.bind("<Button-1>", lambda e, idx=i: self._switch_tab(idx))
            self._tab_widgets.append((btn, underline))

        action_cell = tk.Frame(bar, bg=C_TAB_BG)
        action_cell.pack(side=tk.RIGHT, padx=20)
        sync_lbl = tk.Label(
            action_cell, text="🔗  開啟同步工具", bg=C_TAB_BG, fg=C_TAB_INACTIVE_FG,
            font=(FONT_NAME, 11), padx=16, pady=14, cursor="hand2",
        )
        sync_lbl.pack(side=tk.TOP)
        sync_lbl.bind("<Button-1>", lambda e: self._launch_sync_tool())

    def _switch_tab(self, idx):
        self._active_tab = idx
        for i, (btn, underline) in enumerate(self._tab_widgets):
            active = i == idx
            btn.config(
                fg=C_TAB_ACTIVE_FG if active else C_TAB_INACTIVE_FG,
                font=(FONT_NAME, 11, "bold" if active else "normal"),
            )
            underline.config(bg=C_TAB_UNDERLINE if active else C_TAB_BG)

        for i, page in enumerate(self._pages):
            if i == idx:
                page.pack(fill=tk.BOTH, expand=True)
            else:
                page.pack_forget()

    # ── 內容區容器 ───────────────────────────────────────────────────────────
    def _build_content_area(self):
        self._content = tk.Frame(self, bg=C_PAGE_BG)
        self._content.pack(fill=tk.BOTH, expand=True)

    # ── 底部版本列（幫忙確認目前這台機器跑的是不是最新版）───────────────────
    def _build_footer(self):
        footer = tk.Frame(self, bg=C_PAGE_BG, height=22)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        tk.Frame(footer, bg=C_BORDER, height=1).pack(fill=tk.X, side=tk.TOP)
        tk.Label(
            footer, text=f"Portal 服務主控台　v{CONSOLE_VERSION}",
            bg=C_PAGE_BG, fg=C_TEXT_DIM, font=(FONT_NAME, 8),
        ).pack(side=tk.RIGHT, padx=12)

    # ── 分頁 1：服務控制（每個服務一張卡片：工具列 + 狀態徽章 + 內嵌終端機）────
    def _build_service_page(self, parent: tk.Frame):
        self._svc_widgets = {}

        wrap = tk.Frame(parent, bg=C_PAGE_BG)
        wrap.pack(fill=tk.BOTH, expand=True, padx=24, pady=(18, 8))

        tk.Label(
            wrap, text="服務控制", bg=C_PAGE_BG, fg=C_TEXT,
            font=(FONT_NAME, 18, "bold"),
        ).pack(anchor="w", pady=(0, 12))

        for name, port, dev_cmd, cwd, browser_url in (
            ("Backend (uvicorn)", BACKEND_PORT,
             "uvicorn app.main:app --reload --host 127.0.0.1 --port 8000",
             _BACKEND, f"http://127.0.0.1:{BACKEND_PORT}/api/docs"),
            ("Frontend (vite dev)", FRONTEND_PORT,
             "npm run dev",
             _FRONTEND, f"http://127.0.0.1:{FRONTEND_PORT}"),
        ):
            card = tk.Frame(wrap, bg=C_CARD_BG, highlightbackground=C_BORDER, highlightthickness=1)
            card.pack(fill=tk.BOTH, expand=True, pady=(0, 16))

            header = tk.Frame(card, bg=C_CARD_BG)
            header.pack(fill=tk.X, padx=16, pady=(14, 4))
            tk.Label(
                header, text=name, bg=C_CARD_BG, fg=C_TEXT,
                font=(FONT_NAME, 13, "bold"),
            ).pack(side=tk.LEFT)
            detail_lbl = tk.Label(
                header, text=self._detail_text(port), bg=C_CARD_BG, fg=C_TEXT_DIM,
                font=(FONT_NAME, 9),
            )
            detail_lbl.pack(side=tk.LEFT, padx=12)

            pill = StatusPill(header)
            pill.pack(side=tk.RIGHT)

            toolbar = tk.Frame(card, bg=C_CARD_BG, highlightbackground=C_BORDER, highlightthickness=1)
            toolbar.pack(fill=tk.X, padx=16, pady=(4, 10))

            def _toolbtn(parent_, icon, text, cmd):
                lbl = tk.Label(
                    parent_, text=f"{icon}  {text}", bg=C_CARD_BG, fg=C_BTN_TEXT,
                    font=(FONT_NAME, 10), padx=10, pady=8, cursor="hand2",
                )
                lbl.pack(side=tk.LEFT)
                lbl.bind("<Button-1>", lambda e: cmd())
                return lbl

            _toolbtn(toolbar, "▶", "Start", lambda p=port, c=dev_cmd, d=cwd, n=name: self._start(n, p, c, d))
            _toolbtn(toolbar, "■", "Stop", lambda p=port, n=name: self._stop(n, p))
            _toolbtn(toolbar, "↻", "Restart", lambda p=port, c=dev_cmd, d=cwd, n=name: self._restart(n, p, c, d))
            tk.Frame(toolbar, bg=C_BORDER, width=1, height=18).pack(side=tk.LEFT, padx=8, pady=6)
            _toolbtn(toolbar, "🔄", "Refresh", lambda p=port, n=name: self._refresh_one(n, p))
            _toolbtn(toolbar, "🌐", "開啟網頁", lambda u=browser_url: webbrowser.open(u))
            if port == FRONTEND_PORT:
                tk.Frame(toolbar, bg=C_BORDER, width=1, height=18).pack(side=tk.LEFT, padx=8, pady=6)
                _toolbtn(toolbar, "🔨", "重建正式區前端", lambda: self._build_frontend())

            tk.Label(
                card, text="即時輸出", bg=C_CARD_BG, fg=C_TEXT_DIM,
                font=(FONT_NAME, 9), anchor="w",
            ).pack(fill=tk.X, padx=16)

            log_box = scrolledtext.ScrolledText(
                card, height=8, bg=C_TERM_BG, fg=C_TERM_FG, insertbackground=C_TERM_FG,
                font=("Consolas", 9), wrap=tk.NONE, state=tk.DISABLED, borderwidth=0,
            )
            log_box.pack(fill=tk.BOTH, expand=True, padx=16, pady=(2, 6))
            svc_name = self._nssm_service.get(port)
            if svc_name:
                log_box.insert(
                    tk.END,
                    f"（此服務由 Windows 服務「{svc_name}」管理，以下即時顯示 NSSM log 檔案內容）\n",
                )
            else:
                log_box.insert(tk.END, "（尚未啟動，或此服務是從本程式外部啟動，沒有輸出可顯示）\n")
            log_box.configure(state=tk.DISABLED)

            clear_row = tk.Frame(card, bg=C_CARD_BG)
            clear_row.pack(fill=tk.X, padx=16, pady=(0, 12))
            clear_lbl = tk.Label(
                clear_row, text="清除畫面", bg=C_CARD_BG, fg=C_TEXT_DIM,
                font=(FONT_NAME, 8), cursor="hand2",
            )
            clear_lbl.pack(side=tk.RIGHT)
            clear_lbl.bind("<Button-1>", lambda e, w=log_box: self._clear_log_box(w))

            self._svc_widgets[port] = {"pill": pill, "detail": detail_lbl}
            self._log_queues[port] = queue.Queue()
            self._log_widgets[port] = log_box

            if svc_name:
                self._start_nssm_log_tail(port)

    def _detail_text(self, port: int) -> str:
        """卡片副標題文字：Port 號 + （若由 NSSM 服務管理）服務名稱標註。"""
        svc_name = self._nssm_service.get(port)
        return f"Port {port}" + (f"（Windows 服務：{svc_name}）" if svc_name else "")

    def _clear_log_box(self, widget: tk.Text):
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.configure(state=tk.DISABLED)

    def _run_bg(self, work, on_done=None):
        """在背景執行緒跑 work()，完成後把結果丟回 Tkinter 主執行緒執行 on_done()。

        netstat / taskkill 這類 subprocess 呼叫在部分機器上可能要數百毫秒
        甚至更久，直接在主執行緒（含每 3 秒的排程刷新）呼叫會讓整個視窗
        定期卡頓、按鈕沒反應，一律丟背景執行緒執行。
        """
        def _worker():
            result = work()
            if on_done is not None:
                # ⚠️ 走 _safe_after 不走 self.after：使用者按下按鈕後、work()
                #    還沒跑完就把視窗關掉，這裡會拋
                #    RuntimeError: main thread is not in main loop
                #    （與 [1.96.44] 健康檢查那個是同一類，只是觸發點不同）。
                self._safe_after(0, lambda: on_done(result))
        threading.Thread(target=_worker, daemon=True).start()

    # ── NSSM 服務控制（net start / net stop）─────────────────────────────────
    # 2026-07-18 新增背景：正式區 Backend 是 NSSM 包出來的 Windows 服務
    # （PortalBackend）。若沿用 taskkill 砍掉底下的 uvicorn 行程，NSSM 會
    # 判定成「服務意外中止」並自動重啟（crash-recovery），導致按下 Stop
    # 看起來完全沒有效果 —— 這正是 Samuel 實際遇到的狀況。改為呼叫
    # `net stop`/`net start`，讓 SCM（服務控制管理員）用正常流程停止／
    # 啟動服務，NSSM 就不會誤判成當機。
    #
    # `net start`/`net stop` 操作 Windows 服務需要系統管理員權限；若本程式
    # 沒有以系統管理員身分執行，這裡會失敗並回傳非 0，直接把 stdout/stderr
    # 顯示在 Toast 裡讓使用者知道原因（例如「Access is denied」）。
    def _nssm_net_cmd(self, action: str, svc_name: str):
        """執行 `net start`/`net stop <svc_name>`，回傳 (成功與否, 輸出訊息)。"""
        try:
            r = subprocess.run(
                ["net", action, svc_name],
                capture_output=True,
                text=True,
                encoding="mbcs",
                errors="ignore",
                creationflags=_CREATE_NO_WINDOW,
            )
            msg = (r.stdout + r.stderr).strip()
            return r.returncode == 0, msg
        except Exception as e:
            return False, str(e)

    def _start(self, name, port, cmd, cwd):
        svc_name = self._nssm_service.get(port)
        if svc_name:
            def work():
                return self._nssm_net_cmd("start", svc_name)

            def done(result):
                ok, msg = result
                if ok:
                    self._toast.show(f"{name}（Windows 服務 {svc_name}）已成功啟動。")
                else:
                    self._toast.show(f"啟動失敗，可能需要以系統管理員身分執行本工具：{msg[:100]}", kind="error")
                    self._log_queues.setdefault(port, queue.Queue()).put(f"[Console] net start 失敗：{msg}")

            self._run_bg(work, done)
            return

        def work():
            return get_pid_by_port(port)

        def done(pid):
            if pid:
                self._toast.show(f"{name} 已在執行中（PID {pid}），略過啟動", kind="error")
                return
            new_pid = self._spawn_embedded(port, cmd, cwd)
            self._toast.show(f"{name} 服務已成功啟動。")

        self._run_bg(work, done)

    def _stop(self, name, port):
        svc_name = self._nssm_service.get(port)
        if svc_name:
            def work():
                return self._nssm_net_cmd("stop", svc_name)

            def done(result):
                ok, msg = result
                if ok:
                    self._toast.show(f"{name}（Windows 服務 {svc_name}）已成功停止。")
                else:
                    self._toast.show(f"停止失敗，可能需要以系統管理員身分執行本工具：{msg[:100]}", kind="error")
                    self._log_queues.setdefault(port, queue.Queue()).put(f"[Console] net stop 失敗：{msg}")

            self._run_bg(work, done)
            return

        tracked = self._processes.get(port)

        def work():
            # 優先用本程式自己記錄的 Popen（較準確）；沒有才 fallback 到 netstat 找 PID
            # （服務可能是外部啟動、或本程式重啟過導致記錄遺失）。
            if tracked is not None and tracked.poll() is None:
                ok = kill_pid_tree(tracked.pid)
                return tracked.pid, ok, True
            pid = get_pid_by_port(port)
            if not pid:
                return None, None, False
            ok = kill_pid_tree(pid)
            return pid, ok, False

        def done(result):
            pid, ok, was_tracked = result
            if pid is None:
                self._toast.show(f"{name} 目前未在執行", kind="error")
            elif ok:
                self._toast.show(f"{name} 服務已成功停止。")
            else:
                self._toast.show(f"{name} 停止失敗（PID {pid}）", kind="error")
            if was_tracked:
                self._processes.pop(port, None)

        self._run_bg(work, done)

    def _restart(self, name, port, cmd, cwd):
        svc_name = self._nssm_service.get(port)
        if svc_name:
            def work():
                self._nssm_net_cmd("stop", svc_name)
                return self._nssm_net_cmd("start", svc_name)

            def done(result):
                ok, msg = result
                if ok:
                    self._toast.show(f"{name}（Windows 服務 {svc_name}）已重新啟動。")
                else:
                    self._toast.show(f"重啟失敗，可能需要以系統管理員身分執行本工具：{msg[:100]}", kind="error")
                    self._log_queues.setdefault(port, queue.Queue()).put(f"[Console] net stop/start 失敗：{msg}")

            self._run_bg(work, done)
            return

        tracked = self._processes.get(port)

        def work():
            if tracked is not None and tracked.poll() is None:
                kill_pid_tree(tracked.pid)
                return tracked.pid
            pid = get_pid_by_port(port)
            if pid:
                kill_pid_tree(pid)
            return pid

        def done(pid):
            self._processes.pop(port, None)
            self._toast.show(f"{name} 服務已重新啟動。")
            self.after(2000 if pid else 0, lambda: self._spawn_embedded(port, cmd, cwd))

        self._run_bg(work, done)

    def _refresh_one(self, name, port):
        def work():
            running = check_port("127.0.0.1", port)
            pid = get_pid_by_port(port) if running else None
            return running, pid

        def done(result):
            running, pid = result
            widgets = self._svc_widgets[port]
            widgets["pill"].set_state(running, pid)
            widgets["detail"].config(text=self._detail_text(port))
            self._toast.show(f"{name} 狀態已重新整理。")

        self._run_bg(work, done)

    # ── NSSM 服務 log 檔案 tail（讓內嵌終端機在正式區也有真實輸出可看）─────────
    def _start_nssm_log_tail(self, port: int):
        """啟動背景執行緒，持續把 NSSM 設定的 stdout/stderr log 檔案新增內容
        （見 deploy.bat 的 `nssm set PortalBackend AppStdout/AppStderr`）
        接進內嵌終端機，效果類似 `tail -f`。只在偵測到 NSSM 服務時呼叫。
        """
        for filename in NSSM_BACKEND_LOG_FILES:
            path = _LOG_DIR / filename
            threading.Thread(target=self._tail_file, args=(path, port), daemon=True).start()

    def _tail_file(self, path: _pathlib.Path, port: int):
        """背景執行緒：從檔尾開始，持續讀取檔案新增的內容並丟進 log 佇列。

        只看「執行本程式之後新增的內容」（seek 到檔尾），避免一次把整份
        歷史 log（可能很大）灌進畫面；檔案還不存在時（例如剛裝好服務、
        NSSM 還沒寫過任何一行）先提示一次，之後每秒重新檢查一次。
        """
        q = self._log_queues.setdefault(port, queue.Queue())
        try:
            waited_notice = False
            while not path.exists():
                if not waited_notice:
                    q.put(f"[Console] 等待 log 檔案出現：{path}")
                    waited_notice = True
                time.sleep(2)
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, _os.SEEK_END)
                while True:
                    line = f.readline()
                    if line:
                        q.put(_ANSI_ESCAPE_RE.sub("", line.rstrip("\n")))
                    else:
                        time.sleep(1)
        except Exception as e:
            q.put(f"[Console] 讀取 log 檔案時發生錯誤（{path}）：{e}")

    # ── 內嵌終端機 ───────────────────────────────────────────────────────────
    def _spawn_embedded(self, port, cmd, cwd):
        """啟動指令並把 stdout/stderr 導到內嵌 Log 區，不再跳出獨立 cmd 視窗。"""
        log_box = self._log_widgets.get(port)
        if log_box is not None:
            log_box.configure(state=tk.NORMAL)
            log_box.delete("1.0", tk.END)
            log_box.insert(tk.END, f"[Console] 啟動指令：{cmd}\n")
            log_box.configure(state=tk.DISABLED)

        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=_CREATE_NO_WINDOW,
        )
        self._processes[port] = proc
        q = self._log_queues.setdefault(port, queue.Queue())
        q.put(f"[Console] PID {proc.pid}")
        threading.Thread(target=self._pump_output, args=(proc, port), daemon=True).start()
        return proc.pid

    def _pump_output(self, proc, port):
        """背景執行緒：持續讀取子行程 stdout，逐行丟進佇列給主執行緒顯示。"""
        q = self._log_queues.setdefault(port, queue.Queue())
        try:
            for line in proc.stdout:
                q.put(_ANSI_ESCAPE_RE.sub("", line.rstrip("\n")))
        except Exception as e:
            q.put(f"[Console] 讀取輸出時發生錯誤：{e}")
        finally:
            code = proc.poll()
            q.put(f"[Console] 行程已結束（exit code {code}）")

    def _drain_log_queues(self):
        """每 150ms 執行一次：把各服務累積的輸出搬到對應的 Text widget。"""
        for port, q in self._log_queues.items():
            widget = self._log_widgets.get(port)
            if widget is None:
                continue
            got_any = False
            while True:
                try:
                    line = q.get_nowait()
                except queue.Empty:
                    break
                widget.configure(state=tk.NORMAL)
                widget.insert(tk.END, line + "\n")
                got_any = True
            if got_any:
                self._trim_log_widget(widget)
                widget.see(tk.END)
                widget.configure(state=tk.DISABLED)
        self.after(150, self._drain_log_queues)

    @staticmethod
    def _trim_log_widget(widget: tk.Text, max_lines: int = 2000):
        """限制內嵌終端機最多保留的行數，避免長時間執行後畫面/記憶體愈用愈多。"""
        line_count = int(widget.index("end-1c").split(".")[0])
        if line_count > max_lines:
            widget.delete("1.0", f"{line_count - max_lines}.0")

    def _refresh_service_status(self):
        # 若上一輪背景檢查還沒跑完就跳過本次排程，避免執行緒愈堆愈多
        if getattr(self, "_status_check_running", False):
            self.after(3000, self._refresh_service_status)
            return
        self._status_check_running = True

        ports = list(self._svc_widgets.keys())

        def work():
            results = {}
            for port in ports:
                running = check_port("127.0.0.1", port)
                pid = get_pid_by_port(port) if running else None
                results[port] = (running, pid)
            return results

        def done(results):
            for port, (running, pid) in results.items():
                widgets = self._svc_widgets[port]
                widgets["pill"].set_state(running, pid)
                widgets["detail"].config(text=self._detail_text(port))
            self._status_check_running = False
            self.after(3000, self._refresh_service_status)

        self._run_bg(work, done)

    # ── 開啟同步工具（另開視窗執行 sync_tool.py）───────────────────────────────
    def _launch_sync_tool(self):
        if self._sync_tool_proc is not None and self._sync_tool_proc.poll() is None:
            self._toast.show("同步工具視窗已經開著了", kind="error")
            return
        if not _SYNC_TOOL.exists():
            self._toast.show(f"找不到 sync_tool.py（預期路徑：{_SYNC_TOOL}）", kind="error")
            return
        try:
            # CREATE_NO_WINDOW：隱藏 python.exe 本身的主控台視窗，
            # sync_tool.py 的 tkinter 視窗不受影響，一樣會正常顯示。
            self._sync_tool_proc = subprocess.Popen(
                [_sys.executable, str(_SYNC_TOOL)],
                cwd=str(_HERE),
                creationflags=_CREATE_NO_WINDOW,
            )
            self._toast.show("已開啟同步工具視窗。")
        except Exception as e:
            self._toast.show(f"開啟同步工具失敗：{e}", kind="error")

    # ── 重建正式區前端（npm install && npm run build）───────────────────────
    def _build_frontend(self):
        """執行 `npm install && npm run build`，重建 frontend/dist 靜態檔。

        2026-07-18 新增背景：正式區前端不是跑 vite dev server，而是由
        Backend 直接輸出建置好的 dist 靜態檔（見 deploy.bat／
        prod-update.bat Step 4）；prod-update.bat 本來就有這個步驟，但要
        連著 git pull／pip install／DB index 一起跑一整套。這裡讓
        portal_console.py 也能單獨觸發重建（例如只改了前端程式碼、
        不想跑整套 prod-update.bat），輸出直接接到 Frontend 卡片的內嵌
        終端機，跟其他服務操作維持一致的體驗。
        """
        if self._frontend_build_proc is not None and self._frontend_build_proc.poll() is None:
            self._toast.show("前端建置已在執行中，請稍候", kind="error")
            return

        port = FRONTEND_PORT
        q = self._log_queues.setdefault(port, queue.Queue())
        log_box = self._log_widgets.get(port)
        if log_box is not None:
            log_box.configure(state=tk.NORMAL)
            log_box.delete("1.0", tk.END)
            log_box.configure(state=tk.DISABLED)
        q.put(f"[Console] 開始建置：npm install && npm run build（cwd={_FRONTEND}）")
        self._toast.show("開始建置正式區前端…")

        def work():
            try:
                proc = subprocess.Popen(
                    "npm install && npm run build",
                    cwd=str(_FRONTEND),
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=_CREATE_NO_WINDOW,
                )
            except Exception as e:
                q.put(f"[Console] 啟動建置指令失敗：{e}")
                return None
            self._frontend_build_proc = proc
            q.put(f"[Console] PID {proc.pid}")
            for line in proc.stdout:
                q.put(_ANSI_ESCAPE_RE.sub("", line.rstrip("\n")))
            code = proc.poll()
            q.put(f"[Console] 建置行程已結束（exit code {code}）")
            return code

        def done(code):
            if code == 0:
                self._toast.show("正式區前端建置完成（npm run build 成功）。")
            elif code is None:
                self._toast.show("建置未能啟動，請查看內嵌終端機訊息", kind="error")
            else:
                self._toast.show(f"前端建置失敗（exit code {code}），請查看內嵌終端機訊息", kind="error")

        self._run_bg(work, done)

    # ── 分頁 2：Health Check ─────────────────────────────────────────────────
    # 2026-08-29 擴充：原本只有 6 列（port ×2、DB 連線、Ragic、排程、手動同步），
    # 都只回答「連得上嗎」。切到 PostgreSQL 之後，真正會咬人的問題是
    # 「連上的是**哪一個**資料庫」與「備份還活著嗎」——見 pg_backup.py 檔頭
    # 那段警告：切到 PG 之後，複製 .db 的舊備份會**靜默**變成備份一份凍結在
    # 過去的資料。所以這裡把檢查項目分成四區、共 13 列。
    HEALTH_SECTIONS = [
        ("服務與環境", [
            ("environment", "執行環境（正式／測試）"),
            ("port_backend", f"Backend Port ({BACKEND_PORT})"),
            ("port_frontend", f"Frontend Port ({FRONTEND_PORT})"),
            ("backend_version", "後端版本（commit）"),
            ("runtime", "Console 執行環境"),
        ]),
        ("資料庫", [
            ("db", "資料庫連線"),
            ("db_version", "資料庫版本"),
            ("db_size", "資料庫大小 / 筆數"),
            ("disk", "磁碟剩餘空間"),
        ]),
        ("同步", [
            ("ragic", "Ragic API 連通性"),
            ("scheduler", "自動排程狀態"),
            ("sync_modules", "各模組最後同步"),
            ("last_manual_sync", "最近一次手動同步"),
        ]),
        ("備份", [
            ("backup", "最後備份"),
            ("verify_restore", "最後還原驗證"),
        ]),
    ]

    # 慢檢查（跑在背景執行緒）：key → 方法名稱。順序即畫面由上而下的更新順序。
    _SLOW_CHECKS = [
        ("environment", "_check_environment"),
        ("backend_version", "_check_backend_version"),
        ("runtime", "_check_runtime"),
        ("db", "_check_db"),
        ("db_version", "_check_db_version"),
        ("db_size", "_check_db_size"),
        ("disk", "_check_disk"),
        ("ragic", "_check_ragic"),
        ("scheduler", "_check_scheduler"),
        ("sync_modules", "_check_sync_modules"),
        ("last_manual_sync", "_check_last_manual_sync"),
        ("backup", "_check_backup"),
        ("verify_restore", "_check_verify_restore"),
    ]

    # 狀態 → （符號, 顏色）。"info" 是中性事實（不是好也不是壞）。
    _HEALTH_STYLE = {
        "ok":   ("✓ ", C_OK_TEXT),
        "warn": ("⚠ ", C_WARN_TEXT),
        "err":  ("✕ ", C_ERR_TEXT),
        "info": ("",   C_TEXT_DIM),
    }

    def _build_health_page(self, parent: tk.Frame):
        wrap = tk.Frame(parent, bg=C_PAGE_BG)
        wrap.pack(fill=tk.BOTH, expand=True, padx=24, pady=(18, 8))

        top = tk.Frame(wrap, bg=C_PAGE_BG)
        top.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            top, text="Health Check", bg=C_PAGE_BG, fg=C_TEXT,
            font=(FONT_NAME, 18, "bold"),
        ).pack(side=tk.LEFT)

        refresh_lbl = tk.Label(
            top, text="🔄  重新檢查全部", bg=C_PAGE_BG, fg=C_TAB_BG,
            font=(FONT_NAME, 10, "bold"), cursor="hand2",
        )
        refresh_lbl.pack(side=tk.RIGHT)
        refresh_lbl.bind("<Button-1>", lambda e: self._run_health_checks())
        self._btn_check_all = refresh_lbl

        # 13 列在 1000x860 的視窗放不下（何況幾列會折行），所以放進可捲動容器。
        body = tk.Frame(wrap, bg=C_PAGE_BG)
        body.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(body, bg=C_PAGE_BG, highlightthickness=0)
        vbar = tk.Scrollbar(body, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=C_PAGE_BG)
        win = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win, width=e.width))
        # 滾輪只在游標進入本頁時綁定，離開就解除，避免影響「服務控制」分頁。
        canvas.bind("<Enter>", lambda e: canvas.bind_all(
            "<MouseWheel>",
            lambda ev: canvas.yview_scroll(int(-ev.delta / 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self._health_rows = {}
        for sec_idx, (section, items) in enumerate(self.HEALTH_SECTIONS):
            tk.Label(
                inner, text=section, bg=C_PAGE_BG, fg=C_TEXT_DIM, anchor="w",
                font=(FONT_NAME, 9, "bold"),
            ).pack(fill=tk.X, pady=(0 if sec_idx == 0 else 14, 5))

            card = tk.Frame(inner, bg=C_CARD_BG,
                            highlightbackground=C_BORDER, highlightthickness=1)
            card.pack(fill=tk.X)

            for i, (key, label) in enumerate(items):
                row = tk.Frame(card, bg=C_CARD_BG)
                row.pack(fill=tk.X, padx=18, pady=10)
                tk.Label(
                    row, text=label, bg=C_CARD_BG, fg=C_TEXT, width=22, anchor="nw",
                    font=(FONT_NAME, 10, "bold"),
                ).pack(side=tk.LEFT, anchor="n")
                status_lbl = tk.Label(
                    row, text="—", bg=C_CARD_BG, fg=C_TEXT_DIM, anchor="w",
                    font=(FONT_NAME, 10), justify=tk.LEFT, wraplength=620,
                )
                status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self._health_rows[key] = status_lbl
                if i < len(items) - 1:
                    tk.Frame(card, bg=C_BORDER, height=1).pack(fill=tk.X, padx=18)

        # 開啟頁籤時先自動跑一次（輕量 port 檢查即時，其餘用背景執行緒）
        #
        # ⚠️⚠️ 必須排進 after() 等 mainloop 起來，**不能在這裡直接呼叫**。
        #    _build_health_page() 是在 __init__ 裡執行的，此時 mainloop 還沒開始。
        #    背景 thread 只要搶先跑完第一項檢查就會呼叫 self.after()，而從
        #    **背景執行緒**碰 tkinter API 時主執行緒不在 mainloop，會拋
        #        RuntimeError: main thread is not in main loop
        #    —— thread 當場死掉，所有 slow check 永遠停在「檢查中…」，
        #    而且畫面上看不出是壞了還是還在跑。
        #    2026-08-30：切到 PG 之後檢查變快，這場賽跑才穩定輸掉。
        self.after(100, self._run_health_checks)

    def _run_health_checks(self):
        self._btn_check_all.config(text="檢查中…", fg=C_TEXT_DIM)

        # Port 檢查很快，直接在主執行緒做
        for key, port in (("port_backend", BACKEND_PORT), ("port_frontend", FRONTEND_PORT)):
            ok = check_port("127.0.0.1", port)
            self._health_rows[key].config(
                text="✓ 連線正常" if ok else "✕ 無法連線（服務未啟動？）",
                fg=C_OK_TEXT if ok else C_ERR_TEXT,
            )

        for key, _ in self._SLOW_CHECKS:
            self._health_rows[key].config(text="檢查中…", fg=C_TEXT_DIM)

        threading.Thread(target=self._run_slow_health_checks, daemon=True).start()

    def _safe_after(self, *args):
        """背景執行緒回主執行緒專用。視窗已關閉時放棄排程，不噴 traceback。

        ⚠️ 這裡吞掉的是「UI 已經不存在了」，**不是檢查結果**。
           檢查本身失敗一律照常顯示成紅字（見 _run_slow_health_checks 的註解）——
           「查不出來」不等於「查過沒問題」這條規則沒有因此鬆動。
        """
        try:
            self.after(*args)
        except (RuntimeError, tk.TclError):
            pass

    def _run_slow_health_checks(self):
        """每一項各自檢查、各自回報，**任何一項壞掉都不影響其他項**。

        ⚠️ 這裡的 try/except 只吞「檢查程式自己爆掉」，而且會把錯誤顯示成紅字。
           絕不可以改成 `except: pass` ——「查不出來」不等於「查過沒問題」
           （見記憶：正式區事故的根因就是三道檢查各自靜默跳過）。
        """
        for key, method in self._SLOW_CHECKS:
            try:
                state, msg = getattr(self, method)()
            except Exception as e:
                state, msg = "err", f"檢查失敗（{type(e).__name__}）：{e}"
            self._safe_after(0, self._apply_health, key, state, msg)

        self._safe_after(0, lambda: self._btn_check_all.config(
            text="🔄  重新檢查全部", fg=C_TAB_BG))

    def _apply_health(self, key: str, state: str, msg: str):
        prefix, color = self._HEALTH_STYLE.get(state, self._HEALTH_STYLE["info"])
        self._health_rows[key].config(text=prefix + msg, fg=color)

    # ── 小工具 ───────────────────────────────────────────────────────────────
    @staticmethod
    def _fmt_bytes(n: float) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024 or unit == "TB":
                return f"{n:,.1f} {unit}" if unit != "B" else f"{int(n)} B"
            n /= 1024
        return f"{n:.1f} TB"

    @staticmethod
    def _ago(ts: datetime) -> str:
        d = datetime.now() - ts
        if d < timedelta(0):
            return "剛剛"
        if d.days >= 1:
            return f"{d.days} 天 {d.seconds // 3600} 小時前"
        if d.seconds >= 3600:
            return f"{d.seconds // 3600} 小時前"
        return f"{max(d.seconds // 60, 1)} 分鐘前"

    @staticmethod
    def _read_backend_env() -> dict:
        """直接讀 backend/.env。PG_BACKUP_DIR 這類設定沒有進 app.core.config
        的 Settings，只能自己讀（做法與 backend/scripts/pg_backup.py 相同）。"""
        return _read_env_file(_BACKEND / ".env")

    @staticmethod
    def _backup_root_static() -> str:
        """備份目錄。預設值與 backend/scripts/pg_backup.py 的 DEFAULT_DIR 一致，
        兩邊要改一起改，否則 Console 會去讀一個沒人在寫的目錄。"""
        return PortalConsole._read_backend_env().get("PG_BACKUP_DIR") or r"D:\portal_backup\pg"

    @staticmethod
    def _backup_status_static() -> dict | None:
        p = _os.path.join(PortalConsole._backup_root_static(), "_status.json")
        if not _os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            return json.load(f)

    # ── 各項檢查 ─────────────────────────────────────────────────────────────
    @staticmethod
    def _check_environment():
        """三道依據交叉比對出「這台是正式區還是測試區」。矛盾就是紅燈。

        ⚠️ 矛盾**不是**小問題：正式區的 .env 忘了改成 production，會讓
           APP_ENV=production 才關閉的 /api/docs 在正式區公開，也會讓任何
           「照環境切行為」的邏輯全部走錯分支——而這件事平常完全看不出來。
        """
        info = detect_environment()
        detail = "　｜　".join(f"{name}：{desc}" for name, _, desc in info["signals"])
        if info["conflict"]:
            votes = "、".join(
                f"{name}→{ENV_LABEL[v]}" for name, v, _ in info["signals"] if v)
            return "err", (f"**三道依據互相矛盾（{votes}）**，請人工確認後修正"
                           f"　｜　{detail}")
        if info["env"] == ENV_UNKNOWN:
            return "warn", f"無法判定（三道依據都沒有結論）　｜　{detail}"
        state = "info" if info["env"] == ENV_TEST else "ok"
        return state, f"{ENV_LABEL[info['env']]}　｜　{detail}"

    @staticmethod
    def _check_db():
        from sqlalchemy import text
        from app.core.database import engine

        try:
            t0 = time.time()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            ms = int((time.time() - t0) * 1000)
            return "ok", f"連線正常（{ms} ms）"
        except Exception as e:
            return "err", f"連線失敗：{e}"

    @staticmethod
    def _check_db_version():
        """顯示**實際連上的**資料庫種類、版本與位置。

        ⚠️ 連到 SQLite 一律顯示黃燈：2026-08-29 正式區與測試區都已切到
           PostgreSQL，`portal.db` 從那一刻起就凍結不再更新。此時畫面能正常
           開、查詢也不會報錯，只是看到的全是舊資料——這一列就是要讓那件事
           一眼看得出來。
        """
        from sqlalchemy import text
        from app.core.database import engine

        url = engine.url          # ⚠️ 用 engine.url 而不是 settings，這才是真正連上的那一個
        drv = url.drivername
        with engine.connect() as conn:
            if drv.startswith("postgresql"):
                ver = conn.execute(text("SHOW server_version")).scalar()
                where = f"{url.host}:{url.port or 5432}/{url.database}"
                return "ok", f"PostgreSQL {ver}　｜　{where}"
            if drv.startswith("sqlite"):
                ver = conn.execute(text("SELECT sqlite_version()")).scalar()
                return "warn", (f"SQLite {ver}　｜　{url.database}"
                                "　←　正式環境應為 PostgreSQL，請確認 .env 的 DATABASE_URL")
            ver = conn.execute(text("SELECT version()")).scalar()
            return "info", f"{drv}　｜　{ver}"

    @classmethod
    def _check_db_size(cls):
        from sqlalchemy import text
        from app.core.database import engine

        url = engine.url
        with engine.connect() as conn:
            if url.drivername.startswith("postgresql"):
                size = conn.execute(text(
                    "SELECT pg_size_pretty(pg_database_size(current_database()))"
                )).scalar()
                tables = conn.execute(text(
                    "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'"
                )).scalar()
                # n_live_tup 是統計值（autovacuum 更新），沒跑過 ANALYZE 會是 0，
                # 所以標示為「約」，別讓人誤以為是精確筆數。
                top = conn.execute(text(
                    "SELECT relname, n_live_tup, "
                    "       pg_size_pretty(pg_total_relation_size(relid)) "
                    "FROM pg_stat_user_tables "
                    "ORDER BY pg_total_relation_size(relid) DESC LIMIT 3"
                )).all()
                big = "、".join(f"{r[0]}（約 {r[1]:,} 列 / {r[2]}）" for r in top)
                return "info", f"{size}　｜　{tables} 張表　｜　最大：{big}"

            if url.drivername.startswith("sqlite"):
                path = url.database or ""
                size = cls._fmt_bytes(_os.path.getsize(path)) if _os.path.exists(path) else "檔案不存在"
                tables = conn.execute(text(
                    "SELECT count(*) FROM sqlite_master WHERE type = 'table'"
                )).scalar()
                return "info", f"{size}　｜　{tables} 張表"

            return "info", "（此資料庫種類未支援大小查詢）"

    @classmethod
    def _check_disk(cls):
        """列出「資料庫資料目錄」與「備份目錄」所在磁碟的剩餘空間。

        磁碟滿了的時候，同步與備份都會失敗，而且多半是靜默失敗——這一列
        就是要讓它在變成事故之前先變成黃燈。
        """
        from sqlalchemy import text
        from app.core.database import engine

        url = engine.url
        # drive → 這顆磁碟上放了什麼（用來提示使用者「滿了會影響誰」）
        targets: dict[str, set[str]] = {}

        def _add(path: str, what: str):
            if not path:
                return
            drive = _os.path.splitdrive(_os.path.abspath(path))[0] or "/"
            targets.setdefault(drive, set()).add(what)

        if url.drivername.startswith("postgresql"):
            # 只有 PG 跑在本機時，data_directory 才是「本機的磁碟」。
            if (url.host or "").lower() in ("localhost", "127.0.0.1", "::1", ""):
                try:
                    with engine.connect() as conn:
                        _add(conn.execute(text("SHOW data_directory")).scalar(), "PG 資料")
                except Exception:
                    pass  # 非 superuser 讀不到 data_directory，不是錯誤
        elif url.drivername.startswith("sqlite") and url.database:
            _add(_os.path.dirname(_os.path.abspath(url.database)), "SQLite 檔")

        _add(cls._backup_root_static(), "備份")
        _add(str(_LOG_DIR), "log")

        if not targets:
            return "info", "（找不到可檢查的路徑）"

        parts, worst = [], "ok"
        for drive in sorted(targets):
            try:
                usage = shutil.disk_usage(drive + _os.sep)
            except Exception as e:
                parts.append(f"{drive} 讀取失敗（{type(e).__name__}）")
                worst = "warn"
                continue
            pct = usage.free / usage.total * 100 if usage.total else 0
            gb = usage.free / (1024 ** 3)
            if gb < 10 or pct < 5:
                worst = "err"
            elif (gb < 30 or pct < 15) and worst != "err":
                worst = "warn"
            parts.append(f"{drive} 剩 {cls._fmt_bytes(usage.free)} / "
                         f"{cls._fmt_bytes(usage.total)}（{pct:.0f}%，"
                         f"{'／'.join(sorted(targets[drive]))}）")
        return worst, "　｜　".join(parts)

    @staticmethod
    def _check_backend_version():
        """打 /api/v1/version 取後端的 git commit（全站唯一免登入端點）。

        正式區／測試區顯示不同時，第一個要查的就是版本落差（見記憶：
        商場年度計劃表那次的根因就是 git pull 沒成功）。
        """
        import httpx

        url = f"http://127.0.0.1:{BACKEND_PORT}/api/v1/version"
        try:
            with httpx.Client(timeout=4.0) as client:
                data = client.get(url).json()
        except Exception as e:
            return "info", f"後端未啟動或無法連線（{type(e).__name__}）｜Console v{CONSOLE_VERSION}"

        g = data.get("git") or {}
        short = g.get("commit_short") or "（不明）"
        branch = g.get("branch") or "?"
        date = (g.get("commit_date") or "")[:19].replace("T", " ")
        src = data.get("source") or "?"
        state = "warn" if src == "unavailable" else "info"
        return state, (f"{short}（{branch}）　｜　{date}　｜　來源：{src}"
                       f"　｜　Console v{CONSOLE_VERSION}")

    @staticmethod
    def _check_runtime():
        """顯示 Console 目前實際跑在哪個 Python 上。

        正式區用 `py -3.11`，開發機常是 3.12；套件裝在 A 版、程式跑在 B 版
        是這個專案已經踩過的坑，所以直接把版本與 site-packages 來源攤開。
        """
        v = _sys.version_info
        bits = 64 if _sys.maxsize > 2 ** 32 else 32
        src = _venv_path or "系統 Python（未注入 venv site-packages）"
        state = "info" if _venv_path else "warn"
        return state, (f"Python {v.major}.{v.minor}.{v.micro}（{bits}-bit）"
                       f"　｜　{_sys.executable}　｜　套件來源：{src}")

    @staticmethod
    def _check_ragic():
        import httpx
        from app.core.config import settings

        try:
            server = settings.RAGIC_SERVER_URL or f"{settings.RAGIC_SERVER}.ragic.com"
            account = settings.RAGIC_ACCOUNT_NAME or settings.RAGIC_ACCOUNT
            url = f"https://{server}/{account}/"
            headers = {"Authorization": f"Basic {settings.RAGIC_API_KEY}"}

            t0 = time.time()
            with httpx.Client(timeout=8.0, verify=settings.RAGIC_VERIFY_SSL) as client:
                resp = client.get(url, headers=headers)
            ms = int((time.time() - t0) * 1000)

            if resp.status_code < 500:
                return "ok", f"可連線（HTTP {resp.status_code}，{ms} ms）"
            return "err", f"伺服器回應異常（HTTP {resp.status_code}）"
        except Exception as e:
            return "err", f"無法連線：{e}"

    @staticmethod
    def _check_scheduler():
        """讀取 .env 的 SCHEDULER_ENABLED，判斷後端是否有排程自動同步。

        2026-07-18：原本的「最近一次同步」是抓 logs/ 目錄裡『最新修改』的
        .log 檔案 mtime，但 backend 啟動時建立的常駐 session log（main.py
        ::_setup_file_logging，檔名不含 _manual）只要 backend 還在跑、
        持續有任何 log 輸出就會一直更新 mtime，跟「有沒有真的同步」完全
        無關；而且開發機慣例是 .env 設 SCHEDULER_ENABLED=false（改用
        sync_tool.py 手動同步）。改為直接讀取設定值，如實呈現「有沒有排程」。
        """
        try:
            from app.core.config import settings
            if settings.SCHEDULER_ENABLED:
                return "ok", "已啟用（整點對齊，每 30 分鐘自動同步）"
            return "warn", "已停用（開發模式；需執行 sync_tool.py 或按「同步資料」手動同步）"
        except Exception as e:
            return "err", f"無法讀取設定：{e}"

    @staticmethod
    def _check_sync_modules():
        """從 module_sync_log 讀每個模組**最後一次**的同步結果。

        ⚠️ 用 max(id) 取最後一筆，不是「取最近 N 筆再去重」——後者會讓
           「已經很久沒同步的模組」直接從清單裡消失，而那正是最該被看見的。
        """
        from sqlalchemy import func
        from app.core.database import SessionLocal
        from app.models.module_sync_log import ModuleSyncLog

        db = SessionLocal()
        try:
            latest = (db.query(ModuleSyncLog.module_name,
                               func.max(ModuleSyncLog.id).label("mid"))
                        .group_by(ModuleSyncLog.module_name).subquery())
            rows = (db.query(ModuleSyncLog)
                      .join(latest, ModuleSyncLog.id == latest.c.mid).all())
        finally:
            db.close()

        if not rows:
            return "warn", "module_sync_log 沒有任何紀錄（尚未同步過，或連到了另一個資料庫）"

        stamps = [r.started_at for r in rows if r.started_at]
        if not stamps:
            return "warn", f"{len(rows)} 筆紀錄都沒有 started_at，無法判斷同步時間"
        newest = max(stamps)
        failed = [r.module_name for r in rows if r.status not in ("success", "running")]
        anomaly = [r.module_name for r in rows if getattr(r, "is_anomaly", False)]
        stale = [r.module_name for r in rows
                 if r.started_at and datetime.now() - r.started_at > timedelta(hours=48)]

        def _names(lst):
            head = "、".join(lst[:3])
            return head + (f" 等 {len(lst)} 個" if len(lst) > 3 else "")

        msg = (f"最新 {newest:%Y-%m-%d %H:%M}（{PortalConsole._ago(newest)}）"
               f"　｜　共 {len(rows)} 個模組")
        state = "ok"
        if failed:
            state = "err"
            msg += f"　｜　{len(failed)} 個未成功：{_names(failed)}"
        if anomaly:
            state = "err" if state == "err" else "warn"
            msg += f"　｜　{len(anomaly)} 個標記異常：{_names(anomaly)}"
        if stale:
            state = "err" if state == "err" else "warn"
            msg += f"　｜　{len(stale)} 個超過 48 小時沒同步：{_names(stale)}"
        if state == "ok":
            msg += "　｜　全部成功"
        return state, msg

    @staticmethod
    def _check_last_manual_sync():
        """只看 *_manual.log（sync_tool.py「立即同步」或網頁「同步資料」按鈕才會產生），
        不採計 backend 啟動時建立的常駐 session log，避免誤判。"""
        candidates = list(_LOG_DIR.glob("*_manual.log"))
        if not candidates:
            return "info", "尚未執行過手動同步（或紀錄已被清除）"
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        ts = datetime.fromtimestamp(latest.stat().st_mtime)
        return "info", f"{ts:%Y-%m-%d %H:%M:%S}（{PortalConsole._ago(ts)}）"

    @classmethod
    def _check_backup(cls):
        """讀 pg_backup.py 寫的 _status.json（跟 `--status` 同一個判定門檻）。

        ⚠️⚠️ 超過 2 天沒成功備份就是**紅燈**，不是黃燈。備份排程壞掉的時候
           不會有任何人來通知你——檔案還在、目錄還在、看起來一切正常，
           直到需要還原的那一天（見 pg_backup.py 檔頭）。
        """
        root = cls._backup_root_static()
        try:
            st = cls._backup_status_static()
        except Exception as e:
            return "err", f"{root} 的 _status.json 讀不開：{e}"

        if st is None:
            return "err", (f"找不到 {_os.path.join(root, '_status.json')}"
                           "　←　**從來沒有成功備份過**")

        last = datetime.fromisoformat(st["last_success"])
        age = datetime.now() - last
        state = "err" if age > timedelta(days=2) else "ok"

        extra = ""
        try:
            runs = sorted((d for d in _os.listdir(root)
                           if re.fullmatch(r"\d{8}_\d{6}", d)), reverse=True)
            if runs:
                newest = _os.path.join(root, runs[0])
                files = [f for f in _os.listdir(newest) if f.endswith(".dump")]
                total = sum(_os.path.getsize(_os.path.join(newest, f)) for f in files)
                extra = (f"　｜　最新 {cls._fmt_bytes(total)} / {len(files)} 個 dump"
                         f"　｜　目錄保留 {len(runs)} 份")
        except Exception:
            extra = "　｜　（備份目錄內容讀取失敗）"

        msg = f"{last:%Y-%m-%d %H:%M:%S}（{cls._ago(last)}）{extra}"
        if state == "err":
            msg += f"　←　已經 {age.days} 天沒有成功備份，排程可能壞了"
        return state, msg

    @classmethod
    def _check_verify_restore(cls):
        """上次真的把備份還原回來、逐表比對筆數是什麼時候。

        ⚠️ `pg_dump` 回 0 只代表「寫出了一個檔案」。**沒有還原過的備份不算備份。**
           這一列的資料來自 `py -3.11 scripts\\pg_backup.py --verify-restore`。
        """
        try:
            st = cls._backup_status_static()
        except Exception as e:
            return "warn", f"_status.json 讀不開：{e}"

        if st is None:
            return "warn", "尚無備份紀錄可驗證"

        vr = st.get("last_verify_restore")
        if not vr:
            return "warn", ("**從來沒有驗證過還原** —— pg_dump 成功不代表還原得回來。"
                            "請跑：cd backend && py -3.11 scripts\\pg_backup.py --verify-restore")

        ts = datetime.fromisoformat(vr)
        days = (datetime.now() - ts).days
        run = st.get("last_verify_restore_run") or ""
        state = "warn" if days > 30 else "ok"
        msg = f"{ts:%Y-%m-%d %H:%M:%S}（{cls._ago(ts)}）"
        if run:
            msg += f"　｜　驗證的備份：{run}"
        if state == "warn":
            msg += f"　←　已 {days} 天未驗證，建議每月至少一次"
        return state, msg

    # ── 分頁 3：備份（2026-08-29 新增）────────────────────────────────────────
    # 這一頁只做一件事：讓人**現在就能備份**，而且看得到它真的跑了什麼。
    #
    # ⚠️ 備份邏輯一律呼叫 backend/scripts/pg_backup.py，Console 不自己實作一套
    #    pg_dump。排程跑的與手動按的是同一支腳本、同一組門檻、同一個
    #    _status.json —— 兩套邏輯遲早會分岔，而分岔的那一天你不會知道。
    def _build_backup_page(self, parent: tk.Frame):
        wrap = tk.Frame(parent, bg=C_PAGE_BG)
        wrap.pack(fill=tk.BOTH, expand=True, padx=24, pady=(18, 8))

        top = tk.Frame(wrap, bg=C_PAGE_BG)
        top.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            top, text="備份", bg=C_PAGE_BG, fg=C_TEXT,
            font=(FONT_NAME, 18, "bold"),
        ).pack(side=tk.LEFT)
        refresh = tk.Label(
            top, text="🔄  重新整理", bg=C_PAGE_BG, fg=C_TAB_BG,
            font=(FONT_NAME, 10, "bold"), cursor="hand2",
        )
        refresh.pack(side=tk.RIGHT)
        refresh.bind("<Button-1>", lambda e: self._refresh_backup_page())

        # ── 環境卡 ───────────────────────────────────────────────────────────
        env_card = tk.Frame(wrap, bg=C_CARD_BG,
                            highlightbackground=C_BORDER, highlightthickness=1)
        env_card.pack(fill=tk.X, pady=(0, 12))
        self._bk_env_title = tk.Label(
            env_card, text="偵測中…", bg=C_CARD_BG, fg=C_TEXT, anchor="w",
            font=(FONT_NAME, 13, "bold"),
        )
        self._bk_env_title.pack(fill=tk.X, padx=16, pady=(12, 2))
        self._bk_env_detail = tk.Label(
            env_card, text="", bg=C_CARD_BG, fg=C_TEXT_DIM, anchor="w",
            font=(FONT_NAME, 9), justify=tk.LEFT, wraplength=880,
        )
        self._bk_env_detail.pack(fill=tk.X, padx=16, pady=(0, 12))

        # ── 備份目錄卡 ───────────────────────────────────────────────────────
        dir_card = tk.Frame(wrap, bg=C_CARD_BG,
                            highlightbackground=C_BORDER, highlightthickness=1)
        dir_card.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            dir_card, text="備份目錄", bg=C_CARD_BG, fg=C_TEXT, anchor="w",
            font=(FONT_NAME, 13, "bold"),
        ).pack(fill=tk.X, padx=16, pady=(12, 2))
        self._bk_dir_detail = tk.Label(
            dir_card, text="", bg=C_CARD_BG, fg=C_TEXT_DIM, anchor="w",
            font=(FONT_NAME, 9), justify=tk.LEFT, wraplength=880,
        )
        self._bk_dir_detail.pack(fill=tk.X, padx=16, pady=(0, 10))

        toolbar = tk.Frame(dir_card, bg=C_CARD_BG,
                           highlightbackground=C_BORDER, highlightthickness=1)
        toolbar.pack(fill=tk.X, padx=16, pady=(0, 12))

        def _btn(icon, text, cmd):
            lbl = tk.Label(
                toolbar, text=f"{icon}  {text}", bg=C_CARD_BG, fg=C_BTN_TEXT,
                font=(FONT_NAME, 10), padx=10, pady=8, cursor="hand2",
            )
            lbl.pack(side=tk.LEFT)
            lbl.bind("<Button-1>", lambda e: cmd())
            return lbl

        self._bk_btn_run = _btn("💾", "立即備份", self._run_manual_backup)
        tk.Frame(toolbar, bg=C_BORDER, width=1, height=18).pack(side=tk.LEFT, padx=8, pady=6)
        _btn("📂", "開啟備份資料夾", self._open_backup_dir)

        # ── 內嵌終端機 ───────────────────────────────────────────────────────
        tk.Label(
            wrap, text="pg_backup.py 即時輸出", bg=C_PAGE_BG, fg=C_TEXT_DIM,
            font=(FONT_NAME, 9), anchor="w",
        ).pack(fill=tk.X)
        log_box = scrolledtext.ScrolledText(
            wrap, height=12, bg=C_TERM_BG, fg=C_TERM_FG, insertbackground=C_TERM_FG,
            font=("Consolas", 9), wrap=tk.NONE, state=tk.DISABLED, borderwidth=0,
        )
        log_box.pack(fill=tk.BOTH, expand=True, pady=(2, 6))
        log_box.configure(state=tk.NORMAL)
        log_box.insert(tk.END, "（尚未執行過備份。按「立即備份」開始。）\n")
        log_box.configure(state=tk.DISABLED)
        self._log_widgets[self.BACKUP_LOG_KEY] = log_box
        self._log_queues.setdefault(self.BACKUP_LOG_KEY, queue.Queue())

        clear_row = tk.Frame(wrap, bg=C_PAGE_BG)
        clear_row.pack(fill=tk.X, pady=(0, 6))
        clear_lbl = tk.Label(
            clear_row, text="清除畫面", bg=C_PAGE_BG, fg=C_TEXT_DIM,
            font=(FONT_NAME, 8), cursor="hand2",
        )
        clear_lbl.pack(side=tk.RIGHT)
        clear_lbl.bind("<Button-1>", lambda e: self._clear_log_box(log_box))

        self._backup_proc: subprocess.Popen | None = None
        self._refresh_backup_page()

    def _refresh_backup_page(self):
        """更新環境卡與備份目錄卡（只讀，不建立任何東西）。"""
        info = detect_environment()
        if info["conflict"]:
            self._bk_env_title.config(
                text="⚠ 執行環境：無法判定（三道依據互相矛盾）", fg=C_ERR_TEXT)
        else:
            self._bk_env_title.config(
                text=f"執行環境：{ENV_LABEL[info['env']]}",
                fg=C_ERR_TEXT if info["env"] == ENV_UNKNOWN else C_TEXT)
        lines = [f"　·　{name}：{desc}"
                 + ("" if vote is None else f"　→　判定為 {ENV_LABEL[vote]}")
                 for name, vote, desc in info["signals"]]
        if info["conflict"]:
            lines.append("　·　⚠️ 三道依據不一致時本程式不會自行猜測。請先確認"
                         " backend/.env 的 APP_ENV 是否與這台機器相符，再執行備份。")
        self._bk_env_detail.config(text="\n".join(lines))

        env = self._read_backend_env()
        root = self._backup_root_static()
        configured = bool(env.get("PG_BACKUP_DIR"))
        days = env.get("PG_BACKUP_RETENTION_DAYS") or "14（pg_backup.py 預設）"

        lines = [f"　·　路徑：{root}"
                 + ("（來自 .env 的 PG_BACKUP_DIR）" if configured
                    else "（.env 未設定 PG_BACKUP_DIR，使用 pg_backup.py 的預設值）")]
        if not configured:
            lines.append(f"　·　依這台機器的安裝磁碟，建議值為 {suggest_backup_dir()}"
                         "　—　⚠️ 本程式**不會**自動改寫 .env，要採用請自行填入")
        if _os.path.isdir(root):
            try:
                runs = [d for d in _os.listdir(root)
                        if re.fullmatch(r"\d{8}_\d{6}", d)]
                lines.append(f"　·　狀態：目錄存在，目前保留 {len(runs)} 份備份")
            except Exception as e:
                lines.append(f"　·　狀態：目錄存在，但讀取失敗（{type(e).__name__}）")
        else:
            lines.append("　·　狀態：**目錄不存在** —— 按「立即備份」時會自動建立")

        lines.append(f"　·　保留天數（PG_BACKUP_RETENTION_DAYS）：{days}")
        if str(days).strip() in ("0", "1"):
            lines.append("　·　⚠️ 保留天數只有 1 天：昨天的備份今天就會被刪掉，"
                         "一旦某次備份成功但內容有問題，沒有第二份可以退回")

        # ⚠️ 備份與資料庫在同一顆磁碟不是真備份（pg_backup.py 檔頭）。
        bk_drive = _os.path.splitdrive(_os.path.abspath(root))[0].upper()
        try:
            from app.core.database import engine
            db_drive = ""
            if engine.url.drivername.startswith("sqlite") and engine.url.database:
                db_drive = _os.path.splitdrive(
                    _os.path.abspath(engine.url.database))[0].upper()
            elif engine.url.drivername.startswith("postgresql") and \
                    (engine.url.host or "").lower() in ("localhost", "127.0.0.1", "::1", ""):
                from sqlalchemy import text as _sql_text
                with engine.connect() as conn:
                    dd = conn.execute(_sql_text("SHOW data_directory")).scalar()
                db_drive = _os.path.splitdrive(_os.path.abspath(dd))[0].upper()
            if db_drive and db_drive == bk_drive:
                lines.append(f"　·　⚠️ 備份與資料庫都在 {bk_drive} —— 這顆硬碟壞掉會一起帶走。"
                             "請另外排程複製到 NAS／雲端")
        except Exception:
            pass  # 讀不到就不提示；這只是加值資訊，不影響備份本身

        self._bk_dir_detail.config(text="\n".join(lines))

    def _open_backup_dir(self):
        root = self._backup_root_static()
        if not _os.path.isdir(root):
            self._toast.show(f"備份目錄還不存在：{root}", kind="error")
            return
        try:
            _os.startfile(root)          # noqa: S606（Windows 專用，本程式只跑在 Windows）
        except Exception as e:
            self._toast.show(f"無法開啟資料夾：{e}", kind="error")

    def _run_manual_backup(self):
        """手動觸發 backend/scripts/pg_backup.py，輸出即時導到內嵌終端機。

        ⚠️ 環境判定矛盾時**擋下不跑**。備份是會在磁碟上留下東西的動作，
           在「不知道自己是正式區還是測試區」的狀態下執行，等於不知道自己
           備份的是哪一份資料 —— 那比沒有備份更危險，因為它看起來是成功的。
        """
        if self._backup_proc is not None and self._backup_proc.poll() is None:
            self._toast.show("備份已在執行中，請稍候", kind="error")
            return

        info = detect_environment()
        if info["conflict"]:
            self._toast.show("環境判定矛盾，已擋下備份。請先確認 .env 的 APP_ENV",
                             kind="error")
            return

        script = _BACKEND / "scripts" / "pg_backup.py"
        if not script.exists():
            self._toast.show(f"找不到備份腳本：{script}", kind="error")
            return

        q = self._log_queues.setdefault(self.BACKUP_LOG_KEY, queue.Queue())
        log_box = self._log_widgets.get(self.BACKUP_LOG_KEY)
        if log_box is not None:
            self._clear_log_box(log_box)

        root = self._backup_root_static()
        q.put(f"[Console] 環境：{ENV_LABEL[info['env']]}")
        q.put(f"[Console] 備份目錄：{root}")

        # 「路徑不匹配就自動加上去」＝ 只自動建目錄。
        # ⚠️ 刻意**不**自動改寫 backend/.env（CLAUDE.md §5）：.env 是正式區的
        #    設定來源，程式在使用者沒看見的情況下改它，下一個人看到的設定
        #    就不是他自己寫的那一份。缺 PG_BACKUP_DIR 時只在畫面上提示建議值。
        if not _os.path.isdir(root):
            try:
                _os.makedirs(root, exist_ok=True)
                q.put(f"[Console] 目錄不存在，已自動建立：{root}")
            except Exception as e:
                q.put(f"[Console] ❌ 無法建立備份目錄：{e}")
                self._toast.show(f"無法建立備份目錄：{e}", kind="error")
                return

        cmd = [_sys.executable, str(script)]
        q.put(f"[Console] 執行：{' '.join(cmd)}（cwd={_BACKEND}）")
        self._bk_btn_run.config(text="⏳  備份中…", fg=C_TEXT_DIM)
        self._toast.show("開始備份…")

        def work():
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(_BACKEND),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=_CREATE_NO_WINDOW,
                )
            except Exception as e:
                q.put(f"[Console] ❌ 啟動備份腳本失敗：{e}")
                return None
            self._backup_proc = proc
            q.put(f"[Console] PID {proc.pid}")
            for line in proc.stdout:
                q.put(_ANSI_ESCAPE_RE.sub("", line.rstrip("\n")))
            code = proc.poll()
            q.put(f"[Console] 備份行程結束（exit code {code}）")
            return code

        def done(code):
            self._bk_btn_run.config(text="💾  立即備份", fg=C_BTN_TEXT)
            # ⚠️ pg_backup.py 任何一步失敗都會 exit 非 0，而且不吞例外。
            #    這裡照它的 exit code 判定，不自己重新解讀輸出文字。
            if code == 0:
                self._toast.show("備份完成（pg_backup.py exit 0）")
            elif code is None:
                self._toast.show("備份未能啟動，請查看下方輸出", kind="error")
            else:
                self._toast.show(f"備份失敗（exit code {code}），請查看下方輸出",
                                 kind="error")
            self._refresh_backup_page()
            # 備份／還原驗證兩列的資料就是 _status.json，跑完立刻反映到 Health Check
            self._run_health_checks()

        self._run_bg(work, done)


if __name__ == "__main__":
    app = PortalConsole()
    app.mainloop()
