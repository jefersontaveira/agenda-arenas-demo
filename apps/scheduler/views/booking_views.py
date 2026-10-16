# --- ARQUIVO: apps/scheduler/views/booking_views.py ---
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, TemplateView
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
from django.db import transaction

# Models
from apps.saas.models import Arena
from apps.backoffice.models import Booking, BookingEquipment, Customer, Court, PriceRule, Equipment
from apps.lessons.models import ClassSchedule
from apps.scheduler.forms.booking_forms import PublicBookingForm


# 1. VIEW DE AÇÃO (PROCESSAR A RESERVA)
class PublicBookingAction(CreateView):
    model = Booking
    form_class = PublicBookingForm

    def dispatch(self, request, *args, **kwargs):
        # Garante que a Arena existe e está ativa
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'], is_active=True)
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        # Se der erro no form, mostra qual foi
        print(f"Erro Form: {form.errors}")
        messages.error(self.request, "Erro nos dados. Verifique e tente novamente.")
        return redirect('scheduler:arena_home', arena_slug=self.arena.slug)

    def form_valid(self, form):
        # --- 1. EXTRAÇÃO E TRATAMENTO DOS DADOS ---
        try:
            # Pegamos o ID do campo oculto e buscamos o objeto
            court_id = form.cleaned_data['court_id']
            court = get_object_or_404(Court, id=court_id, arena=self.arena)

            date_str = form.cleaned_data['date']
            time_str = form.cleaned_data['time']

            # Conversão de Data/Hora
            start_time_naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            start_time = timezone.make_aware(start_time_naive)

            duration = self.arena.config.slot_duration
            end_time = start_time + timedelta(minutes=duration)

            # Dados do Cliente
            customer_name = form.cleaned_data['customer_name']
            customer_phone = form.cleaned_data['customer_phone']
            customer_cpf = form.cleaned_data.get('customer_cpf')
            customer_email = form.cleaned_data.get('customer_email')

            # --- CORREÇÃO AQUI: Captura a lista de equipamentos selecionados ---
            # O JS envia inputs com name="equipment_ids"
            selected_eq_ids = self.request.POST.getlist('equipment_ids')

            # Captura tipo de pagamento (total ou partial)
            payment_type = self.request.POST.get('payment_type', 'total')

        except (ValueError, KeyError, Court.DoesNotExist):
            messages.error(self.request, "Dados da reserva inválidos.")
            return redirect('scheduler:arena_home', arena_slug=self.arena.slug)

        # --- 2 e 4. TRAVA DE SEGURANÇA E SALVAMENTO (Concorrência) ---
        try:
            with transaction.atomic():
                # Bloqueia a quadra (Impede Race Conditions no PostgreSQL/MySQL)
                locked_court = Court.objects.select_for_update().get(id=court.id)
                
                base_home_url = reverse('scheduler:arena_home', kwargs={'arena_slug': self.arena.slug})
                if date_str:
                    base_home_url = f"{base_home_url}?date={date_str}"

                # Checa colisão DENTRO da transação
                if Booking.objects.filter(
                        arena=self.arena, court=locked_court, status__in=['CONFIRMED', 'PENDING'],
                        start_time__lt=end_time, end_time__gt=start_time
                ).exists():
                    messages.error(self.request, "Ops! Alguém acabou de reservar esse horário.")
                    return redirect(base_home_url)

                week_day = start_time.weekday()
                if ClassSchedule.objects.filter(
                        class_group__arena=self.arena, class_group__is_active=True, class_group__court=locked_court,
                        day_of_week=week_day, start_time__lt=end_time.time(), end_time__gt=start_time.time()
                ).exists():
                    messages.error(self.request, "Horário indisponível (Aula).")
                    return redirect(base_home_url)

                # --- 3. GESTÃO DO CLIENTE ---
                clean_phone = ''.join(filter(str.isdigit, customer_phone))
                clean_cpf = ''.join(filter(str.isdigit, customer_cpf)) if customer_cpf else None
                formatted_name = customer_name.strip().upper()
                formatted_email = customer_email.strip().lower() if customer_email else None

                customer, created = Customer.objects.update_or_create(
                    arena=self.arena,
                    phone=clean_phone,
                    defaults={
                        'name': formatted_name,
                        'cpf': clean_cpf,
                        'email': formatted_email
                    }
                )

                if not created:
                    customer.name = formatted_name
                    if clean_cpf:
                        customer.cpf = clean_cpf
                    if formatted_email:
                        customer.email = formatted_email
                    customer.save()

                base_price = PriceRule.get_price_for_booking(self.arena, locked_court, start_time)

                booking = Booking(
                    arena=self.arena, court=locked_court, customer=customer,
                    start_time=start_time, end_time=end_time, price=base_price,
                    status='PENDING', payment_status='PENDING',
                    origin='ONLINE'
                )
                booking.save()

                # --- CORREÇÃO: Salva os Equipamentos da Lista ---
                if selected_eq_ids:
                    # Busca os objetos no banco (Filtra pela arena para segurança)
                    equipments = Equipment.objects.filter(id__in=selected_eq_ids, arena=self.arena)

                    for eq in equipments:
                        BookingEquipment.objects.create(
                            booking=booking,
                            equipment=eq,
                            quantity=1,  # Checkbox sempre conta como 1
                            price_snapshot=eq.rental_price
                        )

                # Atualiza total e salva
                booking.update_total_price()

                # Valida a modalidade de pagamento aceita pela Arena
                policy = getattr(self.arena.config, 'payment_policy', 'FULL_OR_HALF')
                if policy == 'FULL_ONLY':
                    payment_type = 'total'
                elif policy == 'FULL_OR_HALF' and payment_type not in ['total', 'partial']:
                    payment_type = 'total'
                elif policy == 'ALL_OPTIONS' and payment_type not in ['total', 'partial', 'venue', 'local']:
                    payment_type = 'total'

                # Define o fluxo conforme a escolha do atleta (sinal, total ou na arena)
                # O amount_paid só se torna > 0 quando o pagamento for de fato confirmado (webhook/caixa)
                booking.amount_paid = 0
                booking.payment_status = 'PENDING'

                if payment_type in ['partial', 'total']:
                    if getattr(settings, 'DEMO_MODE', True):
                        # Bloqueio demonstrativo: impede chamada ao gateway real Asaas
                        booking.delete()
                        messages.warning(
                            self.request,
                            "🔒 Modo Demonstração: Os pagamentos online via PIX real estão desativados neste ambiente de testes para evitar cobranças reais. Para testar o gerenciamento completo de reservas e financeiro, acesse o Painel do Gestor."
                        )
                        return redirect('scheduler:arena_home', arena_slug=self.arena.slug)
                    else:
                        # Em produção: redireciona para o checkout PIX integrado
                        return redirect('scheduler:checkout', booking_id=booking.id)
                elif payment_type in ['venue', 'local']:
                    booking.status = 'CONFIRMED'  # Reserva confirmada, pagamento no local
                    booking.save()
                    customer.total_bookings += 1
                    customer.save()
                    messages.success(self.request, "Reserva confirmada com sucesso! O pagamento será realizado diretamente na arena.")
                    return redirect('scheduler:booking_success', arena_slug=self.arena.slug, booking_id=booking.id)
                else:
                    if getattr(settings, 'DEMO_MODE', True):
                        booking.delete()
                        messages.warning(
                            self.request,
                            "🔒 Modo Demonstração: Os pagamentos online via PIX estão desativados neste ambiente de testes. Utilize o Painel do Gestor para gerenciar agendamentos."
                        )
                        return redirect('scheduler:arena_home', arena_slug=self.arena.slug)
                    else:
                        return redirect('scheduler:checkout', booking_id=booking.id)

        except Exception as e:
            print(f"Erro ao salvar reserva: {e}")  # Log no terminal
            messages.error(self.request, "Erro interno ao processar. Tente novamente.")
            return redirect('scheduler:arena_home', arena_slug=self.arena.slug)


# 2. VIEW DE SUCESSO
class BookingSuccessView(TemplateView):
    template_name = 'scheduler/booking/success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking_id = self.kwargs.get('booking_id')
        context['booking'] = get_object_or_404(Booking, id=booking_id)
        context['arena'] = context['booking'].arena
        return context