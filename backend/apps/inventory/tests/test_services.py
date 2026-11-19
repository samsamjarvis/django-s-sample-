import pytest
from django.utils import timezone

from apps.inventory import services
from apps.inventory.models import Reservation, Stock
from apps.products.tests.factories import ProductFactory


@pytest.mark.django_db
def test_reserve_and_consume():
    p = ProductFactory()
    Stock.objects.update_or_create(
        product=p,
        defaults={"quantity": 5, "reserved_quantity": 0},
    )

    res = services.reserve_stock(p, 2)
    stock = Stock.objects.get(product=p)
    assert stock.quantity == 5
    assert stock.reserved_quantity == 2
    assert res.status == Reservation.STATUS_ACTIVE

    services.consume_reservation(res)
    stock.refresh_from_db()
    assert stock.quantity == 3
    assert stock.reserved_quantity == 0
    res.refresh_from_db()
    assert res.status == Reservation.STATUS_CONSUMED


@pytest.mark.django_db
def test_insufficient_stock():
    p = ProductFactory()
    Stock.objects.update_or_create(
        product=p,
        defaults={"quantity": 1, "reserved_quantity": 0},
    )
    with pytest.raises(services.InsufficientStockError):
        services.reserve_stock(p, 5)


@pytest.mark.django_db
def test_expire_stale():
    p = ProductFactory()

    res = services.reserve_stock(p, 2)
    res.expires_at = timezone.now() - timezone.timedelta(seconds=1)
    res.save(update_fields=["expires_at"])
    Stock.objects.update_or_create(
        product=p,
        defaults={"quantity": 10, "reserved_quantity": 0},
    )
    n = services.expire_stale_reservations()
    assert n == 1
    stock = Stock.objects.get(product=p)
    assert stock.reserved_quantity == 0