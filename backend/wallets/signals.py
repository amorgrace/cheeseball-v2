from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .services import initialize_wallet_balances


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_wallet_balances(sender, instance, created, **kwargs):
    if created:
        initialize_wallet_balances(instance)

