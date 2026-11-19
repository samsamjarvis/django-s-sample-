"""Core signals — cache invalidation برای SiteSettings و صفحه اصلی."""
import logging

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger("silver.core.signals")


@receiver(post_save, dispatch_uid="core.clear_site_settings_cache_save")
@receiver(post_delete, dispatch_uid="core.clear_site_settings_cache_delete")
def _clear_site_settings_cache(sender, instance, **kwargs):
    """هر تغییر در SiteSettings → cache پاک شود."""
    from apps.core.models import SiteSettings
    if isinstance(instance, SiteSettings):
        cache.delete("site_settings_singleton")
        logger.info("cache_cleared site_settings_singleton")


@receiver([post_save, post_delete], dispatch_uid="core.invalidate_home_cache")
def _invalidate_home_cache(sender, instance, **kwargs):
    """هر تغییر در Product/Category/FAQ → cache صفحه اصلی پاک شود."""
    from apps.core.models import FAQ
    from apps.products.models import Category, Product
    if isinstance(instance, (Product, Category, FAQ)):
        cache.delete("home_data_v1")
