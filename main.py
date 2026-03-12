import os
import sys
import logging
from flask import Flask, request
import telebot
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

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ---------- ПРОСТЕЙШИЙ ОБРАБОТЧИК ДЛЯ ТЕСТА ----------
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    logger.debug("🔥🔥🔥 HANDLE_MESSAGE ВЫЗВАН (ТЕСТ) 🔥🔥🔥")
    try:
        bot.reply_to(message, "Привет! Это тестовый ответ. Бот работает.")
    except Exception as e:
        logger.exception("Ошибка при отправке ответа")
    return

# ---------- ДИАГНОСТИКА ----------
logger.debug(f"ИТОГО обработчиков: {len(bot.message_handlers)}")
for i, h in enumerate(bot.message_handlers):
    logger.debug(f"Финальный обработчик {i}: {h}")

# ---------- ВЕБХУК ----------
@app.route('/webhook', methods=['POST'])
def webhook():
    logger.debug("🔥 Вебхук вызван!")
    try:
        json_str = request.get_data().decode('utf-8')
        logger.debug(f"Получен JSON: {json_str[:200]}...")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        logger.debug("✅ process_new_updates завершён")
    except Exception as e:
        logger.exception("❌ Ошибка при обработке вебхука")
        return 'error', 500
    return 'ok', 200

@app.route('/')
def index():
    logger.debug("👋 Корневой путь '/'")
    return "Bot is running!"

logger.info("🎯 main.py загружен")
