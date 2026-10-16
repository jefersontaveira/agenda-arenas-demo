# apps/saas/urls.py
from django.urls import path
from . import views

app_name = 'saas'

urlpatterns = [
    # Dashboard Master Principal
    path('', views.MasterDashboardView.as_view(), name='dashboard'),
    
    # Detalhes e Gestão de Arenas
    path('arenas/nova/', views.ArenaMasterCreateView.as_view(), name='arena_create'),
    path('arenas/<int:pk>/', views.ArenaMasterDetailView.as_view(), name='arena_detail'),
    path('arenas/<int:pk>/editar/', views.ArenaMasterUpdateView.as_view(), name='arena_edit'),
    path('arenas/<int:pk>/toggle-active/', views.toggle_arena_active, name='arena_toggle_active'),
    
    # Mensalidades do SaaS
    path('mensalidades/', views.SubscriptionMasterListView.as_view(), name='subscription_list'),
    path('mensalidades/nova/', views.SubscriptionCreateView.as_view(), name='subscription_create'),
    path('mensalidades/<int:pk>/editar/', views.SubscriptionUpdateView.as_view(), name='subscription_edit'),
    path('mensalidades/<int:pk>/pagar/', views.mark_subscription_paid, name='subscription_mark_paid'),
    path('mensalidades/gerar-lote/', views.generate_monthly_subscriptions, name='subscription_generate_batch'),
]