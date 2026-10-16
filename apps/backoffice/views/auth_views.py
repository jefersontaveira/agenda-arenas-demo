from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages


class ArenaRouterView(LoginRequiredMixin, View):
    def get(self, request):

        user_arenas = request.user.arenas.all()

        if user_arenas.exists():
            # Pega a primeira arena encontrada
            arena = user_arenas.first()

            if arena.slug:
                return redirect('backoffice:dashboard', arena_slug=arena.slug)
            else:
                messages.error(request, "A arena vinculada não possui URL (Slug) configurada.")
                return redirect('login')
        else:
            # Usuário logou mas não tem nenhuma arena
            messages.error(request, "Seu usuário não possui arenas vinculadas.")
            return redirect('login')