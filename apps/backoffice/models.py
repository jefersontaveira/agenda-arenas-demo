# apps/backoffice/models.py
from django.db import models
from apps.core.models import TimeStampedModel, TenantManager
from apps.saas.models import Arena
from django.core.exceptions import ValidationError
from django.utils import timezone


# --- 1. CONFIGURAÇÕES DA ARENA ---
class ArenaConfig(TimeStampedModel):
    """
    Configurações operacionais. Cada Arena tem UMA configuração (OneToOne).
    """
    arena = models.OneToOneField(Arena, on_delete=models.CASCADE, related_name='config')
    slot_duration = models.IntegerField(default=60, verbose_name="Duração do Slot (minutos)")

    # Logos e Visual
    logo = models.ImageField(upload_to='arena_logos/', blank=True, null=True, verbose_name="Logotipo da Arena")
    primary_color = models.CharField(max_length=7, default='#FFC107', verbose_name="Cor Primária")
    secondary_color = models.CharField(max_length=7, default='#212529', verbose_name="Cor Secundária")
    hero_title = models.CharField(max_length=150, blank=True, default='Agende já sua quadra', verbose_name="Título Principal")
    hero_subtitle = models.CharField(max_length=255, blank=True, default='Escolha sua modalidade e garanta seu horário.', verbose_name="Subtítulo")
    hero_image = models.ImageField(upload_to='arena_banners/', blank=True, null=True, verbose_name="Banner de Fundo")

    # Contato e Redes Sociais
    contact_phone = models.CharField(max_length=25, blank=True, null=True, verbose_name="WhatsApp / Telefone")
    instagram = models.CharField(max_length=100, blank=True, null=True, verbose_name="Instagram (@usuario)")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Endereço da Arena")
    about_text = models.TextField(blank=True, null=True, verbose_name="Sobre a Arena")

    # Preços das quadras
    default_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Preço Padrão (Hora)")

    # Política de Pagamento para Reservas Online
    PAYMENT_POLICY_CHOICES = [
        ('FULL_ONLY', 'Apenas 100% (Pagamento integral obrigatório)'),
        ('FULL_OR_HALF', '100% ou 50% (Integral ou Sinal de 50%)'),
        ('ALL_OPTIONS', '100%, 50% ou pagar na arena (Integral, Sinal ou no Local)'),
    ]

    payment_policy = models.CharField(
        max_length=20,
        choices=PAYMENT_POLICY_CHOICES,
        default='FULL_OR_HALF',
        verbose_name="Modalidade de Pagamento Aceita",
        help_text="Define quais opções de pagamento estarão disponíveis para o atleta no agendamento online."
    )

    def __str__(self):
        return f"Config: {self.arena.name}"

    class Meta:
        verbose_name = "Configuração da Arena"
        verbose_name_plural = "Configurações das Arenas"


class AsaasConfig(TimeStampedModel):
    """
    Configurações e credenciais da subconta Asaas da Arena.
    """
    arena = models.OneToOneField(Arena, on_delete=models.CASCADE, related_name='asaas_config')
    wallet_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Wallet ID (Subconta)")
    api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="API Key (Subconta)")

    # Dados cadastrais para a subconta (caso queira salvar no banco)
    cpf_cnpj = models.CharField(max_length=20, blank=True, null=True, verbose_name="CPF/CNPJ")
    company_type = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tipo de Empresa")
    birth_date = models.DateField(blank=True, null=True, verbose_name="Data de Nascimento/Fundação")
    company_email = models.EmailField(blank=True, null=True, verbose_name="E-mail de Login")
    
    # Conta Bancária de Recebimento
    bank_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Código do Banco")
    agency = models.CharField(max_length=10, blank=True, null=True, verbose_name="Agência")
    account = models.CharField(max_length=20, blank=True, null=True, verbose_name="Conta Corrente")
    account_digit = models.CharField(max_length=2, blank=True, null=True, verbose_name="Dígito")
    bank_account_type = models.CharField(max_length=20, default='CONTA_CORRENTE', verbose_name="Tipo de Conta")

    # Status da integração
    is_active = models.BooleanField(default=False, verbose_name="Subconta Ativa")

    def __str__(self):
        return f"Asaas: {self.arena.name}"

    class Meta:
        verbose_name = "Configuração Asaas"
        verbose_name_plural = "Configurações Asaas"


class ArenaOpeningHour(TimeStampedModel):
    """
    Define o horário de funcionamento por dia da semana.
    Permite virar a madrugada.
    """

    DAYS_OF_WEEK = (
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    )

    arena = models.ForeignKey(
        Arena, on_delete=models.CASCADE, related_name='opening_hours'
    )

    weekday = models.IntegerField(choices=DAYS_OF_WEEK)

    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)

    is_closed = models.BooleanField(default=False)
    
    objects = TenantManager()

    def clean(self):
        if not self.is_closed:
            if not self.open_time or not self.close_time:
                raise ValidationError(
                    "Informe horário de abertura e fechamento ou marque como fechado."
                )

    def __str__(self):
        if self.is_closed:
            return f"{self.get_weekday_display()} - Fechado"
        return f"{self.get_weekday_display()} {self.open_time} às {self.close_time}"

    class Meta:
        unique_together = ['arena', 'weekday']
        verbose_name = "Horário de Funcionamento"
        verbose_name_plural = "Horários de Funcionamento"


class Modality(models.Model):
    """
    Esportes disponíveis no sistema (Global -> Agora por Arena).
    """
    arena = models.ForeignKey(Arena, on_delete=models.CASCADE, related_name='modalities', null=True, blank=True)
    name = models.CharField(max_length=50, verbose_name="Nome da Modalidade")
    icon = models.CharField(max_length=50, blank=True, verbose_name="Ícone (CSS Class)")
    emoji = models.CharField(max_length=10, default="🏐", verbose_name="Emoji")

    objects = TenantManager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Modalidade"
        verbose_name_plural = "Modalidades"
        unique_together = ['arena', 'name']


class DayOfWeek(models.Model):
    """
    Dias da semana normalizados no banco de dados.
    """
    DAYS_CHOICES = (
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    )
    number = models.IntegerField(choices=DAYS_CHOICES, unique=True)

    def __str__(self):
        return self.get_number_display()

    class Meta:
        verbose_name = "Dia da Semana"
        verbose_name_plural = "Dias da Semana"


# --- 3. QUADRAS ---
class Court(TimeStampedModel):
    """
    As quadras físicas.
    """
    arena = models.ForeignKey(Arena, on_delete=models.CASCADE, related_name='courts')
    name = models.CharField(max_length=50, verbose_name="Nome da Quadra")
    color = models.CharField(max_length=7, default="#FFFFFF", verbose_name="Cor (Hex)", help_text="Ex: #FF0000")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Preço por Horário")

    # Relação com Modalidades (Uma quadra pode ter vários esportes)
    modalities = models.ManyToManyField(Modality, related_name='courts', verbose_name="Modalidades Aceitas")

    is_active = models.BooleanField(default=True, verbose_name="Quadra Ativa?")
    
    objects = TenantManager()

    @property
    def is_beach_tennis(self):
        # Verifica se TEM "Beach" no nome das modalidades dessa quadra
        return self.modalities.filter(name__icontains="Beach").exists()

    @property
    def is_net_sport(self):
        # Verifica se é Volei ou Futevolei (Esportes de rede sem raquete)
        return self.modalities.filter(name__iregex=r'(Vôlei|Futevôlei|Volei)').exists()

    def __str__(self):
        return f"{self.name} ({self.arena.name})"

    class Meta:
        verbose_name = "Quadra"
        verbose_name_plural = "Quadras"


class Equipment(TimeStampedModel):
    """
    Equipamentos alugáveis da Arena.
    """

    arena = models.ForeignKey(
        Arena, on_delete=models.CASCADE, related_name='equipments'
    )

    name = models.CharField(max_length=100, verbose_name="Nome do Equipamento")
    modalities = models.ManyToManyField(
        Modality, blank=True,
        verbose_name="Modalidades Compatíveis",
        help_text="Modalidades compatíveis"
    )

    total_quantity = models.PositiveIntegerField(default=0, verbose_name="Quantidade Total")

    rental_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Preço de Aluguel"
    )

    is_active = models.BooleanField(default=True, verbose_name="Ativo?")
    
    objects = TenantManager()

    def __str__(self):
        return f"{self.name} ({self.arena.name})"

    class Meta:
        verbose_name = "Equipamento"
        verbose_name_plural = "Equipamentos"


class Customer(TimeStampedModel):
    """
    O Cliente final (Jogador).
    Identificado pelo telefone + Arena (SaaS).
    """
    arena = models.ForeignKey(Arena, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=100, verbose_name="Nome Completo")
    phone = models.CharField(max_length=20, verbose_name="WhatsApp")
    email = models.EmailField("Email", blank=True, null=True)
    cpf = models.CharField("CPF", max_length=14, blank=True, null=True)
    birth_date = models.DateField("Data de Nascimento", blank=True, null=True)
    observation = models.TextField("Observações", blank=True)

    # CRM simples
    total_bookings = models.PositiveIntegerField(default=0, verbose_name="Total de Jogos")
    is_blocked = models.BooleanField(default=False, verbose_name="Bloqueado?")
    
    objects = TenantManager()

    @property
    def formatted_phone(self):
        if not self.phone:
            return ""
        p = self.phone
        if len(p) == 11:
            return f"({p[:2]}) {p[2:7]}-{p[7:]}"
        elif len(p) == 10:
            return f"({p[:2]}) {p[2:6]}-{p[6:]}"
        return p

    def __str__(self):
        return f"{self.name} ({self.phone})"

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        # Garante que não tenha 2 clientes com mesmo telefone NA MESMA arena
        unique_together = ['arena', 'phone']

    def save(self, *args, **kwargs):
        if self.phone:
            import re
            self.phone = re.sub(r'\D', '', self.phone)
        super().save(*args, **kwargs)


class PriceRule(TimeStampedModel):
    DAYS_OF_WEEK = (
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    )

    arena = models.ForeignKey(Arena, on_delete=models.CASCADE, related_name='price_rules')
    court = models.ForeignKey(Court, on_delete=models.CASCADE, null=True, blank=True, related_name='price_rules',
                              help_text="Deixe vazio para aplicar a todas as quadras da arena.")

    name = models.CharField(max_length=100, verbose_name="Nome da Regra", help_text="Ex: Horário Nobre, Fim de Semana")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor por Horário")

    start_time = models.TimeField(verbose_name="Início")
    end_time = models.TimeField(verbose_name="Fim")

    # M2M em vez de texto "0,1,2"
    days = models.ManyToManyField(DayOfWeek, verbose_name="Dias da Semana", related_name="price_rules")
    
    objects = TenantManager()

    def get_days_display_custom(self):
        """
        Gera a string visual "Seg, Ter, Qua".
        """
        if not self.pk:
            return "Nenhum dia"
            
        labels = [day.get_number_display()[:3] for day in self.days.all()]
        if len(labels) == 7:
            return "Todos os dias"
        
        # Opcional: lógicas para 'Seg à Sex' se self.days == [0,1,2,3,4]...
        return ", ".join(labels) if labels else "Nenhum dia"

    def __str__(self):
        return f"{self.name} - R$ {self.price}"

    class Meta:
        verbose_name = "Regra de Preço"
        verbose_name_plural = "Regras de Preço"

    @classmethod
    def get_price_for_booking(cls, arena, court, start_datetime):
        """
        Calcula o preço base da reserva verificando se existe alguma regra ativa.
        Prioridade:
        1. Regra Específica da Quadra
        2. Regra Geral da Arena
        3. Preço Padrão da Quadra
        4. Preço Padrão da Arena
        """

        if timezone.is_aware(start_datetime):
            start_datetime = timezone.localtime(start_datetime)

        weekday = start_datetime.weekday()  # 0 = Segunda, 6 = Domingo
        time = start_datetime.time()  # Hora da reserva (Ex: 18:00)

        # 1. Busca regras que batem com o Dia da Semana e o Horário
        # Nota: start_time__lte (menor ou igual) e end_time__gt (maior que)
        # Filtro Nativo pelo dia da semana!
        rules = cls.objects.filter(
            arena=arena,
            days__number=weekday,
            start_time__lte=time,
            end_time__gt=time
        ).prefetch_related('days')

        # Separa regras de quadra específica e regras gerais
        court_rule = rules.filter(court=court).first()
        arena_rule = rules.filter(court__isnull=True).first()

        # DECISÃO DO PREÇO
        if court_rule:
            return court_rule.price
        elif arena_rule:
            return arena_rule.price
        elif court.price > 0:
            return court.price
        else:
            return arena.config.default_price


class Booking(TimeStampedModel):
    """
    A Reserva (O Core do sistema).
    """

    arena = models.ForeignKey(Arena, on_delete=models.CASCADE, related_name='bookings')
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='bookings')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='bookings')
    start_time = models.DateTimeField(verbose_name="Início")
    end_time = models.DateTimeField(verbose_name="Fim")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Preço Cobrado")

    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('CONFIRMED', 'Confirmado'),
        ('CANCELED', 'Cancelado'),
        ('NO_SHOW', 'Não Compareceu'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('PARTIAL', 'Sinal Pago (50%)'),
        ('PAID', 'Totalmente Pago'),
        ('REFUNDED', 'Estornado'),
    ]

    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Valor Já Pago"
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING',
        verbose_name="Status Pagamento"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CONFIRMED', verbose_name="Status da Reserva")
    
    ORIGIN_CHOICES = [
        ('ONLINE', 'Site / Online (Cliente)'),
        ('BACKOFFICE', 'Balcão / Recepção (Interno)'),
    ]
    origin = models.CharField(
        max_length=20,
        choices=ORIGIN_CHOICES,
        default='BACKOFFICE',
        verbose_name="Origem da Reserva"
    )

    objects = TenantManager()

    def clean(self):
        # Anti-Colisão
        # Verifica se já existe reserva para esta quadra neste horário (excluindo canceladas)

        if not self.court_id or not self.start_time or not self.end_time:
            return

        collision = Booking.objects.filter(
            court=self.court,
            status__in=['PENDING', 'CONFIRMED'],
            start_time__lt=self.end_time,  # Começa antes de eu terminar
            end_time__gt=self.start_time  # Termina depois de eu começar
        ).exclude(pk=self.pk)  # Exclui a si mesmo (caso seja uma edição)

        if collision.exists():
            raise ValidationError("Já existe uma reserva para esta quadra neste horário!")

    @property
    def remaining_balance(self):
        # Calcula quanto falta pagar
        return self.price - self.amount_paid

    def update_total_price(self):
        """
        Método auxiliar para ser chamado EXPLICITAMENTE após salvar os equipamentos.
        """
        # 1. Preço da Regra (Quadra)
        base_price = PriceRule.get_price_for_booking(
            self.arena,
            self.court,
            self.start_time
        )

        # 2. Soma dos Equipamentos (Agora seguros que eles existem)
        equipments_total = sum(
            item.get_total() for item in self.equipments.all()
        )

        self.price = base_price + equipments_total
        self.save()

    def save(self, *args, **kwargs):
        self.clean()

        # No primeiro save (criação), se não tiver preço, calculamos APENAS a quadra.
        # Os equipamentos serão somados depois, via view/form.
        if not self.pk and (not self.price or self.price == 0):
             self.price = PriceRule.get_price_for_booking(
                self.arena,
                self.court,
                self.start_time
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.court.name} - {self.start_time.strftime('%d/%m %H:%M')}"

    class Meta:
        verbose_name = "Reserva"

        verbose_name_plural = "Reservas"
        ordering = ['start_time']


class Payment(TimeStampedModel):
    """
    Registra cada TENTATIVA de pagamento.
    Uma reserva pode ter vários pagamentos (ex: um Pix que expirou e um novo que deu certo).
    """

    STRATEGY_CHOICES = [
        ('TOTAL', 'Valor Total (100%)'),
        ('PARTIAL', 'Sinal (50%)'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('APPROVED', 'Aprovado'),
        ('REJECTED', 'Rejeitado'),
        ('EXPIRED', 'Expirado'),  # Útil para Pix
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')

    # Qual estratégia ele escolheu nessa tentativa?
    strategy = models.CharField(max_length=20, choices=STRATEGY_CHOICES, default='TOTAL')

    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor desta Transação")

    # Dados do Mercado Pago
    transaction_id = models.CharField(max_length=100, unique=True, verbose_name="ID Transação MP")

    # Dados do Pix (Para mostrar na tela)
    pix_qr_code = models.TextField(blank=True, null=True, verbose_name="Copia e Cola")
    pix_qr_code_base64 = models.TextField(blank=True, null=True, verbose_name="Imagem Base64")

    # Links do Asaas (Fatura e Comprovante Bancário)
    invoice_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="Fatura Asaas")
    bank_receipt_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="Comprovante Bancário Asaas")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    def __str__(self):
        return f"Pagamento {self.id} - {self.get_status_display()} ({self.booking})"

    class Meta:
        verbose_name = "Pagamento"
        verbose_name_plural = "Pagamentos"


class BookingEquipment(TimeStampedModel):
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name='equipments', verbose_name="Reserva"
    )

    equipment = models.ForeignKey(
        Equipment, on_delete=models.PROTECT, verbose_name="Equipamento"
    )

    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantidade")

    price_snapshot = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, verbose_name="Preço Unitário Cobrado"
    )

    def get_total(self):
        return self.quantity * self.price_snapshot

    def save(self, *args, **kwargs):
        # Se não informou o preço na hora de salvar, pega do cadastro do equipamento
        if not self.price_snapshot:
            self.price_snapshot = self.equipment.rental_price

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Equipamento da Reserva"
        verbose_name_plural = "Equipamentos da Reserva"


