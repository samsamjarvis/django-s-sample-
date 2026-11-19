"""Products — Category (درختی) + Product + ProductImage."""
from __future__ import annotations

from pathlib import Path
import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


# ══════════════════════════════════════════════════════════════════
# Upload paths — امن، بدون خطا در ذخیره
# ══════════════════════════════════════════════════════════════════

def product_image_path(instance, filename: str) -> str:
    """
    مسیر ذخیره‌سازی تصویر محصول.
    - نام فایل با UUID امن می‌شود (بدون کاراکتر عجیب)
    - اگر محصول ذخیره نشده، در پوشهٔ tmp/
    - اگر محصول ذخیره شده، در پوشهٔ slug یا id
    """
    ext = Path(filename).suffix.lower() or ".jpg"
    safe_name = f"{uuid.uuid4().hex[:12]}{ext}"

    product = getattr(instance, "product", None)
    if product and getattr(product, "slug", None):
        return f"products/{product.slug}/{safe_name}"
    if product and getattr(product, "pk", None):
        return f"products/{product.pk}/{safe_name}"
    return f"products/tmp/{safe_name}"


def category_image_path(instance, filename: str) -> str:
    """مسیر ذخیره‌سازی تصویر دسته‌بندی."""
    ext = Path(filename).suffix.lower() or ".jpg"
    safe_name = f"{uuid.uuid4().hex[:12]}{ext}"
    slug = getattr(instance, "slug", "") or "tmp"
    return f"categories/{slug}/{safe_name}"


# ══════════════════════════════════════════════════════════════════
# Category
# ══════════════════════════════════════════════════════════════════

class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, max_length=140, allow_unicode=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=category_image_path, blank=True, null=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["parent", "is_active"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "sort_order"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # اگر slug خالی یا فقط خط‌تیره باشد، از name بساز
        if not self.slug or set(self.slug) <= set("-"):
            self.slug = slugify(self.name, allow_unicode=True)
        # اگر slug تکراری بود، suffix اضافه کن
        base_slug = self.slug
        n = 1
        while Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{base_slug}-{n}"
            n += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("products:category", kwargs={"slug": self.slug})


# ══════════════════════════════════════════════════════════════════
# Product
# ══════════════════════════════════════════════════════════════════

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=220, allow_unicode=True, blank=True)
    short_description = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)

    price = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(0)])
    discount_price = models.DecimalField(
        max_digits=12, decimal_places=0, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )

    weight_grams = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    material = models.CharField(max_length=80, blank=True)

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)

    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "is_featured"]),
            models.Index(fields=["is_active", "is_new"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "-created_at"]),
            models.Index(fields=["is_active", "price"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # اگر slug خالی یا فقط خط‌تیره باشد، از name بساز
        if not self.slug or set(self.slug) <= set("-"):
            self.slug = slugify(self.name, allow_unicode=True)
        # اگر slug تکراری بود، suffix اضافه کن
        base_slug = self.slug
        n = 1
        while Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{base_slug}-{n}"
            n += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("products:detail", kwargs={"slug": self.slug})

    @property
    def final_price(self) -> int:
        return int(self.discount_price or self.price)

    @property
    def is_discounted(self) -> bool:
        return self.discount_price is not None and self.discount_price < self.price

    @property
    def discount_percent(self) -> int:
        if not self.is_discounted or self.price == 0:
            return 0
        return int((self.price - self.discount_price) / self.price * 100)

    @property
    def main_image(self) -> "ProductImage | None":
        return self.images.filter(is_main=True).first() or self.images.first()

    @property
    def main_image_safe(self):
        """اگر prefetch شده باشد، بدون query اضافه."""
        if hasattr(self, "cached_images"):
            return self.cached_images[0] if self.cached_images else None
        return self.main_image


# ══════════════════════════════════════════════════════════════════
# ProductImage
# ══════════════════════════════════════════════════════════════════

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=product_image_path)
    alt_text = models.CharField(max_length=200, blank=True)
    is_main = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصول"
        ordering = ["-is_main", "sort_order", "id"]
        indexes = [models.Index(fields=["product", "is_main"])]

    def __str__(self) -> str:
        return f"{self.product.name} — {self.id}"

    def save(self, *args, **kwargs):
        # اگر این تصویر main است، بقیهٔ تصاویر همان محصول را main=False کن
        if self.is_main and self.product_id:
            ProductImage.objects.filter(
                product_id=self.product_id, is_main=True,
            ).exclude(pk=self.pk).update(is_main=False)
        # اگر محصول هیچ تصویر main ندارد و این اولین تصویر است، main کن
        if not self.pk and self.product_id and not self.is_main:
            has_main = ProductImage.objects.filter(
                product_id=self.product_id, is_main=True,
            ).exists()
            if not has_main:
                self.is_main = True
        super().save(*args, **kwargs)
