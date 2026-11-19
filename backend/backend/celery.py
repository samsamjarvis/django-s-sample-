"""Celery app برای Silver."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# نام attribute `celery` (نه `app`) — چون celery -A backend.celery
# به‌طور پیش‌فرض دنبال attribute به اسم `celery` می‌گردد
celery = Celery("silver")
celery.config_from_object("django.conf:settings", namespace="CELERY")
celery.autodiscover_tasks()

# alias برای backward compatibility
app = celery


@celery.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
