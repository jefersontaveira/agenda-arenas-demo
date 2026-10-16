import requests
import re
from decouple import config

# Chave e URL do Asaas (Sandbox por padrão, configurável via .env)
ASAAS_MASTER_API_KEY = config('ASAAS_API_KEY', default="")
ASAAS_BASE_URL = config('ASAAS_BASE_URL', default="https://sandbox.asaas.com/api/v3")


def get_asaas_config():
    """Lê as configurações atualizadas do .env ou ambiente."""
    try:
        from decouple import RepositoryEnv, Config
        import os
        if os.path.exists('.env'):
            env_config = Config(RepositoryEnv('.env'))
            api_key = env_config('ASAAS_API_KEY', default='')
            base_url = env_config('ASAAS_BASE_URL', default='')
            if api_key:
                return api_key, base_url or ('https://sandbox.asaas.com/api/v3' if '_hmlg_' in api_key else 'https://api.asaas.com/v3')
    except Exception:
        pass
    
    api_key = config('ASAAS_API_KEY', default='')
    base_url = config('ASAAS_BASE_URL', default='https://sandbox.asaas.com/api/v3')
    return api_key, base_url


def gerar_pagamento_pix_asaas(booking, amount_to_pay):
    """
    Gera uma cobrança PIX no Asaas para uma reserva específica.
    """
    asaas_config = getattr(booking.arena, 'asaas_config', None)
    master_key, default_base_url = get_asaas_config()

    # Prioridade: Chave da subconta da arena ou chave master da plataforma (.env)
    api_key = (asaas_config.api_key if asaas_config and asaas_config.api_key else None) or master_key
    if api_key:
        api_key = api_key.strip().strip('"').strip("'")
    
    # Define URL base de acordo com o tipo da chave (produção ou homologação/sandbox)
    if api_key and '_prod_' in api_key:
        base_url = 'https://api.asaas.com/v3'
    elif api_key and '_hmlg_' in api_key:
        base_url = 'https://sandbox.asaas.com/api/v3'
    else:
        base_url = default_base_url or 'https://sandbox.asaas.com/api/v3'

    masked_key = f"{api_key[:12]}...{api_key[-8:]}" if api_key and len(api_key) > 20 else str(api_key)
    print(f"DEBUG ASAAS: Usando chave [{masked_key}] no endpoint [{base_url}]")

    headers = {
        "access_token": api_key,
        "Content-Type": "application/json",
        "User-Agent": "ArenaApp"
    }

    # --- LIMPEZA E VALIDAÇÃO DE DADOS ---
    # O Asaas exige APENAS números no CPF e Telefone.
    # Se enviar '.' ou '-', a API retorna "invalid_object".
    cpf_raw = str(booking.customer.cpf or "")
    cpf_limpo = re.sub(r'\D', '', cpf_raw)

    telefone_raw = str(booking.customer.phone or "")
    telefone_limpo = re.sub(r'\D', '', telefone_raw)

    # Log de segurança para o seu terminal
    print(f"--- INICIANDO COBRANÇA ASAAS (Booking ID: {booking.id}) ---")
    print(f"DEBUG: Enviando CPF: '{cpf_limpo}' | Telefone: '{telefone_limpo}'")

    if not cpf_limpo:
        raise Exception("Erro Crítico: O CPF do cliente não foi encontrado no banco de dados.")

    # --- 2. CRIAR/BUSCAR CLIENTE NO ASAAS ---
    customer_payload = {
        "name": booking.customer.name,
        "mobilePhone": telefone_limpo,
        "cpfCnpj": cpf_limpo,
        "notificationDisabled": True
    }

    customer_response = requests.post(f"{base_url}/customers", json=customer_payload, headers=headers)

    if not customer_response.ok:
        raise Exception(f"Erro ao cadastrar cliente no Asaas: {customer_response.text}")

    asaas_customer_id = customer_response.json().get("id")

    # --- 3. CRIAR COBRANÇA PIX ---
    # Calculamos o Split (caso queira reativar no futuro)
    # percentual_taxa = float(0) / 100.0
    # taxa_plataforma = percentual_taxa * float(amount_to_pay)
    # valor_arena = float(amount_to_pay) - taxa_plataforma

    charge_payload = {
        "customer": asaas_customer_id,
        "billingType": "PIX",
        "value": float(amount_to_pay),
        "dueDate": booking.start_time.strftime("%Y-%m-%d"),
        "description": f"Reserva {booking.arena.name} - Quadra {booking.court.name}",
        "externalReference": str(booking.id),
        # Se quiser ativar o split, basta descomentar abaixo:
        # "split": [{
        #     "walletId": arena_config.asaas_wallet_id,
        #     "fixedValue": float(valor_arena)
        # }]
    }

    charge_response = requests.post(f"{base_url}/payments", json=charge_payload, headers=headers)

    if not charge_response.ok:
        raise Exception(f"Erro ao criar cobrança no Asaas: {charge_response.text}")

    charge_data = charge_response.json()
    asaas_payment_id = charge_data.get("id")
    invoice_url = charge_data.get("invoiceUrl")
    bank_receipt_url = charge_data.get("transactionReceiptUrl")

    # --- 4. OBTER QR CODE E PAYLOAD PIX ---
    qr_code_url = f"{base_url}/payments/{asaas_payment_id}/pixQrCode"
    qr_code_response = requests.get(qr_code_url, headers=headers)

    if not qr_code_response.ok:
        raise Exception(f"Erro ao recuperar QR Code: {qr_code_response.text}")

    qr_data = qr_code_response.json()

    print(f"--- SUCESSO: Cobrança {asaas_payment_id} gerada! ---")

    return {
        "transaction_id": asaas_payment_id,
        "qr_code": qr_data.get("payload"),
        "qr_code_base64": qr_data.get("encodedImage"),
        "amount": amount_to_pay,
        "invoice_url": invoice_url,
        "bank_receipt_url": bank_receipt_url,
    }


def obter_comprovante_bancario_asaas(booking):
    """
    Busca o link do comprovante bancário oficial emitido pelo Asaas para a reserva.
    Prioriza:
    1. 'transactionReceiptUrl' (comprovante oficial de transação bancária após confirmação)
    2. 'invoiceUrl' (fatura / recibo web oficial do Asaas com autenticação bancária e opção de PDF)
    3. Fallback construído caso a API esteja temporariamente inacessível.
    """
    payment = booking.payments.filter(transaction_id__isnull=False).exclude(transaction_id='').last()
    if not payment:
        return None

    # Se já temos o link direto do comprovante bancário salvo
    if payment.bank_receipt_url:
        return payment.bank_receipt_url

    asaas_config = getattr(booking.arena, 'asaas_config', None)
    master_key, default_base_url = get_asaas_config()
    api_key = (asaas_config.api_key if asaas_config and asaas_config.api_key else None) or master_key
    if api_key:
        api_key = api_key.strip().strip('"').strip("'")

    if api_key and '_prod_' in api_key:
        base_url = 'https://api.asaas.com/v3'
        web_base = 'https://www.asaas.com'
    elif api_key and '_hmlg_' in api_key:
        base_url = 'https://sandbox.asaas.com/api/v3'
        web_base = 'https://sandbox.asaas.com'
    else:
        base_url = default_base_url or 'https://sandbox.asaas.com/api/v3'
        web_base = 'https://sandbox.asaas.com' if 'sandbox' in str(base_url) else 'https://www.asaas.com'

    try:
        headers = {
            "access_token": api_key,
            "Content-Type": "application/json",
            "User-Agent": "ArenaApp"
        }
        resp = requests.get(f"{base_url}/payments/{payment.transaction_id}", headers=headers, timeout=6)
        if resp.ok:
            data = resp.json()
            receipt_url = data.get("transactionReceiptUrl")
            invoice_url = data.get("invoiceUrl")

            if receipt_url:
                payment.bank_receipt_url = receipt_url
            if invoice_url:
                payment.invoice_url = invoice_url
            if receipt_url or invoice_url:
                payment.save(update_fields=['bank_receipt_url', 'invoice_url'])

            if receipt_url:
                return receipt_url
            if invoice_url:
                return invoice_url
    except Exception as e:
        print(f"Erro ao buscar comprovante Asaas: {e}")

    # Fallback se a API falhar ou estiver offline
    if payment.invoice_url:
        return payment.invoice_url

    clean_id = payment.transaction_id.replace('pay_', '')
    return f"{web_base}/i/{clean_id}"
