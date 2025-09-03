# bot.py — Catálogo com /inicial (prefixo) e /tipo (por tipo), banner como foto, viewer com compra
# python-telegram-bot==20.7 | Python 3.12

import os
import sys
import re
import logging
from io import BytesIO
from collections import defaultdict
from typing import Dict, List, Tuple
from dotenv import load_dotenv
import requests  # para envio resiliente do banner
import json  # <-- ADICIONADO
import time
import sqlite3
import uuid
import base64  # <-- ADICIONADO para autenticação Zyntra
from datetime import datetime

try:
    import qrcode  # opcional, para /pix gerar QR de teste
except Exception:
    qrcode = None

# Importar módulo da API Zytra
try:
    from zytra_api import create_zytra_client
except ImportError:
    create_zytra_client = None
    logging.warning("Módulo zytra_api não encontrado. Funcionalidade PIX limitada.")

# Importar sistema de fallback PIX
try:
    from pix_fallback import PIXFallback
except ImportError:
    PIXFallback = None
    logging.warning("Módulo pix_fallback não encontrado. Fallback PIX desabilitado.")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

# =============== LOG ===============
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("bot")

# =============== TOKEN ===============
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
# TOKEN = "SEU_TOKEN_AQUI"
if not TOKEN or ":" not in TOKEN:
    log.error("BOT_TOKEN não encontrado/ inválido. Crie .env com: BOT_TOKEN=123:AA...seu_token")
    sys.exit(1)

# =============== CAMINHOS ===============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_TXT = os.path.join(BASE_DIR, "catalog.txt")
BALANCE_FILE = os.path.join(BASE_DIR, "user_balance.json")  # <-- NOVO
HISTORY_FILE = os.path.join(BASE_DIR, "user_history.json")  # <-- NOVO
SOLD_CODES_FILE = os.path.join(BASE_DIR, "sold_codes.json")  # <-- NOVO para rastrear códigos vendidos

# =============== CONSTANTES/UTILS ===============
PAD = "\u200B" * 60  # padding invisível (mantém botões largos)
# Use um link direto (.png/.jpg) OU um arquivo local (ex.: "banner.png")
IMG_URL = "https://anonpic.org/image.php?di=87FN"  # Imagem M.J.F CARDS via link externo
GROUP_LINK   = "https://t.me/SEU_GRUPO" # <-- troque
SUPPORT_LINK = "https://t.me/SEU_SUPORTE"
NEWS_LINK    = "https://t.me/SEU_CANAL"
PIX_CHAVE    = "SUA_CHAVE_PIX@exemplo.com"
# Troque aqui para o @ do seu suporte/grupo/canal
SUPORTE_AT = "@telegram"
GRUPO_AT = "@telegram"
CANAL_AT = "@telegram"

def money(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def mask_code(code: str) -> str:
    # Máscara simples: revela 6 primeiros, resto *
    if not code: return code
    return code[:6] + ("*" * max(0, len(code) - 6))

def mask_code_str(code: str) -> str:
    # Alias para compatibilidade
    return mask_code(code)

def mask_code_in_text(raw: str, code: str) -> str:
    return raw.replace(code, mask_code_str(code), 1)

# =============== PARSER DO catalog.txt ===============
RE_CODE     = re.compile(r"^\s*codigo\s*>\s*([0-9A-Za-z]+)", re.IGNORECASE | re.MULTILINE)
RE_TIPO     = re.compile(r"^\s*(tipo|ra[cç]a)\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
RE_SUBTIPO  = re.compile(r"^\s*subtipo\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
RE_DISP     = re.compile(r"^\s*dispon[ií]vel\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
RE_PRECO    = re.compile(r"^\s*pre[cç]o\s*:\s*([0-9]+(?:[.,][0-9]+)?)", re.IGNORECASE | re.MULTILINE)

def parse_bool(s: str) -> bool:
    s = (s or "").strip().lower()
    return s in {"sim","true","1","yes","y","ok"}

def norm_price(s: str) -> float:
    if not s: return 0.0
    s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0

class Catalog:
    def __init__(self):
        self.items: List[Dict] = []
        self.types_price: Dict[str, float] = {}
        self.subtypes_by_type: Dict[str, List[str]] = {}
        self.codes_by_pair: Dict[Tuple[str, str], List[Dict]] = {}

    def load(self, path: str):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo {path} não encontrado.")
        raw_all = open(path, "r", encoding="utf-8").read()
        blocks = [b.strip() for b in raw_all.split("---") if b.strip()]

        items: List[Dict] = []
        for blk in blocks:
            m_code = RE_CODE.search(blk)
            m_tipo = RE_TIPO.search(blk)
            m_sub  = RE_SUBTIPO.search(blk)
            if not (m_code and m_tipo and m_sub):
                continue

            code = m_code.group(1).strip()
            tipo = m_tipo.group(2).strip()  # valor (não o rótulo)
            sub  = m_sub.group(1).strip()

            m_disp = RE_DISP.search(blk)
            disponivel = True if m_disp is None else parse_bool(m_disp.group(1))

            m_preco = RE_PRECO.search(blk)
            preco = norm_price(m_preco.group(1) if m_preco else "")

            items.append({
                "type": tipo,
                "subtype": sub,
                "code": code,
                "available": disponivel,
                "price": preco,
                "raw": blk
            })

        types_price: Dict[str, float] = {}
        subtypes_set: Dict[str, set] = defaultdict(set)
        codes_by_pair: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)

        for it in items:
            if it["available"]:
                codes_by_pair[(it["type"], it["subtype"])].append(it)
                subtypes_set[it["type"]].add(it["subtype"])
            if it["price"] > 0:
                types_price[it["type"]] = max(types_price.get(it["type"], 0.0), it["price"])

        for key in codes_by_pair:
            codes_by_pair[key].sort(key=lambda d: (d["type"], d["subtype"], d["code"]))

        self.items = items
        self.types_price = types_price
        self.subtypes_by_type = {t: sorted(list(v)) for t, v in subtypes_set.items()}
        self.codes_by_pair = codes_by_pair

        log.info("Catálogo: %d blocos lidos, %d pares tipo/subtipo com disponibilidade.",
                 len(items), len(self.codes_by_pair))

    def get_types_sorted(self) -> List[Tuple[str, float]]:
        valid_types = sorted({t for (t, _) in self.codes_by_pair.keys()})
        return [(t, float(self.types_price.get(t, 0.0))) for t in valid_types]

    def get_subtypes(self, type_name: str) -> List[str]:
        return self.subtypes_by_type.get(type_name, [])

    def get_codes(self, type_name: str, subtype: str) -> List[Dict]:
        # Obter todos os códigos para o par tipo/subtipo
        result = self.codes_by_pair.get((type_name, subtype), [])
        
        log.info(f"get_codes({type_name}, {subtype}) -> {len(result)} itens")
        return result
        
    def mark_code_as_sold(self, code: str):
        """Marca um código como vendido e remove fisicamente do catalog.txt"""
        for item in self.items:
            if item["code"] == code and item["available"]:
                item["available"] = False
                log.info(f"Código {code} marcado como vendido")
                
                # Remover o item da lista de códigos disponíveis
                type_name = item["type"]
                subtype = item["subtype"]
                pair_key = (type_name, subtype)
                
                # Remover o item da lista de códigos disponíveis para o par tipo/subtipo
                if pair_key in self.codes_by_pair:
                    self.codes_by_pair[pair_key] = [it for it in self.codes_by_pair[pair_key] if it["code"] != code]
                    
                    # Se não houver mais códigos para este par, remover o subtipo da lista
                    if not self.codes_by_pair[pair_key]:
                        if type_name in self.subtypes_by_type:
                            self.subtypes_by_type[type_name] = [s for s in self.subtypes_by_type[type_name] if s != subtype]
                            
                            # Se não houver mais subtipos para este tipo, remover o tipo da lista de preços
                            if not self.subtypes_by_type[type_name]:
                                if type_name in self.types_price:
                                    del self.types_price[type_name]
                
                # Remover fisicamente do arquivo catalog.txt
                self._remove_code_from_file(code)
                                    
                return True
        return False
    
    def _remove_code_from_file(self, code: str):
        """Remove um código fisicamente do arquivo catalog.txt"""
        try:
            with open(CATALOG_TXT, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Encontrar e remover o bloco do código
            lines = content.split('\n')
            new_lines = []
            skip_block = False
            
            for line in lines:
                if line.strip().startswith(f"codigo> {code}"):
                    skip_block = True
                    continue
                elif line.strip() == "---" and skip_block:
                    skip_block = False
                    continue
                elif not skip_block:
                    new_lines.append(line)
            
            # Reescrever o arquivo sem o código vendido
            with open(CATALOG_TXT, "w", encoding="utf-8") as f:
                f.write('\n'.join(new_lines))
            
            log.info(f"Código {code} removido fisicamente do catalog.txt")
            
        except Exception as e:
            log.error(f"Erro ao remover código {code} do arquivo: {e}")

CATALOG = Catalog()
CATALOG.load(CATALOG_TXT)

# =============== SALDO (persistente) ===============
USER_BALANCE: Dict[int, float] = {}
USER_HISTORY: Dict[int, List[Dict]] = {}  # <-- NOVO
SOLD_CODES: List[str] = []  # <-- NOVO para rastrear códigos vendidos
PIX_PAYMENTS: Dict[str, Dict] = {}  # <-- NOVO para rastrear pagamentos PIX
PIX_PAYMENTS_FILE = os.path.join(BASE_DIR, "pix_payments.json")

def load_balance():
    global USER_BALANCE
    if os.path.exists(BALANCE_FILE):
        try:
            with open(BALANCE_FILE, "r", encoding="utf-8") as f:
                USER_BALANCE = {int(k): float(v) for k, v in json.load(f).items()}
        except Exception as e:
            log.warning(f"Falha ao carregar saldo: {e}")

def save_balance():
    try:
        with open(BALANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(USER_BALANCE, f)
    except Exception as e:
        log.warning(f"Falha ao salvar saldo: {e}")

def load_history():
    global USER_HISTORY
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                USER_HISTORY = {int(k): v for k, v in json.load(f).items()}
        except Exception as e:
            log.warning(f"Falha ao carregar histórico: {e}")

def save_history():
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(USER_HISTORY, f)
    except Exception as e:
        log.warning(f"Falha ao salvar histórico: {e}")

def load_sold_codes():
    global SOLD_CODES
    if os.path.exists(SOLD_CODES_FILE):
        try:
            with open(SOLD_CODES_FILE, "r", encoding="utf-8") as f:
                SOLD_CODES = json.load(f)
        except Exception as e:
            log.warning(f"Falha ao carregar códigos vendidos: {e}")

def save_sold_codes():
    try:
        with open(SOLD_CODES_FILE, "w", encoding="utf-8") as f:
            json.dump(SOLD_CODES, f)
    except Exception as e:
        log.warning(f"Falha ao salvar códigos vendidos: {e}")

def load_pix_payments():
    global PIX_PAYMENTS
    if os.path.exists(PIX_PAYMENTS_FILE):
        try:
            with open(PIX_PAYMENTS_FILE, "r", encoding="utf-8") as f:
                PIX_PAYMENTS = json.load(f)
        except Exception as e:
            log.warning(f"Falha ao carregar pagamentos PIX: {e}")

def save_pix_payment(payment_id: str, user_id: int, amount: float, status: str = "pending", qr_code: str = "", charge_data: dict = None):
    """Salva um pagamento PIX no arquivo JSON"""
    PIX_PAYMENTS[payment_id] = {
        "user_id": user_id,
        "amount": amount,
        "status": status,
        "qr_code": qr_code,
        "charge_data": charge_data or {},
        "created_at": datetime.now().isoformat()
    }
    try:
        with open(PIX_PAYMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(PIX_PAYMENTS, f, indent=2)
    except Exception as e:
        log.warning(f"Falha ao salvar pagamento PIX: {e}")

def add_history(user_id: int, item: Dict):
    USER_HISTORY.setdefault(user_id, [])
    # Adiciona timestamp da compra
    item_copy = dict(item)
    item_copy["purchase_time"] = int(time.time())
    USER_HISTORY[user_id].append(item_copy)
    save_history()
    
    # Adiciona o código à lista de códigos vendidos
    if "code" in item and item["code"] not in SOLD_CODES:
        SOLD_CODES.append(item["code"])
        save_sold_codes()
        # Atualiza o catálogo para marcar o código como indisponível
        CATALOG.mark_code_as_sold(item["code"])

def ensure_balance(user_id: int):
    if user_id not in USER_BALANCE:
        USER_BALANCE[user_id] = 0.00
        save_balance()
    if user_id not in USER_HISTORY:
        USER_HISTORY[user_id] = []
        save_history()

# =============== KEYBOARDS ===============
def kb_main() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("Compre aqui", callback_data="go_buy")],
        [InlineKeyboardButton("Adicionar saldo", callback_data="saldo_add"),
         InlineKeyboardButton("Carteira", callback_data="wallet")],
        [InlineKeyboardButton("Grupo", callback_data="group"),
         InlineKeyboardButton("Suporte/Atendimento", callback_data="support")],
        [InlineKeyboardButton("Regras e Trocas", callback_data="rules")],
        [InlineKeyboardButton("Canal de Avisos", callback_data="news")],
    ]
    return InlineKeyboardMarkup(rows)

def kb_buy_home() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("Adicionar saldo", callback_data="saldo_add")],
        [InlineKeyboardButton("Códigos (por Tipo/Subtipo)", callback_data="full_codes")],
        [InlineKeyboardButton("Busca por inicial", callback_data="busca_ini"),
         InlineKeyboardButton("Busca por tipo", callback_data="busca_tipo")],
        [InlineKeyboardButton("<< Voltar", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(rows)

def kb_only_back(back_data: str = "back_buy_home") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("<< Voltar", callback_data=back_data)]])

def kb_subtypes(type_name: str) -> InlineKeyboardMarkup:
    # Obter a lista de subtipos para o tipo especificado
    subs = CATALOG.get_subtypes(type_name)
    log.info(f"kb_subtypes: Criando teclado para {type_name} com {len(subs)} subtipos")
    
    # Criar as linhas do teclado
    rows: List[List[InlineKeyboardButton]] = []
    pair: List[InlineKeyboardButton] = []
    
    # Adicionar botões para cada subtipo (2 por linha)
    for s in subs:
        # Verificar se há códigos disponíveis para este subtipo
        codes = CATALOG.get_codes(type_name, s)
        if not codes:
            log.warning(f"Subtipo {s} do tipo {type_name} não tem códigos disponíveis, pulando")
            continue
            
        callback = f"sub|{type_name}|{s}"
        log.info(f"Adicionando botão: {s} -> {callback}")
        pair.append(InlineKeyboardButton(s, callback_data=callback))
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    
    # Adicionar a última linha se tiver um botão sobrando
    if pair: 
        rows.append(pair)
    
    # Adicionar o botão de voltar
    rows.append([InlineKeyboardButton("<< Voltar", callback_data="back_types")])
    
    # Criar e retornar o teclado
    keyboard = InlineKeyboardMarkup(rows)
    log.info(f"Teclado criado com {len(rows)} linhas")
    return keyboard

def kb_viewer(type_name: str, subtype: str, total_items: int = 1) -> InlineKeyboardMarkup:
    rows = []
    
    # Botão de comprar
    rows.append([InlineKeyboardButton("Comprar", callback_data=f"buy|{type_name}|{subtype}")])
    
    # Botões de navegação apenas se houver mais de um item
    if total_items > 1:
        rows.append([
            InlineKeyboardButton("<<", callback_data=f"nav|{type_name}|{subtype}|prev"),
            InlineKeyboardButton(">>", callback_data=f"nav|{type_name}|{subtype}|next")
        ])
    
    # Botão de voltar
    rows.append([InlineKeyboardButton("<< Voltar", callback_data=f"back_sub|{type_name}")])
    
    return InlineKeyboardMarkup(rows)

def kb_wallet() -> InlineKeyboardMarkup:
    # Remove o botão "Adicionar saldo" da tela de histórico
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Histórico de compras", callback_data="history")],
        [InlineKeyboardButton("<< Voltar", callback_data="back_main")],
    ])

def kb_history_nav(user_id: int, idx: int, total: int) -> InlineKeyboardMarkup:
    rows = []
    if total > 1:
        rows.append([
            InlineKeyboardButton("<<", callback_data=f"history_nav|{idx}|prev"),
            InlineKeyboardButton(">>", callback_data=f"history_nav|{idx}|next")
        ])
    rows.append([InlineKeyboardButton("<< Voltar", callback_data="back_wallet")])
    # Certifique-se que rows é uma lista, não uma tupla
    return InlineKeyboardMarkup(rows)

def kb_only_back_wallet() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("<< Voltar", callback_data="back_wallet")]])

def kb_rules_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("<< Voltar", callback_data="back_main")]])

def kb_types() -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    pair: List[InlineKeyboardButton] = []
    
    # Obter apenas os tipos que têm códigos disponíveis
    # CATALOG.get_types_sorted() já retorna apenas tipos com códigos disponíveis
    # porque é baseado nas chaves de codes_by_pair
    for name, price in CATALOG.get_types_sorted():
        # Verificar se há subtipos disponíveis para este tipo
        subtypes = CATALOG.get_subtypes(name)
        if not subtypes:
            log.warning(f"Tipo {name} não tem subtipos disponíveis, pulando")
            continue
            
        # Verificar se há códigos disponíveis para este tipo
        has_available_codes = False
        for subtype in subtypes:
            codes = CATALOG.get_codes(name, subtype)
            if codes:
                has_available_codes = True
                break
                
        if not has_available_codes:
            log.warning(f"Tipo {name} não tem códigos disponíveis, pulando")
            continue
            
        label = f"{name} - {money(price)}" if price > 0 else name
        btn = InlineKeyboardButton(label, callback_data=f"type|{name}")
        pair.append(btn)
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append([InlineKeyboardButton("<< Voltar", callback_data="back_buy_home")])
    return InlineKeyboardMarkup(rows)

# =============== HOME (banner + legenda) ===============
def build_home_caption(user_id: int) -> str:
    saldo = USER_BALANCE.get(user_id, 0.0)
    return (
        "Bem-vindo(a) ao catálogo!\n\n"
        f"_Saldo atual_: {saldo:0.2f}\n\n"
        "Escolha uma opção:" + PAD
    )

async def send_photo_resilient(chat, photo_source: str, caption: str, reply_markup):
    # 1) Arquivo local
    if os.path.isfile(photo_source):
        with open(photo_source, "rb") as f:
            return await chat.send_photo(photo=f, caption=caption, parse_mode="Markdown", reply_markup=reply_markup)
    # 2) URL direta (Telegram baixa)
    try:
        return await chat.send_photo(photo=photo_source, caption=caption, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        log.warning("send_photo por URL falhou (%s). Tentando baixar e reenviar…", e)
    # 3) Download manual + reenvio
    try:
        r = requests.get(photo_source, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        bio = BytesIO(r.content); bio.name = "banner.png"
        return await chat.send_photo(photo=bio, caption=caption, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e2:
        log.error("Falha para enviar imagem: %s", e2)
        return await chat.send_message(caption + "\n\n(⚠️ Não foi possível carregar a imagem.)",
                                       parse_mode="Markdown", reply_markup=reply_markup)

async def send_home_message(chat, user_id: int):
    # Mensagem única com link invisível para exibir imagem no corpo
    message_text = (
        "Bem-vindo(a) ao catálogo!\n\n"
        f"_Saldo atual_: {USER_BALANCE.get(user_id, 0.0):0.2f}[__]({IMG_URL})\n\n"
        "Escolha uma opção:" + PAD
    )
    
    await chat.send_message(
        message_text,
        parse_mode="Markdown",
        reply_markup=kb_main()
    )

# =============== HANDLERS BÁSICOS ===============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_balance(user_id)
    await send_home_message(update.message.chat, user_id)

async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        CATALOG.load(CATALOG_TXT)
        
        # Marcar códigos vendidos como indisponíveis após o reload
        for code in SOLD_CODES:
            CATALOG.mark_code_as_sold(code)
            
        await update.effective_message.reply_text(f"Catálogo recarregado. Pares disponíveis: {len(CATALOG.codes_by_pair)}\nCódigos vendidos continuam indisponíveis.")
    except Exception as e:
        await update.effective_message.reply_text(f"Erro ao recarregar catálogo: {e}")

async def cmd_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_balance(user_id)
    try:
        val = float(context.args[0])
        USER_BALANCE[user_id] = max(0.0, val)
        save_balance()
        await update.effective_message.reply_text(f"Saldo atualizado: {money(USER_BALANCE[user_id])}")
    except Exception:
        await update.effective_message.reply_text("Uso: /saldo 50")

# Configurações da Zyntra API (baseado no código que funcionou)
ZYNTRA_API_URL = "https://api.zyntrapayments.com/v1/transactions"
ZYNTRA_SECRET_KEY = "sk_live_v22ZRTDZQjPsOWlh7EEOEgYrW3dcxfMjuUDHHyj8Gg"

def generate_basic_auth_string(secret_key: str) -> str:
    """Gera a string de autorização Basic para a Zyntra API."""
    auth_string = f"{secret_key}:x"
    encoded_auth_string = base64.b64encode(auth_string.encode("ascii")).decode("ascii")
    return f"Basic {encoded_auth_string}"

AUTH_HEADER = generate_basic_auth_string(ZYNTRA_SECRET_KEY)

async def cmd_pix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera um pagamento PIX usando a API Zyntra (versão que funcionou)."""
    user_id = update.effective_user.id
    ensure_balance(user_id)
    
    args = context.args
    if not args:
        await update.message.reply_text(
            "💰 *Adicionar Saldo via PIX*\n\n"
            "Use: `/pix VALOR [descrição]`\n"
            "Exemplo: `/pix 50` ou `/pix 50 RecargaSaldo`\n\n"
            "⚡ Pagamento instantâneo via PIX\n"
            "🔒 Processamento seguro via Zytra Payments",
            parse_mode="Markdown"
        )
        return

    try:
        amount_str = args[0].replace(",", ".")
        amount = int(float(amount_str) * 100)  # Converter para centavos
        valor_real = float(amount_str)  # Valor em reais para exibição
        
        description = "Recarga de Saldo" # Descrição padrão
        if len(args) > 1:
            description = " ".join(args[1:])
    except ValueError:
        await update.message.reply_text("❌ Valor inválido. Por favor, insira um número válido (ex: 10.50).")
        return

    if amount <= 0:
        await update.message.reply_text("❌ O valor deve ser maior que zero.")
        return
        
    if valor_real < 1.0:
        await update.message.reply_text("❌ Valor mínimo: R$ 1,00")
        return
        
    if valor_real > 1000.0:
        await update.message.reply_text("❌ Valor máximo: R$ 1.000,00")
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

    # Enviar mensagem de processamento
    processing_msg = await update.message.reply_text(
        "⏳ Gerando pagamento PIX...\n"
        "Aguarde alguns segundos."
    )

    try:
        response = requests.post(ZYNTRA_API_URL, json=payload, headers=headers)
        response.raise_for_status()  # Levanta um erro para códigos de status HTTP ruins (4xx ou 5xx)
        transaction_data = response.json()

        if transaction_data and transaction_data.get("pix"):
            pix_qrcode = transaction_data["pix"].get("qrcode")
            pix_url = transaction_data["pix"].get("url")
            
            # Salvar pagamento no banco de dados
            payment_id = transaction_data.get("id") or str(uuid.uuid4())
            save_pix_payment(payment_id, user_id, valor_real, "pending", pix_qrcode)
            
            message = f"💰 *PIX gerado com sucesso!*\n\n"
            message += f"💵 Valor: {money(valor_real)}\n"
            message += f"📝 Descrição: {description}\n"
            message += f"🆔 ID: `{payment_id[:8]}...`\n"
            message += f"⏰ Válido por: 24 horas\n\n"
            message += f"📱 *Como pagar:*\n"
            message += f"1. Abra seu app bancário\n"
            message += f"2. Escaneie o QR Code ou use o código PIX\n"
            message += f"3. Confirme o pagamento\n\n"
            message += f"✅ Seu saldo será creditado automaticamente!"
            
            await processing_msg.edit_text(message, parse_mode="Markdown")
            
            # Enviar QR Code como texto
            if pix_qrcode:
                await update.message.reply_text(
                    f"📋 *Código PIX (Copia e Cola):*\n\n"
                    f"`{pix_qrcode}`\n\n"
                    f"💡 Toque no código acima para copiar",
                    parse_mode="Markdown"
                )
                
            # Tentar gerar QR Code visual se a biblioteca estiver disponível
            if pix_qrcode and qrcode:
                try:
                    img = qrcode.make(pix_qrcode)
                    bio = BytesIO()
                    bio.name = "pix_qr.png"
                    img.save(bio, "PNG")
                    bio.seek(0)
                    
                    await update.message.reply_photo(
                        bio, 
                        caption=f"📱 QR Code PIX para {money(valor_real)}",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    log.error(f"Erro ao gerar QR Code visual: {e}")
                    
            if pix_url:
                await update.message.reply_text(
                    f"🔗 *Link para pagamento:*\n{pix_url}",
                    parse_mode="Markdown"
                )
        else:
            await processing_msg.edit_text("❌ Erro ao gerar PIX: Resposta da API inválida ou sem dados PIX.")
            log.error(f"Resposta da API Zyntra inválida: {transaction_data}")

    except requests.exceptions.RequestException as e:
        log.error(f"Erro na requisição para a API Zyntra: {e}")
        await processing_msg.edit_text(
            f"❌ Ocorreu um erro ao tentar gerar o PIX. Por favor, tente novamente mais tarde.\n\n"
            f"💡 *Dica:* Este erro pode ocorrer devido a restrições de IP. "
            f"O sistema funciona melhor quando executado em servidores na nuvem."
        )
    except Exception as e:
        log.error(f"Erro inesperado: {e}")
        await processing_msg.edit_text(
            f"❌ Ocorreu um erro inesperado. Por favor, tente novamente mais tarde."
        )

async def cmd_inicial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_balance(user_id)

    if not context.args:
        txt = "Uso: `/inicial 123456`\nEnvie os *primeiros dígitos* do código para filtrar."
        return await update.effective_message.reply_text(txt, parse_mode="Markdown", reply_markup=kb_only_back("back_buy_home"))

    prefixo = "".join(context.args).strip()
    items: List[Dict] = []
    for (_t, _s), lst in CATALOG.codes_by_pair.items():
        items.extend([it for it in lst if it["code"].startswith(prefixo)])

    if not items:
        return await update.effective_message.reply_text(
            f"Não há itens com a inicial *{prefixo}* disponível.",
            parse_mode="Markdown", reply_markup=kb_only_back("back_buy_home")
        )

    fid = _create_filter_session(context, items)
    title = f"Itens iniciando com {prefixo}"
    it0 = items[0]
    txt = _build_filter_text(it0, 0, len(items), title, user_id)
    await update.effective_message.reply_text(txt, reply_markup=kb_viewer_filter(fid, len(items)))

async def cmd_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_balance(user_id)

    if not context.args:
        tipos = ", ".join([t for t, _ in CATALOG.get_types_sorted()]) or "—"
        txt = ("Uso: `/tipo NOME_DO_TIPO`\nEx.: `/tipo Beginner`\n\n"
               f"Tipos disponíveis: {tipos}")
        return await update.effective_message.reply_text(txt, parse_mode="Markdown", reply_markup=kb_only_back("back_buy_home"))

    tipo_query = " ".join(context.args).strip().lower()

    items: List[Dict] = []
    for (_t, _s), lst in CATALOG.codes_by_pair.items():
        if _t.lower() == tipo_query:
            items.extend(lst)

    if not items:
        for (_t, _s), lst in CATALOG.codes_by_pair.items():
            if tipo_query in _t.lower():
                items.extend(lst)

    if not items:
        return await update.effective_message.reply_text(
            f"Não há itens do tipo *{tipo_query}* disponíveis.",
            parse_mode="Markdown", reply_markup=kb_only_back("back_buy_home")
        )

    fid = _create_filter_session(context, items)
    title = f"Itens do tipo {items[0]['type']}"
    txt = _build_filter_text(items[0], 0, len(items), title, user_id)
    await update.effective_message.reply_text(txt, reply_markup=kb_viewer_filter(fid, len(items)))

# =============== FUNÇÕES AUXILIARES PARA FILTROS ===============
def _create_filter_session(context, items: List[Dict]) -> int:
    """Cria uma sessão de filtro e retorna o ID da sessão"""
    fid = int(time.time() * 1000) % 100000  # ID único baseado no timestamp
    context.chat_data[f"flt_items_{fid}"] = items
    context.chat_data[f"flt_idx_{fid}"] = 0
    return fid

def _build_filter_text(it: Dict, idx: int, total: int, title: str, user_id: int) -> str:
    """Constrói o texto para exibição de itens filtrados"""
    raw_masked = mask_code_in_text(it["raw"], it["code"])
    price = float(it.get("price") or CATALOG.types_price.get(it["type"], 0.0))
    saldo = USER_BALANCE.get(user_id, 0.0)
    
    return (
        f"{title}\n"
        f"Visualizando {idx + 1} de {total}\n\n"
        f"{raw_masked}\n\n"
        f"Preço: {money(price)}\n"
        f"Seu Saldo: {money(saldo)}\n{PAD}"
    )

def kb_viewer_filter(fid: int, total_items: int = 1) -> InlineKeyboardMarkup:
    """Cria teclado para navegação em resultados filtrados"""
    rows = []
    
    # Botão de comprar
    rows.append([InlineKeyboardButton("Comprar", callback_data=f"fbuy|{fid}")])
    
    # Botões de navegação apenas se houver mais de um item
    if total_items > 1:
        rows.append([
            InlineKeyboardButton("<<", callback_data=f"fnav|{fid}|prev"),
            InlineKeyboardButton(">>", callback_data=f"fnav|{fid}|next")
        ])
    
    # Botão de voltar
    rows.append([InlineKeyboardButton("<< Voltar", callback_data="back_buy_home")])
    
    return InlineKeyboardMarkup(rows)

# =============== CALLBACKS (menus e navegação) ===============
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    user_id = update.effective_user.id
    ensure_balance(user_id)

    # ===== MENU PRINCIPAL =====
    if data == "go_buy":
        txt = "Catálogo\n\nEscolha uma opção:\n\n" + PAD + PAD
        return await q.edit_message_text(txt, reply_markup=kb_buy_home())

    elif data == "back_main":
        try: await q.message.delete()
        except: pass
        return await send_home_message(q.message.chat, user_id)

    elif data == "wallet":
        txt = f"*Carteira*\nID: `{user_id}`\nSaldo: {money(USER_BALANCE[user_id])}" + PAD
        return await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb_wallet())

    elif data == "saldo_add":
        txt = (
            "*Adicionar saldo de teste*\n\n"
            "Para adicionar saldo, digite o comando:\n"
            "`/pix VALOR`\n\n"
            "Exemplo: `/pix 50`\n\n"
            "Isso irá adicionar o valor informado diretamente à sua carteira para testes.\n"
            "_(Em breve integração real com PIX e QR Code)._"
            + PAD
        )
        # Mostra apenas o botão de voltar na tela de adicionar saldo
        return await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb_only_back_wallet())

    elif data == "history":
        history = USER_HISTORY.get(user_id, [])
        if not history:
            return await q.edit_message_text("Nenhuma compra registrada.\n\n" + PAD, reply_markup=kb_only_back_wallet())
        idx = 0
        context.chat_data["history_idx"] = idx
        return await show_history(q, user_id, idx)
    elif data.startswith("history_nav|"):
        _, idx_str, direction = data.split("|", 2)
        history = USER_HISTORY.get(user_id, [])
        if not history:
            return await q.edit_message_text("Nenhuma compra registrada.\n\n" + PAD, reply_markup=kb_only_back_wallet())
        idx = int(idx_str)
        total = len(history)
        if direction == "next":
            idx = (idx + 1) % total
        else:
            idx = (idx - 1) % total
        context.chat_data["history_idx"] = idx
        return await show_history(q, user_id, idx)

    elif data == "back_wallet":
        txt = f"*Carteira*\nID: `{user_id}`\nSaldo: {money(USER_BALANCE[user_id])}" + PAD
        return await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb_wallet())

    elif data == "group":
        return await q.edit_message_text(
            "Clique abaixo para acessar o grupo oficial:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Ir para o Grupo", url=f"https://t.me/{GRUPO_AT.lstrip('@')}")],
                [InlineKeyboardButton("<< Voltar", callback_data="back_main")]
            ])
        )
    elif data == "news":
        return await q.edit_message_text(
            "Clique abaixo para acessar o canal de avisos:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Ir para o Canal", url=f"https://t.me/{CANAL_AT.lstrip('@')}")],
                [InlineKeyboardButton("<< Voltar", callback_data="back_main")]
            ])
        )
    elif data == "support":
        txt = (
            "*Suporte*\n\n"
            "O suporte funciona das 08h às 22h.\n"
            "Mande sua mensagem no botão abaixo e aguarde que brevemente você será atendido."
        )
        return await q.edit_message_text(
            txt,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Solicitar Suporte", url=f"https://t.me/{SUPORTE_AT.lstrip('@')}")],
                [InlineKeyboardButton("<< Voltar", callback_data="back_main")]
            ])
        )
    elif data == "rules":
        txt = (
            "*Regras e Trocas*\n\n"
            "• Todos os nossos códigos são previamente testados e estão funcionando.\n"
            "• Após realizar sua compra, caso tenha algum problema, basta clicar no botão *Relatar problema* abaixo do seu código.\n"
            "• O prazo para relatar é de 10 minutos após a compra.\n"
            "• Alguém do suporte irá te atender e testar o código para você novamente.\n"
            "• Caso seja detectado que está ruim, seu saldo será estornado.\n\n"
            "Em caso de dúvidas, utilize o botão de suporte abaixo."
        )
        return await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb_rules_back())

    # ===== CATÁLOGO CLÁSSICO (Tipo -> Subtipo -> Viewer) =====
    elif data == "full_codes":
        txt = "Escolha um *tipo* para continuar:" + PAD
        return await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb_types())

    elif data == "back_buy_home":
        return await q.edit_message_text("Catálogo\n\nEscolha uma opção:\n\n" + PAD + PAD, reply_markup=kb_buy_home())

    elif data.startswith("type|"):
        type_name = data.split("|", 1)[1]
        log.info(f"Selecionado tipo: {type_name}")
        
        subs = CATALOG.get_subtypes(type_name)
        log.info(f"Subtipos encontrados: {subs}")
        
        if not subs:
            return await q.answer("Sem subtipos disponíveis para este tipo.", show_alert=True)
            
        # Criar o teclado de subtipos
        keyboard = kb_subtypes(type_name)
        log.info(f"Teclado criado com {len(keyboard.inline_keyboard)} linhas")
        
        txt = f"Escolha um *subtipo* para continuar\nTipo: *{type_name}*" + PAD
        return await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=keyboard)

    elif data == "back_types":
        txt = "Escolha um *tipo* para continuar:" + PAD
        return await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb_types())

    elif data.startswith("sub|"):
        # Extrair tipo e subtipo do callback data
        parts = data.split("|", 2)
        if len(parts) < 3:
            log.error(f"Formato inválido para callback sub: {data}")
            return await q.answer("Erro no formato do callback. Tente novamente.", show_alert=True)
            
        _, type_name, subtype = parts
        log.info(f"Selecionado subtipo: {subtype} do tipo: {type_name}")
        
        # Obter os itens para o par tipo/subtipo
        items = CATALOG.get_codes(type_name, subtype)
        log.info(f"Itens encontrados para {type_name}/{subtype}: {len(items)}")
        
        # Verificar se há itens disponíveis
        if not items:
            log.warning(f"Sem itens para {type_name}/{subtype}")
            return await q.answer("Sem itens disponíveis para essa combinação.", show_alert=True)
        
        # Mostrar o viewer com o primeiro item
        return await show_viewer(q, context, type_name, subtype, 0)

    elif data.startswith("nav|"):
        _, type_name, subtype, direction = data.split("|", 3)
        items = CATALOG.get_codes(type_name, subtype)
        if not items:
            return await q.answer("Sem itens disponíveis.", show_alert=True)
        idx_key = f"idx|{type_name}|{subtype}"
        idx = context.chat_data.get(idx_key, 0)
        idx = (idx + 1) % len(items) if direction == "next" else (idx - 1) % len(items)
        context.chat_data[idx_key] = idx
        return await show_viewer(q, context, type_name, subtype, idx)

    elif data.startswith("back_sub|"):
        _, type_name = data.split("|", 1)
        txt = f"Escolha um *subtipo* para continuar\nTipo: *{type_name}*" + PAD
        return await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb_subtypes(type_name))

    elif data.startswith("buy|"):
        _, type_name, subtype = data.split("|", 2)
        items = CATALOG.get_codes(type_name, subtype)
        idx_key = f"idx|{type_name}|{subtype}"
        idx = context.chat_data.get(idx_key, 0)
        if not items:
            return await q.answer("Sem itens disponíveis.", show_alert=True)
        it = items[idx]
        price = float(CATALOG.types_price.get(type_name, 0.0))
        if USER_BALANCE[user_id] < price:
            return await q.answer("Saldo insuficiente. Adicione saldo.", show_alert=True)
        
        # Processar a compra
        USER_BALANCE[user_id] -= price
        save_balance()
        add_history(user_id, it)  # Esta função já marca o código como vendido
        
        # Atualizar a lista de itens após a compra
        items = CATALOG.get_codes(type_name, subtype)  # Obter a lista atualizada
        
        # Ajustar o índice se necessário (caso o item comprado era o último da lista)
        if items and idx >= len(items):
            idx = len(items) - 1
            context.chat_data[idx_key] = idx
            
        txt = build_viewer_text_full(it, idx, len(items) + 1, user_id)  # +1 porque o item comprado não está mais na lista
        now = int(time.time())
        purchase_time = it.get("purchase_time", now)
        # Criar um novo teclado
        keyboard = []
        
        # Adicionar o botão de relatar problema se necessário (primeiro)
        if now - purchase_time <= 600:
            keyboard.append([InlineKeyboardButton("Relatar problema", url=f"https://t.me/{SUPORTE_AT.lstrip('@')}")])
        
        # Adicionar o botão de voltar (último)
        keyboard.append([InlineKeyboardButton("<< Voltar", callback_data="back_wallet")])
            
        # Criar um novo markup com o teclado completo
        markup = InlineKeyboardMarkup(keyboard)
        
        return await q.edit_message_text(txt, reply_markup=markup)

    # ===== TELAS DE AJUDA PARA BUSCAS =====
    elif data == "busca_ini":
        txt = (
            "*Pesquisa por inicial*\n\n"
            "Para pesquisar por inicial, digite:\n"
            "`/inicial` seguido do prefixo desejado\n"
            "Ex.: `/inicial 123456`"
        )
        return await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb_only_back("back_buy_home"))

    elif data == "busca_tipo":
        tipos = ", ".join([t for t, _ in CATALOG.get_types_sorted()]) or "—"
        txt = (
            "*Pesquisa por tipo*\n\n"
            "Para pesquisar por tipo, digite:\n"
            "`/tipo` seguido do nome do tipo\n"
            "Ex.: `/tipo Beginner`\n\n"
            f"Tipos disponíveis: {tipos}"
        )
        return await q.edit_message_text(txt, parse_mode="Markdown", reply_markup=kb_only_back("back_buy_home"))

    # ===== NAVEGAÇÃO/COMPRA NO VIEWER DE FILTRO (/inicial e /tipo) =====
    elif data.startswith("fnav|"):
        _, fid_str, direction = data.split("|", 2)
        fid = int(fid_str)
        items = context.chat_data.get(f"flt_items_{fid}", [])
        if not items:
            return await q.answer("Filtro expirado. Abra novamente.", show_alert=True)
        idx = context.chat_data.get(f"flt_idx_{fid}", 0)
        idx = (idx + 1) % len(items) if direction == "next" else (idx - 1) % len(items)
        context.chat_data[f"flt_idx_{fid}"] = idx
        it = items[idx]
        txt = _build_filter_text(it, idx, len(items), "Resultados", user_id)
        return await q.edit_message_text(txt, reply_markup=kb_viewer_filter(fid, len(items)))

    elif data.startswith("fbuy|"):
        _, fid_str = data.split("|", 1)
        fid = int(fid_str)
        items = context.chat_data.get(f"flt_items_{fid}", [])
        idx = context.chat_data.get(f"flt_idx_{fid}", 0)
        if not items:
            return await q.answer("Filtro expirado. Abra novamente.", show_alert=True)
        it = items[idx]
        price = float(it.get("price") or CATALOG.types_price.get(it["type"], 0.0))
        if USER_BALANCE[user_id] < price:
            return await q.answer("Saldo insuficiente. Adicione saldo.", show_alert=True)
        USER_BALANCE[user_id] -= price
        save_balance()
        add_history(user_id, it)
        txt = build_viewer_text_full(it, idx, len(items), user_id)
        
        # Criar teclado com ordem correta dos botões
        now = int(time.time())
        purchase_time = it.get("purchase_time", now)
        keyboard = []
        
        # Adicionar o botão de relatar problema se necessário (primeiro)
        if now - purchase_time <= 600:
            keyboard.append([InlineKeyboardButton("Relatar problema", url=f"https://t.me/{SUPORTE_AT.lstrip('@')}")])
        
        # Adicionar o botão de voltar (último)
        keyboard.append([InlineKeyboardButton("<< Voltar", callback_data="back_buy_home")])
        
        markup = InlineKeyboardMarkup(keyboard)
        return await q.edit_message_text(txt, reply_markup=markup)

def build_viewer_text_full(it: Dict, idx: int, total: int, user_id: int) -> str:
    # Mostrar código completo após a compra (sem mascarar)
    raw_full = it["raw"]
    price = float(it.get("price") or CATALOG.types_price.get(it["type"], 0.0))
    saldo = USER_BALANCE.get(user_id, 0.0)
    purchase_time = it.get("purchase_time")
    time_str = ""
    if purchase_time:
        time_str = f"\nHora da compra: {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(purchase_time))}"
    return (
        f"Visualizando {idx + 1} de {total}\n\n"
        f"{raw_full}\n\n"
        f"Preço: {money(price)}\n"
        f"Seu Saldo: {money(saldo)}{time_str}\n{PAD}"
    )

def build_history_text_full(it: Dict, idx: int, total: int, user_id: int) -> str:
    # Mostrar código completo no histórico (sem mascarar)
    raw_full = it["raw"]
    price = float(it.get("price") or CATALOG.types_price.get(it["type"], 0.0))
    saldo = USER_BALANCE.get(user_id, 0.0)
    purchase_time = it.get("purchase_time")
    time_str = ""
    if purchase_time:
        time_str = f"\nHora da compra: {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(purchase_time))}"
    return (
        f"Histórico de compras\nVisualizando {idx + 1} de {total}\n\n"
        f"{raw_full}\n\n"
        f"Preço: {money(price)}\n"
        f"Seu Saldo: {money(saldo)}{time_str}\n{PAD}"
    )

async def show_history(q, user_id: int, idx: int):
    history = USER_HISTORY.get(user_id, [])
    if not history:
        return await q.edit_message_text("Nenhuma compra registrada.\n\n" + PAD, reply_markup=kb_only_back_wallet())
    # Inverter a ordem do histórico para mostrar a última compra primeiro
    history_reversed = list(reversed(history))
    total = len(history_reversed)
    item = history_reversed[idx]
    txt = build_history_text_full(item, idx, total, user_id)
    now = int(time.time())
    purchase_time = item.get("purchase_time", 0)
    # Criar um novo teclado
    keyboard = []
    
    # Adicionar o botão de relatar problema se necessário (primeiro)
    if purchase_time and now - purchase_time <= 600:
        keyboard.append([InlineKeyboardButton("Relatar problema", url=f"https://t.me/{SUPORTE_AT.lstrip('@')}")])
    
    # Adicionar botões de navegação se houver mais de um item
    if total > 1:
        keyboard.append([
            InlineKeyboardButton("<<", callback_data=f"history_nav|{idx}|prev"),
            InlineKeyboardButton(">>", callback_data=f"history_nav|{idx}|next")
        ])
    
    # Adicionar o botão de voltar (último)
    keyboard.append([InlineKeyboardButton("<< Voltar", callback_data="back_wallet")])
    
    # Criar um novo markup com o teclado completo
    markup = InlineKeyboardMarkup(keyboard)
    
    return await q.edit_message_text(txt, reply_markup=markup)

# Comando para listar códigos vendidos (apenas para administradores)
async def cmd_vendidos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista todos os códigos vendidos"""
    # Verificar se o usuário é administrador (você pode ajustar esta lógica conforme necessário)
    admin_ids = [123456789]  # Substitua pelos IDs dos administradores
    if update.effective_user.id not in admin_ids:
        return await update.message.reply_text("Comando disponível apenas para administradores.")
    
    if not SOLD_CODES:
        return await update.message.reply_text("Nenhum código foi vendido ainda.")
    
    # Criar uma mensagem com os códigos vendidos
    txt = "Códigos vendidos:\n\n"
    
    # Agrupar códigos vendidos por tipo e subtipo para melhor organização
    sold_by_type = {}
    for code in SOLD_CODES:
        # Encontrar o item no histórico de todos os usuários
        item_info = None
        for user_id, history in USER_HISTORY.items():
            for item in history:
                if item.get("code") == code:
                    item_info = item
                    break
            if item_info:
                break
        
        if item_info:
            type_name = item_info.get("type", "Desconhecido")
            subtype = item_info.get("subtype", "Desconhecido")
            key = f"{type_name}/{subtype}"
            sold_by_type.setdefault(key, [])
            sold_by_type[key].append(code)
        else:
            # Se não encontrar informações, adicionar ao grupo "Desconhecido"
            sold_by_type.setdefault("Desconhecido", [])
            sold_by_type["Desconhecido"].append(code)
    
    # Formatar a mensagem
    for key, codes in sorted(sold_by_type.items()):
        txt += f"*{key}*:\n"
        for code in sorted(codes):
            txt += f"- {code}\n"
        txt += "\n"
    
    # Enviar a mensagem
    await update.message.reply_text(txt, parse_mode="Markdown")

# =============== BOOTSTRAP ===============
def main():
    load_balance()
    load_history()  # <-- NOVO
    load_sold_codes()  # <-- NOVO para carregar códigos vendidos
    load_pix_payments()  # <-- NOVO para carregar pagamentos PIX
    
    # Verificar se há códigos já vendidos no histórico e marcá-los como indisponíveis
    for user_id, history in USER_HISTORY.items():
        for item in history:
            if "code" in item and item["code"] not in SOLD_CODES:
                SOLD_CODES.append(item["code"])
                CATALOG.mark_code_as_sold(item["code"])
    
    # Salvar a lista atualizada de códigos vendidos
    save_sold_codes()
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reload", cmd_reload))
    app.add_handler(CommandHandler("saldo", cmd_saldo))     # /saldo 50
    app.add_handler(CommandHandler("pix", cmd_pix))         # /pix 50
    app.add_handler(CommandHandler("inicial", cmd_inicial)) # /inicial 123456
    app.add_handler(CommandHandler("tipo", cmd_tipo))       # /tipo Beginner
    app.add_handler(CommandHandler("vendidos", cmd_vendidos)) # /vendidos - listar códigos vendidos
    app.add_handler(CallbackQueryHandler(on_button))
    log.info("Bot iniciado.")
    app.run_polling()



async def show_viewer(q, context: ContextTypes.DEFAULT_TYPE, type_name: str, subtype: str, index: int):
    # Registrar informações para depuração
    log.info(f"show_viewer chamado: type={type_name}, subtype={subtype}, index={index}")
    
    # Obter os itens para o par tipo/subtipo
    items = CATALOG.get_codes(type_name, subtype)
    log.info(f"Itens encontrados: {len(items)}")
    
    # Verificar se há itens disponíveis
    if not items:
        log.warning(f"Sem itens para {type_name}/{subtype}")
        return await q.edit_message_text("Sem itens disponíveis para essa combinação.\n\n" + PAD, reply_markup=kb_subtypes(type_name))
    
    # Garantir que o índice está dentro dos limites
    index = max(0, min(index, len(items) - 1))
    context.chat_data[f"idx|{type_name}|{subtype}"] = index
    log.info(f"Índice ajustado: {index}")
    
    try:
        # Obter o item atual
        it = items[index]
        
        # Mascarar o código no texto bruto
        raw_masked = mask_code_in_text(it["raw"], it["code"])
        
        # Obter o preço (do item ou do tipo)
        price = float(it.get("price") or CATALOG.types_price.get(it["type"], 0.0))
        
        # Obter o saldo do usuário
        saldo = USER_BALANCE.get(q.from_user.id, 0.0)
        
        # Construir o texto da mensagem
        txt = (
            f"Visualizando {index + 1} de {len(items)}\n\n"
            f"{raw_masked}\n\n"
            f"Preço: {money(price)}\n"
            f"Seu Saldo: {money(saldo)}\n{PAD}"
        )
        
        # Criar o teclado de visualização com o número total de itens
        markup = kb_viewer(type_name, subtype, len(items))
        
        # Atualizar a mensagem com o teclado de visualização
        return await q.edit_message_text(txt, reply_markup=markup)
    except Exception as e:
        log.error(f"Erro ao mostrar viewer: {e}")
        return await q.edit_message_text(f"Erro ao exibir item. Tente novamente.\n\nDetalhes: {str(e)}", 
                                       reply_markup=kb_subtypes(type_name))

if __name__ == "__main__":
    main()