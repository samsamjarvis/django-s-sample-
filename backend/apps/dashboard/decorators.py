"""
Dashboard Decorators — دسترسی و امنیت ویوهای پنل.
"""
from __future__ import annotations

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse


def _wants_json(request) -> bool:
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )


def staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if _wants_json(request):
                return JsonResponse({"ok": False, "error": "auth_required"}, status=401)
            return redirect_to_login(request.get_full_path(), login_url=reverse("accounts:login"))
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def superuser_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if _wants_json(request):
                return JsonResponse({"ok": False, "error": "auth_required"}, status=401)
            return redirect_to_login(request.get_full_path(), login_url=reverse("accounts:login"))
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper