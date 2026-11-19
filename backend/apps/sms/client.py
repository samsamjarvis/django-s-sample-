"""
sms.ir HTTP Client.
اسناد: https://api.sms.ir
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger("silver.sms")

BASE_URL = "https://api.sms.ir/v1"
TIMEOUT = 15


class SMSError(Exception):
    pass


@dataclass
class SendResult:
    success: bool
    message_id: str
    code: str
    raw: dict


class SMSIrClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.SMSIR_API_KEY
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{BASE_URL}{endpoint}"
        try:
            r = requests.post(url, json=payload, headers=self.headers, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            logger.exception("smsir_http_error endpoint=%s err=%s", endpoint, exc)
            raise SMSError("خطای ارتباط با سرویس پیامک.")

    def send_verify(self, *, mobile: str, template_id: str, parameters: dict) -> SendResult:
        """
        پیامک مبتنی بر قالب (Verify). parameters: {"code": "12345", ...}
        """
        payload = {
            "mobile": mobile,
            "templateId": int(template_id),
            "parameters": [
                {"name": k, "value": str(v)} for k, v in parameters.items()
            ],
        }
        data = self._post("/send/verify", payload)
        status = data.get("status", 0)
        success = status == 1
        result = SendResult(
            success=success,
            message_id=str((data.get("data") or {}).get("messageId", "")),
            code=str(status),
            raw=data,
        )
        if not success:
            logger.warning("smsir_send_verify_failed mobile_hash=? code=%s", status)
        return result

    def send_bulk(
        self, *, mobiles: list[str], message: str, line_number: Optional[str] = None,
    ) -> SendResult:
        payload = {
            "lineNumber": line_number or settings.SMSIR_LINE_NUMBER,
            "messageText": message,
            "mobiles": mobiles,
        }
        data = self._post("/send/bulk", payload)
        status = data.get("status", 0)
        return SendResult(
            success=status == 1,
            message_id=str((data.get("data") or {}).get("packId", "")),
            code=str(status),
            raw=data,
        )