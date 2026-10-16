from django import forms
from apps.backoffice.models import Customer
import re

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'cpf', 'birth_date', 'observation']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(XX) 9XXXX-XXXX', 'data-mask': 'phone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00', 'data-mask': 'cpf'}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'observation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_phone(self):
        """Remove formatação do telefone (salva apenas números)"""
        phone = self.cleaned_data.get('phone')
        if phone:
            return re.sub(r'\D', '', phone)  # Remove tudo que não for dígito
        return phone

    def clean_cpf(self):
        """Remove formatação do CPF (salva apenas números)"""
        cpf = self.cleaned_data.get('cpf')
        if cpf:
            return re.sub(r'\D', '', cpf)
        return cpf