"""
Inventory signals — اعلان ادمین وقتی موجودی پایین می‌آید.
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.inventory.models import Stock

logger = logging.getLogger("silver.inventory")


@receiver(post_save, sender=Stock, dispatch_uid="inventory.low_stock_alert")
def low_stock_alert(sender, instance: Stock, **kwargs):
    try:
        if instance.is_low and instance.quantity > 0:
            from apps.dashboard import services as dash_services
            dash_services.notify_admins(
                title=f"موجودی کم: {instance.product.name}",
                message=f"موجودی فعلی: {instance.available}",
                url=f"/panel/inventory/",
            )
    except Exception:
        logger.exception("low_stock_alert_failed")