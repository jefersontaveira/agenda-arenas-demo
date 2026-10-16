# apps/saas/models.py
from django.db import models
from django.contrib.auth.models import User
from apps.core.models import TimeStampedModel


class Arena(TimeStampedModel):
    """
    Representa o cliente do seu SaaS (O estabelecimento).
    """
    users = models.ManyToManyField(User, related_name='arenas', blank=True, verbose_name="Usuários da Arena")
    name = models.CharField(max_length=100, verbose_name="Nome da Arena")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL (Slug)")

    # Dados de Contato / Dono
    owner_name = models.CharField(max_length=100, verbose_name="Nome do Proprietário")
    owner_phone = models.CharField(max_length=25, blank=True, null=True, verbose_name="WhatsApp / Telefone do Dono")
    owner_email = models.EmailField(blank=True, null=True, verbose_name="E-mail do Dono")
    cnpj = models.CharField(max_length=20, blank=True, null=True, verbose_name="CNPJ")

    # Informações de Contrato SaaS
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Valor da Mensalidade (R$)")
    due_day = models.PositiveSmallIntegerField(default=10, verbose_name="Dia de Vencimento")

    # Trava de Segurança (Inadimplência)
    is_active = models.BooleanField(default=True, verbose_name="Arena Ativa?")

    @property
    def whatsapp_link(self):
        """Retorna link direto para iniciar conversa no WhatsApp com o dono."""
        if not self.owner_phone:
            return None
        import re
        digits = re.sub(r'\D', '', self.owner_phone)
        if not digits:
            return None
        if len(digits) in [10, 11] and not digits.startswith('55'):
            digits = '55' + digits
        return f"https://wa.me/{digits}"

    @property
    def financial_status(self):
        """
        Retorna ('OVERDUE', 'Atrasado', 'danger'), ('PENDING', 'Pendente', 'warning'),
        ou ('OK', 'Em Dia', 'success').
        """
        from django.utils import timezone
        today = timezone.localdate()
        # Se tem faturas vencidas não pagas
        overdue = self.subscriptions.filter(
            models.Q(status='OVERDUE') | 
            models.Q(status='PENDING', due_date__lt=today)
        ).exists()
        if overdue:
            return {'code': 'OVERDUE', 'label': 'Atrasado', 'badge': 'danger'}

        # Se tem faturas pendentes para vencer este mês
        pending = self.subscriptions.filter(
            status='PENDING',
            due_date__gte=today
        ).exists()
        if pending:
            return {'code': 'PENDING', 'label': 'Pendente', 'badge': 'warning'}

        return {'code': 'OK', 'label': 'Em Dia', 'badge': 'success'}

    @property
    def is_connected_to_asaas(self):
        """
        Retorna True se a arena tiver uma Subconta criada e vinculada no Asaas.
        """
        if hasattr(self, 'asaas_config') and self.asaas_config.wallet_id:
            return True
        return False

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Arena"
        verbose_name_plural = "Arenas"


class Subscription(TimeStampedModel):
    """
    Controle financeiro: Quanto e quando a Arena te paga.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('PAID', 'Pago'),
        ('OVERDUE', 'Atrasado'),
        ('CANCELED', 'Cancelado'),
    ]

    arena = models.ForeignKey(Arena, on_delete=models.CASCADE, related_name='subscriptions')
    due_date = models.DateField(verbose_name="Vencimento")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Mensal")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Status")
    payment_date = models.DateField(null=True, blank=True, verbose_name="Data Pagamento")
    notes = models.TextField(blank=True, verbose_name="Observações")

    def __str__(self):
        return f"{self.arena.name} - {self.get_status_display()}"

    class Meta:
        verbose_name = "Mensalidade"
        verbose_name_plural = "Mensalidades"
