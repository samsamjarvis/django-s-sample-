"""Context processor — SITE_SETTINGS + cart_count + site metadata."""
from __future__ import annotations

import logging

from django.conf import settings
from django.db.models import Count

logger = logging.getLogger("silver.context")


def _get_cart_count(request) -> int:
    try:
        from apps.orders.models import Cart
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            cart = (
                Cart.objects.filter(user=user, is_active=True)
                .annotate(_n=Count("items"))
                .first()
            )
        else:
            session = getattr(request, "session", None)
            session_key = getattr(session, "session_key", None) if session else None
            if not session_key:
                return 0
            cart = (
                Cart.objects.filter(
                    session_key=session_key, user__isnull=True, is_active=True,
                )
                .annotate(_n=Count("items"))
                .first()
            )
        return getattr(cart, "_n", 0)
    except Exception:
        logger.warning("cart_count_failed path=%s", getattr(request, "path", "-"))
        return 0


def _get_site_settings():
    """در DEBUG بدون cache — همیشه تازه از DB."""
    if settings.DEBUG:
        try:
            from apps.core.models import SiteSettings
            return SiteSettings.get_solo()
        except Exception:
            return None

    # Production: cache 60s
    from django.core.cache import cache
    obj = cache.get("site_settings_singleton")
    if obj is None:
        try:
            from apps.core.models import SiteSettings
            obj = SiteSettings.get_solo()
            cache.set("site_settings_singleton", obj, 60)
        except Exception:
            obj = None
    return obj


def site_context(request):
    site_name = getattr(settings, "SITE_NAME", "Silver")
    site_domain = getattr(settings, "SITE_DOMAIN", "localhost")
    site_protocol = getattr(settings, "SITE_PROTOCOL", "http")

    return {
        "SITE_NAME": site_name,
        "SITE_DOMAIN": site_domain,
        "SITE_PROTOCOL": site_protocol,
        "SITE_URL": f"{site_protocol}://{site_domain}",
        "SITE_SETTINGS": _get_site_settings(),
        "ADMIN_LOGIN_ENABLED": getattr(settings, "ADMIN_LOGIN_ENABLED", True),
        "APP_VERSION": getattr(settings, "APP_VERSION", "1.0.0"),
        "current_path": request.path,
        "request_id": getattr(request, "request_id", ""),
        "cart_count": _get_cart_count(request),
        "DEBUG": settings.DEBUG,
    }
