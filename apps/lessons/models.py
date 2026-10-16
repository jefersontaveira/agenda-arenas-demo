from django.db import models
from django.utils import timezone
from apps.backoffice.models import Arena, Court, Customer


class Teacher(models.Model):
    arena = models.ForeignKey(Arena, on_delete=models.CASCADE, related_name='teachers')
    name = models.CharField("Nome Completo", max_length=100)
    phone = models.CharField("Telefone/WhatsApp", max_length=20)
    email = models.EmailField("Email", blank=True, null=True)
    color = models.CharField("Cor na Agenda", max_length=7, default="#0d6efd", help_text="Ex: #FF0000")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "Professores"


class ClassGroup(models.Model):
    """ Ex: Turma de Vôlei Iniciante - Ter/Qui """
    arena = models.ForeignKey(Arena, on_delete=models.CASCADE, related_name='classes')
    court = models.ForeignKey(Court, on_delete=models.SET_NULL, null=True, related_name='classes')
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, related_name='classes')

    name = models.CharField("Nome da Turma", max_length=100)
    description = models.TextField("Descrição", blank=True)

    max_students = models.PositiveIntegerField("Máximo de Alunos", default=8)
    monthly_price = models.DecimalField("Valor da Mensalidade (Padrão)", max_digits=10, decimal_places=2)

    is_active = models.BooleanField("Turma Ativa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.teacher})"

    def active_students_count(self):
        # Contamos ativos e experimentais como ocupando vaga
        return self.enrollments.filter(status__in=['ACTIVE', 'TRIAL']).count()

    class Meta:
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"


class ClassSchedule(models.Model):
    """ Define os dias e horários da turma (Ex: Seg das 18h as 19h) """
    DAYS = (
        (0, 'Segunda-feira'), (1, 'Terça-feira'), (2, 'Quarta-feira'), (3, 'Quinta-feira'),
        (4, 'Sexta-feira'), (5, 'Sábado'), (6, 'Domingo')
    )
    class_group = models.ForeignKey(ClassGroup, related_name='schedules', on_delete=models.CASCADE)
    day_of_week = models.IntegerField("Dia da Semana", choices=DAYS)
    start_time = models.TimeField("Início")
    end_time = models.TimeField("Fim")

    def __str__(self):
        return f"{self.get_day_of_week_display()} - {self.start_time}"

    class Meta:
        verbose_name = "Horário de Aula"
        verbose_name_plural = "Horários de Aula"


class Lesson(models.Model):
    """
    Representa a ocorrência de uma aula no calendário.
    Serve para confirmar que a aula aconteceu ou para registrar exceções (cancelamentos, trocas).
    """
    STATUS = (
        ('SCHEDULED', 'Agendada'),  # O padrão
        ('CONFIRMED', 'Realizada'),  # O professor confirmou que deu a aula
        ('CANCELED', 'Cancelada'),  # Chuva, feriado, manutenção
    )

    class_group = models.ForeignKey(ClassGroup, related_name='lessons', on_delete=models.CASCADE)

    # Campos opcionais para quando a realidade diferir do planejado na Turma (ClassGroup)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name="Professor do Dia")
    court = models.ForeignKey(Court, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Quadra do Dia")

    date = models.DateField("Data da Aula")
    start_time = models.TimeField("Início")
    end_time = models.TimeField("Fim")

    status = models.CharField(max_length=10, choices=STATUS, default='SCHEDULED')
    observation = models.TextField("Observações", blank=True)  # Ex: "Aula cancelada devido à chuva forte"

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Aula (Agenda)"
        verbose_name_plural = "Aulas (Agenda)"
        ordering = ['-date', 'start_time']
        # Evita duplicidade acidental de horário para a mesma turma
        unique_together = ('class_group', 'date', 'start_time')

    def __str__(self):
        status_label = dict(self.STATUS).get(self.status)
        return f"{self.class_group.name} - {self.date.strftime('%d/%m')} ({status_label})"


class Enrollment(models.Model):
    """ O vínculo do aluno com a turma """
    STATUS = (
        ('ACTIVE', 'Ativo'),
        ('PAUSED', 'Suspenso'),
        ('CANCELED', 'Cancelado'),
        ('TRIAL', 'Aula Experimental')
    )

    class_group = models.ForeignKey(ClassGroup, related_name='enrollments', on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, related_name='enrollments', on_delete=models.CASCADE)

    start_date = models.DateField("Data de Início", default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS, default='ACTIVE')

    # Preço acordado (Se for experimental grátis, você salva como 0.00 aqui)
    agreed_price = models.DecimalField("Valor Acordado", max_digits=10, decimal_places=2)

    # Dia do vencimento para este aluno (ex: todo dia 10)
    due_day = models.PositiveIntegerField("Dia do Vencimento", default=10, help_text="Dia do mês que vence a fatura")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} - {self.class_group.name} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"


class MonthlyFee(models.Model):
    """ O Boleto/Cobrança mensal """
    STATUS = (('PENDING', 'Pendente'), ('PAID', 'Pago'), ('OVERDUE', 'Atrasado'), ('CANCELED', 'Cancelado'))

    enrollment = models.ForeignKey(Enrollment, related_name='fees', on_delete=models.CASCADE)

    reference_date = models.DateField("Mês de Referência")
    due_date = models.DateField("Data de Vencimento")

    value = models.DecimalField("Valor", max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS, default='PENDING')

    paid_at = models.DateField("Data do Pagamento", null=True, blank=True)

    # Campo para controle do Robô de Alertas
    last_alert_sent_at = models.DateTimeField("Último Alerta Enviado", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.enrollment.customer.name} - {self.reference_date.strftime('%m/%Y')} - {self.get_status_display()}"

    class Meta:
        verbose_name = "Mensalidade"
        verbose_name_plural = "Mensalidades"