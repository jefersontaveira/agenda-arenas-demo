from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.backoffice.mixins import ArenaOwnerRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from apps.lessons.models import Enrollment
from apps.backoffice.models import Arena
from apps.lessons.forms.enrollment_forms import EnrollmentForm


class EnrollmentCreateView(ArenaOwnerRequiredMixin, CreateView):
    model = Enrollment
    form_class = EnrollmentForm
    template_name = 'lessons/enrollments/enrollment_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        arena = Arena.objects.get(slug=self.kwargs['arena_slug'])
        kwargs['arena'] = arena
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = Arena.objects.get(slug=self.kwargs['arena_slug'])
        return context

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Matrícula de "{self.object.customer.name}" realizada com sucesso!',
                'enrollment': {
                    'id': self.object.id,
                    'customer_name': self.object.customer.name,
                    'class_name': self.object.class_group.name,
                }
            })
        messages.success(self.request, f'Matrícula de "{self.object.customer.name}" realizada com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(e) for e in error_list]
            non_field = form.non_field_errors()
            msg = " ".join([str(e) for e in non_field]) if non_field else "Verifique os dados preenchidos."
            return JsonResponse({
                'success': False,
                'errors': errors,
                'message': msg
            }, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('lessons:student_list', kwargs={'arena_slug': self.kwargs['arena_slug']})


class EnrollmentUpdateView(ArenaOwnerRequiredMixin, UpdateView):
    model = Enrollment
    form_class = EnrollmentForm
    template_name = 'lessons/enrollments/enrollment_form.html'

    def get_queryset(self):
        return Enrollment.objects.filter(class_group__arena__slug=self.kwargs['arena_slug'])

    def get_form_kwargs(self):
        """Passa a arena para o formulário filtrar os campos corretamente"""
        kwargs = super().get_form_kwargs()
        arena = Arena.objects.get(slug=self.kwargs['arena_slug'])
        kwargs['arena'] = arena
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = Arena.objects.get(slug=self.kwargs['arena_slug'])
        context['titulo'] = 'Editar Matrícula'
        return context

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Matrícula de "{self.object.customer.name}" atualizada com sucesso!',
                'enrollment': {
                    'id': self.object.id,
                    'customer_name': self.object.customer.name,
                    'class_name': self.object.class_group.name,
                }
            })
        messages.success(self.request, f'Matrícula de "{self.object.customer.name}" atualizada com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(e) for e in error_list]
            non_field = form.non_field_errors()
            msg = " ".join([str(e) for e in non_field]) if non_field else "Verifique os dados preenchidos."
            return JsonResponse({
                'success': False,
                'errors': errors,
                'message': msg
            }, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('lessons:student_list', kwargs={'arena_slug': self.kwargs['arena_slug']})


class EnrollmentDeleteView(ArenaOwnerRequiredMixin, DeleteView):
    model = Enrollment
    template_name = 'lessons/enrollments/enrollment_confirm_delete.html'

    def get_queryset(self):
        return Enrollment.objects.filter(class_group__arena__slug=self.kwargs['arena_slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = Arena.objects.get(slug=self.kwargs['arena_slug'])
        return context

    def form_valid(self, form):
        self.object = self.get_object()
        name = self.object.customer.name
        class_name = self.object.class_group.name
        self.object.delete()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Matrícula de "{name}" na turma "{class_name}" excluída com sucesso!'
            })
        messages.success(self.request, f'Matrícula de "{name}" na turma "{class_name}" excluída com sucesso!')
        return redirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        return self.form_valid(None)

    def get_success_url(self):
        return reverse_lazy('lessons:student_list', kwargs={'arena_slug': self.kwargs['arena_slug']})