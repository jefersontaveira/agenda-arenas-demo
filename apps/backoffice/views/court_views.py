from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import JsonResponse
from apps.backoffice.mixins import ArenaOwnerRequiredMixin

from django.db.models import Count
from apps.saas.models import Arena
from apps.backoffice.models import Court, Modality
from apps.backoffice.forms.court_forms import CourtForm


class CourtListView(ArenaOwnerRequiredMixin, ListView):
    model = Court
    template_name = 'backoffice/courts/court_list.html'
    context_object_name = 'courts'

    def get_queryset(self):
        # FILTRO DE SEGURANÇA: Só traz quadras da arena que está na URL
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])
        return Court.objects.filter(arena=self.arena).order_by('name')

    def get_context_data(self, **kwargs):
        # Envia a variável 'arena' para o HTML poder usar o nome dela
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        context['all_modalities'] = Modality.objects.for_arena(self.arena).annotate(court_count=Count('courts')).order_by('name')
        if hasattr(self.arena, 'config'):
            context['default_price'] = self.arena.config.default_price
        else:
            context['default_price'] = 0

        return context


class CourtCreateView(ArenaOwnerRequiredMixin, CreateView):
    model = Court
    form_class = CourtForm
    template_name = 'backoffice/courts/court_form.html'

    def dispatch(self, request, *args, **kwargs):
        # Captura a arena antes de qualquer coisa
        self.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['arena'] = self.arena
        return kwargs

    def form_valid(self, form):
        # O Pulo do Gato: Antes de salvar, avisamos que essa quadra pertence a essa Arena
        form.instance.arena = self.arena
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Quadra criada com sucesso!',
                'court': {
                    'id': self.object.id,
                    'name': self.object.name,
                }
            })
        messages.success(self.request, "Quadra criada com sucesso!")
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.arena
        return context

    def get_success_url(self):
        return reverse('backoffice:court_list', kwargs={'arena_slug': self.arena.slug})


class CourtUpdateView(ArenaOwnerRequiredMixin, UpdateView):
    model = Court
    form_class = CourtForm
    template_name = 'backoffice/courts/court_form.html'
    context_object_name = 'court'

    def get_queryset(self):
        # SEGURANÇA: Só permite editar se a quadra pertencer à arena da URL
        return Court.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.object.arena
        context['is_editing'] = True
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['arena'] = self.object.arena
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Quadra atualizada com sucesso!',
                'court': {
                    'id': self.object.id,
                    'name': self.object.name,
                }
            })
        messages.success(self.request, "Quadra atualizada!")
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
        return reverse('backoffice:court_list', kwargs={'arena_slug': self.kwargs['arena_slug']})


class CourtDeleteView(ArenaOwnerRequiredMixin, DeleteView):
    model = Court
    template_name = 'backoffice/courts/court_confirm_delete.html'
    context_object_name = 'court'

    def get_queryset(self):
        # SEGURANÇA: Só permite excluir se a quadra for desta arena
        return Court.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = self.object.arena
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        court_name = self.object.name
        self.object.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Quadra '{court_name}' removida com sucesso!"
            })
        messages.success(request, f"Quadra '{court_name}' removida.")
        return redirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('backoffice:court_list', kwargs={'arena_slug': self.kwargs['arena_slug']})