import sys
import os
import logging
from flask import Flask, request
import telebot

# Настройка логирования в stderr (попадет в server log) и в файл
log_file = '/tmp/bot_debug.log'
with open(log_file, 'a') as f:
    f.write("🚀 Загрузка final_bot.py\n")

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    with open(log_file, 'a') as f:
        f.write("❌ BOT_TOKEN не задан\n")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Бот работает!")

@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.reply_to(message, f"Ты написал: {message.text}")

@app.route('/webhook', methods=['POST'])
def webhook():
    with open(log_file, 'a') as f:
        f.write("🔥 Вебхук вызван\n")
    try:
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        with open(log_file, 'a') as f:
            f.write("✅ Update обработан\n")
    except Exception as e:
        with open(log_file, 'a') as f:
            f.write(f"❌ Ошибка: {e}\n")
        return 'error', 500
    return 'ok', 200

@app.route('/')
def index():
    return "Бот работает"