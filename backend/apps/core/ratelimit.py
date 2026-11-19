"""
Rate limiting decorators — همه‌ی مسیرهای حساس باید از این‌ها استفاده کنند.
پاسخ: HTML → redirect با پیام؛ AJAX → JSON 429.
"""
from __future__ import annotations

from functools import wraps

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django_ratelimit.core import is_ratelimited
from django_ratelimit.exceptions import Ratelimited


def _wants_json(request) -> bool:
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )


def ratelimit(key: str = "ip", rate: str = "10/m", method: str = "POST",
              block: bool = True, message: str = "تعداد درخواست‌ها زیاد است. کمی بعد تلاش کنید."):
    """
    Decorator — به‌جای raise، پاسخ نرم برمی‌گرداند.

    مثال:
        @ratelimit(key="ip", rate="5/m")
        def login_view(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            limited = is_ratelimited(
                request=request, group=None, fn=view_func,
                key=key, rate=rate, method=method,
                increment=True,
            )
            if limited:
                if _wants_json(request):
                    return JsonResponse(
                        {"ok": False, "error": "rate_limited", "message": message},
                        status=429,
                    )
                messages.error(request, message)
                return redirect(request.META.get("HTTP_REFERER") or "/")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def ratelimit_view(view_func):
    """تبدیل Ratelimited exception به پاسخ نرم."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Ratelimited:
            if _wants_json(request):
                return JsonResponse(
                    {"ok": False, "error": "rate_limited"},
                    status=429,
                )
            messages.error(request, "تعداد درخواست‌ها زیاد است.")
            return redirect(request.META.get("HTTP_REFERER") or "/")
    return wrapper