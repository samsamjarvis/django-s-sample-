"""
Orders signals — hooks برای پیامک، اعطای امتیاز، اعلان ادمین.
از transaction.on_commit استفاده می‌شود.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.dispatch import Signal

logger = logging.getLogger("silver.orders")

# Signal اختصاصی که از orders.services.mark_paid صدا زده می‌شود
on_order_paid = Signal()  # kwargs: order


def _handle_order_paid(sender, order, **kwargs):
    """اجرای پس از commit موفق پرداخت."""
    def _do():
        # ۱) پیامک سفارش
        try:
            from apps.sms import services as sms_services
            sms_services.send_order_notification(order)
        except Exception:
            logger.exception("order_paid_sms_failed order=%s", order.order_number)

        # ۲) امتیاز وفاداری
        try:
            from apps.crm import services as crm_services
            points = crm_services.points_for_order_amount(order.total_amount)
            if points > 0:
                crm_services.award_points(
                    order.user, points, reason="خرید",
                    reference=order.order_number,
                )
        except Exception:
            logger.exception("order_paid_loyalty_failed order=%s", order.order_number)

        # ۳) اعلان ادمین
        try:
            from apps.dashboard import services as dash_services
            dash_services.notify_admins(
                title=f"سفارش پرداخت‌شده #{order.order_number}",
                message=f"مبلغ: {order.total_amount} تومان",
                url=f"/panel/orders/{order.id}/",
            )
        except Exception:
            logger.exception("order_paid_notify_failed order=%s", order.order_number)

    transaction.on_commit(_do)


on_order_paid.connect(_handle_order_paid, dispatch_uid="orders.on_order_paid")