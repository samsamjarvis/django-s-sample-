"""Admin برای Core — SiteSettings, FAQ, ContactMessage, Page."""
from django.contrib import admin
from django.utils.html import format_html

from .models import SiteSettings, FAQ, ContactMessage, Page


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("برند", {
            "fields": ("site_name", "tagline", "logo", "favicon"),
        }),
        ("تماس", {
            "fields": ("phone", "email", "address"),
        }),
        ("Hero صفحه اصلی", {
            "fields": ("hero_image", "hero_image_preview", "hero_title", "hero_subtitle"),
            "description": "عکس دست با انگشتر. اگر خالی باشد، placeholder SVG نمایش داده می‌شود.",
        }),
        ("شبکه‌های اجتماعی", {
            "classes": ("collapse",),
            "fields": ("instagram", "telegram", "whatsapp"),
        }),
        ("درگاه و پیامک", {
            "classes": ("collapse",),
            "fields": ("zarinpal_merchant_id", "sms_ir_line"),
        }),
        ("حالت", {
            "fields": ("maintenance_mode",),
        }),
    )
    readonly_fields = ("hero_image_preview",)

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def hero_image_preview(self, obj):
        if obj and obj.hero_image:
            return format_html(
                '<img src="{}" style="max-width:400px;max-height:260px;'
                'border-radius:12px;border:1px solid #ddd" /><br>'
                '<small style="color:#666">این تصویر در Hero صفحه اصلی نمایش داده می‌شود.</small>',
                obj.hero_image.url,
            )
        return "هنوز عکسی آپلود نشده — اگر آپلود نکنی، placeholder SVG نمایش داده می‌شود."
    hero_image_preview.short_description = "پیش‌نمایش Hero"


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "sort_order", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("question", "answer")
    list_editable = ("sort_order", "is_active")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("name", "email", "subject")


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "updated_at")
    list_filter = ("is_published",)
    prepopulated_fields = {"slug": ("title",)}
