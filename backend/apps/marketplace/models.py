"""Marketplace — ExternalSource + ExternalProduct + MarketplaceSync."""
from django.db import models

from apps.products.models import Product


class ExternalSource(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    base_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "منبع خارجی"
        verbose_name_plural = "منابع خارجی"

    def __str__(self) -> str:
        return self.name


class ExternalProduct(models.Model):
    source = models.ForeignKey(ExternalSource, on_delete=models.CASCADE, related_name="products")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="external_refs")
    external_id = models.CharField(max_length=100, db_index=True)
    external_url = models.URLField(blank=True)
    external_price = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)
    external_stock = models.PositiveIntegerField(default=0)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "محصول خارجی"
        verbose_name_plural = "محصولات خارجی"
        unique_together = [("source", "external_id")]

    def __str__(self) -> str:
        return f"{self.source.name}/{self.external_id}"


class MarketplaceSync(models.Model):
    STATUS_OK = "ok"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [(STATUS_OK, "موفق"), (STATUS_FAILED, "ناموفق")]

    source = models.ForeignKey(ExternalSource, on_delete=models.CASCADE, related_name="syncs")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "همگام‌سازی"
        verbose_name_plural = "همگام‌سازی‌ها"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.source.name} — {self.status}"