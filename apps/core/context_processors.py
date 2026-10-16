# apps/core/context_processors.py
from apps.saas.models import Arena


def user_arenas_context(request):
    # Se o usuário não está logado, não retorna nada
    if not request.user.is_authenticated:
        return {}

    # Busca todas as arenas onde o campo 'user' é o usuário logado
    # values('name', 'slug') deixa a consulta mais leve, trazendo só o necessário pro menu
    my_arenas = Arena.objects.filter(users=request.user, is_active=True).values('name', 'slug')

    return {
        'my_arenas': my_arenas
    }