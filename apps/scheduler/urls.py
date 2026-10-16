from django.urls import path
from apps.scheduler.views.home.home_views import (
    ArenaPublicView, MyAppointmentsView, my_bookings_ajax, save_customer_profile_ajax
)
from apps.scheduler.views.booking_views import PublicBookingAction, BookingSuccessView
from apps.scheduler.views.payments.payment_views import checkout_view, check_payment_status
from apps.scheduler.views.payments.webhook_views import asaas_webhook

app_name = 'scheduler'

urlpatterns = [
    # Tela Principal
    path('<slug:arena_slug>/', ArenaPublicView.as_view(), name='arena_home'),

    # Ações
    path('<slug:arena_slug>/confirmar/', PublicBookingAction.as_view(), name='booking_action'),
    path('<slug:arena_slug>/sucesso/<int:booking_id>/', BookingSuccessView.as_view(), name='booking_success'),

    # Página Dedicada e API: Meus Agendamentos do Atleta
    path('<slug:arena_slug>/meus-agendamentos/', MyAppointmentsView.as_view(), name='my_bookings'),
    path('<slug:arena_slug>/api/meus-agendamentos/', my_bookings_ajax, name='my_bookings_ajax'),
    path('<slug:arena_slug>/salvar-perfil/', save_customer_profile_ajax, name='save_customer_profile_ajax'),

    # Rota de Pagamento (Onde mostra o QR Code)
    path('pagamento/<int:booking_id>/', checkout_view, name='checkout'),
    path('pagamento/<int:booking_id>/status/', check_payment_status, name='check_payment_status'),
    path('webhook/asaas/', asaas_webhook, name='asaas_webhook'),
]