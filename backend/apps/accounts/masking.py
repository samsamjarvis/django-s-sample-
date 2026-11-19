"""ابزارهای مخفی‌سازی داده حساس در لاگ‌ها."""
from __future__ import annotations


def mask_email(email: str | None) -> str:
    """user@example.com → u***@example.com"""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def mask_phone(phone: str | None) -> str:
    """09123456789 → 0912***6789"""
    if not phone or len(phone) < 7:
        return "***"
    return f"{phone[:4]}***{phone[-4:]}"


def mask_card(card: str | None) -> str:
    """6037991234567890 → 6037********7890"""
    if not card or len(card) < 8:
        return "****"
    return f"{card[:4]}{'*' * (len(card) - 8)}{card[-4:]}"


def mask_address(addr: str | None, keep_chars: int = 10) -> str:
    if not addr:
        return "***"
    if len(addr) <= keep_chars:
        return addr[:3] + "***"
    return addr[:keep_chars] + "…"