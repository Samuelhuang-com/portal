#!/usr/bin/env python3
"""Portal API 測試工具（GUI）"""
import json
import threading
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ── 設定 ──────────────────────────────────────────────────────────────────────
BASE     = "http://127.0.0.1:8000/api/v1"
USERNAME = "admin"
PASSWORD = "Admin@2026"

PRESETS = [
    ("每月統計 (2026/6)",  "GET /mall/full-building-maintenance/period-stats?period_type=month&year=2026&month=6&frequency_type=monthly"),
    ("每季統計 (2026/Q2)", "GET /mall/full-building-maintenance/period-stats?period_type=quarter&year=2026&quarter=2&frequency_type=quarterly"),
    ("每年統計 (2026)",    "GET /mall/full-building-maintenance/period-stats?period_type=year&year=2026&frequency_type=yearly"),
    ("年度矩陣 (2026)",    "GET /mall/full-building-maintenance/schedule/annual-matrix?year=2026"),
    ("排程 KPI (2026/06)", "GET /mall/full-building-maintenance/schedule/kpi?year_month=2026/06"),
    ("排程列表 (2026/06)", "GET /mall/full-building-maintenance/schedule?year_month=2026/06"),
    ("逾期排程",           "GET /mall/full-building-maintenance/schedule/overdue"),
    ("批次清單",           "GET /mall/full-building-maintenance/batches"),
    ("全站統計",           "GET /mall/full-building-maintenance/stats?year=2026&month=6"),
    ("保養項目",           "GET /mall/full-building-maintenance/items"),
]


def get_token():
    data = json.dumps({"identifier": USERNAME, "password": PASSWORD}).encode()
    req  = urllib.request.Request(
        f"{BASE}/auth/login", data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())["access_token"]


def call_api(method_path: str, token: str):
    parts  = method_path.strip().split(" ", 1)
    method = parts[0].upper() if len(parts) == 2 else "GET"
    path   = parts[1] if len(parts) == 2 else parts[0]
    if not path.startswith("/api"):
        path = path if path.startswith("/") else "/" + path
    url = BASE + path
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {token}",
                      "Content-Type": "application/json", "Cache-Control": "no-cache"},
        method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
        except Exception:
            body = {"error": str(e)}
        return e.code, body


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Portal API 測試工具")
        self.geometry("960x680")
        self.configure(bg="#1e1e2e")
        self._token = None
        self._build()

    def _build(self):
        # ── 標題列 ──────────────────────────────────────────────────────────
        top = tk.Frame(self, bg="#1e1e2e")
        top.pack(fill="x", padx=12, pady=(12, 4))

        tk.Label(top, text="Portal API Tester", font=("Segoe UI", 14, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(side="left")

        self.status_lbl = tk.Label(top, text="● 未登入", font=("Segoe UI", 10),
                                   bg="#1e1e2e", fg="#f38ba8")
        self.status_lbl.pack(side="right")

        tk.Button(top, text="重新登入", command=self._login_bg,
                  bg="#45475a", fg="#cdd6f4", relief="flat",
                  padx=10, cursor="hand2").pack(side="right", padx=6)

        # ── 預設快捷鈕 ──────────────────────────────────────────────────────
        preset_frame = tk.LabelFrame(self, text=" 快速選單 ", font=("Segoe UI", 9),
                                     bg="#1e1e2e", fg="#a6adc8", bd=1)
        preset_frame.pack(fill="x", padx=12, pady=4)

        cols = 5
        for i, (label, url) in enumerate(PRESETS):
            btn = tk.Button(preset_frame, text=label,
                            command=lambda u=url: self._preset(u),
                            bg="#313244", fg="#cdd6f4", relief="flat",
                            padx=6, pady=3, cursor="hand2",
                            activebackground="#45475a", activeforeground="#cdd6f4")
            btn.grid(row=i // cols, column=i % cols, padx=3, pady=3, sticky="ew")
        for c in range(cols):
            preset_frame.columnconfigure(c, weight=1)

        # ── 輸入列 ──────────────────────────────────────────────────────────
        inp = tk.Frame(self, bg="#1e1e2e")
        inp.pack(fill="x", padx=12, pady=6)

        tk.Label(inp, text="API 路徑：", font=("Segoe UI", 10),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")

        self.url_var = tk.StringVar(value="GET /mall/full-building-maintenance/period-stats?period_type=month&year=2026&month=6&frequency_type=monthly")
        self.url_entry = tk.Entry(inp, textvariable=self.url_var,
                                  font=("Consolas", 10), bg="#313244", fg="#cdd6f4",
                                  insertbackground="#cdd6f4", relief="flat", bd=4)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.url_entry.bind("<Return>", lambda e: self._send())

        self.send_btn = tk.Button(inp, text="▶ 送出", command=self._send,
                                  bg="#89b4fa", fg="#1e1e2e", font=("Segoe UI", 10, "bold"),
                                  relief="flat", padx=14, cursor="hand2")
        self.send_btn.pack(side="left")

        # ── 狀態列 ──────────────────────────────────────────────────────────
        info = tk.Frame(self, bg="#1e1e2e")
        info.pack(fill="x", padx=12)
        self.code_lbl = tk.Label(info, text="", font=("Consolas", 10),
                                 bg="#1e1e2e", fg="#a6e3a1")
        self.code_lbl.pack(side="left")
        self.time_lbl = tk.Label(info, text="", font=("Consolas", 9),
                                 bg="#1e1e2e", fg="#6c7086")
        self.time_lbl.pack(side="left", padx=8)

        # ── 結果區 ──────────────────────────────────────────────────────────
        result_frame = tk.Frame(self, bg="#1e1e2e")
        result_frame.pack(fill="both", expand=True, padx=12, pady=(4, 0))

        btn_bar = tk.Frame(result_frame, bg="#1e1e2e")
        btn_bar.pack(fill="x", pady=(0, 4))
        tk.Label(btn_bar, text="回應 JSON", font=("Segoe UI", 10),
                 bg="#1e1e2e", fg="#a6adc8").pack(side="left")

        tk.Button(btn_bar, text="複製全部", command=self._copy,
                  bg="#45475a", fg="#cdd6f4", relief="flat",
                  padx=8, cursor="hand2").pack(side="right")
        tk.Button(btn_bar, text="清除", command=self._clear,
                  bg="#45475a", fg="#f38ba8", relief="flat",
                  padx=8, cursor="hand2").pack(side="right", padx=4)

        self.result = scrolledtext.ScrolledText(
            result_frame, font=("Consolas", 10), bg="#181825", fg="#cdd6f4",
            insertbackground="#cdd6f4", relief="flat", bd=0, wrap="none")
        self.result.pack(fill="both", expand=True)

        # ── 底部版本 ─────────────────────────────────────────────────────────
        tk.Label(self, text="Portal Dev Tool — admin@2026",
                 font=("Segoe UI", 8), bg="#1e1e2e", fg="#45475a").pack(pady=4)

        # 啟動時自動登入
        self.after(200, self._login_bg)

    # ── 動作 ─────────────────────────────────────────────────────────────────
    def _login_bg(self):
        self.status_lbl.config(text="● 登入中…", fg="#f9e2af")
        threading.Thread(target=self._do_login, daemon=True).start()

    def _do_login(self):
        try:
            self._token = get_token()
            self.after(0, lambda: self.status_lbl.config(text="● 已登入", fg="#a6e3a1"))
        except Exception as e:
            self._token = None
            err_msg = str(e)
            self.after(0, lambda msg=err_msg: self.status_lbl.config(text=f"● 登入失敗：{msg}", fg="#f38ba8"))

    def _preset(self, url):
        self.url_var.set(url)
        self._send()

    def _send(self):
        if not self._token:
            self._login_bg()
            messagebox.showinfo("提示", "正在重新登入，請稍後再試")
            return
        self.send_btn.config(state="disabled", text="等待中…")
        self.code_lbl.config(text="")
        self.time_lbl.config(text="")
        path = self.url_var.get().strip()
        threading.Thread(target=self._do_send, args=(path,), daemon=True).start()

    def _do_send(self, path):
        import time
        t0 = time.time()
        try:
            code, data = call_api(path, self._token)
        except Exception as e:
            code, data = 0, {"exception": str(e)}
        elapsed = time.time() - t0
        text = json.dumps(data, ensure_ascii=False, indent=2)
        color = "#a6e3a1" if 200 <= code < 300 else "#f38ba8"
        self.after(0, lambda: self._show(code, text, color, elapsed))

    def _show(self, code, text, color, elapsed):
        self.result.config(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("end", text)
        self.result.config(state="normal")
        self.code_lbl.config(text=f"HTTP {code}", fg=color)
        self.time_lbl.config(text=f"({elapsed:.2f}s)")
        self.send_btn.config(state="normal", text="▶ 送出")

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.result.get("1.0", "end").strip())
        messagebox.showinfo("已複製", "JSON 已複製到剪貼簿")

    def _clear(self):
        self.result.config(state="normal")
        self.result.delete("1.0", "end")
        self.code_lbl.config(text="")
        self.time_lbl.config(text="")


if __name__ == "__main__":
    app = App()
    app.mainloop()
