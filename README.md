# Bot Telegram - Catálogo de Códigos

Bot Telegram para venda de códigos com sistema de pagamento PIX integrado à Zyntra Payments.

## Deploy no VPS via GitHub

### 1. Preparação Local

1. Crie um repositório no GitHub
2. Faça upload dos arquivos do bot
3. Configure as variáveis de ambiente

### 2. Configuração no VPS

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python e Git
sudo apt install python3 python3-pip git -y

# Clonar o repositório
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
cd SEU_REPOSITORIO

# Instalar dependências
pip3 install -r requirements.txt

# Configurar variáveis de ambiente
nano .env
```

### 3. Arquivo .env

Crie o arquivo `.env` com:

```
BOT_TOKEN=seu_token_do_bot
ZYNTRA_API_URL=https://api.zyntra.com
ZYNTRA_SECRET_KEY=sua_chave_secreta
```

### 4. Executar o Bot

```bash
# Executar em background
nohup python3 bot.py > bot.log 2>&1 &

# Ou usar screen para sessão persistente
screen -S bot
python3 bot.py
# Ctrl+A+D para sair sem parar o bot
```

### 5. Verificar Status

```bash
# Ver logs
tail -f bot.log

# Ver processos
ps aux | grep python

# Reconectar ao screen
screen -r bot
```

### 6. Atualizações

```bash
# Parar o bot
pkill -f bot.py

# Atualizar código
git pull origin main

# Reiniciar
nohup python3 bot.py > bot.log 2>&1 &
```

## Estrutura do Projeto

- `bot.py` - Arquivo principal do bot
- `catalog.txt` - Catálogo de códigos
- `config.py` - Configurações
- `zytra_api.py` - Integração com Zyntra
- `pix_fallback.py` - Sistema de fallback PIX
- `.env` - Variáveis de ambiente (não incluir no Git)
- `requirements.txt` - Dependências Python

## Funcionalidades

- ✅ Catálogo de códigos por tipo/subtipo
- ✅ Sistema de saldo de usuários
- ✅ Pagamentos PIX via Zyntra
- ✅ Histórico de compras
- ✅ Sistema de fallback PIX
- ✅ Webhook para confirmação de pagamentos

## Suporte

Para dúvidas ou problemas, consulte os logs do bot ou entre em contato.