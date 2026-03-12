import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import Database

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()

@dp.startup()
async def on_startup():
    await db.connect()
    print("✅ Бот запущен, БД подключена")

@dp.shutdown()
async def on_shutdown():
    await db.close()
    print("👋 Бот остановлен")

# Простой обработчик команд
@dp.message()
async def echo(message):
    await message.answer("Привет! Я работаю и подключён к БД.")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))