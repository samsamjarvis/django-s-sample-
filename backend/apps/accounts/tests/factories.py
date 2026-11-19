import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = "کاربر"
    last_name = "تست"
    is_active = True
    is_customer = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        pw = extracted or "TestPass123!"
        self.set_password(pw)
        if create:
            self.save()