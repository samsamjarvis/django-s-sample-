import pytest
from django.test import RequestFactory

from apps.accounts.tests.factories import UserFactory
from apps.customers.models import Address
from apps.inventory.models import Stock
from apps.orders import services as order_services
from apps.products.tests.factories import ProductFactory


@pytest.mark.django_db
def test_cart_add_and_finalize():
    user = UserFactory()
    p = ProductFactory()
    Stock.objects.update_or_create(
        product=p,
        defaults={"quantity": 10, "reserved_quantity": 0},
    )
    rf = RequestFactory()
    req = rf.get("/")
    req.user = user
    req.session = {"k": "v"}
    # session_key مشکل FakeSession دارد؛ از MockSession استفاده کن
    from django.contrib.sessions.backends.db import SessionStore
    req.session = SessionStore()

    cart = order_services.get_or_create_cart(req)
    item = order_services.add_to_cart(cart, p, 2)
    assert cart.items.count() == 1

    address = Address.objects.create(
        user=user, recipient_name="تست", recipient_phone="09120000000",
        province="تهران", city="تهران", full_address="تست", is_default=True,
    )
    order = order_services.finalize_order(
        cart, shipping_address=address, user=user,
    )
    assert order.items.count() == 1
    assert order.total_amount == p.final_price * 2