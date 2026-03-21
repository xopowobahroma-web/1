import os
import requests
import logging
import time

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.api_key = os.environ.get('MISTRAL_API_KEY')
        if not self.api_key:
            logger.error("❌ MISTRAL_API_KEY не задан!")
            raise ValueError("MISTRAL_API_KEY не задан")
        
        self.base_url = "https://api.mistral.ai/v1/chat/completions"
        self.model = "mistral-tiny"  # бесплатная модель: mistral-tiny, open-mistral-nemo, mistral-small-latest
        self.max_tokens = 2575
        self.max_retries = 3
        self.retry_delay = 2
        
        logger.info(f"✅ LLM Client инициализирован с Mistral, модель {self.model}, max_tokens={self.max_tokens}")

    def ask(self, user_message: str, context: str) -> str:
        logger.debug(f"Запрос к Mistral: user_message={user_message[:50]}...")

        for attempt in range(self.max_retries + 1):
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

                # Обработка 429 (rate limit)
                if response.status_code == 429:
                    error_data = response.json() if response.text else {}
                    logger.warning(f"Mistral 429 (попытка {attempt+1}/{self.max_retries+1}): {error_data}")
                    if attempt < self.max_retries:
                        delay = self.retry_delay * (2 ** attempt)
                        logger.info(f"Повторная попытка через {delay} секунд...")
                        time.sleep(delay)
                        continue
                    else:
                        return "Сервис временно перегружен. Пожалуйста, попробуйте позже."

                response.raise_for_status()
                data = response.json()
                logger.debug(f"Ответ от Mistral получен, статус {response.status_code}")

                # Проверка ошибок в ответе
                if 'error' in data:
                    logger.error(f"Mistral вернул ошибку: {data['error']}")
                    return "Извини, сейчас я временно недоступен. Попробуй позже."

                choices = data.get('choices', [])
                if not choices:
                    logger.warning(f"Ответ Mistral не содержит choices. Полный ответ: {data}")
                    return "Извините, я не смог сформулировать ответ. Попробуйте позже."

                choice = choices[0]
                finish_reason = choice.get('finish_reason')
                message = choice.get('message', {})
                content = message.get('content')

                if not content:
                    if finish_reason == 'length':
                        logger.warning("Ответ не содержит текста из-за превышения лимита токенов.")
                        return "Извините, ваш запрос слишком длинный. Пожалуйста, сократите сообщение."
                    else:
                        logger.warning(f"Ответ не содержит текста. finish_reason: {finish_reason}")
                        return "Извините, я не смог сформулировать ответ. Попробуйте позже."

                logger.debug(f"Содержимое ответа: {content[:100]}...")
                return content

            except requests.exceptions.RequestException as e:
                if response is not None:
                    logger.error(f"Тело ответа ошибки Mistral: {response.text}")
                logger.exception(f"❌ Ошибка Mistral API: {e}")
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Повторная попытка через {delay} секунд из-за ошибки...")
                    time.sleep(delay)
                    continue
                else:
                    return "Извини, сейчас я временно недоступен. Попробуй позже."
        
        return "Извини, сейчас я временно недоступен. Попробуй позже."
