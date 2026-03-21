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
        # Используем модель с большим контекстом
        self.model = "stepfun/step-3.5-flash:free"
        self.max_tokens = 2000  # Увеличено для больших ответов
        # Примерный лимит контекста модели (можно уточнить, но для безопасности)
        self.model_context_limit = 8192  # Предположим 8k
        logger.info(f"✅ LLM Client инициализирован с моделью {self.model}, max_tokens={self.max_tokens}")

    def _truncate_context(self, context: str, user_message: str) -> str:
        """
        Грубое усечение системного контекста, чтобы гарантировать место для ответа.
        Ориентируемся на примерную длину в символах (не точные токены, но проще).
        """
        # Оставляем 70% лимита для контекста, 30% для ответа (приблизительно)
        max_context_chars = int(self.model_context_limit * 0.7 * 3)  # 1 токен ≈ 3 символа
        if len(context) + len(user_message) > max_context_chars:
            # Обрезаем системный контекст
            available = max_context_chars - len(user_message)
            if available > 100:
                context = context[:available]
                logger.warning(f"Системный контекст был обрезан до {len(context)} символов")
            else:
                context = "Будь кратким помощником."
        return context

    def ask(self, user_message: str, context: str) -> str:
        logger.debug(f"Запрос к OpenRouter: user_message={user_message[:50]}...")

        # Если контекст подозрительно длинный, обрезаем
        if len(context) > 6000:
            context = self._truncate_context(context, user_message)

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

            # Если контент пустой, но есть reasoning, используем reasoning
            if not content and reasoning:
                content = reasoning
                logger.debug("Использован reasoning вместо content")

            # Если контент всё ещё пуст, анализируем причину
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
