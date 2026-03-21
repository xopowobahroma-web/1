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
        self.model = "stepfun/step-3.5-flash:free"
        self.max_tokens = 2575
        logger.info(f"✅ LLM Client инициализирован с моделью {self.model}, max_tokens={self.max_tokens}")

    def ask(self, user_message: str, context: str) -> str:
        logger.debug(f"Запрос к OpenRouter: user_message={user_message[:50]}...")
        response = None
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
                    "max_tokens": self.max_tokens,
                    "temperature": 0.7
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Ответ от OpenRouter получен, статус {response.status_code}")

            if 'error' in data:
                logger.error(f"OpenRouter вернул ошибку: {data['error']}")
                return "Извини, сейчас я временно недоступен. Попробуй позже."

            choices = data.get('choices', [])
            if not choices:
                logger.warning(f"Ответ OpenRouter не содержит choices. Полный ответ: {data}")
                return "Извините, я не смог сформулировать ответ. Попробуйте позже."

            choice = choices[0]
            finish_reason = choice.get('finish_reason')
            message = choice.get('message', {})
            content = message.get('content')
            reasoning = message.get('reasoning')

            if not content and reasoning:
                content = reasoning
                logger.debug("Использован reasoning вместо content")

            if not content:
                if finish_reason == 'length':
                    logger.warning("Ответ OpenRouter не содержит текста из-за превышения лимита токенов.")
                    return "Извините, ваш запрос слишком длинный. Пожалуйста, сократите сообщение или разбейте на несколько частей."
                else:
                    logger.warning(f"Ответ OpenRouter не содержит текста. finish_reason: {finish_reason}, полный ответ: {data}")
                    return "Извините, я не смог сформулировать ответ. Попробуйте позже."

            logger.debug(f"Содержимое ответа: {content[:100]}...")
            return content

        except Exception as e:
            if response is not None:
                logger.error(f"Тело ответа ошибки OpenRouter: {response.text}")
            logger.exception(f"❌ Ошибка OpenRouter API: {e}")
            return "Извини, сейчас я временно недоступен. Попробуй позже."
