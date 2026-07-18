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
   未以系統管理員身分執行，Start/Stop/Restart 會失敗並在 Toast 顯示原因。

執行方式：
  cd portal
  python portal_console.py
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

import queue
import re
import socket
import subprocess
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime
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
    ]

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
        self._build_content_area()

        self._page_service = tk.Frame(self._content, bg=C_PAGE_BG)
        self._page_health = tk.Frame(self._content, bg=C_PAGE_BG)
        self._build_service_page(self._page_service)
        self._build_health_page(self._page_health)
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

        if idx == 0:
            self._page_health.pack_forget()
            self._page_service.pack(fill=tk.BOTH, expand=True)
        else:
            self._page_service.pack_forget()
            self._page_health.pack(fill=tk.BOTH, expand=True)

    # ── 內容區容器 ───────────────────────────────────────────────────────────
    def _build_content_area(self):
        self._content = tk.Frame(self, bg=C_PAGE_BG)
        self._content.pack(fill=tk.BOTH, expand=True)

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
                self.after(0, lambda: on_done(result))
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

    # ── 分頁 2：Health Check ─────────────────────────────────────────────────
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

        card = tk.Frame(wrap, bg=C_CARD_BG, highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        self._health_rows = {}
        items = [
            ("port_backend", f"Backend Port ({BACKEND_PORT})"),
            ("port_frontend", f"Frontend Port ({FRONTEND_PORT})"),
            ("db", "資料庫連線"),
            ("ragic", "Ragic API 連通性"),
            ("scheduler", "自動排程狀態"),
            ("last_manual_sync", "最近一次手動同步"),
        ]
        for i, (key, label) in enumerate(items):
            row = tk.Frame(card, bg=C_CARD_BG)
            row.pack(fill=tk.X, padx=18, pady=12)
            tk.Label(
                row, text=label, bg=C_CARD_BG, fg=C_TEXT, width=22, anchor="w",
                font=(FONT_NAME, 10, "bold"),
            ).pack(side=tk.LEFT)
            status_lbl = tk.Label(
                row, text="—", bg=C_CARD_BG, fg=C_TEXT_DIM, anchor="w",
                font=(FONT_NAME, 10),
            )
            status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._health_rows[key] = status_lbl
            if i < len(items) - 1:
                tk.Frame(card, bg=C_BORDER, height=1).pack(fill=tk.X, padx=18)

        # 開啟頁籤時先自動跑一次（輕量 port 檢查即時，DB/Ragic 用背景執行緒）
        self._run_health_checks()

    def _run_health_checks(self):
        self._btn_check_all.config(text="檢查中…", fg=C_TEXT_DIM)

        # Port 檢查很快，直接在主執行緒做
        for key, port in (("port_backend", BACKEND_PORT), ("port_frontend", FRONTEND_PORT)):
            ok = check_port("127.0.0.1", port)
            lbl = self._health_rows[key]
            lbl.config(
                text="✓ 連線正常" if ok else "✕ 無法連線（服務未啟動？）",
                fg=C_OK_TEXT if ok else C_ERR_TEXT,
            )

        for key in ("db", "ragic", "scheduler", "last_manual_sync"):
            self._health_rows[key].config(text="檢查中…", fg=C_TEXT_DIM)

        threading.Thread(target=self._run_slow_health_checks, daemon=True).start()

    def _run_slow_health_checks(self):
        db_ok, db_msg = self._check_db()
        ragic_ok, ragic_msg = self._check_ragic()
        sched_ok, sched_msg = self._check_scheduler()
        manual_sync_msg = self._last_manual_sync_time()

        def _apply():
            self._health_rows["db"].config(
                text=("✓ " if db_ok else "✕ ") + db_msg,
                fg=C_OK_TEXT if db_ok else C_ERR_TEXT,
            )
            self._health_rows["ragic"].config(
                text=("✓ " if ragic_ok else "✕ ") + ragic_msg,
                fg=C_OK_TEXT if ragic_ok else C_ERR_TEXT,
            )
            self._health_rows["scheduler"].config(
                text=("✓ " if sched_ok else "⚠ ") + sched_msg,
                fg=C_OK_TEXT if sched_ok else C_WARN_TEXT,
            )
            self._health_rows["last_manual_sync"].config(text=manual_sync_msg, fg=C_TEXT_DIM)
            self._btn_check_all.config(text="🔄  重新檢查全部", fg=C_TAB_BG)

        self.after(0, _apply)

    @staticmethod
    def _check_db():
        try:
            from sqlalchemy import text
            from app.core.database import engine

            t0 = time.time()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            ms = int((time.time() - t0) * 1000)
            return True, f"連線正常（{ms} ms）"
        except Exception as e:
            return False, f"連線失敗：{e}"

    @staticmethod
    def _check_ragic():
        try:
            import httpx
            from app.core.config import settings

            server = settings.RAGIC_SERVER_URL or f"{settings.RAGIC_SERVER}.ragic.com"
            account = settings.RAGIC_ACCOUNT_NAME or settings.RAGIC_ACCOUNT
            url = f"https://{server}/{account}/"
            headers = {"Authorization": f"Basic {settings.RAGIC_API_KEY}"}

            t0 = time.time()
            with httpx.Client(timeout=8.0, verify=settings.RAGIC_VERIFY_SSL) as client:
                resp = client.get(url, headers=headers)
            ms = int((time.time() - t0) * 1000)

            if resp.status_code < 500:
                return True, f"可連線（HTTP {resp.status_code}，{ms} ms）"
            return False, f"伺服器回應異常（HTTP {resp.status_code}）"
        except Exception as e:
            return False, f"無法連線：{e}"

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
                return True, "已啟用（整點對齊，每 30 分鐘自動同步）"
            return False, "已停用（開發模式；需執行 sync_tool.py 或按「同步資料」手動同步）"
        except Exception as e:
            return False, f"無法讀取設定：{e}"

    @staticmethod
    def _last_manual_sync_time() -> str:
        """只看 *_manual.log（sync_tool.py「立即同步」或網頁「同步資料」按鈕才會產生），
        不採計 backend 啟動時建立的常駐 session log，避免誤判。"""
        try:
            candidates = list(_LOG_DIR.glob("*_manual.log"))
            if not candidates:
                return "尚未執行過手動同步（或紀錄已被清除）"
            latest = max(candidates, key=lambda p: p.stat().st_mtime)
            ts = datetime.fromtimestamp(latest.stat().st_mtime)
            return ts.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            return f"（無法讀取：{e}）"


if __name__ == "__main__":
    app = PortalConsole()
    app.mainloop()
