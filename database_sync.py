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
        conn = self.pool.getconn()
        try:
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

    # ----- Users -----
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
            self.pool.putconn(conn)
            raise
        else:
            self.pool.putconn(conn)

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

    # ----- Conversations -----
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

    # ----- Long-term memory -----
    @retry_on_db_error()
    def add_memory(self, user_id: int, key: str, value: str):
        """Сохраняет факт о пользователе."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO user_memory (user_id, key, value) VALUES (%s, %s, %s)",
                    (user_id, key, value)
                )
                conn.commit()
        except Exception:
            self.pool.putconn(conn)
            raise
        else:
            self.pool.putconn(conn)

    @retry_on_db_error()
    def get_all_memories(self, user_id: int):
        """Возвращает все сохранённые факты пользователя."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT key, value, created_at FROM user_memory WHERE user_id = %s ORDER BY created_at",
                    (user_id,)
                )
                rows = cur.fetchall()
                return [{'key': r[0], 'value': r[1], 'created_at': r[2]} for r in rows]
        except Exception:
            self.pool.putconn(conn)
            raise
        else:
            self.pool.putconn(conn)

    @retry_on_db_error()
    def delete_memory(self, user_id: int, key: str):
        """Удаляет конкретный факт (опционально)."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_memory WHERE user_id = %s AND key = %s",
                    (user_id, key)
                )
                conn.commit()
        except Exception:
            self.pool.putconn(conn)
            raise
        else:
            self.pool.putconn(conn)
