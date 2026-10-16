import calendar
from datetime import date
from django.utils import timezone
from apps.lessons.models import Enrollment, MonthlyFee


def add_months(sourcedate, months):
    """ Adiciona meses mantendo o último dia do mês se necessário """
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def generate_monthly_fees_routine(arena=None, mode='default', days_threshold=7):
    """
    Gera faturas mensais para alunos com matrícula ativa.
    
    Parâmetros:
    - arena: Objeto Arena (opcional). Se informado, gera apenas para aquela arena.
    - mode:
        * 'default': Mês atual faltante + faturas do próximo mês com vencimento em até 'days_threshold' dias (padrão: 7).
        * 'current_month': Apenas faturas pendentes do mês atual.
        * 'next_month': Faturas do próximo mês para todas as matrículas ativas.
        * 'both': Mês atual e próximo mês para todas as matrículas ativas.
    - days_threshold: Quantos dias de antecedência para antecipar fatura futura no modo 'default'.
    
    Retorna:
    - created_count (int): Quantidade de novas faturas criadas.
    - details (list): Lista com detalhes das faturas criadas.
    """
    today = timezone.now().date()
    
    qs = Enrollment.objects.filter(status='ACTIVE').select_related(
        'customer', 'class_group', 'class_group__arena'
    )
    if arena:
        qs = qs.filter(class_group__arena=arena)
        
    created_count = 0
    details = []
    
    # Determina quais offsets de meses serão avaliados
    if mode == 'current_month':
        month_offsets = [0]
    elif mode == 'next_month':
        month_offsets = [1]
    elif mode == 'both':
        month_offsets = [0, 1]
    else:  # 'default'
        month_offsets = [0, 1]

    for enrollment in qs:
        start_reference = enrollment.start_date.replace(day=1)

        for offset in month_offsets:
            target_date = add_months(today, offset)
            year = target_date.year
            month = target_date.month
            reference_date = date(year, month, 1)

            # Não gera fatura para mês anterior ao início da matrícula
            if reference_date < start_reference:
                continue

            # Calcula dia de vencimento no mês alvo
            last_day = calendar.monthrange(year, month)[1]
            due_day = min(enrollment.due_day, last_day)
            due_date = date(year, month, due_day)

            # No modo 'default', para o próximo mês (offset == 1), só gera se faltar <= days_threshold dias
            if mode == 'default' and offset == 1:
                days_until = (due_date - today).days
                if days_until > days_threshold:
                    continue

            # Regra: Uma cobrança não pode iniciar atrasada
            # Se a data de vencimento calculada já passou, ajusta para hoje
            if due_date < today:
                due_date = today

            # Verifica se já existe fatura para esta matrícula nesta referência
            exists = MonthlyFee.objects.filter(
                enrollment=enrollment,
                reference_date=reference_date
            ).exists()

            if not exists:
                fee = MonthlyFee.objects.create(
                    enrollment=enrollment,
                    reference_date=reference_date,
                    due_date=due_date,
                    value=enrollment.agreed_price,
                    status='PENDING'
                )
                created_count += 1
                details.append({
                    'fee_id': fee.id,
                    'customer_name': enrollment.customer.name,
                    'due_date': due_date,
                    'value': fee.value,
                    'reference': reference_date
                })

    return created_count, details
