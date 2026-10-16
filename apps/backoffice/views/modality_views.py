from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse

from apps.backoffice.mixins import ArenaOwnerRequiredMixin
from apps.saas.models import Arena
from apps.backoffice.models import Modality
from apps.backoffice.forms.modality_forms import ModalityForm


class ModalityListView(ArenaOwnerRequiredMixin, View):
    """Redireciona para a tela unificada de quadras e modalidades"""
    def get(self, request, arena_slug):
        return redirect('backoffice:court_list', arena_slug=arena_slug)


class ModalityCreateView(ArenaOwnerRequiredMixin, CreateView):
    model = Modality
    form_class = ModalityForm
    template_name = 'backoffice/modalities/modality_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])
        context['is_editing'] = False
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.arena = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])
        
        # Validar unique_together manualmente para retornar erro amigável se necessário
        if Modality.objects.filter(arena=self.object.arena, name__iexact=self.object.name).exists():
            form.add_error('name', 'Já existe uma modalidade com este nome nesta arena.')
            return self.form_invalid(form)
            
        self.object.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Modalidade '{self.object.name}' cadastrada com sucesso!",
                'modality': {
                    'id': self.object.id,
                    'name': self.object.name,
                    'emoji': self.object.emoji,
                }
            })
        messages.success(self.request, f"Modalidade '{self.object.name}' cadastrada com sucesso!")
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


class ModalityUpdateView(ArenaOwnerRequiredMixin, UpdateView):
    model = Modality
    form_class = ModalityForm
    template_name = 'backoffice/modalities/modality_form.html'
    context_object_name = 'modality'

    def get_queryset(self):
        return Modality.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])
        context['is_editing'] = True
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        
        # Validar unique_together manualmente
        if Modality.objects.filter(arena=self.object.arena, name__iexact=self.object.name).exclude(pk=self.object.pk).exists():
            form.add_error('name', 'Já existe uma modalidade com este nome nesta arena.')
            return self.form_invalid(form)
            
        self.object.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Modalidade '{self.object.name}' atualizada com sucesso!",
                'modality': {
                    'id': self.object.id,
                    'name': self.object.name,
                    'emoji': self.object.emoji,
                }
            })
        messages.success(self.request, f"Modalidade '{self.object.name}' atualizada com sucesso!")
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


class ModalityDeleteView(ArenaOwnerRequiredMixin, DeleteView):
    model = Modality
    template_name = 'backoffice/modalities/modality_confirm_delete.html'
    context_object_name = 'modality'

    def get_queryset(self):
        return Modality.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = get_object_or_404(Arena, slug=self.kwargs['arena_slug'])
        context['linked_courts'] = self.object.courts.filter(arena=context['arena'])
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        modality_name = self.object.name
        self.object.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f"Modalidade '{modality_name}' removida com sucesso!"
            })
        messages.success(request, f"Modalidade '{modality_name}' removida com sucesso!")
        return redirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('backoffice:court_list', kwargs={'arena_slug': self.kwargs['arena_slug']})