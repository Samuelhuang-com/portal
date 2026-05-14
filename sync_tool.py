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
  python sync_tool.py
"""

import asyncio
import importlib
import inspect
import logging
import os
import pathlib
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk
from datetime import datetime

# ── 路徑設定：讓 app.* 可以被 import ─────────────────────────────────────────
# 注意：所有路徑先解析為絕對路徑，再切換 CWD。
_HERE    = pathlib.Path(__file__).resolve().parent   # portal/ 絕對路徑
_BACKEND = _HERE / "backend"                          # portal/backend/ 絕對路徑
_LOG_DIR = _HERE / "logs"                             # portal/logs/ 絕對路徑

# ⚠️ 必須在 import 任何 app.* 之前切換 CWD 到 backend/
#    原因：app.core.config 的 env_file=".env" 與 DATABASE_URL="sqlite:///./portal.db"
#    都是基於 CWD 的相對路徑，需與 uvicorn 啟動位置一致（portal/backend/）。
os.chdir(_BACKEND)

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
    ("核准請購單清單", "app.services.purchase_request_sync",          "sync_list_only"),
    ("核准請款單清單", "app.services.claim_request_sync",             "sync_list_only"),
]

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
C_SUCCESS = "#4ec9b0"
C_WARN    = "#f0c040"
C_ERROR   = "#f04040"
C_INFO    = "#d4d4d4"


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

    def __init__(self, text_widget: scrolledtext.ScrolledText):
        super().__init__()
        self._w = text_widget
        self.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        ))

    def emit(self, record: logging.LogRecord):
        msg   = self.format(record) + "\n"
        color = self._COLORS.get(record.levelno, C_INFO)
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

        self._build_ui()
        self._setup_logging()
        self._check_env()

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

        tk.Label(
            tbl_frame, text="同步結果",
            bg=C_PANEL, fg=C_DIM,
            font=("Microsoft JhengHei UI", 9, "bold"),
        ).pack(anchor=tk.W, padx=10, pady=(8, 2))

        # Treeview 表格
        cols = ("模組", "狀態", "開始時間", "耗時(秒)", "撈取", "寫入", "錯誤", "觸發")
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
        self._tree.tag_configure("success", foreground=C_SUCCESS)
        self._tree.tag_configure("partial", foreground=C_WARN)
        self._tree.tag_configure("error",   foreground=C_ERROR)
        self._tree.tag_configure("pending", foreground=C_DIM)
        self._tree.tag_configure("running", foreground=C_ACCENT)

        vsb = ttk.Scrollbar(tbl_frame, orient=tk.VERTICAL,
                            command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4))
        self._tree.pack(fill=tk.BOTH, expand=True, padx=(4, 0), pady=(0, 4))

        # 初始填滿所有模組列（狀態為「—」）
        self._tree_ids: dict[str, str] = {}
        for name, _, _ in MODULES:
            iid = self._tree.insert(
                "", tk.END,
                values=(name, "—", "—", "—", "—", "—", "—", "—"),
                tags=("pending",),
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
    # Logging 設定
    # ─────────────────────────────────────────────────────────────────────────
    def _setup_logging(self):
        fmt = logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self._gui_handler = _GuiLogHandler(self._log_text)
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
    def _on_sync(self):
        self._trigger_sync("手動")

    def _trigger_sync(self, triggered_by: str = "手動"):
        if self._running:
            return
        self._running = True
        self._btn_sync.config(state=tk.DISABLED, text="同步中…")
        self._progress.start(12)
        self._lbl_status.config(text="同步中…", fg=C_ACCENT)
        # 重置表格狀態
        for name in self._tree_ids:
            self._tree.item(
                self._tree_ids[name],
                values=(name, "⟳", "—", "—", "—", "—", "—", triggered_by),
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
        logger.info(f"━━━  同步開始（{triggered_by}）━━━  log：{log_path}")

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

        self.after(0, self._on_sync_done, ok, partial, err, log_path)

        # 若自動同步開啟，排定下一次
        if self._auto_interval > 0:
            self.after(0, self._schedule_next_auto)

    async def _run_all_modules(self, results: list[dict], triggered_by: str):
        logger = logging.getLogger(__name__)
        total  = len(MODULES)

        for i, (name, mod_path, func_name) in enumerate(MODULES, 1):
            self.after(0, self._lbl_module.config,
                       {"text": f"[{i}/{total}]  {name}"})
            self.after(0, self._lbl_status.config, {"text": f"{name}…"})

            logger.info(f"[{i:02d}/{total}] 開始：{name}")
            t0       = datetime.now()
            status   = "success"
            fetched  = upserted = err_count = 0

            try:
                mod  = importlib.import_module(mod_path)
                func = getattr(mod, func_name)
                if inspect.iscoroutinefunction(func):
                    result = await func()
                else:
                    result = await asyncio.to_thread(func)

                duration = round((datetime.now() - t0).total_seconds(), 2)

                if isinstance(result, dict):
                    fetched   = result.get("fetched",  0)
                    upserted  = result.get("upserted", 0)
                    errors    = result.get("errors",   [])
                    err_count = len(errors)
                else:
                    errors = []

                if errors:
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
                         triggered_by: str):
        iid = self._tree_ids.get(name)
        if iid:
            err_disp = str(err_count) if err_count else "0"
            self._tree.item(
                iid,
                values=(name, status_txt, start_str, dur,
                        fetched, upserted, err_disp, triggered_by),
                tags=(tag,),
            )

    def _on_sync_done(self, ok: int, partial: int, err: int,
                      log_path: pathlib.Path):
        self._running = False
        self._btn_sync.config(state=tk.NORMAL, text="▶  立即同步所有模組")
        self._progress.stop()
        self._lbl_module.config(text="")

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

    # ── 清除 Log ─────────────────────────────────────────────────────────────
    def _on_clear(self):
        self._log_text.config(state=tk.NORMAL)
        self._log_text.delete("1.0", tk.END)
        self._log_text.config(state=tk.DISABLED)

    # ── 關閉時清理 ───────────────────────────────────────────────────────────
    def destroy(self):
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
