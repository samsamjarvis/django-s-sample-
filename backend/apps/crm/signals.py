"""
CRM signals — تخصیص خودکار تیکت به اولین ادمین فعال.
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.crm.models import Ticket

logger = logging.getLogger("silver.crm")


@receiver(post_save, sender=Ticket, dispatch_uid="crm.auto_assign_ticket")
def auto_assign_ticket(sender, instance: Ticket, created, **kwargs):
    if not created or instance.assigned_to_id:
        return
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin = User.objects.filter(is_staff=True, is_active=True).order_by("id").first()
        if admin:
            instance.assigned_to = admin
            instance.save(update_fields=["assigned_to"])
    except Exception:
        logger.exception("auto_assign_ticket_failed")