import shutil
from pathlib import Path
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db import connections

BASE_DIR = Path(settings.BASE_DIR)
SEED_DB = BASE_DIR / 'db_seed_clean.sqlite3'
ACTIVE_DB = BASE_DIR / 'db.sqlite3'


def ensure_active_database():
    """Garante que o banco ativo exista e esteja inicializado com o seed limpo."""
    try:
        if not ACTIVE_DB.exists() or ACTIVE_DB.stat().st_size == 0:
            if SEED_DB.exists():
                connections.close_all()
                shutil.copyfile(SEED_DB, ACTIVE_DB)
    except Exception as e:
        print(f"[WARN] Erro ao assegurar banco ativo: {e}")


def demo_autologin_view(request):
    """
    Realiza o login automatico do visitante como gestor da arena demonstrativa
    e redireciona diretamente para o painel de gestao da arena 'arena-demo'.
    Protegido pela flag DEMO_MODE.
    """
    if not getattr(settings, 'DEMO_MODE', True):
        return HttpResponseForbidden("Modo demonstração desativado neste ambiente de produção.")

    ensure_active_database()

    try:
        user = User.objects.get(username='demo_gestor')
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        request.session.save()
        return HttpResponseRedirect('/gestao/arena-demo/')
    except Exception:
        # Se o banco foi clonado sem o arquivo ativo, força a cópia do snapshot limpo e autentica
        try:
            if SEED_DB.exists():
                connections.close_all()
                shutil.copyfile(SEED_DB, ACTIVE_DB)
                user = User.objects.get(username='demo_gestor')
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                request.session.save()
                return HttpResponseRedirect('/gestao/arena-demo/')
        except Exception:
            pass
        return HttpResponseRedirect('/accounts/login/')


@csrf_exempt
def demo_reset_database_view(request):
    """
    Restaura o banco SQLite a partir do snapshot limpo 'db_seed_clean.sqlite3'.
    Protegido pela flag DEMO_MODE e restrito a requisições POST.
    """
    if not getattr(settings, 'DEMO_MODE', True):
        return JsonResponse({'status': 'error', 'message': 'Modo demonstração desativado neste ambiente.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método não permitido. Utilize POST.'}, status=405)

    # Verificação de token opcional se configurado
    demo_secret = getattr(settings, 'DEMO_SECRET_TOKEN', None)
    if demo_secret:
        received_token = request.headers.get('x-demo-token') or request.POST.get('token')
        if received_token != demo_secret:
            return JsonResponse({'status': 'error', 'message': 'Token de demonstração inválido.'}, status=401)

    try:
        if SEED_DB.exists():
            # Fecha conexões ativas com o SQLite antes de substituir o arquivo no Windows/Linux
            connections.close_all()
            shutil.copyfile(SEED_DB, ACTIVE_DB)
            return JsonResponse({
                'status': 'success',
                'message': 'Demonstração resetada com sucesso! O banco retornou ao estado original.'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Arquivo de template seed não encontrado.'
            }, status=500)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def demo_status_view(request):
    """
    Informa o status do sandbox e informacoes da arena de teste.
    """
    demo_enabled = getattr(settings, 'DEMO_MODE', True)
    return JsonResponse({
        'status': 'online',
        'demo_mode': demo_enabled,
        'arena': 'Arena Prime Beach & Sports',
        'slug': 'arena-demo',
        'role': 'demo_gestor',
        'time_limit_minutes': 20,
        'notice': 'Versão de testes interativa. Em breve disponível para arenas reais.' if demo_enabled else 'Ambiente de produção ativo.'
    })
