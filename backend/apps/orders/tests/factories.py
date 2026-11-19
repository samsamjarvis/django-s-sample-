import factory
from factory.django import DjangoModelFactory

from apps.accounts.tests.factories import UserFactory
from apps.orders.models import Cart, Order
from apps.products.tests.factories import ProductFactory


class CartFactory(DjangoModelFactory):
    class Meta:
        model = Cart

    user = factory.SubFactory(UserFactory)


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    shipping_full_name = "گیرنده تست"
    shipping_phone = "09120000000"
    shipping_province = "تهران"
    shipping_city = "تهران"
    shipping_address = "خیابان تست"
    total_amount = 1_000_000