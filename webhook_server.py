from flask import Flask, request, jsonify
import json
import logging
import sqlite3
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configurações da Zytra Payments
ZYTRA_SECRET_KEY = "sk_live_v22ZRTDZQjPsOWlh7EEOEgYrW3dcxfMjuUDHHyj8Gg"
ZYTRA_PUBLIC_KEY = "pk_live_v2BeWQ5kzTiOxcChXfBJSy149rMqFrr8o4"

def init_webhook_db():
    """Inicializa o banco de dados para armazenar webhooks"""
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Tabela para armazenar webhooks recebidos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            payment_id TEXT,
            status TEXT,
            amount REAL,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_data TEXT
        )
    ''')
    
    # Tabela para armazenar pagamentos PIX pendentes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pix_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id TEXT UNIQUE,
            user_id INTEGER,
            amount REAL,
            status TEXT DEFAULT 'pending',
            qr_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def add_balance_to_user(user_id, amount):
    """Adiciona saldo ao usuário no banco de dados do bot"""
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        # Buscar saldo atual do usuário
        cursor.execute('SELECT saldo FROM usuarios WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result:
            current_balance = result[0]
            new_balance = current_balance + amount
            
            # Atualizar saldo
            cursor.execute('UPDATE usuarios SET saldo = ? WHERE user_id = ?', (new_balance, user_id))
            logger.info(f"Saldo atualizado para usuário {user_id}: {current_balance} -> {new_balance}")
        else:
            logger.warning(f"Usuário {user_id} não encontrado no banco de dados")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao adicionar saldo ao usuário {user_id}: {e}")
        return False

def update_payment_status(payment_id, status):
    """Atualiza o status de um pagamento PIX"""
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE pix_payments 
            SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE payment_id = ?
        ''', (status, payment_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar status do pagamento {payment_id}: {e}")
        return False

@app.route('/webhook/zytra', methods=['POST'])
def zytra_webhook():
    """Endpoint para receber webhooks da Zytra Payments"""
    try:
        # Obter dados do webhook
        data = request.get_json()
        
        if not data:
            logger.warning("Webhook recebido sem dados JSON")
            return jsonify({'error': 'No JSON data'}), 400
        
        logger.info(f"Webhook recebido: {json.dumps(data, indent=2)}")
        
        # Extrair informações do webhook
        event_type = data.get('type', 'unknown')
        payment_data = data.get('data', {})
        payment_id = payment_data.get('id') or data.get('id')
        status = payment_data.get('status', 'unknown')
        amount = payment_data.get('amount', 0)
        
        # Salvar webhook no banco de dados
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO webhooks (event_type, payment_id, status, amount, raw_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (event_type, payment_id, status, amount, json.dumps(data)))
        
        # Buscar informações do pagamento PIX
        cursor.execute('SELECT user_id, amount FROM pix_payments WHERE payment_id = ?', (payment_id,))
        pix_payment = cursor.fetchone()
        
        if pix_payment:
            user_id, pix_amount = pix_payment
            
            # Se o pagamento foi aprovado/pago
            if status.upper() in ['PAID', 'APPROVED', 'COMPLETED', 'SUCCESS']:
                logger.info(f"Pagamento PIX aprovado: {payment_id} - Usuário: {user_id} - Valor: {pix_amount}")
                
                # Atualizar status do pagamento
                update_payment_status(payment_id, 'completed')
                
                # Adicionar saldo ao usuário
                if add_balance_to_user(user_id, pix_amount):
                    logger.info(f"Saldo de R$ {pix_amount} adicionado ao usuário {user_id}")
                else:
                    logger.error(f"Falha ao adicionar saldo ao usuário {user_id}")
            
            elif status.upper() in ['FAILED', 'CANCELLED', 'REJECTED']:
                logger.info(f"Pagamento PIX falhou: {payment_id} - Status: {status}")
                update_payment_status(payment_id, 'failed')
        
        conn.commit()
        conn.close()
        
        # Retornar resposta de sucesso
        return jsonify({'status': 'success', 'message': 'Webhook processado'}), 200
        
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/webhook/test', methods=['GET', 'POST'])
def test_webhook():
    """Endpoint de teste para verificar se o webhook está funcionando"""
    if request.method == 'GET':
        return jsonify({
            'status': 'active',
            'message': 'Webhook server is running',
            'timestamp': datetime.now().isoformat()
        })
    else:
        data = request.get_json() or {}
        logger.info(f"Teste webhook recebido: {data}")
        return jsonify({'status': 'received', 'data': data})

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de verificação de saúde"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Inicializar banco de dados
    init_webhook_db()
    
    # Executar servidor Flask
    logger.info("Iniciando servidor webhook...")
    app.run(host='0.0.0.0', port=5000, debug=True)