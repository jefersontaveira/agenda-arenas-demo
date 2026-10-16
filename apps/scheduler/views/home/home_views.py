# --- ARQUIVO: apps/scheduler/views/home/home_views.py ---
import json
from datetime import datetime, date, timedelta
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import re

from apps.saas.models import Arena
from apps.backoffice.models import Booking, Court, Modality, ArenaConfig, PriceRule, ArenaOpeningHour, Equipment, Customer
from apps.lessons.models import ClassSchedule
from apps.scheduler.forms.booking_forms import PublicBookingForm


@method_decorator(never_cache, name='dispatch')
class ArenaPublicView(TemplateView):
    template_name = 'scheduler/home/arena_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs['arena_slug']
        self.arena = get_object_or_404(Arena, slug=slug, is_active=True)

        tempo_limite = timezone.now() - timedelta(minutes=15)
        Booking.objects.filter(
            arena=self.arena,
            status='PENDING',
            created_at__lt=tempo_limite
        ).update(status='CANCELED')

        context['arena'] = self.arena

        # 1. Filtros
        selected_date_str = self.request.GET.get('date', str(date.today()))
        selected_modality_id = self.request.GET.get('modality')

        try:
            current_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            current_date = date.today()

        if current_date < date.today():
            current_date = date.today()

        # 2. Configuração Básica
        try:
            config = self.arena.config
        except ArenaConfig.DoesNotExist:
            context['error'] = "Arena sem configuração."
            return context

        # 3. Horário de Funcionamento
        weekday_num = current_date.weekday()
        opening_rule = ArenaOpeningHour.objects.filter(arena=self.arena, weekday=weekday_num).first()

        if not opening_rule or opening_rule.is_closed:
            context['closed_message'] = "A Arena está fechada neste dia."
            context['selected_date'] = current_date
            return context

        # Range preciso do dia operacional (inclui horários após meia-noite)
        open_naive = datetime.combine(current_date, opening_rule.open_time)
        close_naive = datetime.combine(current_date, opening_rule.close_time)
        if close_naive <= open_naive:
            close_naive += timedelta(days=1)
        current_time = timezone.make_aware(open_naive)
        end_time = timezone.make_aware(close_naive)
        duration = config.slot_duration
        now = timezone.now()

        # 4. Quadras
        courts = Court.objects.filter(arena=self.arena, is_active=True)
        if selected_modality_id:
            courts = courts.filter(modalities__id=selected_modality_id)

        # --- NOVA LÓGICA DE EQUIPAMENTOS ---
        all_equipments = list(Equipment.objects.filter(arena=self.arena, is_active=True))

        # 5. Reservas e Aulas
        daily_bookings = list(Booking.objects.filter(
            arena=self.arena,
            start_time__gte=current_time,
            start_time__lt=end_time,
            status__in=['PENDING', 'CONFIRMED']
        ).prefetch_related('equipments'))

        daily_classes = list(ClassSchedule.objects.filter(
            class_group__arena=self.arena, class_group__is_active=True, day_of_week=weekday_num
        ).select_related('class_group'))

        daily_rules = PriceRule.objects.filter(arena=self.arena, days__number=weekday_num).order_by('-price')

        # 6. Loop de Slots
        available_slots = []

        while current_time < end_time:
            slot_end = current_time + timedelta(minutes=duration)
            if slot_end > end_time: break

            slot_time_only = current_time.time()
            slot_end_time_only = slot_end.time()

            # A. Verifica Quadras Livres
            free_courts_data = []
            for court in courts:
                is_taken = any(b.court_id == court.id and b.start_time < slot_end and b.end_time > current_time for b in
                               daily_bookings)
                is_taken_by_class = any(
                    c.class_group.court_id == court.id and c.start_time < slot_end_time_only and c.end_time > slot_time_only
                    for c in daily_classes)

                if not is_taken and not is_taken_by_class:
                    # [NOVO] Extrai IDs das modalidades da quadra para o filtro JS
                    court_modality_ids = list(court.modalities.values_list('id', flat=True))

                    # Gera flags visuais (opcional, mas bom manter)
                    mod_names = [m.name.lower() for m in court.modalities.all()]
                    is_bt = any('beach' in m for m in mod_names)
                    is_net = any('vôlei' in m or 'volei' in m or 'fute' in m for m in mod_names)

                    # Calcula o preço REAL desta quadra neste horário usando a hierarquia oficial
                    court_price = PriceRule.get_price_for_booking(self.arena, court, current_time)

                    free_courts_data.append({
                        'id': court.id,
                        'name': court.name,
                        'price': float(court_price),
                        'modality_ids': court_modality_ids,  # <--- IMPORTANTE PARA O FILTRO
                        'is_bt': is_bt,
                        'is_net': is_net
                    })

            # B. Calcula Estoque de CADA Equipamento para este Horário
            slot_equipments_data = []

            for eq in all_equipments:
                used_count = 0
                for booking in daily_bookings:
                    # Verifica colisão de horário
                    if booking.start_time < slot_end and booking.end_time > current_time:
                        # Verifica se a reserva usa este equipamento
                        for booked_item in booking.equipments.all():
                            if booked_item.equipment_id == eq.id:
                                used_count += booked_item.quantity

                current_stock = max(0, eq.total_quantity - used_count)

                # [NOVO] Extrai IDs das modalidades do equipamento para o filtro JS
                eq_modality_ids = list(eq.modalities.values_list('id', flat=True))

                slot_equipments_data.append({
                    'id': eq.id,
                    'name': eq.name,
                    'price': float(eq.rental_price),
                    'stock': current_stock,
                    'modality_ids': eq_modality_ids,  # <--- IMPORTANTE PARA O FILTRO
                    # Flags para ajudar no ícone do JS
                    'is_ball': 'bola' in eq.name.lower(),
                    'is_racket': 'raquete' in eq.name.lower()
                })

            # C. Define Preço do Horário (baseado na menor taxa das quadras livres disponíveis)
            if free_courts_data:
                current_price = min(c['price'] for c in free_courts_data)
            else:
                first_court = courts.first() if courts.exists() else None
                current_price = float(PriceRule.get_price_for_booking(self.arena, first_court, current_time) if first_court else config.default_price)

            # D. Adiciona ao Slot final
            available_slots.append({
                'time': current_time,
                'courts': free_courts_data,
                'courts_json': json.dumps(free_courts_data),

                # Lista completa (o JS vai filtrar baseado nos modality_ids acima)
                'equipments_json': json.dumps(slot_equipments_data),

                'is_full': len(free_courts_data) == 0 or current_time < now,
                'price': float(current_price),
            })

            current_time += timedelta(minutes=duration)

        context.update({
            'arena': self.arena,
            'modalities': Modality.objects.filter(courts__arena=self.arena).distinct(),
            'selected_date': current_date,
            'selected_modality_id': int(selected_modality_id) if selected_modality_id else None,
            'available_slots': available_slots,
            'form': PublicBookingForm(),
            'all_opening_hours': self.arena.opening_hours.all().order_by('weekday'),
        })
        return context


# Ajax: Identificação do Atleta e Busca de Agendamentos
@csrf_exempt
def my_bookings_ajax(request, arena_slug):
    arena = get_object_or_404(Arena, slug=arena_slug, is_active=True)

    if request.method == "POST":
        if request.content_type == 'application/json':
            try:
                body = json.loads(request.body)
            except Exception:
                body = {}
            raw_phone = body.get('phone', '')
            name = body.get('name', '').strip()
        else:
            raw_phone = request.POST.get('phone', '')
            name = request.POST.get('name', '').strip()
    else:
        raw_phone = request.GET.get('phone', '').strip()
        name = request.GET.get('name', '').strip()

    phone_digits = re.sub(r'\D', '', raw_phone)

    if not phone_digits or len(phone_digits) < 8:
        return JsonResponse({
            'success': False,
            'error': 'Telefone inválido. Informe o número com DDD.',
            'bookings': [],
            'customer': None
        }, status=400)

    # 1. Busca cliente por telefone na arena
    customer = Customer.objects.filter(arena=arena, phone=phone_digits).first()
    if not customer and len(phone_digits) >= 10:
        # Fallback para busca pelos últimos 8 ou 9 dígitos
        customer = Customer.objects.filter(arena=arena, phone__endswith=phone_digits[-8:]).first()

    # Se o cliente já existe e informou um nome novo/atualizado
    if customer:
        if name and (not customer.name or customer.name == 'Cliente'):
            customer.name = name.upper()
            customer.save(update_fields=['name'])
    elif name:
        # Se não existe ainda, podemos registrar o cliente preliminarmente
        customer, _ = Customer.objects.get_or_create(
            arena=arena,
            phone=phone_digits,
            defaults={'name': name.upper()}
        )

    customer_data = None
    if customer:
        customer_data = {
            'name': customer.name,
            'phone': customer.phone,
            'cpf': customer.cpf or '',
            'email': customer.email or ''
        }
    else:
        customer_data = {
            'name': name.upper() if name else '',
            'phone': phone_digits,
            'cpf': '',
            'email': ''
        }

    # 2. Busca reservas do cliente
    bookings_qs = Booking.objects.filter(
        arena=arena,
        customer__phone__icontains=phone_digits[-8:]
    ).select_related('court').prefetch_related('payments').order_by('-start_time')[:30]

    now = timezone.now()
    data = []
    for b in bookings_qs:
        local_start = timezone.localtime(b.start_time)
        local_end = timezone.localtime(b.end_time)

        # Checa expiração de reservas PENDING
        is_expired = False
        if b.status == 'PENDING' and b.created_at:
            if b.created_at < now - timedelta(minutes=15):
                is_expired = True
                if b.status != 'CANCELED':
                    b.status = 'CANCELED'
                    b.save(update_fields=['status'])

        # Cores e textos
        color = 'secondary'
        status_text = b.get_status_display()
        if b.status == 'CONFIRMED':
            color = 'success'
        elif b.status == 'PENDING':
            color = 'warning text-dark'
        elif b.status in ['CANCELED', 'NO_SHOW']:
            color = 'danger'

        checkout_url = ""
        success_url = ""
        if b.status == 'PENDING' and not is_expired:
            checkout_url = f"/app/pagamento/{b.id}/"
        elif b.status == 'CONFIRMED':
            success_url = f"/app/{arena_slug}/sucesso/{b.id}/"

        data.append({
            'id': b.id,
            'date': local_start.strftime('%d/%m/%Y'),
            'time': f"{local_start.strftime('%H:%M')} às {local_end.strftime('%H:%M')}",
            'court': b.court.name,
            'status': b.status,
            'status_text': status_text,
            'color': color,
            'payment_status': b.payment_status,
            'payment_status_text': b.get_payment_status_display(),
            'payment_method': 'PIX (Asaas)',
            'price': float(b.price) if b.price else 0.00,
            'total_price': float(b.price) if b.price else 0.00,
            'amount_paid': float(b.amount_paid) if b.amount_paid else 0.00,
            'remaining_balance': float(b.remaining_balance) if b.price else 0.00,
            'is_expired': is_expired,
            'checkout_url': checkout_url,
            'success_url': success_url,
        })

    return JsonResponse({
        'success': True,
        'customer': customer_data,
        'bookings': data
    })


# Ajax: Salvar Dados de Pagamento / Perfil do Atleta
@csrf_exempt
def save_customer_profile_ajax(request, arena_slug):
    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Método não permitido.'}, status=405)

    arena = get_object_or_404(Arena, slug=arena_slug, is_active=True)

    if request.content_type == 'application/json':
        try:
            body = json.loads(request.body)
        except Exception:
            body = {}
    else:
        body = request.POST

    raw_name = body.get('name', '').strip()
    raw_phone = body.get('phone', '').strip()
    raw_cpf = body.get('cpf', '').strip()
    raw_email = body.get('email', '').strip()

    phone_digits = re.sub(r'\D', '', raw_phone)
    if not (10 <= len(phone_digits) <= 11):
        return JsonResponse({'success': False, 'error': 'Telefone inválido. Informe DDD + número.'}, status=400)

    if len(raw_name) < 2:
        return JsonResponse({'success': False, 'error': 'Nome do atleta é obrigatório.'}, status=400)

    cpf_digits = re.sub(r'\D', '', raw_cpf) if raw_cpf else None
    if cpf_digits and len(cpf_digits) != 11:
        return JsonResponse({'success': False, 'error': 'CPF inválido. Deve conter 11 números.'}, status=400)

    customer, _ = Customer.objects.update_or_create(
        arena=arena,
        phone=phone_digits,
        defaults={
            'name': raw_name.upper(),
            'cpf': cpf_digits,
            'email': raw_email.lower() if raw_email else None
        }
    )

    return JsonResponse({
        'success': True,
        'message': 'Dados salvos com sucesso!',
        'customer': {
            'name': customer.name,
            'phone': customer.phone,
            'cpf': customer.cpf or '',
            'email': customer.email or ''
        }
    })


@method_decorator(csrf_exempt, name='dispatch')
class MyAppointmentsView(TemplateView):
    """
    Página dedicada para o Atleta visualizar seus agendamentos,
    fazer pagamentos PIX pendentes e gerenciar seu perfil.
    """
    template_name = 'scheduler/home/my_bookings_page.html'

    def dispatch(self, request, *args, **kwargs):
        # Se a requisição for AJAX/JSON, responde com a API de agendamentos
        if (
            request.headers.get('x-requested-with') == 'XMLHttpRequest'
            or 'application/json' in request.headers.get('accept', '')
            or request.method == 'POST'
            or request.GET.get('format') == 'json'
        ):
            return my_bookings_ajax(request, kwargs.get('arena_slug'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs['arena_slug']
        arena = get_object_or_404(Arena, slug=slug, is_active=True)
        context['arena'] = arena
        context['all_opening_hours'] = ArenaOpeningHour.objects.filter(arena=arena).order_by('weekday')
        return context