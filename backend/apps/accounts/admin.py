from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, TwoFactorOTP, RecoveryCode, SecurityEvent


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "full_name", "is_staff", "is_customer", "is_active", "date_joined")
    list_filter = ("is_active", "is_staff", "is_customer", "two_factor_enabled")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-date_joined",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "avatar")}),
        ("نقش‌ها", {"fields": ("is_active", "is_staff", "is_superuser", "is_customer")}),
        ("2FA", {"fields": ("two_factor_enabled", "two_factor_confirmed_at")}),
        ("تاریخ‌ها", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )


@admin.register(TwoFactorOTP)
class TwoFactorOTPAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "purpose", "expires_at", "used_at", "created_at")
    list_filter = ("purpose",)
    search_fields = ("phone_hash",)


@admin.register(RecoveryCode)
class RecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "used_at", "created_at")
    list_filter = ("used_at",)


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event_type", "user", "ip", "email_attempted")
    list_filter = ("event_type",)
    search_fields = ("user__email", "ip", "email_attempted")
    readonly_fields = ("user", "event_type", "ip", "user_agent", "email_attempted", "detail", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
