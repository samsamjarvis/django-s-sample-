"""Custom middleware — admin hide + session + seo + log + error."""
from __future__ import annotations

import logging
import time
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.db.models import F
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render

logger = logging.getLogger("silver")


class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_prefix = "/" + settings.ADMIN_URL.strip("/") + "/"

    def __call__(self, request):
        if request.path.startswith(self.admin_prefix):
            if not settings.ADMIN_LOGIN_ENABLED and not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")
            if not (request.user.is_staff or request.user.is_superuser):
                if not request.user.is_authenticated:
                    return redirect(f"{settings.LOGIN_URL}?next={request.path}")
                raise Http404
        return self.get_response(request)


class SessionPasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                from apps.accounts import session_security
                if not session_security.check_session_password_stamp(request):
                    auth_logout(request)
                    messages.error(request, "به دلیل تغییر رمز، دوباره وارد شوید.")
                    return redirect(settings.LOGIN_URL)
            except ImportError:
                pass
        return self.get_response(request)


class SeoMiddleware:
    NOINDEX_PREFIXES = (
        "/admin/", "/panel/", "/my/", "/cart/", "/orders/",
        "/payment/", "/auth/", "/customers/", "/crm/", "/health/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in ("GET", "HEAD"):
            try:
                from apps.seo.models import Redirect
                r = Redirect.objects.filter(
                    from_path=request.path, is_active=True,
                ).first()
                if r:
                    Redirect.objects.filter(pk=r.pk).update(hits=F("hits") + 1)
                    return HttpResponseRedirect(r.to_path, status=r.status_code)
            except Exception:
                pass

        request.seo_noindex = any(
            request.path.startswith(p) for p in self.NOINDEX_PREFIXES
        )
        return self.get_response(request)


class RequestLoggingMiddleware:
    SKIP_PATHS = ("/health/", "/health/live/", "/health/ready/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        skip = any(request.path.startswith(p) for p in self.SKIP_PATHS)
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.request_id = request_id
        started = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - started) * 1000
        response["X-Request-ID"] = request_id
        if not skip:
            logger.info(
                "req=%s method=%s path=%s status=%s dur_ms=%.1f ip=%s",
                request_id, request.method, request.path,
                getattr(response, "status_code", "?"), duration_ms,
                request.META.get("REMOTE_ADDR", "-"),
            )
        return response


class ErrorHandlingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Http404:
            raise
        except Exception:
            logger.exception("Unhandled req=%s path=%s",
                             getattr(request, "request_id", "-"), request.path)
            is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
            if is_ajax:
                return JsonResponse(
                    {"ok": False, "error": "server_error",
                     "message": "خطای غیرمنتظره. لطفاً دوباره تلاش کنید.",
                     "request_id": getattr(request, "request_id", "")},
                    status=500,
                )
            return render(request, "500.html", status=500)
