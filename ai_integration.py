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
        # Используем указанную модель
       self.model = os.environ.get('HUGGINGFACE_MODEL', 'Qwen/Qwen3.5-397B-A17B')
        self.client = InferenceClient(
            token=self.api_key,
            model=self.model,
            timeout=30
        )
    
    def ask(self, user_message: str, context: str) -> str:
        try:
            prompt = f"{context}\n\nUser: {user_message}\nAssistant:"
            response = self.client.text_generation(
                prompt,
                max_new_tokens=500,
                temperature=0.7,
                top_p=0.9
            )
            return response
        except Exception as e:
            logger.exception(f"Hugging Face API Error: {e}")
            return "Извини, сейчас я временно недоступен. Расскажи, как ты?"
