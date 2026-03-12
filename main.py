import os
import sys
import logging
from flask import Flask, request
import telebot
from database_sync import Database  # импортируем наш синхронный класс

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Инициализация базы данных ---
try:
    db = Database()
    logger.info("✅ База данных инициализирована")
except Exception as e:
    logger.exception("❌ Ошибка инициализации БД")
    sys.exit(1)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не задан!")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- Обработчики команд ---
@bot.message_handler(commands=['start'])
def start(message):
    logger.info(f"Команда /start от {message.chat.id}")
    try:
        # Сохраняем или обновляем пользователя в базе
        user = db.get_or_create_user(message.from_user.id)
        logger.debug(f"Пользователь {user['telegram_id']} обработан")
        bot.reply_to(message, f"Привет! Ты в системе. Твой ID: {user['id']}")
    except Exception as e:
        logger.exception("Ошибка при обработке /start")
        bot.reply_to(message, "Произошла ошибка, попробуй позже.")

@bot.message_handler(commands=['stats'])
def stats(message):
    logger.info(f"Команда /stats от {message.chat.id}")
    try:
        # Получаем последние 5 записей настроения
        moods = db.get_recent_mood(message.from_user.id, limit=3)
        if moods:
            reply = "Последние записи настроения:\n"
            for m in moods:
                reply += f"{m['timestamp']}: стресс {m['stress_level']}, мысль о использовании: {m['thoughts_about_use']}\n"
        else:
            reply = "У тебя пока нет записей о настроении."
        bot.reply_to(message, reply)
    except Exception as e:
        logger.exception("Ошибка при обработке /stats")
        bot.reply_to(message, "Не удалось получить статистику.")

@bot.message_handler(func=lambda message: True)
def echo(message):
    logger.info(f"Сообщение от {message.chat.id}: {message.text}")
    try:
        # Сохраняем диалог в базу
        db.add_conversation(
            user_id=message.from_user.id,
            role="user",
            message=message.text,
            context_used=None
        )
        bot.reply_to(message, f"Ты написал: {message.text}")
    except Exception as e:
        logger.exception("Ошибка при сохранении сообщения")
        bot.reply_to(message, "Не удалось сохранить сообщение.")

# --- Вебхук ---
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

logger.info("🎯 main.py полностью загружен, ожидаем запросы")
