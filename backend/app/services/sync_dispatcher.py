"""
sync_dispatcher.py — Sync 函數註冊表（Dispatcher）

用途：
  將 module_key 字串對映到對應的 sync 函數，
  讓 sync_service.run_sync() 能依 RagicConnection.module_key 分派同步工作。

使用方式：
  在各 sync 服務的入口函數上加 @register("module_key")：

    from app.services.sync_dispatcher import register

    @register("security_patrol")
    async def sync_all() -> dict:
        ...

  呼叫時：
    from app.services.sync_dispatcher import dispatch
    result = await dispatch("security_patrol")

注意：
  SYNC_REGISTRY 在各 sync 模組被 import 時自動填入。
  請確保在呼叫 dispatch() 前已 import 過所有 sync 服務（例如在 lifespan startup）。
"""
import asyncio
import inspect
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

# module_key → callable (sync or async)
SYNC_REGISTRY: dict[str, Callable[[], Any]] = {}


def register(module_key: str):
    """
    Decorator：將 sync 入口函數註冊到 SYNC_REGISTRY。
    支援 async def 和 def 兩種形式。

    用法：
        @register("inventory")
        async def sync_from_ragic() -> dict:
            ...
    """
    def decorator(fn: Callable) -> Callable:
        if module_key in SYNC_REGISTRY:
            logger.warning(
                f"[Dispatcher] module_key '{module_key}' 已被 "
                f"{SYNC_REGISTRY[module_key].__module__} 註冊，將被覆蓋"
            )
        SYNC_REGISTRY[module_key] = fn
        logger.debug(f"[Dispatcher] 已註冊：{module_key} → {fn.__module__}.{fn.__name__}")
        return fn
    return decorator


async def dispatch(module_key: str) -> dict:
    """
    依 module_key 找到對應的 sync 函數並執行。
    自動處理 async / sync 兩種函數形式。

    回傳：sync 函數的 dict 結果，或錯誤說明。
    """
    fn = SYNC_REGISTRY.get(module_key)
    if fn is None:
        logger.error(f"[Dispatcher] 未知 module_key: '{module_key}'，已註冊：{list(SYNC_REGISTRY.keys())}")
        return {
            "fetched": 0,
            "upserted": 0,
            "errors": [f"未知 module_key: '{module_key}'，請檢查 RagicConnection 設定"],
        }

    try:
        if inspect.iscoroutinefunction(fn):
            result = await fn()
        else:
            # 同步函數：在 thread pool 執行，避免阻塞 event loop
            result = await asyncio.get_event_loop().run_in_executor(None, fn)
        return result if isinstance(result, dict) else {"fetched": 0, "upserted": 0, "errors": []}
    except Exception as exc:
        logger.exception(f"[Dispatcher] module_key='{module_key}' 執行失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "errors": [str(exc)]}


def list_registered() -> list[str]:
    """回傳目前已註冊的所有 module_key（除錯用）"""
    return sorted(SYNC_REGISTRY.keys())
