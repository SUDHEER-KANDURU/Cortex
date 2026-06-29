"""Celery application factory."""

from celery import Celery
from cortex.config import get_settings


def create_celery() -> Celery:
    """Create and configure the Celery app."""
    settings = get_settings()

    app = Celery(
        "cortex",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["cortex.pipeline.infrastructure.celery_tasks"],
    )

    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
    )

    return app


celery_app = create_celery()
