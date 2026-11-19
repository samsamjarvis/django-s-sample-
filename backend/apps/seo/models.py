"""SEO — SEOMeta + Redirect."""
from django.db import models


class SEOMeta(models.Model):
    url_path = models.CharField(max_length=300, unique=True)
    title = models.CharField(max_length=200, blank=True)
    description = models.CharField(max_length=300, blank=True)
    keywords = models.CharField(max_length=300, blank=True)
    canonical = models.URLField(blank=True)
    og_image = models.ImageField(upload_to="seo/", blank=True, null=True)
    robots = models.CharField(max_length=80, default="index,follow")
    schema_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "متاتگ SEO"
        verbose_name_plural = "متاتگ‌های SEO"

    def __str__(self) -> str:
        return self.url_path


class Redirect(models.Model):
    from_path = models.CharField(max_length=300, unique=True)
    to_path = models.CharField(max_length=300)
    status_code = models.PositiveSmallIntegerField(default=301)
    is_active = models.BooleanField(default=True)
    hits = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ریدایرکت"
        verbose_name_plural = "ریدایرکت‌ها"

    def __str__(self) -> str:
        return f"{self.from_path} → {self.to_path}"