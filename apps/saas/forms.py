from datetime import date
from calendar import monthrange
from django import forms
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Arena, Subscription
from apps.backoffice.models import ArenaConfig

User = get_user_model()


class ArenaMasterForm(forms.ModelForm):
    # --- Dados Operacionais / ArenaConfig ---
    address = forms.CharField(
        label="Endereço da Arena",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Av. das Américas, 1500 - Barra da Tijuca, RJ'
        })
    )
    contact_phone = forms.CharField(
        label="Telefone Comercial da Arena",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: (21) 3333-4444'
        })
    )
    slot_duration = forms.IntegerField(
        label="Duração do Slot (minutos)",
        required=False,
        initial=60,
        min_value=15,
        max_value=360,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '5'
        }),
        help_text="Duração padrão de cada horário reservado (ex: 60 ou 90 min)."
    )
    default_price = forms.DecimalField(
        label="Preço Base por Hora (R$)",
        required=False,
        initial=0.00,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.50'
        }),
        help_text="Valor padrão da hora para reservas na arena."
    )

    # --- Acesso ao Sistema & Usuários ---
    create_owner_user = forms.BooleanField(
        label="Criar/Vincular conta de acesso para o proprietário",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    owner_password = forms.CharField(
        label="Senha Inicial de Acesso",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Defina a senha (ou deixe vazio para gerar automático: Arena@2025)'
        }),
        help_text="O login será feito utilizando o e-mail do proprietário."
    )
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all().order_by('username'),
        required=False,
        label="Usuários com Acesso à Gestão",
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': '4'
        }),
        help_text="Usuários do sistema vinculados à arena. Segure Ctrl para selecionar múltiplos."
    )

    # --- Faturamento Inicial ---
    generate_first_invoice = forms.BooleanField(
        label="Gerar primeira fatura de mensalidade deste mês",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Arena
        fields = [
            'name', 'slug', 'owner_name', 'owner_phone', 'owner_email',
            'cnpj', 'monthly_fee', 'due_day', 'is_active', 'users'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Arena Beach Point', 'id': 'id_arena_name'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: arena-beach-point', 'id': 'id_arena_slug'}),
            'owner_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo do proprietário/gestor'}),
            'owner_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(XX) 9XXXX-XXXX'}),
            'owner_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'dono@arena.com', 'id': 'id_owner_email'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'monthly_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'due_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 31}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created_user_account = None
        self.user_password_used = None
        self.first_invoice_created = None

        if self.instance and self.instance.pk:
            # Em modo de edição de arena existente
            self.fields['create_owner_user'].initial = False
            self.fields['generate_first_invoice'].initial = False

            if hasattr(self.instance, 'config'):
                cfg = self.instance.config
                self.fields['address'].initial = cfg.address
                self.fields['contact_phone'].initial = cfg.contact_phone
                self.fields['slot_duration'].initial = cfg.slot_duration
                self.fields['default_price'].initial = cfg.default_price

            if self.instance.users.exists():
                self.fields['users'].initial = self.instance.users.all()

    def clean_slug(self):
        slug = self.cleaned_data.get('slug', '').strip()
        name = self.cleaned_data.get('name', '').strip()
        if not slug and name:
            slug = slugify(name)
        else:
            slug = slugify(slug)

        if not slug:
            raise ValidationError("O campo slug é obrigatório.")

        # Verificar unicidade
        qs = Arena.objects.filter(slug=slug)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError(f"O slug '{slug}' já está em uso por outra arena. Escolha outro.")

        return slug

    def save(self, commit=True):
        arena = super().save(commit=commit)
        if commit:
            self._save_extra_data(arena)
        else:
            old_save_m2m = self.save_m2m
            def new_save_m2m():
                old_save_m2m()
                self._save_extra_data(arena)
            self.save_m2m = new_save_m2m
        return arena

    def _save_extra_data(self, arena):
        # 1. Atualizar ou Criar ArenaConfig
        config, _ = ArenaConfig.objects.get_or_create(arena=arena)
        address = self.cleaned_data.get('address')
        contact_phone = self.cleaned_data.get('contact_phone')
        slot_duration = self.cleaned_data.get('slot_duration')
        default_price = self.cleaned_data.get('default_price')

        if address is not None:
            config.address = address
        if contact_phone is not None:
            config.contact_phone = contact_phone
        if slot_duration is not None:
            config.slot_duration = slot_duration
        if default_price is not None:
            config.default_price = default_price
        config.save()
        arena.config = config

        # 2. Criar ou Vincular Usuário de Acesso para o Proprietário
        create_user = self.cleaned_data.get('create_owner_user')
        owner_email = (self.cleaned_data.get('owner_email') or '').strip().lower()
        owner_name = (self.cleaned_data.get('owner_name') or '').strip()
        custom_password = (self.cleaned_data.get('owner_password') or '').strip()

        if create_user and owner_email:
            user = User.objects.filter(email__iexact=owner_email).first()
            if not user:
                base_username = slugify(owner_email.split('@')[0]).replace('-', '_') or f"user_{arena.slug}"
                username = base_username
                c = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{c}"
                    c += 1

                if not custom_password:
                    custom_password = f"Arena@{timezone.now().year}"

                first_name = owner_name.split()[0] if owner_name else ""
                last_name = " ".join(owner_name.split()[1:]) if len(owner_name.split()) > 1 else ""

                user = User.objects.create_user(
                    username=username,
                    email=owner_email,
                    password=custom_password,
                    first_name=first_name,
                    last_name=last_name
                )
                self.created_user_account = user
                self.user_password_used = custom_password
            else:
                if custom_password:
                    user.set_password(custom_password)
                    user.save()
                    self.user_password_used = custom_password
                self.created_user_account = user

            arena.users.add(user)

        # 3. Gerar Fatura Inicial do Mês se solicitado
        generate_invoice = self.cleaned_data.get('generate_first_invoice')
        if generate_invoice and arena.monthly_fee and arena.monthly_fee > 0:
            today = timezone.localdate()
            month = today.month
            year = today.year

            exists = Subscription.objects.filter(
                arena=arena,
                due_date__year=year,
                due_date__month=month
            ).exists()

            if not exists:
                max_day = monthrange(year, month)[1]
                due_day = min(arena.due_day or 10, max_day)
                due_date = date(year, month, due_day)

                sub = Subscription.objects.create(
                    arena=arena,
                    due_date=due_date,
                    amount=arena.monthly_fee,
                    status='PENDING',
                    notes=f"Primeira fatura de adesão - Ref. {month:02d}/{year}"
                )
                self.first_invoice_created = sub



class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['arena', 'due_date', 'amount', 'status', 'payment_date', 'notes']
        widgets = {
            'arena': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ex: Pago via PIX'}),
        }


class GenerateSubscriptionsForm(forms.Form):
    month = forms.IntegerField(
        label="Mês de Referência",
        min_value=1,
        max_value=12,
        initial=timezone.now().month,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    year = forms.IntegerField(
        label="Ano",
        min_value=2024,
        max_value=2035,
        initial=timezone.now().year,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
