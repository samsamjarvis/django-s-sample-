import factory
from factory.django import DjangoModelFactory

from apps.erp.models import Supplier
from apps.products.tests.factories import ProductFactory


class SupplierFactory(DjangoModelFactory):
    class Meta:
        model = Supplier

    name = factory.Sequence(lambda n: f"تأمین‌کننده {n}")