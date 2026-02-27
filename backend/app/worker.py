"""
Celery worker entry point.

Start with:
    celery -A app.worker worker --loglevel=info

The import of celery_app triggers task registration via the `include` list
in app/tasks/__init__.py.
"""

from app.tasks import celery_app  # noqa: F401 — side-effect import registers tasks
