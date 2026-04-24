from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import settings

scheduler = BackgroundScheduler()


def start_scheduler():
    if not settings.SCHEDULER_ENABLED:
        return
    from app.services.sync_service import sync_all_active

    scheduler.add_job(
        sync_all_active,
        trigger="interval",
        minutes=60,
        id="ragic_sync_all",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
