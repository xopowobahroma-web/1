import psycopg2
from psycopg2 import pool
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.dsn = os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL')
        if not self.dsn:
            raise ValueError("DATABASE_URL or SUPABASE_DB_URL must be set")
        # Создаём пул соединений (минимум 1, максимум 10)
        self.pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=self.dsn)
        logger.info("Database pool created")

    def close(self):
        if self.pool:
            self.pool.closeall()

    def _get_columns(self, cursor):
        """Возвращает список имён колонок из курсора или пустой список."""
        if cursor.description:
            return [desc[0] for desc in cursor.description]
        return []

    # ----- Users -----
    def get_or_create_user(self, telegram_id: int):
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                # Пытаемся найти пользователя
                cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
                row = cur.fetchone()
                if not row:
                    # Создаём нового
                    cur.execute(
                        "INSERT INTO users (telegram_id, last_active) VALUES (%s, NOW()) RETURNING id, telegram_id, last_active",
                        (telegram_id,)
                    )
                    row = cur.fetchone()
                    conn.commit()
                else:
                    # Обновляем время активности
                    cur.execute(
                        "UPDATE users SET last_active = NOW() WHERE telegram_id = %s",
                        (telegram_id,)
                    )
                    conn.commit()
                # Преобразуем кортеж в словарь
                col_names = self._get_columns(cur)
                return dict(zip(col_names, row)) if row else None
        except Exception as e:
            logger.exception(f"Error in get_or_create_user: {e}")
            raise
        finally:
            self.pool.putconn(conn)

    def update_last_active(self, user_id: int):
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET last_active = NOW() WHERE id = %s", (user_id,))
                conn.commit()
        except Exception as e:
            logger.exception(f"Error in update_last_active: {e}")
            raise
        finally:
            self.pool.putconn(conn)

    # ----- Sleep logs -----
    def add_sleep_log(self, user_id: int, sleep_start: datetime = None, sleep_end: datetime = None,
                      quality: str = None, notes: str = None, triggered_by: str = None):
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO sleep_logs 
                       (user_id, sleep_start, sleep_end, quality, notes, triggered_by)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (user_id, sleep_start, sleep_end, quality, notes, triggered_by)
                )
                conn.commit()
        except Exception as e:
            logger.exception(f"Error in add_sleep_log: {e}")
            raise
        finally:
            self.pool.putconn(conn)

    # ----- Mood logs -----
    def add_mood_log(self, user_id: int, stress_level: int, mood: str = None, thoughts_about_use: bool = False):
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO mood_logs (user_id, stress_level, mood, thoughts_about_use)
                       VALUES (%s, %s, %s, %s)""",
                    (user_id, stress_level, mood, thoughts_about_use)
                )
                conn.commit()
        except Exception as e:
            logger.exception(f"Error in add_mood_log: {e}")
            raise
        finally:
            self.pool.putconn(conn)

    # ----- Conversations -----
    def add_conversation(self, user_id: int, role: str, message: str, context_used: dict = None):
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO conversations (user_id, role, message, context_used)
                       VALUES (%s, %s, %s, %s)""",
                    (user_id, role, message, psycopg2.extras.Json(context_used) if context_used else None)
                )
                conn.commit()
        except Exception as e:
            logger.exception(f"Error in add_conversation: {e}")
            raise
        finally:
            self.pool.putconn(conn)

    def get_recent_conversations(self, user_id: int, limit: int = 20):
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT role, message, timestamp FROM conversations
                       WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s""",
                    (user_id, limit)
                )
                rows = cur.fetchall()
                # Переворачиваем, чтобы получить хронологический порядок
                rows.reverse()
                col_names = self._get_columns(cur)
                return [dict(zip(col_names, row)) for row in rows]
        except Exception as e:
            logger.exception(f"Error in get_recent_conversations: {e}")
            return []
        finally:
            self.pool.putconn(conn)

    # ----- Triggers -----
    def add_trigger(self, user_id: int, trigger_text: str, category: str = None):
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO triggers (user_id, trigger_text, category) VALUES (%s, %s, %s)",
                    (user_id, trigger_text, category)
                )
                conn.commit()
        except Exception as e:
            logger.exception(f"Error in add_trigger: {e}")
            raise
        finally:
            self.pool.putconn(conn)

    # ----- Агрегированные данные для контекста -----
    def get_sleep_stats(self, user_id: int, days: int = 7):
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT sleep_start, sleep_end FROM sleep_logs
                       WHERE user_id = %s AND sleep_start > NOW() - INTERVAL '1 day' * %s
                       ORDER BY sleep_start""",
                    (user_id, days)
                )
                rows = cur.fetchall()
                col_names = self._get_columns(cur)
                return [dict(zip(col_names, row)) for row in rows]
        except Exception as e:
            logger.exception(f"Error in get_sleep_stats: {e}")
            return []
        finally:
            self.pool.putconn(conn)

    def get_recent_mood(self, user_id: int, limit: int = 5):
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT stress_level, mood, thoughts_about_use, timestamp
                       FROM mood_logs WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s""",
                    (user_id, limit)
                )
                rows = cur.fetchall()
                col_names = self._get_columns(cur)
                return [dict(zip(col_names, row)) for row in rows]
        except Exception as e:
            logger.exception(f"Error in get_recent_mood: {e}")
            return []
        finally:
            self.pool.putconn(conn)
