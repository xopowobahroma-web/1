from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import Database
from datetime import datetime
import pytz
from config import TIMEZONE

router = Router()

@router.callback_query(F.data.startswith("mental_load:"))
async def process_mental_load(callback: CallbackQuery, db: Database):
    level = int(callback.data.split(":")[1])
    user = await db.get_or_create_user(callback.from_user.id)
    await db.add_mood_log(user['id'], stress_level=level)
    await callback.message.edit_text(f"Записал: ментальная нагрузка {level}. Были ли мысли о веществах или тяга к работе?", 
                                     reply_markup=thoughts_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("thoughts:"))
async def process_thoughts(callback: CallbackQuery, db: Database):
    answer = callback.data.split(":")[1]
    user = await db.get_or_create_user(callback.from_user.id)
    thoughts = (answer == "yes")
    # Обновим последнюю запись настроения? Упростим: создадим отдельную запись или обновим.
    # Для простоты создадим новую запись с thoughts_about_use
    # Но мы не знаем stress_level. Поэтому лучше сохранять отдельно.
    await db.add_trigger(user['id'], trigger_text="Мысли об употреблении" if thoughts else "Нет мыслей", category="thoughts")
    await callback.message.edit_text("Спасибо за ответ. Постарайся расслабиться перед сном.")
    await callback.answer()

# Аналогично другие callback'и