from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
import pytz
from database import Database
from keyboards import sleep_quality_keyboard, wakeup_reason_keyboard
from config import TIMEZONE

router = Router()

class SleepStates(StatesGroup):
    waiting_sleep_start = State()
    waiting_wakeup_time = State()
    waiting_quality = State()
    waiting_trigger = State()

@router.message(Command("sleep"))
async def cmd_sleep(message: Message, state: FSMContext):
    await message.answer("Когда лёг спать? Отправь время в формате ЧЧ:ММ или просто нажми /now для текущего времени.")
    await state.set_state(SleepStates.waiting_sleep_start)

@router.message(Command("now"))
async def cmd_now(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == SleepStates.waiting_sleep_start:
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        await state.update_data(sleep_start=now)
        await message.answer("Что делал перед сном? (кратко)", reply_markup=None)
        await state.set_state(SleepStates.waiting_trigger)
    else:
        await message.answer("Сейчас нет активного ожидания времени.")

@router.message(SleepStates.waiting_sleep_start)
async def process_sleep_start(message: Message, state: FSMContext):
    try:
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        time_str = message.text.strip()
        sleep_start = datetime.strptime(time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day, tzinfo=tz
        )
        if sleep_start > now:
            # Значит, время относится к предыдущему дню
            sleep_start -= timedelta(days=1)
        await state.update_data(sleep_start=sleep_start)
        await message.answer("Что делал перед сном? (кратко)")
        await state.set_state(SleepStates.waiting_trigger)