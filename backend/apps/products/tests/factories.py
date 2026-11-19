import factory
from factory.django import DjangoModelFactory

from apps.products.models import Category, Product


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"دسته {n}")
    slug = factory.Sequence(lambda n: f"cat-{n}")


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"محصول {n}")
    slug = factory.Sequence(lambda n: f"prod-{n}")
    category = factory.SubFactory(CategoryFactory)
    price = 1_000_000
    is_active = True