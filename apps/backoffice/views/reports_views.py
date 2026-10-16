from datetime import date, timedelta
import json

from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncDate
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.backoffice.mixins import ArenaOwnerRequiredMixin

from apps.backoffice.models import Booking, BookingEquipment, Customer
from apps.saas.models import Arena
from apps.lessons.models import ClassGroup


class ArenaReportView(ArenaOwnerRequiredMixin, TemplateView):
    template_name = 'backoffice/reports/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        arena = Arena.objects.get(slug=self.kwargs['arena_slug'])
        context['arena'] = arena

        # --- 1. FILTRO DE DATA ---
        today = date.today()
        default_start = today.replace(day=1)
        next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
        default_end = next_month - timedelta(days=1)

        start_date_str = self.request.GET.get('start_date', str(default_start))
        end_date_str = self.request.GET.get('end_date', str(default_end))

        context['start_date'] = start_date_str
        context['end_date'] = end_date_str

        # --- QUERYSETS DE RESERVAS ---
        bookings = Booking.objects.filter(
            arena=arena,
            start_time__date__gte=start_date_str,
            end_time__date__lte=end_date_str
        )

        valid_bookings = bookings.filter(status__in=['CONFIRMED', 'PENDING'])
        cancelled_bookings = bookings.filter(status='CANCELED')

        # --- 2. KPI FINANCEIROS (TOTAIS) ---

        # A. Receita de Quadras
        total_court_revenue = valid_bookings.aggregate(total=Sum('price'))['total'] or 0

        # B. Receita de Equipamentos
        total_equipment_revenue = BookingEquipment.objects.filter(
            booking__in=valid_bookings
        ).aggregate(total=Sum(F('quantity') * F('price_snapshot')))['total'] or 0

        # C. Receita de Aulas (MRR)
        active_classes = ClassGroup.objects.filter(arena=arena, is_active=True)
        total_class_revenue = 0
        class_performance = []

        for group in active_classes:
            # Filtra matrículas ativas
            active_enrollments = group.enrollments.filter(status='ACTIVE')
            student_count = active_enrollments.count()

            # Soma valor acordado
            group_revenue = active_enrollments.aggregate(total=Sum('agreed_price'))['total'] or 0

            total_class_revenue += group_revenue

            class_performance.append({
                'name': group.name,
                'students': student_count,
                'revenue': group_revenue,
                'teacher': group.teacher.name if group.teacher else 'Sem professor'
            })

        # Totais para o Contexto
        context['financial'] = {
            'courts': total_court_revenue,
            'equipment': total_equipment_revenue,
            'classes': total_class_revenue,
            'grand_total': total_court_revenue + total_equipment_revenue + total_class_revenue
        }
        context['class_mrr'] = total_class_revenue

        # --- 3. OPERACIONAL ---
        total_count = bookings.count()
        valid_count = valid_bookings.count()
        cancel_count = cancelled_bookings.count()

        # Calcula taxas
        cancel_rate = (cancel_count / total_count * 100) if total_count > 0 else 0
        completion_rate = 100 - cancel_rate  # <--- CÁLCULO FEITO AQUI AGORA

        popular_court = valid_bookings.values('court__name') \
            .annotate(count=Count('id')).order_by('-count').first()

        context['operational'] = {
            'total_bookings': valid_count,
            'cancel_count': cancel_count,
            'cancel_rate': round(cancel_rate, 1),
            'completion_rate': round(completion_rate, 1),  # <--- ENVIANDO PRO TEMPLATE
            'popular_court': popular_court['court__name'] if popular_court else "Nenhuma"
        }

        # --- 4. TOP 5 CLIENTES ---
        top_customers = valid_bookings.values('customer__name', 'customer__phone') \
                            .annotate(bookings_count=Count('id'), total_spent=Sum('price')) \
                            .order_by('-bookings_count')[:5]
        context['top_customers'] = top_customers

        # --- 5. DETALHE EQUIPAMENTOS ---
        equipment_stats = BookingEquipment.objects.filter(booking__in=valid_bookings) \
            .values('equipment__name') \
            .annotate(qty_rented=Sum('quantity'), income=Sum(F('quantity') * F('price_snapshot'))) \
            .order_by('-income')
        context['equipment_stats'] = equipment_stats

        context['class_performance'] = sorted(class_performance, key=lambda x: x['revenue'], reverse=True)

        # =================================================================
        # --- 6. DADOS PARA GRÁFICOS (CHART.JS) - ADICIONADO AQUI ---
        # =================================================================

        # A. Gráfico de Linha: Receita Diária (Locações)
        # Agrupa as reservas por dia (TruncDate) e soma o preço
        daily_revenue_data = valid_bookings.annotate(date=TruncDate('start_time')) \
            .values('date') \
            .annotate(daily_total=Sum('price')) \
            .order_by('date')

        # Prepara listas simples para o JavaScript
        dates_labels = [item['date'].strftime('%d/%m') for item in daily_revenue_data]
        # Converter Decimal para Float para o JSON funcionar
        revenues_data = [float(item['daily_total']) for item in daily_revenue_data]

        # B. Gráfico de Rosca: Fontes de Receita
        revenue_sources = {
            'Locações': float(total_court_revenue),
            'Aulas (Mensal)': float(total_class_revenue),
            'Equipamentos': float(total_equipment_revenue)
        }

        # Serializa para JSON (String) para o Template ler com segurança
        context['chart_dates'] = json.dumps(dates_labels)
        context['chart_revenues'] = json.dumps(revenues_data)
        context['chart_sources_labels'] = json.dumps(list(revenue_sources.keys()))
        context['chart_sources_data'] = json.dumps(list(revenue_sources.values()))

        return context