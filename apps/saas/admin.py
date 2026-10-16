# apps/saas/admin.py
from django.contrib import admin
from .models import Arena, Subscription

@admin.register(Arena)
class ArenaAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'owner_name', 'owner_phone', 'monthly_fee', 'due_day', 'is_active', 'created_at')
    search_fields = ('name', 'owner_name', 'owner_phone', 'owner_email', 'slug')
    list_filter = ('is_active',)
    filter_horizontal = ('users',)
    prepopulated_fields = {'slug': ('name',)} # Preenche o slug automaticamente ao digitar o nome

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('arena', 'status', 'due_date', 'amount', 'payment_date')
    list_filter = ('status', 'due_date')
    search_fields = ('arena__name',)
