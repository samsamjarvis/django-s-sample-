"""
CRM Service — تیکت‌ها، امتیاز وفاداری، تعامل مشتری.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.crm.models import (
    CustomerInteraction, LoyaltyAccount, LoyaltyTransaction, Ticket, TicketMessage,
)

logger = logging.getLogger("silver.crm")


class CRMError(Exception):
    pass


TIER_THRESHOLDS = {
    LoyaltyAccount.TIER_BRONZE: 0,
    LoyaltyAccount.TIER_SILVER: 1000,
    LoyaltyAccount.TIER_GOLD: 5000,
}


def _tier_for_points(points: int) -> str:
    if points >= TIER_THRESHOLDS[LoyaltyAccount.TIER_GOLD]:
        return LoyaltyAccount.TIER_GOLD
    if points >= TIER_THRESHOLDS[LoyaltyAccount.TIER_SILVER]:
        return LoyaltyAccount.TIER_SILVER
    return LoyaltyAccount.TIER_BRONZE


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------
@transaction.atomic
def create_ticket(
    user, subject: str, body: str, *,
    priority: str = Ticket.PRIORITY_NORMAL,
) -> Ticket:
    ticket = Ticket.objects.create(user=user, subject=subject, priority=priority)
    TicketMessage.objects.create(ticket=ticket, author=user, body=body)
    logger.info("ticket_create id=%s user=%s", ticket.id, user.id)
    return ticket


@transaction.atomic
def reply_ticket(ticket: Ticket, author, body: str, *, internal: bool = False) -> TicketMessage:
    if ticket.status == Ticket.STATUS_CLOSED:
        raise CRMError("تیکت بسته است.")
    msg = TicketMessage.objects.create(
        ticket=ticket, author=author, body=body, is_internal=internal,
    )
    if ticket.status == Ticket.STATUS_OPEN and author != ticket.user:
        ticket.status = Ticket.STATUS_IN_PROGRESS
        ticket.save(update_fields=["status", "updated_at"])
    logger.info("ticket_reply ticket=%s author=%s", ticket.id, author.id)
    return msg


@transaction.atomic
def close_ticket(ticket: Ticket, *, by=None) -> Ticket:
    ticket.status = Ticket.STATUS_CLOSED
    ticket.save(update_fields=["status", "updated_at"])
    logger.info("ticket_close ticket=%s by=%s", ticket.id, getattr(by, "id", None))
    return ticket


# ---------------------------------------------------------------------------
# Loyalty (هرگز مانع تراکنش نشود — تمام استثناها swallow می‌شوند)
# ---------------------------------------------------------------------------
@transaction.atomic
def ensure_loyalty_account(user) -> LoyaltyAccount:
    account, _ = LoyaltyAccount.objects.get_or_create(user=user)
    return account


@transaction.atomic
def award_points(user, points: int, reason: str, reference: str = "") -> Optional[LoyaltyTransaction]:
    if points <= 0:
        return None
    try:
        account = LoyaltyAccount.objects.select_for_update().get_or_create(user=user)[0]
        account.points += points
        account.tier = _tier_for_points(account.points)
        account.save(update_fields=["points", "tier", "updated_at"])
        tx = LoyaltyTransaction.objects.create(
            account=account, delta=points, reason=reason, reference=reference,
        )
        logger.info("loyalty_award user=%s +%s tier=%s", user.id, points, account.tier)
        return tx
    except Exception:
        # طبق درخواست: هیچ‌چیز جلوی عملیات اصلی را نگیرد
        logger.exception("loyalty_award_failed user=%s points=%s", user.id, points)
        return None


@transaction.atomic
def redeem_points(user, points: int, reason: str, reference: str = "") -> Optional[LoyaltyTransaction]:
    if points <= 0:
        return None
    try:
        account = LoyaltyAccount.objects.select_for_update().get(user=user)
        if account.points < points:
            raise CRMError("امتیاز کافی نیست.")
        account.points -= points
        account.tier = _tier_for_points(account.points)
        account.save(update_fields=["points", "tier", "updated_at"])
        tx = LoyaltyTransaction.objects.create(
            account=account, delta=-points, reason=reason, reference=reference,
        )
        logger.info("loyalty_redeem user=%s -%s", user.id, points)
        return tx
    except LoyaltyAccount.DoesNotExist:
        return None
    except Exception:
        logger.exception("loyalty_redeem_failed user=%s", user.id)
        return None


def points_for_order_amount(total_amount: Decimal) -> int:
    """۱ امتیاز برای هر ۱۰,۰۰۰ تومان."""
    try:
        return int(Decimal(total_amount) // Decimal("10000"))
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Interactions
# ---------------------------------------------------------------------------
@transaction.atomic
def log_interaction(user, kind: str, summary: str, *, by=None) -> CustomerInteraction:
    return CustomerInteraction.objects.create(
        user=user, kind=kind, summary=summary, created_by=by,
    )