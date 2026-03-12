import os
import sys
import json
import logging
import requests
from flask import Flask, request
from database_sync import Database
from ai_integration import HuggingFaceClient

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Инициализация базы данных ---
try:
    db = Database()
    logger.info("✅ База данных инициализирована")
except Exception as e:
    logger.exception("❌ Ошибка инициализации БД")
    sys.exit(1)

# --- Токен бота ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не задан!")
    sys.exit(1)

# --- Hugging Face клиент ---
try:
    hf_client = HuggingFaceClient()
    logger.info("✅ Hugging Face клиент инициализирован")
except Exception as e:
    logger.exception("❌ Ошибка инициализации Hugging Face")
    sys.exit(1)

app = Flask(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id: int, text: str):
    """Отправляет сообщение через Telegram API."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
        logger.debug(f"✅ Сообщение отправлено в чат {chat_id}")
    except Exception as e:
        logger.exception(f"❌ Ошибка отправки сообщения: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    logger.debug("🔥 Вебхук вызван")
    try:
        update = request.get_json()
        logger.debug(f"Получен update: {update}")
    except Exception as e:
        logger.exception("❌ Ошибка парсинга JSON")
        return 'error', 400

    if 'message' not in update:
        return 'ok', 200

    msg = update['message']
    chat_id = msg['chat']['id']
    text = msg.get('text', '')
    user_telegram_id = msg['from']['id']
    first_name = msg['from'].get('first_name', '')

    # Получаем или создаём пользователя в БД
    try:
        user = db.get_or_create_user(user_telegram_id)
        if user is None:
            raise Exception("User creation returned None")
        user_id = user['id']
        logger.debug(f"Пользователь {user_id} обработан")
    except Exception as e:
        logger.exception("Ошибка работы с БД")
        send_message(chat_id, "❌ Ошибка доступа к базе данных. Попробуй позже.")
        return 'ok', 200

    # Сохраняем сообщение пользователя
    try:
        db.add_conversation(user_id, 'user', text, None)
    except Exception as e:
        logger.exception("Ошибка сохранения диалога")

    # Обработка команды /start
    if text.startswith('/start'):
        reply = f"Привет, {first_name}! Я твой помощник по сну, настроению и психологии. Задавай любые вопросы."
        send_message(chat_id, reply)
        try:
            db.add_conversation(user_id, 'assistant', reply, None)
        except Exception as e:
            logger.exception("Ошибка сохранения ответа")
        return 'ok', 200

    # Обычное текстовое сообщение
    if text:
        context = "Ты — эксперт в области сомнологии, химических зависимостей и психологии. Отвечай кратко и по делу, используя историю диалога.\n\n"
        try:
            convs = db.get_recent_conversations(user_id, limit=5)
            if convs:
                context += "Последние сообщения:\n"
                for c in convs:
                    context += f"{c['role']}: {c['message']}\n"
        except Exception as e:
            logger.exception("Ошибка получения истории")

        try:
            reply = hf_client.ask(text, context)
        except Exception as e:
            logger.exception("Ошибка вызова Hugging Face")
            reply = "Извини, сейчас я не могу ответить. Попробуй позже."

        send_message(chat_id, reply)
        try:
            db.add_conversation(user_id, 'assistant', reply, None)
        except Exception as e:
            logger.exception("Ошибка сохранения ответа")

    return 'ok', 200

@app.route('/')
def index():
    logger.debug("👋 Корневой путь '/'")
    return "Bot is running!"

if __name__ == '__main__':
    app.run()
