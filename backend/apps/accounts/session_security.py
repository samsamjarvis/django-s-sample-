"""
Session security — invalidate روی تغییر رمز، lifetime ادمین.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.utils import timezone

from apps.accounts.models import SecurityEvent, User

logger = logging.getLogger("silver.session")


def stamp_session_after_login(request, user: User) -> None:
    """پس از login: ثبت password_changed_at در session."""
    request.session["pwd_stamp"] = (
        user.password_changed_at.timestamp() if user.password_changed_at else 0
    )
    # تنظیم انقضا برای ادمین
    if user.is_staff or user.is_superuser:
        admin_age = getattr(settings, "ADMIN_SESSION_AGE", 8 * 3600)
        request.session.set_expiry(admin_age)
    else:
        request.session.set_expiry(settings.SESSION_COOKIE_AGE)


def check_session_password_stamp(request) -> bool:
    """
    True اگر session معتبر، False اگر باید logout شود.
    در middleware صدا زده می‌شود.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return True

    stamped = request.session.get("pwd_stamp", None)
    current = (
        user.password_changed_at.timestamp() if user.password_changed_at else 0
    )
    if stamped is None:
        # session قدیمی — اجازه بده ولی stamp کن
        request.session["pwd_stamp"] = current
        return True
    if stamped != current:
        logger.warning(
            "session_invalidated user=%s old=%s new=%s",
            user.id, stamped, current,
        )
        SecurityEvent.objects.create(
            user=user,
            event_type=SecurityEvent.TYPE_SESSION_INVALIDATED,
            ip=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
            detail={"reason": "password_changed"},
        )
        return False
    return True


def force_logout_all_sessions(user: User, *, request=None, reason: str = "") -> None:
    """
    ابطال همه نشست‌ها — با bump password_changed_at.
    کاربر جاری هم logout می‌شود.
    """
    user.password_changed_at = timezone.now()
    user.save(update_fields=["password_changed_at", "updated_at"])
    SecurityEvent.objects.create(
        user=user,
        event_type=SecurityEvent.TYPE_SESSION_INVALIDATED,
        ip=(request.META.get("REMOTE_ADDR") if request else None),
        detail={"reason": reason or "manual"},
    )
    logger.info("force_logout_all user=%s reason=%s", user.id, reason)