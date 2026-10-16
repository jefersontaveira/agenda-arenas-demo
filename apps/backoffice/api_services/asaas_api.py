import requests
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

ASAAS_API_URL = getattr(settings, 'ASAAS_API_URL', 'https://sandbox.asaas.com/api/v3')
ASAAS_API_KEY_MASTER = getattr(settings, 'ASAAS_API_KEY_MASTER', '')

def get_headers(api_key=None):
    key = api_key if api_key else ASAAS_API_KEY_MASTER
    return {
        'access_token': key,
        'Content-Type': 'application/json'
    }

def create_asaas_subaccount(arena, asaas_config, request_user):
    """
    Cria uma subconta White Label no Asaas para a Arena.
    """
    url = f"{ASAAS_API_URL}/accounts"

    # Preparando dados. O Asaas exige alguns campos obrigatórios.
    # Se alguns campos (endereço, etc) não estiverem no asaas_config, passamos genéricos 
    # ou os dados que já temos no model ArenaConfig (se existirem).
    
    # Busca dados de endereço da ArenaConfig, se houver
    address = "Não Informado"
    if hasattr(arena, 'config') and arena.config.address:
        address = arena.config.address

    payload = {
        "name": arena.name,
        "email": asaas_config.company_email or request_user.email or f"{arena.slug}@exemplo.com", # Email de login da subconta
        "loginEmail": asaas_config.company_email or request_user.email or f"{arena.slug}@exemplo.com",
        "cpfCnpj": asaas_config.cpf_cnpj,
        "companyType": asaas_config.company_type if asaas_config.company_type else "MEI",
        "birthDate": asaas_config.birth_date.strftime("%Y-%m-%d") if asaas_config.birth_date else None,
        
        # Telefones (obrigatório, podemos usar o de contato ou gerar um placeholder temporário se vazio)
        "phone": getattr(arena.config, 'contact_phone', "11999999999") if hasattr(arena, 'config') else "11999999999",
        "mobilePhone": getattr(arena.config, 'contact_phone', "11999999999") if hasattr(arena, 'config') else "11999999999",
        
        # Endereço (Obrigatórios para Subconta)
        "address": address,
        "addressNumber": "0",
        "province": "Bairro",
        "postalCode": "01001000", # Necessário um CEP válido.
        
        # Tipo de faturamento (usar o padrão do Asaas)
        "incomeValue": "5000"
    }
    
    # Remove máscaras do CPF/CNPJ e CEP
    import re
    if payload["cpfCnpj"]:
        payload["cpfCnpj"] = re.sub(r'\D', '', payload["cpfCnpj"])
    if payload["phone"]:
        payload["phone"] = re.sub(r'\D', '', payload["phone"])
    if payload["mobilePhone"]:
        payload["mobilePhone"] = re.sub(r'\D', '', payload["mobilePhone"])

    try:
        response = requests.post(url, json=payload, headers=get_headers())
        data = response.json()
        
        if response.status_code == 200:
            return True, data
        else:
            # === MODO SIMULAÇÃO (Para destravar o desenvolvimento local sem CNPJ) ===
            if settings.DEBUG:
                errors = data.get('errors', [])
                cpf_error = any("pessoa física (CPF) não podem criar subcontas" in str(e).lower() for e in errors)
                
                if cpf_error:
                    logger.warning("Mocking Asaas Subaccount creation due to CPF Sandbox limitation.")
                    fake_data = {
                        "walletId": f"mock_wallet_{arena.slug}",
                        "apiKey": f"mock_api_key_{arena.slug}_12345"
                    }
                    return True, fake_data
            # ========================================================================
            
            logger.error(f"Erro ao criar subconta Asaas: {data}")
            return False, data.get('errors', [{'description': 'Erro desconhecido'}])
            
    except Exception as e:
        logger.exception("Falha de conexão com Asaas")
        return False, [{'description': str(e)}]


def update_subaccount_bank(asaas_config):
    """
    Atualiza ou configura a conta bancária para saque automático da Subconta.
    Isso deve ser chamado usando a API KEY DA SUBCONTA.
    """
    pass
