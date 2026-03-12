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
        self.model = os.environ.get('HUGGINGFACE_MODEL', 'Qwen/Qwen2-7B-Instruct')
        self.client = InferenceClient(
            token=self.api_key,
            model=self.model,
            timeout=30
        )
    
    def ask(self, user_message: str, context: str) -> str:
        try:
            messages = [
                {"role": "system", "content": context},
                {"role": "user", "content": user_message}
            ]
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
