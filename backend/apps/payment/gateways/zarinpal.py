"""
Zarinpal Gateway Client — نسخه ۴ API.
اسناد: https://docs.zarinpal.com/paymentGateway/
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger("silver.payment.zarinpal")


BASE_LIVE = "https://payment.zarinpal.com/pg"
BASE_SANDBOX = "https://sandbox.zarinpal.com/pg"
START_PAY_LIVE = "https://payment.zarinpal.com/pg/StartPay/{authority}"
START_PAY_SANDBOX = "https://sandbox.zarinpal.com/pg/StartPay/{authority}"

TIMEOUT = 20


class ZarinpalError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


@dataclass
class RequestResult:
    authority: str
    code: int
    gateway_url: str
    raw: dict


@dataclass
class VerifyResult:
    code: int
    ref_id: str
    card_pan: str
    raw: dict

    @property
    def is_success(self) -> bool:
        return self.code in (100, 101)


class ZarinpalClient:
    """کلاینت زرین‌پال. تمام فراخوانی‌ها این‌جا متمرکز است."""

    def __init__(self, merchant_id: Optional[str] = None, sandbox: Optional[bool] = None):
        self.merchant_id = merchant_id or settings.ZARINPAL_MERCHANT_ID
        self.sandbox = settings.ZARINPAL_SANDBOX if sandbox is None else sandbox
        self.base = BASE_SANDBOX if self.sandbox else BASE_LIVE
        self.start_pay = START_PAY_SANDBOX if self.sandbox else START_PAY_LIVE

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base}{endpoint}"
        try:
            resp = requests.post(url, json=payload, timeout=TIMEOUT,
                                 headers={"Accept": "application/json"})
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.exception("zarinpal_http_error endpoint=%s err=%s", endpoint, exc)
            raise ZarinpalError(-1, "خطای ارتباط با درگاه پرداخت.")

    def request_payment(
        self, *, amount: int, callback_url: str, description: str,
        mobile: str = "", email: str = "",
    ) -> RequestResult:
        """
        درخواست پرداخت. amount به ریال (یا تومان؟ زرین‌پال ریال می‌گیرد).
        توجه: اگر ذخیره شما تومان است، اینجا × ۱۰ کن.
        """
        payload = {
            "merchant_id": self.merchant_id,
            "amount": amount,  # ریال
            "callback_url": callback_url,
            "description": description,
            "metadata": {"mobile": mobile, "email": email},
        }
        data = self._post("/v4/payment/request.json", payload)
        errors = data.get("errors") or []
        if errors:
            err = errors[0] if isinstance(errors, list) else errors
            raise ZarinpalError(int(err.get("code", -1)), err.get("message", "خطای نامشخص"))
        result = data.get("data") or {}
        authority = result.get("authority", "")
        code = int(result.get("code", 0))
        if code != 100 or not authority:
            raise ZarinpalError(code, "درگاه پرداخت درخواست را نپذیرفت.")
        gateway_url = self.start_pay.format(authority=authority)
        logger.info("zarinpal_request amount=%s authority=%s", amount, authority)
        return RequestResult(authority=authority, code=code, gateway_url=gateway_url, raw=data)

    def verify_payment(self, *, amount: int, authority: str) -> VerifyResult:
        payload = {
            "merchant_id": self.merchant_id,
            "amount": amount,
            "authority": authority,
        }
        data = self._post("/v4/payment/verify.json", payload)
        errors = data.get("errors") or []
        # 101 = already verified → treat as success
        result = data.get("data") or {}
        code = int(result.get("code", 0))
        if errors and code not in (100, 101):
            err = errors[0] if isinstance(errors, list) else errors
            code = int(err.get("code", -1))
        ref_id = str(result.get("ref_id", ""))
        card_pan = str(result.get("card_pan", ""))
        logger.info("zarinpal_verify authority=%s code=%s ref=%s", authority, code, ref_id)
        return VerifyResult(code=code, ref_id=ref_id, card_pan=card_pan, raw=data)