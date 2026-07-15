"""AI service: OpenAI GPT, Ollama local LLM, automatic online/offline switching."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


class AIService:
    """Unified AI service that manages OpenAI and Ollama connections."""

    def __init__(self):
        self._openai_client = None
        self._ollama_available: Optional[bool] = None
        self.preferred_model: str = settings.openai_model

    @property
    def openai_client(self):
        if self._openai_client is None:
            from openai import AsyncOpenAI
            self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._openai_client

    async def check_ollama(self) -> bool:
        """Check if Ollama is reachable."""
        if self._ollama_available is not None:
            return self._ollama_available
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                self._ollama_available = resp.status_code == 200
        except Exception:
            self._ollama_available = False
        return self._ollama_available

    async def check_openai(self) -> bool:
        """Check if OpenAI API key is configured and valid."""
        if not settings.openai_api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def get_best_backend(self) -> str:
        """Determine whether to use OpenAI or Ollama."""
        if await self.check_openai():
            self.preferred_model = settings.openai_model
            return "openai"
        if await self.check_ollama():
            self.preferred_model = settings.ollama_model
            return "ollama"
        return "none"

    async def stream_chat_openai(
        self, messages: List[Dict[str, str]], model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from OpenAI."""
        model = model or settings.openai_model
        try:
            stream = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_tokens=2048,
                temperature=0.7,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as exc:
            logger.error("OpenAI streaming failed: %s", exc)
            yield f"[Error: {exc}]"

    async def stream_chat_ollama(
        self, messages: List[Dict[str, str]], model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion from Ollama."""
        model = model or settings.ollama_model
        payload = {"model": model, "messages": messages, "stream": True}
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{settings.ollama_base_url}/api/chat",
                    json=payload,
                ) as response:
                    async for line in response.aiter_lines():
                        if line.strip():
                            import json
                            data = json.loads(line)
                            if "message" in data:
                                yield data["message"].get("content", "")
        except Exception as exc:
            logger.error("Ollama streaming failed: %s", exc)
            yield f"[Error: {exc}]"

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat using the best available backend."""
        backend = await self.get_best_backend()
        if backend == "openai":
            async for chunk in self.stream_chat_openai(messages, model):
                yield chunk
        elif backend == "ollama":
            async for chunk in self.stream_chat_ollama(messages, model):
                yield chunk
        else:
            yield "[No AI backend available. Please configure OpenAI API key or start Ollama.]"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> str:
        """Non-streaming chat completion."""
        result = ""
        async for chunk in self.stream_chat(messages, model):
            result += chunk
        return result

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Estimate token count (rough approximation)."""
        return len(text) // 4

    async def get_available_models(self) -> Dict[str, List[str]]:
        """List available models from both backends."""
        result: Dict[str, List[str]] = {"openai": [], "ollama": []}
        if await self.check_openai():
            try:
                models = await self.openai_client.models.list()
                result["openai"] = [m.id for m in models.data if "gpt" in m.id]
            except Exception:
                result["openai"] = [settings.openai_model]
        if await self.check_ollama():
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                    if resp.status_code == 200:
                        data = resp.json()
                        result["ollama"] = [m["name"] for m in data.get("models", [])]
            except Exception:
                result["ollama"] = [settings.ollama_model]
        return result


ai_service = AIService()
