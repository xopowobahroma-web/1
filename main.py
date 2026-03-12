import os
import sys
import logging
from flask import Flask, request
import telebot
from telebot import types
from database_sync import Database  # наш синхронный класс

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Инициализация базы ---
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

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- Вспомогательные функции для диалогов ---
def get_user_id_or_start_dialog(message):
    """Проверяет, есть ли пользователь в БД, и возвращает его id или начинает диалог с /start"""
    try:
        user = db.get_or_create_user(message.from_user.id)
        return user['id']
    except Exception as e:
        logger.exception("Ошибка получения пользователя")
        bot.reply_to(message, "❌ Ошибка доступа к базе. Попробуй позже.")
        return None

# --- Обработчик отмены диалога ---
@bot.message_handler(commands=['cancel'])
def cancel_dialog(message):
    bot.reply_to(message, "❌ Диалог отменён. Можешь начать заново.")
    # Здесь можно сбросить состояние, но мы не храним состояния, поэтому просто ответ

# --- КОМАНДА /sleep ---
# Храним временные данные в словаре, привязанном к chat.id (простой способ без состояний)
sleep_data = {}

@bot.message_handler(commands=['sleep'])
def cmd_sleep(message):
    user_id = get_user_id_or_start_dialog(message)
    if not user_id:
        return
    chat_id = message.chat.id
    # Инициализируем словарь для этого пользователя
    sleep_data[chat_id] = {'user_id': user_id, 'step': 'start_time'}
    bot.reply_to(message, "🌙 Введи время начала сна (например, 2025-03-12 23:00 или оставь пустым для текущего времени):")
    bot.register_next_step_handler(message, process_sleep_start)

def process_sleep_start(message):
    chat_id = message.chat.id
    if message.text == '/cancel':
        cancel_dialog(message)
        return
    # Сохраняем время начала
    from datetime import datetime
    try:
        if message.text.strip():
            sleep_start = datetime.fromisoformat(message.text.strip())
        else:
            sleep_start = None  # позже установим как NOW() в БД? Но в add_sleep_log может быть None, тогда NULL
        sleep_data[chat_id]['start'] = sleep_start
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат. Попробуй ещё раз или отправь /cancel")
        bot.register_next_step_handler(message, process_sleep_start)
        return
    sleep_data[chat_id]['step'] = 'end_time'
    bot.reply_to(message, "⏰ Введи время окончания сна (аналогично):")
    bot.register_next_step_handler(message, process_sleep_end)

def process_sleep_end(message):
    chat_id = message.chat.id
    if message.text == '/cancel':
        cancel_dialog(message)
        return
    try:
        if message.text.strip():
            sleep_end = datetime.fromisoformat(message.text.strip())
        else:
            sleep_end = None
        sleep_data[chat_id]['end'] = sleep_end
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат. Попробуй ещё раз или отправь /cancel")
        bot.register_next_step_handler(message, process_sleep_end)
        return
    sleep_data[chat_id]['step'] = 'quality'
    bot.reply_to(message, "⭐ Оцени качество сна (1-5 или оставь пустым):")
    bot.register_next_step_handler(message, process_sleep_quality)

def process_sleep_quality(message):
    chat_id = message.chat.id
    if message.text == '/cancel':
        cancel_dialog(message)
        return
    quality = message.text.strip() if message.text.strip() else None
    sleep_data[chat_id]['quality'] = quality
    sleep_data[chat_id]['step'] = 'notes'
    bot.reply_to(message, "📝 Добавь заметки (или оставь пустым):")
    bot.register_next_step_handler(message, process_sleep_notes)

def process_sleep_notes(message):
    chat_id = message.chat.id
    if message.text == '/cancel':
        cancel_dialog(message)
        return
    notes = message.text.strip() if message.text.strip() else None
    sleep_data[chat_id]['notes'] = notes
    sleep_data[chat_id]['step'] = 'triggered_by'
    bot.reply_to(message, "🔔 Укажи, что вызвало пробуждение (или оставь пустым):")
    bot.register_next_step_handler(message, process_sleep_triggered)

def process_sleep_triggered(message):
    chat_id = message.chat.id
    if message.text == '/cancel':
        cancel_dialog(message)
        return
    triggered_by = message.text.strip() if message.text.strip() else None
    data = sleep_data.pop(chat_id, None)
    if not data:
        bot.reply_to(message, "❌ Ошибка данных. Начни заново.")
        return
    try:
        db.add_sleep_log(
            user_id=data['user_id'],
            sleep_start=data.get('start'),
            sleep_end=data.get('end'),
            quality=data['quality'],
            notes=data['notes'],
            triggered_by=triggered_by
        )
        bot.reply_to(message, "✅ Сон записан!")
    except Exception as e:
        logger.exception("Ошибка сохранения сна")
        bot.reply_to(message, "❌ Ошибка при сохранении. Попробуй позже.")

# --- КОМАНДА /mood ---
mood_data = {}

@bot.message_handler(commands=['mood'])
def cmd_mood(message):
    user_id = get_user_id_or_start_dialog(message)
    if not user_id:
        return
    chat_id = message.chat.id
    mood_data[chat_id] = {'user_id': user_id, 'step': 'stress'}
    bot.reply_to(message, "📊 Уровень стресса (от 1 до 10):")
    bot.register_next_step_handler(message, process_mood_stress)

def process_mood_stress(message):
    chat_id = message.chat.id
    if message.text == '/cancel':
        cancel_dialog(message)
        return
    try:
        stress = int(message.text.strip())
        if not 1 <= stress <= 10:
            raise ValueError
        mood_data[chat_id]['stress'] = stress
    except:
        bot.reply_to(message, "❌ Введи число от 1 до 10 или /cancel")
        bot.register_next_step_handler(message, process_mood_stress)
        return
    mood_data[chat_id]['step'] = 'mood_text'
    bot.reply_to(message, "😊 Опиши своё настроение словами (или оставь пустым):")
    bot.register_next_step_handler(message, process_mood_text)

def process_mood_text(message):
    chat_id = message.chat.id
    if message.text == '/cancel':
        cancel_dialog(message)
        return
    mood_text = message.text.strip() if message.text.strip() else None
    mood_data[chat_id]['mood_text'] = mood_text
    mood_data[chat_id]['step'] = 'thoughts'
    bot.reply_to(message, "💭 Были мысли об употреблении? (да/нет или оставь пустым для нет)")
    bot.register_next_step_handler(message, process_mood_thoughts)

def process_mood_thoughts(message):
    chat_id = message.chat.id
    if message.text == '/cancel':
        cancel_dialog(message)
        return
    text = message.text.strip().lower()
    thoughts = True if text in ['да', 'yes', '1'] else False
    data = mood_data.pop(chat_id, None)
    if not data:
        bot.reply_to(message, "❌ Ошибка данных. Начни заново.")
        return
    try:
        db.add_mood_log(
            user_id=data['user_id'],
            stress_level=data['stress'],
            mood=data['mood_text'],
            thoughts_about_use=thoughts
        )
        bot.reply_to(message, "✅ Настроение записано!")
    except Exception as e:
        logger.exception("Ошибка сохранения настроения")
        bot.reply_to(message, "❌ Ошибка при сохранении.")

# --- КОМАНДА /triggers ---
trigger_data = {}

@bot.message_handler(commands=['triggers'])
def cmd_trigger(message):
    user_id = get_user_id_or_start_dialog(message)
    if not user_id:
        return
    chat_id = message.chat.id
    trigger_data[chat_id] = {'user_id': user_id, 'step': 'text'}
    bot.reply_to(message, "⚡ Введи текст триггера:")
    bot.register_next_step_handler(message, process_trigger_text)

def process_trigger_text(message):
    chat_id = message.chat.id
    if message.text == '/cancel':
        cancel_dialog(message)
        return
    text = message.text.strip()
    if not text:
        bot.reply_to(message, "❌ Текст не может быть пустым. Попробуй ещё раз или /cancel")
        bot.register_next_step_handler(message, process_trigger_text)
        return
    trigger_data[chat_id]['text'] = text
    trigger_data[chat_id]['step'] = 'category'
    bot.reply_to(message, "📂 Категория (например, 'еда', 'стресс', или оставь пустым):")
    bot.register_next_step_handler(message, process_trigger_category)

def process_trigger_category(message):
    chat_id = message.chat.id
    if message.text == '/cancel':
        cancel_dialog(message)
        return
    category = message.text.strip() if message.text.strip() else None
    data = trigger_data.pop(chat_id, None)
    if not data:
        bot.reply_to(message, "❌ Ошибка данных. Начни заново.")
        return
    try:
        db.add_trigger(
            user_id=data['user_id'],
            trigger_text=data['text'],
            category=category
        )
        bot.reply_to(message, "✅ Триггер записан!")
    except Exception as e:
        logger.exception("Ошибка сохранения триггера")
        bot.reply_to(message, "❌ Ошибка при сохранении.")

# --- КОМАНДА /start (обновлена с учётом базы) ---
@bot.message_handler(commands=['start'])
def start(message):
    logger.info(f"Команда /start от {message.chat.id}")
    try:
        user = db.get_or_create_user(message.from_user.id)
        bot.reply_to(message, f"Привет! Ты в системе. Твой ID: {user['id']}\n"
                              "Доступные команды:\n"
                              "/sleep — записать сон\n"
                              "/mood — записать настроение\n"
                              "/triggers — добавить триггер\n"
                              "/stats — статистика\n"
                              "/cancel — отменить текущий диалог")
    except Exception as e:
        logger.exception("Ошибка при обработке /start")
        bot.reply_to(message, "Произошла ошибка, попробуй позже.")

# --- КОМАНДА /stats (расширенная) ---
@bot.message_handler(commands=['stats'])
def stats(message):
    logger.info(f"Команда /stats от {message.chat.id}")
    try:
        user = db.get_or_create_user(message.from_user.id)
        moods = db.get_recent_mood(user['id'], limit=3)
        # Можно добавить статистику по сну и триггерам, но для простоты оставим так
        reply = "📊 **Последние записи настроения:**\n"
        if moods:
            for m in moods:
                reply += f"• {m['timestamp']}: стресс {m['stress_level']}, мысли: {'да' if m['thoughts_about_use'] else 'нет'}\n"
        else:
            reply += "Нет данных о настроении.\n"

        # Сон (последние 3 записи)
        sleeps = db.get_sleep_stats(user['id'], days=30)  # последние 30 дней
        reply += "\n🌙 **Последние записи сна:**\n"
        if sleeps:
            for s in sleeps[-3:]:
                reply += f"• {s['sleep_start']} — {s['sleep_end']}\n"
        else:
            reply += "Нет данных о сне.\n"

        bot.reply_to(message, reply, parse_mode='Markdown')
    except Exception as e:
        logger.exception("Ошибка при обработке /stats")
        bot.reply_to(message, "Не удалось получить статистику.")

# --- Обработчик всех текстовых сообщений (если не команда и не в диалоге) ---
@bot.message_handler(func=lambda message: True)
def fallback(message):
    # Если сообщение не является командой и не обрабатывается в диалогах, просто игнорируем или отвечаем
    # Но чтобы не мешать диалогам, можно отвечать только если не в процессе
    # Упрощённо: отвечаем эхом, но это может мешать диалогам. Лучше напоминать о командах.
    bot.reply_to(message, "Используй команды: /start, /sleep, /mood, /triggers, /stats, /cancel")

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
