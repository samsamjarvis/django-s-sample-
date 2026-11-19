import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.orders.models import Order
from apps.payment import services as payment_services
from apps.payment.models import Payment

logger = logging.getLogger("silver.payment")


@login_required
def initiate(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.payment_status == Order.PAYMENT_PAID:
        messages.info(request, "این سفارش قبلاً پرداخت شده.")
        return redirect("orders:detail", order_number=order.order_number)

    try:
        payment = payment_services.initiate_payment(
            order,
            callback_url=request.build_absolute_uri(reverse("payment:verify")),
        )
        url = payment_services.get_gateway_redirect_url(payment)
    except payment_services.PaymentError as exc:
        messages.error(request, str(exc))
        return redirect("orders:detail", order_number=order.order_number)
    except Exception:
        logger.exception("payment_initiate_failed order=%s", order.order_number)
        messages.error(request, "خطا در ایجاد پرداخت.")
        return redirect("orders:detail", order_number=order.order_number)

    return redirect(url)


@require_http_methods(["GET"])
def verify(request):
    """بازگشت از درگاه زرین‌پال — GET."""
    authority = request.GET.get("Authority") or request.GET.get("authority")
    status = request.GET.get("Status") or request.GET.get("status") or "NOK"
    if not authority:
        return HttpResponseBadRequest("پارامتر نا معتبر")

    try:
        payment = payment_services.verify_payment(authority=authority, status=status)
    except payment_services.PaymentError as exc:
        payment = (
            Payment.objects.filter(authority=authority)
            .select_related("order").first()
        )
        return render(request, "payment/failed.html", {
            "error": str(exc),
            "order": payment.order if payment else None,
        })
    except Exception:
        logger.exception("payment_verify_failed authority=%s", authority)
        return render(request, "payment/failed.html", {
            "error": "خطای غیرمنتظره در تأیید پرداخت.",
        })

    return render(request, "payment/success.html", {
        "payment": payment, "order": payment.order,
    })