from django.core.management.base import BaseCommand
from apps.lessons.services import generate_monthly_fees_routine


class Command(BaseCommand):
    help = 'Gera faturas mensais automaticamente para alunos ativos 7 dias antes do vencimento.'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando rotina de geração de faturas mensais...")
        created_count, details = generate_monthly_fees_routine(mode='default', days_threshold=7)
        for item in details:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Fatura gerada: {item['customer_name']} - Vencimento: {item['due_date'].strftime('%d/%m/%Y')} (R$ {item['value']})"
                )
            )
        self.stdout.write(self.style.SUCCESS(f'Rotina finalizada. {created_count} fatura(s) gerada(s).'))

