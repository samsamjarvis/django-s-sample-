"""Products signals — auto Stock creation + auto thumb."""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Product, ProductImage

logger = logging.getLogger("silver.products")


@receiver(post_save, sender=Product, dispatch_uid="products.auto_stock")
def auto_create_stock(sender, instance: Product, created, **kwargs):
    """
    وقتی محصول جدید ساخته می‌شود، یک Stock با موجودی ۱۰ خودکار بساز.
    ادمین می‌تواند بعداً از پنل تغییر دهد.
    """
    if not created:
        return
    try:
        from apps.inventory.models import Stock
        Stock.objects.get_or_create(
            product=instance,
            defaults={"quantity": 10, "reserved_quantity": 0},
        )
        logger.info("auto_stock_created product=%s qty=10", instance.id)
    except Exception:
        logger.exception("auto_stock_failed product=%s", instance.id)


@receiver(post_save, sender=ProductImage, dispatch_uid="products.auto_thumb")
def auto_generate_thumbs(sender, instance: ProductImage, created, **kwargs):
    """تولید خودکار thumbnail هنگام آپلود."""
    if not created or not instance.image:
        return
    try:
        from pathlib import Path
        from django.conf import settings
        from .thumbs import SIZES, get_or_create_thumb

        full = Path(settings.MEDIA_ROOT) / instance.image.name
        if full.exists():
            for size_key in SIZES:
                get_or_create_thumb(full, size_key)
    except Exception:
        logger.exception("auto_thumb_failed img=%s", instance.id)