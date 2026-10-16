import re

def validate_cpf(cpf):
    """Remove caracteres não numéricos e valida o tamanho do CPF."""
    cpf = re.sub(r'\D', '', cpf)
    return len(cpf) == 11

def validate_phone(phone):
    """Valida se o telefone tem entre 10 e 11 dígitos numéricos (DDD + número)."""
    phone = re.sub(r'\D', '', phone)
    return 10 <= len(phone) <= 11
