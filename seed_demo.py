import os
import shutil
from pathlib import Path
import django
from datetime import time, date, timedelta
from django.utils import timezone
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.saas.models import Arena, Subscription
from apps.backoffice.models import (
    ArenaConfig, AsaasConfig, ArenaOpeningHour, Modality, DayOfWeek, Court, Equipment, Customer, PriceRule, Booking
)
from apps.lessons.models import Teacher, ClassGroup, ClassSchedule, Lesson, Enrollment, MonthlyFee

def populate():
    print("[*] Populando banco de dados de demonstracao da Arena atualizado...")

    # 1. Usuario Gestor da Arena & Superadmin
    user, created = User.objects.get_or_create(username='demo_gestor', defaults={
        'first_name': 'Gestor',
        'last_name': 'Demonstracao',
        'email': 'gestor.demo@arenaexemplo.com'
    })
    user.set_password('demo1234')
    user.is_staff = True
    user.save()

    admin, _ = User.objects.get_or_create(username='admin', defaults={
        'email': 'admin@arenaexemplo.com',
        'first_name': 'Super',
        'last_name': 'Admin',
        'is_staff': True,
        'is_superuser': True
    })
    admin.set_password('admin1234')
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()
    print("[OK] Usuarios configurados: demo_gestor / demo1234 e admin / admin1234")

    # 2. Dias da Semana
    for num, name in DayOfWeek.DAYS_CHOICES:
        DayOfWeek.objects.get_or_create(number=num)

    # 3. Arena Unica de Demonstracao
    arena, _ = Arena.objects.get_or_create(slug='arena-demo', defaults={
        'name': 'Arena Prime Beach & Sports',
        'owner_name': 'Jeferson Taveira',
        'owner_phone': '(85) 99876-5432',
        'owner_email': 'gestor.demo@arenaexemplo.com',
        'cnpj': '12.345.678/0001-90',
        'monthly_fee': Decimal('299.00'),
        'due_day': 10,
        'is_active': True,
    })
    arena.users.add(user)
    print(f"[OK] Arena configurada: {arena.name} ({arena.slug})")

    # 4. Modalidades (agora vinculadas a Arena)
    modalidades_data = [
        {"name": "Beach Tennis", "emoji": "BT", "icon": "bi-tennis"},
        {"name": "Volei de Praia", "emoji": "VP", "icon": "bi-volleyball"},
        {"name": "Futevolei", "emoji": "FV", "icon": "bi-dribbble"},
        {"name": "Padel", "emoji": "PD", "icon": "bi-table-tennis"},
        {"name": "Funcional de Areia", "emoji": "FA", "icon": "bi-heart-pulse"},
    ]
    modalidades = {}
    for m in modalidades_data:
        mod, _ = Modality.objects.get_or_create(
            arena=arena,
            name=m['name'],
            defaults={'emoji': m['emoji'], 'icon': m['icon']}
        )
        modalidades[m['name']] = mod
    print("[OK] Modalidades cadastradas para a Arena")

    # 5. Configuracao da Arena (com branding, site customizavel e politicas)
    config, _ = ArenaConfig.objects.get_or_create(arena=arena, defaults={
        'slot_duration': 60,
        'default_price': Decimal('80.00'),
        'primary_color': '#A855F7',
        'secondary_color': '#060814',
        'hero_title': 'Arena Prime Beach & Sports',
        'hero_subtitle': 'Agende sua quadra de Beach Tennis, Padel e Futevôlei em tempo real.',
        'contact_phone': '(85) 99876-5432',
        'instagram': '@arenaprime.sports',
        'address': 'Av. Beira Mar, 1200 - Fortaleza, CE',
        'about_text': 'Complexo esportivo de areia e padel com estrutura premium, iluminação LED profissional e bar integrado.',
        'payment_policy': 'ALL_OPTIONS',
    })

    # 6. Integracao Asaas (Subconta Ativa Sandbox)
    asaas, _ = AsaasConfig.objects.get_or_create(arena=arena, defaults={
        'wallet_id': 'wallet_demo_sandbox_8899',
        'api_key': 'sandbox_dummy_token_demo_987654321',
        'cpf_cnpj': '12.345.678/0001-90',
        'company_type': 'MEI',
        'company_email': 'gestor.demo@arenaexemplo.com',
        'bank_code': '260',
        'agency': '0001',
        'account': '1234567',
        'account_digit': '8',
        'bank_account_type': 'CONTA_CORRENTE',
        'is_active': True,
    })
    print("[OK] Configuracao da Arena e Subconta Asaas ativas")

    # 7. Horarios de Funcionamento (Segunda a Domingo, das 06:00 as 23:00)
    for day_num in range(7):
        ArenaOpeningHour.objects.get_or_create(
            arena=arena,
            weekday=day_num,
            defaults={
                'open_time': time(6, 0),
                'close_time': time(23, 0),
                'is_closed': False
            }
        )

    # 8. Quadras da Arena
    quadras_data = [
        {"name": "Quadra 1 - Central Beach", "color": "#00F2FE", "price": Decimal("90.00"), "mods": ["Beach Tennis", "Volei de Praia", "Futevolei"]},
        {"name": "Quadra 2 - Padel Pro", "color": "#A855F7", "price": Decimal("110.00"), "mods": ["Padel"]},
        {"name": "Quadra 3 - Areia Sunset", "color": "#F59E0B", "price": Decimal("80.00"), "mods": ["Beach Tennis", "Futevolei", "Funcional de Areia"]},
        {"name": "Quadra 4 - Training Sand", "color": "#10B981", "price": Decimal("75.00"), "mods": ["Volei de Praia", "Funcional de Areia"]},
    ]
    quadras = {}
    for q in quadras_data:
        court, _ = Court.objects.get_or_create(
            arena=arena,
            name=q['name'],
            defaults={'color': q['color'], 'price': q['price'], 'is_active': True}
        )
        for m_name in q['mods']:
            court.modalities.add(modalidades[m_name])
        quadras[q['name']] = court
    print("[OK] 4 Quadras estruturadas com modalidades e cores")

    # 9. Regras de Preco Especiais (Horario Nobre Noturno)
    regra_nobre, _ = PriceRule.objects.get_or_create(
        arena=arena,
        name="Horario Nobre (Noite)",
        defaults={
            'price': Decimal('120.00'),
            'start_time': time(18, 0),
            'end_time': time(23, 0),
        }
    )
    dias_semana = DayOfWeek.objects.filter(number__in=[0, 1, 2, 3, 4])
    regra_nobre.days.set(dias_semana)

    # 10. Clientes / Atletas
    clientes_data = [
        {"name": "Lucas Menezes", "phone": "(85) 99123-4567", "email": "lucas.menezes@email.com", "games": 14},
        {"name": "Camila Vasconcelos", "phone": "(85) 99876-5432", "email": "camila.v@email.com", "games": 9},
        {"name": "Rodrigo Albuquerque", "phone": "(85) 98765-1122", "email": "rodrigo.alb@email.com", "games": 22},
        {"name": "Mariana Barreto", "phone": "(85) 99234-8899", "email": "mariana.barreto@email.com", "games": 6},
        {"name": "Thiago Siqueira", "phone": "(85) 98111-3344", "email": "thiago.siqueira@email.com", "games": 18},
        {"name": "Beatriz Farias", "phone": "(85) 99777-6655", "email": "beatriz.farias@email.com", "games": 4},
    ]
    clientes = {}
    for c in clientes_data:
        cust, _ = Customer.objects.get_or_create(
            arena=arena,
            phone=c['phone'],
            defaults={'name': c['name'], 'email': c['email'], 'total_bookings': c['games']}
        )
        clientes[c['name']] = cust
    print("[OK] Clientes cadastrados")

    # 11. Professores / Instrutores
    prof_carlos, _ = Teacher.objects.get_or_create(
        arena=arena,
        name="Prof. Carlos Eduardo (Kadu)",
        defaults={'phone': '(85) 99444-2211', 'email': 'kadu.beachtennis@arena.com', 'color': '#00F2FE'}
    )
    prof_ana, _ = Teacher.objects.get_or_create(
        arena=arena,
        name="Profa. Ana Clara Silva",
        defaults={'phone': '(85) 99333-1122', 'email': 'ana.futevolei@arena.com', 'color': '#A855F7'}
    )
    print("[OK] Professores cadastrados")

    # 12. Turmas de Aula
    turma_bt_iniciante, _ = ClassGroup.objects.get_or_create(
        arena=arena,
        name="Beach Tennis - Iniciante / Fundamentos",
        defaults={
            'court': quadras["Quadra 1 - Central Beach"],
            'teacher': prof_carlos,
            'description': "Turma para quem esta iniciando no Beach Tennis. Pegada correta, movimentacao e saque.",
            'max_students': 6,
            'monthly_price': Decimal('220.00'),
            'is_active': True
        }
    )
    ClassSchedule.objects.get_or_create(class_group=turma_bt_iniciante, day_of_week=1, defaults={'start_time': time(7, 0), 'end_time': time(8, 0)})
    ClassSchedule.objects.get_or_create(class_group=turma_bt_iniciante, day_of_week=3, defaults={'start_time': time(7, 0), 'end_time': time(8, 0)})

    turma_fut_avancado, _ = ClassGroup.objects.get_or_create(
        arena=arena,
        name="Futevolei - Misto Intermediario / Avancado",
        defaults={
            'court': quadras["Quadra 3 - Areia Sunset"],
            'teacher': prof_ana,
            'description': "Evolucao de ataque, pingo, tubarao e posicionamento defensivo.",
            'max_students': 8,
            'monthly_price': Decimal('250.00'),
            'is_active': True
        }
    )
    ClassSchedule.objects.get_or_create(class_group=turma_fut_avancado, day_of_week=0, defaults={'start_time': time(19, 0), 'end_time': time(20, 0)})
    ClassSchedule.objects.get_or_create(class_group=turma_fut_avancado, day_of_week=2, defaults={'start_time': time(19, 0), 'end_time': time(20, 0)})

    # Matriculas de Alunos
    Enrollment.objects.get_or_create(class_group=turma_bt_iniciante, customer=clientes["Lucas Menezes"], defaults={'agreed_price': Decimal('220.00'), 'status': 'ACTIVE', 'due_day': 10})
    Enrollment.objects.get_or_create(class_group=turma_bt_iniciante, customer=clientes["Camila Vasconcelos"], defaults={'agreed_price': Decimal('220.00'), 'status': 'ACTIVE', 'due_day': 10})
    Enrollment.objects.get_or_create(class_group=turma_fut_avancado, customer=clientes["Rodrigo Albuquerque"], defaults={'agreed_price': Decimal('250.00'), 'status': 'ACTIVE', 'due_day': 5})
    Enrollment.objects.get_or_create(class_group=turma_fut_avancado, customer=clientes["Beatriz Farias"], defaults={'agreed_price': Decimal('0.00'), 'status': 'TRIAL', 'due_day': 15})
    print("[OK] Turmas, horarios e matriculas configurados")

    # 13. Reservas Dinamicas de Hoje e Amanha
    hoje = timezone.now().date()
    agendamentos = [
        # Hoje
        {"court": "Quadra 1 - Central Beach", "cust": "Lucas Menezes", "date": hoje, "hour": 8, "status": "CONFIRMED", "paid": True, "val": 90.00, "origin": "ONLINE"},
        {"court": "Quadra 1 - Central Beach", "cust": "Thiago Siqueira", "date": hoje, "hour": 17, "status": "CONFIRMED", "paid": True, "val": 90.00, "origin": "BACKOFFICE"},
        {"court": "Quadra 1 - Central Beach", "cust": "Rodrigo Albuquerque", "date": hoje, "hour": 19, "status": "CONFIRMED", "paid": True, "val": 120.00, "origin": "ONLINE"},
        {"court": "Quadra 2 - Padel Pro", "cust": "Mariana Barreto", "date": hoje, "hour": 18, "status": "CONFIRMED", "paid": True, "val": 120.00, "origin": "ONLINE"},
        {"court": "Quadra 3 - Areia Sunset", "cust": "Camila Vasconcelos", "date": hoje, "hour": 9, "status": "CONFIRMED", "paid": True, "val": 80.00, "origin": "BACKOFFICE"},
        {"court": "Quadra 3 - Areia Sunset", "cust": "Thiago Siqueira", "date": hoje, "hour": 18, "status": "PENDING", "paid": False, "val": 120.00, "origin": "ONLINE"},
        # Amanha
        {"court": "Quadra 1 - Central Beach", "cust": "Beatriz Farias", "date": hoje + timedelta(days=1), "hour": 10, "status": "CONFIRMED", "paid": True, "val": 90.00, "origin": "ONLINE"},
        {"court": "Quadra 2 - Padel Pro", "cust": "Lucas Menezes", "date": hoje + timedelta(days=1), "hour": 19, "status": "CONFIRMED", "paid": True, "val": 120.00, "origin": "BACKOFFICE"},
        {"court": "Quadra 3 - Areia Sunset", "cust": "Rodrigo Albuquerque", "date": hoje + timedelta(days=1), "hour": 20, "status": "CONFIRMED", "paid": True, "val": 120.00, "origin": "ONLINE"},
    ]

    for ag in agendamentos:
        c_obj = quadras[ag["court"]]
        cust_obj = clientes[ag["cust"]]
        st = timezone.make_aware(timezone.datetime.combine(ag["date"], time(ag["hour"], 0)))
        et = timezone.make_aware(timezone.datetime.combine(ag["date"], time(ag["hour"] + 1, 0)))
        
        Booking.objects.get_or_create(
            arena=arena,
            court=c_obj,
            start_time=st,
            defaults={
                'end_time': et,
                'customer': cust_obj,
                'price': Decimal(str(ag["val"])),
                'status': ag["status"],
                'payment_status': 'PAID' if ag["paid"] else 'PENDING',
                'amount_paid': Decimal(str(ag["val"])) if ag["paid"] else Decimal('0.00'),
                'origin': ag.get('origin', 'BACKOFFICE')
            }
        )

    print("[OK] Reservas e agendamentos preenchidos!")

    # 14. Gera Snapshot Limpo para o Sandbox
    base_dir = Path(__file__).resolve().parent
    active_db = base_dir / 'db.sqlite3'
    seed_db = base_dir / 'db_seed_clean.sqlite3'
    if active_db.exists():
        shutil.copyfile(active_db, seed_db)
        print(f"[OK] Snapshot limpo criado em {seed_db.name} para o Sandbox!")

    print("[CONCLUIDO] Populacao e snapshot concluidos com sucesso!")

if __name__ == '__main__':
    populate()
