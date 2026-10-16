from django.contrib import admin
from .models import (
    ArenaConfig, Modality, Court, Booking, Customer, 
    PriceRule, Equipment, BookingEquipment, ArenaOpeningHour, AsaasConfig
)


# --- INLINES (Tabelas dentro de outras tabelas) ---
class BookingEquipmentInline(admin.TabularInline):
    """
    Mostra os equipamentos alugados dentro da tela da Reserva.
    Substitui os antigos checkboxes 'wants_ball'.
    """
    model = BookingEquipment
    extra = 0  # Não mostra linhas vazias extras
    readonly_fields = ['price_snapshot']  # Protege o histórico de preço


# --- ADMINS PRINCIPAIS ---

@admin.register(Modality)
class ModalityAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'emoji')


@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ('name', 'arena', 'price', 'is_active')
    list_filter = ('arena', 'is_active')
    filter_horizontal = ('modalities',)  # Mantido: Interface melhor para selecionar várias modalidades


@admin.register(ArenaConfig)
class ArenaConfigAdmin(admin.ModelAdmin):
    list_display = ('arena', 'default_price', 'slot_duration', 'payment_policy')
    search_fields = ('arena__name',)

    fieldsets = (
        ("Configurações Gerais", {
            "fields": ("arena", "logo", "primary_color", "secondary_color", "default_price", "slot_duration", "payment_policy")
        }),
    )


@admin.register(AsaasConfig)
class AsaasConfigAdmin(admin.ModelAdmin):
    list_display = ('arena', 'wallet_id', 'is_active')
    search_fields = ('arena__name', 'cpf_cnpj')



@admin.register(ArenaOpeningHour)
class ArenaOpeningHourAdmin(admin.ModelAdmin):
    # NOVO: Para gerenciar os horários complexos (virada de noite)
    list_display = ('arena', 'get_weekday_display', 'open_time', 'close_time', 'is_closed')
    list_filter = ('arena', 'weekday', 'is_closed')
    ordering = ('arena', 'weekday')


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    # NOVO: Controle de estoque (Bolas, Raquetes, Nadadeiras...)
    list_display = ('name', 'arena', 'total_quantity', 'rental_price', 'is_active')
    list_filter = ('arena', 'is_active')
    filter_horizontal = ('modalities',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    # ATUALIZADO: Removemos 'wants_ball'. Adicionamos 'price' e 'payment_status'.
    list_display = ('id', 'arena', 'get_customer_name', 'court', 'start_time', 'price', 'status', 'payment_status')

    # Filtros laterais
    list_filter = ('arena', 'status', 'payment_status', 'start_time', 'court')

    # Campo de busca (Mantido sua lógica de buscar por nome e telefone)
    search_fields = ('customer__name', 'customer__phone', 'id')

    # Adiciona a tabelinha de equipamentos dentro da reserva
    inlines = [BookingEquipmentInline]

    # Função para mostrar o nome bonito na tabela
    @admin.display(description='Cliente')
    def get_customer_name(self, obj):
        return obj.customer.name


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'arena', 'total_bookings', 'is_blocked')
    list_filter = ('arena', 'is_blocked')
    search_fields = ['name', 'phone', 'cpf', 'email']


@admin.register(PriceRule)
class PriceRuleAdmin(admin.ModelAdmin):
    # ATUALIZADO: Usamos 'get_days_display_custom' que já criamos no Model
    list_display = ('name', 'arena', 'court', 'price', 'start_time', 'end_time', 'get_days_display_custom')
    list_filter = ('arena', 'court')
    search_fields = ('name', 'arena__name')
    ordering = ('arena', 'start_time')