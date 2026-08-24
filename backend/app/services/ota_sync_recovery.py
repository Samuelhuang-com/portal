"""
OTA 同步：孤兒 `running` 紀錄回收（2026-08-24 新增）
==========================================================================

要修的問題
--------------------------------------------------------------------------
`ota_scraper_service.sync_source()` 的流程是：

    start_sync_log(...)      → status='running'
    db.commit()              # ⚠️ 這裡就已經落地
    try:
        ...實際擷取...
        finish_sync_log('success')
    except Exception:
        finish_sync_log('failed')

`except Exception` 攔得住「這個來源抓失敗」，攔不住這幾種：

  · **Ctrl-C** —— KeyboardInterrupt 是 BaseException，不是 Exception ← 最常見
  · 行程被砍、後端重啟、uvicorn --reload 在擷取中途重載
  · 機器休眠／當機、WinError 6 那種 driver 層崩潰

任何一種發生，那一列就永遠停在 running。

**而它不是顯示問題。** `ota_admin.run_sync()` 開頭：

    if running:
        raise HTTPException(409, "目前已有同步在執行中…")

一列孤兒 running ＝ 整個 OTA 模組的同步從此鎖死，而畫面上只顯示
「擷取中…」，沒有任何錯誤訊息告訴你為什麼按不下去。

--------------------------------------------------------------------------
判定順序：先問行程死了沒，問不到才用逾時
--------------------------------------------------------------------------
| 層 | 依據 | 精準度 |
|----|------|--------|
| 1  | `worker_host` ＝本機 且 `worker_pid` 已不存在 | **確定**死了 |
| 2  | `started_at` 超過 `STALE_MINUTES` | 推測 |
| 3  | 呼叫端 `force=True`（UI 的「強制解除」） | 人工判斷 |

⚠️ **為什麼不能「後端一啟動就把所有 running 標成 failed」**（本來的第一直覺）：
   回補是用 `ota_scraper_cli` 跑的，那是**獨立行程**。後端重啟一次就會把
   一個正在跑的 CLI 同步誤判成死掉，然後兩邊同時寫同一批資料。
   第 1 層那個 host+pid 就是為了避開這件事 —— 只回收「確實是這台機器上、
   確實已經不在的」那些。

⚠️ **不要在 Windows 上用 `os.kill(pid, 0)` 探測**：POSIX 上 signal 0 是
   「只檢查不送訊號」，但 Python 在 Windows 上遇到非 CTRL_* 的訊號會走
   `TerminateProcess` —— 那會**真的把那個行程殺掉**。這裡改用 ctypes
   開 handle 的方式，見 `_pid_alive()`。
"""
from __future__ import annotations

import logging
import os
import socket
import sys
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.ota_review import OtaSyncLog

logger = logging.getLogger(__name__)

# 逾時門檻：單一來源翻 200 頁實測約 20–40 分鐘，90 分留足餘裕。
# 真的跑超過 90 分鐘的，本來也該當異常看待。
STALE_MINUTES = 90


def ensure_worker_columns() -> list[str]:
    """
    補上 `ota_sync_logs.worker_host` / `worker_pid`，回傳實際新增的欄位名。

    ⚠️ **這支必須有三個呼叫端**，因為有三個行程會寫 `ota_sync_logs`：
       `main.py`（後端）、`sync_tool.py`（同步工具）、`ota_scraper_cli.py`（回補）。
       少接一個，那條路徑就會在「使用者按下同步」的當下爆
       `no such column: ota_sync_logs.worker_host`。

    ⚠️ 不可以假設「反正後端會先重啟過」—— 正式區可能只跑 sync_tool，
       使用者也可能直接下 CLI 回補。**寫這張表的每個入口都要自己確認 schema。**

    ⚠️ 這支不放 `main.py` 而放這裡的理由：ALTER 一旦有三份拷貝就會各自漂移。
       2026-08-24 第一版就是各寫各的，`ota_scraper_cli.py` 直接漏掉。
    """
    from sqlalchemy import text

    from app.core.database import engine

    added: list[str] = []
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(ota_sync_logs)")).fetchall()
        if not rows:
            return added                 # 表還沒建 → create_all 會直接帶上新欄位
        existing = {row[1] for row in rows}
        for col, typedef in (("worker_host", "VARCHAR(60) DEFAULT ''"),
                             ("worker_pid", "INTEGER")):
            if col not in existing:
                conn.execute(text(
                    f"ALTER TABLE ota_sync_logs ADD COLUMN {col} {typedef}"))
                added.append(col)
        if added:
            conn.commit()
    return added


def worker_identity() -> tuple[str, int]:
    """目前行程的身分，寫進 `start_sync_log()`。"""
    try:
        host = socket.gethostname()[:60]
    except OSError:                                     # pragma: no cover
        host = ""
    return host, os.getpid()


def _pid_alive(pid: int) -> bool | None:
    """
    這個 pid 還活著嗎？

    回傳 `True`／`False`；**探測不了就回 `None`**（不要假裝知道）——
    `None` 會讓呼叫端退回逾時判定，而不是把一個可能還在跑的同步收掉。
    """
    if pid <= 0:
        return None

    if sys.platform == "win32":
        # ⚠️ 不可用 os.kill：Windows 上 Python 會走 TerminateProcess，
        #    「探測」會變成「處決」。
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            err = ctypes.get_last_error()
            # 87 ERROR_INVALID_PARAMETER ＝ 沒有這個 pid → 確定死了
            if err == 87:
                return False
            # 5 ERROR_ACCESS_DENIED ＝ 行程存在但權限不足 → 活著
            if err == 5:
                return True
            return None
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return None
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)

    try:
        os.kill(pid, 0)                 # POSIX：signal 0 只檢查，不送訊號
        return True
    except ProcessLookupError:
        return False
    except PermissionError:             # 行程存在，只是不屬於我們
        return True
    except OSError:                     # pragma: no cover
        return None


@dataclass
class ReapedLog:
    log_id: int
    source_id: int
    reason: str


def reap_stale_running(
    db: Session,
    *,
    force: bool = False,
    stale_minutes: int = STALE_MINUTES,
) -> list[ReapedLog]:
    """
    把孤兒 `running` 收成 `failed`，回傳被收掉的清單（沒有就回空 list）。

    ⚠️ **呼叫端自己 commit**。這樣它才能跟 `run_sync()` 的檢查在
       同一個交易裡完成，不會有「剛收完、下一行又讀到舊值」的窗口。

    ⚠️ 只動 `ota_sync_logs`，**不碰 `ota_reviews`**。
       中斷前抓到的評論是逐頁 upsert 進去的，那些是好資料，留著。
    """
    rows = db.execute(
        select(OtaSyncLog).where(OtaSyncLog.status == "running")
    ).scalars().all()
    if not rows:
        return []

    now = twnow()
    this_host, _ = worker_identity()
    reaped: list[ReapedLog] = []

    for log in rows:
        reason = ""

        if force:
            reason = "人工強制解除"
        elif log.worker_pid and log.worker_host and log.worker_host == this_host:
            alive = _pid_alive(log.worker_pid)
            if alive is False:
                reason = f"執行行程 pid={log.worker_pid} 已不存在"

        if not reason and log.started_at:
            age_min = (now - log.started_at).total_seconds() / 60
            if age_min > stale_minutes:
                reason = f"已執行 {age_min:,.0f} 分鐘，超過 {stale_minutes} 分鐘門檻"

        if not reason:
            continue                    # 還活著／還在門檻內 → 不要動它

        log.status = "failed"
        log.completed_at = now
        log.error_message = (
            f"{log.error_message or ''}"
            f"［自動收尾］{reason}。擷取行程中斷（Ctrl-C／重啟／崩潰）"
            f"未能正常收尾，此紀錄由系統標記為失敗。已入庫的評論不受影響。"
        ).strip()[:1000]
        reaped.append(ReapedLog(log.id, log.source_id, reason))
        logger.warning("[OTA] 回收孤兒同步紀錄 #%s（來源 #%s）：%s",
                       log.id, log.source_id, reason)

    return reaped
