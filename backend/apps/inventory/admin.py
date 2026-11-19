from django.contrib import admin
from .models import Stock, StockMovement, Reservation


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "reserved_quantity", "available", "is_low", "updated_at")
    search_fields = ("product__name",)
    readonly_fields = ("available", "is_low")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "kind", "quantity", "reference", "created_at")
    list_filter = ("kind",)
    search_fields = ("product__name", "reference")
    readonly_fields = ("created_at",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "quantity", "status", "expires_at", "created_at")
    list_filter = ("status",)
    search_fields = ("product__name", "order_reference")
    readonly_fields = ("created_at", "updated_at")
