from datetime import datetime, timedelta
from django.db.models import Sum

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import FormView, UpdateView, DeleteView
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseRedirect

from apps.backoffice.mixins import ArenaOwnerRequiredMixin
from apps.saas.models import Arena
from apps.backoffice.models import (
    Booking, Court, Customer, PriceRule,
    Equipment, BookingEquipment
)
from apps.backoffice.forms.booking_forms import AdminBookingForm
from apps.lessons.models import ClassSchedule
from apps.backoffice.services import obter_comprovante_bancario_asaas


class BookingCreateView(ArenaOwnerRequiredMixin, FormView):
    template_name = 'backoffice/bookings/booking_form.html'
    form_class = AdminBookingForm

    def dispatch(self, request, *args, **kwargs):
        # 1. Capture Arena from URL
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])

        # 2. Capture Court from URL (if specific court clicked) or GET param
        court_id = self.kwargs.get('court_id') or request.GET.get('court')
        self.court = None
        if court_id:
            self.court = get_object_or_404(Court, pk=court_id, arena=self.arena)

        # 3. Capture Date/Time from GET parameters
        date_str = request.GET.get('date')
        time_str = request.GET.get('time')

        if not date_str or not time_str:
            messages.error(request, "Selecione um horário na agenda.")
            return redirect('backoffice:dashboard', arena_slug=self.arena.slug)

        try:
            naive_start = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            self.start_time = timezone.make_aware(naive_start)
        except ValueError:
            messages.error(request, "Formato de data/hora inválido.")
            return redirect('backoffice:dashboard', arena_slug=self.arena.slug)


        duration = self.arena.config.slot_duration
        self.end_time = self.start_time + timedelta(minutes=duration)

        now = timezone.localtime()
        if now >= self.end_time:
            messages.warning(request, "Atenção: Este horário já passou.")

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """
        Pre-fill the form with data from URL/Context
        This fixes the TypeError: __init__() got an unexpected keyword argument 'start_time'
        """
        initial = super().get_initial()
        initial['start_time'] = self.start_time
        initial['end_time'] = self.end_time
        if self.court:
            initial['court'] = self.court
        return initial

    def get_form_kwargs(self):
        """
        Pass 'arena' to the form's __init__ so it can filter querysets
        """
        kwargs = super().get_form_kwargs()
        kwargs['arena'] = self.arena
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        context['court'] = self.court
        context['start_time'] = self.start_time
        context['is_editing'] = False

        # 1. CÁLCULO DE PREÇO DA QUADRA
        if self.court:
            base_price = PriceRule.get_price_for_booking(self.arena, self.court, self.start_time)
        else:
            base_price = getattr(self.arena.config, 'default_price', 0)
        context['court_price'] = float(base_price)

        # 2. BUSCA E FILTRAGEM DE EQUIPAMENTOS
        if self.court:
            court_modalities = self.court.modalities.all()

            # Busca do banco (QuerySet)
            equipments_qs = Equipment.objects.filter(
                arena=self.arena,
                is_active=True,
                modalities__in=court_modalities
            ).distinct()
        else:
            equipments_qs = Equipment.objects.none()

        # 3. CÁLCULO DE ESTOQUE EM TEMPO REAL
        # Importante: Converter para list() AGORA para persistir o atributo current_stock
        equipments_list = list(equipments_qs)

        # Precisamos saber o fim da reserva para checar colisão
        end_time = self.end_time

        for eq in equipments_list:
            # Soma quantos itens desse tipo já estão alugados neste horário
            used_qty = BookingEquipment.objects.filter(
                booking__arena=self.arena,
                booking__status__in=['CONFIRMED', 'PENDING'],
                booking__start_time__lt=end_time,  # Colisão se começa antes de eu terminar
                booking__end_time__gt=self.start_time,  # E termina depois de eu começar
                equipment=eq
            ).aggregate(total=Sum('quantity'))['total'] or 0

            # Atribui o campo temporário "current_stock" ao objeto na LISTA
            eq.current_stock = max(0, eq.total_quantity - used_qty)

        # Passamos a lista calculada para o template
        context['equipments'] = equipments_list

        return context

    def form_valid(self, form):
        # 1. Extração de Dados Básicos
        # Se o campo court não estiver no form, usamos o self.court definido no dispatch
        court = form.cleaned_data.get('court') or self.court
        start_time = form.cleaned_data['start_time']
        end_time = form.cleaned_data['end_time']

        customer_name = form.cleaned_data['customer_name']
        customer_phone = form.cleaned_data['customer_phone']
        
        import re
        clean_phone = re.sub(r'\D', '', customer_phone)

        # 2. Verificação de Conflito com AULAS
        week_day = start_time.date().weekday()
        conflict_class = ClassSchedule.objects.filter(
            class_group__arena=self.arena,
            class_group__is_active=True,
            class_group__court=court,
            day_of_week=week_day,
            start_time__lt=end_time.time(),
            end_time__gt=start_time.time()
        ).first()

        if conflict_class:
            form.add_error(None, f"BLOQUEADO: Aula '{conflict_class.class_group.name}' neste horário!")
            return self.form_invalid(form)

        # 3. Verificação de Conflito com OUTRAS RESERVAS
        if Booking.objects.filter(
                arena=self.arena,
                court=court,
                status__in=['CONFIRMED', 'PENDING'],
                start_time__lt=end_time,
                end_time__gt=start_time
        ).exists():
            form.add_error(None, "Já existe uma reserva neste horário/quadra!")
            return self.form_invalid(form)

        # 4. Gestão do Cliente (Cria ou Atualiza)
        cpf = form.cleaned_data.get('cpf')
        customer, created = Customer.objects.get_or_create(
            arena=self.arena,
            phone=clean_phone,
            defaults={'name': customer_name, 'cpf': cpf}
        )
        if not created:
            if customer.name != customer_name:
                customer.name = customer_name
            if cpf and customer.cpf != cpf:
                customer.cpf = cpf
            customer.save()

        # 5. Criação Inicial da Reserva (Sem equipamentos ainda)
        # Calculamos apenas o preço base da quadra/regra por enquanto
        base_price = PriceRule.get_price_for_booking(self.arena, court, start_time)

        booking = Booking(
            arena=self.arena,
            court=court,
            customer=customer,
            start_time=start_time,
            end_time=end_time,
            price=base_price,  # Preço provisório
            status='CONFIRMED',  # Padrão, será ajustado abaixo se for Pending
            payment_status='PAID',  # Padrão
            amount_paid=0
        )

        # Captura a escolha de pagamento do HTML
        payment_choice = self.request.POST.get('payment_status', 'paid')

        # Define status inicial (provisório)
        if payment_choice == 'pending':
            booking.status = 'PENDING'
            booking.payment_status = 'PENDING'
        elif payment_choice == 'deposit':
            booking.payment_status = 'PARTIAL'
        else:
            booking.payment_status = 'PAID'

        try:
            # Salva para gerar o ID da reserva
            booking.save()

            # 6. EQUIPAMENTOS DINÂMICOS (A Mágica acontece aqui)
            # Pega a lista de IDs marcada no HTML (ex: ['1', '5'])
            selected_ids = self.request.POST.getlist('equipment_ids')

            for eq_id in selected_ids:
                # Busca o equipamento garantindo que é desta arena
                equipment = Equipment.objects.filter(id=eq_id, arena=self.arena).first()
                if equipment:
                    BookingEquipment.objects.create(
                        booking=booking,
                        equipment=equipment,
                        quantity=1,  # Por enquanto fixo em 1
                        price_snapshot=equipment.rental_price
                    )

            # 7. Atualiza Preço Total e Valor Pago
            # O método update_total_price soma Quadra + Equipamentos salvos acima
            booking.update_total_price()

            # Recalcula o 'amount_paid' baseado no preço final REAL
            if booking.payment_status == 'PAID':
                booking.amount_paid = booking.price
            elif booking.payment_status == 'PARTIAL':
                booking.amount_paid = booking.price / 2
            elif booking.payment_status == 'PENDING':
                booking.amount_paid = 0

            booking.save()

            # Atualiza estatísticas do cliente
            customer.total_bookings += 1
            customer.save()

            messages.success(self.request, "Reserva criada com sucesso!")

        except Exception as e:
            # Se der erro, tenta apagar a reserva para não ficar "lixo" no banco
            if booking.pk: booking.delete()
            form.add_error(None, f"Erro ao salvar: {e}")
            return self.form_invalid(form)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('backoffice:dashboard',
                       kwargs={'arena_slug': self.arena.slug}) + f"?date={self.start_time.date()}"


class BookingUpdateView(ArenaOwnerRequiredMixin, UpdateView):
    model = Booking
    form_class = AdminBookingForm
    template_name = 'backoffice/bookings/booking_form.html'
    context_object_name = 'booking'

    def get_queryset(self):
        return Booking.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['arena'] = self.object.arena
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        # Pre-fill customer manual fields
        initial['customer_name'] = self.object.customer.name
        initial['customer_phone'] = self.object.customer.phone
        initial['cpf'] = self.object.customer.cpf

        # Pre-fill equipment checkboxes based on existing BookingEquipment relations
        # We check if there is ANY equipment with "Raquete" or "Bola" attached to this booking
        has_racket = BookingEquipment.objects.filter(booking=self.object, equipment__name__icontains="Raquete").exists()
        has_ball = BookingEquipment.objects.filter(booking=self.object, equipment__name__icontains="Bola").exists()

        initial['wants_racket'] = has_racket
        initial['wants_ball'] = has_ball

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Dados básicos da Reserva sendo editada
        context['arena'] = self.object.arena
        context['court'] = self.object.court
        context['start_time'] = self.object.start_time
        context['is_editing'] = True

        # 1. CÁLCULO DE PREÇO DA QUADRA
        base_price = PriceRule.get_price_for_booking(
            self.object.arena, self.object.court, self.object.start_time
        )
        context['court_price'] = float(base_price)

        # 2. BUSCA DE EQUIPAMENTOS (Filtrado por modalidade)
        court_modalities = self.object.court.modalities.all()

        equipments_qs = Equipment.objects.filter(
            arena=self.object.arena,
            is_active=True,
            modalities__in=court_modalities
        ).distinct()

        # 3. CÁLCULO DE ESTOQUE (COM CORREÇÃO DE LISTA)
        # Importante: Converter para list() AGORA para persistir o atributo current_stock
        equipments_list = list(equipments_qs)

        start_time = self.object.start_time
        end_time = self.object.end_time

        for eq in equipments_list:
            # Soma quantos itens já estão alugados neste horário
            used_qty = BookingEquipment.objects.filter(
                booking__arena=self.object.arena,
                booking__status__in=['CONFIRMED', 'PENDING'],
                booking__start_time__lt=end_time,
                booking__end_time__gt=start_time,
                equipment=eq
            ).exclude(booking__pk=self.object.pk) \
                           .aggregate(total=Sum('quantity'))['total'] or 0
            # ^^^ O exclude é CRUCIAL na edição: não conta o que eu mesmo já reservei!

            # Atribui o campo temporário "current_stock"
            eq.current_stock = max(0, eq.total_quantity - used_qty)

        # Passa a lista calculada para o template
        context['equipments'] = equipments_list

        # 4. EQUIPAMENTOS JÁ SELECIONADOS (Para marcar o checkbox)
        current_eq_ids = self.object.equipments.values_list('equipment_id', flat=True)
        context['selected_eq_ids'] = list(current_eq_ids)

        # 5. DADOS DO PAGAMENTO BANCÁRIO / ASAAS
        last_payment = self.object.payments.filter(transaction_id__isnull=False).exclude(transaction_id='').last()
        context['has_bank_payment'] = bool(last_payment)
        context['bank_payment'] = last_payment
        if last_payment:
            context['bank_receipt_url'] = last_payment.bank_receipt_url or last_payment.invoice_url

        return context

    def form_valid(self, form):
        # 1. Atualiza Dados do Cliente (Se mudou)
        customer = self.object.customer
        new_name = form.cleaned_data['customer_name']
        new_cpf = form.cleaned_data.get('cpf')
        if customer.name != new_name or (new_cpf and customer.cpf != new_cpf):
            customer.name = new_name
            if new_cpf:
                customer.cpf = new_cpf
            customer.save()

        # 2. SINCRONIZAÇÃO DE EQUIPAMENTOS (A Lógica Dinâmica)

        # A. O que o usuário marcou agora no formulário? (Lista de IDs vindo do HTML)
        # Convertendo para int para comparar corretamente
        selected_ids = [int(x) for x in self.request.POST.getlist('equipment_ids')]

        # B. O que já estava salvo no banco?
        current_eq_ids = list(self.object.equipments.values_list('equipment_id', flat=True))

        # C. Adicionar Novos (Marcou agora, mas não tinha antes)
        for eq_id in selected_ids:
            if eq_id not in current_eq_ids:
                eq = Equipment.objects.filter(id=eq_id, arena=self.object.arena).first()
                if eq:
                    BookingEquipment.objects.create(
                        booking=self.object,
                        equipment=eq,
                        quantity=1,
                        price_snapshot=eq.rental_price
                    )

        # D. Remover Desmarcados (Tinha antes, mas não veio agora)
        for eq_id in current_eq_ids:
            if eq_id not in selected_ids:
                # Remove o BookingEquipment específico
                self.object.equipments.filter(equipment_id=eq_id).delete()

        # 3. Recalcula Preço Total (Soma Quadra + Equipamentos atuais)
        self.object.update_total_price()

        # 4. Atualiza Status Financeiro
        payment_choice = self.request.POST.get('payment_status')

        if self.object.payment_status != 'PAID':
            if payment_choice:
                if payment_choice == 'pending':
                    self.object.payment_status = 'PENDING'
                    self.object.amount_paid = 0
                elif payment_choice == 'deposit':
                    self.object.payment_status = 'PARTIAL'
                    self.object.amount_paid = self.object.price / 2
                elif payment_choice == 'paid':
                    self.object.payment_status = 'PAID'
                    self.object.amount_paid = self.object.price
            else:
                if self.object.payment_status == 'PARTIAL':
                    self.object.amount_paid = self.object.price / 2
        else:
            print(f"--- SEGURANÇA: Tentativa de alterar pagamento já confirmado na reserva {self.object.id} ---")

        # O status da reserva (CONFIRMED/PENDING) geralmente segue o pagamento
        if self.object.payment_status == 'PENDING':
            self.object.status = 'PENDING'
        else:
            self.object.status = 'CONFIRMED'

        self.object.save()
        messages.success(self.request, "Reserva atualizada com sucesso!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('backoffice:dashboard',
                       kwargs={'arena_slug': self.object.arena.slug}) + f"?date={self.object.start_time.date()}"


class BookingDeleteView(ArenaOwnerRequiredMixin, DeleteView):
    model = Booking
    template_name = 'backoffice/bookings/booking_confirm_delete.html'

    def get_queryset(self):
        return Booking.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.object.arena
        return context

    def form_valid(self, form):
        self.object = self.get_object()
        success_url = self.get_success_url()

        # Soft Delete (Cancel)
        self.object.status = 'CANCELED'
        self.object.save()

        # Optional: Release equipment?
        # Usually canceled booking equipment stays in record but effectively 'returned'
        # or you might want to delete BookingEquipment records here.

        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        messages.success(self.request, "Reserva cancelada.")
        return reverse('backoffice:dashboard',
                       kwargs={'arena_slug': self.object.arena.slug}) + f"?date={self.object.start_time.date()}"


def booking_bank_receipt(request, arena_slug, pk):
    """
    Redireciona para o comprovante bancário oficial emitido pelo Asaas (Banco/Pix).
    """
    arena = get_object_or_404(Arena, slug=arena_slug)
    if not (request.user.is_superuser or arena.owner == request.user):
        messages.error(request, "Acesso não autorizado.")
        return redirect('backoffice:dashboard', arena_slug=arena.slug)

    booking = get_object_or_404(Booking, pk=pk, arena=arena)
    receipt_url = obter_comprovante_bancario_asaas(booking)
    if receipt_url:
        return redirect(receipt_url)

    messages.warning(
        request,
        "Nenhum comprovante bancário online gerado no Asaas para esta reserva (pagamento feito no balcão)."
    )
    return redirect('backoffice:booking_edit', arena_slug=arena.slug, pk=booking.id)