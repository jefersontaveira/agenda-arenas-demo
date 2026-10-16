import requests
import json
import time
from django.conf import settings


def generate_pix_payment(booking):
    """
    Gera um pagamento Pix dinâmico usando as credenciais da Arena.
    """

    # --- CONFIGURAÇÃO DE AMBIENTE ---
    MODO_TESTE_SANDBOX = True

    # MUDANÇA AQUI: Não usamos mais o 'test_user_...'.
    # Usamos um e-mail genérico qualquer, pois o Vendedor já é de Teste.
    EMAIL_GENERICO = "cliente_teste_sistema_99@gmail.com"
    CPF_TESTE_GENERICO = "19119119100"  # CPF Mágico do Sandbox

    # --- 1. RECUPERAÇÃO DO TOKEN DINÂMICO ---
    try:
        arena_config = booking.arena.config
        access_token = arena_config.mp_access_token
    except Exception:
        return {"error": "Configuração da Arena não encontrada."}

    if not access_token:
        return {"error": "A Arena não está conectada ao Mercado Pago."}

    # --- 2. PREPARAÇÃO DOS DADOS ---
    amount = float(booking.price)

    # Lógica de Decisão: Sandbox vs Produção
    if MODO_TESTE_SANDBOX:
        # MODO TESTE: Usamos dados genéricos
        payer_email = EMAIL_GENERICO
        first_name = "Comprador"
        last_name = "Generico"

        # No Sandbox com Vendedor Fake, DEVEMOS enviar o CPF genérico
        identification_data = {
            "type": "CPF",
            "number": CPF_TESTE_GENERICO
        }

        print(f"⚠️ MODO SANDBOX: Usando {payer_email} + CPF {CPF_TESTE_GENERICO}")

    else:
        # MODO PRODUÇÃO
        payer_email = booking.customer.email
        if not payer_email:
            payer_email = f"cliente_sem_email_{booking.id}@email.com"

        try:
            raw_name = booking.customer.name.strip()
            parts = raw_name.split()
            first_name = parts[0]
            last_name = parts[-1] if len(parts) > 1 else "Cliente"
        except:
            first_name = "Cliente"
            last_name = "Real"

        # Em produção, enviamos SEM CPF para evitar travas de cadastro
        identification_data = None

    # --- 3. MONTAGEM DO PAYLOAD ---
    payload = {
        "transaction_amount": amount,
        "description": f"Reserva: {booking.court.name}",
        "payment_method_id": "pix",
        "payer": {
            "email": payer_email,
            "first_name": first_name,
            "last_name": last_name,
            "identification": identification_data
        },
        "notification_url": f"{settings.MERCADO_PAGO_WEBHOOK_BASE}/scheduler/webhook/mercadopago/",
        "external_reference": str(booking.id)
    }

    # Limpeza final: remove chaves nulas
    if payload["payer"]["identification"] is None:
        del payload["payer"]["identification"]

    # --- 4. ENVIO PARA A API ---
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": f"book_{booking.id}_{int(time.time())}"
    }

    url = "https://api.mercadopago.com/v1/payments"

    print(f"--- GERANDO PIX ---")
    print(f"Arena (Vendedor): {booking.arena.name}")
    print(f"Comprador: {payer_email}")

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code == 201:
            return response.json()
        else:
            print(f"Erro MP Status: {response.status_code}")
            print(f"Erro MP Body: {response.text}")

            if response.status_code == 401:
                return {"error": "Token inválido. Reconecte a conta da Arena."}

            return {"error": "Falha ao gerar Pix", "details": response.json()}

    except Exception as e:
        print(f"Erro de conexão: {e}")
        return {"error": "Erro de conexão"}