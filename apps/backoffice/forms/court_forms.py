from django import forms
from apps.backoffice.models import Court, Modality


class CourtForm(forms.ModelForm):
    class Meta:
        model = Court
        fields = ['name', 'price', 'modalities', 'color', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Quadra de Areia 1'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1.00'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control form-control-color',
                'type': 'color',  # Isso cria o seletor de cor nativo
                'title': 'Escolha a cor da quadra'
            }),
            'modalities': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'style': 'height: 120px;'  # Força altura para ver a lista
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch'
            }),
        }

    def __init__(self, *args, **kwargs):
        arena = kwargs.pop('arena', None)
        super().__init__(*args, **kwargs)
        # Garante que as modalidades apareçam
        if arena:
            self.fields['modalities'].queryset = Modality.objects.for_arena(arena)
        else:
            self.fields['modalities'].queryset = Modality.objects.none()

        if arena and hasattr(arena, 'config'):
            default_price = arena.config.default_price
            self.fields['price'].help_text = f"Se deixar R$ 0,00, será usado o Preço Padrão da arena (R$ {default_price})."
        else:
            self.fields['price'].help_text = "Se deixar R$ 0,00, será usado o Preço Padrão da arena."