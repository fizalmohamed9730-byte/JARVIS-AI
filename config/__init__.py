"""JARVIS configuration package."""

from __future__ import annotations

import logging
from typing import Optional

from langchain_core.language_models import BaseChatModel

from config.settings import settings

logger = logging.getLogger(__name__)

_llm_instance: Optional[BaseChatModel] = None


def get_llm() -> BaseChatModel:
    """Get or create the configured LLM instance.

    Uses OpenAI GPT when an API key is available and internet is reachable.
    Falls back to Ollama for offline operation.
    """
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    if settings.openai_api_key:
        try:
            from langchain_openai import ChatOpenAI

            _llm_instance = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=0.7,
                max_tokens=2048,
                streaming=True,
            )
            logger.info("Using OpenAI model: %s", settings.openai_model)
            return _llm_instance
        except Exception as e:
            logger.warning("Failed to initialize OpenAI: %s", e)

    try:
        from langchain_community.llms import Ollama

        _llm_instance = Ollama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.7,
        )
        logger.info("Using Ollama model: %s", settings.ollama_model)
        return _llm_instance
    except Exception as e:
        logger.warning("Failed to initialize Ollama: %s", e)

    try:
        from langchain_community.llms import FakeLLM

        _llm_instance = FakeLLM(
            responses=["I'm JARVIS, but I'm currently offline and no LLM is available."]
        )
        logger.warning("No LLM available – using fallback stub.")
        return _llm_instance
    except Exception:
        pass

    raise RuntimeError(
        "No LLM backend available. Configure OPENAI_API_KEY or install Ollama."
    )


def reset_llm() -> None:
    """Reset the cached LLM instance so it is recreated on next access."""
    global _llm_instance
    _llm_instance = None
