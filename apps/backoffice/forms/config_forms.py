from django import forms
from apps.backoffice.models import ArenaConfig, PriceRule, Equipment, ArenaOpeningHour, Court, AsaasConfig, Modality, DayOfWeek


# --- 1. REGRAS DE PREÇO ---
class PriceRuleForm(forms.ModelForm):
    DAYS_CHOICES = [
        ('0', 'Segunda'), ('1', 'Terça'), ('2', 'Quarta'),
        ('3', 'Quinta'), ('4', 'Sexta'), ('5', 'Sábado'), ('6', 'Domingo'),
    ]

    days = forms.MultipleChoiceField(
        choices=DAYS_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label="Dias da Semana",
        required=True
    )

    class Meta:
        model = PriceRule
        fields = ['name', 'court', 'price', 'start_time', 'end_time', 'days']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Horário Nobre, Fim de Semana...'}),
            'court': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.50', 'min': '0'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.arena = kwargs.pop('arena', None)
        super().__init__(*args, **kwargs)

        arena = self.arena or getattr(self.instance, 'arena', None)
        if arena:
            self.fields['court'].queryset = Court.objects.filter(arena=arena).order_by('name')
        else:
            self.fields['court'].queryset = Court.objects.none()

        self.fields['court'].required = False
        self.fields['court'].empty_label = "Todas as Quadras da Arena"

        # Preenche os checkboxes se estiver editando
        if self.instance and self.instance.pk:
            self.initial['days'] = [str(d.number) for d in self.instance.days.all()]

    def clean_days(self):
        days_list = self.cleaned_data.get('days')
        if not days_list:
            raise forms.ValidationError("Selecione pelo menos um dia da semana.")
        day_objects = []
        for d in days_list:
            day_obj, _ = DayOfWeek.objects.get_or_create(number=int(d))
            day_objects.append(day_obj)
        return day_objects

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time and start_time >= end_time:
            self.add_error('end_time', "O horário de término deve ser posterior ao horário de início.")

        return cleaned_data


# --- 2. CONFIGURAÇÃO GERAL ---
class ArenaConfigForm(forms.ModelForm):
    class Meta:
        model = ArenaConfig
        fields = ['default_price', 'slot_duration', 'payment_policy']
        widgets = {
            'default_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'slot_duration': forms.NumberInput(attrs={'class': 'form-control', 'step': '5'}),
            'payment_policy': forms.RadioSelect(attrs={'class': 'btn-check'}),
        }


# --- 2.1. PERSONALIZAÇÃO DO SITE DA ARENA ---
class SiteCustomizeForm(forms.ModelForm):
    class Meta:
        model = ArenaConfig
        fields = [
            'logo', 'primary_color', 'secondary_color',
            'hero_image', 'hero_title', 'hero_subtitle',
            'contact_phone', 'instagram', 'address', 'about_text'
        ]
        widgets = {
            'logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color w-100', 'style': 'height: 42px;'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color w-100', 'style': 'height: 42px;'}),
            'hero_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'hero_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Agende já sua quadra'}),
            'hero_subtitle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Escolha sua modalidade e garanta seu horário.'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: (11) 99999-9999'}),
            'instagram': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: @suaarena'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Rua do Esporte, 100 - Centro'}),
            'about_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Conte um pouco sobre sua arena, vestiários, bar, estacionamento...'}),
        }


# --- 3. EQUIPAMENTOS ---
class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['name', 'total_quantity', 'rental_price', 'modalities', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Bola de Futevôlei, Raquete...'}),
            'total_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'rental_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.50', 'min': '0'}),
            'modalities': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

    def __init__(self, *args, **kwargs):
        self.arena = kwargs.pop('arena', None)
        super().__init__(*args, **kwargs)
        self.fields['modalities'].required = False
        arena = self.arena or getattr(self.instance, 'arena', None)
        if arena:
            self.fields['modalities'].queryset = Modality.objects.filter(arena=arena).order_by('name')
        else:
            self.fields['modalities'].queryset = Modality.objects.none()


# --- 4. HORÁRIOS ---
class ArenaOpeningHourForm(forms.ModelForm):
    class Meta:
        model = ArenaOpeningHour
        fields = ['weekday', 'open_time', 'close_time', 'is_closed']
        widgets = {
            'weekday': forms.Select(attrs={'class': 'form-select'}),
            'open_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'close_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'is_closed': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

    def __init__(self, *args, **kwargs):
        self.arena = kwargs.pop('arena', None)
        super().__init__(*args, **kwargs)
        if self.arena and not getattr(self.instance, 'arena_id', None):
            self.instance.arena = self.arena

    def clean(self):
        cleaned_data = super().clean()
        weekday = cleaned_data.get('weekday')
        arena = self.arena or getattr(self.instance, 'arena', None)
        if arena is not None and weekday is not None:
            existing = ArenaOpeningHour.objects.filter(arena=arena, weekday=weekday)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                self.add_error('weekday', "Já existe um horário configurado para este dia da semana nesta arena.")
        return cleaned_data


# --- 5. ASAAS (FINANCEIRO) ---
class AsaasConfigForm(forms.ModelForm):
    class Meta:
        model = AsaasConfig
        fields = [
            'cpf_cnpj', 'company_type', 'birth_date', 'company_email', 
            'bank_code', 'agency', 'account', 'account_digit', 'bank_account_type'
        ]
        widgets = {
            'cpf_cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CPF ou CNPJ'}),
            'company_type': forms.Select(choices=[
                ('MEI', 'MEI'), ('LIMITED', 'LTDA'), ('INDIVIDUAL', 'Individual'), ('ASSOCIATION', 'Associação'),
                ('PF', 'Pessoa Física')
            ], attrs={'class': 'form-select'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'company_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email para acesso à subconta'}),
            'bank_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código do Banco (ex: 001)'}),
            'agency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Agência sem dígito'}),
            'account': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Conta'}),
            'account_digit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dígito'}),
            'bank_account_type': forms.Select(choices=[
                ('CONTA_CORRENTE', 'Conta Corrente'),
                ('CONTA_POUPANCA', 'Conta Poupança')
            ], attrs={'class': 'form-select'}),
        }