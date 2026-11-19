import factory
from factory.django import DjangoModelFactory

from apps.sms.models import SMSTemplate


class SMSTemplateFactory(DjangoModelFactory):
    class Meta:
        model = SMSTemplate

    key = factory.Sequence(lambda n: f"tmpl-{n}")
    title = factory.Sequence(lambda n: f"قالب {n}")
    body = "کد شما: {code}"