from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from database import Database
from ai_integration import ask_ai

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, db: Database):
    user = await db.get_or_create_user(message.from_user.id)
    await message.answer(
        "Привет! Я помогу тебе наладить режим сна и следить за самочувствием.\n"
        "Я буду присылать напоминания и задавать вопросы. Ты также можешь писать мне в любое время.\n\n"
        "Основные команды:\n"
        "/sleep — записать сон\n"
        "/wakeup — отметить пробуждение\n"
        "/mood — оценить настроение\n"
        "/stats — статистика"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Я помогаю следить за сном и настроением. Просто пиши мне, что ты чувствуешь, или используй команды."
    )

# Обработка всех текстовых сообщений (не команд)
@router.message(F.text)
async def handle_text(message: Message, db: Database):
    user = await db.get_or_create_user(message.from_user.id)
    answer = await ask_ai(user['id'], message.text, db)
    await message.answer(answer, parse_mode="HTML")