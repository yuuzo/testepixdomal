#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Específico da API Zyntra Real

Baseado nos resultados do teste anterior, vamos focar na URL que responde:
https://api.zyntrapayments.com
"""

import requests
import base64
import json
from datetime import datetime, timedelta
import config

def test_zyntra_endpoints():
    """Testa endpoints específicos da Zyntra"""
    base_url = "https://api.zyntrapayments.com"
    
    # Lista de endpoints possíveis baseados em APIs de pagamento comuns
    endpoints_to_test = [
        # Endpoints de informação
        "/",
        "/health",
        "/status",
        "/ping",
        "/docs",
        "/swagger",
        "/api-docs",
        
        # Endpoints de API
        "/v1",
        "/v2",
        "/api/v1",
        "/api/v2",
        
        # Endpoints de transações
        "/v1/transactions",
        "/v1/payments",
        "/v1/charges",
        "/v1/orders",
        "/v1/pix",
        "/v1/pix/charges",
        "/v1/pix/transactions",
        
        # Endpoints alternativos
        "/transactions",
        "/payments",
        "/charges",
        "/pix",
        "/create-charge",
        "/create-payment",
        "/create-transaction"
    ]
    
    print("🔍 TESTANDO ENDPOINTS DA API ZYNTRA")
    print(f"🌐 Base URL: {base_url}")
    print("=" * 60)
    
    # Teste GET simples primeiro
    print("\n📋 TESTANDO REQUISIÇÕES GET:")
    for endpoint in endpoints_to_test:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=5)
            status_emoji = "✅" if response.status_code == 200 else "⚠️" if response.status_code in [401, 403] else "❌"
            print(f"  {status_emoji} {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text[:200].replace('\n', ' ')
                print(f"    📄 Conteúdo: {content}...")
            elif response.status_code in [401, 403]:
                print(f"    🔐 Requer autenticação")
            elif response.status_code == 404:
                print(f"    🚫 Endpoint não encontrado")
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ {endpoint}: Erro de conexão")
    
    # Teste POST com autenticação
    print("\n📋 TESTANDO REQUISIÇÕES POST COM AUTENTICAÇÃO:")
    
    # Dados de teste mínimos
    test_data = {
        "amount": 100,
        "currency": "BRL",
        "payment_method": "pix"
    }
    
    # Diferentes formatos de autenticação para testar
    auth_methods = [
        {"name": "Basic (secret:x)", "headers": {"Authorization": f"Basic {base64.b64encode(f'{config.ZYNTRA_SECRET_KEY}:x'.encode()).decode()}"}},
        {"name": "Basic (secret:)", "headers": {"Authorization": f"Basic {base64.b64encode(f'{config.ZYNTRA_SECRET_KEY}:'.encode()).decode()}"}},
        {"name": "Bearer secret", "headers": {"Authorization": f"Bearer {config.ZYNTRA_SECRET_KEY}"}},
        {"name": "Bearer public", "headers": {"Authorization": f"Bearer {config.ZYNTRA_PUBLIC_KEY}"}},
        {"name": "X-API-Key secret", "headers": {"X-API-Key": config.ZYNTRA_SECRET_KEY}},
        {"name": "X-API-Key public", "headers": {"X-API-Key": config.ZYNTRA_PUBLIC_KEY}},
    ]
    
    post_endpoints = [
        "/v1/transactions",
        "/v1/payments",
        "/v1/charges",
        "/v1/pix",
        "/transactions",
        "/payments",
        "/charges",
        "/pix"
    ]
    
    for auth_method in auth_methods:
        print(f"\n🔐 Testando {auth_method['name']}:")
        
        headers = {"Content-Type": "application/json"}
        headers.update(auth_method['headers'])
        
        for endpoint in post_endpoints:
            url = f"{base_url}{endpoint}"
            try:
                response = requests.post(url, json=test_data, headers=headers, timeout=5)
                
                if response.status_code == 401:
                    print(f"  🔐 {endpoint}: 401 - Token inválido")
                elif response.status_code == 400:
                    print(f"  ⚠️ {endpoint}: 400 - Dados inválidos (mas autenticação OK!)")
                    print(f"    📄 Resposta: {response.text[:100]}...")
                elif response.status_code == 200 or response.status_code == 201:
                    print(f"  ✅ {endpoint}: {response.status_code} - SUCESSO!")
                    print(f"    📄 Resposta: {response.text[:200]}...")
                elif response.status_code == 404:
                    print(f"  🚫 {endpoint}: 404 - Endpoint não encontrado")
                else:
                    print(f"  ❓ {endpoint}: {response.status_code} - {response.text[:50]}...")
                    
            except requests.exceptions.RequestException as e:
                print(f"  ❌ {endpoint}: Erro de conexão")

def test_zyntra_documentation_endpoints():
    """Testa endpoints que podem conter documentação"""
    base_url = "https://api.zyntrapayments.com"
    
    doc_endpoints = [
        "/docs",
        "/swagger",
        "/api-docs",
        "/openapi.json",
        "/swagger.json",
        "/redoc",
        "/documentation",
        "/help",
        "/reference"
    ]
    
    print("\n📚 PROCURANDO DOCUMENTAÇÃO DA API:")
    
    for endpoint in doc_endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"  ✅ {endpoint}: Documentação encontrada!")
                print(f"    🔗 URL: {url}")
                content_type = response.headers.get('content-type', '')
                print(f"    📄 Tipo: {content_type}")
                
                if 'json' in content_type:
                    try:
                        data = response.json()
                        if 'info' in data:
                            print(f"    📋 Título: {data.get('info', {}).get('title', 'N/A')}")
                            print(f"    📋 Versão: {data.get('info', {}).get('version', 'N/A')}")
                    except:
                        pass
                        
            elif response.status_code == 404:
                print(f"  🚫 {endpoint}: Não encontrado")
            else:
                print(f"  ❓ {endpoint}: {response.status_code}")
                
        except requests.exceptions.RequestException:
            print(f"  ❌ {endpoint}: Erro de conexão")

def main():
    """Função principal"""
    print("🚀 TESTE ESPECÍFICO DA API ZYNTRA")
    print("=" * 60)
    
    if config.ZYNTRA_SECRET_KEY.startswith("sua_chave_"):
        print("❌ AVISO: Você ainda está usando chaves placeholder!")
        print("📝 Para testes reais, substitua as chaves no config.py")
        print("🔄 Continuando com chaves placeholder para teste de estrutura...\n")
    
    # Testa endpoints
    test_zyntra_endpoints()
    
    # Procura documentação
    test_zyntra_documentation_endpoints()
    
    print("\n" + "=" * 60)
    print("🏁 TESTE CONCLUÍDO")
    print("\n📋 ANÁLISE DOS RESULTADOS:")
    print("1. ✅ A API Zyntra existe em: https://api.zyntrapayments.com")
    print("2. 🔐 Ela requer autenticação (erro 401)")
    print("3. 🚫 O endpoint /v1/pix retorna 404 (não existe)")
    print("4. ✅ O endpoint /v1/transactions existe mas requer auth válida")
    print("\n📝 PRÓXIMOS PASSOS:")
    print("1. Obtenha chaves de API reais da Zyntra")
    print("2. Verifique a documentação oficial")
    print("3. Use o endpoint /v1/transactions (não /v1/pix)")
    print("4. Confirme o formato correto de autenticação")

if __name__ == "__main__":
    main()