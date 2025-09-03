#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste da API Zyntra com credenciais reais do usuário
"""

import requests
import json
import base64

def test_zyntra_credenciais_reais():
    print("🧪 TESTE DA API ZYNTRA - CREDENCIAIS REAIS")
    print("=" * 60)
    
    # Credenciais reais fornecidas pelo usuário
    username = "atendimentocasadecor@outlook.com"
    password = "loki23"
    
    # URL oficial da documentação
    base_url = "https://api.zyntrapayments.com/v1"
    endpoint = "/transactions"
    url = base_url + endpoint
    
    print(f"📧 Username: {username}")
    print(f"🔑 Password: {password}")
    print(f"📡 URL: {url}")
    
    # Teste 1: Basic Auth conforme documentação
    print("\n1️⃣ TESTE BASIC AUTH:")
    auth_string = base64.b64encode(f"{username}:{password}".encode()).decode()
    print(f"🔐 Auth String: {auth_string}")
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_string}"
    }
    
    payload = {
        "amount": 100,  # R$ 1,00 em centavos
        "paymentMethod": "pix",
        "customer": {
            "name": "Teste Cliente",
            "email": "teste@exemplo.com",
            "document": "12345678901"
        },
        "items": [
            {
                "name": "Produto Teste",
                "quantity": 1,
                "price": 100
            }
        ]
    }
    
    try:
        print("🚀 Enviando requisição POST...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
        if response.status_code == 200 or response.status_code == 201:
            print("✅ SUCESSO! Transação criada!")
            return True
        else:
            print(f"❌ ERRO {response.status_code}")
            
    except Exception as e:
        print(f"🔥 ERRO DE CONEXÃO: {e}")
    
    # Teste 2: Verificar se é necessário GET primeiro
    print("\n2️⃣ TESTE GET (verificar se API está ativa):")
    try:
        response = requests.get(base_url, headers=headers, timeout=10)
        print(f"📊 GET Status: {response.status_code}")
        print(f"📄 GET Response: {response.text[:200]}...")
    except Exception as e:
        print(f"🔥 GET ERRO: {e}")
    
    # Teste 3: Testar endpoint raiz
    print("\n3️⃣ TESTE ENDPOINT RAIZ:")
    try:
        root_url = "https://api.zyntrapayments.com"
        response = requests.get(root_url, headers=headers, timeout=10)
        print(f"📊 Root Status: {response.status_code}")
        print(f"📄 Root Response: {response.text[:200]}...")
    except Exception as e:
        print(f"🔥 Root ERRO: {e}")
    
    # Teste 4: Diferentes formatos de auth
    print("\n4️⃣ TESTE FORMATOS ALTERNATIVOS:")
    
    # Bearer Token
    headers_bearer = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_string}"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers_bearer, timeout=10)
        print(f"🔐 Bearer Status: {response.status_code}")
        print(f"📄 Bearer Response: {response.text[:100]}...")
    except Exception as e:
        print(f"🔥 Bearer ERRO: {e}")
    
    # API Key
    headers_apikey = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-API-Key": username,
        "X-API-Secret": password
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers_apikey, timeout=10)
        print(f"🔑 API Key Status: {response.status_code}")
        print(f"📄 API Key Response: {response.text[:100]}...")
    except Exception as e:
        print(f"🔥 API Key ERRO: {e}")
    
    return False

def test_auth_validation():
    """Testa se as credenciais estão no formato correto"""
    print("\n🔍 VALIDAÇÃO DAS CREDENCIAIS")
    print("=" * 60)
    
    username = "atendimentocasadecor@outlook.com"
    password = "loki23"
    
    print(f"📧 Email válido: {'@' in username and '.' in username}")
    print(f"🔑 Password não vazio: {len(password) > 0}")
    print(f"📏 Tamanho do password: {len(password)} caracteres")
    
    # Testar encoding
    auth_string = base64.b64encode(f"{username}:{password}".encode()).decode()
    print(f"🔐 Base64 encoding: {auth_string}")
    
    # Decodificar para verificar
    decoded = base64.b64decode(auth_string).decode()
    print(f"🔓 Decoded: {decoded}")
    print(f"✅ Encoding/Decoding OK: {decoded == f'{username}:{password}'}")

if __name__ == "__main__":
    print("🎯 INICIANDO TESTE COMPLETO DA API ZYNTRA\n")
    
    # Validar credenciais
    test_auth_validation()
    
    # Teste principal
    success = test_zyntra_credenciais_reais()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 TESTE CONCLUÍDO COM SUCESSO!")
    else:
        print("⚠️  TESTE FALHOU - Possíveis causas:")
        print("   1. Credenciais incorretas ou expiradas")
        print("   2. Conta não ativada na Zyntra")
        print("   3. API em manutenção")
        print("   4. Necessário ativar modo sandbox/produção")
    print("=" * 60)