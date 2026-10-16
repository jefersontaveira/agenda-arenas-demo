import random
import string
import datetime

from apps.backoffice.models import Customer
from apps.saas.models import Arena

def generate_random_phone():
    # Generate a random 11-digit Brazilian phone number starting with 859
    return '859' + ''.join(random.choices(string.digits, k=8))

def generate_random_name():
    first_names = ['João', 'Maria', 'Pedro', 'Ana', 'Lucas', 'Julia', 'Marcos', 'Fernanda', 'Carlos', 'Camila', 'Rafael', 'Amanda', 'Rodrigo', 'Beatriz', 'Felipe', 'Mariana', 'Thiago', 'Leticia', 'Bruno', 'Gabriela', 'Gustavo', 'Larissa', 'Diego', 'Nathalia', 'Renato', 'Carolina', 'Eduardo', 'Aline', 'Leonardo', 'Bruna', 'Victor', 'Jessica', 'Marcelo', 'Juliana', 'André', 'Isabella', 'Gabriel', 'Laura', 'Matheus', 'Sophia']
    last_names = ['Silva', 'Santos', 'Oliveira', 'Souza', 'Rodrigues', 'Ferreira', 'Alves', 'Pereira', 'Lima', 'Gomes', 'Costa', 'Ribeiro', 'Martins', 'Carvalho', 'Almeida', 'Lopes', 'Soares', 'Fernandes', 'Vieira', 'Barbosa', 'Rocha', 'Dias', 'Nascimento', 'Andrade', 'Moreira', 'Nunes', 'Marques', 'Machado', 'Mendes', 'Freitas', 'Cardoso', 'Ramos', 'Gonçalves', 'Santana', 'Teixeira']
    return f"{random.choice(first_names)} {random.choice(last_names)}"

def generate_random_email(name):
    domains = ['gmail.com', 'hotmail.com', 'yahoo.com.br', 'outlook.com']
    clean_name = name.lower().replace(' ', '.').replace('ã', 'a').replace('õ', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ç', 'c')
    return f"{clean_name}{random.randint(1, 999)}@{random.choice(domains)}"

def populate(num_customers=100):
    arena = Arena.objects.first()
    if not arena:
        print("Erro: Nenhuma arena encontrada no banco de dados. Crie uma arena primeiro.")
        return

    print(f"Criando {num_customers} clientes para a arena '{arena.name}'...")
    
    customers_created = 0
    while customers_created < num_customers:
        name = generate_random_name()
        phone = generate_random_phone()
        email = generate_random_email(name) if random.choice([True, False]) else ''
        
        # Check if phone already exists
        if not Customer.objects.filter(arena=arena, phone=phone).exists():
            Customer.objects.create(
                arena=arena,
                name=name,
                phone=phone,
                email=email,
                observation='Cliente gerado automaticamente para testes.' if random.choice([True, False, False]) else ''
            )
            customers_created += 1
            if customers_created % 10 == 0:
                print(f"{customers_created} clientes criados...")

    print("Concluído! 100 clientes gerados com sucesso.")

populate(100)
