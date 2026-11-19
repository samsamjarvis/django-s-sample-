"""Forms — Address با لیبل‌های فارسی."""
from django import forms

from .models import Address


class AddressForm(forms.ModelForm):
    # فیلدهای non-model با لیبل فارسی
    full_address = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "خیابان، کوچه، پلاک، واحد",
        }),
        label="آدرس کامل",
        error_messages={"required": "آدرس کامل الزامی است."},
    )
    postal_code = forms.CharField(
        required=False, max_length=10,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "مثلاً ۱۲۳۴۵۶۷۸۹۰",
            "inputmode": "numeric",
        }),
        label="کد پستی",
    )

    class Meta:
        model = Address
        fields = (
            "title", "recipient_name", "recipient_phone",
            "province", "city", "is_default",
        )
        labels = {
            "title": "عنوان آدرس",
            "recipient_name": "نام گیرنده",
            "recipient_phone": "شماره تماس گیرنده",
            "province": "استان",
            "city": "شهر",
            "is_default": "آدرس پیش‌فرض",
        }
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "مثلاً خانه، محل کار",
            }),
            "recipient_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "نام و نام خانوادگی گیرنده",
            }),
            "recipient_phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "۰۹۱۲۳۴۵۶۷۸۹",
                "inputmode": "numeric",
            }),
            "province": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "مثلاً تهران، اصفهان، شیراز",
            }),
            "city": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "نام شهر",
            }),
            "is_default": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }
        error_messages = {
            "title": {"required": "عنوان آدرس الزامی است."},
            "recipient_name": {"required": "نام گیرنده الزامی است."},
            "recipient_phone": {"required": "شماره تماس گیرنده الزامی است."},
            "province": {"required": "استان الزامی است."},
            "city": {"required": "شهر الزامی است."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["full_address"].initial = self.instance.full_address
            self.fields["postal_code"].initial = self.instance.postal_code

        if "recipient_phone" in self.fields:
            self.fields["recipient_phone"].help_text = "مثال: ۰۹۱۲۳۴۵۶۷۸۹"

    def clean_recipient_phone(self):
        phone = (self.cleaned_data.get("recipient_phone") or "").strip()
        translation = {
            "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
            "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
            "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
            "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
        }
        phone = "".join(translation.get(ch, ch) for ch in phone)
        phone = phone.replace(" ", "").replace("-", "")

        if not phone.startswith("09"):
            raise forms.ValidationError("شماره باید با ۰۹ شروع شود.")
        if len(phone) != 11:
            raise forms.ValidationError("شماره باید ۱۱ رقم باشد.")
        if not phone.isdigit():
            raise forms.ValidationError("شماره فقط شامل ارقام باشد.")
        return phone

    def clean_postal_code(self):
        code = (self.cleaned_data.get("postal_code") or "").strip()
        if not code:
            return ""
        translation = {
            "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
            "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
        }
        code = "".join(translation.get(ch, ch) for ch in code)
        if not code.isdigit():
            raise forms.ValidationError("کد پستی فقط شامل ارقام باشد.")
        if len(code) != 10:
            raise forms.ValidationError("کد پستی باید ۱۰ رقم باشد.")
        return code

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.full_address = self.cleaned_data["full_address"]
        instance.postal_code = self.cleaned_data.get("postal_code") or None
        if commit:
            instance.save()
        return instance
