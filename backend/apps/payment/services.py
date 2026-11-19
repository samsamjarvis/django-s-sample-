"""
Payment Service — چرخه پرداخت زرین‌پال.
- initiate_payment : ایجاد Payment + ریدایرکت به درگاه
- verify_payment   : تأیید پس از بازگشت از درگاه
- handle_callback  : نقطه ورود ویو
"""
from __future__ import annotations

import logging
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.orders.models import Order
from apps.orders import services as order_services
from apps.payment.models import Payment, PaymentAttempt
from apps.payment.gateways.zarinpal import (
    VerifyResult, ZarinpalClient, ZarinpalError,
)

logger = logging.getLogger("silver.payment")


class PaymentError(Exception):
    pass


# ---------------------------------------------------------------------------
# Initiate
# ---------------------------------------------------------------------------
@transaction.atomic
def initiate_payment(order: Order, *, callback_url: Optional[str] = None) -> Payment:
    """
    ایجاد رکورد Payment و فراخوانی درگاه. authority در Payment ذخیره می‌شود.
    """
    if order.payment_status == Order.PAYMENT_PAID:
        raise PaymentError("این سفارش قبلاً پرداخت شده است.")
    if order.status == Order.STATUS_CANCELED:
        raise PaymentError("سفارش لغو شده است.")

    # اگر Payment فعال قبلی هست، همان را برگردان (برای جلوگیری از رکورد تکراری)
    existing = Payment.objects.filter(
        order=order, status__in=[Payment.STATUS_INITIATED, Payment.STATUS_PENDING],
    ).first()
    if existing and existing.authority:
        logger.info("reuse_payment order=%s payment=%s", order.order_number, existing.id)
        return existing

    payment = Payment.objects.create(
        order=order,
        gateway=Payment.GATEWAY_ZARINPAL,
        amount=order.total_amount,
        status=Payment.STATUS_INITIATED,
    )

    callback = callback_url or settings.ZARINPAL_CALLBACK_URL or \
               reverse("payment:verify")
    client = ZarinpalClient()
    try:
        result = client.request_payment(
            amount=int(order.total_amount) * 10,  # تومان → ریال
            callback_url=callback,
            description=f"سفارش {order.order_number}",
            mobile=order.shipping_phone,
        )
    except ZarinpalError as exc:
        payment.status = Payment.STATUS_FAILED
        payment.raw_response = {"error": str(exc), "code": exc.code}
        payment.save(update_fields=["status", "raw_response", "updated_at"])
        PaymentAttempt.objects.create(
            payment=payment, status="failed",
            code=str(exc.code), message=exc.message, response={},
        )
        raise PaymentError(f"خطا در ایجاد پرداخت: {exc.message}")

    payment.authority = result.authority
    payment.status = Payment.STATUS_PENDING
    payment.raw_response = result.raw
    payment.save(update_fields=["authority", "status", "raw_response", "updated_at"])
    logger.info("payment_initiated order=%s payment=%s authority=%s",
                order.order_number, payment.id, result.authority)
    return payment


def get_gateway_redirect_url(payment: Payment) -> str:
    """URL درگاه برای redirect کاربر."""
    if not payment.authority:
        raise PaymentError("پرداخت فاقد authority است.")
    client = ZarinpalClient()
    return client.start_pay.format(authority=payment.authority)


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
@transaction.atomic
def verify_payment(*, authority: str, status: str = "OK") -> Payment:
    """
    بعد از بازگشت از درگاه.
    - status از زرین‌پال: OK یا NOK
    - اگر OK، با verify تایید می‌شود.
    """
    payment = (
        Payment.objects.select_for_update()
        .select_related("order")
        .filter(authority=authority)
        .first()
    )
    if not payment:
        raise PaymentError("تراکنش پیدا نشد.")

    if payment.status == Payment.STATUS_PAID:
        logger.info("already_paid payment=%s", payment.id)
        return payment

    if status != "OK":
        payment.status = Payment.STATUS_CANCELED
        payment.save(update_fields=["status", "updated_at"])
        PaymentAttempt.objects.create(
            payment=payment, status="canceled", code="",
            message="کاربر از درگاه بازگشت (NOK)",
        )
        order_services.mark_payment_failed(payment.order, reason="zarinpal NOK")
        raise PaymentError("پرداخت توسط کاربر لغو شد.")

    client = ZarinpalClient()
    try:
        result: VerifyResult = client.verify_payment(
            amount=int(payment.amount) * 10,
            authority=authority,
        )
    except ZarinpalError as exc:
        PaymentAttempt.objects.create(
            payment=payment, status="error", code=str(exc.code),
            message=exc.message,
        )
        order_services.mark_payment_failed(payment.order, reason=str(exc))
        raise PaymentError(f"خطا در تأیید پرداخت: {exc.message}")

    if not result.is_success:
        payment.status = Payment.STATUS_FAILED
        payment.raw_response = result.raw
        payment.save(update_fields=["status", "raw_response", "updated_at"])
        PaymentAttempt.objects.create(
            payment=payment, status="failed",
            code=str(result.code), message="verify failed", response=result.raw,
        )
        order_services.mark_payment_failed(payment.order, reason=f"code={result.code}")
        raise PaymentError(f"پرداخت تأیید نشد (کد {result.code}).")

    # موفقیت
    payment.status = Payment.STATUS_PAID
    payment.ref_id = result.ref_id
    payment.card_pan = result.card_pan
    payment.paid_at = timezone.now()
    payment.raw_response = result.raw
    payment.save(update_fields=[
        "status", "ref_id", "card_pan", "paid_at", "raw_response", "updated_at",
    ])
    PaymentAttempt.objects.create(
        payment=payment, status="success",
        code=str(result.code), message="verified", response=result.raw,
    )
    order_services.mark_paid(payment.order, payment_id=payment.id)
    logger.info("payment_verified payment=%s order=%s ref=%s",
                payment.id, payment.order.order_number, result.ref_id)
    return payment


def payments_for_order(order: Order):
    return Payment.objects.filter(order=order).order_by("-created_at")