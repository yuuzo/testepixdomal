#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Teste para Autenticação da API Zyntra

Este script testa diferentes formatos de autenticação para identificar
o método correto da API Zyntra Payments.
"""

import requests
import base64
import json
from datetime import datetime, timedelta
import config

class ZyntraAuthTester:
    def __init__(self):
        self.base_urls = [
            "https://api.zyntrapayments.com",
            "https://api.zyntra.com",
            "https://zyntra.com/api",
            "https://payments.zyntra.com/api"
        ]
        
        self.endpoints = [
            "/v1/transactions",
            "/v1/pix",
            "/v1/payments",
            "/api/v1/transactions",
            "/transactions",
            "/pix"
        ]
        
        self.secret_key = config.ZYNTRA_SECRET_KEY
        self.public_key = config.ZYNTRA_PUBLIC_KEY
        
    def test_basic_auth_variations(self):
        """Testa diferentes variações de Basic Auth"""
        print("\n=== TESTANDO BASIC AUTH VARIATIONS ===")
        
        auth_variations = [
            # Formato 1: secret:x (padrão Stripe-like)
            base64.b64encode(f"{self.secret_key}:x".encode()).decode(),
            
            # Formato 2: secret: (sem senha)
            base64.b64encode(f"{self.secret_key}:".encode()).decode(),
            
            # Formato 3: public:secret
            base64.b64encode(f"{self.public_key}:{self.secret_key}".encode()).decode(),
            
            # Formato 4: secret:public
            base64.b64encode(f"{self.secret_key}:{self.public_key}".encode()).decode(),
            
            # Formato 5: apenas secret
            base64.b64encode(self.secret_key.encode()).decode(),
            
            # Formato 6: apenas public
            base64.b64encode(self.public_key.encode()).decode()
        ]
        
        for i, auth_string in enumerate(auth_variations, 1):
            print(f"\nTeste {i}: Basic {auth_string[:20]}...")
            self._test_auth_method("Basic", auth_string)
    
    def test_bearer_token_variations(self):
        """Testa diferentes variações de Bearer Token"""
        print("\n=== TESTANDO BEARER TOKEN VARIATIONS ===")
        
        bearer_tokens = [
            self.secret_key,
            self.public_key,
            f"{self.secret_key}:{self.public_key}",
            f"{self.public_key}:{self.secret_key}"
        ]
        
        for i, token in enumerate(bearer_tokens, 1):
            print(f"\nTeste {i}: Bearer {token[:20]}...")
            self._test_auth_method("Bearer", token)
    
    def test_api_key_variations(self):
        """Testa diferentes variações de API Key"""
        print("\n=== TESTANDO API KEY VARIATIONS ===")
        
        api_key_headers = [
            {"X-API-Key": self.secret_key},
            {"X-API-Key": self.public_key},
            {"api-key": self.secret_key},
            {"api-key": self.public_key},
            {"Authorization": self.secret_key},
            {"Authorization": self.public_key},
            {"X-Auth-Token": self.secret_key},
            {"X-Auth-Token": self.public_key}
        ]
        
        for i, headers in enumerate(api_key_headers, 1):
            header_name = list(headers.keys())[0]
            header_value = list(headers.values())[0]
            print(f"\nTeste {i}: {header_name}: {header_value[:20]}...")
            self._test_auth_method("API-Key", headers)
    
    def _test_auth_method(self, auth_type, auth_data):
        """Testa um método específico de autenticação"""
        
        # Dados de teste PIX
        test_data = {
            "amount": 100,  # R$ 1,00 em centavos
            "paymentMethod": "pix",
            "customer": {
                "name": "Teste Auth",
                "email": "teste@auth.com",
                "document": "12345678901"
            },
            "items": [{
                "name": "Teste de Autenticação",
                "quantity": 1,
                "amount": 100
            }],
            "pixExpiration": (datetime.now() + timedelta(minutes=30)).isoformat(),
            "webhookUrl": config.WEBHOOK_URL
        }
        
        for base_url in self.base_urls:
            for endpoint in self.endpoints:
                url = f"{base_url}{endpoint}"
                
                # Preparar headers
                headers = {"Content-Type": "application/json"}
                
                if auth_type == "Basic":
                    headers["Authorization"] = f"Basic {auth_data}"
                elif auth_type == "Bearer":
                    headers["Authorization"] = f"Bearer {auth_data}"
                elif auth_type == "API-Key":
                    headers.update(auth_data)
                
                try:
                    response = requests.post(
                        url, 
                        json=test_data, 
                        headers=headers, 
                        timeout=10
                    )
                    
                    print(f"  {url}: {response.status_code}")
                    
                    if response.status_code != 401:
                        print(f"    ✅ SUCESSO! Resposta: {response.text[:100]}...")
                        print(f"    🔑 Método: {auth_type}")
                        print(f"    🌐 URL: {url}")
                        print(f"    📋 Headers: {headers}")
                        return True
                    else:
                        error_msg = response.text[:50] if response.text else "Sem mensagem"
                        print(f"    ❌ 401: {error_msg}...")
                        
                except requests.exceptions.RequestException as e:
                    print(f"  {url}: ❌ Erro de conexão: {str(e)[:50]}...")
                except Exception as e:
                    print(f"  {url}: ❌ Erro: {str(e)[:50]}...")
        
        return False
    
    def test_simple_get_requests(self):
        """Testa requisições GET simples para verificar se a API responde"""
        print("\n=== TESTANDO REQUISIÇÕES GET SIMPLES ===")
        
        get_endpoints = [
            "/",
            "/health",
            "/status",
            "/v1",
            "/api",
            "/docs",
            "/swagger"
        ]
        
        for base_url in self.base_urls:
            print(f"\nTestando {base_url}:")
            for endpoint in get_endpoints:
                url = f"{base_url}{endpoint}"
                try:
                    response = requests.get(url, timeout=5)
                    print(f"  {endpoint}: {response.status_code}")
                    if response.status_code == 200:
                        print(f"    ✅ Resposta: {response.text[:100]}...")
                except requests.exceptions.RequestException as e:
                    print(f"  {endpoint}: ❌ {str(e)[:30]}...")
    
    def run_all_tests(self):
        """Executa todos os testes"""
        print("🔍 INICIANDO TESTES DE AUTENTICAÇÃO DA API ZYNTRA")
        print(f"🔑 Secret Key: {self.secret_key[:10]}...")
        print(f"🔑 Public Key: {self.public_key[:10]}...")
        print("=" * 60)
        
        # Teste requisições GET simples primeiro
        self.test_simple_get_requests()
        
        # Testa diferentes métodos de autenticação
        self.test_basic_auth_variations()
        self.test_bearer_token_variations()
        self.test_api_key_variations()
        
        print("\n" + "=" * 60)
        print("🏁 TESTES CONCLUÍDOS")
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. Se algum teste foi bem-sucedido, use esse método")
        print("2. Se todos falharam, verifique:")
        print("   - As chaves de API estão corretas?")
        print("   - A URL base está correta?")
        print("   - A API Zyntra está funcionando?")
        print("3. Consulte a documentação oficial da Zyntra")
        print("4. Entre em contato com o suporte da Zyntra")

def main():
    """Função principal"""
    if config.ZYNTRA_SECRET_KEY.startswith("sk_live_your_") or config.ZYNTRA_PUBLIC_KEY.startswith("pk_live_your_"):
        print("❌ ERRO: Você ainda está usando chaves placeholder!")
        print("📝 Edite o arquivo config.py e substitua pelas chaves reais da Zyntra.")
        return
    
    tester = ZyntraAuthTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()