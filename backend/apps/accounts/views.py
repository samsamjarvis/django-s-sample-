import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, update_session_auth_hash
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods, require_POST

from apps.accounts import session_security
from apps.accounts import twofa
from apps.accounts.forms import (
    LoginForm, PasswordChangeForm, PasswordResetConfirmForm,
    PasswordResetRequestForm, PasswordResetVerifyForm, ProfileForm,
    SignupForm, TwoFactorDisableForm, TwoFactorMethodChoiceForm,
    TwoFactorSetupConfirmForm, TwoFactorVerifyForm,
)
from apps.accounts.masking import mask_email
from apps.accounts.models import SecurityEvent
from apps.core.ratelimit import ratelimit
from apps.sms import services as sms_services
from backend.security import hmac_sign

logger = logging.getLogger("silver.accounts")
User = get_user_model()


# ───────────── helpers ─────────────
def _safe_next(request, default="/"):
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return default


def _stamp_and_login(request, user):
    auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    session_security.stamp_session_after_login(request, user)
    user.last_login_ip = request.META.get("REMOTE_ADDR")
    user.last_login_user_agent = request.META.get("HTTP_USER_AGENT", "")[:300]
    user.save(update_fields=["last_login_ip", "last_login_user_agent"])


# ═════════════ Login / Logout ═════════════
@never_cache
@csrf_protect
@ratelimit(key="ip", rate="10/m")
@ratelimit(key="post:email", rate="5/5m")
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect(_safe_next(request))

    form = LoginForm(request.POST or None)
    error = None

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        password = form.cleaned_data["password"]
        user = authenticate(request, email=email, password=password)

        if user is None:
            error = "ایمیل یا رمز عبور نادرست است."
            SecurityEvent.objects.create(
                event_type=SecurityEvent.TYPE_LOGIN_FAILED,
                ip=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
                email_attempted=email,
            )
            logger.warning("login_failed email=%s ip=%s",
                           mask_email(email), request.META.get("REMOTE_ADDR"))

        elif not user.is_active:
            error = "حساب غیرفعال است."

        elif user.two_factor_enabled:
            # ذخیره pending — هنوز login نکن
            request.session["pending_2fa_user_id"] = user.id
            request.session["pending_2fa_next"] = _safe_next(request)
            request.session["pending_2fa_started"] = timezone.now().isoformat()
            return redirect("accounts:two_factor_verify")

        else:
            _stamp_and_login(request, user)
            SecurityEvent.objects.create(
                user=user,
                event_type=SecurityEvent.TYPE_LOGIN_SUCCESS,
                ip=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
            )
            messages.success(request, "خوش آمدید!")
            return redirect(_safe_next(request))

    return render(request, "accounts/login.html", {
        "form": form, "error": error, "next": request.GET.get("next", ""),
    })


@never_cache
@csrf_protect
@ratelimit(key="ip", rate="20/m")
@require_http_methods(["GET", "POST"])
def two_factor_verify(request):
    """صفحه تأیید 2FA در login — پشتیبانی TOTP + SMS + recovery."""
    user_id = request.session.get("pending_2fa_user_id")
    if not user_id:
        messages.error(request, "جلسه منقضی شد. دوباره وارد شوید.")
        return redirect("accounts:login")

    # منقضی شدن pending بعد از ۵ دقیقه
    started_iso = request.session.get("pending_2fa_started", "")
    if started_iso:
        try:
            started = timezone.datetime.fromisoformat(started_iso)
            if timezone.is_naive(started):
                started = timezone.make_aware(started, timezone.get_current_timezone())
            if (timezone.now() - started).total_seconds() > 300:
                request.session.pop("pending_2fa_user_id", None)
                messages.error(request, "زمان تأیید منقضی شد. دوباره وارد شوید.")
                return redirect("accounts:login")
        except (ValueError, TypeError):
            pass

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect("accounts:login")

    method = request.POST.get("method", "totp") or "totp"
    form = TwoFactorMethodChoiceForm(request.POST or None)
    error = None
    info = None

    if request.method == "POST":
        action = request.POST.get("action", "")
        # action = send_sms | verify
        if action == "send_sms":
            try:
                twofa.send_sms_otp(user, request=request)
                info = "کد پیامک ارسال شد."
                method = "sms"
                form = TwoFactorMethodChoiceForm(initial={"method": "sms"})
            except twofa.TwoFAError as exc:
                error = str(exc)
        elif form.is_valid():
            code = form.cleaned_data["code"]
            ok = False
            if method == "totp":
                ok = twofa.verify_totp(user, code, request=request)
            elif method == "sms":
                ok = twofa.verify_sms_otp(user, code, request=request)
            elif method == "recovery":
                ok = twofa.verify_recovery_code(user, code, request=request)

            if ok:
                nxt = request.session.pop("pending_2fa_next", "/")
                request.session.pop("pending_2fa_user_id", None)
                request.session.pop("pending_2fa_started", None)
                _stamp_and_login(request, user)
                SecurityEvent.objects.create(
                    user=user,
                    event_type=SecurityEvent.TYPE_LOGIN_SUCCESS,
                    ip=request.META.get("REMOTE_ADDR"),
                    detail={"via_2fa": True, "method": method},
                )
                messages.success(request, "ورود موفق!")
                return redirect(nxt or "/")
            error = "کد نادرست یا منقضی است."
            method = form.cleaned_data.get("method") or method
        else:
            # فرم invalid — پیام خطا بده
            for field_errors in form.errors.values():
                error = field_errors[0]
                break

    return render(request, "accounts/two_factor.html", {
        "form": form, "error": error, "info": info,
        "method": method,
        "has_phone": bool(user.phone),
        "recovery_remaining": twofa.recovery_codes_remaining(user),
    })


@login_required
@require_http_methods(["GET", "POST"])
def logout_view(request):
    """خروج — POST امن یا GET با ?confirm=1، در غیر این صورت صفحه تأیید."""
    if request.method == "POST" or request.GET.get("confirm") == "1":
        user = request.user
        SecurityEvent.objects.create(
            user=user,
            event_type=SecurityEvent.TYPE_LOGOUT,
            ip=request.META.get("REMOTE_ADDR"),
        )
        auth_logout(request)
        messages.success(request, "با موفقیت خارج شدید.")
        return redirect("core:home")
    return render(request, "accounts/logout_confirm.html")


# ═════════════ Signup / Profile ═════════════
@never_cache
@csrf_protect
@ratelimit(key="ip", rate="3/h")
@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("core:home")

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = form.save()
        except Exception:
            logger.exception("signup_failed")
            form.add_error(None, "خطا در ثبت‌نام. دوباره تلاش کنید.")
        else:
            _stamp_and_login(request, user)
            messages.success(request, "حساب شما ساخته شد!")
            return redirect("core:home")
    return render(request, "accounts/signup.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "پروفایل به‌روز شد.")
        return redirect("accounts:profile")

    # داده‌های 2FA برای نمایش
    recovery_remaining = twofa.recovery_codes_remaining(request.user)
    return render(request, "accounts/profile.html", {
        "form": form, "user": request.user,
        "recovery_remaining": recovery_remaining,
    })


# ═════════════ Password Change ═════════════
@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="5/h")
def password_change(request):
    form = PasswordChangeForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        request.user.set_password(form.cleaned_data["new_password1"])
        request.user.password_changed_at = timezone.now()
        request.user.save(update_fields=["password", "password_changed_at", "updated_at"])
        update_session_auth_hash(request, request.user)
        session_security.stamp_session_after_login(request, request.user)

        SecurityEvent.objects.create(
            user=request.user,
            event_type=SecurityEvent.TYPE_PASSWORD_CHANGED,
            ip=request.META.get("REMOTE_ADDR"),
        )
        messages.success(request, "رمز شما تغییر کرد.")
        return redirect("accounts:profile")
    return render(request, "accounts/password_change.html", {"form": form})


# ═════════════ Password Reset (via SMS OTP) ═════════════
@never_cache
@csrf_protect
@ratelimit(key="ip", rate="3/h")
@require_http_methods(["GET", "POST"])
def password_reset_request(request):
    """مرحله ۱: کاربر ایمیل می‌دهد → OTP به تلفنش می‌رود."""
    form = PasswordResetRequestForm(request.POST or None)
    error = None

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        user = User.objects.filter(email=email, is_active=True).first()
        # پیام یکسان حتی اگر کاربر نباشد (جلوگیری از user enumeration)
        generic_msg = (
            "اگر حسابی با این ایمیل و شماره تلفن ثبت‌شده باشد، "
            "کد بازیابی پیامک شد."
        )
        if user and user.phone:
            try:
                sms_services.send_otp(
                    user.phone, purpose="password_reset",
                    user=user, ip=request.META.get("REMOTE_ADDR"),
                )
                request.session["pwd_reset_user_id"] = user.id
                messages.success(request, generic_msg)
                return redirect("accounts:password_reset_verify")
            except sms_services.SMSVerificationError as exc:
                logger.warning("pwd_reset_sms_failed user=%s err=%s", user.id, exc)
                error = "ارسال پیامک ناموفق بود. بعداً تلاش کنید."
        else:
            # بدون افشا
            messages.success(request, generic_msg)
            return redirect("accounts:login")

    return render(request, "accounts/password_reset_request.html", {
        "form": form, "error": error,
    })


@never_cache
@csrf_protect
@ratelimit(key="ip", rate="10/m")
@require_http_methods(["GET", "POST"])
def password_reset_verify(request):
    """مرحله ۲: کد پیامک → session تأیید."""
    user_id = request.session.get("pwd_reset_user_id")
    if not user_id:
        messages.error(request, "جلسه منقضی شد.")
        return redirect("accounts:password_reset_request")
    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return redirect("accounts:password_reset_request")

    form = PasswordResetVerifyForm(request.POST or None)
    error = None
    if request.method == "POST" and form.is_valid():
        try:
            sms_services.verify_otp(
                user.phone, purpose="password_reset",
                code=form.cleaned_data["code"],
            )
            request.session["pwd_reset_verified"] = True
            return redirect("accounts:password_reset_confirm")
        except sms_services.SMSVerificationError as exc:
            error = str(exc)

    return render(request, "accounts/password_reset_verify.html", {
        "form": form, "error": error,
    })


@never_cache
@csrf_protect
@require_http_methods(["GET", "POST"])
def password_reset_confirm(request):
    """مرحله ۳: رمز جدید."""
    if not request.session.get("pwd_reset_verified"):
        return redirect("accounts:password_reset_request")
    user_id = request.session.get("pwd_reset_user_id")
    if not user_id:
        return redirect("accounts:password_reset_request")
    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return redirect("accounts:password_reset_request")

    form = PasswordResetConfirmForm(request.POST or None)
    error = None
    if request.method == "POST" and form.is_valid():
        user.set_password(form.cleaned_data["password1"])
        user.password_changed_at = timezone.now()
        user.save(update_fields=["password", "password_changed_at", "updated_at"])
        SecurityEvent.objects.create(
            user=user,
            event_type=SecurityEvent.TYPE_PASSWORD_RESET,
            ip=request.META.get("REMOTE_ADDR"),
        )
        # پاک کردن session pending
        for k in ("pwd_reset_user_id", "pwd_reset_verified"):
            request.session.pop(k, None)
        messages.success(request, "رمز شما بازیابی شد. اکنون وارد شوید.")
        return redirect("accounts:login")

    return render(request, "accounts/password_reset_confirm.html", {
        "form": form, "error": error,
    })


# ═════════════ 2FA Setup / Manage ═════════════
@login_required
@require_http_methods(["GET", "POST"])
def twofa_setup(request):
    """شروع راه‌اندازی TOTP — نمایش QR."""
    if request.user.two_factor_enabled:
        messages.info(request, "۲FA از قبل فعال است.")
        return redirect("accounts:twofa_manage")

    try:
        data = twofa.prepare_totp(request.user)
    except twofa.TwoFAError as exc:
        messages.error(request, str(exc))
        return redirect("accounts:profile")

    return render(request, "accounts/twofa_setup.html", {
        "secret": data["secret"],
        "uri": data["uri"],
        "qr_base64": data["qr_base64"],
    })


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="user", rate="10/m")
def twofa_setup_confirm(request):
    """تأیید کد ۶ رقمی TOTP — فعال‌سازی + نمایش recovery codes."""
    if request.user.two_factor_enabled:
        return redirect("accounts:twofa_manage")

    form = TwoFactorSetupConfirmForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            raw_codes = twofa.confirm_totp(
                request.user, form.cleaned_data["code"], request=request,
            )
        except twofa.TwoFAError as exc:
            messages.error(request, str(exc))
        else:
            # فقط یک‌بار نمایش داده می‌شوند
            request.session["_recovery_codes_shown_once"] = raw_codes
            return redirect("accounts:twofa_recovery_codes")

    return render(request, "accounts/twofa_setup_confirm.html", {"form": form})


@login_required
@require_http_methods(["GET"])
def twofa_recovery_codes(request):
    """نمایش یک‌باره recovery codes."""
    codes = request.session.pop("_recovery_codes_shown_once", None)
    if not codes:
        return redirect("accounts:twofa_manage")
    return render(request, "accounts/twofa_recovery_codes.html", {"codes": codes})


@login_required
@require_http_methods(["GET", "POST"])
def twofa_manage(request):
    """مدیریت 2FA — غیرفعال‌سازی، تولید مجدد codes."""
    return render(request, "accounts/twofa_manage.html", {
        "recovery_remaining": twofa.recovery_codes_remaining(request.user),
    })


@login_required
@require_POST
@ratelimit(key="user", rate="5/h")
def twofa_disable(request):
    form = TwoFactorDisableForm(request.POST)
    if form.is_valid():
        try:
            twofa.disable_twofa(
                request.user, password=form.cleaned_data["password"], request=request,
            )
        except twofa.TwoFAError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "۲FA غیرفعال شد.")
    else:
        messages.error(request, "رمز عبور را وارد کنید.")
    return redirect("accounts:twofa_manage")


@login_required
@require_POST
@ratelimit(key="user", rate="3/h")
def twofa_regenerate_recovery(request):
    try:
        raw_codes = twofa.regenerate_recovery_codes(request.user, request=request)
        request.session["_recovery_codes_shown_once"] = raw_codes
        return redirect("accounts:twofa_recovery_codes")
    except twofa.TwoFAError as exc:
        messages.error(request, str(exc))
        return redirect("accounts:twofa_manage")