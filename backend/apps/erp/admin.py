from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, Expense


class POItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_name", "email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "contact_name", "email")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "supplier", "status", "total_cost", "created_at")
    list_filter = ("status",)
    search_fields = ("reference", "supplier__name")
    inlines = [POItemInline]


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ("purchase_order", "product", "quantity", "unit_cost")
    search_fields = ("product__name",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("category", "amount", "description", "paid_at", "created_by")
    list_filter = ("category", "paid_at")
    search_fields = ("description",)
