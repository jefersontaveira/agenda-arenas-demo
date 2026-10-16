from datetime import time
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.saas.models import Arena
from apps.backoffice.models import ArenaConfig, ArenaOpeningHour


@receiver(post_save, sender=Arena)
def create_arena_config(sender, instance, created, **kwargs):
    """
    Sempre que uma Arena é criada (created=True),
    nós criamos automaticamente a configuração padrão dela e os horários padrão.
    """
    if created:
        ArenaConfig.objects.create(
            arena=instance,
            slot_duration=60,
            default_price=0
        )

        default_open = time(16, 0)
        default_close = time(23, 0)

        for weekday in range(7):
            ArenaOpeningHour.objects.create(
                arena=instance,
                weekday=weekday,
                open_time=default_open,
                close_time=default_close,
                is_closed=False
            )