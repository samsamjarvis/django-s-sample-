from django.contrib import admin
from .models import Payment, PaymentAttempt


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "amount", "status", "authority", "ref_id", "created_at")
    list_filter = ("status", "gateway")
    search_fields = ("order__order_number", "authority", "ref_id")
    readonly_fields = ("raw_response", "created_at", "updated_at")


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ("payment", "status", "code", "created_at")
    list_filter = ("status",)
    readonly_fields = ("created_at",)
