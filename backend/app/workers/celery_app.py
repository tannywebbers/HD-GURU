from __future__ import annotations

import datetime as dt
import socket

from celery import Celery
from celery.signals import (
    task_postrun,
    task_prerun,
    worker_ready,
    worker_shutdown,
)

from app.core.config import settings

celery_app = Celery(
    "hd_guru",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="uploads",
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_TASK_EAGER_PROPAGATES,
    task_soft_time_limit=settings.WORKER_TASK_TIMEOUT,
    task_time_limit=settings.WORKER_TASK_TIMEOUT * 2,
    beat_schedule={
        "cleanup-expired-media": {
            "task": "uploads.cleanup_expired",
            "schedule": 3600.0,
        },
        "analytics-retention": {
            "task": "analytics.retention_run",
            "schedule": 24 * 3600.0,
        },
    },
)

from app.workers import tasks  # noqa: E402,F401  (register tasks)


def _current_hostname(sender) -> str:
    return getattr(sender, "hostname", None) or socket.gethostname()


def _update_worker(
    *,
    name: str,
    status: str,
    current_job_id: str | None = None,
) -> None:
    """Persist worker status records used by health + readiness checks."""
    try:
        from app.core.database import SessionLocal
        from app.models.enums import WorkerStatus
        from app.models.worker import Worker
        from app.services import system_log_service

        now = dt.datetime.now(dt.timezone.utc)
        with SessionLocal() as db:
            worker = db.query(Worker).filter(Worker.name == name).first()
            if worker is None:
                db.add(
                    Worker(
                        name=name,
                        hostname=name,
                        status=status,
                        last_heartbeat=now,
                        started_at=now if status != WorkerStatus.OFFLINE else None,
                    )
                )
            else:
                worker.status = status
                worker.last_heartbeat = now
                worker.current_job_id = current_job_id
                if status == WorkerStatus.OFFLINE:
                    worker.started_at = None
            db.commit()
        system_log_service.record_worker_status(
            worker=name,
            status=status.value if hasattr(status, "value") else str(status),
        )
    except Exception:
        # Health checks must never crash because bookkeeping failed.
        pass


@worker_ready.connect
def _on_ready(sender, **kwargs):
    from app.models.enums import WorkerStatus

    _update_worker(name=_current_hostname(sender), status=WorkerStatus.IDLE)


@worker_shutdown.connect
def _on_shutdown(sender, **kwargs):
    from app.models.enums import WorkerStatus

    _update_worker(name=_current_hostname(sender), status=WorkerStatus.OFFLINE)


@task_prerun.connect
def _on_task_prerun(sender, task_id, task, **kwargs):
    from app.models.enums import WorkerStatus

    _update_worker(
        name=_current_hostname(sender),
        status=WorkerStatus.BUSY,
        current_job_id=task_id,
    )


@task_postrun.connect
def _on_task_postrun(sender, task_id, task, **kwargs):
    from app.models.enums import WorkerStatus

    _update_worker(
        name=_current_hostname(sender),
        status=WorkerStatus.IDLE,
        current_job_id=None,
    )
