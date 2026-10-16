from django.urls import path
from apps.backoffice.views.court_views import (
    CourtListView,
    CourtCreateView,
    CourtUpdateView,
    CourtDeleteView,
)
from apps.backoffice.views.config_views import (
    ArenaConfigUpdateView,
    SiteCustomizeView,
    PriceRuleListView,
    PriceRuleCreateView,
    PriceRuleUpdateView,
    PriceRuleDeleteView,
    OpeningHoursListView, OpeningHourCreateView, OpeningHourUpdateView, OpeningHourDeleteView,
    ReplicateMondayHoursView,
    EquipmentListView, EquipmentCreateView, EquipmentUpdateView, EquipmentDeleteView,
    AsaasConfigUpdateView
)
from apps.backoffice.views.dashboard_views import DashboardView
from apps.backoffice.views.customer_views import (
    CustomerListView, CustomerCreateView, CustomerUpdateView, CustomerDeleteView,
    CustomerDetailView, get_customer_data, search_customers_ajax
)
from apps.backoffice.views.booking_views import (
    BookingCreateView,
    BookingUpdateView,
    BookingDeleteView,
    booking_bank_receipt
)

from apps.backoffice.views.modality_views import (
    ModalityListView,
    ModalityCreateView,
    ModalityUpdateView,
    ModalityDeleteView
)
from apps.backoffice.views.auth_views import ArenaRouterView
from apps.backoffice.views.reports_views import ArenaReportView

app_name = 'backoffice'

urlpatterns = [
    # Roteador
    path('roteador/', ArenaRouterView.as_view(), name='router'),

    # Clientes
    path('<slug:arena_slug>/clientes/', CustomerListView.as_view(), name='customer_list'),
    path('<slug:arena_slug>/clientes/novo/', CustomerCreateView.as_view(), name='customer_create'),
    path('<slug:arena_slug>/clientes/<int:pk>/', CustomerDetailView.as_view(), name='customer_detail'),
    path('<slug:arena_slug>/clientes/<int:pk>/editar/', CustomerUpdateView.as_view(), name='customer_edit'),
    path('<slug:arena_slug>/clientes/<int:pk>/excluir/', CustomerDeleteView.as_view(), name='customer_delete'),
    
    path('api/cliente/<int:customer_id>/', get_customer_data, name='api_customer_data'),
    path('<slug:arena_slug>/clientes/api/buscar/', search_customers_ajax, name='api_customer_search'),

    # --- RESERVAS (BOOKING) ---
    path('<slug:arena_slug>/', DashboardView.as_view(), name='dashboard'),

    # ADICIONADO: Rota genérica para "Nova Reserva"
    path('<slug:arena_slug>/reservar/nova/', BookingCreateView.as_view(), name='booking_add'),

    # Rota específica (clicando na grid)
    path('<slug:arena_slug>/reservar/<int:court_id>/', BookingCreateView.as_view(), name='booking_create'),

    path('<slug:arena_slug>/reserva/<int:pk>/editar/', BookingUpdateView.as_view(), name='booking_edit'),
    path('<slug:arena_slug>/reserva/<int:pk>/cancelar/', BookingDeleteView.as_view(), name='booking_delete'),
    path('<slug:arena_slug>/reserva/<int:pk>/comprovante/', booking_bank_receipt, name='booking_bank_receipt'),

    # Quadras
    path('<slug:arena_slug>/quadras/', CourtListView.as_view(), name='court_list'),
    path('<slug:arena_slug>/quadras/nova/', CourtCreateView.as_view(), name='court_create'),
    path('<slug:arena_slug>/quadras/<int:pk>/editar/', CourtUpdateView.as_view(), name='court_edit'),
    path('<slug:arena_slug>/quadras/<int:pk>/excluir/', CourtDeleteView.as_view(), name='court_delete'),

    # Personalizar Site Público da Arena
    path('<slug:arena_slug>/personalizar-site/', SiteCustomizeView.as_view(), name='site_customize'),

    # Configurações Gerais
    path('<slug:arena_slug>/configuracoes/', ArenaConfigUpdateView.as_view(), name='arena_config'),
    path('<slug:arena_slug>/configuracoes/financeiro/', AsaasConfigUpdateView.as_view(), name='asaas_config'),

    # Horários
    path('<slug:arena_slug>/horarios/', OpeningHoursListView.as_view(), name='opening_hours_list'),
    path('<slug:arena_slug>/horarios/novo/', OpeningHourCreateView.as_view(), name='opening_hour_add'),
    path('<slug:arena_slug>/horarios/<int:pk>/editar/', OpeningHourUpdateView.as_view(), name='opening_hour_edit'),
    path('<slug:arena_slug>/horarios/<int:pk>/remover/', OpeningHourDeleteView.as_view(), name='opening_hour_delete'),
    path('<slug:arena_slug>/horarios/replicar-segunda/', ReplicateMondayHoursView.as_view(), name='opening_hours_replicate_monday'),

    # Equipamentos
    path('<slug:arena_slug>/equipamentos/', EquipmentListView.as_view(), name='equipment_list'),
    path('<slug:arena_slug>/equipamentos/novo/', EquipmentCreateView.as_view(), name='equipment_add'),
    path('<slug:arena_slug>/equipamentos/<int:pk>/editar/', EquipmentUpdateView.as_view(), name='equipment_edit'),
    path('<slug:arena_slug>/equipamentos/<int:pk>/remover/', EquipmentDeleteView.as_view(), name='equipment_delete'),

    # Regras de Preço
    path('arena/<slug:arena_slug>/regras-preco/', PriceRuleListView.as_view(), name='price_rules'),
    path('arena/<slug:arena_slug>/regras-preco/nova/', PriceRuleCreateView.as_view(), name='price_rule_add'),
    path('arena/<slug:arena_slug>/regras-preco/<int:pk>/editar/', PriceRuleUpdateView.as_view(),
         name='price_rule_edit'),
    path('arena/<slug:arena_slug>/regras-preco/<int:pk>/deletar/', PriceRuleDeleteView.as_view(),
         name='price_rule_delete'),

    # Modalidades
    path('<slug:arena_slug>/modalidades/', ModalityListView.as_view(), name='modality_list'),
    path('<slug:arena_slug>/modalidades/nova/', ModalityCreateView.as_view(), name='modality_create'),
    path('<slug:arena_slug>/modalidades/<int:pk>/editar/', ModalityUpdateView.as_view(), name='modality_edit'),
    path('<slug:arena_slug>/modalidades/<int:pk>/excluir/', ModalityDeleteView.as_view(), name='modality_delete'),

    # Relatórios
    path('<slug:arena_slug>/relatorios/', ArenaReportView.as_view(), name='reports'),
]