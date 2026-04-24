"""
全域 APScheduler 單例 + RagicConnection Job 管理 helpers

設計：
  - scheduler 在此模組建立，由 main.py lifespan 負責 start() / shutdown()
  - register_connection_job / deregister_connection_job 供 ragic router 在 CRUD 時呼叫
  - 所有 RagicConnection 排程 job ID 格式：f"ragic_conn_{conn_id}"
  - 硬編碼模組同步（_auto_sync）的 job ID 為 "module_auto_sync"，互不干擾
  - 所有 interval 均使用 CronTrigger 對齊整點（e.g. 30 分鐘 → :00 / :30）
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# 全域單例——由 main.py lifespan 負責啟動與關閉
scheduler = AsyncIOScheduler()

_CONN_JOB_PREFIX = "ragic_conn_"


def _job_id(conn_id: str) -> str:
    return f"{_CONN_JOB_PREFIX}{conn_id}"


def make_cron_trigger(minutes: int) -> CronTrigger:
    """
    將分鐘間隔轉換為對齊整點的 CronTrigger。

    minutes < 60  → 每小時固定分鐘觸發（e.g. 15 → :00/:15/:30/:45）
    minutes >= 60 → 每 N 小時整點觸發  （e.g. 120 → 0:00/2:00/4:00...）
    """
    m = max(1, minutes)
    if m < 60:
        step = m
        minute_vals = ",".join(str(i) for i in range(0, 60, step))
        return CronTrigger(minute=minute_vals)
    else:
        hours = m // 60
        return CronTrigger(hour=f"*/{hours}", minute="0")


def register_connection_job(conn_id: str, interval_minutes: int) -> None:
    """
    新增或更新指定 RagicConnection 的排程任務。

    若 job 已存在則重新排程（reschedule）；否則新增。
    排程觸發時呼叫 sync_service.run_sync(conn_id, triggered_by="scheduler")。
    """
    # 延遲 import 避免啟動時循環依賴
    from app.services.sync_service import run_sync

    jid = _job_id(conn_id)
    trigger = make_cron_trigger(interval_minutes)

    if scheduler.get_job(jid):
        scheduler.reschedule_job(jid, trigger=trigger)
    else:
        scheduler.add_job(
            run_sync,
            trigger=trigger,
            args=[conn_id, "scheduler"],
            id=jid,
            replace_existing=True,
            misfire_grace_time=300,  # 5 分鐘寬限
        )


def deregister_connection_job(conn_id: str) -> None:
    """移除指定 RagicConnection 的排程任務（若存在）。"""
    jid = _job_id(conn_id)
    if scheduler.get_job(jid):
        scheduler.remove_job(jid)


# ── 模組自動同步間隔（hardcoded modules）─────────────────────────────────────
_MODULE_JOB_ID = "module_auto_sync"
_module_sync_interval: int = 30   # 預設 30 分鐘，可透過 API 動態修改


def get_module_sync_interval() -> int:
    """回傳目前硬編碼模組的自動同步間隔（分鐘）。"""
    return _module_sync_interval


def set_module_sync_interval(minutes: int) -> None:
    """
    變更硬編碼模組的自動同步間隔，即時重新排程（CronTrigger 對齊整點）。
    注意：此設定為 in-memory，服務重啟後恢復預設 30 分鐘。
    """
    global _module_sync_interval
    _module_sync_interval = max(5, minutes)
    trigger = make_cron_trigger(_module_sync_interval)
    if scheduler.get_job(_MODULE_JOB_ID):
        scheduler.reschedule_job(_MODULE_JOB_ID, trigger=trigger)


def list_connection_jobs() -> list[dict]:
    """
    回傳目前已排程的 RagicConnection jobs 摘要清單。
    用於 GET /api/v1/ragic/scheduler/status。
    """
    result = []
    for job in scheduler.get_jobs():
        if not job.id.startswith(_CONN_JOB_PREFIX):
            continue
        conn_id = job.id[len(_CONN_JOB_PREFIX):]
        next_run = job.next_run_time
        result.append({
            "conn_id":      conn_id,
            "job_id":       job.id,
            "next_run_at":  next_run.isoformat() if next_run else None,
            "trigger":      str(job.trigger),
        })
    return result
