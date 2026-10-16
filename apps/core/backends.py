from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError

User = get_user_model()

from django.db.models import Q

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username:
            return None
            
        identifier = username.strip()
        cache_key = f"failed_login_{identifier.lower()}"
        attempts = cache.get(cache_key, 0)
        
        # Permite login tanto por e-mail quanto por nome de usuário
        user = User.objects.filter(
            Q(email__iexact=identifier) | Q(username__iexact=identifier)
        ).order_by('id').first()
            
        if attempts >= 5 and identifier.lower() not in ['gestor.demo@arenaexemplo.com', 'demo_gestor', 'admin']:
            if user and user.is_active:
                # O admin reativou o usuário manualmente no banco
                cache.delete(cache_key)
                attempts = 0
            else:
                raise ValidationError("Sua conta foi bloqueada por excesso de tentativas falhas. Entre em contato com o suporte.")
            
        if user and not user.is_active:
            raise ValidationError("Sua conta foi bloqueada. Entre em contato com o suporte.")

        if user and user.check_password(password) and self.user_can_authenticate(user):
            cache.delete(cache_key)
            return user
        else:
            # Não bloqueia os usuários de demonstração do portfólio
            if identifier.lower() in ['gestor.demo@arenaexemplo.com', 'demo_gestor', 'admin']:
                return None
            attempts += 1
            # Bloqueio de 1 hora
            cache.set(cache_key, attempts, timeout=3600)
            
            remaining = 5 - attempts
            if remaining == 0:
                if user:
                    user.is_active = False
                    user.save()
                raise ValidationError("Sua conta foi bloqueada por excesso de tentativas falhas.")
            elif remaining <= 2:
                raise ValidationError(f"E-mail ou senha incorretos. Você tem apenas mais {remaining} tentativa(s) antes do bloqueio.")
            else:
                raise ValidationError("E-mail ou senha incorretos.")
