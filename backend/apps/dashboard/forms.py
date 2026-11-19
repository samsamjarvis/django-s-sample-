"""Forms برای پنل ادمین."""
from django import forms

from apps.core.models import SiteSettings
from apps.products.models import Category, Product


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "category", "name", "slug", "short_description", "description",
            "price", "discount_price", "weight_grams", "material",
            "is_active", "is_featured", "is_new",
            "seo_title", "seo_description",
        )
        widgets = {
            "category": forms.Select(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "نام محصول"}),
            "slug": forms.TextInput(attrs={"class": "form-control", "dir": "ltr", "placeholder": "اختیاری — خودکار"}),
            "short_description": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "price": forms.NumberInput(attrs={"class": "form-control"}),
            "discount_price": forms.NumberInput(attrs={"class": "form-control"}),
            "weight_grams": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "material": forms.TextInput(attrs={"class": "form-control"}),
            "seo_title": forms.TextInput(attrs={"class": "form-control"}),
            "seo_description": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "category": "دسته‌بندی", "name": "نام محصول", "slug": "Slug (اختیاری)",
            "short_description": "توضیح کوتاه", "description": "توضیح کامل",
            "price": "قیمت (تومان)", "discount_price": "قیمت با تخفیف",
            "weight_grams": "وزن (گرم)", "material": "جنس",
            "is_active": "فعال", "is_featured": "ویژه", "is_new": "جدید",
            "seo_title": "SEO — عنوان", "seo_description": "SEO — توضیح",
        }

    def clean_slug(self):
        return (self.cleaned_data.get("slug") or "").strip()


class CategoryAdminForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "slug", "description", "parent", "sort_order", "is_active", "image")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "مثلاً گردنبند"}),
            "slug": forms.TextInput(attrs={"class": "form-control", "dir": "ltr", "placeholder": "اختیاری — خودکار"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "parent": forms.Select(attrs={"class": "form-control"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control"}),
            "image": forms.FileInput(attrs={"class": "form-control-file", "accept": "image/*"}),
        }
        labels = {
            "name": "نام دسته", "slug": "Slug (اختیاری)",
            "description": "توضیحات", "parent": "دسته والد",
            "sort_order": "ترتیب نمایش", "is_active": "فعال",
            "image": "تصویر دسته",
        }

    def clean_slug(self):
        return (self.cleaned_data.get("slug") or "").strip()


class SiteSettingsPanelForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = (
            "site_name", "tagline",
            "logo", "favicon",
            "phone", "email", "address",
            "hero_image", "hero_title", "hero_subtitle",
            "instagram", "telegram", "whatsapp",
            "zarinpal_merchant_id", "sms_ir_line",
            "maintenance_mode",
        )
        widgets = {
            "site_name": forms.TextInput(attrs={"class": "form-control"}),
            "tagline": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.FileInput(attrs={"class": "form-control-file", "accept": "image/*"}),
            "favicon": forms.FileInput(attrs={"class": "form-control-file", "accept": "image/*"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "dir": "ltr"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "hero_image": forms.FileInput(attrs={"class": "form-control-file", "accept": "image/*"}),
            "hero_title": forms.TextInput(attrs={"class": "form-control"}),
            "hero_subtitle": forms.TextInput(attrs={"class": "form-control"}),
            "instagram": forms.URLInput(attrs={"class": "form-control", "dir": "ltr"}),
            "telegram": forms.URLInput(attrs={"class": "form-control", "dir": "ltr"}),
            "whatsapp": forms.URLInput(attrs={"class": "form-control", "dir": "ltr"}),
            "zarinpal_merchant_id": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "sms_ir_line": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
        }
        labels = {
            "site_name": "نام سایت", "tagline": "شعار",
            "logo": "لوگو (PNG شفاف توصیه می‌شود)",
            "favicon": "Favicon",
            "phone": "تلفن", "email": "ایمیل", "address": "آدرس",
            "hero_image": "عکس Hero صفحه اصلی",
            "hero_title": "عنوان Hero",
            "hero_subtitle": "زیرعنوان Hero",
            "instagram": "اینستاگرام", "telegram": "تلگرام", "whatsapp": "واتساپ",
            "zarinpal_merchant_id": "Merchant ID زرین‌پال",
            "sms_ir_line": "خط پیامک sms.ir",
            "maintenance_mode": "حالت تعمیرات",
        }


class StockAdjustForm(forms.Form):
    delta = forms.IntegerField(
        label="تغییر موجودی",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    reason = forms.CharField(
        max_length=200, required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="دلیل",
    )


class GatewaySettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ("zarinpal_merchant_id", "sms_ir_line")
        widgets = {
            "zarinpal_merchant_id": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "sms_ir_line": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
        }
