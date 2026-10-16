from django.views.generic import TemplateView
from django.utils import timezone
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from apps.backoffice.mixins import ArenaOwnerRequiredMixin

from apps.backoffice.models import Arena
from apps.lessons.models import ClassSchedule, Enrollment, MonthlyFee


class LessonsDashboardView(ArenaOwnerRequiredMixin, TemplateView):
    template_name = 'lessons/dashboard/dashboard_lessons.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        arena_slug = self.kwargs['arena_slug']
        arena = get_object_or_404(Arena, slug=arena_slug)

        hoje = timezone.now().date()
        dia_da_semana = hoje.weekday()

        # Vamos tentar buscar SEM filtro de dia primeiro para ver se existe ALGO
        total_schedules = ClassSchedule.objects.filter(class_group__arena=arena).count()
        print(f"Total de horários cadastrados nesta arena (qualquer dia): {total_schedules}")

        # Agora a busca oficial
        aulas_hoje = ClassSchedule.objects.filter(
            class_group__arena=arena,
            class_group__is_active=True,
            day_of_week=dia_da_semana
        ).select_related('class_group').order_by('start_time')

        # 3. KPIs (Indicadores) - Mantive simples para não dar erro se não tiver dados
        total_alunos = Enrollment.objects.filter(class_group__arena=arena, status='ACTIVE').count()
        aulas_experimentais = Enrollment.objects.filter(class_group__arena=arena, status='TRIAL').count()
        inadimplentes = MonthlyFee.objects.filter(enrollment__class_group__arena=arena, status='OVERDUE').count()

        # Receita (Soma tudo que foi pago no mês atual)
        receita = MonthlyFee.objects.filter(
            enrollment__class_group__arena=arena,
            status='PAID',
            paid_at__month=hoje.month,
            paid_at__year=hoje.year
        ).aggregate(Sum('value'))['value__sum'] or 0

        # 4. Envia tudo para o HTML
        context['arena'] = arena
        context['hoje'] = hoje
        context['aulas_hoje'] = aulas_hoje  # Aqui está a lista que preenche a tabela!

        context['kpis'] = {
            'alunos_ativos': total_alunos,
            'experimentais': aulas_experimentais,
            'inadimplentes': inadimplentes,
            'receita_realizada': receita,
            'receita_prevista': 0  # Podemos calcular depois
        }

        # Listas para alimentar os modais de Nova Turma e Nova Matrícula
        context['teachers'] = arena.teachers.all()
        context['courts'] = arena.courts.filter(is_active=True)
        context['classes'] = arena.classes.filter(is_active=True)
        context['customers'] = arena.customers.all().order_by('name')

        return context