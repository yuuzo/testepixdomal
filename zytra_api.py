import requests
import json
import logging
import uuid
from datetime import datetime, timedelta
import config
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ZytraPayments:
    def __init__(self, user: str, password: str):
        self.user = user
        self.password = password
        self.base_url = "https://api.zyntrapayments.com/v1"
        # Usar Basic Authentication com usuário e senha
        import base64
        auth_string = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Basic {auth_string}"
        }
    
    def create_pix_charge(self, amount, description, customer_info=None):
        """
        Cria uma cobrança PIX na Zytra Payments
        
        Args:
            amount (float): Valor da cobrança em reais
            description (str): Descrição da cobrança
            customer_info (dict): Informações do cliente (opcional)
        
        Returns:
            dict: Resposta da API com dados da cobrança
        """
        try:
            # Gerar ID único para a cobrança
            charge_id = str(uuid.uuid4())
            
            # Dados da transação PIX conforme exemplo fornecido pelo dono da Zyntra
            charge_data = {
                "amount": int(amount * 100),  # Valor em centavos
                "paymentMethod": "pix",
                "customer": {
                    "name": customer_info.get("name", config.DEFAULT_CUSTOMER_NAME) if customer_info else config.DEFAULT_CUSTOMER_NAME,
                    "email": customer_info.get("email", config.DEFAULT_CUSTOMER_EMAIL) if customer_info else config.DEFAULT_CUSTOMER_EMAIL,
                    "phone": customer_info.get("phone", "11999999999") if customer_info else "11999999999",
                    "document": {
                        "number": customer_info.get("document", "11144477735") if customer_info else "11144477735",
                        "type": "cpf"
                    },
                    "address": {
                        "street": customer_info.get("street", "Rua Exemplo") if customer_info else "Rua Exemplo",
                        "streetNumber": customer_info.get("streetNumber", "123") if customer_info else "123",
                        "complement": customer_info.get("complement", "") if customer_info else "",
                        "zipCode": customer_info.get("zipCode", "01234567") if customer_info else "01234567",
                        "neighborhood": customer_info.get("neighborhood", "Centro") if customer_info else "Centro",
                        "city": customer_info.get("city", "São Paulo") if customer_info else "São Paulo",
                        "state": customer_info.get("state", "SP") if customer_info else "SP",
                        "country": "BR"
                    }
                },
                "items": [
                    {
                        "title": description,
                        "unitPrice": int(amount * 100),
                        "quantity": 1,
                        "tangible": False
                    }
                ]
            }
            
            # Adicionar webhook se configurado
            if hasattr(config, 'WEBHOOK_URL') and config.WEBHOOK_URL:
                charge_data["webhook"] = {
                    "url": config.WEBHOOK_URL
                }
            
            # Adicionar informações do cliente se fornecidas (preservando estrutura do documento)
            if customer_info:
                # Salvar estrutura do documento antes de atualizar
                document_structure = charge_data["customer"]["document"]
                charge_data["customer"].update(customer_info)
                # Restaurar estrutura correta do documento se foi sobrescrita
                if "document" in customer_info and isinstance(customer_info["document"], str):
                    charge_data["customer"]["document"] = {
                        "number": customer_info["document"],
                        "type": "cpf"
                    }
                elif "document" not in customer_info:
                    charge_data["customer"]["document"] = document_structure
            
            # Verificar se está em modo de demonstração
            if config.DEMO_MODE:
                logger.info("Modo demonstração ativado - gerando dados fictícios")
                return {
                    "success": True,
                    "charge_id": charge_id,
                    "qr_code": "00020126580014br.gov.bcb.pix0136123e4567-e12b-12d3-a456-426614174000520400005303986540510.005802BR5913LOJA EXEMPLO6009SAO PAULO62070503***6304A1B2",
                    "qr_code_image": f"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                    "amount": amount,
                    "description": description,
                    "expires_at": (datetime.now() + timedelta(hours=config.PIX_EXPIRATION_HOURS)).isoformat(),
                    "status": "pending",
                    "payment_url": f"https://pay.zyntra.com/pix/{charge_id}",
                    "webhook_url": config.WEBHOOK_URL
                }
            
            logger.info(f"Criando cobrança PIX: {json.dumps(charge_data, indent=2)}")
            
            # Fazer requisição para criar transação conforme documentação
            url = f"{self.base_url}/transactions"
            logger.info(f"Criando transação PIX: {url}")
            logger.info(f"Dados: {json.dumps(charge_data, indent=2)}")
            
            response = requests.post(url, json=charge_data, headers=self.headers, timeout=30)
            
            logger.info(f"Resposta da API Zytra: Status {response.status_code}")
            logger.info(f"Resposta da API Zytra: {response.text}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                # Extrair QR code PIX conforme estrutura da resposta da Zyntra
                qr_code = None
                if "pix" in result and "qrcode" in result["pix"]:
                    qr_code = result["pix"]["qrcode"]
                
                return {
                    "success": True,
                    "charge_id": result.get("id", charge_id),
                    "qr_code": qr_code,
                    "qr_code_text": qr_code,  # O mesmo código serve para copia e cola
                    "amount": amount,
                    "status": result.get("status", "waiting_payment"),
                    "expires_at": result.get("pix", {}).get("expirationDate") if "pix" in result else None,
                    "secure_url": result.get("secureUrl"),
                    "charge_data": result
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code} - {response.text}"
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão com API Zytra: {e}")
            return {
                "success": False,
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Erro ao criar cobrança PIX: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def get_charge_status(self, charge_id):
        """
        Consulta o status de uma cobrança
        
        Args:
            charge_id (str): ID da cobrança
        
        Returns:
            dict: Status da cobrança
        """
        try:
            response = requests.get(
                f"{self.base_url}/charges/{charge_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Erro ao consultar status da cobrança: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_qr_code_data(self, charge_data):
        """
        Extrai dados do QR Code da resposta da API
        
        Args:
            charge_data (dict): Dados da cobrança retornados pela API
        
        Returns:
            dict: Dados do QR Code
        """
        try:
            # Tentar extrair QR code de diferentes possíveis estruturas de resposta
            qr_code = None
            qr_code_base64 = None
            
            # Possíveis caminhos para o QR code na resposta
            possible_paths = [
                ['qr_code'],
                ['pix', 'qr_code'],
                ['payment_method', 'pix', 'qr_code'],
                ['data', 'qr_code'],
                ['charge', 'qr_code']
            ]
            
            for path in possible_paths:
                current = charge_data
                try:
                    for key in path:
                        current = current[key]
                    qr_code = current
                    break
                except (KeyError, TypeError):
                    continue
            
            # Tentar extrair QR code em base64
            possible_base64_paths = [
                ['qr_code_base64'],
                ['pix', 'qr_code_base64'],
                ['payment_method', 'pix', 'qr_code_base64']
            ]
            
            for path in possible_base64_paths:
                current = charge_data
                try:
                    for key in path:
                        current = current[key]
                    qr_code_base64 = current
                    break
                except (KeyError, TypeError):
                    continue
            
            return {
                "qr_code": qr_code,
                "qr_code_base64": qr_code_base64,
                "has_qr_code": bool(qr_code or qr_code_base64)
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do QR Code: {e}")
            return {
                "qr_code": None,
                "qr_code_base64": None,
                "has_qr_code": False,
                "error": str(e)
            }

# Função auxiliar para criar instância da API
def create_zytra_client():
    """Cria cliente da API Zyntra com as credenciais configuradas"""
    return ZytraPayments(config.ZYNTRA_USER, config.ZYNTRA_PASSWORD)

# Função de teste
if __name__ == "__main__":
    # Teste básico da API
    client = create_zytra_client()
    
    # Testar criação de cobrança
    result = client.create_pix_charge(
        amount=10.50,
        description="Teste de cobrança PIX",
        customer_info={
            "name": "Teste Cliente",
            "email": "teste@exemplo.com"
        }
    )
    
    print("Resultado do teste:")
    print(json.dumps(result, indent=2, ensure_ascii=False))