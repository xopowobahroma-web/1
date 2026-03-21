import os
import sys
import logging
import requests
from flask import Flask, request
from database_sync import Database
from ai_integration import LLMClient

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

# --- LLM клиент (Mistral) ---
try:
    llm_client = LLMClient()
    logger.info("✅ LLM клиент инициализирован")
except Exception as e:
    logger.exception("❌ Ошибка инициализации LLM клиента")
    sys.exit(1)

app = Flask(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Хранилище для сбора длинных текстов (ключ – chat_id)
history_buffer = {}

def send_message(chat_id: int, text: str):
    logger.debug(f"Отправка сообщения в чат {chat_id}: {text[:50]}...")
    url = f"{TELEGRAM_API_URL}/sendMessage"
    
    # Убираем Markdown-разметку
    clean_text = text.replace('**', '').replace('*', '').replace('`', '').replace('_', '').replace('~~', '').replace('![', '').replace('](', ' ').replace(')', '')
    
    payload = {'chat_id': chat_id, 'text': clean_text}
    try:
        r = requests.post(url, json=payload, timeout=5)
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

    logger.debug(f"Обработка сообщения от {user_telegram_id}: {text[:50]}...")

    # Работа с пользователем в БД
    try:
        user = db.get_or_create_user(user_telegram_id)
        if user is None:
            raise Exception("User creation failed")
        user_id = user['id']
        logger.debug(f"Пользователь {user_id} обработан")
    except Exception as e:
        logger.exception("Ошибка БД")
        send_message(chat_id, "❌ Ошибка доступа к базе данных.")
        return 'ok', 200

    # Сохраняем сообщение пользователя (кроме команд, которые не должны попадать в историю)
    if not text.startswith('/'):
        try:
            db.add_conversation(user_id, 'user', text, None)
            logger.debug("Сообщение пользователя сохранено")
        except Exception as e:
            logger.exception("Ошибка сохранения диалога")

    # --- Команда /remember_start (начать сбор истории) ---
    if text == '/remember_start':
        history_buffer[chat_id] = []
        send_message(chat_id, "📝 Отправляй текст частями. Когда закончишь, напиши /remember_stop [ключ]")
        return 'ok', 200

    # --- Команда /remember_stop [ключ] (сохранить накопленное) ---
    if text.startswith('/remember_stop'):
        if chat_id not in history_buffer or not history_buffer[chat_id]:
            send_message(chat_id, "❌ Нет накопленного текста. Сначала отправь /remember_start")
            return 'ok', 200

        # Разбираем ключ (если есть)
        parts = text.split(maxsplit=1)
        key = parts[1].strip() if len(parts) > 1 else 'история'

        full_text = "\n".join(history_buffer[chat_id])
        try:
            db.add_memory(user_id, key, full_text)
            send_message(chat_id, f"✅ История сохранена под ключом «{key}»")
        except Exception as e:
            logger.exception("Ошибка сохранения памяти")
            send_message(chat_id, "❌ Не удалось сохранить историю.")

        # Очищаем буфер
        del history_buffer[chat_id]
        return 'ok', 200

    # --- Если пользователь в режиме сбора истории ---
    if chat_id in history_buffer:
        history_buffer[chat_id].append(text)
        # Не отвечаем, просто копим
        return 'ok', 200

    # --- Команда /remember для быстрого сохранения одного факта ---
    if text.startswith('/remember'):
        try:
            parts = text.split(':', 1)
            if len(parts) == 2:
                key = parts[0].replace('/remember', '').strip()
                value = parts[1].strip()
                if key and value:
                    db.add_memory(user_id, key, value)
                    send_message(chat_id, f"✅ Запомнил: {key} — {value}")
                else:
                    send_message(chat_id, "❌ Используй: /remember ключ: значение")
            else:
                send_message(chat_id, "❌ Используй: /remember ключ: значение")
        except Exception as e:
            logger.exception("Ошибка при сохранении памяти")
            send_message(chat_id, "❌ Не удалось сохранить.")
        return 'ok', 200

    # --- Команда /start ---
    if text.startswith('/start'):
        reply = (f"Привет, {first_name}! Я твой помощник.\n\n"
                 "📌 Как я могу помочь?\n"
                 "Я помню историю диалога и могу запоминать важные факты о тебе.\n\n"
                 "Команды:\n"
                 "/remember ключ: значение – сохранить один факт\n"
                 "/remember_start – начать ввод длинной истории (например, биографии)\n"
                 "/remember_stop [ключ] – закончить ввод и сохранить историю\n\n"
                 "Просто общайся со мной – я буду учитывать всё, что ты рассказал.")
        send_message(chat_id, reply)
        try:
            db.add_conversation(user_id, 'assistant', reply, None)
        except Exception as e:
            logger.exception("Ошибка сохранения ответа")
        return 'ok', 200

    # --- Обычное текстовое сообщение ---
    if text:
        # Формируем контекст: сначала долговременная память, потом последние диалоги
        context = "Ты — эксперт в области сомнологии, химических зависимостей и психологии. Отвечай кратко и по делу, используя историю диалога и долговременные факты о пользователе.\n\n"

        # Добавляем все сохранённые факты из памяти
        try:
            memories = db.get_all_memories(user_id)
            if memories:
                context += "Долговременные факты о пользователе:\n"
                for mem in memories:
                    context += f"- {mem['key']}: {mem['value']}\n"
                context += "\n"
        except Exception as e:
            logger.exception("Ошибка получения памяти")

        # Добавляем последние сообщения
        try:
            convs = db.get_recent_conversations(user_id, limit=5)
            if convs:
                context += "Последние сообщения:\n"
                for c in convs:
                    context += f"{c['role']}: {c['message']}\n"
        except Exception as e:
            logger.exception("Ошибка получения истории")

        # Получаем ответ от нейросети
        logger.debug("Запрос к LLM...")
        reply = llm_client.ask(text, context)
        logger.debug(f"Ответ от LLM получен: {reply[:100]}...")

        send_message(chat_id, reply)
        try:
            db.add_conversation(user_id, 'assistant', reply, None)
            logger.debug("Ответ LLM сохранён в БД")
        except Exception as e:
            logger.exception("Ошибка сохранения ответа")

    return 'ok', 200

@app.route('/')
def index():
    return "Bot is running!"
