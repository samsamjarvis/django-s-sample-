"""Health endpoints — liveness / readiness / full."""
from __future__ import annotations

import logging
import os
import sys

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

logger = logging.getLogger("silver.health")


@require_GET
@never_cache
@csrf_exempt
def liveness(request):
    return JsonResponse({"ok": True, "status": "alive"})


@require_GET
@never_cache
@csrf_exempt
def readiness(request):
    checks = {}
    healthy = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
        healthy = False
        logger.error("health_db_error: %s", exc)

    try:
        cache.set("__health__", "ok", timeout=5)
        if cache.get("__health__") == "ok":
            checks["cache"] = "ok"
        else:
            checks["cache"] = "mismatch"
            healthy = False
    except Exception as exc:
        checks["cache"] = f"error: {type(exc).__name__}"
        healthy = False
        logger.error("health_cache_error: %s", exc)

    return JsonResponse(
        {"ok": healthy, "checks": checks},
        status=200 if healthy else 503,
    )


@require_GET
@never_cache
@csrf_exempt
def full(request):
    return JsonResponse({
        "ok": True,
        "version": os.environ.get("APP_VERSION", "dev"),
        "debug": settings.DEBUG,
        "python": sys.version.split()[0],
        "site": getattr(settings, "SITE_DOMAIN", ""),
    })
