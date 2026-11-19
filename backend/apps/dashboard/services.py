"""
Dashboard Service — Audit log + اعلان ادمین.
"""
from __future__ import annotations

import logging
from typing import Iterable, Optional

from django.contrib.auth import get_user_model

from apps.dashboard.models import AdminNotification, AuditLog

logger = logging.getLogger("silver.dashboard")
User = get_user_model()


def log_action(
    *, user, action: str, model_name: str = "", object_id="",
    changes: Optional[dict] = None, request=None,
) -> AuditLog:
    ip = None
    ua = ""
    if request is not None:
        ip = request.META.get("REMOTE_ADDR")
        ua = request.META.get("HTTP_USER_AGENT", "")[:300]
    entry = AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action, model_name=model_name, object_id=str(object_id or ""),
        changes=changes or {}, ip=ip, user_agent=ua,
    )
    logger.info("audit action=%s model=%s obj=%s", action, model_name, object_id)
    return entry


def notify_admins(
    title: str, message: str = "", url: str = "", *,
    staff_only: bool = True, users: Optional[Iterable] = None,
) -> int:
    """اعلان به ادمین‌ها — از on_commit صدا زده شود."""
    if users is not None:
        recipients = users
    elif staff_only:
        recipients = User.objects.filter(is_staff=True, is_active=True)
    else:
        recipients = User.objects.filter(is_active=True)
    count = 0
    for u in recipients:
        AdminNotification.objects.create(user=u, title=title, message=message, url=url)
        count += 1
    return count


def mark_notification_read(notification: AdminNotification) -> AdminNotification:
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return notification


def recent_audit(limit: int = 100):
    return AuditLog.objects.select_related("user").order_by("-created_at")[:limit]