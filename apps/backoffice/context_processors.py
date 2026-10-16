def arena_context(request):
    """
    Injeta a variável 'arena' em todos os templates se o usuário for dono de uma.
    """
    if request.user.is_authenticated and hasattr(request.user, 'arena'):
        return {'arena': request.user.arena}
    return {}