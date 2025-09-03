# Configurações da API Zyntra Payments
# Para obter suas chaves da API:
# 1. Acesse o painel da Zyntra Payments
# 2. Vá em Configurações > API Keys
# 3. Copie suas chaves e cole abaixo

# IMPORTANTE: Credenciais corretas da Zyntra
ZYNTRA_USER = "atendimentocasadecor@outlook.com"  # Usuário da Zyntra
ZYNTRA_PASSWORD = "loki23"  # Senha da Zyntra
# Manter as chaves antigas como backup
ZYNTRA_SECRET_KEY = "sk_live_v22ZRTDZQjPsOWlh7EEOEgYrW3dcxfMjuUDHHyj8Gg"  # Sua chave secreta da Zyntra
ZYNTRA_PUBLIC_KEY = "pk_live_v2BeWQ5kzTiOxcChXfBJSy149rMqFrr8o4"  # Sua chave pública da Zyntra

# URL base da API (pode variar conforme a documentação)
ZYNTRA_BASE_URL = "https://api.zyntrapayments.com/v1"

# Configurações do webhook
WEBHOOK_URL = "https://fda20b32aac2.ngrok-free.app/webhook/zytra"

# Modo de demonstração (True = usar dados fictícios, False = usar API real)
DEMO_MODE = False

# Configurações do PIX
PIX_CHAVE = "atendimentocasadecor@outlook.com"  # Chave PIX para fallback
PIX_EXPIRATION_HOURS = 24
DEFAULT_CUSTOMER_NAME = "Cliente Telegram"
DEFAULT_CUSTOMER_EMAIL = "cliente@exemplo.com"
DEFAULT_CUSTOMER_DOCUMENT = "00000000000"