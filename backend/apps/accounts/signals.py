"""Accounts signals — profile + password_changed_at + 2FA hooks."""
from __future__ import annotations

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from apps.accounts.models import User

logger = logging.getLogger("silver.accounts")


@receiver(pre_save, sender=User, dispatch_uid="accounts.track_password_change")
def track_password_change(sender, instance: User, **kwargs):
    """اگر password hash تغییر کرد، password_changed_at را آپدیت کن."""
    if not instance.pk:
        return
    try:
        old = User.objects.only("password").get(pk=instance.pk)
    except User.DoesNotExist:
        return
    if old.password != instance.password:
        instance.password_changed_at = timezone.now()


@receiver(post_save, sender=User, dispatch_uid="accounts.ensure_profiles")
def ensure_user_profiles(sender, instance: User, created, **kwargs):
    if not created:
        return
    try:
        from apps.customers.models import CustomerProfile
        CustomerProfile.objects.get_or_create(user=instance)
    except Exception:
        logger.exception("profile_create_failed user=%s", instance.id)
    if instance.is_customer:
        try:
            from apps.crm.models import LoyaltyAccount
            LoyaltyAccount.objects.get_or_create(user=instance)
        except Exception:
            logger.exception("loyalty_create_failed user=%s", instance.id)