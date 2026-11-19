"""Core — SiteSettings، FAQ، ContactMessage، Page."""
from django.db import models


class SiteSettings(models.Model):
    site_name = models.CharField(max_length=100, default="Silver")
    tagline = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to="site/", blank=True, null=True)
    favicon = models.ImageField(upload_to="site/", blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    instagram = models.URLField(blank=True)
    telegram = models.URLField(blank=True)
    whatsapp = models.URLField(blank=True)
    zarinpal_merchant_id = models.CharField(max_length=100, blank=True)
    sms_ir_line = models.CharField(max_length=30, blank=True)
    # ═══ Hero section (صفحه اصلی) ═══
    hero_image = models.ImageField(
        upload_to="site/hero/", blank=True, null=True,
        help_text="عکس دست با انگشتر — بالای صفحه اصلی",
    )
    hero_title = models.CharField(
        max_length=200, blank=True, default="ارسال به سراسر ایران",
    )
    hero_subtitle = models.CharField(max_length=300, blank=True)

    maintenance_mode = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"


    # ═══ Cache-busted URLs (فایل آپلود جدید = URL جدید) ═══
    def _bust(self, field):
        if not field:
            return ""
        try:
            import os
            mtime = int(os.path.getmtime(field.path))
            return f"{field.url}?v={mtime}"
        except Exception:
            return field.url if hasattr(field, "url") else ""

    @property
    def logo_url(self):
        return self._bust(self.logo)

    @property
    def favicon_url(self):
        return self._bust(self.favicon)

    @property
    def hero_image_url(self):
        return self._bust(self.hero_image)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> "SiteSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class FAQ(models.Model):
    question = models.CharField(max_length=300)
    answer = models.TextField()
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "سوال پرتکرار"
        verbose_name_plural = "سوالات پرتکرار"
        ordering = ["sort_order", "-created_at"]
        indexes = [models.Index(fields=["is_active", "sort_order"])]

    def __str__(self) -> str:
        return self.question[:80]


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "پیام تماس"
        verbose_name_plural = "پیام‌های تماس"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["is_read", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.name} — {self.subject}"


class Page(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    content = models.TextField()
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "صفحه"
        verbose_name_plural = "صفحات"
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title