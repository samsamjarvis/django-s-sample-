"""
ابزارهای امنیتی:
- FieldCipher : رمزنگاری متقارن Fernet برای فیلدهای حساس DB
- HMAC helpers: امضای payload (ریکوئست/ریسپانس هش‌شده)
- axes_lockout_response : پاسخ قفل‌شدن لاگین
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger("silver.security")


class FieldCipher:
    """رمزنگاری متقارن Fernet برای فیلدهای DB."""

    def __init__(self, key: str):
        if not key:
            raise ValueError("ENCRYPTION_KEY is not set.")
        try:
            self._fernet = Fernet(key.encode())
        except Exception:
            digest = hashlib.sha256(key.encode()).digest()
            self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return self._fernet.encrypt(str(value).encode()).decode()

    def decrypt(self, token: Optional[str]) -> Optional[str]:
        if not token:
            return None
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken:
            logger.warning("FieldCipher.decrypt: invalid token")
            return None


_cipher: Optional[FieldCipher] = None


def get_cipher() -> FieldCipher:
    global _cipher
    if _cipher is None:
        _cipher = FieldCipher(settings.ENCRYPTION_KEY)
    return _cipher


def encrypt_field(value: Optional[str]) -> Optional[str]:
    if not settings.FIELD_ENCRYPTION_ENABLED or value is None:
        return value
    return get_cipher().encrypt(value)


def decrypt_field(value: Optional[str]) -> Optional[str]:
    if not settings.FIELD_ENCRYPTION_ENABLED or value is None:
        return value
    return get_cipher().decrypt(value)


def hmac_sign(payload: str, secret: Optional[str] = None) -> str:
    """HMAC-SHA256 برای امضای payload — معادل «ریکوئست/ریسپانس هش‌شده»."""
    secret = secret or settings.SECRET_KEY
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def hmac_verify(payload: str, signature: str, secret: Optional[str] = None) -> bool:
    return hmac.compare_digest(hmac_sign(payload, secret), signature)


def axes_lockout_response(request, credentials=None, *args, **kwargs):
    logger.warning("axes_lockout ip=%s user=%s",
                   request.META.get("REMOTE_ADDR"),
                   (credentials or {}).get("username"))
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {"ok": False, "error": "locked_out",
             "message": "حساب موقتاً قفل شده. لطفاً بعداً تلاش کنید."},
            status=429,
        )
    from django.shortcuts import render
    return render(request, "security/lockout.html", status=429)