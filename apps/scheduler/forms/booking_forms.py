# apps/scheduler/forms/booking_forms.py
import re
from django import forms
from apps.backoffice.models import Booking


class PublicBookingForm(forms.ModelForm):
    # --- CAMPOS OCULTOS (Recebem dados via JavaScript do Slot clicado) ---
    court_id = forms.IntegerField(widget=forms.HiddenInput())
    date = forms.CharField(widget=forms.HiddenInput()) # Formato YYYY-MM-DD
    time = forms.CharField(widget=forms.HiddenInput()) # Formato HH:MM

    # --- CAMPOS VISUAIS ---
    customer_name = forms.CharField(
        label="Seu Nome",
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: João Silva'})
    )

    customer_phone = forms.CharField(
        label="Seu WhatsApp",
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(XX) 9XXXX-XXXX'})
    )

    customer_cpf = forms.CharField(
        label="Seu CPF",
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'})
    )

    customer_email = forms.EmailField(
        label="Seu Email (Opcional)",
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'})
    )

    wants_ball = forms.BooleanField(
        required=False,
        label="Alugar bola?",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'})
    )

    wants_racket = forms.BooleanField(
        required=False,
        label="Alugar raquete?",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'})
    )

    def clean_customer_cpf(self):
        """Valida e limpa o CPF para apenas números."""
        cpf = self.cleaned_data.get('customer_cpf')
        cpf_limpo = re.sub(r'\D', '', str(cpf))

        if len(cpf_limpo) != 11:
            raise forms.ValidationError("O CPF deve conter exatamente 11 números.")

        return cpf_limpo

    def clean_customer_phone(self):
        """Valida e limpa o telefone."""
        phone = self.cleaned_data.get('customer_phone')
        phone_limpo = re.sub(r'\D', '', str(phone))

        if not (10 <= len(phone_limpo) <= 11):
            raise forms.ValidationError("Telefone inválido. Use DDD + Número (ex: 85999998888).")

        return phone_limpo

    def clean_customer_name(self):
        """Garante que o nome não tenha espaços desnecessários e respeite o limite."""
        name = self.cleaned_data.get('customer_name')
        if name:
            name = name.strip()
        return name

    class Meta:
        model = Booking
        fields = [] # Continuamos sem fields automáticos, controlamos tudo manualmente na View