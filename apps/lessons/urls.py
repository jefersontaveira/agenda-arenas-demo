from django.urls import path

from apps.lessons.views.dashboard_views import LessonsDashboardView
from apps.lessons.views.enrollment_views import (
    EnrollmentCreateView,
    EnrollmentDeleteView,
    EnrollmentUpdateView)
from apps.lessons.views.student_views import StudentListView, StudentDetailView, EnrollmentStatusUpdateView
from apps.lessons.views.teacher_views import (
    TeacherListView,
    TeacherCreateView,
    TeacherUpdateView,
    TeacherDeleteView
)
from apps.lessons.views.class_views import (
    ClassGroupCreateView,
    ClassScheduleListView,
    ClassGroupUpdateView,
    ClassGroupDeleteView,
    ClassGroupDetailView
)

from apps.lessons.views.financial_views import (
    FinancialListView,
    FinancialDetailView,
    FeeStatusUpdateView,
    FeeUpdateView,
    FeePayView,
    FeeUndoPayView,
    GenerateMonthlyFeesView,
    FeeCreateView
)

app_name = 'lessons'

urlpatterns = [
    # Aulas
    path('gestao/<slug:arena_slug>/aulas/', LessonsDashboardView.as_view(), name='aulas'),

    # Turmas
    path('gestao/<slug:arena_slug>/turmas/nova/', ClassGroupCreateView.as_view(), name='class_create'),
    path('gestao/<slug:arena_slug>/aulas/turma/<int:pk>/', ClassGroupDetailView.as_view(), name='class_detail'),
    path('gestao/<slug:arena_slug>/aulas/turma/<int:pk>/editar/', ClassGroupUpdateView.as_view(), name='class_update'),
    path('gestao/<slug:arena_slug>/aulas/grade-completa/', ClassScheduleListView.as_view(), name='grade_completa'),
    path('gestao/<slug:arena_slug>/aulas/turma/<int:pk>/excluir/', ClassGroupDeleteView.as_view(), name='class_delete'),

    # Alunos
    path('matricula/nova/<slug:arena_slug>/', EnrollmentCreateView.as_view(), name='enrollment_create'),
    path('matricula/excluir/<slug:arena_slug>/<int:pk>/', EnrollmentDeleteView.as_view(), name='enrollment_delete'),
    path('gestao/<slug:arena_slug>/alunos/', StudentListView.as_view(), name='student_list'),
    path('gestao/<slug:arena_slug>/alunos/<int:pk>/', StudentDetailView.as_view(), name='student_detail'),
    path('gestao/<slug:arena_slug>/alunos/<int:pk>/status/', EnrollmentStatusUpdateView.as_view(), name='enrollment_status_update'),
    path('matricula/editar/<slug:arena_slug>/<int:pk>/', EnrollmentUpdateView.as_view(), name='enrollment_update'),

    # PROFESSORES
    path('gestao/<slug:arena_slug>/professores/', TeacherListView.as_view(), name='teacher_list'),
    path('gestao/<slug:arena_slug>/professores/novo/', TeacherCreateView.as_view(), name='teacher_create'),
    path('gestao/<slug:arena_slug>/professores/<int:pk>/editar/', TeacherUpdateView.as_view(), name='teacher_update'),
    path('gestao/<slug:arena_slug>/professores/<int:pk>/excluir/', TeacherDeleteView.as_view(), name='teacher_delete'),

    # --- FINANCEIRO ---
    path('gestao/<slug:arena_slug>/financeiro/', FinancialListView.as_view(), name='financial_list'),
    path('gestao/<slug:arena_slug>/financeiro/nova-cobranca/', FeeCreateView.as_view(), name='fee_create'),
    path('gestao/<slug:arena_slug>/financeiro/gerar-cobrancas/', GenerateMonthlyFeesView.as_view(), name='generate_fees'),
    path('gestao/<slug:arena_slug>/financeiro/<int:pk>/', FinancialDetailView.as_view(), name='financial_detail'),
    path('gestao/<slug:arena_slug>/financeiro/<int:pk>/status/', FeeStatusUpdateView.as_view(), name='fee_status_update'),
    path('gestao/<slug:arena_slug>/financeiro/<int:pk>/editar/', FeeUpdateView.as_view(), name='fee_update'),
    path('gestao/<slug:arena_slug>/financeiro/<int:pk>/pagar/', FeePayView.as_view(), name='fee_pay'),
    path('gestao/<slug:arena_slug>/financeiro/<int:pk>/estornar/', FeeUndoPayView.as_view(), name='fee_undo_pay'),
]

