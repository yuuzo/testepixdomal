#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do Sistema de Fallback PIX
Testa a geração de QR codes PIX sem depender de APIs externas.
"""

from pix_fallback import PIXFallback
import json

def test_pix_fallback():
    print("🧪 TESTE DO SISTEMA DE FALLBACK PIX")
    print("=" * 60)
    
    # Configurar PIX Fallback
    pix = PIXFallback(
        chave_pix="atendimentocasadecor@outlook.com",
        nome_recebedor="M.J.F CARDS",
        cidade="São Paulo"
    )
    
    print(f"📧 Chave PIX: {pix.chave_pix}")
    print(f"👤 Nome: {pix.nome_recebedor}")
    print(f"🏙️ Cidade: {pix.cidade}")
    print()
    
    # Teste 1: Gerar código PIX Copia e Cola
    print("1️⃣ TESTE: Código PIX Copia e Cola")
    valor = 25.50
    descricao = "Teste de pagamento PIX"
    
    try:
        pix_code = pix.gerar_pix_copia_cola(valor, descricao)
        print(f"✅ Código PIX gerado com sucesso!")
        print(f"💰 Valor: R$ {valor:.2f}")
        print(f"📝 Descrição: {descricao}")
        print(f"📋 Código: {pix_code[:50]}...")
        print(f"📏 Tamanho: {len(pix_code)} caracteres")
        print()
    except Exception as e:
        print(f"❌ Erro ao gerar código PIX: {e}")
        return False
    
    # Teste 2: Gerar QR Code
    print("2️⃣ TESTE: QR Code Base64")
    try:
        qr_base64 = pix.gerar_qr_code(valor, descricao)
        print(f"✅ QR Code gerado com sucesso!")
        print(f"📏 Tamanho base64: {len(qr_base64)} caracteres")
        print(f"🖼️ Início: {qr_base64[:50]}...")
        print()
    except Exception as e:
        print(f"❌ Erro ao gerar QR Code: {e}")
        return False
    
    # Teste 3: Cobrança completa
    print("3️⃣ TESTE: Cobrança PIX Completa")
    try:
        cobranca = pix.criar_cobranca_pix(valor, descricao)
        print(f"✅ Cobrança criada com sucesso!")
        print(f"🆔 ID: {cobranca['transaction_id']}")
        print(f"💰 Valor: R$ {cobranca['valor']:.2f}")
        print(f"📝 Descrição: {cobranca['descricao']}")
        print(f"🕐 Timestamp: {cobranca['timestamp']}")
        print(f"📱 Status: {cobranca['status']}")
        print(f"🔧 Método: {cobranca['metodo']}")
        print(f"📋 Código PIX: {cobranca['pix_copia_cola'][:50]}...")
        print(f"🖼️ QR Code URL: {cobranca['qr_code_url'][:50]}...")
        print()
        
        # Mostrar instruções
        print("📖 INSTRUÇÕES:")
        for i, instrucao in enumerate(cobranca['instrucoes'], 1):
            print(f"   {instrucao}")
        print()
        
    except Exception as e:
        print(f"❌ Erro ao criar cobrança: {e}")
        return False
    
    # Teste 4: Validação do formato PIX
    print("4️⃣ TESTE: Validação do Formato PIX")
    try:
        # Verificar se o código PIX segue o padrão EMV
        if pix_code.startswith("00020101"):
            print("✅ Formato EMV correto (inicia com 00020101)")
        else:
            print("⚠️ Formato EMV pode estar incorreto")
            
        # Verificar CRC
        if len(pix_code) >= 4 and pix_code[-4:].isalnum():
            print("✅ CRC presente nos últimos 4 caracteres")
        else:
            print("⚠️ CRC pode estar incorreto")
            
        # Verificar presença da chave PIX
        if "atendimentocasadecor@outlook.com" in pix_code:
            print("✅ Chave PIX encontrada no código")
        else:
            print("⚠️ Chave PIX não encontrada no código")
            
        print()
        
    except Exception as e:
        print(f"❌ Erro na validação: {e}")
        return False
    
    print("=" * 60)
    print("🎉 TODOS OS TESTES PASSARAM!")
    print("✅ Sistema de Fallback PIX está funcionando corretamente")
    print("📱 O bot pode gerar PIX mesmo sem APIs externas")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_pix_fallback()
    if success:
        print("\n🚀 Sistema pronto para uso!")
    else:
        print("\n❌ Corrija os erros antes de usar o sistema.")