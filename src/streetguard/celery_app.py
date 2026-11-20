from celery import Celery

from streetguard.config import get_settings

settings = get_settings()
celery_app = Celery(
    "streetguard",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["streetguard.workers.detection"],
)
celery_app.conf.update(
    task_default_queue="detection",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)
