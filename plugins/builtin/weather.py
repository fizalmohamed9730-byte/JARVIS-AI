"""Weather plugin for JARVIS AI assistant."""

import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..base import BasePlugin

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    """Weather data container."""
    location: str
    temperature: float
    feels_like: float
    humidity: int
    wind_speed: float
    wind_direction: str
    description: str
    icon: str
    pressure: int
    visibility: int
    timestamp: str


@dataclass
class ForecastDay:
    """Daily forecast data."""
    date: str
    temp_high: float
    temp_low: float
    description: str
    icon: str
    humidity: int
    wind_speed: float
    precipitation: float


class WeatherPlugin(BasePlugin):
    """Weather information plugin."""

    @property
    def name(self) -> str:
        return "weather"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Provides weather information and forecasts"

    @property
    def author(self) -> str:
        return "JARVIS Team"

    def __init__(self):
        super().__init__()
        self._api_key: Optional[str] = None
        self._base_url = "https://api.openweathermap.org/data/2.5"
        self._units = "metric"

    async def initialize(self) -> None:
        """Initialize weather plugin."""
        await super().initialize()
        self._api_key = self._config.get("api_key")
        self._units = self._config.get("units", "metric")

        if not self._api_key:
            self._logger.warning("OpenWeatherMap API key not configured")

    async def execute(self, action: str, **kwargs) -> Any:
        """Execute weather action."""
        actions = {
            "current": self.get_current_weather,
            "forecast": self.get_forecast,
            "alerts": self.get_alerts
        }

        handler = actions.get(action)
        if handler:
            return await handler(**kwargs)

        raise ValueError(f"Unknown action: {action}")

    def get_capabilities(self) -> List[str]:
        return ["current_weather", "forecast", "alerts"]

    async def get_current_weather(
        self,
        location: str,
        units: Optional[str] = None
    ) -> WeatherData:
        """Get current weather for location."""
        if not self._api_key:
            return self._get_mock_weather(location)

        units = units or self._units
        url = f"{self._base_url}/weather"
        params = {
            "q": location,
            "appid": self._api_key,
            "units": units
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_current_weather(data, location)
                else:
                    error = await response.text()
                    self._logger.error(f"Weather API error: {error}")
                    return self._get_mock_weather(location)

    async def get_forecast(
        self,
        location: str,
        days: int = 5,
        units: Optional[str] = None
    ) -> List[ForecastDay]:
        """Get weather forecast for location."""
        if not self._api_key:
            return self._get_mock_forecast(location, days)

        units = units or self._units
        url = f"{self._base_url}/forecast"
        params = {
            "q": location,
            "appid": self._api_key,
            "units": units,
            "cnt": days * 8
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_forecast(data, days)
                else:
                    self._logger.error(f"Forecast API error: {response.status}")
                    return self._get_mock_forecast(location, days)

    async def get_alerts(
        self,
        location: str
    ) -> List[Dict[str, Any]]:
        """Get weather alerts for location."""
        if not self._api_key:
            return []

        url = f"{self._base_url}/onecall"
        geocode_url = "https://api.openweathermap.org/geo/1.0/direct"
        params = {"q": location, "appid": self._api_key, "limit": 1}

        async with aiohttp.ClientSession() as session:
            async with session.get(geocode_url, params=params) as response:
                if response.status != 200:
                    return []
                geo_data = await response.json()
                if not geo_data:
                    return []

                lat = geo_data[0]["lat"]
                lon = geo_data[0]["lon"]

            params = {
                "lat": lat,
                "lon": lon,
                "appid": self._api_key,
                "exclude": "minutely,hourly,daily"
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    alerts = data.get("alerts", [])
                    return [
                        {
                            "event": alert.get("event", "Unknown"),
                            "description": alert.get("description", ""),
                            "start": alert.get("start", 0),
                            "end": alert.get("end", 0),
                            "sender": alert.get("sender_name", "")
                        }
                        for alert in alerts
                    ]
                return []

    def _parse_current_weather(self, data: dict, location: str) -> WeatherData:
        """Parse API response into WeatherData."""
        main = data.get("main", {})
        wind = data.get("wind", {})
        weather = data.get("weather", [{}])[0]

        return WeatherData(
            location=location,
            temperature=main.get("temp", 0),
            feels_like=main.get("feels_like", 0),
            humidity=main.get("humidity", 0),
            wind_speed=wind.get("speed", 0),
            wind_direction=self._deg_to_compass(wind.get("deg", 0)),
            description=weather.get("description", "Unknown"),
            icon=weather.get("icon", "01d"),
            pressure=main.get("pressure", 0),
            visibility=data.get("visibility", 0),
            timestamp=datetime.utcnow().isoformat()
        )

    def _parse_forecast(self, data: dict, days: int) -> List[ForecastDay]:
        """Parse API response into forecast days."""
        daily_data: Dict[str, List[dict]] = {}

        for item in data.get("list", []):
            date = item["dt_txt"].split(" ")[0]
            if date not in daily_data:
                daily_data[date] = []
            daily_data[date].append(item)

        forecasts = []
        for date, items in list(daily_data.items())[:days]:
            temps = [item["main"]["temp"] for item in items]
            weather = items[len(items) // 2]["weather"][0]
            humidity = sum(item["main"]["humidity"] for item in items) // len(items)
            wind_speed = sum(item["wind"]["speed"] for item in items) / len(items)
            precipitation = sum(
                item.get("pop", 0) for item in items
            ) / len(items) * 100

            forecasts.append(ForecastDay(
                date=date,
                temp_high=max(temps),
                temp_low=min(temps),
                description=weather.get("description", "Unknown"),
                icon=weather.get("icon", "01d"),
                humidity=humidity,
                wind_speed=wind_speed,
                precipitation=precipitation
            ))

        return forecasts

    def _deg_to_compass(self, deg: float) -> str:
        """Convert degrees to compass direction."""
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = round(deg / 45) % 8
        return directions[idx]

    def _get_mock_weather(self, location: str) -> WeatherData:
        """Return mock weather data when API unavailable."""
        return WeatherData(
            location=location,
            temperature=22.0,
            feels_like=21.0,
            humidity=65,
            wind_speed=5.2,
            wind_direction="NW",
            description="partly cloudy",
            icon="02d",
            pressure=1013,
            visibility=10000,
            timestamp=datetime.utcnow().isoformat()
        )

    def _get_mock_forecast(self, location: str, days: int) -> List[ForecastDay]:
        """Return mock forecast data when API unavailable."""
        forecasts = []
        base_date = datetime.utcnow()

        for i in range(days):
            date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            forecasts.append(ForecastDay(
                date=date,
                temp_high=25.0 + i,
                temp_low=15.0 + i,
                description="partly cloudy",
                icon="02d",
                humidity=60,
                wind_speed=5.0,
                precipitation=20.0
            ))

        return forecasts

    async def on_command(self, command: str, args: Optional[Dict] = None) -> Optional[str]:
        """Handle weather commands."""
        if command == "weather":
            location = args.get("location", "New York") if args else "New York"
            weather = await self.get_current_weather(location)
            return (
                f"Weather in {weather.location}: "
                f"{weather.temperature}°C, {weather.description}. "
                f"Humidity: {weather.humidity}%, "
                f"Wind: {weather.wind_speed} m/s {weather.wind_direction}"
            )

        elif command == "forecast":
            location = args.get("location", "New York") if args else "New York"
            days = args.get("days", 5) if args else 5
            forecast = await self.get_forecast(location, days)

            lines = [f"Weather forecast for {location}:"]
            for day in forecast:
                lines.append(
                    f"  {day.date}: {day.temp_low}°C - {day.temp_high}°C, "
                    f"{day.description}"
                )
            return "\n".join(lines)

        return None
