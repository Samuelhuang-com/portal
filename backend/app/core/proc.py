"""
行程存活探測（2026-08-24 建立）

⚠️ **為什麼放在 `core/` 而不是留在原本的 service 裡**：
   2026-08-24 早上為了回收 `ota_sync_logs` 的孤兒 `running`，在
   `services/ota_sync_recovery.py` 寫了 `_pid_alive()`；同一天下午
   `core/sync_lock.py` 也需要它（判斷 `.sync.lock.owner` 裡的 pid 還在不在）。

   `core` 不可以反過來 import `services`，而複製一份就等著兩邊漂移 ——
   尤其這支裡面有 Windows 的地雷（見下），漂移的代價是「探測變成處決」。
   所以搬到 `core/proc.py`，兩邊共用。
"""
from __future__ import annotations

import os
import socket
import sys


def worker_identity() -> tuple[str, int]:
    """目前行程的身分：`(hostname, pid)`。"""
    try:
        host = socket.gethostname()[:60]
    except OSError:                                     # pragma: no cover
        host = ""
    return host, os.getpid()


def pid_alive(pid: int) -> bool | None:
    """
    這個 pid 還活著嗎？

    回傳 `True`／`False`；**探測不了就回 `None`**（不要假裝知道）——
    呼叫端看到 `None` 應該退回別的判斷方式，而不是當成「死了」。

    ⚠️⚠️ **Windows 上絕對不可以用 `os.kill(pid, 0)`**：
       POSIX 的 signal 0 是「只檢查不送訊號」，但 Python 在 Windows 上
       遇到非 `CTRL_*` 的訊號會走 `TerminateProcess` ——
       **探測會變成處決**，直接把那個行程殺掉。
    """
    if pid <= 0:
        return None

    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            err = ctypes.get_last_error()
            if err == 87:       # ERROR_INVALID_PARAMETER ＝ 沒有這個 pid
                return False
            if err == 5:        # ERROR_ACCESS_DENIED ＝ 行程存在但權限不足
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
