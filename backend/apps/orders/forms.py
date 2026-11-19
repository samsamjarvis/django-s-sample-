from django import forms

from apps.customers.models import Address


class CartAddForm(forms.Form):
    product_id = forms.IntegerField()
    quantity = forms.IntegerField(min_value=1, max_value=20, initial=1)


class CheckoutForm(forms.Form):
    address = forms.ModelChoiceField(
        queryset=Address.objects.none(),
        empty_label=None,
        widget=forms.RadioSelect(attrs={"class": "address-radio"}),
        label="آدرس تحویل",
        error_messages={"required": "آدرس تحویل را انتخاب کنید."},
    )
    customer_note = forms.CharField(
        required=False, max_length=500,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        label="یادداشت برای سفارش",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and user.is_authenticated:
            self.fields["address"].queryset = Address.objects.filter(user=user)