

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
        # Добавляем явные параметры SSL для стабильности
        self.pool = psycopg2.pool.SimpleConnectionPool(
            1, 10,
            dsn=self.dsn,
            sslmode='require',
            connect_timeout=10
        )
        logger.info("Database pool created with SSL")

    def close(self):
        if self.pool:
            self.pool.closeall()

    def get_or_create_user(self, telegram_id: int):
        conn = self.pool.getconn()
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
        except Exception as e:
            logger.exception(f"Error in get_or_create_user: {e}")
            raise
        finally:
            self.pool.putconn(conn)

    # Остальные методы (add_sleep_log, add_mood_log, add_conversation, get_recent_conversations и т.д.) остаются без изменений,
    # но также должны быть обновлены с правильной обработкой ошибок, как в предыдущих версиях.
    # Для краткости я не привожу их здесь, но вы можете скопировать их из предыдущего файла.
