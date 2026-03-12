import os
import sys
import logging
from flask import Flask, request
import telebot

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Диагностика загрузки ---
logger.info("🚀 START: main.py загружается")

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не задан!")
    sys.exit(1)
else:
    logger.info(f"✅ BOT_TOKEN получен, длина {len(BOT_TOKEN)}")

# Инициализация бота
try:
    bot = telebot.TeleBot(BOT_TOKEN)
    logger.info("✅ Бот инициализирован")
except Exception as e:
    logger.exception("❌ Ошибка при инициализации бота")
    sys.exit(1)

app = Flask(__name__)
logger.info("✅ Flask приложение создано")

# --- Обработчики команд с логированием ---
@bot.message_handler(commands=['start'])
def start(message):
    logger.info(f"🔥🔥🔥 Обработчик start вызван! chat_id={message.chat.id}")
    bot.reply_to(message, "Привет! Я бот, работающий на Render!")

@bot.message_handler(func=lambda message: True)
def echo(message):
    logger.info(f"🔥🔥🔥 Обработчик echo вызван! текст={message.text}")
    bot.reply_to(message, f"Ты написал: {message.text}")

# --- Вебхук ---
@app.route('/webhook', methods=['POST'])
def webhook():
    logger.debug("🔥 Вебхук вызван!")
    try:
        json_str = request.get_data().decode('utf-8')
        logger.debug(f"Получен JSON: {json_str[:200]}...")
        update = telebot.types.Update.de_json(json_str)
        logger.debug("✅ Update распарсен, передаём боту...")
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

logger.info("🎯 main.py полностью загружен, ожидаем запросы")
