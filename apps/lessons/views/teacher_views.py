from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.backoffice.mixins import ArenaOwnerRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from apps.lessons.models import Teacher
from apps.backoffice.models import Arena
from apps.lessons.forms.teacher_forms import TeacherForm

class TeacherListView(ArenaOwnerRequiredMixin, ListView):
    model = Teacher
    template_name = 'lessons/teachers/teacher_list.html'
    context_object_name = 'teachers'

    def get_queryset(self):
        # Filtra professores apenas desta arena
        return Teacher.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = Arena.objects.get(slug=self.kwargs['arena_slug'])
        return context

class TeacherCreateView(ArenaOwnerRequiredMixin, CreateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'lessons/teachers/teacher_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = Arena.objects.get(slug=self.kwargs['arena_slug'])
        context['titulo'] = "Novo Professor"
        return context

    def form_valid(self, form):
        # Vincula o professor à arena automaticamente
        arena = Arena.objects.get(slug=self.kwargs['arena_slug'])
        form.instance.arena = arena
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Professor "{self.object.name}" cadastrado com sucesso!',
                'teacher': {
                    'id': self.object.id,
                    'name': self.object.name,
                    'phone': self.object.phone,
                    'email': self.object.email or '',
                    'color': self.object.color,
                }
            })
        messages.success(self.request, f'Professor "{self.object.name}" cadastrado com sucesso!')
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
        return reverse_lazy('lessons:teacher_list', kwargs={'arena_slug': self.kwargs['arena_slug']})

class TeacherUpdateView(ArenaOwnerRequiredMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'lessons/teachers/teacher_form.html'

    def get_queryset(self):
        return Teacher.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = Arena.objects.get(slug=self.kwargs['arena_slug'])
        context['titulo'] = f"Editar {self.object.name}"
        return context

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Professor "{self.object.name}" atualizado com sucesso!',
                'teacher': {
                    'id': self.object.id,
                    'name': self.object.name,
                    'phone': self.object.phone,
                    'email': self.object.email or '',
                    'color': self.object.color,
                }
            })
        messages.success(self.request, f'Professor "{self.object.name}" atualizado com sucesso!')
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
        return reverse_lazy('lessons:teacher_list', kwargs={'arena_slug': self.kwargs['arena_slug']})

class TeacherDeleteView(ArenaOwnerRequiredMixin, DeleteView):
    model = Teacher
    template_name = 'lessons/teachers/teacher_confirm_delete.html'

    def get_queryset(self):
        return Teacher.objects.filter(arena__slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = Arena.objects.get(slug=self.kwargs['arena_slug'])
        return context

    def form_valid(self, form):
        self.object = self.get_object()
        name = self.object.name
        self.object.delete()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Professor "{name}" excluído com sucesso!'
            })
        messages.success(self.request, f'Professor "{name}" excluído com sucesso!')
        return redirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        return self.form_valid(None)

    def get_success_url(self):
        return reverse_lazy('lessons:teacher_list', kwargs={'arena_slug': self.kwargs['arena_slug']})