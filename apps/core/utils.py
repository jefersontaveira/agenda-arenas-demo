from datetime import datetime, time
from django.db.models import Q


def is_time_occupied(court, date_obj, start_time, end_time):
    """
    Retorna True se o horário estiver ocupado (por Reserva OU Aula).
    Retorna False se estiver livre.
    """
    from apps.core.models import Booking
    from apps.lessons.models import ClassSchedule  # Importe aqui para evitar erro circular

    # 1. Checagem de Reservas (Bookings) - Já existente
    # Verifica se existe alguma reserva confirmada/pendente que colida com o horário
    has_booking = Booking.objects.filter(
        court=court,
        start_time__date=date_obj,
        status__in=['CONFIRMED', 'PENDING'],  # Ignora canceladas
        start_time__lt=datetime.combine(date_obj, end_time).replace(tzinfo=start_time.tzinfo),
        end_time__gt=datetime.combine(date_obj, start_time).replace(tzinfo=start_time.tzinfo)
    ).exists()

    if has_booking:
        return True

    # 2. Checagem de Aulas (Lessons) - NOVO!
    # Verifica se existe alguma aula ATIVA neste dia da semana e horário
    week_day = date_obj.weekday()  # 0=Segunda, 6=Domingo

    has_class = ClassSchedule.objects.filter(
        class_group__is_active=True,  # A turma tem que estar ativa
        class_group__arena=court.arena,  # Segurança extra
        court=court,  # Na mesma quadra
        day_of_week=week_day,  # No mesmo dia da semana
        # Lógica de colisão de horário:
        start_time__lt=end_time,
        end_time__gt=start_time
    ).exists()

    if has_class:
        return True

    return False