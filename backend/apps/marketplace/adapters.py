"""
Marketplace Adapters — الگوی Adapter برای منابع خارجی.
هر منبع خارجی باید از BaseAdapter ارث ببرد.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger("silver.marketplace")


@dataclass
class ExternalProductData:
    external_id: str
    name: str
    price: Decimal
    stock: int
    url: str = ""
    description: str = ""
    image_url: str = ""


class BaseAdapter(ABC):
    """قرارداد مشترک منابع خارجی."""

    def __init__(self, source):
        self.source = source

    @abstractmethod
    def fetch_products(self) -> list[ExternalProductData]:
        ...

    @abstractmethod
    def fetch_product(self, external_id: str) -> ExternalProductData | None:
        ...


class StubAdapter(BaseAdapter):
    """برای تست — منابع ساختگی."""

    def fetch_products(self):
        return [
            ExternalProductData(
                external_id="stub-1",
                name=f"[{self.source.name}] نمونه محصول",
                price=Decimal("1500000"),
                stock=10,
            )
        ]

    def fetch_product(self, external_id):
        products = self.fetch_products()
        return next((p for p in products if p.external_id == external_id), None)


def get_adapter(source) -> BaseAdapter:
    """در فاز ۷ هر منبع به آداپتور خودش وصل می‌شود."""
    # TODO فاز ۷: نقشه source.slug → Adapter
    return StubAdapter(source)