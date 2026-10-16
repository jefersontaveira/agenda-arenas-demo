from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.urls import reverse_lazy
from django.db import transaction
from django.http import JsonResponse
from django.contrib import messages
from apps.backoffice.mixins import ArenaOwnerRequiredMixin
from django.views.generic import ListView

from apps.lessons.models import ClassGroup, ClassSchedule
from apps.lessons.forms.classes import ClassGroupForm, ClassScheduleFormSet
from apps.backoffice.models import Arena


class ClassGroupCreateView(ArenaOwnerRequiredMixin, CreateView):
    model = ClassGroup
    form_class = ClassGroupForm
    template_name = 'lessons/classes/class_form.html'

    def get_success_url(self):
        # Redireciona para o dashboard após salvar
        return reverse_lazy('lessons:aulas', kwargs={'arena_slug': self.kwargs['arena_slug']})

    def get_form_kwargs(self):
        # Passa o slug da arena para o formulário filtrar os campos
        kwargs = super().get_form_kwargs()
        kwargs['arena_slug'] = self.kwargs['arena_slug']
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['arena'] = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])
        if self.request.POST:
            data['schedules'] = ClassScheduleFormSet(self.request.POST)
        else:
            data['schedules'] = ClassScheduleFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        schedules = context['schedules']

        with transaction.atomic():
            # 1. Configura a Arena antes de salvar
            arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])
            form.instance.arena = arena

            # 2. Salva a Turma (Pai)
            self.object = form.save()

            # 3. Salva os Horários (Filhos)
            if schedules.is_valid():
                schedules.instance = self.object
                schedules.save()
            else:
                if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    sched_errors = []
                    for err in schedules.errors:
                        if err:
                            sched_errors.append(str(err))
                    if schedules.non_form_errors():
                        sched_errors.extend([str(e) for e in schedules.non_form_errors()])
                    msg = " ".join(sched_errors) if sched_errors else "Erro nos horários informados."
                    return JsonResponse({
                        'success': False,
                        'message': msg
                    }, status=400)
                # Se os horários estiverem errados, volta para o form
                return self.render_to_response(self.get_context_data(form=form))

        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Turma "{self.object.name}" criada com sucesso!',
                'class_group': {
                    'id': self.object.id,
                    'name': self.object.name
                }
            })
        messages.success(self.request, f'Turma "{self.object.name}" criada com sucesso!')
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


class ClassGroupUpdateView(ArenaOwnerRequiredMixin, UpdateView):
    model = ClassGroup
    form_class = ClassGroupForm
    template_name = 'lessons/classes/class_form.html'  # Reutilizamos o mesmo template
    context_object_name = 'turma'

    def get_queryset(self):
        # SEGURANÇA: Garante que o usuário só pode editar turmas DESTA arena
        return ClassGroup.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_success_url(self):
        # Redireciona de volta para a grade completa após salvar
        return reverse_lazy('lessons:grade_completa', kwargs={'arena_slug': self.kwargs['arena_slug']})

    def get_form_kwargs(self):
        # Passa o slug da arena para o formulário filtrar os campos (Professores/Quadras)
        kwargs = super().get_form_kwargs()
        kwargs['arena_slug'] = self.kwargs['arena_slug']
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['arena'] = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])

        if self.request.POST:
            # Se for POST, preenche com os dados enviados
            data['schedules'] = ClassScheduleFormSet(self.request.POST, instance=self.object)
        else:
            # Se for GET, preenche com os dados do BANCO (instance=self.object)
            data['schedules'] = ClassScheduleFormSet(instance=self.object)

        # Variável para mudar o título do botão/página no template
        data['titulo_pagina'] = f"Editar Turma: {self.object.name}"
        data['texto_botao'] = "Salvar Alterações"

        return data

    def form_valid(self, form):
        context = self.get_context_data()
        schedules = context['schedules']

        with transaction.atomic():
            # 1. Salva as alterações da Turma (Pai)
            self.object = form.save()

            # 2. Salva/Atualiza/Deleta os Horários (Filhos)
            if schedules.is_valid():
                schedules.instance = self.object
                schedules.save()
            else:
                return self.render_to_response(self.get_context_data(form=form))

        return super().form_valid(form)


class ClassGroupDeleteView(ArenaOwnerRequiredMixin, DeleteView):
    model = ClassGroup
    template_name = 'lessons/classes/class_confirm_delete.html'
    context_object_name = 'turma'

    def get_queryset(self):
        # SEGURANÇA: Garante que o usuário só exclua turmas DESTA arena
        # Isso impede que alguém mude o ID na URL para apagar turma de outro dono
        return ClassGroup.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_success_url(self):
        # Após excluir, volta para a lista geral (Grade Completa)
        return reverse_lazy('lessons:grade_completa', kwargs={'arena_slug': self.kwargs['arena_slug']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Passamos a arena para o template (para o botão voltar)
        context['arena'] = self.object.arena
        return context

    def form_valid(self, form):
        self.object = self.get_object()
        name = self.object.name
        self.object.delete()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Turma "{name}" excluída com sucesso!'
            })
        messages.success(self.request, f'Turma "{name}" excluída com sucesso!')
        return redirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        return self.form_valid(None)


class ClassScheduleListView(ArenaOwnerRequiredMixin, ListView):
    model = ClassSchedule
    template_name = 'lessons/classes/grade_lista.html'
    context_object_name = 'schedules'

    def dispatch(self, request, *args, **kwargs):
        # Captura a arena para usar no filtro e no contexto
        self.arena = get_object_or_404(Arena, slug=self.kwargs.get('arena_slug'))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return ClassSchedule.objects.filter(
            class_group__is_active=True,
            class_group__arena=self.arena
        ).select_related(
            'class_group',
            'class_group__teacher',
            'class_group__court'
        ).order_by('day_of_week', 'start_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        context['teachers'] = self.arena.teachers.all()
        context['courts'] = self.arena.courts.filter(is_active=True)
        return context


class ClassGroupDetailView(ArenaOwnerRequiredMixin, DetailView):
    model = ClassGroup
    template_name = 'lessons/classes/class_detail.html'
    context_object_name = 'turma'

    def get_queryset(self):
        # SEGURANÇA: Garante que o usuário só veja turmas DESTA arena
        return ClassGroup.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])
        context['arena'] = arena
        
        # Variáveis necessárias para os modais (Nova Turma, Nova Matrícula)
        context['teachers'] = arena.teachers.all()
        context['courts'] = arena.courts.filter(is_active=True)
        context['classes'] = arena.classes.filter(is_active=True)
        context['customers'] = arena.customers.all().order_by('name')
        
        return context