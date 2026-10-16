from django import forms
from django.core.exceptions import ValidationError
from apps.lessons.models import Enrollment, ClassGroup, MonthlyFee
from apps.backoffice.models import Customer, Arena


class EnrollmentForm(forms.ModelForm):
    # --- Campos Extras (Espelho do Customer) ---
    new_student_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome Completo'})
    )
    new_student_phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(XX) 9XXXX-XXXX'})
    )
    # ADICIONADO: Campo de Email
    new_student_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'})
    )

    class Meta:
        model = Enrollment
        fields = ['customer', 'class_group', 'start_date', 'agreed_price', 'due_day', 'status']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'class_group': forms.Select(attrs={'class': 'form-select'}),
            'agreed_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'due_day': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.arena = kwargs.pop('arena', None)
        super().__init__(*args, **kwargs)

        if self.arena:
            self.fields['customer'].required = False
            self.fields['customer'].queryset = Customer.objects.filter(arena=self.arena)
            self.fields['class_group'].queryset = ClassGroup.objects.filter(arena=self.arena)

    def clean(self):
        cleaned_data = super().clean()
        customer = cleaned_data.get('customer')
        new_name = cleaned_data.get('new_student_name')
        new_phone = cleaned_data.get('new_student_phone')

        # Se não selecionou existente E não preencheu nome/telefone novos -> Erro
        if not customer and not (new_name and new_phone):
            raise ValidationError("Selecione um aluno ou preencha Nome e WhatsApp para criar um novo.")

        return cleaned_data

    def save(self, commit=True):
        # 1. Lógica do Cliente (que já fizemos)
        customer = self.cleaned_data.get('customer')
        new_name = self.cleaned_data.get('new_student_name')
        new_phone = self.cleaned_data.get('new_student_phone')
        new_email = self.cleaned_data.get('new_student_email')

        if customer:
            changed = False
            if new_email and customer.email != new_email:
                customer.email = new_email
                changed = True
            if changed:
                customer.save()
            self.instance.customer = customer
        elif new_name and new_phone:
            import re
            cleaned_phone = re.sub(r'\D', '', new_phone)
            customer = Customer.objects.filter(arena=self.arena, phone=cleaned_phone).first()
            if customer:
                if new_name and customer.name != new_name:
                    customer.name = new_name
                if new_email and customer.email != new_email:
                    customer.email = new_email
                customer.save()
            else:
                customer = Customer.objects.create(
                    arena=self.arena,
                    name=new_name,
                    phone=cleaned_phone,
                    email=new_email,
                    observation="Cadastrado via Matrícula"
                )
            self.instance.customer = customer

        # 2. Salva a Matrícula primeiro (para ter um ID)
        enrollment = super().save(commit=commit)

        # 3. Lógica FINANCEIRA (A Mágica acontece aqui)
        # Só cria se for uma NOVA matrícula (não edição) e se tiver sido salva no banco
        if commit and not self.instance.pk:
            # Infelizmente o super().save() já salva e define o PK, então precisamos de outra lógica para saber se é novo
            # Mas como o form save é chamado, vamos verificar se JÁ EXISTE cobrança para evitar duplicar
            pass

            # CORREÇÃO: A melhor forma de saber se é criação é checar se enrollment foi recém criado.
        # Vamos fazer uma verificação simples: Se não tem nenhuma MonthlyFee, cria a primeira.

        if commit and not enrollment.fees.exists():

            # Data de referência: Mês da data de início
            start_date = enrollment.start_date
            reference_date = start_date.replace(day=1)  # 01/MM/AAAA

            # Data de Vencimento: Usa o dia escolhido (due_day) no mês de início
            try:
                due_date = start_date.replace(day=enrollment.due_day)
            except ValueError:
                # Caso o dia seja 31 e o mês só tenha 30, joga pro último dia do mês
                # (Lógica simplificada, ideal é usar bibliotecas de data)
                import calendar
                last_day = calendar.monthrange(start_date.year, start_date.month)[1]
                due_date = start_date.replace(day=last_day)

            # Regra: Uma cobrança não pode iniciar atrasada
            # Se a data de vencimento calculada já passou, define para a data de hoje.
            from django.utils import timezone
            today = timezone.now().date()
            if due_date < today:
                due_date = today

            MonthlyFee.objects.create(
                enrollment=enrollment,
                reference_date=reference_date,
                due_date=due_date,
                value=enrollment.agreed_price,
                status='PENDING'
            )

        return enrollment