"""
跨行程同步鎖（2026-07-15 新增）

背景：
  sync_tool.py（獨立行程，可能在正式區/開發機上單獨執行）與後端本身的排程
  （AsyncIOScheduler：module_auto_sync、purchase_list_sync、RagicConnection
  排程等）過去完全互不知情，可能同時對同一份 SQLite 檔案（portal.db）寫入，
  觸發 "database is locked"。

作法：
  用檔案鎖（filelock 套件，跨平台，Windows 上用系統原生檔案鎖）在「實際執行
  同步／寫入 DB」的呼叫前後互斥，讓 sync_tool.py 與後端排程之間不會同時
  跑同一批寫入。鎖檔案固定跟 portal.db 放同一個資料夾（從 DATABASE_URL 推算），
  搬到 C:\\Portal_Data\\ 之後，鎖檔案自然也在那裡，不受 OneDrive 同步影響。

  若 DATABASE_URL 已經不是 SQLite（例如日後遷移到 PostgreSQL），這把鎖視為
  不需要（PostgreSQL 原生支援多行程並發寫入），直接放行、不阻塞。

用法：
  後端（FastAPI，async 呼叫端）：
      from app.core.sync_lock import async_sync_lock
      async with async_sync_lock("模組名稱"):
          ...實際同步／DB 寫入邏輯...

  sync_tool.py（同步／threading 呼叫端，已在背景執行緒執行，可放心阻塞）：
      from app.core.sync_lock import sync_lock
      with sync_lock("模組名稱"):
          ...實際同步／DB 寫入邏輯...

  兩者共用同一個鎖檔案，async 版只是把「等待鎖」丟到 thread pool 執行，
  避免卡住 FastAPI 的事件迴圈；一旦拿到鎖，行為完全等價。
"""
import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Optional

from filelock import FileLock, Timeout

from app.core.config import settings

logger = logging.getLogger(__name__)

# 逾時預設 90 秒：略長於已知最長批次（購買同步約 67 秒），逾時就放棄本次同步，
# 寧可跳過這一輪、留給下一次排程重試，也不要無限期卡住整個佇列。
DEFAULT_TIMEOUT = 90.0

_SQLITE_URL_RE = re.compile(r"^sqlite(\+\w+)?:///")


def _lock_file_path() -> Optional[Path]:
    """
    鎖檔案路徑：跟 DATABASE_URL 指到的 portal.db 放同一個資料夾，命名 .sync.lock。
    若 DATABASE_URL 不是 SQLite（已遷移 PostgreSQL 等），回傳 None（不需要這把鎖）。
    """
    db_url = settings.DATABASE_URL
    m = _SQLITE_URL_RE.match(db_url)
    if not m:
        return None
    raw_path = db_url[m.end():]
    db_path = Path(raw_path).resolve()
    return db_path.parent / ".sync.lock"


def _make_lock(timeout: float) -> Optional[FileLock]:
    path = _lock_file_path()
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(path), timeout=timeout)


@contextmanager
def sync_lock(module_name: str = "", timeout: float = DEFAULT_TIMEOUT):
    """
    同步版跨行程鎖。給已經在背景執行緒（threading.Thread）執行的呼叫端使用
    （例如 sync_tool.py），可以放心阻塞等待，不會卡住任何事件迴圈。
    """
    lock = _make_lock(timeout)
    if lock is None:
        yield
        return
    try:
        with lock:
            yield
    except Timeout:
        logger.warning(
            "[SyncLock] %s 等待跨行程鎖逾時（%.0fs）："
            "可能有其他同步（sync_tool.py 或後端排程）正在進行中，本次略過",
            module_name or "(unnamed)",
            timeout,
        )
        raise


@asynccontextmanager
async def async_sync_lock(module_name: str = "", timeout: float = DEFAULT_TIMEOUT):
    """
    非同步版跨行程鎖。給 FastAPI 後端的 async 排程／路由使用：等待鎖的過程
    丟到 thread pool 執行，不會阻塞事件迴圈，伺服器仍可正常回應其他 HTTP 請求。

    2026-07-16 修正（重要）：
      filelock 套件預設 thread_local=True —— 鎖的內部狀態（file descriptor、
      lock_counter）是「每一條 OS 執行緒」各自保存一份，不是共用的。
      舊版寫法用 `loop.run_in_executor(None, lock.acquire)` 把 acquire() 丟到
      asyncio 預設 thread pool 的某個 worker 執行緒去等待/取得鎖，但後面的
      `lock.release()` 卻是在呼叫端（事件迴圈）那條執行緒直接呼叫——兩者是不同
      的 OS 執行緒。於是 release() 在事件迴圈執行緒看到的是全新、從未鎖過的
      context（is_locked 為 False），release() 內部的 `if self.is_locked:`
      直接跳過，變成完全無害、不會拋錯也不會記 log 的 no-op。結果：worker
      執行緒真正開啟的檔案控制代碼（lock_file_fd）永遠沒被關閉，底層 OS 鎖
      永遠卡在「鎖定」狀態，後面所有模組都會排隊等 90 秒逾時失敗——這正是
      「同步全部」批次執行時，第一個模組成功後、後面全部卡住逾時的根本原因
      （單一模組同步用的是 sync_lock()，acquire/release 都在同一條執行緒內
      直接呼叫，不會踩到這個問題，因此不受影響）。

      修法：用「單一 worker 執行緒」的 ThreadPoolExecutor，強制 acquire() 與
      release() 一定跑在同一條 OS 執行緒上，徹底避開 filelock 的 thread-local
      陷阱（不依賴特定 filelock 版本是否支援 thread_local=False 參數）。
    """
    lock = _make_lock(timeout)
    if lock is None:
        yield
        return
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        try:
            await loop.run_in_executor(executor, lock.acquire)
        except Timeout:
            logger.warning(
                "[SyncLock] %s 等待跨行程鎖逾時（%.0fs）："
                "可能有其他同步（sync_tool.py 或後端排程）正在進行中，本次略過",
                module_name or "(unnamed)",
                timeout,
            )
            raise
        try:
            yield
        finally:
            # release 也必須丟回「同一顆」單執行緒 executor，確保跟 acquire
            # 是同一條 OS 執行緒，這樣 filelock 的 thread-local context 才會
            # 對得起來，鎖才會真的被釋放。
            await loop.run_in_executor(executor, lock.release)
    finally:
        executor.shutdown(wait=False)
