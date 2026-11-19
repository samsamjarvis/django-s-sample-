from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.crm import services as crm_services
from apps.crm.models import LoyaltyAccount, Ticket
from .forms import TicketForm, TicketReplyForm


@login_required
def ticket_list(request):
    tickets = Ticket.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "crm/tickets.html", {"tickets": tickets})


@login_required
@require_http_methods(["GET", "POST"])
def ticket_create(request):
    form = TicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            ticket = crm_services.create_ticket(
                request.user,
                subject=form.cleaned_data["subject"],
                body=form.cleaned_data["body"],
                priority=form.cleaned_data["priority"],
            )
        except Exception:
            messages.error(request, "خطا در ایجاد تیکت.")
        else:
            messages.success(request, "تیکت ثبت شد.")
            return redirect("crm:ticket_detail", pk=ticket.id)
    return render(request, "crm/ticket_form.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, user=request.user)
    messages_qs = (
        ticket.messages.filter(is_internal=False)
        .select_related("author").order_by("created_at")
    )
    form = TicketReplyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            crm_services.reply_ticket(ticket, request.user, form.cleaned_data["body"])
        except crm_services.CRMError as exc:
            messages.error(request, str(exc))
        except Exception:
            messages.error(request, "خطا در ارسال پاسخ.")
        else:
            return redirect("crm:ticket_detail", pk=ticket.id)
    return render(request, "crm/ticket_detail.html", {
        "ticket": ticket, "messages_qs": messages_qs, "form": form,
    })


@login_required
def loyalty(request):
    account, _ = LoyaltyAccount.objects.get_or_create(user=request.user)
    return render(request, "crm/loyalty.html", {
        "account": account,
        "transactions": account.transactions.all()[:20],
    })