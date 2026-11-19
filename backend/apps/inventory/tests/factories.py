import factory
from factory.django import DjangoModelFactory

from apps.inventory.models import Reservation, Stock
from apps.products.tests.factories import ProductFactory


class StockFactory(DjangoModelFactory):
    class Meta:
        model = Stock

    product = factory.SubFactory(ProductFactory)
    quantity = 10


class ReservationFactory(DjangoModelFactory):
    class Meta:
        model = Reservation

    product = factory.SubFactory(ProductFactory)
    quantity = 1
    expires_at = factory.LazyFunction(lambda: Reservation.default_expiry())