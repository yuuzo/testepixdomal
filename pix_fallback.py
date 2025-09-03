import qrcode
import io
import base64
from datetime import datetime
import uuid
import json
from typing import Dict, Any, Optional

class PIXFallback:
    """
    Sistema de fallback para PIX que funciona independentemente de APIs externas.
    Gera QR codes PIX válidos usando o padrão brasileiro.
    """
    
    def __init__(self, chave_pix: str, nome_recebedor: str, cidade: str = "São Paulo"):
        self.chave_pix = chave_pix
        self.nome_recebedor = nome_recebedor
        self.cidade = cidade
        
    def gerar_pix_copia_cola(self, valor: float, descricao: str = "", txid: str = None) -> str:
        """
        Gera o código PIX Copia e Cola seguindo o padrão EMV.
        """
        if not txid:
            txid = str(uuid.uuid4())[:25]  # Máximo 25 caracteres
            
        # Formatação do valor (sempre com 2 casas decimais)
        valor_str = f"{valor:.2f}"
        
        # Construção do payload PIX
        payload = ""
        
        # Payload Format Indicator
        payload += "000201"  # 00 = ID, 02 = tamanho, 01 = versão
        
        # Point of Initiation Method
        payload += "010212"  # 01 = ID, 02 = tamanho, 12 = dinâmico
        
        # Merchant Account Information
        merchant_info = ""
        merchant_info += "0014br.gov.bcb.pix"  # 00 = ID, 14 = tamanho, br.gov.bcb.pix
        merchant_info += f"01{len(self.chave_pix):02d}{self.chave_pix}"  # 01 = ID, chave PIX
        
        if descricao:
            merchant_info += f"02{len(descricao):02d}{descricao}"  # 02 = ID, descrição
            
        payload += f"26{len(merchant_info):02d}{merchant_info}"  # 26 = ID, merchant info
        
        # Merchant Category Code
        payload += "52040000"  # 52 = ID, 04 = tamanho, 0000 = categoria
        
        # Transaction Currency
        payload += "5303986"  # 53 = ID, 03 = tamanho, 986 = BRL
        
        # Transaction Amount
        payload += f"54{len(valor_str):02d}{valor_str}"
        
        # Country Code
        payload += "5802BR"  # 58 = ID, 02 = tamanho, BR
        
        # Merchant Name
        nome_truncado = self.nome_recebedor[:25]  # Máximo 25 caracteres
        payload += f"59{len(nome_truncado):02d}{nome_truncado}"
        
        # Merchant City
        cidade_truncada = self.cidade[:15]  # Máximo 15 caracteres
        payload += f"60{len(cidade_truncada):02d}{cidade_truncada}"
        
        # Additional Data Field Template
        if txid:
            additional_data = f"05{len(txid):02d}{txid}"  # 05 = ID, txid
            payload += f"62{len(additional_data):02d}{additional_data}"
        
        # CRC16 (será calculado)
        payload += "6304"
        
        # Calcular CRC16
        crc = self._calcular_crc16(payload)
        payload += f"{crc:04X}"
        
        return payload
    
    def _calcular_crc16(self, payload: str) -> int:
        """
        Calcula o CRC16 para o payload PIX.
        """
        crc = 0xFFFF
        for char in payload:
            crc ^= ord(char) << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc
    
    def gerar_qr_code(self, valor: float, descricao: str = "", txid: str = None) -> str:
        """
        Gera QR code PIX e retorna como base64.
        """
        pix_code = self.gerar_pix_copia_cola(valor, descricao, txid)
        
        # Criar QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(pix_code)
        qr.make(fit=True)
        
        # Converter para imagem
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converter para base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return img_base64
    
    def criar_cobranca_pix(self, valor: float, descricao: str = "") -> Dict[str, Any]:
        """
        Cria uma cobrança PIX completa com QR code e informações.
        """
        txid = str(uuid.uuid4())[:25]
        timestamp = datetime.now().isoformat()
        
        # Gerar códigos PIX
        pix_copia_cola = self.gerar_pix_copia_cola(valor, descricao, txid)
        qr_code_base64 = self.gerar_qr_code(valor, descricao, txid)
        
        return {
            "success": True,
            "transaction_id": txid,
            "timestamp": timestamp,
            "valor": valor,
            "descricao": descricao,
            "chave_pix": self.chave_pix,
            "nome_recebedor": self.nome_recebedor,
            "cidade": self.cidade,
            "pix_copia_cola": pix_copia_cola,
            "qr_code_base64": qr_code_base64,
            "qr_code_url": f"data:image/png;base64,{qr_code_base64}",
            "status": "pending",
            "metodo": "pix_fallback",
            "instrucoes": [
                "1. Abra o app do seu banco",
                "2. Escolha a opção PIX",
                "3. Escaneie o QR code ou cole o código",
                "4. Confirme o pagamento"
            ]
        }

# Exemplo de uso
if __name__ == "__main__":
    # Configuração de exemplo
    pix = PIXFallback(
        chave_pix="exemplo@email.com",
        nome_recebedor="Loja Exemplo",
        cidade="São Paulo"
    )
    
    # Criar cobrança
    cobranca = pix.criar_cobranca_pix(25.50, "Pagamento teste")
    
    print("=== COBRANÇA PIX GERADA ===")
    print(f"ID: {cobranca['transaction_id']}")
    print(f"Valor: R$ {cobranca['valor']:.2f}")
    print(f"Descrição: {cobranca['descricao']}")
    print(f"\nCódigo PIX Copia e Cola:")
    print(cobranca['pix_copia_cola'])
    print(f"\nQR Code gerado com sucesso!")