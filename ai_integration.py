import os
import requests
import logging

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.api_key = os.environ.get('OPENROUTER_API_KEY')
        if not self.api_key:
            logger.error("❌ OPENROUTER_API_KEY не задан!")
            raise ValueError("OPENROUTER_API_KEY не задан")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        # Используем актуальную бесплатную модель
        self.model = "stepfun/step-3.5-flash:free"
        logger.info(f"✅ LLM Client инициализирован с моделью {self.model}")

    def ask(self, user_message: str, context: str) -> str:
        logger.debug(f"Запрос к OpenRouter: user_message={user_message[:50]}...")
        response = None  # для безопасной обработки в except
        try:
            response = requests.post(
                url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": context},
                        {"role": "user", "content": user_message}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Ответ от OpenRouter получен, статус {response.status_code}")

            # Безопасное извлечение содержимого
            content = data.get('choices', [{}])[0].get('message', {}).get('content')

            # Логируем, если content None или пустая строка
            if content:
                logger.debug(f"Содержимое ответа: {content[:100]}...")
            else:
                logger.warning("Ответ OpenRouter не содержит текста (content is None or empty)")

            # Если content всё же None, заменяем на fallback сообщение
            return content if content else "Извините, я не смог сформулировать ответ. Попробуйте позже."

        except Exception as e:
            # Логируем тело ответа, если оно доступно
            if response is not None:
                logger.error(f"Тело ответа ошибки OpenRouter: {response.text}")
            logger.exception(f"❌ Ошибка OpenRouter API: {e}")
            return "Извини, сейчас я временно недоступен. Попробуй позже."
