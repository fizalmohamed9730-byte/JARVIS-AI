"""Utility tools for JARVIS AI agent system."""

from __future__ import annotations

import logging
import re
import threading
import time
from datetime import datetime
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def get_current_time() -> str:
    """Get the current date and time.

    Returns:
        The current date, time, day of week, and timezone info.
    """
    now = datetime.now()
    day_name = now.strftime("%A")
    return (
        f"Current Date & Time:\n"
        f"  Date: {now.strftime('%B %d, %Y')}\n"
        f"  Time: {now.strftime('%I:%M:%S %p')}\n"
        f"  Day: {day_name}\n"
        f"  ISO: {now.isoformat()}"
    )


@tool
def get_weather(location: str = "") -> str:
    """Get current weather information for a location.

    Args:
        location: City name or location. Defaults to auto-detect.

    Returns:
        Current weather information including temperature and conditions.
    """
    if not location or not location.strip():
        location = "auto"

    try:
        import httpx

        api_key = __import__("os").environ.get("OPENWEATHER_API_KEY", "")

        if api_key:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
            with httpx.Client(timeout=10) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()

            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            desc = data["weather"][0]["description"]
            city = data["name"]
            wind_speed = data["wind"]["speed"]

            return (
                f"Weather in {city}:\n"
                f"  Temperature: {temp}°C (feels like {feels_like}°C)\n"
                f"  Condition: {desc.title()}\n"
                f"  Humidity: {humidity}%\n"
                f"  Wind: {wind_speed} m/s"
            )

        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(f"weather now {location}", max_results=1))

            if results:
                return f"Weather info for {location}:\n{results[0].get('body', 'No data available')}\n\nTip: Set OPENWEATHER_API_KEY for detailed weather."
        except ImportError:
            pass

        return (
            f"Weather data requires API key.\n"
            f"Set OPENWEATHER_API_KEY environment variable for live weather data.\n"
            f"You can get a free key at: https://openweathermap.org/api"
        )

    except Exception as e:
        return f"Error getting weather: {e}"


@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression.

    Args:
        expression: The mathematical expression to evaluate.
            Supports: +, -, *, /, **, %, sqrt, sin, cos, tan, pi, e, abs, round.
            Example: '2**10 + sqrt(144)'

    Returns:
        The result of the calculation.
    """
    if not expression or not expression.strip():
        return "Error: Expression cannot be empty."

    import math

    allowed_names = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "log": math.log, "log10": math.log10,
        "log2": math.log2, "exp": math.exp, "pow": pow,
        "pi": math.pi, "e": math.e, "tau": math.tau,
        "ceil": math.ceil, "floor": math.floor,
        "factorial": math.factorial, "gcd": math.gcd,
    }

    sanitized = re.sub(r"[a-zA-Z_]+", lambda m: m.group() if m.group() in allowed_names else "", expression)

    for op in ["import", "exec", "eval", "open", "__", "os.", "sys."]:
        if op in sanitized:
            return f"Error: Disallowed expression content: {op}"

    try:
        result = eval(sanitized, {"__builtins__": {}}, allowed_names)
        return f"{expression} = {result}"
    except ZeroDivisionError:
        return "Error: Division by zero."
    except Exception as e:
        return f"Error evaluating expression: {e}"


@tool
def translate(text: str, target_language: str = "es") -> str:
    """Translate text to the target language.

    Args:
        text: The text to translate.
        target_language: Target language code (e.g., 'es' for Spanish, 'fr' for French,
            'de' for German, 'ja' for Japanese, 'zh' for Chinese). Defaults to 'es'.

    Returns:
        The translated text.
    """
    if not text or not text.strip():
        return "Error: Text to translate cannot be empty."

    target_language = target_language.strip().lower()

    language_names = {
        "es": "Spanish", "fr": "French", "de": "German", "it": "Italian",
        "pt": "Portuguese", "ru": "Russian", "ja": "Japanese", "ko": "Korean",
        "zh": "Chinese", "ar": "Arabic", "hi": "Hindi", "nl": "Dutch",
        "sv": "Swedish", "pl": "Polish", "tr": "Turkish", "vi": "Vietnamese",
        "th": "Thai", "id": "Indonesian",
    }

    lang_name = language_names.get(target_language, target_language.upper())

    try:
        from deep_translator import GoogleTranslator

        translated = GoogleTranslator(source="auto", target=target_language).translate(text)
        return f"Translated to {lang_name}:\n{translated}"

    except ImportError:
        pass

    try:
        import httpx

        url = "https://api.mymemory.translated.net/get"
        params = {"q": text, "langpair": f"auto|{target_language}"}

        with httpx.Client(timeout=10) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        translated = data.get("responseData", {}).get("translatedText", "")
        if translated:
            return f"Translated to {lang_name}:\n{translated}"

        return f"Translation service returned empty result. Try: pip install deep-translator"

    except Exception as e:
        return (
            f"Translation requires a library. Install one of:\n"
            f"  - pip install deep-translator\n"
            f"  Or use an API key for better results.\n"
            f"Error: {e}"
        )


@tool
def summarize(text: str, max_sentences: int = 3) -> str:
    """Create a summary of the given text.

    Args:
        text: The text to summarize.
        max_sentences: Maximum sentences in the summary. Defaults to 3.

    Returns:
        A summarized version of the text.
    """
    if not text or not text.strip():
        return "Error: Text to summarize cannot be empty."

    max_sentences = max(1, min(10, max_sentences))

    try:
        import re

        text = re.sub(r'\s+', ' ', text.strip())

        sentences = re.split(r'(?<=[.!?])\s+', text)

        if len(sentences) <= max_sentences:
            return f"Summary (full text is short enough):\n{text}"

        word_freq: dict[str, int] = {}
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "through", "during",
            "before", "after", "above", "below", "between", "and", "but", "or",
            "not", "no", "so", "if", "than", "that", "this", "these", "those",
            "it", "its", "they", "them", "their", "we", "our", "you", "your",
            "he", "she", "his", "her", "my", "i", "me",
        }

        for word in re.findall(r'\b[a-z]+\b', text.lower()):
            if word not in stop_words and len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1

        scored: list[tuple[int, float, str]] = []
        for i, sentence in enumerate(sentences):
            score = 0
            words = re.findall(r'\b[a-z]+\b', sentence.lower())
            for word in words:
                score += word_freq.get(word, 0)
            if i < 2:
                score *= 1.5
            scored.append((i, score, sentence.strip()))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:max_sentences]
        top.sort(key=lambda x: x[0])

        summary = " ".join(s[2] for s in top)
        return f"Summary:\n{summary}"

    except Exception as e:
        return f"Error summarizing text: {e}"


@tool
def set_timer(minutes: float = 1.0, message: str = "Timer finished!") -> str:
    """Set a timer that will alert after the specified duration.

    Args:
        minutes: Duration in minutes. Supports decimals (e.g., 0.5 for 30 seconds).
        message: Message to display when timer finishes. Defaults to 'Timer finished!'

    Returns:
        A confirmation that the timer has been set.
    """
    if minutes <= 0:
        return "Error: Timer duration must be positive."

    seconds = int(minutes * 60)

    def _timer_callback():
        try:
            import winsound
            for _ in range(3):
                winsound.Beep(1000, 500)
                time.sleep(0.2)
        except ImportError:
            pass
        logger.info("TIMER: %s", message)

    timer = threading.Timer(seconds, _timer_callback)
    timer.daemon = True
    timer.start()

    if minutes >= 1:
        time_str = f"{minutes:.1f} minutes"
    else:
        time_str = f"{seconds} seconds"

    return f"Timer set for {time_str}: {message}"


utility_tools = [
    get_current_time, get_weather, calculate,
    translate, summarize, set_timer,
]
