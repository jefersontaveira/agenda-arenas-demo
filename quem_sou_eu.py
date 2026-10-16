import requests

# --- COLE AQUI O TOKEN QUE ESTÁ NO SEU BANCO DE DADOS (Arena Config) ---
TOKEN_PARA_VERIFICAR = "APP_USR-8120828684298351-012118-abbd467b81f3213c9810d19b14675614-3132602002"


def verificar_dono():
    url = "https://api.mercadopago.com/users/me"
    headers = {"Authorization": f"Bearer {TOKEN_PARA_VERIFICAR}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        print("-" * 30)
        print("🕵️  IDENTIDADE DO DONO DO TOKEN")
        print("-" * 30)
        print(f"ID do Usuário: {data['id']}")
        print(f"Nome/Empresa: {data.get('first_name', '')} {data.get('last_name', '')}")
        print(f"Apelido (Nickname): {data.get('nickname')}")
        print(f"Email: {data.get('email')}")
        print(f"Tags: {data.get('tags')}")
        print("-" * 30)

        # ANÁLISE AUTOMÁTICA
        if "test_user" in data.get('tags', []):
            print("✅ ESTE É UM USUÁRIO DE TESTE (VENDEDOR VÁLIDO)")
            print("Agora confira: O ID deste usuário é DIFERENTE do ID do comprador?")
        else:
            print("🚨 PERIGO: ESTE É UM USUÁRIO REAL (PRODUÇÃO)!")
            print("Contas reais NÃO podem cobrar usuários 'test_user_...'.")
            print("SOLUÇÃO: Você precisa trocar esse token pelo token da 'Arena Teste 01'.")

    else:
        print("❌ Token Inválido ou Expirado.")


if __name__ == "__main__":
    verificar_dono()