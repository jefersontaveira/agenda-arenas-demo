from django import forms
from apps.backoffice.models import Booking

class AdminBookingForm(forms.ModelForm):
    # --- CAMPOS MANUAIS (Para criar/editar o cliente na hora) ---
    customer_phone = forms.CharField(
        label="Telefone do Cliente",
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '(XX) 9XXXX-XXXX',
            'data-mask': 'phone' # Ajuda se você usar um plugin de máscara JS
        })
    )

    customer_name = forms.CharField(
        label="Nome do Cliente",
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome completo'
        })
    )

    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control cpf-mask',
            'placeholder': '000.000.000-00'
        })
    )

    # --- NOTA IMPORTANTE ---
    # Removemos 'wants_racket' e 'wants_ball' daqui.
    # Agora o template gera checkboxes dinâmicos baseado no banco de dados (Equipment)
    # e a View captura isso via request.POST.getlist('equipment_ids').

    class Meta:
        model = Booking
        # Apenas os campos essenciais que o Form precisa validar/salvar do modelo Booking
        fields = ['start_time', 'end_time']
        widgets = {
            'start_time': forms.HiddenInput(),
            'end_time': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        # Removemos 'arena' do kwargs antes de chamar o super,
        # pois o ModelForm padrão do Django não espera esse argumento.
        self.arena = kwargs.pop('arena', None)
        super().__init__(*args, **kwargs)