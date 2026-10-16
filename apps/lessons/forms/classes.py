from django import forms
from django.forms import inlineformset_factory
from apps.lessons.models import ClassGroup, ClassSchedule, Teacher
from apps.backoffice.models import Court


class ClassGroupForm(forms.ModelForm):
    class Meta:
        model = ClassGroup
        fields = ['name', 'teacher', 'court', 'description', 'max_students', 'monthly_price', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        # Recebemos a 'arena' para filtrar apenas profs e quadras DAQUELA arena
        arena_slug = kwargs.pop('arena_slug', None)
        super().__init__(*args, **kwargs)

        # Adiciona classes Bootstrap
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'
        self.fields['is_active'].widget.attrs['class'] = 'form-check-input'

        self.fields['teacher'].required = False
        self.fields['court'].required = False

        if arena_slug:
            self.fields['teacher'].queryset = Teacher.objects.filter(arena__slug=arena_slug)
            self.fields['court'].queryset = Court.objects.filter(arena__slug=arena_slug)


class ClassScheduleForm(forms.ModelForm):
    class Meta:
        model = ClassSchedule
        fields = ['day_of_week', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'


# Criamos um "Conjunto de Formulários" que vincula ClassGroup a ClassSchedule
ClassScheduleFormSet = inlineformset_factory(
    ClassGroup,
    ClassSchedule,
    form=ClassScheduleForm,
    extra=1,  # Começa exibindo 1 linha vazia
    can_delete=True  # Permite excluir um dia
)