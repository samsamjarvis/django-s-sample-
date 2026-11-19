"""
Marketplace Service — همگام‌سازی محصولات خارجی با Product محلی.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.marketplace.adapters import ExternalProductData, get_adapter
from apps.marketplace.models import ExternalProduct, ExternalSource, MarketplaceSync
from apps.products.models import Category, Product

logger = logging.getLogger("silver.marketplace")


class MarketplaceError(Exception):
    pass


@transaction.atomic
def sync_source(source: ExternalSource, *, default_category: Category) -> MarketplaceSync:
    """
    همگام‌سازی یک منبع: fetch → upsert ExternalProduct → اختیاری اتصال به Product.
    """
    adapter = get_adapter(source)
    try:
        items = adapter.fetch_products()
    except Exception as exc:
        logger.exception("marketplace_fetch_failed source=%s", source.id)
        return MarketplaceSync.objects.create(
            source=source, status=MarketplaceSync.STATUS_FAILED,
            summary=f"fetch error: {exc}",
        )

    created = updated = 0
    for data in items:
        obj, is_new = ExternalProduct.objects.update_or_create(
            source=source, external_id=data.external_id,
            defaults={
                "external_url": data.url,
                "external_price": data.price,
                "external_stock": data.stock,
                "last_synced_at": timezone.now(),
            },
        )
        if is_new:
            created += 1
        else:
            updated += 1

    sync = MarketplaceSync.objects.create(
        source=source, status=MarketplaceSync.STATUS_OK,
        summary=f"created={created} updated={updated}",
    )
    logger.info("marketplace_sync source=%s created=%s updated=%s",
                source.id, created, updated)
    return sync


@transaction.atomic
def import_external_as_product(
    ext: ExternalProduct, *,
    category: Category, name_override: str = "",
) -> Product:
    """
    ساخت Product محلی از ExternalProduct. slug یکتا با suffix.
    """
    base_slug = f"ext-{ext.source.slug}-{ext.external_id}"
    slug = base_slug
    i = 1
    while Product.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{i}"
        i += 1

    product = Product.objects.create(
        category=category,
        name=name_override or f"{ext.source.name} - {ext.external_id}",
        slug=slug,
        price=ext.external_price or Decimal("0"),
        is_active=True,
    )
    ext.product = product
    ext.save(update_fields=["product"])
    logger.info("marketplace_import ext=%s → product=%s", ext.id, product.id)
    return product