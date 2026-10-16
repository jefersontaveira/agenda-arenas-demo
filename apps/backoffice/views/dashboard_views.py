from datetime import timedelta, datetime
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.utils import timezone
from django.db.models import Sum

from apps.backoffice.mixins import ArenaOwnerRequiredMixin
from apps.saas.models import Arena
from apps.backoffice.models import Booking, Court, ArenaOpeningHour, Equipment, BookingEquipment, ArenaConfig

# Tenta importar ClassSchedule, se não existir (app lessons desligado), ignora
try:
    from apps.lessons.models import ClassSchedule

    HAS_LESSONS = True
except ImportError:
    HAS_LESSONS = False


class DashboardView(ArenaOwnerRequiredMixin, TemplateView):
    template_name = 'backoffice/dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 1. Configuração Inicial
        arena_slug = self.kwargs.get('arena_slug')
        arena = get_object_or_404(Arena, slug=arena_slug)
        context['arena'] = arena

        # --- PROTEÇÃO: Garante que a Config existe para não quebrar a tela ---
        if not hasattr(arena, 'config'):
            # Cria uma config padrão se não existir
            ArenaConfig.objects.create(arena=arena)

        # 2. Gestão da Data
        date_str = self.request.GET.get('date')
        if date_str:
            try:
                current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                current_date = timezone.localtime().date()
        else:
            current_date = timezone.localtime().date()

        context['current_date'] = current_date
        weekday = current_date.weekday()  # 0=Segunda, 6=Domingo

        # 3. Horários de Funcionamento
        opening_hours = ArenaOpeningHour.objects.filter(arena=arena, weekday=weekday, is_closed=False).first()

        # Inicializa KPIs zerados (para o template não quebrar se estiver fechado)
        context['kpis'] = {'revenue': 0, 'occupancy': 0, 'games_count': 0}
        context['equipment_stats'] = []

        if not opening_hours:
            context['is_closed'] = True
            return context  # Retorna aqui, mas já com as variáveis básicas definidas

        context['is_closed'] = False

        # Define range do dia
        start_time = datetime.combine(current_date, opening_hours.open_time)
        end_time = datetime.combine(current_date, opening_hours.close_time)
        if end_time < start_time:
            end_time += timedelta(days=1)

        # 4. Quadras Ativas
        courts = Court.objects.filter(arena=arena, is_active=True)
        context['courts'] = courts

        # 5.1 Busca Reservas do Dia
        daily_bookings = Booking.objects.filter(
            arena=arena,
            start_time__gte=timezone.make_aware(start_time),
            start_time__lt=timezone.make_aware(end_time),
            status__in=['CONFIRMED', 'PENDING']
        ).select_related('customer', 'court')
        context['daily_bookings'] = daily_bookings

        # 5.2 Busca Aulas do Dia (Se o módulo existir)
        daily_classes = []
        if HAS_LESSONS:
            daily_classes = ClassSchedule.objects.filter(
                class_group__arena=arena,
                class_group__is_active=True,
                day_of_week=weekday
            ).select_related('class_group', 'class_group__court', 'class_group__teacher')

        # 6. Montagem da Grid (Agenda)
        # Usa getattr para garantir que não quebre se slot_duration for None
        slot_duration = getattr(arena.config, 'slot_duration', 60) or 60
        grid = {}

        current_slot = start_time
        while current_slot < end_time:
            slot_data = {}
            slot_aware = timezone.make_aware(current_slot)
            slot_time_only = current_slot.time()

            for court in courts:
                item_to_show = None

                # A. Reserva
                booking = next((
                    b for b in daily_bookings 
                    if b.court_id == court.id and b.start_time <= slot_aware < b.end_time
                ), None)
                if booking:
                    item_to_show = booking

                # B. Aula
                if not item_to_show and HAS_LESSONS:
                    lesson = next((
                        l for l in daily_classes
                        if l.class_group.court_id == court.id and l.start_time <= slot_time_only < l.end_time
                    ), None)
                    if lesson:
                        item_to_show = lesson

                slot_data[court] = item_to_show

            grid[current_slot] = slot_data
            current_slot += timedelta(minutes=slot_duration)

        context['grid'] = grid

        # Verifica passado
        now = timezone.localtime()
        context['past_slots'] = [dt for dt in grid.keys() if timezone.make_aware(dt) < now]

        # 7. KPIs (Faturamento real arrecadado)
        total_revenue = daily_bookings.filter(payment_status__in=['PAID', 'PARTIAL']).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        games_count = daily_bookings.count()

        # Ocupação
        total_slots = len(grid) * courts.count()
        occupancy = 0
        if total_slots > 0:
            occupied_slots = 0
            for dt, court_data in grid.items():
                for c, item in court_data.items():
                    if item: occupied_slots += 1
            occupancy = int((occupied_slots / total_slots) * 100)

        context['kpis'] = {
            'revenue': float(total_revenue),
            'occupancy': occupancy,
            'games_count': games_count
        }

        # 8. ESTOQUE DE EQUIPAMENTOS
        # Só tenta buscar se a tabela existir (pós-migration)
        try:
            all_equipments = Equipment.objects.filter(arena=arena, is_active=True)
            equipment_stats = []

            for eq in all_equipments:
                rented_now = BookingEquipment.objects.filter(
                    equipment=eq,
                    booking__arena=arena,
                    booking__status__in=['CONFIRMED', 'PENDING'],
                    booking__start_time__lte=now,
                    booking__end_time__gt=now
                ).aggregate(total_qty=Sum('quantity'))['total_qty'] or 0

                available = max(0, eq.total_quantity - rented_now)

                equipment_stats.append({
                    'name': eq.name,
                    'total': eq.total_quantity,
                    'used': rented_now,
                    'available': available
                })
            context['equipment_stats'] = equipment_stats
        except Exception:
            context['equipment_stats'] = []

        return context

    def get(self, request, *args, **kwargs):
        if request.GET.get('live_check') == '1':
            return self.get_live_feed(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def get_live_feed(self, request, *args, **kwargs):
        from django.http import JsonResponse
        from django.template.loader import render_to_string

        context = self.get_context_data(**kwargs)
        arena = context['arena']
        daily_bookings = context.get('daily_bookings', [])

        bookings_list = []
        for b in daily_bookings:
            bookings_list.append({
                'id': b.id,
                'customer_name': b.customer.name if b.customer else 'Atleta',
                'court_id': b.court_id,
                'court_name': b.court.name if b.court else '',
                'time': timezone.localtime(b.start_time).strftime('%H:%M'),
                'price': float(b.price),
                'amount_paid': float(b.amount_paid),
                'remaining_balance': float(b.remaining_balance),
                'payment_status': b.payment_status,
                'status': b.status,
                'is_paid': b.payment_status == 'PAID',
            })

        latest_global = Booking.objects.filter(
            arena=arena,
            status__in=['CONFIRMED', 'PENDING']
        ).select_related('customer', 'court').order_by('-id').first()

        latest_global_data = None
        if latest_global:
            latest_global_data = {
                'id': latest_global.id,
                'customer_name': latest_global.customer.name if latest_global.customer else 'Atleta',
                'court_name': latest_global.court.name if latest_global.court else '',
                'date_str': timezone.localtime(latest_global.start_time).strftime('%Y-%m-%d'),
                'date_display': timezone.localtime(latest_global.start_time).strftime('%d/%m/%Y'),
                'time_display': timezone.localtime(latest_global.start_time).strftime('%H:%M'),
                'price': float(latest_global.price),
                'amount_paid': float(latest_global.amount_paid),
                'remaining_balance': float(latest_global.remaining_balance),
                'payment_status': latest_global.payment_status,
                'status': latest_global.status,
                'is_paid': latest_global.payment_status == 'PAID',
            }

        grid_html = render_to_string('backoffice/dashboard/_dashboard_grid.html', context, request=request)

        return JsonResponse({
            'success': True,
            'current_date': context['current_date'].strftime('%Y-%m-%d'),
            'bookings': bookings_list,
            'latest_global': latest_global_data,
            'kpis': context['kpis'],
            'grid_html': grid_html,
            'timestamp': timezone.now().timestamp(),
        })