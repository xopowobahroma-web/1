import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Импортируем наши настройки и класс для работы с БД
from config import BOT_TOKEN, SUPABASE_DB_URL, SUPABASE_URL, SUPABASE_ANON_KEY
from database import Database

# Настраиваем базовое логирование, чтобы видеть ошибки
logging.basicConfig(level=logging.INFO)

# --- Инициализация ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()

# --- Обработчики команд (они остаются такими же) ---
@dp.message()
async def echo(message: types.Message):
    """Простой эхо-обработчик для проверки."""
    await message.answer("Привет! Я облачный бот и я работаю!")

# --- События запуска и остановки ---
@dp.startup()
async def on_startup() -> None:
    """Что сделать при запуске бота."""
    await db.connect()
    # Устанавливаем вебхук, чтобы Telegram знал, где наш бот живет
    webhook_url = f"https://{os.getenv('PA_USERNAME')}.pythonanywhere.com/webhook"
    await bot.set_webhook(webhook_url)
    print(f"✅ Бот запущен, вебхук установлен на {webhook_url}")

@dp.shutdown()
async def on_shutdown() -> None:
    """Что сделать при остановке бота."""
    await db.close()
    # Удаляем вебхук при остановке (хороший тон)
    await bot.delete_webhook()
    print("👋 Бот остановлен, вебхук удален")

# --- Создание aiohttp приложения (это и есть наш веб-сервер) ---
app = web.Application()

# Создаем обработчик для пути "/webhook"
webhook_requests_handler = SimpleRequestHandler(
    dispatcher=dp,
    bot=bot,
)
# Регистрируем его в нашем aiohttp приложении
webhook_requests_handler.register(app, path="/webhook")

# Настраиваем приложение
setup_application(app, dp, bot=bot)

# --- Точка входа для PythonAnywhere ---
# Именно эту переменную будет искать WSGI-сервер PythonAnywhere
application = app

# Этот блок нужен только для локального запуска (для отладки)
if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)