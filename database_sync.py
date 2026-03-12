import psycopg2
from psycopg2 import pool, extras
from psycopg2 import OperationalError
from datetime import datetime
import os
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)

def retry_on_db_error(max_retries=5, delay=1):
    """Декоратор для повторных попыток при ошибках базы данных (теперь 5 попыток)."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    logger.warning(f"Database error (attempt {attempt+1}/{max_retries}): {e}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay * (attempt + 1))
        return wrapper
    return decorator

class Database:
    def __init__(self):
        self.dsn = os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL')
        if not self.dsn:
            raise ValueError("DATABASE_URL or SUPABASE_DB_URL must be set")
        self.pool = psycopg2.pool.SimpleConnectionPool(
            1, 10,
            dsn=self.dsn,
            sslmode='require',
            connect_timeout=20,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
        logger.info("Database pool created with SSL and keepalive")

    def close(self):
        if self.pool:
            self.pool.closeall()

    def _get_connection(self):
        """Возвращает рабочее соединение из пула, проверяя его жизнеспособность."""
        conn = self.pool.getconn()
        try:
            # Проверяем соединение лёгким запросом
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        except Exception as e:
            logger.warning(f"Connection {conn} is broken, discarding and getting new one. Error: {e}")
            self.pool.putconn(conn, close=True)
            conn = self.pool.getconn()
        return conn

    def _get_columns(self, cursor):
        if cursor.description:
            return [desc[0] for desc in cursor.description]
        return []

    @retry_on_db_error()
    def get_or_create_user(self, telegram_id: int):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, telegram_id, last_active FROM users WHERE telegram_id = %s", (telegram_id,))
                row = cur.fetchone()
                if row:
                    cur.execute("UPDATE users SET last_active = NOW() WHERE telegram_id = %s", (telegram_id,))
                    conn.commit()
                    return {'id': row[0], 'telegram_id': row[1], 'last_active': row[2]}
                else:
                    cur.execute(
                        "INSERT INTO users (telegram_id, last_active) VALUES (%s, NOW()) RETURNING id, telegram_id, last_active",
                        (telegram_id,)
                    )
                    row = cur.fetchone()
                    conn.commit()
                    if row:
                        return {'id': row[0], 'telegram_id': row[1], 'last_active': row[2]}
                    else:
                        raise Exception("Failed to create user: no row returned")
        except Exception:
            # В случае любой ошибки возвращаем соединение (но не закрываем)
            self.pool.putconn(conn)
            raise
        else:
            # Если всё ок, возвращаем соединение в пул
            self.pool.putconn(conn)

    # Аналогично модифицируем остальные методы, заменяя self.pool.getconn() на self._get_connection()
    # и добавляя блоки finally/else для возврата соединения.
    # Для краткости приведу только один метод, но вы должны применить тот же паттерн ко всем.
    # Ниже показаны остальные методы с изменениями.

    @retry_on_db_error()
    def update_last_active(self, user_id: int):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET last_active = NOW() WHERE id = %s", (user_id,))
                conn.commit()
        except Exception:
            self.pool.putconn(conn)
            raise
        else:
            self.pool.putconn(conn)

    @retry_on_db_error()
    def add_sleep_log(self, user_id: int, sleep_start: datetime = None, sleep_end: datetime = None,
                      quality: str = None, notes: str = None, triggered_by: str = None):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO sleep_logs 
                       (user_id, sleep_start, sleep_end, quality, notes, triggered_by)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (user_id, sleep_start, sleep_end, quality, notes, triggered_by)
                )
                conn.commit()
        except Exception:
            self.pool.putconn(conn)
            raise
        else:
            self.pool.putconn(conn)

    @retry_on_db_error()
    def add_mood_log(self, user_id: int, stress_level: int, mood: str = None, thoughts_about_use: bool = False):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO mood_logs (user_id, stress_level, mood, thoughts_about_use)
                       VALUES (%s, %s, %s, %s)""",
                    (user_id, stress_level, mood, thoughts_about_use)
                )
                conn.commit()
        except Exception:
            self.pool.putconn(conn)
            raise
        else:
            self.pool.putconn(conn)

    @retry_on_db_error()
    def add_conversation(self, user_id: int, role: str, message: str, context_used: dict = None):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO conversations (user_id, role, message, context_used)
                       VALUES (%s, %s, %s, %s)""",
                    (user_id, role, message, extras.Json(context_used) if context_used else None)
                )
                conn.commit()
        except Exception:
            self.pool.putconn(conn)
            raise
        else:
            self.pool.putconn(conn)

    @retry_on_db_error()
    def get_recent_conversations(self, user_id: int, limit: int = 20):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT role, message, timestamp FROM conversations
                       WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s""",
                    (user_id, limit)
                )
                rows = cur.fetchall()
                rows.reverse()
                return [{'role': r[0], 'message': r[1], 'timestamp': r[2]} for r in rows]
        except Exception:
            self.pool.putconn(conn)
            raise
        else:
            self.pool.putconn(conn)

    @retry_on_db_error()
    def add_trigger(self, user_id: int, trigger_text: str, category: str = None):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO triggers (user_id, trigger_text, category) VALUES (%s, %s, %s)",
                    (user_id, trigger_text, category)
                )
                conn.commit()
        except Exception:
            self.pool.putconn(conn)
            raise
        else:
            self.pool.putconn(conn)

    @retry_on_db_error()
    def get_sleep_stats(self, user_id: int, days: int = 7):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT sleep_start, sleep_end FROM sleep_logs
                       WHERE user_id = %s AND sleep_start > NOW() - INTERVAL '1 day' * %s
                       ORDER BY sleep_start""",
                    (user_id, days)
                )
                rows = cur.fetchall()
                return [{'sleep_start': r[0], 'sleep_end': r[1]} for r in rows]
        except Exception:
            self.pool.putconn(conn)
            raise
        else:
            self.pool.putconn(conn)

    @retry_on_db_error()
    def get_recent_mood(self, user_id: int, limit: int = 5):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT stress_level, mood, thoughts_about_use, timestamp
                       FROM mood_logs WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s""",
                    (user_id, limit)
                )
                rows = cur.fetchall()
                return [{'stress_level': r[0], 'mood': r[1], 'thoughts_about_use': r[2], 'timestamp': r[3]} for r in rows]
        except Exception:
            self.pool.putconn(conn)
            raise
        else:
            self.pool.putconn(conn)
