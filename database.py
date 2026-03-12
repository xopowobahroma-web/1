import asyncpg
from datetime import datetime
from config import SUPABASE_DB_URL

class Database:
    def __init__(self): # Исправлено: __init__
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(SUPABASE_DB_URL)

    async def close(self):
        if self.pool:
            await self.pool.close()

    # ----- Users -----
    async def get_or_create_user(self, telegram_id: int):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_id = $1", telegram_id # Исправлено: убран лишний пробел перед запятой
            )
            if not row:
                row = await conn.fetchrow(
                    "INSERT INTO users (telegram_id, last_active) VALUES ($1, NOW()) RETURNING *",
                    telegram_id # Исправлено: убран лишний пробел перед запятой
                )
            else:
                await conn.execute(
                    "UPDATE users SET last_active = NOW() WHERE telegram_id = $1",
                    telegram_id # Исправлено: убран лишний пробел перед запятой
                )
            return dict(row)

    async def update_last_active(self, user_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_active = NOW() WHERE id = $1", user_id # Исправлено: убран лишний пробел перед запятой
            )

    # ----- Sleep logs -----
    async def add_sleep_log(self, user_id: int, sleep_start: datetime = None, sleep_end: datetime = None,
                            quality: str = None, notes: str = None, triggered_by: str = None): # Исправлено: двоеточие перед with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sleep_logs 
                (user_id, sleep_start, sleep_end, quality, notes, triggered_by)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                user_id, sleep_start, sleep_end, quality, notes, triggered_by
            )

    # ----- Mood logs -----
    async def add_mood_log(self, user_id: int, stress_level: int, mood: str = None, thoughts_about_use: bool = False): # Исправлено: двоеточие перед str
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mood_logs (user_id, stress_level, mood, thoughts_about_use)
                VALUES ($1, $2, $3, $4)
                """,
                user_id, stress_level, mood, thoughts_about_use
            )

    # ----- Conversations -----
    async def add_conversation(self, user_id: int, role: str, message: str, context_used: dict = None): # Исправлено: двоеточие перед dict
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversations (user_id, role, message, context_used)
                VALUES ($1, $2, $3, $4)
                """,
                user_id, role, message, context_used
            )

    async def get_recent_conversations(self, user_id: int, limit: int = 20):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT role, message, timestamp FROM conversations
                WHERE user_id = $1 ORDER BY timestamp DESC LIMIT $2
                """,
                user_id, limit
            )
            return [dict(r) for r in reversed(rows)]  # возвращаем в хронологическом порядке

    # ----- Triggers -----
    async def add_trigger(self, user_id: int, trigger_text: str, category: str = None): # Исправлено: двоеточие перед str
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO triggers (user_id, trigger_text, category) VALUES ($1, $2, $3)",
                user_id, trigger_text, category # Исправлено: убран лишний пробел перед запятой
            )

    # ----- Агрегированные данные для контекста -----
    async def get_sleep_stats(self, user_id: int, days: int = 7):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT sleep_start, sleep_end FROM sleep_logs
                WHERE user_id = $1 AND sleep_start > NOW() - INTERVAL '1 day' * $2
                ORDER BY sleep_start
                """,
                user_id, days
            )
            # Здесь можно рассчитать среднюю продолжительность и т.п.
            return rows

    async def get_recent_mood(self, user_id: int, limit: int = 5): # Исправлено: двоеточие перед int
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT stress_level, mood, thoughts_about_use, timestamp
                FROM mood_logs WHERE user_id = $1 ORDER BY timestamp DESC LIMIT $2
                """,
                user_id, limit
            )
            return [dict(r) for r in rows]
