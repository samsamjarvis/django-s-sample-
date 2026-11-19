import factory
from factory.django import DjangoModelFactory

from apps.accounts.tests.factories import UserFactory
from apps.crm.models import Ticket


class TicketFactory(DjangoModelFactory):
    class Meta:
        model = Ticket

    user = factory.SubFactory(UserFactory)
    subject = "تیکت تست"