"""
SMS Service — لایه بالای SMSIrClient. تمام ارسال‌ها از این‌جا.
شامل: OTP، اعلان سفارش، پیامک گروهی.
"""
from __future__ import annotations

import logging
import secrets
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.sms.client import SMSIrClient, SMSError
from apps.sms.models import OTPRequest, SMSLog, SMSTemplate
from backend.security import decrypt_field, hmac_sign

logger = logging.getLogger("silver.sms")


class SMSVerificationError(Exception):
    pass


# ---------------------------------------------------------------------------
# OTP
# ---------------------------------------------------------------------------
def _generate_code(length: int = 5) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


@transaction.atomic
def send_otp(
    phone: str, purpose: str, *,
    user=None, ip: Optional[str] = None, ttl_minutes: int = 2,
) -> OTPRequest:
    """
    ارسال OTP پیامکی. هر درخواست جدید OTP های فعال قبلی را باطل می‌کند.
    """
    if not phone:
        raise SMSVerificationError("شماره تلفن الزامی است.")

    # باطل‌سازی OTPهای فعال قبلی برای همین شماره/هدف
    OTPRequest.objects.filter(
        phone_hash=hmac_sign(phone), purpose=purpose, used_at__isnull=True,
    ).update(used_at=timezone.now())

    code = _generate_code()
    expires_at = timezone.now() + timezone.timedelta(minutes=ttl_minutes) \
        if hasattr(timezone, "timedelta") else timezone.now()
    from datetime import timedelta
    expires_at = timezone.now() + timedelta(minutes=ttl_minutes)

    otp = OTPRequest.objects.create(
        user=user,
        phone_hash=hmac_sign(phone),
        code_hash=hmac_sign(code),
        purpose=purpose,
        expires_at=expires_at,
        ip=ip,
    )

    # ارسال پیامک از طریق قالب
    template_id = settings.SMSIR_TEMPLATE_OTP or "100000"
    try:
        client = SMSIrClient()
        result = client.send_verify(
            mobile=phone, template_id=template_id, parameters={"code": code},
        )
        SMSLog.objects.create(
            user=user, phone=phone, template_key="otp",
            status=SMSLog.STATUS_SENT if result.success else SMSLog.STATUS_FAILED,
            provider_message_id=result.message_id, response_code=result.code,
            response_data=result.raw, sent_at=timezone.now() if result.success else None,
        )
        if not result.success:
            logger.warning("otp_send_failed phone_hash=%s", otp.phone_hash[:12])
    except SMSError as exc:
        SMSLog.objects.create(
            user=user, phone=phone, template_key="otp",
            status=SMSLog.STATUS_FAILED, response_code="", response_data={"error": str(exc)},
        )
        logger.exception("otp_send_exception phone_hash=%s", otp.phone_hash[:12])
        # در محیط dev، کد را در لاگ چاپ کن برای تست:
        if settings.DEBUG:
            logger.warning("DEV OTP for %s: %s", phone, code)
        raise SMSVerificationError("ارسال پیامک ناموفق بود. بعداً تلاش کنید.")

    logger.info("otp_sent phone_hash=%s purpose=%s", otp.phone_hash[:12], purpose)
    return otp


@transaction.atomic
def verify_otp(
    phone: str, purpose: str, code: str,
) -> OTPRequest:
    """
    بررسی کد. اگر معتبر بود → used_at ثبت. در غیر این صورت شمارنده تلاش.
    """
    otp = (
        OTPRequest.objects.select_for_update()
        .filter(
            phone_hash=hmac_sign(phone), purpose=purpose, used_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )
    if not otp:
        raise SMSVerificationError("کد معتبری یافت نشد. دوباره درخواست دهید.")

    if not otp.is_usable:
        raise SMSVerificationError("کد منقضی شده است. دوباره درخواست دهید.")

    otp.attempts += 1
    if hmac_sign(code) != otp.code_hash:
        otp.save(update_fields=["attempts"])
        remaining = otp.max_attempts - otp.attempts
        raise SMSVerificationError(
            f"کد نادرست است. {max(remaining, 0)} تلاش باقی مانده."
        )

    otp.used_at = timezone.now()
    otp.save(update_fields=["used_at", "attempts"])
    logger.info("otp_verified phone_hash=%s purpose=%s", otp.phone_hash[:12], purpose)
    return otp


# ---------------------------------------------------------------------------
# Transactional SMS (Order)
# ---------------------------------------------------------------------------
def send_order_notification(order) -> Optional[SMSLog]:
    """ارسال پیامک سفارش — از قالب استفاده می‌کند."""
    try:
        phone = order.shipping_phone
        if not phone:
            return None
        template_id = settings.SMSIR_TEMPLATE_ORDER or "100001"
        client = SMSIrClient()
        result = client.send_verify(
            mobile=phone,
            template_id=template_id,
            parameters={
                "order_number": order.order_number,
                "total": str(order.total_amount),
            },
        )
        log = SMSLog.objects.create(
            user=order.user, phone=phone, template_key="order_paid",
            status=SMSLog.STATUS_SENT if result.success else SMSLog.STATUS_FAILED,
            provider_message_id=result.message_id, response_code=result.code,
            response_data=result.raw, sent_at=timezone.now() if result.success else None,
        )
        return log
    except Exception:
        logger.exception("send_order_notification_failed order=%s", order.order_number)
        return None


def send_raw(phone: str, message: str, *, user=None) -> SMSLog:
    """پیامک خام (بدون قالب) — برای اعلان‌های ادمین."""
    try:
        client = SMSIrClient()
        result = client.send_bulk(mobiles=[phone], message=message)
        return SMSLog.objects.create(
            user=user, phone=phone, template_key="",
            message=message,
            status=SMSLog.STATUS_SENT if result.success else SMSLog.STATUS_FAILED,
            provider_message_id=result.message_id, response_code=result.code,
            response_data=result.raw, sent_at=timezone.now() if result.success else None,
        )
    except Exception:
        logger.exception("send_raw_failed")
        return SMSLog.objects.create(
            user=user, phone=phone, message=message,
            status=SMSLog.STATUS_FAILED, response_code="",
            response_data={"error": "exception"},
        )