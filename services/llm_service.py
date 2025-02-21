from abc import ABC, abstractmethod
from typing import Optional
import asyncio
from aiohttp import ClientSession
from constants import DEFAULT_MAX_TOKENS, MAX_CACHE_SIZE
from functools import lru_cache

class LLMService(ABC):
    @abstractmethod
    async def get_completion(self, prompt: str) -> Optional[str]:
        pass

class GroqLLMService(LLMService):
    def __init__(self, api_key: str, model: str, max_tokens: int = DEFAULT_MAX_TOKENS, cache_size: int = MAX_CACHE_SIZE):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self._rate_limit = asyncio.Semaphore(5)  # Максимум 5 одновременных запросов
        self._cache = {}
        self._cache_size = cache_size

    async def get_completion(self, prompt: str) -> Optional[str]:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Invalid prompt")

        async with self._rate_limit:
            async with ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                data = {
                    "prompt": prompt,
                    "max_tokens": self.max_tokens,
                    "model": self.model
                }
                try:
                    async with session.post("https://api.groq.com/v1/llm", headers=headers, json=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result.get("text", "").strip()
                        return None
                except Exception as e:
                    raise Exception(f"LLM API error: {str(e)}")

    @lru_cache(maxsize=MAX_CACHE_SIZE)
    async def get_completion_cached(self, prompt: str) -> Optional[str]:
        cache_key = f"{self.model}:{prompt}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        result = await self.get_completion(prompt)
        if result and len(self._cache) < self._cache_size:
            self._cache[cache_key] = result
        return result 