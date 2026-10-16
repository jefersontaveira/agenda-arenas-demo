# apps/saas/views.py
from datetime import date
from calendar import monthrange
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, DetailView, UpdateView, ListView, CreateView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db.models import Count, Q, Sum, Max

from .models import Arena, Subscription
from .forms import ArenaMasterForm, SubscriptionForm, GenerateSubscriptionsForm
from apps.backoffice.models import Booking, Court, Customer


class SuperuserRequiredMixin(UserPassesTestMixin):
    """Garante que apenas superusuários do Django tenham acesso ao painel Master."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def handle_no_permission(self):
        messages.error(self.request, "Acesso restrito ao Administrador Geral da Plataforma.")
        return redirect('login')


def superuser_check(user):
    return user.is_authenticated and user.is_superuser


class MasterDashboardView(SuperuserRequiredMixin, TemplateView):
    """
    Painel Central de Logística do SaaS.
    Mostra métricas consolidadas de todas as Arenas, faturamento e quantitativos.
    """
    template_name = 'saas/master_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        current_year = today.year
        current_month = today.month

        # Arenas com anotações de quantitativos
        arenas_qs = Arena.objects.annotate(
            total_courts=Count('courts', distinct=True),
            total_bookings=Count('bookings', distinct=True),
            online_bookings=Count('bookings', filter=Q(bookings__origin='ONLINE'), distinct=True),
            backoffice_bookings=Count('bookings', filter=Q(bookings__origin='BACKOFFICE'), distinct=True),
            last_booking_date=Max('bookings__start_time')
        ).order_by('-created_at')

        # Filtro de busca na tabela
        q = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '').strip()
        
        filtered_arenas = arenas_qs
        if q:
            filtered_arenas = filtered_arenas.filter(
                Q(name__icontains=q) | 
                Q(owner_name__icontains=q) |
                Q(owner_phone__icontains=q) |
                Q(slug__icontains=q)
            )
        if status_filter == 'active':
            filtered_arenas = filtered_arenas.filter(is_active=True)
        elif status_filter == 'inactive':
            filtered_arenas = filtered_arenas.filter(is_active=False)

        # Métricas Globais
        total_arenas = arenas_qs.count()
        active_arenas = arenas_qs.filter(is_active=True).count()
        inactive_arenas = total_arenas - active_arenas
        
        # MRR (Receita Recorrente Mensal contratada)
        mrr = arenas_qs.filter(is_active=True).aggregate(total=Sum('monthly_fee'))['total'] or 0

        # Mensalidades do Mês Atual
        month_subs = Subscription.objects.filter(due_date__year=current_year, due_date__month=current_month)
        paid_month = month_subs.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0
        pending_month = month_subs.filter(status__in=['PENDING', 'OVERDUE']).aggregate(total=Sum('amount'))['total'] or 0

        # Arenas Inadimplentes (Qualquer fatura OVERDUE ou PENDING vencida)
        overdue_arena_ids = Subscription.objects.filter(
            Q(status='OVERDUE') | Q(status='PENDING', due_date__lt=today)
        ).values_list('arena_id', flat=True).distinct()
        overdue_arenas_count = Arena.objects.filter(id__in=overdue_arena_ids, is_active=True).count()

        # Quantitativos Globais de Reservas
        all_bookings = Booking.objects.all()
        total_bookings_count = all_bookings.count()
        total_online_count = all_bookings.filter(origin='ONLINE').count()
        total_backoffice_count = all_bookings.filter(origin='BACKOFFICE').count()
        online_rate = round((total_online_count / total_bookings_count * 100), 1) if total_bookings_count > 0 else 0

        # Últimas Mensalidades
        recent_subscriptions = Subscription.objects.select_related('arena').order_by('-due_date')[:8]

        context.update({
            'arenas': filtered_arenas,
            'total_arenas': total_arenas,
            'active_arenas': active_arenas,
            'inactive_arenas': inactive_arenas,
            'overdue_arenas_count': overdue_arenas_count,
            'mrr': mrr,
            'paid_month': paid_month,
            'pending_month': pending_month,
            'total_bookings_count': total_bookings_count,
            'total_online_count': total_online_count,
            'total_backoffice_count': total_backoffice_count,
            'online_rate': online_rate,
            'recent_subscriptions': recent_subscriptions,
            'current_month_name': today.strftime('%B de %Y'),
            'search_query': q,
            'status_filter': status_filter,
            'generate_form': GenerateSubscriptionsForm(),
        })
        return context


class ArenaMasterDetailView(SuperuserRequiredMixin, DetailView):
    """Detalhes completos de logística de uma Arena específica."""
    model = Arena
    template_name = 'saas/arena_detail.html'
    context_object_name = 'arena'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        arena = self.object

        # Reservas desta Arena
        bookings = Booking.objects.filter(arena=arena)
        total_bookings = bookings.count()
        online_bookings = bookings.filter(origin='ONLINE').count()
        backoffice_bookings = bookings.filter(origin='BACKOFFICE').count()
        online_percent = round((online_bookings / total_bookings * 100), 1) if total_bookings > 0 else 0

        # Faturamento movimentado nas reservas da arena
        total_booking_volume = bookings.filter(status='CONFIRMED').aggregate(total=Sum('price'))['total'] or 0

        # Quadras e Clientes
        courts = Court.objects.filter(arena=arena)
        customers_count = Customer.objects.filter(arena=arena).count()

        # Histórico de Mensalidades do SaaS
        subscriptions = arena.subscriptions.order_by('-due_date')

        context.update({
            'total_bookings': total_bookings,
            'online_bookings': online_bookings,
            'backoffice_bookings': backoffice_bookings,
            'online_percent': online_percent,
            'total_booking_volume': total_booking_volume,
            'courts': courts,
            'customers_count': customers_count,
            'subscriptions': subscriptions,
        })
        return context


class ArenaMasterCreateView(SuperuserRequiredMixin, CreateView):
    """Cadastrar nova Arena no ecossistema SaaS com todas as configurações pertinentes."""
    model = Arena
    form_class = ArenaMasterForm
    template_name = 'saas/arena_form.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        arena = self.object
        msg = f"Arena <strong>'{arena.name}'</strong> cadastrada com sucesso!"
        
        if getattr(form, 'created_user_account', None):
            user = form.created_user_account
            pwd = getattr(form, 'user_password_used', None)
            if pwd:
                msg += f" Conta de acesso criada para <strong>{user.email}</strong> (Senha inicial: <code>{pwd}</code>)."
            else:
                msg += f" Usuário de acesso <strong>{user.email}</strong> vinculado com sucesso."

        if getattr(form, 'first_invoice_created', None):
            sub = form.first_invoice_created
            msg += f" Primeira fatura de R$ {sub.amount:.2f} gerada para vencimento em {sub.due_date.strftime('%d/%m/%Y')}."

        messages.success(self.request, msg)
        return response

    def get_success_url(self):
        return reverse('saas:arena_detail', kwargs={'pk': self.object.pk})


class ArenaMasterUpdateView(SuperuserRequiredMixin, UpdateView):
    """Editar dados cadastrais, plano, mensalidade e dono da Arena."""
    model = Arena
    form_class = ArenaMasterForm
    template_name = 'saas/arena_form.html'
    context_object_name = 'arena'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Dados da arena '{self.object.name}' atualizados com sucesso!")
        return response

    def get_success_url(self):
        return reverse('saas:arena_detail', kwargs={'pk': self.object.pk})


@user_passes_test(superuser_check)
def toggle_arena_active(request, pk):
    """Ativar ou Bloquear arena (trava de inadimplência ou cancelamento)."""
    arena = get_object_or_404(Arena, pk=pk)
    arena.is_active = not arena.is_active
    arena.save()
    status_str = "ativada" if arena.is_active else "bloqueada / desativada"
    messages.info(request, f"Arena '{arena.name}' foi {status_str}.")
    return redirect(request.META.get('HTTP_REFERER', reverse('saas:dashboard')))


class SubscriptionMasterListView(SuperuserRequiredMixin, ListView):
    """Listagem de todas as faturas e mensalidades do SaaS."""
    model = Subscription
    template_name = 'saas/subscription_list.html'
    context_object_name = 'subscriptions'
    paginate_by = 25

    def get_queryset(self):
        qs = Subscription.objects.select_related('arena').order_by('-due_date')
        status = self.request.GET.get('status', '').strip()
        arena_id = self.request.GET.get('arena', '').strip()
        if status:
            qs = qs.filter(status=status)
        if arena_id:
            qs = qs.filter(arena_id=arena_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arenas'] = Arena.objects.order_by('name')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_arena'] = self.request.GET.get('arena', '')
        return context


class SubscriptionCreateView(SuperuserRequiredMixin, CreateView):
    """Criar fatura/mensalidade avulsa."""
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'saas/subscription_form.html'
    success_url = reverse_lazy('saas:subscription_list')

    def get_initial(self):
        initial = super().get_initial()
        arena_id = self.request.GET.get('arena')
        if arena_id:
            try:
                arena = Arena.objects.get(pk=arena_id)
                initial['arena'] = arena
                initial['amount'] = arena.monthly_fee
                # Calcular data com base no due_day
                today = timezone.localdate()
                day = min(arena.due_day or 10, monthrange(today.year, today.month)[1])
                initial['due_date'] = date(today.year, today.month, day)
            except Arena.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        messages.success(self.request, "Mensalidade criada com sucesso!")
        return super().form_valid(form)


class SubscriptionUpdateView(SuperuserRequiredMixin, UpdateView):
    """Editar fatura/mensalidade."""
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'saas/subscription_form.html'
    success_url = reverse_lazy('saas:subscription_list')

    def form_valid(self, form):
        messages.success(self.request, "Mensalidade atualizada com sucesso!")
        return super().form_valid(form)


@user_passes_test(superuser_check)
def mark_subscription_paid(request, pk):
    """Registrar pagamento imediato de uma mensalidade."""
    subscription = get_object_or_404(Subscription, pk=pk)
    subscription.status = 'PAID'
    subscription.payment_date = timezone.localdate()
    subscription.save()
    messages.success(request, f"Pagamento da fatura de R$ {subscription.amount} da arena '{subscription.arena.name}' registrado com sucesso!")
    return redirect(request.META.get('HTTP_REFERER', reverse('saas:subscription_list')))


@user_passes_test(superuser_check)
def generate_monthly_subscriptions(request):
    """
    Gera automaticamente faturas de mensalidade para todas as arenas ativas que possuam valor configurado.
    Evita duplicidade se já houver fatura no mês.
    """
    if request.method == 'POST':
        form = GenerateSubscriptionsForm(request.POST)
        if form.is_valid():
            month = form.cleaned_data['month']
            year = form.cleaned_data['year']
            
            active_arenas = Arena.objects.filter(is_active=True, monthly_fee__gt=0)
            created_count = 0
            skipped_count = 0

            for arena in active_arenas:
                # Checa se já existe fatura deste mês/ano para esta arena
                exists = Subscription.objects.filter(
                    arena=arena,
                    due_date__year=year,
                    due_date__month=month
                ).exists()

                if not exists:
                    # Ajusta dia de vencimento para o mês
                    max_day = monthrange(year, month)[1]
                    due_day = min(arena.due_day or 10, max_day)
                    due_date = date(year, month, due_day)

                    Subscription.objects.create(
                        arena=arena,
                        due_date=due_date,
                        amount=arena.monthly_fee,
                        status='PENDING',
                        notes=f"Gerado automaticamente - Ref. {month:02d}/{year}"
                    )
                    created_count += 1
                else:
                    skipped_count += 1

            messages.success(
                request,
                f"Processamento concluído: {created_count} faturas geradas com sucesso! ({skipped_count} já existiam)."
            )
    return redirect('saas:dashboard')