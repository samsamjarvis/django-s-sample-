from django import forms

from apps.crm.models import Ticket


class TicketForm(forms.Form):
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="موضوع",
    )
    body = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        label="توضیح",
    )
    priority = forms.ChoiceField(
        choices=Ticket.PRIORITY_CHOICES,
        initial=Ticket.PRIORITY_NORMAL,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="اولویت",
    )


class TicketReplyForm(forms.Form):
    body = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        label="پاسخ",
    )