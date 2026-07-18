#!/usr/bin/env python3
"""
Portal 服務主控台 — OPERA 風格畫面範例（mockup，僅供設計方向確認）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 這是獨立的畫面範例，不是正式工具，不會啟動/停止真正的 uvicorn/vite！
   按鈕只會切換畫面上的假狀態＋跳出 Toast，用來確認「淺色版型」方向是否喜歡。
   確認方向後才會套用到 portal_console.py 本體（含真正的服務控制邏輯）。

參考畫面：Oracle Hospitality OPERA Fiscal Integration Solution
（圖示分頁列＋工具列＋卡片式設定內容＋底部按鈕列＋Toast 通知）

圖示：用 emoji 代替（跟 portal_console.py 既有做法一致，不需要額外圖檔）

執行方式：
  cd portal
  python portal_console_mockup.py
"""

import tkinter as tk

# ── 色系：淺色版型，沿用 Portal 品牌色 + 既有受保護頁面背景色 ──────────────────
C_TAB_BG = "#1B3A5C"        # 品牌主色（分頁列背景，對應 OPERA 的 teal）
C_TAB_ACTIVE_FG = "#ffffff"
C_TAB_INACTIVE_FG = "#9db3c9"
C_TAB_UNDERLINE = "#4BA8E8"  # 品牌輔色

C_PAGE_BG = "#f0f4f8"       # 沿用 Portal 網頁版「頁面背景」受保護色碼
C_CARD_BG = "#ffffff"
C_BORDER = "#e2e8f0"
C_TEXT = "#1f2937"
C_TEXT_DIM = "#6b7280"

C_TOOLBAR_BG = "#ffffff"
C_BTN_TEXT = "#374151"
C_BTN_DISABLED = "#c3c9d1"

C_RUNNING_BG = "#e6f4ea"
C_RUNNING_FG = "#1e7e34"
C_STOPPED_BG = "#f4e6e6"
C_STOPPED_FG = "#b3261e"

C_TOAST_BG = "#e8f5e9"
C_TOAST_FG = "#256029"
C_TOAST_BORDER = "#a5d6a7"

FONT_NAME = "Microsoft JhengHei UI"


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

    def __init__(self, parent, width=92, height=26):
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0)
        # 注意：不能叫 self._w / self._h —— tkinter.Widget 內部已經用 self._w
        # 存放這個元件自己的 Tcl widget path（例如 ".!toplevel.!frame.!canvas"）。
        # 之前這裡誤用 self._w 存像素寬度（int），把內部的 widget path 蓋掉，
        # 導致之後呼叫 self.delete(...) 時 Tcl 找不到正確的 widget 命令，
        # 噴出 "invalid command name "92"" 這種看起來莫名其妙的錯誤。
        self._pill_w, self._pill_h = width, height
        self.set_state(False)

    def set_state(self, running: bool):
        self.delete("all")
        bg = C_RUNNING_BG if running else C_STOPPED_BG
        fg = C_RUNNING_FG if running else C_STOPPED_FG
        text = "● Running" if running else "● Stopped"
        rounded_rect(self, 1, 1, self._pill_w - 1, self._pill_h - 1,
                     r=(self._pill_h - 2) // 2, fill=bg, outline=bg)
        self.create_text(
            self._pill_w / 2, self._pill_h / 2, text=text, fill=fg,
            font=(FONT_NAME, 9, "bold"),
        )


class Toast(tk.Frame):
    """暫時性通知條（仿 OPERA 底部「Service was successfully stopped.」綠色提示）。"""

    def __init__(self, parent):
        super().__init__(parent, bg=C_TOAST_BG, highlightbackground=C_TOAST_BORDER,
                          highlightthickness=1, bd=0)
        self._label = tk.Label(
            self, bg=C_TOAST_BG, fg=C_TOAST_FG,
            font=(FONT_NAME, 10), padx=14, pady=10,
        )
        self._label.pack()
        self._hide_job = None

    def show(self, message: str, ms: int = 3000):
        self._label.config(text=f"✅  {message}")
        self.place(relx=0.98, rely=0.90, anchor="e")
        self.lift()
        if self._hide_job:
            self.after_cancel(self._hide_job)
        self._hide_job = self.after(ms, self.place_forget)


class MockupWindow(tk.Tk):
    TABS = [
        ("🌐", "服務控制"),
        ("📋", "Health Check"),
        ("⚙️", "設定"),
    ]

    def __init__(self):
        super().__init__()
        self.title("Portal 服務主控台 — 畫面範例（mockup，非正式工具）")
        self.geometry("980x720")
        self.configure(bg=C_PAGE_BG)
        self.minsize(900, 640)

        self._running = False
        self._active_tab = 0

        self._build_tab_bar()
        self._build_toolbar()
        self._build_content_area()

        self._toast = Toast(self)

        self._render_service_tab()

    # ── 分頁列（圖示＋文字，仿 Adapter / BE Gateway / Configuration…）──────────
    def _build_tab_bar(self):
        bar = tk.Frame(self, bg=C_TAB_BG, height=54)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)

        self._tab_widgets = []
        for i, (icon, label) in enumerate(self.TABS):
            cell = tk.Frame(bar, bg=C_TAB_BG)
            cell.pack(side=tk.LEFT, padx=(20 if i == 0 else 0, 0), pady=0)

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
            self._render_service_tab()
        else:
            self._render_placeholder_tab(self.TABS[idx][1])

    # ── 工具列（Start/Stop/Restart | Refresh + 狀態徽章 + Help）────────────────
    def _build_toolbar(self):
        toolbar = tk.Frame(self, bg=C_TOOLBAR_BG, height=46, highlightbackground=C_BORDER,
                            highlightthickness=1)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        left = tk.Frame(toolbar, bg=C_TOOLBAR_BG)
        left.pack(side=tk.LEFT, padx=14)

        def _toolbtn(parent, icon, text, cmd, disabled=False):
            fg = C_BTN_DISABLED if disabled else C_BTN_TEXT
            lbl = tk.Label(
                parent, text=f"{icon}  {text}", bg=C_TOOLBAR_BG, fg=fg,
                font=(FONT_NAME, 10), padx=10, cursor="hand2" if not disabled else "arrow",
            )
            lbl.pack(side=tk.LEFT)
            if not disabled:
                lbl.bind("<Button-1>", lambda e: cmd())
            return lbl

        _toolbtn(left, "▶", "Start", self._on_start)
        _toolbtn(left, "■", "Stop", self._on_stop)
        _toolbtn(left, "↻", "Restart", self._on_restart)

        tk.Frame(left, bg=C_BORDER, width=1, height=20).pack(side=tk.LEFT, padx=10)

        _toolbtn(left, "🔄", "Refresh", self._on_refresh)

        right = tk.Frame(toolbar, bg=C_TOOLBAR_BG)
        right.pack(side=tk.RIGHT, padx=14)

        tk.Label(right, text="❓ Help", bg=C_TOOLBAR_BG, fg=C_BTN_TEXT,
                 font=(FONT_NAME, 10)).pack(side=tk.RIGHT, padx=(14, 0))

        self._status_pill = StatusPill(right)
        self._status_pill.pack(side=tk.RIGHT, padx=(14, 0))

    # ── 內容區（卡片式設定畫面，仿 Adapter Settings）───────────────────────────
    def _build_content_area(self):
        self._content = tk.Frame(self, bg=C_PAGE_BG)
        self._content.pack(fill=tk.BOTH, expand=True)

    def _clear_content(self):
        for w in self._content.winfo_children():
            w.destroy()

    def _render_placeholder_tab(self, label):
        self._clear_content()
        tk.Label(
            self._content, text=f"（{label} 頁面樣式待套用——先確認「服務控制」頁的方向）",
            bg=C_PAGE_BG, fg=C_TEXT_DIM, font=(FONT_NAME, 11),
        ).pack(expand=True)

    def _render_service_tab(self):
        self._clear_content()

        wrap = tk.Frame(self._content, bg=C_PAGE_BG)
        wrap.pack(fill=tk.BOTH, expand=True, padx=28, pady=22)

        tk.Label(
            wrap, text="Backend 服務設定", bg=C_PAGE_BG, fg=C_TEXT,
            font=(FONT_NAME, 20, "bold"),
        ).pack(anchor="w")

        cols = tk.Frame(wrap, bg=C_PAGE_BG)
        cols.pack(fill=tk.BOTH, expand=True, pady=(18, 0))

        left = tk.Frame(cols, bg=C_PAGE_BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 24))
        right = tk.Frame(cols, bg=C_PAGE_BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._section(
            left, "服務位址",
            [
                ("指令", "uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"),
                ("Port", "8000"),
                ("Working Directory", str(_pathlib_display("backend"))),
            ],
        )

        self._section(
            right, "狀態資訊",
            [
                ("目前狀態", "Stopped（示意，未接真實偵測）"),
                ("PID", "—"),
                ("最後一次操作", "尚未操作"),
            ],
        )

        bottom = tk.Frame(self, bg=C_CARD_BG, height=50, highlightbackground=C_BORDER,
                           highlightthickness=1)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)
        bottom.pack_propagate(False)

        tk.Label(
            bottom, text="portal_console.py mockup v0.1", bg=C_CARD_BG, fg=C_TEXT_DIM,
            font=(FONT_NAME, 9),
        ).pack(side=tk.LEFT, padx=16)

        btn_row = tk.Frame(bottom, bg=C_CARD_BG)
        btn_row.pack(side=tk.RIGHT, padx=16)

        tk.Label(btn_row, text="關閉視窗", bg=C_CARD_BG, fg=C_TEXT_DIM,
                 font=(FONT_NAME, 10), cursor="hand2").pack(side=tk.LEFT, padx=10)
        tk.Frame(btn_row, bg=C_BORDER, width=1, height=18).pack(side=tk.LEFT, padx=4)
        tk.Label(
            btn_row, text="測試連線", bg=C_CARD_BG, fg=C_TAB_BG,
            font=(FONT_NAME, 10, "bold"), cursor="hand2",
            highlightbackground=C_TAB_BG, highlightthickness=1, padx=10, pady=4,
        ).pack(side=tk.LEFT, padx=10)
        tk.Label(
            btn_row, text="重新整理", bg=C_TAB_BG, fg="white",
            font=(FONT_NAME, 10, "bold"), cursor="hand2", padx=12, pady=4,
        ).pack(side=tk.LEFT, padx=10)

    def _section(self, parent, title, rows):
        tk.Label(
            parent, text=title, bg=C_PAGE_BG, fg=C_TEXT,
            font=(FONT_NAME, 12, "bold"),
        ).pack(anchor="w")
        tk.Frame(parent, bg=C_BORDER, height=1).pack(fill=tk.X, pady=(4, 12))

        for label, value in rows:
            row = tk.Frame(parent, bg=C_PAGE_BG)
            row.pack(fill=tk.X, pady=(0, 12))
            tk.Label(row, text=label, bg=C_PAGE_BG, fg=C_TEXT_DIM,
                     font=(FONT_NAME, 9)).pack(anchor="w")
            box = tk.Frame(row, bg=C_CARD_BG, highlightbackground=C_BORDER,
                            highlightthickness=1)
            box.pack(fill=tk.X, pady=(2, 0))
            tk.Label(box, text=value, bg=C_CARD_BG, fg=C_TEXT, font=(FONT_NAME, 10),
                     anchor="w", padx=10, pady=8, wraplength=380, justify=tk.LEFT).pack(fill=tk.X)

    # ── 假動作：只切換畫面狀態＋跳 Toast，不會真的啟停任何服務 ──────────────────
    def _on_start(self):
        self._running = True
        self._status_pill.set_state(True)
        self._toast.show("服務已成功啟動。")

    def _on_stop(self):
        self._running = False
        self._status_pill.set_state(False)
        self._toast.show("服務已成功停止。")

    def _on_restart(self):
        self._running = True
        self._status_pill.set_state(True)
        self._toast.show("服務已重新啟動。")

    def _on_refresh(self):
        self._toast.show("狀態已重新整理。")


def _pathlib_display(sub: str) -> str:
    import pathlib
    return pathlib.Path(__file__).resolve().parent / sub


if __name__ == "__main__":
    app = MockupWindow()
    app.mainloop()
