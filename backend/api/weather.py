"""Weather API route — fetches live data from Open-Meteo (no API key needed)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/weather", tags=["Weather"])

LAT = 10.38   # Pudukottai, Tamil Nadu
LON = 78.82

@router.get("")
async def get_weather(lat: float = LAT, lon: float = LON):
    """Return current weather for the given coordinates (default: Pudukottai)."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        logger.warning("Weather fetch failed: %s", exc)
        return {"error": "Weather unavailable", "temperature": None, "condition": None, "location": "Unknown"}

    current = data.get("current", {})
    code = current.get("weather_code", 0)
    conditions = {0: "Clear", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
                  45: "Foggy", 48: "Foggy", 51: "Light Drizzle", 53: "Drizzle",
                  55: "Heavy Drizzle", 61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
                  71: "Light Snow", 73: "Snow", 75: "Heavy Snow",
                  80: "Light Showers", 81: "Showers", 82: "Heavy Showers",
                  95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm"}
    condition = conditions.get(code, "Unknown")

    return {
        "temperature": current.get("temperature_2m"),
        "feels_like": current.get("apparent_temperature"),
        "humidity": current.get("relative_humidity_2m"),
        "condition": condition,
        "wind_speed": current.get("wind_speed_10m"),
        "location": "Pudukottai, Tamil Nadu",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
