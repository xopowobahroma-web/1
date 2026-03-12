import os
import sys
import logging
from flask import Flask, request
import telebot
from telebot import types
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

# --- Вспомогательные функции ---
def get_user_id_or_start_dialog(message):
    try:
        user = db.get_or_create_user(message.from_user.id)
        return user['id']
    except Exception as e:
        logger.exception("Ошибка получения пользователя")
        bot.reply_to(message, "❌ Ошибка доступа к базе. Попробуй позже.")
        return None

# --- Обработчик отмены ---
@bot.message_handler(commands=['cancel'])
def cancel_dialog(message):
    logger.debug("🔥 cancel_dialog вызван")
    bot.reply_to(message, "❌ Диалог отменён. Можешь начать заново.")

# --- Словари для временного хранения данных диалогов ---
sleep_data = {}
mood_data = {}
trigger_data = {}

# ---------- КОМАНДА /sleep ----------
@bot.message_handler(commands=['sleep'])
def cmd_sleep(message):
    logger.debug("🔥 cmd_sleep вызван")
    user_id = get_user_id_or_start_dialog(message)
    if not user_id:
        return
    chat_id = message.chat.id
    sleep_data[chat_id] = {'user_id': user_id, 'step': 'start_time'}
    bot.reply_to(message, "🌙 Введи время начала сна (например, 2025-03-12 23:00 или оставь пустым для текущего времени):")
    bot.register_next_step_handler(message, process_sleep_start)

# ... (весь код команд /sleep, /mood, /triggers, /start, /stats без изменений, как в предыдущем сообщении)
# Для краткости я не буду повторять их здесь, но они должны быть такими же, как в предыдущем полном листинге.
# Главное – после определения всех обработчиков добавить следующую диагностику.

# ---------- ДИАГНОСТИКА РЕГИСТРАЦИИ ОБРАБОТЧИКОВ ----------
logger.debug(f"Всего обработчиков команд: {len(bot.message_handlers)}")
for i, handler in enumerate(bot.message_handlers):
    logger.debug(f"Обработчик {i}: {handler}")

# ---------- ОСНОВНОЙ ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ ----------
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    logger.debug("🔥🔥🔥 HANDLE_MESSAGE ВЫЗВАН 🔥🔥🔥")
    # Проверяем, не находится ли пользователь в активном диалоге
    if message.chat.id in sleep_data or message.chat.id in mood_data or message.chat.id in trigger_data:
        logger.debug("Пользователь в диалоге, игнорируем обычный обработчик")
        return

    logger.info(f"Обработка обычного сообщения от {message.chat.id}: {message.text[:50]}...")
    try:
        user = db.get_or_create_user(message.from_user.id)
        user_id = user['id']

        db.add_conversation(user_id, 'user', message.text, None)

        context = "Ты — эксперт в области сомнологии, химических зависимостей и психологии. Твоя задача — помогать пользователю анализировать его сон, настроение и триггеры, используя глубокое понимание этих тем. Отвечай информативно, но кратко. Используй данные из истории диалога для персонализации.\n\n"

        convs = db.get_recent_conversations(user_id, limit=5)
        if convs:
            context += "Последние сообщения:\n"
            for c in convs:
                context += f"{c['role']}: {c['message']}\n"

        moods = db.get_recent_mood(user_id, limit=1)
        if moods:
            m = moods[0]
            context += f"Последнее настроение: стресс {m['stress_level']}, мысли об употреблении: {m['thoughts_about_use']}\n"

        sleeps = db.get_sleep_stats(user_id, days=7)
        if sleeps:
            last_sleep = sleeps[-1]
            context += f"Последний сон: начался {last_sleep['sleep_start']}, закончился {last_sleep['sleep_end']}\n"

        reply = hf_client.ask(message.text, context)
        db.add_conversation(user_id, 'assistant', reply, None)
        bot.reply_to(message, reply)
    except Exception as e:
        logger.exception("Ошибка при обработке обычного сообщения")
        bot.reply_to(message, "Произошла внутренняя ошибка, попробуй позже.")

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

logger.info("🎯 main.py полностью загружен, ожидаем запросы")
