from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import AddressForm
from .models import Address


@login_required
def address_list(request):
    return render(request, "customers/addresses.html", {
        "addresses": Address.objects.filter(user=request.user),
    })


@login_required
@require_http_methods(["GET", "POST"])
def address_add(request):
    form = AddressForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        addr = form.save(commit=False)
        addr.user = request.user
        addr.save()
        messages.success(request, "آدرس اضافه شد.")
        return redirect("customers:address_list")
    return render(request, "customers/address_form.html", {"form": form, "is_edit": False})


@login_required
@require_http_methods(["GET", "POST"])
def address_edit(request, pk):
    addr = get_object_or_404(Address, pk=pk, user=request.user)
    form = AddressForm(request.POST or None, instance=addr)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "آدرس به‌روز شد.")
        return redirect("customers:address_list")
    return render(request, "customers/address_form.html", {"form": form, "is_edit": True})


@login_required
@require_POST
def address_delete(request, pk):
    addr = get_object_or_404(Address, pk=pk, user=request.user)
    addr.delete()
    messages.success(request, "آدرس حذف شد.")
    return redirect("customers:address_list")


@login_required
@require_POST
def address_set_default(request, pk):
    addr = get_object_or_404(Address, pk=pk, user=request.user)
    addr.is_default = True
    addr.save()
    messages.success(request, "آدرس پیش‌فرض تنظیم شد.")
    return redirect("customers:address_list")