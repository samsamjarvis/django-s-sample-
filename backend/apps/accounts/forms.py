from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

from backend.security import hmac_sign

User = get_user_model()

PHONE_REGEX = r"^09\d{9}$"


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "ایمیل"}),
        error_messages={"required": "ایمیل الزامی است."},
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "رمز عبور"}),
        error_messages={"required": "رمز عبور الزامی است."},
    )


class SignupForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=11,
        validators=[RegexValidator(PHONE_REGEX, "شماره باید ۱۱ رقم و با ۰۹ شروع شود.")],
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "۰۹۱۲۳۴۵۶۷۸۹"}),
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        label="رمز عبور",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        label="تکرار رمز عبور",
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        if User.objects.filter(phone_hash=hmac_sign(phone)).exists():
            raise forms.ValidationError("این شماره قبلاً ثبت شده است.")
        return phone

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p1 != p2:
            self.add_error("password2", "رمز عبور و تکرار آن یکسان نیستند.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.phone = self.cleaned_data["phone"]
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "avatar")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "avatar": forms.FileInput(attrs={"class": "form-control"}),
        }


class TwoFactorVerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6, min_length=4,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "کد پیامک"}),
    )
    
# ═════════════ فاز ۶: 2FA Forms ═════════════

class TwoFactorMethodChoiceForm(forms.Form):
    """انتخاب روش 2FA در صفحه verify."""
    method = forms.ChoiceField(
        choices=[
            ("totp", "اپلیکیشن Authenticator"),
            ("sms", "پیامک"),
            ("recovery", "کد بازیابی"),
        ],
        widget=forms.HiddenInput,
        initial="totp",
    )
    code = forms.CharField(
        max_length=16, min_length=4,
        widget=forms.TextInput(attrs={
            "class": "form-control", "autocomplete": "one-time-code",
            "inputmode": "numeric", "placeholder": "کد ۶ رقمی",
        }),
        label="کد تأیید",
    )


class TwoFactorSetupConfirmForm(forms.Form):
    code = forms.CharField(
        max_length=6, min_length=6,
        widget=forms.TextInput(attrs={
            "class": "form-control", "autocomplete": "one-time-code",
            "inputmode": "numeric", "placeholder": "کد ۶ رقمی از اپ",
        }),
        label="کد ۶ رقمی از اپ Authenticator",
    )


class TwoFactorDisableForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        label="رمز عبور برای تأیید",
    )


# ═════════════ Password reset (via SMS OTP) ═════════════

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control"}),
        label="ایمیل حساب",
    )


class PasswordResetVerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6, min_length=4,
        widget=forms.TextInput(attrs={
            "class": "form-control", "autocomplete": "one-time-code",
            "inputmode": "numeric", "placeholder": "کد پیامک",
        }),
        label="کد پیامک",
    )


class PasswordResetConfirmForm(forms.Form):
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        label="رمز جدید",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        label="تکرار رمز جدید",
    )

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "رمزها یکسان نیستند.")
        return cleaned


# ═════════════ Password change (logged-in) ═════════════

class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        label="رمز فعلی",
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        label="رمز جدید",
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        label="تکرار رمز جدید",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_old_password(self):
        old = self.cleaned_data["old_password"]
        if self.user and not self.user.check_password(old):
            raise forms.ValidationError("رمز فعلی نادرست است.")
        return old

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("new_password1"), cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            self.add_error("new_password2", "رمزها یکسان نیستند.")
        return cleaned