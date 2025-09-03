import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import base64

# Configurações da Zyntra API
ZYNTRA_API_URL = "https://api.zyntrapayments.com/v1/transactions"
ZYNTRA_SECRET_KEY = "sk_live_v22ZRTDZQjPsOWlh7EEOEgYrW3dcxfMjuUDHHyj8Gg"

# Configurações do Telegram Bot
TELEGRAM_BOT_TOKEN = "8359368509:AAH_MYjiDurBD64VqAmbj-demIHa3CJ1Z-s"

# Habilitar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def generate_basic_auth_string(secret_key: str) -> str:
    """Gera a string de autorização Basic para a Zyntra API."""
    auth_string = f"{secret_key}:x"
    encoded_auth_string = base64.b64encode(auth_string.encode("ascii")).decode("ascii")
    return f"Basic {encoded_auth_string}"

AUTH_HEADER = generate_basic_auth_string(ZYNTRA_SECRET_KEY)

async def start(update: Update, context) -> None:
    """Envia uma mensagem quando o comando /start é emitido."""
    user = update.effective_user
    await update.message.reply_html(
        f"Olá {user.mention_html()}!\nEu sou um bot que gera pagamentos PIX via Zyntra. "
        "Use o comando /pix <valor> [descrição] para gerar um PIX.\n" 
        "Exemplo: /pix 10.50 ou /pix 10.50 CompraDeProduto",
    )

async def help_command(update: Update, context) -> None:
    """Envia uma mensagem quando o comando /help é emitido."""
    await update.message.reply_text(
        "Use o comando /pix <valor> [descrição] para gerar um PIX.\n" 
        "Exemplo: /pix 10.50 ou /pix 10.50 CompraDeProduto"
    )

async def generate_pix(update: Update, context) -> None:
    """Gera um pagamento PIX usando a API Zyntra."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "Uso incorreto. Por favor, use: /pix <valor> [descrição]\n" 
            "Exemplo: /pix 10.50 ou /pix 10.50 CompraDeProduto"
        )
        return

    try:
        amount_str = args[0].replace(",", ".")
        amount = int(float(amount_str) * 100)  # Converter para centavos
        description = "Pagamento PIX" # Descrição padrão
        if len(args) > 1:
            description = " ".join(args[1:])
    except ValueError:
        await update.message.reply_text("Valor inválido. Por favor, insira um número válido (ex: 10.50).")
        return

    if amount <= 0:
        await update.message.reply_text("O valor deve ser maior que zero.")
        return

    # Dados do cliente (fictícios, mas completos como no curl que funcionou)
    customer_data = {
        "document": {
            "number": "10850239400", # CPF fictício
            "type": "cpf"
        },
        "name": update.effective_user.full_name or "Cliente Teste",
        "email": f"user_{update.effective_user.id}@example.com", 
        "phone": "21983021324" # Telefone fictício
    }

    # Dados de shipping (fictícios, mas completos como no curl que funcionou)
    shipping_data = {
        "address": {
            "street": "Rua Ficticia",
            "streetNumber": "123",
            "zipCode": "58073175",
            "complement": "Apto 101",
            "neighborhood": "Bairro Teste",
            "city": "Cidade Teste",
            "state": "PB",
            "country": "br"
        }
    }

    # Dados da transação PIX
    payload = {
        "amount": amount,
        "paymentMethod": "pix",
        "customer": customer_data,
        "shipping": shipping_data, 
        "items": [
            {
                "title": description,
                "unitPrice": amount,
                "quantity": 1,
                "tangible": False
            }
        ],
        "pix": {
            "expiresInDays": 1 # PIX válido por 1 dia
        }
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": AUTH_HEADER # AUTH_HEADER já inclui "Basic "
    }

    try:
        # Removendo verify=False para voltar ao comportamento padrão de verificação SSL
        response = requests.post(ZYNTRA_API_URL, json=payload, headers=headers)
        response.raise_for_status()  # Levanta um erro para códigos de status HTTP ruins (4xx ou 5xx)
        transaction_data = response.json()

        if transaction_data and transaction_data.get("pix"):
            pix_qrcode = transaction_data["pix"].get("qrcode")
            pix_url = transaction_data["pix"].get("url")
            
            message = f"PIX gerado com sucesso para {description} no valor de R$ {amount/100:.2f}!\n\n"
            if pix_qrcode:
                message += f"QR Code PIX: {pix_qrcode}\n"
            if pix_url:
                message += f"Link para pagamento: {pix_url}\n"
            
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("Erro ao gerar PIX: Resposta da API inválida ou sem dados PIX.")
            logger.error(f"Resposta da API Zyntra inválida: {transaction_data}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição para a API Zyntra: {e}")
        await update.message.reply_text(
            f"Ocorreu um erro ao tentar gerar o PIX. Por favor, tente novamente mais tarde. Erro: {e}"
        )
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        await update.message.reply_text(
            f"Ocorreu um erro inesperado. Por favor, tente novamente mais tarde. Erro: {e}"
        )

def main() -> None:
    """Inicia o bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("pix", generate_pix))

    logger.info("Bot do Telegram iniciado. Pressione Ctrl+C para parar.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
