from django import forms
from apps.lessons.models import Teacher

class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['name', 'phone', 'email', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Professor'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(XX) 9XXXX-XXXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
            # O type='color' cria um seletor visual de cores
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color', 'title': 'Escolha a cor'}),
        }