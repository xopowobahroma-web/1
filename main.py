import os
import sys
import logging
from flask import Flask, request
import telebot

# Настройка логирования
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не задан! Проверьте переменные окружения на Render.")
    sys.exit(1)

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- Обработчики команд бота ---
@bot.message_handler(commands=['start'])
def start(message):
    logger.info(f"Команда /start от {message.chat.id}")
    bot.reply_to(message, "Привет! Я бот, работающий на Render!")

@bot.message_handler(func=lambda message: True)
def echo(message):
    logger.info(f"Сообщение от {message.chat.id}: {message.text}")
    bot.reply_to(message, f"Ты написал: {message.text}")

# --- Вебхук для приема обновлений ---
@app.route('/webhook', methods=['POST'])
def webhook():
    logger.debug("🔥 Вебхук вызван!")
    try:
        json_str = request.get_data().decode('utf-8')
        logger.debug(f"Получен JSON: {json_str[:200]}...")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        logger.debug("✅ Update обработан")
    except Exception as e:
        logger.exception("❌ Ошибка при обработке вебхука")
        return 'error', 500
    return 'ok', 200

# --- Корневой путь для проверки ---
@app.route('/')
def index():
    logger.debug("👋 Корневой путь '/'")
    return "Bot is running!"
