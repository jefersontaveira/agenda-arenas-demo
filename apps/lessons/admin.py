from django.contrib import admin
from .models import Teacher, ClassGroup, ClassSchedule, Enrollment, MonthlyFee, Lesson


# --- INLINE: Para adicionar horários dentro da tela da Turma ---
class ClassScheduleInline(admin.TabularInline):
    model = ClassSchedule
    extra = 1  # Quantas linhas vazias aparecem por padrão
    verbose_name = "Horário de Aula"
    verbose_name_plural = "Horários de Aula"


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'arena')
    list_filter = ('arena',)
    search_fields = ('name', 'phone')


@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    # Mostra a quadra aqui, pois no seu modelo ela pertence à turma
    list_display = ('name', 'teacher', 'court', 'monthly_price', 'active_students_count', 'is_active')
    list_filter = ('arena', 'is_active', 'teacher', 'court')
    search_fields = ('name',)

    # Isso permite editar os horários na mesma página da turma
    inlines = [ClassScheduleInline]


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'class_group', 'status', 'due_day', 'agreed_price', 'start_date')
    list_filter = ('status', 'class_group', 'due_day')
    search_fields = ('customer__name', 'customer__phone', 'class_group__name')
    autocomplete_fields = ['customer', 'class_group']  # Ajuda se tiver muitos alunos


@admin.register(MonthlyFee)
class MonthlyFeeAdmin(admin.ModelAdmin):
    list_display = ('get_customer_name', 'get_class_name', 'reference_date', 'due_date', 'value', 'status')
    list_filter = ('status', 'due_date', 'reference_date')
    search_fields = ('enrollment__customer__name', 'enrollment__customer__phone')
    date_hierarchy = 'due_date'  # Cria uma navegação por data no topo

    # Helpers para mostrar nome do cliente e turma na listagem de boletos
    @admin.display(description='Aluno')
    def get_customer_name(self, obj):
        return obj.enrollment.customer.name

    @admin.display(description='Turma')
    def get_class_name(self, obj):
        return obj.enrollment.class_group.name


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    # Mostra a Turma, Data, Hora, Status e qual Prof. deu a aula
    list_display = ('get_class_name', 'date', 'start_time', 'status', 'get_teacher_display')

    # Filtros laterais poderosos para achar aulas canceladas ou de uma data específica
    list_filter = ('status', 'date', 'class_group__arena', 'class_group__teacher')

    # Busca pelo nome da turma ou observação
    search_fields = ('class_group__name', 'observation')

    # Navegação por data no topo da lista (Ano > Mês > Dia)
    date_hierarchy = 'date'

    # Ordenação padrão (mais recentes primeiro)
    ordering = ['-date', 'start_time']

    @admin.display(description='Turma')
    def get_class_name(self, obj):
        return obj.class_group.name

    @admin.display(description='Professor do Dia')
    def get_teacher_display(self, obj):
        # Lógica inteligente: Mostra o substituto se houver, senão mostra o titular
        if obj.teacher:
            return f"{obj.teacher.name} (Subst.)"
        elif obj.class_group.teacher:
            return obj.class_group.teacher.name
        return "-"