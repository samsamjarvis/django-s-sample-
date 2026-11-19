from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "product_image_path", "unit_price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "status", "payment_status", "total_amount", "created_at")
    list_filter = ("status", "payment_status")
    search_fields = ("order_number", "user__email", "shipping_full_name")
    inlines = [OrderItemInline]
    readonly_fields = ("order_number", "created_at", "updated_at")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("user__email", "session_key")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "quantity", "unit_price", "created_at")
    search_fields = ("product__name",)


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "from_status", "to_status", "created_at")
    readonly_fields = ("created_at",)
