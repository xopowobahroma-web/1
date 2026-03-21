
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
            content = data['choices'][0]['message']['content']
            logger.debug(f"Содержимое ответа: {content[:100]}...")
            return content
        except Exception as e:
            # Добавляем логирование тела ответа при ошибке
            if 'response' in locals() and hasattr(response, 'text'):
                logger.error(f"Тело ответа ошибки OpenRouter: {response.text}")
            logger.exception(f"❌ Ошибка OpenRouter API: {e}")
            return "Извини, сейчас я временно недоступен. Попробуй позже."
