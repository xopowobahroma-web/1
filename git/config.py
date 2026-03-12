import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Supabase (оставьте, если используете)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")   # или os.getenv("SUPABASE_DB_URL")
SUPABASE_DB_URL = DATABASE_URL
# Hugging Face
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")  # токен вида hf_...
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "Qwen/Qwen2.5-72B-Instruct")  # модель по умолчанию
HUGGINGFACE_INFERENCE_URL = os.getenv("HUGGINGFACE_INFERENCE_URL", "https://api-inference.huggingface.co/models/")

# Временная зона
TIMEZONE = "Europe/Moscow"