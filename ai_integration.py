import os
from huggingface_hub import InferenceClient
import logging

logger = logging.getLogger(__name__)

class HuggingFaceClient:
    def __init__(self):
        self.api_key = os.environ.get('HUGGINGFACE_API_KEY')
        if not self.api_key:
            logger.error("❌ HUGGINGFACE_API_KEY не задан в окружении!")
            raise ValueError("HUGGINGFACE_API_KEY не задан")
        self.model = os.environ.get('HUGGINGFACE_MODEL', 'mistralai/Mistral-7B-Instruct-v0.2')
        self.client = InferenceClient(
            token=self.api_key,
            model=self.model,
            timeout=30
        )
        logger.info(f"HuggingFaceClient инициализирован с моделью {self.model}")
    
    def ask(self, user_message: str, context: str) -> str:
        try:
            # Формируем сообщения в формате chat
            messages = [
                {"role": "system", "content": context},
                {"role": "user", "content": user_message}
            ]
            # Используем chat_completion для instruct-моделей
            response = self.client.chat_completion(
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                top_p=0.9
            )
            if response and response.choices:
                return response.choices[0].message.content
            else:
                return "Извини, я не получил осмысленного ответа от модели."
        except Exception as e:
            logger.exception(f"Hugging Face API Error: {e}")
            return "Извини, сейчас я временно недоступен. Расскажи, как ты?"
