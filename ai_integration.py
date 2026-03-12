import aiohttp
from huggingface_hub import InferenceClient, AsyncInferenceClient
from config import settings
import asyncio

class HuggingFaceClient:
    def __init__(self):
        self.api_key = settings.HUGGINGFACE_API_KEY
        self.model = settings.HUGGINGFACE_MODEL
        # Используем асинхронный клиент
        self.client = AsyncInferenceClient(
            token=self.api_key,
            model=self.model,
            timeout=30  # таймаут в секундах
        )
    
    async def ask(self, user_message: str, context: str) -> str:
        """
        Отправляет запрос к Hugging Face Inference API
        """
        try:
            # Формируем сообщения в формате chat
            messages = [
                {"role": "system", "content": context},
                {"role": "user", "content": user_message}
            ]
            
            # Отправляем запрос
            response = await self.client.chat_completion(
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
                top_p=0.9
            )
            
            # Извлекаем ответ
            if response and response.choices:
                return response.choices[0].message.content
            else:
                return "Извини, я не получил осмысленного ответа от модели."
                
        except Exception as e:
            print(f"Hugging Face API Error: {e}")
            return "Извини, сейчас я временно недоступен. Расскажи, как ты?"