"""
TwoFA Service — TOTP + SMS + Recovery Codes.
تمام منطق 2FA این‌جا. ویوها فقط این سرویس را صدا می‌زنند.
"""
from __future__ import annotations

import logging
import secrets
from typing import Optional

import pyotp
import qrcode
from django.db import transaction
from django.utils import timezone
from io import BytesIO
import base64

from apps.accounts.masking import mask_email, mask_phone
from apps.accounts.models import RecoveryCode, SecurityEvent, User
from apps.sms import services as sms_services
from backend.security import hmac_sign

logger = logging.getLogger("silver.2fa")


class TwoFAError(Exception):
    pass


ISSUER_NAME = "Silver"
TOTP_VALID_WINDOW = 1  # اجازه ±30s انحراف ساعت
RECOVERY_CODE_COUNT = 10


# ─────────── Security event helper ───────────
def _log_event(
    *, user: Optional[User], event_type: str,
    request=None, email_attempted: str = "", detail: Optional[dict] = None,
) -> SecurityEvent:
    return SecurityEvent.objects.create(
        user=user,
        event_type=event_type,
        ip=(request.META.get("REMOTE_ADDR") if request else None),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:300] if request else ""),
        email_attempted=email_attempted[:254],
        detail=detail or {},
    )


def log_security_event(*args, **kwargs) -> SecurityEvent:
    """Public wrapper — برای استفاده از viewها و سیگنال‌ها."""
    return _log_event(*args, **kwargs)


# ─────────── TOTP setup ───────────
@transaction.atomic
def prepare_totp(user: User) -> dict:
    """
    مرحله ۱: ساخت secret و URI و QR — هنوز two_factor_enabled=False.
    secret در ciphertext ذخیره می‌شود تا مرحله confirm.
    """
    if user.two_factor_enabled:
        raise TwoFAError("۲FA قبلاً فعال است.")
    secret = pyotp.random_base32()
    user.two_factor_secret = secret
    user.two_factor_confirmed_at = None
    user.save(update_fields=["two_factor_secret_ciphertext", "two_factor_confirmed_at", "updated_at"])

    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.email, issuer_name=ISSUER_NAME)
    qr_b64 = _make_qr_base64(uri)
    return {
        "secret": secret,
        "uri": uri,
        "qr_base64": qr_b64,
        "manual_entry": secret,
    }


def _make_qr_base64(uri: str) -> str:
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@transaction.atomic
def confirm_totp(user: User, code: str, *, request=None) -> list[str]:
    """
    مرحله ۲: تأیید کد + فعال‌سازی 2FA + تولید recovery codes.
    برمی‌گرداند لیست recovery codeهای خام (فقط یک‌بار نمایش داده می‌شوند).
    """
    secret = user.two_factor_secret
    if not secret:
        raise TwoFAError("ابتدا باید ثبت‌نام TOTP را شروع کنید.")

    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=TOTP_VALID_WINDOW):
        _log_event(
            user=user, event_type=SecurityEvent.TYPE_2FA_FAILED,
            request=request, detail={"stage": "confirm_totp"},
        )
        raise TwoFAError("کد نادرست است یا منقضی شده.")

    user.two_factor_enabled = True
    user.two_factor_confirmed_at = timezone.now()
    user.save(update_fields=[
        "two_factor_enabled", "two_factor_confirmed_at", "updated_at",
    ])

    # پاک کردن recovery codeهای قبلی + تولید جدید
    RecoveryCode.objects.filter(user=user, used_at__isnull=True).delete()
    raw_codes: list[str] = []
    for _ in range(RECOVERY_CODE_COUNT):
        code = RecoveryCode.generate_code()
        raw_codes.append(code)
        RecoveryCode.objects.create(
            user=user, code_hash=hmac_sign(code),
        )

    _log_event(
        user=user, event_type=SecurityEvent.TYPE_2FA_ENABLED,
        request=request, detail={"method": "totp"},
    )
    logger.info("2fa_enabled user=%s method=totp", user.id)
    return raw_codes


# ─────────── Verify (login) ───────────
def verify_totp(user: User, code: str, *, request=None) -> bool:
    """بررسی کد TOTP برای login."""
    secret = user.two_factor_secret
    if not secret:
        return False
    totp = pyotp.TOTP(secret)
    ok = totp.verify(code, valid_window=TOTP_VALID_WINDOW)
    _log_event(
        user=user, event_type=(
            SecurityEvent.TYPE_2FA_SUCCESS if ok else SecurityEvent.TYPE_2FA_FAILED
        ),
        request=request, detail={"method": "totp"},
    )
    return ok


def send_sms_otp(user: User, *, request=None) -> None:
    """ارسال OTP پیامکی برای login."""
    if not user.phone:
        raise TwoFAError("شماره تلفن ثبت نشده.")
    try:
        sms_services.send_otp(
            user.phone, purpose="login_2fa",
            user=user, ip=(request.META.get("REMOTE_ADDR") if request else None),
        )
        logger.info("2fa_sms_sent user=%s phone=%s",
                    user.id, mask_phone(user.phone))
    except sms_services.SMSVerificationError as exc:
        raise TwoFAError(str(exc))


def verify_sms_otp(user: User, code: str, *, request=None) -> bool:
    """بررسی OTP پیامکی برای login."""
    if not user.phone:
        return False
    try:
        sms_services.verify_otp(user.phone, purpose="login_2fa", code=code)
    except sms_services.SMSVerificationError:
        _log_event(
            user=user, event_type=SecurityEvent.TYPE_2FA_FAILED,
            request=request, detail={"method": "sms"},
        )
        return False
    _log_event(
        user=user, event_type=SecurityEvent.TYPE_2FA_SUCCESS,
        request=request, detail={"method": "sms"},
    )
    return True


@transaction.atomic
def verify_recovery_code(
    user: User, code: str, *, request=None,
) -> bool:
    """بررسی کد بازیابی — یک‌بارمصرف."""
    code = code.strip().lower().replace(" ", "")
    hashed = hmac_sign(code)
    rc = (
        RecoveryCode.objects.select_for_update()
        .filter(user=user, code_hash=hashed, used_at__isnull=True)
        .first()
    )
    if not rc:
        _log_event(
            user=user, event_type=SecurityEvent.TYPE_2FA_FAILED,
            request=request, detail={"method": "recovery"},
        )
        return False
    rc.used_at = timezone.now()
    rc.save(update_fields=["used_at"])
    _log_event(
        user=user, event_type=SecurityEvent.TYPE_RECOVERY_CODE_USED,
        request=request, detail={"recovery_id": rc.id},
    )
    remaining = RecoveryCode.objects.filter(user=user, used_at__isnull=True).count()
    logger.warning(
        "recovery_code_used user=%s remaining=%s", user.id, remaining,
    )
    return True


# ─────────── Disable ───────────
@transaction.atomic
def disable_twofa(user: User, *, password: str, request=None) -> None:
    """غیرفعال‌سازی 2FA — نیازمند تأیید رمز."""
    if not user.check_password(password):
        raise TwoFAError("رمز عبور نادرست است.")
    if not user.two_factor_enabled:
        return
    user.two_factor_enabled = False
    user.two_factor_secret = None
    user.two_factor_confirmed_at = None
    user.save(update_fields=[
        "two_factor_enabled", "two_factor_secret_ciphertext",
        "two_factor_confirmed_at", "updated_at",
    ])
    RecoveryCode.objects.filter(user=user).delete()
    _log_event(
        user=user, event_type=SecurityEvent.TYPE_2FA_DISABLED,
        request=request, detail={},
    )
    logger.info("2fa_disabled user=%s", user.id)


# ─────────── Recovery codes regeneration ───────────
@transaction.atomic
def regenerate_recovery_codes(user: User, *, request=None) -> list[str]:
    if not user.two_factor_enabled:
        raise TwoFAError("2FA فعال نیست.")
    RecoveryCode.objects.filter(user=user, used_at__isnull=True).delete()
    raw = []
    for _ in range(RECOVERY_CODE_COUNT):
        code = RecoveryCode.generate_code()
        raw.append(code)
        RecoveryCode.objects.create(user=user, code_hash=hmac_sign(code))
    logger.info("recovery_codes_regenerated user=%s", user.id)
    return raw


def recovery_codes_remaining(user: User) -> int:
    return RecoveryCode.objects.filter(user=user, used_at__isnull=True).count()