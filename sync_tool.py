#!/usr/bin/env python3
"""
Portal 同步管理工具
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
獨立 Python GUI 程式，完全脫離 Web 伺服器
• 直接讀取 backend/.env 設定
• 操作同一份 SQLite 資料庫
• 呼叫同一組 Ragic API sync 服務
• 每次啟動 → portal/logs/YYYYMMDD_HHMMSS.log
• 每次同步 → portal/logs/YYYYMMDD_HHMMSS_manual.log
• 支援自動同步間隔（15分/30分/1小時/2小時/4小時/8小時）

執行方式：
  cd portal
  python sync_tool.py          # 或直接雙擊 run_sync_tool.bat
"""

# ── Python 環境自動修正（必須在所有其他 import 之前）────────────────────────
# 若以系統 Python（如 C:\Python314）執行且 sqlalchemy 不可用，
# 自動找到安裝有套件的 Python（venv312 優先）並重新啟動本腳本。
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
    _portal  = _script.parent
    _backend = _portal / "backend"

    # 候選 Python 清單（依優先序）
    _candidates = [
        _backend / "venv312" / "Scripts" / "python.exe",  # 正式區 venv312
        _portal  / "backend" / "venv312" / "Scripts" / "python.exe",
        _backend / "venv311" / "Scripts" / "python.exe",
        _backend / "venv"    / "Scripts" / "python.exe",
        _backend / ".venv"   / "Scripts" / "python.exe",
        _pathlib.Path(r"C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe"),
        _pathlib.Path(r"C:\Users\admin\AppData\Local\Programs\Python\Python311\python.exe"),
        _pathlib.Path(r"C:\Python312\python.exe"),
        _pathlib.Path(r"C:\Python311\python.exe"),
    ]

    # glob 也掃 venv3* 目錄（捕捉任意版本號命名）
    for _vd in sorted(_backend.glob("venv3*"), reverse=True):
        _p = _vd / "Scripts" / "python.exe"
        if _p not in _candidates:
            _candidates.insert(2, _p)

    for _py in _candidates:
        if not _pathlib.Path(_py).exists():
            continue
        # 確認該 Python 有 sqlalchemy
        import subprocess as _sp
        _r = _sp.run(
            [str(_py), "-c", "import sqlalchemy"],
            capture_output=True,
        )
        if _r.returncode == 0:
            print(f"[SyncTool] 自動切換 Python：{_py}")
            _os.execv(str(_py), [str(_py)] + _sys.argv)
            # execv 成功後不會執行到這行

    print("[SyncTool] ⚠ 找不到含 sqlalchemy 的 Python！請確認 venv312 已建立並安裝套件。")
    print(f"[SyncTool]   目前 Python：{_sys.executable}")

_check_and_relaunch()
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import importlib
import inspect
import json
import logging
import os
import pathlib
import queue
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk
from datetime import date, datetime

# ── 路徑設定：讓 app.* 可以被 import ─────────────────────────────────────────
# 注意：所有路徑先解析為絕對路徑，再切換 CWD。
_HERE    = pathlib.Path(__file__).resolve().parent   # portal/ 絕對路徑
_BACKEND = _HERE / "backend"                          # portal/backend/ 絕對路徑
_LOG_DIR     = _HERE / "logs"                          # portal/logs/ 絕對路徑
_CONFIG_PATH = _HERE / "sync_tool_config.json"        # 暫停模組設定檔

# ⚠️ 必須在 import 任何 app.* 之前切換 CWD 到 backend/
#    原因：app.core.config 的 env_file=".env" 與 DATABASE_URL="sqlite:///./portal.db"
#    都是基於 CWD 的相對路徑，需與 uvicorn 啟動位置一致（portal/backend/）。
os.chdir(_BACKEND)

# ── 自動注入 venv site-packages（若存在）────────────────────────────────────
# 正式區通常有獨立 venv，套件不在系統 Python 裡。
# 支援常見目錄名稱：venv / .venv / env
def _inject_site_packages() -> str | None:
    """
    注入 site-packages 到 sys.path。
    優先順序：
      1. venv（backend/venv312, backend/venv, backend/.venv 等，以及 portal/ 同名目錄）
      2. 與執行中 Python 同版本的 site-packages（系統 Python 無 venv 時）
      3. 正式機固定備援路徑（Python311 → Python312）
    """
    # ── 1. 掃描 venv（含版本號命名如 venv312）───────────────────────────────
    search_roots = [_BACKEND, _BACKEND.parent]
    # 明確名稱優先（最常用的在前）；也 glob venv3* 捕捉 venv310/venv311/venv312/venv313
    explicit_names = ("venv312", "venv311", "venv310", "venv", ".venv", "env")
    for root in search_roots:
        # 先試明確名稱
        for venv_name in explicit_names:
            site_pkgs = root / venv_name / "Lib" / "site-packages"
            if not site_pkgs.exists():
                lib_dir = root / venv_name / "lib"
                if lib_dir.exists():
                    matches = list(lib_dir.glob("python*/site-packages"))
                    site_pkgs = matches[0] if matches else site_pkgs
            if site_pkgs.exists():
                if str(site_pkgs) not in sys.path:
                    sys.path.insert(0, str(site_pkgs))
                return str(site_pkgs)
        # glob 捕捉其他版本號格式（如 venv313、venv38 等）
        for venv_dir in sorted(root.glob("venv3*"), reverse=True):
            if not venv_dir.is_dir():
                continue
            site_pkgs = venv_dir / "Lib" / "site-packages"
            if site_pkgs.exists():
                if str(site_pkgs) not in sys.path:
                    sys.path.insert(0, str(site_pkgs))
                return str(site_pkgs)

    # ── 2. 從目前執行的 python.exe 反推 site-packages ────────────────────────
    py_exe = pathlib.Path(sys.executable)
    # Windows：python.exe → ../Lib/site-packages
    candidate = py_exe.parent.parent / "Lib" / "site-packages"
    if candidate.exists():
        # 確認此 site-packages 有 sqlalchemy（避免用到沒有套件的全新 Python）
        if (candidate / "sqlalchemy").exists():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return str(candidate)

    # ── 3. 正式機固定備援路徑（依序嘗試常見安裝位置）──────────────────────
    fallbacks = [
        pathlib.Path(r"C:\Users\admin\AppData\Local\Programs\Python\Python312\Lib\site-packages"),
        pathlib.Path(r"C:\Users\admin\AppData\Local\Programs\Python\Python311\Lib\site-packages"),
        pathlib.Path(r"C:\Python312\Lib\site-packages"),
        pathlib.Path(r"C:\Python311\Lib\site-packages"),
    ]
    for fallback in fallbacks:
        if fallback.exists() and (fallback / "sqlalchemy").exists():
            if str(fallback) not in sys.path:
                sys.path.insert(0, str(fallback))
            return str(fallback)

    return None

_venv_path = _inject_site_packages()
if _venv_path:
    print(f"[SyncTool] site-packages 注入：{_venv_path}")
else:
    print(f"[SyncTool] ⚠ 未找到 site-packages，使用系統 Python：{sys.executable}")

if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

_LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── 同步模組清單（與 main.py _auto_sync 保持一致）────────────────────────────
MODULES: list[tuple[str, str, str]] = [
    ("客房保養",       "app.services.room_maintenance_sync",          "sync_from_ragic"),
    ("倉庫庫存",       "app.services.inventory_sync",                 "sync_from_ragic"),
    ("客房保養明細",   "app.services.room_maintenance_detail_sync",   "sync_from_ragic"),
    ("飯店週期保養",   "app.services.periodic_maintenance_sync",      "sync_from_ragic"),
    ("B4F巡檢",       "app.services.b4f_inspection_sync",            "sync_from_ragic"),
    ("RF巡檢",        "app.services.rf_inspection_sync",             "sync_from_ragic"),
    ("B2F巡檢",       "app.services.b2f_inspection_sync",            "sync_from_ragic"),
    ("B1F巡檢",       "app.services.b1f_inspection_sync",            "sync_from_ragic"),
    ("商場週期保養",   "app.services.mall_periodic_maintenance_sync", "sync_from_ragic"),
    ("全棟例行維護",   "app.services.full_building_maintenance_sync", "sync_from_ragic"),
    ("大直工務報修",   "app.services.dazhi_repair_sync",              "sync_from_ragic"),
    ("商場工務報修",   "app.services.luqun_repair_sync",              "sync_from_ragic"),
    ("保全巡檢",       "app.services.security_patrol_sync",           "sync_all"),
    ("商場工務巡檢",   "app.services.mall_facility_inspection_sync",  "sync_all"),
    ("飯店每日巡檢",   "app.services.hotel_daily_inspection_sync",    "sync_all"),
    ("每日數值登錄",   "app.services.hotel_meter_readings_sync",      "sync_all"),
    ("IHG客房保養",   "app.services.ihg_room_maintenance_sync",      "sync_from_ragic"),
    ("核准請購單清單", "app.services.purchase_request_sync",              "sync_list_only"),
    ("核准請款單清單", "app.services.claim_request_sync",               "sync_list_only"),
    ("日曜請購單清單", "app.services.nichiyo_purchase_request_sync",    "sync_list_only"),
    ("日曜請款單清單", "app.services.nichiyo_claim_request_sync",       "sync_list_only"),
    ("主管交辦／緊急事件", "app.services.other_tasks_sync",             "sync_from_ragic"),
    ("週期保養預排",       "app.services.pm_plan_sync",                 "sync_from_ragic"),
    ("飯店例行維護",       "app.services.hotel_routine_pm_sync",        "sync_from_ragic"),
]

# ── 報修報表寄信排程 key（非同步模組，獨立處理）─────────────────────────────
MAIL_KEY = "📧 報修未完成報表寄信"

# ── 自動同步間隔選項（分鐘，0 = 關閉）─────────────────────────────────────
INTERVAL_OPTIONS: list[tuple[str, int]] = [
    ("關閉",   0),
    ("15分",  15),
    ("30分",  30),
    ("1小時", 60),
    ("2小時", 120),
    ("4小時", 240),
    ("8小時", 480),
]

# ── 顏色常數 ──────────────────────────────────────────────────────────────────
C_BG      = "#1e1e1e"
C_PANEL   = "#252526"
C_HEADER  = "#1B3A5C"
C_ACCENT  = "#4BA8E8"
C_BTN     = "#0e639c"
C_TEXT    = "#d4d4d4"
C_DIM     = "#888888"
C_SUCCESS  = "#4ec9b0"
C_WARN     = "#f0c040"
C_ERROR    = "#f04040"
C_INFO     = "#d4d4d4"
C_DISABLED = "#555555"   # 暫停模組的文字顏色


# ─────────────────────────────────────────────────────────────────────────────
# GUI Log Handler
# ─────────────────────────────────────────────────────────────────────────────
class _GuiLogHandler(logging.Handler):
    _COLORS = {
        logging.DEBUG:    C_DIM,
        logging.INFO:     C_INFO,
        logging.WARNING:  C_WARN,
        logging.ERROR:    C_ERROR,
        logging.CRITICAL: C_ERROR,
    }

    def __init__(self, text_widget: scrolledtext.ScrolledText,
                 buffer: list | None = None):
        super().__init__()
        self._w      = text_widget
        self._buffer = buffer          # list of (msg, color, levelno) — 供篩選重繪用
        self.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        ))

    def emit(self, record: logging.LogRecord):
        msg   = self.format(record) + "\n"
        color = self._COLORS.get(record.levelno, C_INFO)
        if self._buffer is not None:
            self._buffer.append((msg, color, record.levelno))
        self._w.after(0, self._append, msg, color)

    def _append(self, msg: str, color: str):
        tag = f"c{color[1:]}"
        self._w.config(state=tk.NORMAL)
        self._w.tag_config(tag, foreground=color)
        self._w.insert(tk.END, msg, tag)
        self._w.see(tk.END)
        self._w.config(state=tk.DISABLED)


# ─────────────────────────────────────────────────────────────────────────────
# 主視窗
# ─────────────────────────────────────────────────────────────────────────────
class SyncApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Portal 同步管理工具")
        self.geometry("1380x820")
        self.minsize(900, 580)
        self.configure(bg=C_BG)

        self._running          = False
        self._auto_interval    = 0          # 0 = 關閉
        self._auto_timer: threading.Timer | None = None
        self._countdown_job    = None       # after() job id
        self._next_sync_at: datetime | None = None
        self._startup_fh: logging.FileHandler | None = None
        self._gui_handler: _GuiLogHandler | None     = None
        self._filter_active    = False      # True = 只顯示錯誤列
        self._last_results: list[dict] = [] # 最近一次同步結果（供篩選用）
        self._log_buffer: list[tuple[str, str, int]] = []  # (msg, color, levelno)
        self._log_filter_active = False     # True = Log 面板只顯示 WARNING+
        self._disabled_modules: set[str] = self._load_disabled()  # 暫停同步的模組名稱集合
        self._single_syncing: set[str] = set()  # 正在單獨同步中的模組名稱

        # ── 排程執行緒狀態 ────────────────────────────────────────────────────
        self._sched_last_interval: dict[str, datetime]        = {}  # 間隔模式：上次執行時間
        self._sched_daily_done:    dict[str, tuple[date, str]] = {}  # 每日模式：(已觸發日期, 設定時間)
        self._sched_thread_running = True

        # FIFO 任務佇列：scheduler tick 入佇列，runner thread 依序取出執行
        self._task_queue: queue.Queue = queue.Queue()

        self._sched_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True, name="SyncScheduler",
        )
        self._runner_thread = threading.Thread(
            target=self._task_runner_loop, daemon=True, name="SyncTaskRunner",
        )

        self._build_ui()
        self._setup_logging()
        self._update_sync_btn_label()   # 若有暫停模組，按鈕立即顯示數量
        self._check_env()
        self._ensure_db_schema()        # 確保 DB Schema 與 ORM 模型一致（migration）

        # ⚠️ 必須在 _build_ui() 之後啟動，確保 _lbl_bottom 等 UI 元件已建立完成
        self._sched_thread.start()
        self._runner_thread.start()

    # ─────────────────────────────────────────────────────────────────────────
    # UI 建構
    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── 標題列 ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=C_HEADER, pady=8)
        hdr.pack(fill=tk.X)

        tk.Label(
            hdr, text="⚡  Portal 同步管理工具",
            bg=C_HEADER, fg="white",
            font=("Microsoft JhengHei UI", 13, "bold"),
        ).pack(side=tk.LEFT, padx=16)

        self._lbl_logpath = tk.Label(
            hdr, text="", bg=C_HEADER, fg=C_DIM,
            font=("Consolas", 9),
        )
        self._lbl_logpath.pack(side=tk.RIGHT, padx=16)

        self._lbl_status = tk.Label(
            hdr, text="就緒", bg=C_HEADER, fg=C_ACCENT,
            font=("Microsoft JhengHei UI", 10),
        )
        self._lbl_status.pack(side=tk.RIGHT, padx=4)

        # 即時時鐘（YYYYMMDD  HH:MM:SS）
        self._lbl_clock = tk.Label(
            hdr, text="",
            bg=C_HEADER, fg="#90c0e8",
            font=("Consolas", 11, "bold"),
        )
        self._lbl_clock.pack(side=tk.RIGHT, padx=(24, 4))
        self._tick_clock()   # 啟動每秒更新

        # ── 控制列 ──────────────────────────────────────────────────────────
        ctrl = tk.Frame(self, bg=C_PANEL, pady=7, padx=14)
        ctrl.pack(fill=tk.X)

        self._btn_sync = tk.Button(
            ctrl,
            text="▶  立即同步所有模組",
            bg=C_BTN, fg="white",
            activebackground="#1177bb", activeforeground="white",
            font=("Microsoft JhengHei UI", 11, "bold"),
            relief=tk.FLAT, padx=18, pady=5,
            command=self._on_sync,
            cursor="hand2",
        )
        self._btn_sync.pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            ctrl, text="清除 Log",
            bg="#3c3c3c", fg=C_TEXT,
            activebackground="#555555",
            font=("Microsoft JhengHei UI", 10),
            relief=tk.FLAT, padx=10, pady=5,
            command=self._on_clear, cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 12))

        self._btn_send_repair = tk.Button(
            ctrl,
            text="📧 寄送報修未完成報表",
            bg="#1a4a2e", fg="#4ec9b0",
            activebackground="#1e6038", activeforeground="white",
            font=("Microsoft JhengHei UI", 10),
            relief=tk.FLAT, padx=12, pady=5,
            command=self._on_send_repair_report,
            cursor="hand2",
        )
        self._btn_send_repair.pack(side=tk.LEFT, padx=(0, 12))

        tk.Button(
            ctrl,
            text="⚙ 排程設定",
            bg="#3a3a5c", fg="#c0c0e0",
            activebackground="#4a4a7c", activeforeground="white",
            font=("Microsoft JhengHei UI", 10),
            relief=tk.FLAT, padx=12, pady=5,
            command=self._open_schedule_dialog,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 12))

        self._progress = ttk.Progressbar(ctrl, mode="indeterminate", length=180)
        self._progress.pack(side=tk.LEFT, padx=(0, 8))

        self._lbl_module = tk.Label(
            ctrl, text="", bg=C_PANEL, fg=C_ACCENT,
            font=("Microsoft JhengHei UI", 10),
        )
        self._lbl_module.pack(side=tk.LEFT)

        # ── 自動同步間隔列 ────────────────────────────────────────────────
        interval_outer = tk.Frame(self, bg="#1a1a2e", pady=6)
        interval_outer.pack(fill=tk.X)

        tk.Label(
            interval_outer, text="⏱  自動同步間隔：",
            bg="#1a1a2e", fg=C_DIM,
            font=("Microsoft JhengHei UI", 10),
        ).pack(side=tk.LEFT, padx=(14, 4))

        self._interval_btns: dict[int, tk.Button] = {}
        for label, minutes in INTERVAL_OPTIONS:
            btn = tk.Button(
                interval_outer,
                text=label,
                bg="#2d2d3f", fg=C_TEXT,
                activebackground=C_ACCENT,
                font=("Microsoft JhengHei UI", 9),
                relief=tk.FLAT, padx=10, pady=3,
                cursor="hand2",
                command=lambda m=minutes: self._set_interval(m),
            )
            btn.pack(side=tk.LEFT, padx=2)
            self._interval_btns[minutes] = btn

        self._lbl_countdown = tk.Label(
            interval_outer, text="",
            bg="#1a1a2e", fg=C_WARN,
            font=("Consolas", 10),
        )
        self._lbl_countdown.pack(side=tk.LEFT, padx=(14, 4))

        # 初始高亮「關閉」
        self._highlight_interval_btn(0)

        # ── 主區域（左：Log，右：結果表）────────────────────────────────────
        paned = tk.PanedWindow(
            self, orient=tk.HORIZONTAL,
            bg=C_BG, sashwidth=5, sashrelief=tk.FLAT,
        )
        paned.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # 左：Log 輸出
        log_frame = tk.Frame(paned, bg=C_BG)
        paned.add(log_frame, stretch="always", minsize=400)

        # Log 標題列（含錯誤篩選按鈕）
        log_hdr = tk.Frame(log_frame, bg=C_PANEL, pady=4)
        log_hdr.pack(fill=tk.X)

        tk.Label(
            log_hdr, text="Log 輸出",
            bg=C_PANEL, fg=C_DIM,
            font=("Microsoft JhengHei UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=4)

        self._btn_log_filter = tk.Button(
            log_hdr,
            text="⚠  只顯示錯誤 Log",
            bg="#3c2020", fg=C_ERROR,
            activebackground="#5a2020", activeforeground=C_ERROR,
            font=("Microsoft JhengHei UI", 9),
            relief=tk.FLAT, padx=8, pady=2,
            cursor="hand2",
            command=self._toggle_log_filter,
        )
        self._btn_log_filter.pack(side=tk.RIGHT, padx=4)

        self._log_text = scrolledtext.ScrolledText(
            log_frame,
            bg=C_BG, fg=C_TEXT,
            font=("Consolas", 10),
            state=tk.DISABLED,
            relief=tk.FLAT,
            wrap=tk.NONE,
            insertbackground=C_ACCENT,
        )
        self._log_text.pack(fill=tk.BOTH, expand=True)

        hbar = tk.Scrollbar(log_frame, orient=tk.HORIZONTAL,
                            command=self._log_text.xview)
        hbar.pack(fill=tk.X)
        self._log_text.configure(xscrollcommand=hbar.set)

        # 右：同步結果統計表
        tbl_frame = tk.Frame(paned, bg=C_PANEL)
        paned.add(tbl_frame, stretch="never", minsize=560)

        tbl_hdr = tk.Frame(tbl_frame, bg=C_PANEL)
        tbl_hdr.pack(fill=tk.X, padx=6, pady=(6, 2))

        tk.Label(
            tbl_hdr, text="同步結果",
            bg=C_PANEL, fg=C_DIM,
            font=("Microsoft JhengHei UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=4)

        self._btn_filter = tk.Button(
            tbl_hdr,
            text="⚠  只顯示錯誤",
            bg="#3c2020", fg=C_ERROR,
            activebackground="#5a2020", activeforeground=C_ERROR,
            font=("Microsoft JhengHei UI", 9),
            relief=tk.FLAT, padx=8, pady=2,
            cursor="hand2",
            command=self._toggle_filter,
        )
        self._btn_filter.pack(side=tk.RIGHT, padx=4)

        # Treeview 表格
        cols = ("模組", "狀態", "開始時間", "耗時(秒)", "撈取", "寫入", "錯誤", "觸發", "操作")
        self._tree = ttk.Treeview(
            tbl_frame,
            columns=cols,
            show="headings",
            height=22,
        )

        # 欄寬 & 標題
        col_cfg = {
            "模組":    (110, tk.W),
            "狀態":    ( 58, tk.CENTER),
            "開始時間": ( 75, tk.CENTER),
            "耗時(秒)": ( 68, tk.E),
            "撈取":    ( 52, tk.E),
            "寫入":    ( 52, tk.E),
            "錯誤":    ( 48, tk.E),
            "觸發":    ( 52, tk.CENTER),
            "操作":    ( 58, tk.CENTER),
        }
        for col, (w, anchor) in col_cfg.items():
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, minwidth=w, anchor=anchor)

        # Treeview 樣式
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview",
            background=C_PANEL, fieldbackground=C_PANEL,
            foreground=C_TEXT, rowheight=24,
            font=("Microsoft JhengHei UI", 9),
        )
        style.configure("Treeview.Heading",
            background="#2d2d2d", foreground=C_DIM,
            font=("Microsoft JhengHei UI", 9, "bold"),
            relief="flat",
        )
        style.map("Treeview",
            background=[("selected", "#094771")],
            foreground=[("selected", "white")],
        )

        # tag 顏色
        self._tree.tag_configure("success",  foreground=C_SUCCESS)
        self._tree.tag_configure("partial",  foreground=C_WARN)
        self._tree.tag_configure("error",    foreground=C_ERROR)
        self._tree.tag_configure("pending",  foreground=C_DIM)
        self._tree.tag_configure("running",  foreground=C_ACCENT)
        self._tree.tag_configure("disabled", foreground=C_DISABLED)

        # 左鍵點擊（操作欄同步按鈕）
        self._tree.bind("<Button-1>", self._on_tree_left_click)
        # 滑鼠移動（游標提示）
        self._tree.bind("<Motion>", self._on_tree_motion)
        # 右鍵選單綁定
        self._tree.bind("<Button-3>", self._on_tree_right_click)

        vsb = ttk.Scrollbar(tbl_frame, orient=tk.VERTICAL,
                            command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4))
        self._tree.pack(fill=tk.BOTH, expand=True, padx=(4, 0), pady=(0, 4))

        # 初始填滿所有模組列（狀態為「—」，已暫停者標灰）
        self._tree_ids: dict[str, str] = {}
        for name, _, _ in MODULES:
            is_disabled = name in self._disabled_modules
            iid = self._tree.insert(
                "", tk.END,
                values=(name, "⏸ 暫停" if is_disabled else "—",
                        "—", "—", "—", "—", "—", "—",
                        "" if is_disabled else "▶ 同步"),
                tags=("disabled" if is_disabled else "pending",),
            )
            self._tree_ids[name] = iid

        # ── 底部狀態列 ───────────────────────────────────────────────────
        self._lbl_bottom = tk.Label(
            self, text="就緒", bg="#007acc", fg="white",
            font=("Microsoft JhengHei UI", 9),
            anchor=tk.W, padx=8, pady=2,
        )
        self._lbl_bottom.pack(fill=tk.X, side=tk.BOTTOM)

    # ─────────────────────────────────────────────────────────────────────────
    # 即時時鐘
    # ─────────────────────────────────────────────────────────────────────────
    def _tick_clock(self):
        """每秒更新 Header 時鐘標籤。"""
        self._lbl_clock.config(text=datetime.now().strftime("%Y%m%d  %H:%M:%S"))
        self.after(1000, self._tick_clock)

    # ─────────────────────────────────────────────────────────────────────────
    # Logging 設定
    # ─────────────────────────────────────────────────────────────────────────
    def _setup_logging(self):
        fmt = logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self._gui_handler = _GuiLogHandler(self._log_text, buffer=self._log_buffer)
        self._gui_handler.setLevel(logging.DEBUG)

        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = _LOG_DIR / f"{ts}.log"
        self._startup_fh = logging.FileHandler(log_path, encoding="utf-8")
        self._startup_fh.setLevel(logging.DEBUG)
        self._startup_fh.setFormatter(fmt)

        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(self._gui_handler)
        root.addHandler(self._startup_fh)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

        self._lbl_logpath.config(text=f"Log：{log_path.name}")
        self._lbl_bottom.config(text=f"啟動 log：{log_path}")

        logger = logging.getLogger(__name__)
        logger.info("━━━  Portal 同步管理工具 啟動  ━━━")
        logger.info(f"Backend 路徑：{_BACKEND}")
        logger.info(f"Log 資料夾  ：{_LOG_DIR}")
        logger.info(f"本次啟動 Log：{log_path}")

    def _check_env(self):
        logger = logging.getLogger(__name__)
        try:
            from app.core.config import settings
            logger.info(f"資料庫：{settings.DATABASE_URL}")
            logger.info(f"環境  ：{getattr(settings, 'ENV', 'unknown')}")
            logger.info("設定載入成功 ✓")
            self._lbl_status.config(text="就緒 ✓", fg=C_SUCCESS)
        except Exception as exc:
            logger.error(f"設定載入失敗：{exc}")
            self._lbl_status.config(text="⚠ 設定錯誤", fg=C_ERROR)
            self._lbl_bottom.config(text=f"⚠ 無法載入 app.core.config：{exc}")

    def _ensure_db_schema(self):
        """
        確保 SQLite DB Schema 與目前 ORM 模型一致（獨立於 FastAPI lifespan）。

        執行順序（與 main.py lifespan 保持一致）：
          1. import 所有 ORM model → Base.metadata 知道所有表格
          2. hotel_mr_reading 舊版偵測 + DROP（必須在 create_all 之前）
          3. Base.metadata.create_all → 建立尚未存在的表格（不影響已有表格）
          4. hotel_mr_batch 時間欄位補丁（ALTER TABLE，必須在 create_all 之後）
        """
        logger = logging.getLogger(__name__)
        try:
            from app.core.database import Base, engine
            from sqlalchemy import text

            # ── 1. import 所有 ORM models ────────────────────────────────────
            import app.models.room_maintenance          # noqa
            import app.models.inventory                # noqa
            import app.models.room_maintenance_detail  # noqa
            import app.models.room                     # noqa
            import app.models.periodic_maintenance     # noqa
            import app.models.mall_periodic_maintenance  # noqa
            import app.models.full_building_maintenance  # noqa
            import app.models.b4f_inspection           # noqa
            import app.models.rf_inspection            # noqa
            import app.models.b2f_inspection           # noqa
            import app.models.b1f_inspection           # noqa
            import app.models.security_patrol          # noqa
            import app.models.approval                 # noqa
            import app.models.memo                     # noqa
            import app.models.memo_file                # noqa
            import app.models.calendar_event           # noqa
            import app.models.dazhi_repair             # noqa
            import app.models.luqun_repair             # noqa
            import app.models.module_sync_log          # noqa
            import app.models.ragic_app_directory      # noqa
            import app.models.mall_facility_inspection  # noqa
            import app.models.hotel_daily_inspection   # noqa
            import app.models.hotel_meter_readings     # noqa
            import app.models.ihg_room_maintenance     # noqa
            import app.models.menu_config              # noqa
            import app.models.role_permission          # noqa
            import app.models.wiki                     # noqa
            import app.models.purchase_request         # noqa
            import app.models.claim_request            # noqa
            import app.models.nichiyo_purchase_request  # noqa
            import app.models.nichiyo_claim_request    # noqa
            import app.models.ragic_sheet_config       # noqa
            import app.models.other_tasks              # noqa
            import app.models.pm_plan                  # noqa
            import app.models.hotel_routine_pm         # noqa
            import app.models.hotel_routine_pm_schedule  # noqa

            # ── 2. hotel_mr_reading 舊版偵測 → DROP（在 create_all 之前）────
            with engine.connect() as conn:
                try:
                    result = conn.execute(text("PRAGMA table_info(hotel_mr_reading)"))
                    cols = {row[1] for row in result.fetchall()}
                    if cols and "meter_name" in cols:
                        conn.execute(text("DROP TABLE IF EXISTS hotel_mr_reading"))
                        conn.commit()
                        logger.info("[DB] hotel_mr_reading（舊版 per-meter）已刪除，等待重建")
                except Exception as e:
                    logger.warning("[DB] hotel_mr_reading 遷移檢查失敗：%s", e)

            # ── 3. create_all：建立尚未存在的表格 ─────────────────────────────
            Base.metadata.create_all(bind=engine)
            logger.info("[DB] 資料表確認完成（create_all）")

            # ── 4. hotel_mr_batch 時間欄位補丁（ALTER TABLE）────────────────
            new_cols = [
                ("start_time", "TEXT NOT NULL DEFAULT ''"),
                ("end_time",   "TEXT NOT NULL DEFAULT ''"),
                ("work_hours", "TEXT NOT NULL DEFAULT ''"),
            ]
            with engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(hotel_mr_batch)"))
                existing = {row[1] for row in result.fetchall()}
                for col, typedef in new_cols:
                    if col not in existing:
                        conn.execute(
                            text(f"ALTER TABLE hotel_mr_batch ADD COLUMN {col} {typedef}")
                        )
                        conn.commit()
                        logger.info("[DB] hotel_mr_batch.%s 欄位已新增", col)

            # ── 5. calendar_custom_events.zone 欄位補丁（區域別）─────────────
            with engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(calendar_custom_events)"))
                existing = {row[1] for row in result.fetchall()}
                if "zone" not in existing:
                    conn.execute(text(
                        "ALTER TABLE calendar_custom_events "
                        "ADD COLUMN zone TEXT NOT NULL DEFAULT '其它'"
                    ))
                    conn.commit()
                    logger.info("[DB] calendar_custom_events.zone 欄位已新增")

            logger.info("[DB] Schema 確認完成 ✓")

        except Exception as exc:
            logger.error("[DB] Schema 確認失敗：%s", exc, exc_info=True)
            self._lbl_bottom.config(text=f"⚠ DB Schema 確認失敗：{exc}")

    # ─────────────────────────────────────────────────────────────────────────
    # 自動同步間隔
    # ─────────────────────────────────────────────────────────────────────────
    def _highlight_interval_btn(self, active_minutes: int):
        for m, btn in self._interval_btns.items():
            if m == active_minutes:
                btn.config(bg=C_ACCENT, fg="white", font=("Microsoft JhengHei UI", 9, "bold"))
            else:
                btn.config(bg="#2d2d3f", fg=C_TEXT, font=("Microsoft JhengHei UI", 9, "normal"))

    def _set_interval(self, minutes: int):
        # 取消舊計時器
        if self._auto_timer is not None:
            self._auto_timer.cancel()
            self._auto_timer = None
        if self._countdown_job is not None:
            self.after_cancel(self._countdown_job)
            self._countdown_job = None

        self._auto_interval = minutes
        self._highlight_interval_btn(minutes)

        if minutes == 0:
            self._next_sync_at = None
            self._lbl_countdown.config(text="")
            logging.getLogger(__name__).info("自動同步已關閉")
        else:
            logging.getLogger(__name__).info(
                f"自動同步間隔設定為 {minutes} 分鐘"
            )
            self._schedule_next_auto()

    def _schedule_next_auto(self):
        """排定下一次自動同步（minutes 秒後觸發）。"""
        if self._auto_interval <= 0:
            return
        delay_sec = self._auto_interval * 60
        import time as _time
        from datetime import timedelta
        self._next_sync_at = datetime.now() + timedelta(seconds=delay_sec)
        self._auto_timer = threading.Timer(delay_sec, self._auto_sync_fire)
        self._auto_timer.daemon = True
        self._auto_timer.start()
        self._update_countdown()

    def _update_countdown(self):
        if self._next_sync_at is None or self._auto_interval == 0:
            return
        remaining = (self._next_sync_at - datetime.now()).total_seconds()
        if remaining > 0:
            m, s = divmod(int(remaining), 60)
            self._lbl_countdown.config(
                text=f"下次自動同步：{m:02d}:{s:02d}"
            )
            self._countdown_job = self.after(1000, self._update_countdown)
        else:
            self._lbl_countdown.config(text="自動同步啟動中…")

    def _auto_sync_fire(self):
        """timer callback（在背景執行緒呼叫）。"""
        logging.getLogger(__name__).info("⏱  自動同步觸發")
        self.after(0, self._trigger_sync, "排程")

    # ─────────────────────────────────────────────────────────────────────────
    # 同步控制
    # ─────────────────────────────────────────────────────────────────────────
    def _update_sync_btn_label(self):
        """更新同步按鈕標題，顯示有效/總模組數。"""
        active = len(MODULES) - len(self._disabled_modules)
        total  = len(MODULES)
        suffix = f"（{active}/{total}）" if self._disabled_modules else ""
        self._btn_sync.config(text=f"▶  立即同步所有模組{suffix}")

    def _on_sync(self):
        self._trigger_sync("手動")

    def _trigger_sync(self, triggered_by: str = "手動"):
        if self._running:
            return
        self._running = True
        self._btn_sync.config(state=tk.DISABLED, text="同步中…")
        self._progress.start(12)
        self._lbl_status.config(text="同步中…", fg=C_ACCENT)
        # 重置表格狀態（已暫停模組保持灰色，不改為「⟳」）
        for name in self._tree_ids:
            if name in self._disabled_modules:
                self._tree.item(
                    self._tree_ids[name],
                    values=(name, "⏸ 暫停", "—", "—", "—", "—", "—", "—", ""),
                    tags=("disabled",),
                )
            else:
                self._tree.item(
                    self._tree_ids[name],
                    values=(name, "⟳", "—", "—", "—", "—", "—", triggered_by, "⟳"),
                    tags=("running",),
                )
        threading.Thread(
            target=self._sync_thread,
            args=(triggered_by,),
            daemon=True,
        ).start()

    def _sync_thread(self, triggered_by: str):
        logger = logging.getLogger(__name__)

        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = _LOG_DIR / f"{ts}_manual.log"
        fmt      = logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)

        root      = logging.getLogger()
        sa_logger = logging.getLogger("sqlalchemy.engine")
        prev_sa   = sa_logger.level
        root.addHandler(fh)
        sa_logger.setLevel(logging.INFO)

        self.after(0, self._lbl_logpath.config, {"text": f"Log：{log_path.name}"})
        self.after(0, self._lbl_bottom.config,  {"text": f"同步中… → {log_path}"})
        skipped_cnt = len(self._disabled_modules)
        active_cnt  = len(MODULES) - skipped_cnt
        logger.info(
            f"━━━  同步開始（{triggered_by}）"
            f"  有效：{active_cnt}  暫停：{skipped_cnt}  ━━━  log：{log_path}"
        )

        results: list[dict] = []
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_all_modules(results, triggered_by))
        except Exception as exc:
            logger.error(f"同步主流程異常：{exc}", exc_info=True)
        finally:
            loop.close()
            sa_logger.setLevel(prev_sa)
            root.removeHandler(fh)
            fh.close()

        ok      = sum(1 for r in results if r["status"] == "success")
        partial = sum(1 for r in results if r["status"] == "partial")
        err     = sum(1 for r in results if r["status"] == "error")
        logger.info(f"━━━  同步完成 ── 成功：{ok}  部分：{partial}  失敗：{err}  ━━━")

        self.after(0, self._on_sync_done, ok, partial, err, log_path, results)

        # 若自動同步開啟，排定下一次
        if self._auto_interval > 0:
            self.after(0, self._schedule_next_auto)

    async def _run_all_modules(self, results: list[dict], triggered_by: str):
        logger = logging.getLogger(__name__)
        # 只計算「有效」模組數量
        active_modules = [(n, m, f) for n, m, f in MODULES
                          if n not in self._disabled_modules]
        total = len(active_modules)

        for i, (name, mod_path, func_name) in enumerate(active_modules, 1):
            self.after(0, self._lbl_module.config,
                       {"text": f"[{i}/{total}]  {name}"})
            self.after(0, self._lbl_status.config, {"text": f"{name}…"})

            logger.info(f"[{i:02d}/{total}] 開始：{name}")
            t0       = datetime.now()
            status   = "success"
            fetched  = upserted = err_count = 0

            try:
                # 2026-07-15：跨行程鎖，避免與後端排程同時寫入 portal.db
                from app.core.sync_lock import async_sync_lock

                mod  = importlib.import_module(mod_path)
                func = getattr(mod, func_name)
                async with async_sync_lock(name):
                    if inspect.iscoroutinefunction(func):
                        result = await func()
                    else:
                        result = await asyncio.to_thread(func)

                duration = round((datetime.now() - t0).total_seconds(), 2)

                if isinstance(result, dict):
                    fetched   = result.get("fetched",  0)
                    upserted  = result.get("upserted", 0)
                    _e        = result.get("errors",   0)
                    # 相容 int（計數）或 list（明細）兩種格式
                    err_count = _e if isinstance(_e, int) else len(_e)
                else:
                    err_count = 0

                if err_count > 0:
                    status = "partial"
                    logger.warning(
                        f"  ✗ {name}：fetched={fetched}, "
                        f"upserted={upserted}, errors={err_count}, {duration}s"
                    )
                else:
                    logger.info(
                        f"  ✓ {name}：fetched={fetched}, "
                        f"upserted={upserted}, {duration}s"
                    )

            except Exception as exc:
                duration  = round((datetime.now() - t0).total_seconds(), 2)
                status    = "error"
                err_count = 1
                logger.error(f"  ✗ {name} 異常：{exc}", exc_info=True)

            results.append({
                "name": name, "status": status,
                "duration": duration, "fetched": fetched,
                "upserted": upserted, "err_count": err_count,
                "triggered_by": triggered_by,
            })

            # 更新表格
            status_txt = {"success": "✓ 成功", "partial": "~ 部分", "error": "✗ 失敗"}[status]
            start_str  = t0.strftime("%H:%M:%S")
            self.after(0, self._update_tree_row, name, status, status_txt,
                       start_str, f"{duration:.1f}", fetched, upserted,
                       err_count, triggered_by)

    def _update_tree_row(self, name: str, tag: str, status_txt: str,
                         start_str: str, dur: str,
                         fetched: int, upserted: int, err_count: int,
                         triggered_by: str, sync_btn: str = "▶ 同步"):
        iid = self._tree_ids.get(name)
        if iid:
            err_disp = str(err_count) if err_count else "0"
            self._tree.item(
                iid,
                values=(name, status_txt, start_str, dur,
                        fetched, upserted, err_disp, triggered_by, sync_btn),
                tags=(tag,),
            )

    def _on_sync_done_single(self, name: str, tag: str, status_txt: str,
                             start_str: str, dur: str,
                             fetched: int, upserted: int, err_count: int):
        """單一模組同步完成後的 UI 更新。"""
        self._single_syncing.discard(name)
        self._update_tree_row(
            name, tag, status_txt, start_str, dur,
            fetched, upserted, err_count, "手動",
            sync_btn="▶ 同步",
        )

    def _on_sync_done(self, ok: int, partial: int, err: int,
                      log_path: pathlib.Path, results: list[dict]):
        self._running = False
        self._btn_sync.config(state=tk.NORMAL)
        self._update_sync_btn_label()
        self._progress.stop()
        self._lbl_module.config(text="")

        # 儲存本次結果供篩選使用
        self._last_results = results

        # 若篩選模式開啟，自動重新套用（同步後立刻更新）
        if self._filter_active:
            self._apply_filter(active=True)

        # 更新篩選按鈕提示（顯示錯誤/部分數量）
        bad = err + partial
        if bad > 0:
            self._btn_filter.config(
                text=f"⚠  只顯示錯誤（{bad}）",
                state=tk.NORMAL,
            )
        else:
            self._btn_filter.config(
                text="✓  無錯誤",
                bg="#1a2e1a", fg=C_SUCCESS,
                state=tk.DISABLED,
            )
            # 若原本篩選中，自動關閉
            if self._filter_active:
                self._filter_active = False

        ts = datetime.now().strftime("%H:%M:%S")
        if err == 0 and partial == 0:
            self._lbl_status.config(text=f"✓ 完成  {ts}", fg=C_SUCCESS)
            self._lbl_bottom.config(
                text=f"同步完成 ── {ok} 個模組全部成功  ({ts})  ← {log_path}"
            )
        else:
            self._lbl_status.config(
                text=f"⚠ 完成  {ts}（失敗：{err}）", fg=C_WARN
            )
            self._lbl_bottom.config(
                text=(f"同步完成 ── 成功：{ok}  部分：{partial}  "
                      f"失敗：{err}  ({ts})  ← {log_path}")
            )
        self._lbl_logpath.config(text=f"Log：{log_path.name}")

    # ── 單一模組同步（操作欄點擊）────────────────────────────────────────────
    def _on_tree_left_click(self, event: tk.Event):
        """偵測是否點擊「操作」欄的「▶ 同步」，若是則觸發單一模組同步。"""
        region = self._tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col_id = self._tree.identify_column(event.x)
        # 找出欄位名稱（col_id 形如 "#9"）
        cols = self._tree["columns"]
        try:
            col_idx = int(col_id.lstrip("#")) - 1
            col_name = cols[col_idx]
        except (ValueError, IndexError):
            return
        if col_name != "操作":
            return
        iid = self._tree.identify_row(event.y)
        if not iid:
            return
        name = self._tree.item(iid, "values")[0]
        if not name:
            return
        # 已暫停、或全體同步中、或本模組正在單同步 → 忽略
        if (name in self._disabled_modules
                or self._running
                or name in self._single_syncing):
            return
        self._trigger_single_module_sync(name)

    def _on_tree_motion(self, event: tk.Event):
        """滑鼠移到「操作」欄且可點擊時，游標顯示 hand2。"""
        region = self._tree.identify_region(event.x, event.y)
        if region != "cell":
            self._tree.config(cursor="")
            return
        col_id = self._tree.identify_column(event.x)
        cols = self._tree["columns"]
        try:
            col_idx = int(col_id.lstrip("#")) - 1
            col_name = cols[col_idx]
        except (ValueError, IndexError):
            self._tree.config(cursor="")
            return
        if col_name != "操作":
            self._tree.config(cursor="")
            return
        iid = self._tree.identify_row(event.y)
        if not iid:
            self._tree.config(cursor="")
            return
        name = self._tree.item(iid, "values")[0]
        if (name in self._disabled_modules
                or self._running
                or name in self._single_syncing):
            self._tree.config(cursor="")
        else:
            self._tree.config(cursor="hand2")

    def _trigger_single_module_sync(self, name: str):
        """觸發單一模組同步（背景執行）。"""
        self._single_syncing.add(name)
        # 更新操作欄顯示
        iid = self._tree_ids.get(name)
        if iid:
            vals = list(self._tree.item(iid, "values"))
            vals[8] = "⟳"
            self._tree.item(iid, values=vals)
        logging.getLogger(__name__).info("▶ 單一同步開始：%s", name)
        threading.Thread(
            target=self._single_module_thread,
            args=(name,),
            daemon=True,
        ).start()

    def _single_module_thread(self, name: str):
        """單一模組同步執行緒（背景）。"""
        logger = logging.getLogger(__name__)
        # 找對應的 service module/function
        entry = next(((m, f) for n, m, f in MODULES if n == name), None)
        if entry is None:
            logger.error("找不到模組定義：%s", name)
            self._single_syncing.discard(name)
            return

        mod_path, func_name = entry
        t0 = datetime.now()
        status = "success"
        fetched = upserted = err_count = 0
        duration = 0.0

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 2026-07-15：跨行程鎖，避免與後端排程同時寫入 portal.db
            from app.core.sync_lock import sync_lock

            mod  = importlib.import_module(mod_path)
            func = getattr(mod, func_name)
            with sync_lock(name):
                if inspect.iscoroutinefunction(func):
                    result = loop.run_until_complete(func())
                else:
                    result = func()
            duration = round((datetime.now() - t0).total_seconds(), 2)
            if isinstance(result, dict):
                fetched   = result.get("fetched",  0)
                upserted  = result.get("upserted", 0)
                _e        = result.get("errors",   0)
                # 相容 int（計數）或 list（明細）兩種格式
                err_count = _e if isinstance(_e, int) else len(_e)
                if err_count > 0:
                    status = "partial"
        except Exception as exc:
            duration  = round((datetime.now() - t0).total_seconds(), 2)
            status    = "error"
            err_count = 1
            logger.error("單一同步 ✗ %s：%s", name, exc, exc_info=True)
        finally:
            loop.close()

        status_txt = {"success": "✓ 成功", "partial": "~ 部分", "error": "✗ 失敗"}[status]
        start_str  = t0.strftime("%H:%M:%S")
        logger.info(
            "單一同步 %s %s fetched=%d upserted=%d dur=%.1fs",
            name, status_txt, fetched, upserted, duration,
        )

        self.after(
            0, self._on_sync_done_single,
            name, status, status_txt, start_str,
            f"{duration:.1f}", fetched, upserted, err_count,
        )

    # ── 錯誤篩選 ─────────────────────────────────────────────────────────────
    def _toggle_filter(self):
        """切換「只顯示錯誤」/「全部顯示」。"""
        self._filter_active = not self._filter_active
        self._apply_filter(active=self._filter_active)

    def _apply_filter(self, active: bool):
        """
        active=True  → detach 所有非 error/partial 的列（只留錯誤）
        active=False → reattach 所有列，按原始模組順序排列
        """
        if active:
            # 先確保全部都在（以免重複 detach）
            self._apply_filter(active=False)
            # 取得這次有錯誤的模組名稱集合
            error_names = {
                r["name"] for r in self._last_results
                if r["status"] in ("error", "partial")
            }
            for name, iid in self._tree_ids.items():
                if name not in error_names:
                    self._tree.detach(iid)
            # 更新按鈕外觀（啟用中）
            self._btn_filter.config(
                bg=C_ERROR, fg="white",
                text=f"✕  取消篩選（顯示全部）",
            )
        else:
            # 按 MODULES 原始順序 reattach 所有列
            for idx, (name, _, _) in enumerate(MODULES):
                iid = self._tree_ids.get(name)
                if iid:
                    # reattach 若已在樹中不會出錯（tkinter 會忽略）
                    try:
                        self._tree.reattach(iid, "", idx)
                    except tk.TclError:
                        pass
            # 更新按鈕外觀（未啟用）
            bad = sum(
                1 for r in self._last_results
                if r["status"] in ("error", "partial")
            )
            if bad > 0:
                self._btn_filter.config(
                    bg="#3c2020", fg=C_ERROR,
                    text=f"⚠  只顯示錯誤（{bad}）",
                    state=tk.NORMAL,
                )
            else:
                self._btn_filter.config(
                    text="⚠  只顯示錯誤",
                    bg="#3c2020", fg=C_ERROR,
                    state=tk.NORMAL,
                )

    # ── 模組暫停 / 恢復 ──────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    # Config 讀寫（disabled_modules + module_schedules 合併存一個 JSON）
    # ─────────────────────────────────────────────────────────────────────────
    def _load_config(self) -> dict:
        """讀取 sync_tool_config.json，回傳完整 dict。"""
        try:
            if _CONFIG_PATH.exists():
                return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_config(self, data: dict):
        """將 config dict 寫回 sync_tool_config.json。"""
        try:
            _CONFIG_PATH.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logging.getLogger(__name__).warning("無法儲存設定：%s", exc)

    @staticmethod
    def _load_disabled() -> set[str]:
        """從 sync_tool_config.json 讀取暫停模組清單。"""
        try:
            if _CONFIG_PATH.exists():
                data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
                return set(data.get("disabled_modules", []))
        except Exception:
            pass
        return set()

    def _save_disabled(self):
        """將目前暫停清單合併寫回 sync_tool_config.json（保留其他欄位）。"""
        try:
            data = self._load_config()
            data["disabled_modules"] = sorted(self._disabled_modules)
            self._save_config(data)
        except Exception as exc:
            logging.getLogger(__name__).warning("無法儲存暫停設定：%s", exc)

    def get_module_schedules(self) -> dict:
        """讀取 module_schedules 設定，回傳 dict[module_name, schedule_dict]。"""
        return self._load_config().get("module_schedules", {})

    def save_module_schedules(self, schedules: dict):
        """將 module_schedules 合併寫回 config（保留 disabled_modules 等其他欄位）。"""
        data = self._load_config()
        data["module_schedules"] = schedules
        self._save_config(data)

    def _on_tree_right_click(self, event: tk.Event):
        """右鍵點擊 Treeview 行 → 彈出暫停/恢復選單。"""
        iid = self._tree.identify_row(event.y)
        if not iid:
            return
        name = self._tree.item(iid, "values")[0]
        if not name:
            return

        menu = tk.Menu(self, tearoff=0,
                       bg=C_PANEL, fg=C_TEXT,
                       activebackground="#094771", activeforeground="white",
                       relief=tk.FLAT, bd=1)

        if name in self._disabled_modules:
            menu.add_command(
                label=f"▶  恢復同步：{name}",
                command=lambda: self._set_module_disabled(name, False),
            )
        else:
            menu.add_command(
                label=f"⏸  暫停同步：{name}",
                command=lambda: self._set_module_disabled(name, True),
            )

        menu.add_separator()
        if self._disabled_modules:
            menu.add_command(
                label="▶  恢復全部已暫停模組",
                command=self._enable_all_modules,
            )

        menu.tk_popup(event.x_root, event.y_root)

    def _set_module_disabled(self, name: str, disabled: bool):
        """設定單一模組的暫停/啟用狀態，並更新 UI 和設定檔。"""
        iid = self._tree_ids.get(name)
        if not iid:
            return

        if disabled:
            self._disabled_modules.add(name)
            self._tree.item(
                iid,
                values=(name, "⏸ 暫停", "—", "—", "—", "—", "—", "—", ""),
                tags=("disabled",),
            )
            logging.getLogger(__name__).info("⏸  已暫停模組：%s", name)
        else:
            self._disabled_modules.discard(name)
            self._tree.item(
                iid,
                values=(name, "—", "—", "—", "—", "—", "—", "—", "▶ 同步"),
                tags=("pending",),
            )
            logging.getLogger(__name__).info("▶  已恢復模組：%s", name)

        self._save_disabled()
        self._update_sync_btn_label()

    def _enable_all_modules(self):
        """恢復全部已暫停模組。"""
        for name in list(self._disabled_modules):
            self._set_module_disabled(name, False)

    # ── Log 錯誤篩選 ─────────────────────────────────────────────────────────
    def _toggle_log_filter(self):
        """切換 Log 面板「只顯示錯誤」/「顯示全部」。"""
        self._log_filter_active = not self._log_filter_active
        self._apply_log_filter(active=self._log_filter_active)

    def _apply_log_filter(self, active: bool):
        """
        active=True  → ScrolledText 只重繪 WARNING / ERROR / CRITICAL 條目
        active=False → ScrolledText 重繪所有 buffer 條目
        """
        self._log_filter_active = active
        self._log_text.config(state=tk.NORMAL)
        self._log_text.delete("1.0", tk.END)

        entries = self._log_buffer
        if active:
            entries = [(m, c, lv) for (m, c, lv) in entries
                       if lv >= logging.WARNING]
            self._btn_log_filter.config(
                bg=C_ERROR, fg="white",
                text="✕  取消篩選（顯示全部 Log）",
            )
        else:
            self._btn_log_filter.config(
                bg="#3c2020", fg=C_ERROR,
                text="⚠  只顯示錯誤 Log",
            )

        for msg, color, _ in entries:
            tag = f"c{color[1:]}"
            self._log_text.tag_config(tag, foreground=color)
            self._log_text.insert(tk.END, msg, tag)

        self._log_text.see(tk.END)
        self._log_text.config(state=tk.DISABLED)

    # ── 寄送報修未完成報表 ───────────────────────────────────────────────────
    def _on_send_repair_report(self):
        """點擊「寄送報修未完成報表」按鈕。"""
        if self._running:
            logging.getLogger(__name__).warning("同步中，請稍後再寄送報表")
            return
        self._btn_send_repair.config(state=tk.DISABLED, text="寄送中…")
        self._lbl_status.config(text="寄送報修報表…", fg=C_ACCENT)
        threading.Thread(target=self._send_repair_report_thread, daemon=True).start()

    def _send_repair_report_thread(self):
        """
        背景執行 force_send_now（強制寄送，不檢查 is_enabled / 不防重複）。
        完成後還原按鈕狀態並在 Log 顯示結果。
        """
        logger = logging.getLogger(__name__)
        now = datetime.now()
        year, month = now.year, now.month
        logger.info("━━━  手動觸發：寄送報修未完成報表（%d年%02d月）  ━━━", year, month)
        t0 = datetime.now()
        try:
            from app.core.database import SessionLocal as _SL
            from app.services.repair_report_service import force_send_now as _send
            with _SL() as db:
                result = _send(db, year=year, month=month)
            dur = round((datetime.now() - t0).total_seconds(), 1)
            sent, failed = result.get("sent", 0), result.get("failed", 0)
            if failed == 0:
                logger.info("✓ 報修未完成報表寄送完成：sent=%d failed=%d（%.1fs）", sent, failed, dur)
            else:
                logger.warning("⚠ 報修未完成報表寄送部分失敗：sent=%d failed=%d（%.1fs）", sent, failed, dur)
            self.after(0, self._on_send_repair_done, failed == 0, dur)
        except Exception as exc:
            dur = round((datetime.now() - t0).total_seconds(), 1)
            logger.error("✗ 寄送失敗：%s", exc, exc_info=True)
            self.after(0, self._on_send_repair_done, False, dur)

    def _on_send_repair_done(self, success: bool, dur: float):
        """寄送完成後更新 UI（必須在主執行緒呼叫）。"""
        ts = datetime.now().strftime("%H:%M:%S")
        if success:
            self._lbl_status.config(text=f"✓ 報表寄送完成  {ts}", fg=C_SUCCESS)
            self._lbl_bottom.config(text=f"報修未完成報表寄送完成（{dur:.1f}s）  {ts}")
        else:
            self._lbl_status.config(text=f"⚠ 報表寄送失敗  {ts}", fg=C_ERROR)
            self._lbl_bottom.config(text=f"⚠ 報修未完成報表寄送失敗，請查看 Log  {ts}")
        self._btn_send_repair.config(state=tk.NORMAL, text="📧 寄送報修未完成報表")

    # ── 排程執行緒 ───────────────────────────────────────────────────────────
    def _scheduler_loop(self):
        """
        背景排程主迴圈，每 30 秒 tick 一次。
        讀取 sync_tool_config.json 的 module_schedules，依模式觸發任務。
        """
        import time
        logger = logging.getLogger(__name__)
        logger.info("[排程] 排程執行緒啟動（每 30 秒檢查一次）")
        while self._sched_thread_running:
            try:
                self._scheduler_tick()
            except Exception as exc:
                logger.error("[排程] tick 發生例外：%s", exc, exc_info=True)
            time.sleep(30)
        logger.info("[排程] 排程執行緒結束")

    def _scheduler_tick(self):
        """
        單次排程檢查：
          - interval 模式：距上次執行已超過設定分鐘數 → 觸發
          - daily 模式：目前時間在設定 HH:MM 同一分鐘內、且今天尚未觸發 → 觸發
        """
        schedules = self.get_module_schedules()
        if not schedules:
            return

        now   = datetime.now()
        today = now.date()
        logger = logging.getLogger(__name__)

        for module_name, cfg in schedules.items():
            mode = cfg.get("mode", "off")
            if mode == "off":
                continue

            if mode == "interval":
                ivl = cfg.get("interval_minutes", 0)
                if ivl <= 0:
                    continue
                # 全體同步中或此模組正在單獨同步中 → 跳過，下次再試
                if self._running or module_name in self._single_syncing:
                    continue
                last = self._sched_last_interval.get(module_name)
                elapsed = (now - last).total_seconds() if last else float("inf")
                if elapsed >= ivl * 60:
                    self._sched_last_interval[module_name] = now
                    logger.info("[排程] ⏱ 間隔觸發：%s（%d 分鐘）", module_name, ivl)
                    self.after(0, self._lbl_bottom.config,
                               {"text": f"[排程] ⏱ 觸發：{module_name}"})
                    self._trigger_scheduled(module_name)

            elif mode == "daily":
                time_str = cfg.get("time", "")
                if not time_str:
                    continue
                try:
                    h, m = map(int, time_str.split(":"))
                except ValueError:
                    logger.warning("[排程] 指定時間格式錯誤（%s）：%s", module_name, time_str)
                    continue
                # 目前時間在目標分鐘內，且 (今天, 設定時間) 組合尚未觸發
                # ⚠️ dedup key 包含 time_str：改了時間後同一天仍可重新觸發
                done_key = self._sched_daily_done.get(module_name)
                if (now.hour == h and now.minute == m
                        and done_key != (today, time_str)):
                    self._sched_daily_done[module_name] = (today, time_str)
                    logger.info("[排程] 🕐 每日觸發：%s（設定 %s）", module_name, time_str)
                    self.after(0, self._lbl_bottom.config,
                               {"text": f"[排程] 🕐 觸發：{module_name}（{time_str}）"})
                    self._trigger_scheduled(module_name)

            elif mode == "weekly":
                time_str = cfg.get("time", "07:00")
                try:
                    weekday = int(cfg.get("weekday", 0))  # 0=週一, 6=週日
                    h, m = map(int, time_str.split(":"))
                except (ValueError, TypeError):
                    logger.warning("[排程] 每週設定格式錯誤（%s）：weekday=%s time=%s",
                                   module_name, cfg.get("weekday"), time_str)
                    continue
                _WD_NAMES = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
                wd_name   = _WD_NAMES[weekday] if 0 <= weekday <= 6 else f"weekday={weekday}"
                # dedup key 格式與 daily 不同，避免互相覆蓋
                dedup_val = f"weekly:{weekday}:{time_str}"
                done_key  = self._sched_daily_done.get(module_name)
                if (now.weekday() == weekday
                        and now.hour == h and now.minute == m
                        and done_key != (today, dedup_val)):
                    self._sched_daily_done[module_name] = (today, dedup_val)
                    logger.info("[排程] 📅 每週觸發：%s（%s %s）", module_name, wd_name, time_str)
                    self.after(0, self._lbl_bottom.config,
                               {"text": f"[排程] 📅 觸發：{module_name}（{wd_name} {time_str}）"})
                    self._trigger_scheduled(module_name)

    def _trigger_scheduled(self, module_name: str):
        """將排程任務加入 FIFO 佇列，由 runner thread 依序執行（避免 SQLite 競爭）。"""
        logger = logging.getLogger(__name__)
        if module_name == MAIL_KEY:
            self._task_queue.put((module_name, self._scheduled_mail_thread, ()))
        else:
            if module_name in self._disabled_modules:
                logger.info("[排程] 模組已暫停，跳過：%s", module_name)
                return
            self._task_queue.put((module_name, self._scheduled_sync_thread, (module_name,)))
        qsize = self._task_queue.qsize()
        logger.info("[排程] 加入佇列：%s（佇列共 %d 項）", module_name, qsize)
        self.after(0, self._lbl_bottom.config,
                   {"text": f"[排程] 佇列：{module_name}（共 {qsize} 項待執行）"})

    def _task_runner_loop(self):
        """
        FIFO 任務 runner（獨立 thread，永久執行）。
        scheduler tick 只負責入佇列，本 thread 依序取出並執行，
        確保同一時間絕不會有兩個同步/寄信任務並發，避免 SQLite 鎖定。
        """
        logger = logging.getLogger(__name__)
        logger.info("[排程] 任務 runner 執行緒啟動")
        while self._sched_thread_running:
            try:
                module_name, func, args = self._task_queue.get(timeout=1)
                remaining = self._task_queue.qsize()
                logger.info("[排程] ▶ 開始執行：%s（佇列剩 %d 項）",
                            module_name, remaining)
                self.after(0, self._lbl_bottom.config,
                           {"text": f"[排程] ▶ 執行中：{module_name}（佇列剩 {remaining} 項）"})
                try:
                    func(*args)
                except Exception as exc:
                    logger.error("[排程] 執行例外 %s：%s", module_name, exc, exc_info=True)
                finally:
                    self._task_queue.task_done()
            except queue.Empty:
                pass   # 沒有任務，繼續等
        logger.info("[排程] 任務 runner 執行緒結束")

    def _scheduled_sync_thread(self, name: str):
        """排程觸發的單一模組同步（背景執行緒）。"""
        import time as _time
        logger = logging.getLogger(__name__)
        entry = next(((m, f) for n, m, f in MODULES if n == name), None)
        if entry is None:
            logger.error("[排程] 找不到模組定義：%s", name)
            return

        # 若全體同步進行中，最多等 60 秒後放棄
        wait = 0
        while self._running and wait < 60:
            _time.sleep(5); wait += 5
        if self._running:
            logger.warning("[排程] 等待逾時，略過：%s", name)
            return

        self._single_syncing.add(name)
        mod_path, func_name = entry
        t0       = datetime.now()
        status   = "success"
        fetched  = upserted = err_count = 0
        duration = 0.0

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 2026-07-15：跨行程鎖，避免與後端排程同時寫入 portal.db
            from app.core.sync_lock import sync_lock

            mod  = importlib.import_module(mod_path)
            func = getattr(mod, func_name)
            with sync_lock(name):
                if inspect.iscoroutinefunction(func):
                    result = loop.run_until_complete(func())
                else:
                    result = func()
            duration = round((datetime.now() - t0).total_seconds(), 2)
            if isinstance(result, dict):
                fetched   = result.get("fetched",  0)
                upserted  = result.get("upserted", 0)
                _e        = result.get("errors",   0)
                err_count = _e if isinstance(_e, int) else len(_e)
                if err_count > 0:
                    status = "partial"
        except Exception as exc:
            duration  = round((datetime.now() - t0).total_seconds(), 2)
            status    = "error"
            err_count = 1
            logger.error("[排程] 同步失敗 %s：%s", name, exc, exc_info=True)
        finally:
            loop.close()

        status_txt = {"success": "✓ 成功", "partial": "~ 部分", "error": "✗ 失敗"}[status]
        logger.info("[排程] 同步完成 %s %s fetched=%d upserted=%d dur=%.1fs",
                    name, status_txt, fetched, upserted, duration)
        start_str = t0.strftime("%H:%M:%S")
        self.after(
            0, self._on_sync_done_single,
            name, status, status_txt, start_str,
            f"{duration:.1f}", fetched, upserted, err_count,
        )

    def _scheduled_mail_thread(self):
        """排程觸發的報修報表寄信（背景執行緒）。"""
        logger = logging.getLogger(__name__)
        now = datetime.now()
        year, month = now.year, now.month
        logger.info("[排程] 📧 報修未完成報表寄信觸發（%d年%02d月）", year, month)
        t0 = datetime.now()
        try:
            from app.core.database import SessionLocal as _SL
            from app.services.repair_report_service import force_send_now as _send
            with _SL() as db:
                result = _send(db, year=year, month=month)
            dur  = round((datetime.now() - t0).total_seconds(), 1)
            sent = result.get("sent", 0)
            fail = result.get("failed", 0)
            if fail == 0:
                logger.info("[排程] 📧 寄信完成：sent=%d（%.1fs）", sent, dur)
                self.after(0, self._lbl_bottom.config,
                           {"text": f"[排程] 📧 報修報表寄信完成 sent={sent}（{dur:.1f}s）"})
            else:
                logger.warning("[排程] 📧 寄信部分失敗：sent=%d failed=%d（%.1fs）",
                               sent, fail, dur)
                self.after(0, self._lbl_bottom.config,
                           {"text": f"⚠ [排程] 📧 報修報表寄信部分失敗 sent={sent} failed={fail}"})
        except Exception as exc:
            dur = round((datetime.now() - t0).total_seconds(), 1)
            logger.error("[排程] 📧 寄信失敗：%s", exc, exc_info=True)
            self.after(0, self._lbl_bottom.config,
                       {"text": "⚠ [排程] 📧 報修報表寄信失敗，請查看 Log"})

    # ── 排程設定對話框 ────────────────────────────────────────────────────────
    def _open_schedule_dialog(self):
        """開啟「每模組排程設定」對話框。"""
        dlg = tk.Toplevel(self)
        dlg.title("⚙ 排程設定")
        dlg.configure(bg=C_BG)
        dlg.resizable(True, True)
        dlg.grab_set()   # modal

        # ── 說明 ──────────────────────────────────────────────────────────────
        tk.Label(
            dlg,
            text="各模組可獨立設定排程模式。設定後由 sync_tool 的排程 thread 執行。",
            bg=C_BG, fg=C_DIM,
            font=("Microsoft JhengHei UI", 9),
            wraplength=700,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, padx=16, pady=(10, 0))

        # ── 可捲動區域 ────────────────────────────────────────────────────────
        outer = tk.Frame(dlg, bg=C_BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        canvas = tk.Canvas(outer, bg=C_BG, highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=C_BG)
        canvas_win = canvas.create_window((0, 0), window=inner, anchor=tk.NW)

        def _on_inner_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_win, width=event.width)

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # 滑鼠滾輪支援
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ── 表頭 ──────────────────────────────────────────────────────────────
        hdr_cfg = [
            ("模組名稱",         220, tk.W),
            ("模式",             240, tk.CENTER),
            ("間隔（分鐘）",     130, tk.CENTER),
            ("星期",             110, tk.CENTER),
            ("時間（HH:MM）",   130, tk.CENTER),
        ]
        for col_idx, (text, width, anchor) in enumerate(hdr_cfg):
            lbl = tk.Label(
                inner, text=text,
                bg="#2d2d2d", fg=C_DIM,
                font=("Microsoft JhengHei UI", 9, "bold"),
                width=width // 10, anchor=anchor,
                relief=tk.FLAT, padx=6, pady=4,
            )
            lbl.grid(row=0, column=col_idx, padx=2, pady=(0, 2), sticky=tk.EW)

        # ── 載入已儲存設定 ────────────────────────────────────────────────────
        saved = self.get_module_schedules()

        # 排程項目 = 所有同步模組 + 報修報表寄信（使用 module-level MAIL_KEY）
        sched_items = [(name,) for name, _, _ in MODULES] + [(MAIL_KEY,)]

        INTERVAL_CHOICES = [
            ("關閉（僅手動）", 0),
            ("15 分", 15),
            ("30 分", 30),
            ("1 小時", 60),
            ("2 小時", 120),
            ("4 小時", 240),
            ("8 小時", 480),
        ]
        INTERVAL_VALUES = [v for _, v in INTERVAL_CHOICES]
        INTERVAL_LABELS = [l for l, _ in INTERVAL_CHOICES]

        WEEKDAY_LABELS = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        WEEKDAY_VALUES = [0, 1, 2, 3, 4, 5, 6]

        # 存放每列的控制變數
        row_vars: list[dict] = []   # [{mode_var, interval_var, time_var, ...}, ...]

        for row_idx, (name,) in enumerate(sched_items, start=1):
            cfg = saved.get(name, {})
            mode_val = cfg.get("mode", "off")  # off | interval | daily
            ivl_val  = cfg.get("interval_minutes", 60)
            time_val = cfg.get("time", "08:00")

            # 模組名稱
            is_mail = (name == MAIL_KEY)
            row_bg = "#1a2e1a" if is_mail else (C_PANEL if row_idx % 2 == 0 else C_BG)

            tk.Label(
                inner, text=name,
                bg=row_bg, fg="#4ec9b0" if is_mail else C_TEXT,
                font=("Microsoft JhengHei UI", 9, "bold" if is_mail else "normal"),
                anchor=tk.W, padx=6, pady=4,
            ).grid(row=row_idx, column=0, padx=2, pady=1, sticky=tk.EW)

            # 讀取 weekly 設定（weekday 預設週一=0）
            wd_val = cfg.get("weekday", 0)

            # 模式 Radiobuttons（關閉 / 間隔 / 指定時間 / 每週）
            mode_var = tk.StringVar(value=mode_val)
            mode_frame = tk.Frame(inner, bg=row_bg)
            mode_frame.grid(row=row_idx, column=1, padx=2, pady=1, sticky=tk.EW)

            for m_label, m_val in [
                ("關閉", "off"), ("間隔", "interval"),
                ("每日", "daily"), ("每週", "weekly"),
            ]:
                tk.Radiobutton(
                    mode_frame, text=m_label, variable=mode_var, value=m_val,
                    bg=row_bg, fg=C_TEXT, selectcolor="#094771",
                    activebackground=row_bg, activeforeground=C_ACCENT,
                    font=("Microsoft JhengHei UI", 9),
                ).pack(side=tk.LEFT, padx=3)

            # 間隔 Combobox
            interval_var = tk.StringVar()
            # 找對應 label
            try:
                ivl_label = INTERVAL_LABELS[INTERVAL_VALUES.index(ivl_val)]
            except ValueError:
                ivl_label = INTERVAL_LABELS[0]
            interval_var.set(ivl_label)

            ivl_cb = ttk.Combobox(
                inner, textvariable=interval_var,
                values=INTERVAL_LABELS,
                width=12, state="readonly",
                font=("Microsoft JhengHei UI", 9),
            )
            ivl_cb.grid(row=row_idx, column=2, padx=6, pady=1)

            # 星期 Combobox（供 weekly 模式使用）
            weekday_var = tk.StringVar()
            try:
                wd_label = WEEKDAY_LABELS[WEEKDAY_VALUES.index(int(wd_val))]
            except (ValueError, IndexError):
                wd_label = WEEKDAY_LABELS[0]
            weekday_var.set(wd_label)

            wd_cb = ttk.Combobox(
                inner, textvariable=weekday_var,
                values=WEEKDAY_LABELS,
                width=7, state="readonly",
                font=("Microsoft JhengHei UI", 9),
            )
            wd_cb.grid(row=row_idx, column=3, padx=4, pady=1)

            # 指定時間 Entry (HH:MM) — daily 與 weekly 共用
            time_var = tk.StringVar(value=time_val)
            time_entry = tk.Entry(
                inner, textvariable=time_var,
                width=8,
                bg="#2d2d2d", fg=C_TEXT,
                insertbackground=C_ACCENT,
                font=("Consolas", 10),
                relief=tk.FLAT,
            )
            time_entry.grid(row=row_idx, column=4, padx=6, pady=1)

            # 動態啟用/停用控制項
            # ⚠️ 必須用 closure factory，避免 trace_add 傳入的 3 個位置參數
            def _make_state_updater(_mv, _cb, _wd_cb, _entry):
                def _update(*_args):
                    m = _mv.get()
                    _cb.configure(state="readonly" if m == "interval" else "disabled")
                    _wd_cb.configure(state="readonly" if m == "weekly" else "disabled")
                    _entry.configure(
                        state=tk.NORMAL if m in ("daily", "weekly") else tk.DISABLED
                    )
                return _update

            _updater = _make_state_updater(mode_var, ivl_cb, wd_cb, time_entry)
            mode_var.trace_add("write", _updater)
            _updater()   # 初始套用

            row_vars.append({
                "name":         name,
                "mode_var":     mode_var,
                "interval_var": interval_var,
                "weekday_var":  weekday_var,
                "time_var":     time_var,
            })

        # ── 按鈕列 ────────────────────────────────────────────────────────────
        btn_frame = tk.Frame(dlg, bg=C_BG, pady=8)
        btn_frame.pack(fill=tk.X, padx=16)

        def _on_save():
            import re as _re
            result = {}
            for rv in row_vars:
                name     = rv["name"]
                mode     = rv["mode_var"].get()
                ivl_lbl  = rv["interval_var"].get()
                wd_lbl   = rv["weekday_var"].get()
                time_str = rv["time_var"].get().strip()

                # 驗證指定時間格式（daily / weekly 共用）
                if mode in ("daily", "weekly"):
                    if not _re.match(r"^\d{2}:\d{2}$", time_str):
                        from tkinter import messagebox
                        messagebox.showerror("格式錯誤", f"「{name}」的指定時間格式必須為 HH:MM，例如 07:00", parent=dlg)
                        return

                try:
                    ivl_val = INTERVAL_VALUES[INTERVAL_LABELS.index(ivl_lbl)]
                except ValueError:
                    ivl_val = 0

                try:
                    wd_val = WEEKDAY_VALUES[WEEKDAY_LABELS.index(wd_lbl)]
                except ValueError:
                    wd_val = 0

                entry = {"mode": mode}
                if mode == "interval":
                    entry["interval_minutes"] = ivl_val
                elif mode == "daily":
                    entry["time"] = time_str
                elif mode == "weekly":
                    entry["weekday"] = wd_val
                    entry["time"]    = time_str
                result[name] = entry

            self.save_module_schedules(result)
            logging.getLogger(__name__).info(
                "[排程設定] 已儲存 %d 個模組排程設定", len(result)
            )
            canvas.unbind_all("<MouseWheel>")
            dlg.destroy()

        def _on_cancel():
            canvas.unbind_all("<MouseWheel>")
            dlg.destroy()

        tk.Button(
            btn_frame, text="✓  儲存",
            bg=C_BTN, fg="white",
            activebackground="#1177bb", activeforeground="white",
            font=("Microsoft JhengHei UI", 10, "bold"),
            relief=tk.FLAT, padx=18, pady=5,
            command=_on_save, cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_frame, text="取消",
            bg="#3c3c3c", fg=C_TEXT,
            activebackground="#555555",
            font=("Microsoft JhengHei UI", 10),
            relief=tk.FLAT, padx=12, pady=5,
            command=_on_cancel, cursor="hand2",
        ).pack(side=tk.LEFT)

        # ── 視窗大小與置中 ────────────────────────────────────────────────────
        dlg.update_idletasks()
        row_count   = len(sched_items) + 1   # +1 表頭
        dlg_height  = min(row_count * 34 + 130, 700)
        dlg.geometry(f"860x{dlg_height}")
        # 置中於主視窗
        x = self.winfo_x() + (self.winfo_width()  - 860) // 2
        y = self.winfo_y() + (self.winfo_height() - dlg_height) // 2
        dlg.geometry(f"860x{dlg_height}+{max(0,x)}+{max(0,y)}")
        dlg.minsize(700, 400)

    # ── 清除 Log ─────────────────────────────────────────────────────────────
    def _on_clear(self):
        self._log_buffer.clear()
        self._log_filter_active = False
        self._btn_log_filter.config(
            bg="#3c2020", fg=C_ERROR,
            text="⚠  只顯示錯誤 Log",
        )
        self._log_text.config(state=tk.NORMAL)
        self._log_text.delete("1.0", tk.END)
        self._log_text.config(state=tk.DISABLED)

    # ── 關閉時清理 ───────────────────────────────────────────────────────────
    def destroy(self):
        self._sched_thread_running = False   # 通知排程 thread 結束
        if self._auto_timer:
            self._auto_timer.cancel()
        if self._countdown_job:
            self.after_cancel(self._countdown_job)
        root = logging.getLogger()
        if self._gui_handler:
            root.removeHandler(self._gui_handler)
        if self._startup_fh:
            root.removeHandler(self._startup_fh)
            self._startup_fh.close()
        super().destroy()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = SyncApp()
    app.mainloop()
