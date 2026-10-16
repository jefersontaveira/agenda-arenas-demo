from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.backoffice.mixins import ArenaOwnerRequiredMixin
from django.db.models import Q
from apps.lessons.models import Enrollment
from apps.backoffice.models import Arena


class StudentListView(ArenaOwnerRequiredMixin, ListView):
    model = Enrollment
    template_name = 'lessons/enrollments/student_list.html'
    context_object_name = 'matriculas'
    paginate_by = 20

    def get_queryset(self):
        arena_slug = self.kwargs['arena_slug']
        queryset = Enrollment.objects.filter(
            class_group__arena__slug=arena_slug
        ).select_related('customer', 'class_group').order_by('customer__name')

        # Lógica de Busca (Opcional, mas muito útil)
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(customer__name__icontains=q) |
                Q(class_group__name__icontains=q)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        arena = Arena.objects.get(slug=self.kwargs['arena_slug'])
        context['arena'] = arena
        context['classes'] = arena.classes.filter(is_active=True)
        context['customers'] = arena.customers.all().order_by('name')
        return context


class StudentDetailView(ArenaOwnerRequiredMixin, DetailView):
    model = Enrollment
    template_name = 'lessons/enrollments/student_detail.html'
    context_object_name = 'matricula'

    def get_queryset(self):
        arena_slug = self.kwargs['arena_slug']
        return Enrollment.objects.filter(
            class_group__arena__slug=arena_slug
        ).select_related('customer', 'class_group')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['arena'] = Arena.objects.get(slug=self.kwargs['arena_slug'])
        context['fees'] = self.object.fees.all().order_by('-reference_date', '-due_date')
        return context


from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

class EnrollmentStatusUpdateView(ArenaOwnerRequiredMixin, View):
    def post(self, request, arena_slug, pk):
        enrollment = get_object_or_404(Enrollment, pk=pk, class_group__arena__slug=arena_slug)
        status = request.POST.get('status')
        if status in dict(Enrollment.STATUS).keys():
            enrollment.status = status
            enrollment.save()
            messages.success(request, f"Status da matrícula alterado para {enrollment.get_status_display()}.")
        else:
            messages.error(request, "Status inválido.")
        return redirect('lessons:student_detail', arena_slug=arena_slug, pk=pk)