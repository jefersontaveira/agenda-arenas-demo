
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from apps.core import views as core_views

urlpatterns = [
    # Recomenda-se usar uma URL difícil de adivinhar para maior segurança
    path('own/', admin.site.urls),

    # Rota da Landing Page (Raiz do site)
    path('', core_views.home, name='home'),

    # --- SISTEMA DE LOGIN ---
    path('accounts/login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),

    # URLs do Backoffice
    path('gestao/', include('apps.backoffice.urls')),

    # URLs das Aulas
    path('', include('apps.lessons.urls')),

    # URLs do Cliente (Scheduler)
    path('app/', include('apps.scheduler.urls')),

    # URLs do Saas (Saas)
    path('saas/', include('apps.saas.urls')),

    # --- ROTAS DE SANDBOX DEMO (PORTFOLIO) ---
    path('demo/entrar/', core_views.demo_autologin_view, name='demo_autologin'),
    path('demo/reset/', core_views.demo_reset_database_view, name='demo_reset'),
    path('demo/status/', core_views.demo_status_view, name='demo_status'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
