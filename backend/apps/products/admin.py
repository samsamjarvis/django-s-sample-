"""Admin برای Products — آپلود عکس مستقیم در فرم."""
from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductImage


# ═════════ Category ═════════
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "thumb", "parent", "is_active", "sort_order", "created_at")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active", "sort_order")
    readonly_fields = ("image_preview",)
    fields = (
        "name", "slug", "description", "parent", "sort_order", "is_active",
        "image", "image_preview",
    )

    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;object-fit:cover;border-radius:50%" />',
                obj.image.url,
            )
        return "—"
    thumb.short_description = ""

    def image_preview(self, obj):
        if obj and obj.image:
            return format_html(
                '<img src="{}" style="width:150px;height:150px;object-fit:cover;'
                'border-radius:50%;border:2px solid #ddd" /><br>'
                '<small style="color:#666">این تصویر در نوار دسته‌بندی صفحه اصلی نمایش داده می‌شود.</small>',
                obj.image.url,
            )
        return "برای نمایش دایره‌ای، تصویر مربعی ۲۰۰×۲۰۰ آپلود کن."
    image_preview.short_description = "پیش‌نمایش"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "slug" in form.base_fields:
            form.base_fields["slug"].required = False
        return form


# ═════════ ProductImage — StackedInline (کارت عمودی) ═════════
class ProductImageInline(admin.StackedInline):
    """
    در فرم «افزودن محصول» این بخش با ۳ ردیف خالی نمایش داده می‌شود.
    کاربر می‌تواند همزمان با ساخت محصول، از سیستم فایل انتخاب کند.
    """
    model = ProductImage
    extra = 3                 # ۳ ردیف خالی آماده
    max_num = 10              # حداکثر ۱۰ عکس برای هر محصول
    fields = (
        "image",
        "preview",
        "alt_text",
        "is_main",
        "sort_order",
    )
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj and obj.image:
            return format_html(
                '<img src="{}" style="width:180px;height:180px;object-fit:cover;'
                'border-radius:8px;border:1px solid #ddd" />',
                obj.image.url,
            )
        return "—"
    preview.short_description = "پیش‌نمایش فعلی"


# ═════════ Product ═════════
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "category", "thumb", "price",
        "is_active", "is_featured", "is_new", "created_at",
    )
    list_filter = ("is_active", "is_featured", "is_new", "category")
    search_fields = ("name", "slug", "short_description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline]
    list_editable = ("is_active", "is_featured", "is_new")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("category", "name", "slug", "short_description", "description"),
        }),
        ("قیمت", {"fields": ("price", "discount_price")}),
        ("مشخصات", {"fields": ("weight_grams", "material")}),
        ("وضعیت", {"fields": ("is_active", "is_featured", "is_new")}),
        ("SEO", {"classes": ("collapse",), "fields": ("seo_title", "seo_description")}),
        ("تاریخ‌ها", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )

    def thumb(self, obj):
        main = obj.main_image
        if main and main.image:
            return format_html(
                '<img src="{}" style="width:48px;height:48px;object-fit:cover;border-radius:4px" />',
                main.image.url,
            )
        return "—"
    thumb.short_description = "تصویر"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "slug" in form.base_fields:
            form.base_fields["slug"].required = False
        return form


# ═════════ ProductImage standalone admin (مدیریت تکی) ═════════
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "preview", "is_main", "sort_order", "created_at")
    list_filter = ("is_main",)
    search_fields = ("product__name", "alt_text")
    readonly_fields = ("preview", "created_at")

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;object-fit:cover;border-radius:6px" />',
                obj.image.url,
            )
        return "—"
    preview.short_description = "پیش‌نمایش"
