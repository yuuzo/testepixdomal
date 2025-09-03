# Sistema PIX para Telegram Bot

Este sistema permite gerar cobranças PIX através de um bot do Telegram integrado com a API da Zyntra Payments.

## 📋 Configuração

### 1. Configurar as Chaves da API

Edite o arquivo `config.py` e substitua as chaves pelos valores reais da sua conta Zyntra:

```python
# Suas chaves reais da Zyntra Payments
ZYNTRA_SECRET_KEY = "sk_live_sua_chave_secreta_aqui"
ZYNTRA_PUBLIC_KEY = "pk_live_sua_chave_publica_aqui"

# Para usar o sistema real, altere para False
DEMO_MODE = False
```

### 2. Como Obter as Chaves da Zyntra

1. Acesse o painel da Zyntra Payments
2. Vá em **Configurações** > **API Keys**
3. Copie sua **Secret Key** (sk_live_...)
4. Copie sua **Public Key** (pk_live_...)
5. Cole as chaves no arquivo `config.py`

### 3. Configurar o Webhook

1. Mantenha o ngrok rodando: `ngrok http 5000`
2. Copie a URL do ngrok (ex: `https://abc123.ngrok-free.app`)
3. No painel da Zyntra, configure o webhook para: `https://abc123.ngrok-free.app/webhook/zytra`
4. Atualize a URL no arquivo `config.py`:

```python
WEBHOOK_URL = "https://sua_url_ngrok.ngrok-free.app/webhook/zytra"
```

## 🚀 Como Usar

### Comandos do Bot

1. **Iniciar o bot**: `/start`
2. **Gerar PIX**: `/pix 25.50 Descrição do pagamento`

### Exemplo de Uso

```
/pix 15.75 Compra de produto
```

O bot irá retornar:
- QR Code para pagamento
- Código PIX para copiar e colar
- Link de pagamento
- Informações da cobrança

## 🔧 Executar o Sistema

### 1. Iniciar o Servidor Webhook

```bash
python webhook_server.py
```

### 2. Iniciar o Ngrok

```bash
ngrok http 5000
```

### 3. Iniciar o Bot do Telegram

```bash
python bot.py
```

## 🧪 Modo de Demonstração

Por padrão, o sistema está em modo de demonstração (`DEMO_MODE = True`). Neste modo:

- ✅ Não faz chamadas reais para a API
- ✅ Gera dados fictícios para teste
- ✅ Permite testar toda a funcionalidade
- ✅ QR codes e links funcionais para demonstração

Para usar a API real:
1. Configure suas chaves reais no `config.py`
2. Altere `DEMO_MODE = False`
3. Reinicie o sistema

## 📁 Estrutura dos Arquivos

- `bot.py` - Bot principal do Telegram
- `zytra_api.py` - Integração com API da Zyntra
- `webhook_server.py` - Servidor para receber webhooks
- `config.py` - Configurações do sistema
- `.env` - Token do bot do Telegram

## 🔍 Logs e Debugging

Todos os logs são exibidos no terminal. Para debugar:

1. Verifique os logs do webhook server
2. Verifique os logs do bot
3. Teste a API diretamente:

```python
from zytra_api import create_zytra_client
client = create_zytra_client()
result = client.create_pix_charge(10.50, "Teste")
print(result)
```

## ⚠️ Importante

- Mantenha o ngrok sempre rodando
- A URL do ngrok muda a cada reinicialização
- Atualize o webhook na Zyntra quando a URL mudar
- Nunca compartilhe suas chaves da API
- Use HTTPS sempre em produção

## 🆘 Solução de Problemas

### Erro "Token inválido"
- Verifique se as chaves estão corretas no `config.py`
- Confirme se está usando as chaves da conta correta
- Teste primeiro em modo demonstração

### Bot não responde
- Verifique se apenas uma instância está rodando
- Confirme se o token do bot está correto no `.env`
- Reinicie o bot se necessário

### Webhook não funciona
- Verifique se o ngrok está rodando
- Confirme se a URL está atualizada na Zyntra
- Teste o endpoint: `curl https://sua_url.ngrok-free.app/webhook/zytra`

## 📞 Suporte

Para problemas específicos da API Zyntra, consulte:
- Documentação: https://zyntra.readme.io/
- Suporte da Zyntra Payments