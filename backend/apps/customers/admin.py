from django.contrib import admin
from .models import CustomerProfile, Address, CustomerNote


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "loyalty_tier", "marketing_opt_in", "created_at")
    list_filter = ("loyalty_tier", "marketing_opt_in")
    search_fields = ("user__email",)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "province", "city", "is_default")
    search_fields = ("user__email", "recipient_name", "province", "city")
    list_filter = ("province", "is_default")


@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
    list_display = ("user", "body", "created_by", "created_at")
    search_fields = ("user__email", "body")
