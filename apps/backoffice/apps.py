from django.apps import AppConfig

class BackofficeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.backoffice'
    verbose_name = 'Gestão da Arena'

    def ready(self):
        # Importa os sinais quando o app estiver pronto para rodar
        import apps.backoffice.signals
