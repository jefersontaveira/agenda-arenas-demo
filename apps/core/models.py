from django.db import models

class TenantQuerySet(models.QuerySet):
    def for_arena(self, arena):
        return self.filter(arena=arena)

class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)
        
    def for_arena(self, arena):
        return self.get_queryset().for_arena(arena)



class TimeStampedModel(models.Model):
    """
    Classe abstrata que adiciona created_at e updated_at
    automaticamente em qualquer tabela que herdar dela.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        abstract = True
