from huggingface_hub import AsyncInferenceClient
from config import HUGGINGFACE_API_KEY, HUGGINGFACE_MODEL

class HuggingFaceClient:
    def __init__(self):
        self.client = AsyncInferenceClient(token=HUGGINGFACE_API_KEY)
        self.model = HUGGINGFACE_MODEL

    async def ask(self, user_message: str, context: str) -> str:
        messages = [
            {"role": "system", "content": context},
            {"role": "user", "content": user_message}
        ]
        response = await self.client.chat_completion(
            model=self.model,
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content