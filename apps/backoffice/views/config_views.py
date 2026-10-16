from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from apps.backoffice.mixins import ArenaOwnerRequiredMixin
from django.contrib import messages
from django.http import JsonResponse

# Models
from apps.saas.models import Arena
from apps.backoffice.models import (
    ArenaConfig,
    PriceRule,
    Equipment,
    ArenaOpeningHour,
    AsaasConfig,
    Modality,
    Court,
)
# Forms
from apps.backoffice.forms.config_forms import (
    ArenaConfigForm,
    SiteCustomizeForm,
    PriceRuleForm,
    EquipmentForm,
    ArenaOpeningHourForm,
    AsaasConfigForm
)
from django.shortcuts import redirect

# --- 1. CONFIGURAÇÃO GERAL (Logo, Preço Padrão) ---
class ArenaConfigUpdateView(ArenaOwnerRequiredMixin, UpdateView):
    model = ArenaConfig
    form_class = ArenaConfigForm
    template_name = 'backoffice/config/config_form.html'

    def get_object(self, queryset=None):
        arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])

        # CORREÇÃO: Removemos campos antigos do defaults
        config, created = ArenaConfig.objects.get_or_create(
            arena=arena,
            defaults={
                'slot_duration': 60,
                'default_price': 0,
                'payment_policy': 'FULL_OR_HALF'
            }
        )
        return config

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.object.arena
        return context

    def get_success_url(self):
        messages.success(self.request, "Configurações atualizadas com sucesso!")
        return reverse('backoffice:arena_config', kwargs={'arena_slug': self.object.arena.slug})


# --- 1.1. PERSONALIZAR SITE DA ARENA ---
class SiteCustomizeView(ArenaOwnerRequiredMixin, View):
    template_name = 'backoffice/config/site_customize.html'

    def _ensure_opening_hours(self, arena):
        """Garante que existam registros de horários para os 7 dias da semana (0 a 6)."""
        existing_days = set(ArenaOpeningHour.objects.filter(arena=arena).values_list('weekday', flat=True))
        for day in range(7):
            if day not in existing_days:
                # Padrão: Seg a Sab aberto das 07:00 às 23:00; Domingo fechado por padrão (ou editável)
                is_closed = (day == 6)
                open_t = None if is_closed else "07:00"
                close_t = None if is_closed else "23:00"
                ArenaOpeningHour.objects.create(
                    arena=arena,
                    weekday=day,
                    open_time=open_t,
                    close_time=close_t,
                    is_closed=is_closed
                )

    def get(self, request, arena_slug):
        arena = get_object_or_404(Arena, slug=arena_slug)
        config, _ = ArenaConfig.objects.get_or_create(
            arena=arena,
            defaults={'slot_duration': 60, 'default_price': 0}
        )
        self._ensure_opening_hours(arena)

        form = SiteCustomizeForm(instance=config)
        opening_hours = ArenaOpeningHour.objects.filter(arena=arena).order_by('weekday')

        # Monta a URL pública canônica da página de reservas
        public_url = request.build_absolute_uri(
            reverse('scheduler:arena_home', kwargs={'arena_slug': arena.slug})
        )

        return render(request, self.template_name, {
            'arena': arena,
            'config': config,
            'form': form,
            'opening_hours': opening_hours,
            'public_url': public_url,
        })

    def post(self, request, arena_slug):
        arena = get_object_or_404(Arena, slug=arena_slug)
        config, _ = ArenaConfig.objects.get_or_create(
            arena=arena,
            defaults={'slot_duration': 60, 'default_price': 0}
        )
        self._ensure_opening_hours(arena)

        form = SiteCustomizeForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()

            # Salva os 7 horários da semana diretamente
            for day in range(7):
                hour_obj = ArenaOpeningHour.objects.filter(arena=arena, weekday=day).first()
                if hour_obj:
                    is_closed = request.POST.get(f'day_{day}_closed') == 'on'
                    open_t = request.POST.get(f'day_{day}_open_time')
                    close_t = request.POST.get(f'day_{day}_close_time')

                    hour_obj.is_closed = is_closed
                    hour_obj.open_time = open_t if not is_closed and open_t else None
                    hour_obj.close_time = close_t if not is_closed and close_t else None
                    hour_obj.save()

            messages.success(request, "Site da arena e horários atualizados com sucesso!")
            return redirect('backoffice:site_customize', arena_slug=arena.slug)

        opening_hours = ArenaOpeningHour.objects.filter(arena=arena).order_by('weekday')
        public_url = request.build_absolute_uri(
            reverse('scheduler:arena_home', kwargs={'arena_slug': arena.slug})
        )
        return render(request, self.template_name, {
            'arena': arena,
            'config': config,
            'form': form,
            'opening_hours': opening_hours,
            'public_url': public_url,
        })



# --- 2. REGRAS DE PREÇO ---

class PriceRuleListView(ArenaOwnerRequiredMixin, ListView):
    model = PriceRule
    template_name = 'backoffice/config/price_rules_list.html'
    context_object_name = 'rules'

    def get_queryset(self):
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])
        return PriceRule.objects.filter(arena=self.arena).select_related('court').prefetch_related('days').order_by('start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        context['courts'] = Court.objects.filter(arena=self.arena).order_by('name')
        return context


class PriceRuleCreateView(ArenaOwnerRequiredMixin, CreateView):
    model = PriceRule
    form_class = PriceRuleForm
    template_name = 'backoffice/config/price_rule_form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['arena'] = self.arena
        return kwargs

    def form_valid(self, form):
        form.instance.arena = self.arena
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Regra '{self.object.name}' criada com sucesso!"
            })
        messages.success(self.request, f"Regra '{self.object.name}' criada com sucesso!")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(e) for e in error_list]
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('backoffice:price_rules', kwargs={'arena_slug': self.arena.slug})


class PriceRuleUpdateView(ArenaOwnerRequiredMixin, UpdateView):
    model = PriceRule
    form_class = PriceRuleForm
    template_name = 'backoffice/config/price_rule_form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        return context

    def get_queryset(self):
        return PriceRule.objects.filter(arena=self.arena)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['arena'] = self.arena
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Regra '{self.object.name}' atualizada com sucesso!"
            })
        messages.success(self.request, f"Regra '{self.object.name}' atualizada com sucesso!")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(e) for e in error_list]
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('backoffice:price_rules', kwargs={'arena_slug': self.arena.slug})


class PriceRuleDeleteView(ArenaOwnerRequiredMixin, DeleteView):
    model = PriceRule
    template_name = 'backoffice/config/price_rule_confirm_delete.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        return context

    def get_queryset(self):
        return PriceRule.objects.filter(arena=self.arena)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        name = self.object.name
        self.object.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Regra '{name}' excluída com sucesso!"
            })
        messages.success(request, f"Regra '{name}' removida com sucesso.")
        return redirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('backoffice:price_rules', kwargs={'arena_slug': self.arena.slug})



# --- 3. EQUIPAMENTOS (NOVO) ---

class EquipmentListView(ArenaOwnerRequiredMixin, ListView):
    model = Equipment
    template_name = 'backoffice/config/equipment_list.html'
    context_object_name = 'equipments'

    def get_queryset(self):
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])
        return Equipment.objects.filter(arena=self.arena).prefetch_related('modalities').order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        context['all_modalities'] = Modality.objects.filter(arena=self.arena).order_by('name')
        return context


class EquipmentCreateView(ArenaOwnerRequiredMixin, CreateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = 'backoffice/config/equipment_form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['arena'] = self.arena
        return kwargs

    def form_valid(self, form):
        form.instance.arena = self.arena
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Equipamento '{self.object.name}' cadastrado com sucesso!"
            })
        messages.success(self.request, f"Equipamento '{self.object.name}' cadastrado com sucesso!")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(e) for e in error_list]
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('backoffice:equipment_list', kwargs={'arena_slug': self.arena.slug})


class EquipmentUpdateView(ArenaOwnerRequiredMixin, UpdateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = 'backoffice/config/equipment_form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        return context

    def get_queryset(self):
        return Equipment.objects.filter(arena=self.arena)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['arena'] = self.arena
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Equipamento '{self.object.name}' atualizado com sucesso!"
            })
        messages.success(self.request, f"Equipamento '{self.object.name}' atualizado com sucesso!")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(e) for e in error_list]
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('backoffice:equipment_list', kwargs={'arena_slug': self.arena.slug})


class EquipmentDeleteView(ArenaOwnerRequiredMixin, DeleteView):
    model = Equipment
    template_name = 'backoffice/config/equipment_confirm_delete.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        return context

    def get_queryset(self):
        return Equipment.objects.filter(arena=self.arena)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        name = self.object.name
        self.object.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Equipamento '{name}' excluído com sucesso!"
            })
        messages.success(request, f"Equipamento '{name}' removido com sucesso.")
        return redirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('backoffice:equipment_list', kwargs={'arena_slug': self.arena.slug})



# --- 4. HORÁRIOS DE FUNCIONAMENTO (NOVO) ---

class OpeningHoursListView(ArenaOwnerRequiredMixin, ListView):
    model = ArenaOpeningHour
    template_name = 'backoffice/config/opening_hours_list.html'
    context_object_name = 'hours'

    def _ensure_opening_hours(self):
        """Garante que existam registros de horários para os 7 dias da semana (0 a 6)."""
        existing_days = set(ArenaOpeningHour.objects.filter(arena=self.arena).values_list('weekday', flat=True))
        for day in range(7):
            if day not in existing_days:
                is_closed = (day == 6)
                open_t = None if is_closed else "07:00"
                close_t = None if is_closed else "23:00"
                ArenaOpeningHour.objects.create(
                    arena=self.arena,
                    weekday=day,
                    open_time=open_t,
                    close_time=close_t,
                    is_closed=is_closed
                )

    def get_queryset(self):
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])
        self._ensure_opening_hours()
        return ArenaOpeningHour.objects.filter(arena=self.arena).order_by('weekday')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        return context


class OpeningHourCreateView(ArenaOwnerRequiredMixin, CreateView):
    model = ArenaOpeningHour
    form_class = ArenaOpeningHourForm
    template_name = 'backoffice/config/opening_hour_form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['arena'] = self.arena
        return kwargs

    def form_valid(self, form):
        form.instance.arena = self.arena
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Horário de {self.object.get_weekday_display()} configurado com sucesso!"
            })
        messages.success(self.request, "Horário configurado!")
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(e) for e in error_list]
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('backoffice:opening_hours_list', kwargs={'arena_slug': self.arena.slug})


class OpeningHourUpdateView(ArenaOwnerRequiredMixin, UpdateView):
    model = ArenaOpeningHour
    form_class = ArenaOpeningHourForm
    template_name = 'backoffice/config/opening_hour_form.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        return context

    def get_queryset(self):
        return ArenaOpeningHour.objects.filter(arena=self.arena)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['arena'] = self.arena
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Horário de {self.object.get_weekday_display()} atualizado com sucesso!",
                'hour': {
                    'id': self.object.id,
                    'weekday': self.object.weekday,
                    'weekday_display': self.object.get_weekday_display(),
                    'open_time': self.object.open_time.strftime('%H:%M') if self.object.open_time else '',
                    'close_time': self.object.close_time.strftime('%H:%M') if self.object.close_time else '',
                    'is_closed': self.object.is_closed
                }
            })
        messages.success(self.request, "Horário atualizado!")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(e) for e in error_list]
            return JsonResponse({
                'success': False,
                'errors': errors
            }, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('backoffice:opening_hours_list', kwargs={'arena_slug': self.arena.slug})


class ReplicateMondayHoursView(ArenaOwnerRequiredMixin, View):
    """Copia o horário de Segunda-feira para todos os outros dias da semana (Terça a Domingo)."""
    def post(self, request, arena_slug):
        arena = get_object_or_404(Arena, slug=arena_slug)

        # Garante ou localiza Segunda-feira (weekday=0)
        monday = ArenaOpeningHour.objects.filter(arena=arena, weekday=0).first()
        if not monday:
            monday = ArenaOpeningHour.objects.create(
                arena=arena,
                weekday=0,
                open_time="07:00",
                close_time="23:00",
                is_closed=False
            )

        # Replicar para os demais dias (1 a 6: Terça a Domingo)
        for day in range(1, 7):
            hour_obj, _ = ArenaOpeningHour.objects.get_or_create(
                arena=arena,
                weekday=day,
                defaults={
                    'open_time': monday.open_time,
                    'close_time': monday.close_time,
                    'is_closed': monday.is_closed
                }
            )
            hour_obj.open_time = monday.open_time
            hour_obj.close_time = monday.close_time
            hour_obj.is_closed = monday.is_closed
            hour_obj.save()

        msg = "Horário de Segunda-feira replicado com sucesso para toda a semana!"
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': msg})

        messages.success(request, msg)
        return redirect('backoffice:opening_hours_list', arena_slug=arena.slug)


class OpeningHourDeleteView(ArenaOwnerRequiredMixin, DeleteView):
    model = ArenaOpeningHour
    template_name = 'backoffice/config/opening_hour_confirm_delete.html'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        return context

    def get_queryset(self):
        return ArenaOpeningHour.objects.filter(arena=self.arena)

    def get_success_url(self):
        messages.success(self.request, "Horário removido.")
        return reverse('backoffice:opening_hours_list', kwargs={'arena_slug': self.arena.slug})


# --- 5. ASAAS / FINANCEIRO ---
from apps.backoffice.api_services.asaas_api import create_asaas_subaccount

class AsaasConfigUpdateView(ArenaOwnerRequiredMixin, UpdateView):
    model = AsaasConfig
    form_class = AsaasConfigForm
    template_name = 'backoffice/config/asaas_config_form.html'

    def get_object(self, queryset=None):
        arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])
        config, created = AsaasConfig.objects.get_or_create(arena=arena)
        return config

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.object.arena
        return context

    def form_valid(self, form):
        # Salva o formulário localmente primeiro
        config = form.save(commit=False)
        
        # Só tenta criar a conta se ela ainda não tem wallet_id
        if not config.wallet_id:
            success, response_data = create_asaas_subaccount(self.object.arena, config, self.request.user)
            
            if success:
                config.wallet_id = response_data.get('walletId')
                config.api_key = response_data.get('apiKey')
                config.is_active = True
                messages.success(self.request, "Subconta criada com sucesso no Asaas!")
            else:
                # Tratar erros retornados pelo Asaas
                error_msgs = ", ".join([e.get('description', '') for e in response_data])
                messages.error(self.request, f"Erro ao criar Subconta: {error_msgs}")
                return self.form_invalid(form)
                
        config.save()
        
        if config.wallet_id:
            messages.success(self.request, "Configurações financeiras salvas com sucesso!")
            
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('backoffice:asaas_config', kwargs={'arena_slug': self.object.arena.slug})