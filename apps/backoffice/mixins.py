from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from apps.saas.models import Arena


class ArenaOwnerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin que garante que:
    1. Usuário está logado.
    2. Usuário é dono da arena especificada na URL (slug).
    """

    def test_func(self):
        # Pega o slug da URL
        slug = self.kwargs.get('arena_slug')
        if not slug:
            return True  # Deixa passar se a view não tem slug (ex: roteador)

        # Pega a arena do banco
        arena = get_object_or_404(Arena, slug=slug)

        # O usuário logado é dono/gestor dessa arena?
        # Verifica se o usuário logado está na lista de usuários da arena
        return self.request.user in arena.users.all()