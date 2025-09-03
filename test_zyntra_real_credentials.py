#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste da API Zyntra com as credenciais reais fornecidas pelo dono da Zyntra
"""

import sys
import os
import json
import requests
import base64
from datetime import datetime

# Adicionar o diretório atual ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import config
    from zytra_api import ZytraPayments, create_zytra_client
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    sys.exit(1)

def test_credentials_encoding():
    """Testa a codificação das credenciais"""
    print("=== TESTE DE CODIFICAÇÃO DAS CREDENCIAIS ===")
    
    secret_key = config.ZYNTRA_SECRET_KEY
    print(f"Secret Key: {secret_key}")
    
    # Testar codificação conforme exemplo do dono da Zyntra
    auth_string = base64.b64encode(f"{secret_key}:x".encode()).decode()
    print(f"Auth String (Base64): {auth_string}")
    
    # Verificar se corresponde ao exemplo fornecido
    expected_auth = "c2tfbGl2ZV92MjJaUlREWlFqUHNPV2xoN0VFT0VnWXJXM2RjeGZNanVVREhIeWo4R2c6eA=="
    print(f"Auth Esperado: {expected_auth}")
    print(f"Auth Gerado:   {auth_string}")
    print(f"Credenciais corretas: {auth_string == expected_auth}")
    
    return auth_string

def test_api_connection():
    """Testa a conexão com a API"""
    print("\n=== TESTE DE CONEXÃO COM A API ===")
    
    base_url = "https://api.zyntrapayments.com/v1"
    auth_string = test_credentials_encoding()
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Basic {auth_string}"
    }
    
    # Testar endpoint de transações
    try:
        print(f"Testando endpoint: {base_url}/transactions")
        response = requests.get(f"{base_url}/transactions", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Resposta: {response.text[:500]}..." if len(response.text) > 500 else f"Resposta: {response.text}")
        
        if response.status_code == 200:
            print("✅ Conexão com API estabelecida com sucesso!")
            return True
        else:
            print(f"❌ Erro na conexão: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False

def test_pix_creation():
    """Testa a criação de uma cobrança PIX"""
    print("\n=== TESTE DE CRIAÇÃO DE COBRANÇA PIX ===")
    
    try:
        # Criar cliente da API
        client = create_zytra_client()
        print("Cliente da API criado com sucesso")
        
        # Dados de teste
        amount = 10.00
        description = "Teste de cobrança PIX - Credenciais Reais"
        customer_info = {
            "name": "Cliente Teste",
            "email": "teste@exemplo.com",
            "phone": "11999999999",
            "document": "11144477735",  # CPF válido para teste
            "street": "Rua Teste",
            "streetNumber": "123",
            "zipCode": "01234567",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP"
        }
        
        print(f"Criando cobrança PIX de R$ {amount:.2f}")
        print(f"Descrição: {description}")
        
        # Criar cobrança
        result = client.create_pix_charge(
            amount=amount,
            description=description,
            customer_info=customer_info
        )
        
        print("\n=== RESULTADO DA CRIAÇÃO ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get("success"):
            print("\n✅ Cobrança PIX criada com sucesso!")
            
            # Verificar se tem QR code
            if result.get("qr_code"):
                print(f"✅ QR Code PIX gerado: {result['qr_code'][:50]}...")
            else:
                print("⚠️ QR Code PIX não encontrado na resposta")
                
            # Verificar se tem URL de pagamento
            if result.get("secure_url"):
                print(f"✅ URL de pagamento: {result['secure_url']}")
                
            return True
        else:
            print(f"❌ Erro ao criar cobrança: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Função principal de teste"""
    print("TESTE DA API ZYNTRA COM CREDENCIAIS REAIS")
    print("=" * 50)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Modo Demo: {getattr(config, 'DEMO_MODE', 'Não definido')}")
    
    # Desabilitar modo demo para teste real
    config.DEMO_MODE = False
    print("Modo demo desabilitado para teste real")
    
    # Executar testes
    tests = [
        ("Codificação de Credenciais", test_credentials_encoding),
        ("Conexão com API", test_api_connection),
        ("Criação de Cobrança PIX", test_pix_creation)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erro no teste {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumo dos resultados
    print("\n" + "=" * 50)
    print("RESUMO DOS TESTES")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
    
    # Verificar se todos os testes passaram
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 TODOS OS TESTES PASSARAM! A integração está funcionando!")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique os logs acima.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)