from django import forms
from apps.backoffice.models import Modality


class ModalityForm(forms.ModelForm):
    class Meta:
        model = Modality
        fields = ['name', 'emoji', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Ex: Vôlei, Futevôlei, Beach Tennis, Futebol...',
                'autocomplete': 'off',
            }),
            'emoji': forms.TextInput(attrs={
                'class': 'form-control form-control-lg text-center',
                'placeholder': '🏐',
                'maxlength': '10',
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: bi-trophy (opcional)',
            }),
        }
        labels = {
            'name': 'Nome da Modalidade',
            'emoji': 'Emoji',
            'icon': 'Classe do Ícone (Opcional)',
        }
        help_texts = {
            'emoji': 'Selecione um dos esportes abaixo ou digite seu próprio emoji.',
        }
