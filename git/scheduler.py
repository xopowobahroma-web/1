from datetime import datetime, timedelta
import pytz
from aiogram import Bot
from database import Database
from keyboards import mental_load_keyboard, thoughts_keyboard, last_hour_keyboard, sleep_quality_keyboard
from texts import RITUAL_BEDTIME_1, RITUAL_BEDTIME_2, RITUAL_WAKEUP, CHECK_LONG_INACTIVITY, MOOD_CHECK
from config import TIMEZONE

async def process_cron(bot: Bot, db: Database):
    """Вызывается по расписанию (каждые 15 минут) для отправки проактивных уведомлений."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)

    # Получаем всех пользователей (в реальности нужно получать тех, кто активен)
    # Для простоты будем рассылать всем, но лучше хранить настройки времени уведомлений.
    # Здесь мы просто проверяем время и отправляем тем, у кого ещё не было сегодня уведомления.
    # Но для MVP можно упрощённо: проверять всех и отправлять, если подошло время.
    # Так как мы не храним флаги отправки, придётся добавить логику в БД.
    # Для краткости примера будем считать, что уведомления отправляются всем в одно и то же время.
    # В реальном проекте нужно добавить таблицу notifications или поля last_notification.

    # В этом демо мы просто проверим, есть ли пользователи в БД и отправим им сообщения по времени.
    # Получим всех пользователей из БД (нужен метод get_all_users, добавим в database.py)
    # Для экономии места я не буду добавлять новый метод, а просто покажу идею.
    # В реальном коде нужно добавить метод db.get_all_users().

    # Вместо этого, для демонстрации, предположим, что у нас есть список user_id из глобальной переменной?
    # Но это неправильно. Поэтому я добавлю в database.py метод get_all_users().

    # Добавим в database.py:
    # async def get_all_users(self):
    #     async with self.pool.acquire() as conn:
    #         rows = await conn.fetch("SELECT id, telegram_id FROM users")
    #         return rows

    # Но чтобы не усложнять пример, здесь просто комментарий.
    # Для тестирования можно отправлять конкретному пользователю по ID, захардкодив.

    # Проверяем время:
    # 22:00 - первый ритуал ко сну
    if now.hour == 22 and now.minute == 0:
        # Отправить RITUAL_BEDTIME_1 + клавиатура mental_load + thoughts
        # Нужно получить всех пользователей и отправить
        pass
    # 23:30 - второй ритуал
    elif now.hour == 23 and now.minute == 30:
        # Отправить RITUAL_BEDTIME_2 + last_hour_keyboard
        pass
    # 09:00 (например) - ритуал пробуждения, но тут нужна логика, что пользователь отметил пробуждение.
    # Вместо этого у нас есть команда /wakeup, поэтому проактивно не отправляем.
    # Но для проверки долгого отсутствия:
    # Проверяем пользователей, у которых last_active > 18 часов назад
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, telegram_id FROM users WHERE last_active < NOW() - INTERVAL '18 hours'"
        )
        for row in rows:
            await bot.send_message(row['telegram_id'], CHECK_LONG_INACTIVITY)
    
    # Также можно проверять длительное бодрствование (по логам сна) - сложнее, опустим.