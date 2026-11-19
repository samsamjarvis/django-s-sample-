from django.contrib import admin
from .models import ExternalSource, ExternalProduct, MarketplaceSync


@admin.register(ExternalSource)
class ExternalSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ExternalProduct)
class ExternalProductAdmin(admin.ModelAdmin):
    list_display = ("source", "external_id", "product", "external_price", "external_stock", "last_synced_at")
    list_filter = ("source",)
    search_fields = ("external_id", "product__name")


@admin.register(MarketplaceSync)
class MarketplaceSyncAdmin(admin.ModelAdmin):
    list_display = ("source", "status", "created_at")
    list_filter = ("status", "source")
    readonly_fields = ("created_at",)
