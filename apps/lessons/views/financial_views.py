from datetime import datetime
from decimal import Decimal
from django.views.generic import ListView, DetailView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.backoffice.mixins import ArenaOwnerRequiredMixin
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import JsonResponse
from django.template.loader import render_to_string
from apps.lessons.models import MonthlyFee, Enrollment
from apps.backoffice.models import Arena


class FinancialListView(ArenaOwnerRequiredMixin, ListView):
    model = MonthlyFee
    template_name = 'lessons/financial/financial_list.html'
    context_object_name = 'cobrancas'
    paginate_by = 20

    def get_queryset(self):
        # Filtra pela arena
        queryset = MonthlyFee.objects.filter(
            enrollment__class_group__arena__slug=self.kwargs['arena_slug']
        ).select_related('enrollment__customer', 'enrollment__class_group').order_by('due_date', 'id')

        # Filtro de Status (Opcional: ?status=PENDING)
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filtro de Busca (Opcional: ?q=...)
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(enrollment__customer__name__icontains=q) |
                Q(enrollment__customer__phone__icontains=q) |
                Q(enrollment__class_group__name__icontains=q)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        arena = Arena.objects.get(slug=self.kwargs['arena_slug'])
        context['arena'] = arena

        # Totais para o cabeçalho da página (totais gerais da arena)
        base_qs = MonthlyFee.objects.filter(
            enrollment__class_group__arena__slug=self.kwargs['arena_slug']
        )
        context['total_pendente'] = base_qs.filter(status='PENDING').aggregate(Sum('value'))['value__sum'] or 0
        context['total_recebido'] = base_qs.filter(status='PAID').aggregate(Sum('value'))['value__sum'] or 0
        context['total_atrasado'] = base_qs.filter(status='OVERDUE').aggregate(Sum('value'))['value__sum'] or 0

        # Next page URL para Infinite Scroll
        page_obj = context.get('page_obj')
        if page_obj and page_obj.has_next():
            qp_next = self.request.GET.copy()
            qp_next['page'] = page_obj.next_page_number()
            context['next_page_url'] = f"?{qp_next.urlencode()}"
        else:
            context['next_page_url'] = None

        # Alunos ativos para geração de cobrança individual
        context['active_enrollments'] = Enrollment.objects.filter(
            class_group__arena=arena,
            status='ACTIVE'
        ).select_related('customer', 'class_group').order_by('customer__name')

        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            page_obj = context.get('page_obj')
            html = render_to_string(
                'lessons/financial/_cobranca_rows.html',
                context,
                request=self.request
            )
            has_next = page_obj.has_next() if page_obj else False
            next_url = None
            if has_next:
                qp = self.request.GET.copy()
                qp['page'] = page_obj.next_page_number()
                next_url = f"?{qp.urlencode()}"

            return JsonResponse({
                'html': html,
                'has_next': has_next,
                'next_url': next_url,
                'count': page_obj.paginator.count if page_obj else 0,
                'total_pendente': f"{context['total_pendente']:.2f}",
                'total_recebido': f"{context['total_recebido']:.2f}",
                'total_atrasado': f"{context['total_atrasado']:.2f}",
            })
        return super().render_to_response(context, **response_kwargs)


class FinancialDetailView(ArenaOwnerRequiredMixin, DetailView):
    """ Detalhes de uma mensalidade/fatura específica """
    model = MonthlyFee
    template_name = 'lessons/financial/financial_detail.html'
    context_object_name = 'fee'

    def get_queryset(self):
        return MonthlyFee.objects.filter(
            enrollment__class_group__arena__slug=self.kwargs['arena_slug']
        ).select_related(
            'enrollment__customer',
            'enrollment__class_group__arena',
            'enrollment__class_group__teacher',
            'enrollment__class_group__court'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        arena = Arena.objects.get(slug=self.kwargs['arena_slug'])
        context['arena'] = arena
        # Outras faturas da mesma matrícula para visualização de histórico
        context['other_fees'] = MonthlyFee.objects.filter(
            enrollment=self.object.enrollment
        ).exclude(pk=self.object.pk).order_by('-due_date')
        context['status_choices'] = MonthlyFee.STATUS
        return context


class FeeStatusUpdateView(ArenaOwnerRequiredMixin, View):
    """ Altera rapidamente o status da fatura """

    def post(self, request, arena_slug, pk):
        fee = get_object_or_404(MonthlyFee, pk=pk, enrollment__class_group__arena__slug=arena_slug)
        new_status = request.POST.get('status')
        valid_statuses = dict(MonthlyFee.STATUS).keys()

        if new_status in valid_statuses:
            fee.status = new_status
            if new_status == 'PAID':
                paid_at_str = request.POST.get('paid_at')
                if paid_at_str:
                    try:
                        fee.paid_at = datetime.strptime(paid_at_str, '%Y-%m-%d').date()
                    except ValueError:
                        fee.paid_at = timezone.now().date()
                elif not fee.paid_at:
                    fee.paid_at = timezone.now().date()
            else:
                fee.paid_at = None

            fee.save()
            messages.success(request, f"Status da fatura alterado para {fee.get_status_display()}.")
        else:
            messages.error(request, "Status inválido.")

        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('lessons:financial_detail', arena_slug=arena_slug, pk=pk)


class FeeUpdateView(ArenaOwnerRequiredMixin, View):
    """ Edita dados da fatura (vencimento, valor, status, data de pagamento) """

    def post(self, request, arena_slug, pk):
        fee = get_object_or_404(MonthlyFee, pk=pk, enrollment__class_group__arena__slug=arena_slug)

        due_date_str = request.POST.get('due_date')
        value_str = request.POST.get('value')
        status = request.POST.get('status')
        paid_at_str = request.POST.get('paid_at')

        try:
            if due_date_str:
                fee.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            if value_str:
                clean_value = value_str.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
                fee.value = Decimal(clean_value)
            if status in dict(MonthlyFee.STATUS).keys():
                fee.status = status
                if status == 'PAID':
                    if paid_at_str:
                        fee.paid_at = datetime.strptime(paid_at_str, '%Y-%m-%d').date()
                    elif not fee.paid_at:
                        fee.paid_at = timezone.now().date()
                else:
                    fee.paid_at = None

            fee.save()
            messages.success(request, "Fatura atualizada com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao atualizar fatura: {e}")

        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('lessons:financial_detail', arena_slug=arena_slug, pk=pk)


class FeePayView(ArenaOwnerRequiredMixin, View):
    """ Action para marcar uma mensalidade como PAGA """

    def get(self, request, arena_slug, pk):
        fee = get_object_or_404(MonthlyFee, pk=pk, enrollment__class_group__arena__slug=arena_slug)

        # Marca como pago
        fee.status = 'PAID'
        fee.paid_at = timezone.now().date()
        fee.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Pagamento de {fee.enrollment.customer.name} confirmado!"
            })

        messages.success(request, f"Pagamento de {fee.enrollment.customer.name} confirmado!")
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('lessons:financial_list', arena_slug=arena_slug)


from apps.lessons.services import generate_monthly_fees_routine


class FeeUndoPayView(ArenaOwnerRequiredMixin, View):
    """ Action para desfazer um pagamento (se clicou errado) """

    def get(self, request, arena_slug, pk):
        fee = get_object_or_404(MonthlyFee, pk=pk, enrollment__class_group__arena__slug=arena_slug)

        fee.status = 'PENDING'
        fee.paid_at = None
        fee.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Pagamento de {fee.enrollment.customer.name} estornado/desfeito."
            })

        messages.warning(request, f"Pagamento de {fee.enrollment.customer.name} estornado/desfeito.")
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('lessons:financial_list', arena_slug=arena_slug)


class GenerateMonthlyFeesView(ArenaOwnerRequiredMixin, View):
    """ Action para gerar cobranças em lote para uma arena """

    def post(self, request, arena_slug):
        arena = get_object_or_404(Arena, slug=arena_slug)
        mode = request.POST.get('mode', 'default')
        if mode not in ['default', 'current_month', 'next_month', 'both']:
            mode = 'default'

        created_count, details = generate_monthly_fees_routine(arena=arena, mode=mode)

        if created_count > 0:
            msg = f"{created_count} cobrança(s) gerada(s) com sucesso!"
        else:
            msg = "Nenhuma nova cobrança pendente. Todas as faturas dos alunos ativos já estão em dia!"

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'created_count': created_count,
                'message': msg
            })

        if created_count > 0:
            messages.success(request, msg)
        else:
            messages.info(request, msg)

        return redirect('lessons:financial_list', arena_slug=arena_slug)


class FeeCreateView(ArenaOwnerRequiredMixin, View):
    """ Cria manualmente uma mensalidade avulsa para um aluno/matrícula """

    def post(self, request, arena_slug):
        from apps.lessons.models import Enrollment
        arena = get_object_or_404(Arena, slug=arena_slug)
        enrollment_id = request.POST.get('enrollment')
        enrollment = get_object_or_404(Enrollment, pk=enrollment_id, class_group__arena=arena)

        ref_month_str = request.POST.get('reference_month')
        due_date_str = request.POST.get('due_date')
        value_str = request.POST.get('value')
        status = request.POST.get('status', 'PENDING')

        errors = {}

        # Mês de referência
        reference_date = None
        if ref_month_str:
            try:
                reference_date = datetime.strptime(ref_month_str, '%Y-%m').date().replace(day=1)
            except ValueError:
                errors['reference_month'] = 'Mês de referência inválido.'
        else:
            errors['reference_month'] = 'Informe o mês de referência.'

        # Vencimento
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                errors['due_date'] = 'Data de vencimento inválida.'
        else:
            errors['due_date'] = 'Informe a data de vencimento.'

        # Valor
        value = None
        if value_str:
            try:
                clean_val = str(value_str).replace('R$', '').replace(' ', '').replace(',', '.')
                value = Decimal(clean_val)
                if value < 0:
                    errors['value'] = 'O valor não pode ser negativo.'
            except Exception:
                errors['value'] = 'Valor inválido.'
        else:
            errors['value'] = 'Informe o valor da fatura.'

        # Status
        valid_statuses = dict(MonthlyFee.STATUS).keys()
        if status not in valid_statuses:
            status = 'PENDING'

        # Validação: Já existe fatura para esse mês?
        if reference_date and not errors:
            fee_exists = MonthlyFee.objects.filter(
                enrollment=enrollment,
                reference_date=reference_date
            ).exists()
            if fee_exists:
                errors['reference_month'] = f'Já existe uma cobrança de {reference_date.strftime("%m/%Y")} cadastrada para este aluno.'

        # Regra: Uma cobrança de mensalidade não pode iniciar atrasada
        today = timezone.now().date()
        if due_date and status == 'PENDING' and due_date < today:
            due_date = today

        if errors:
            first_err = next(iter(errors.values()))
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': errors,
                    'message': first_err
                }, status=400)
            messages.error(request, first_err)
            next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
            return redirect(next_url or 'lessons:financial_list', arena_slug=arena_slug)

        paid_at = today if status == 'PAID' else None

        fee = MonthlyFee.objects.create(
            enrollment=enrollment,
            reference_date=reference_date,
            due_date=due_date,
            value=value,
            status=status,
            paid_at=paid_at
        )

        msg = f"Cobrança de {enrollment.customer.name} (Ref: {reference_date.strftime('%m/%Y')} - R$ {fee.value}) gerada com sucesso!"

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            from django.urls import reverse
            return JsonResponse({
                'success': True,
                'fee_id': fee.id,
                'redirect_url': reverse('lessons:financial_detail', kwargs={'arena_slug': arena_slug, 'pk': fee.pk}),
                'message': msg
            })

        messages.success(request, msg)
        return redirect('lessons:financial_detail', arena_slug=arena_slug, pk=fee.pk)
