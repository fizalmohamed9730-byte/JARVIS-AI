"""News plugin for JARVIS AI assistant."""

import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..base import BasePlugin

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    """News article container."""
    title: str
    description: str
    content: str
    author: str
    source: str
    url: str
    image_url: Optional[str]
    published_at: str
    category: str


class NewsPlugin(BasePlugin):
    """News aggregation plugin."""

    @property
    def name(self) -> str:
        return "news"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Provides news headlines and article search"

    @property
    def author(self) -> str:
        return "JARVIS Team"

    def __init__(self):
        super().__init__()
        self._api_key: Optional[str] = None
        self._base_url = "https://newsapi.org/v2"
        self._tech_sources = [
            "techcrunch",
            "the-verge",
            "ars-technica",
            "wired",
            "engadget"
        ]

    async def initialize(self) -> None:
        """Initialize news plugin."""
        await super().initialize()
        self._api_key = self._config.get("api_key")

        if not self._api_key:
            self._logger.warning("NewsAPI key not configured")

    async def execute(self, action: str, **kwargs) -> Any:
        """Execute news action."""
        actions = {
            "headlines": self.get_headlines,
            "search": self.search_news,
            "tech": self.get_tech_news
        }

        handler = actions.get(action)
        if handler:
            return await handler(**kwargs)

        raise ValueError(f"Unknown action: {action}")

    def get_capabilities(self) -> List[str]:
        return ["headlines", "search", "tech_news"]

    async def get_headlines(
        self,
        category: str = "general",
        country: str = "us",
        page_size: int = 10
    ) -> List[NewsArticle]:
        """Get top headlines by category."""
        if not self._api_key:
            return self._get_mock_headlines(category, page_size)

        url = f"{self._base_url}/top-headlines"
        params = {
            "country": country,
            "category": category,
            "pageSize": page_size,
            "apiKey": self._api_key
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_articles(data.get("articles", []), category)
                else:
                    error = await response.text()
                    self._logger.error(f"News API error: {error}")
                    return self._get_mock_headlines(category, page_size)

    async def search_news(
        self,
        query: str,
        page_size: int = 10,
        sort_by: str = "relevancy",
        language: str = "en"
    ) -> List[NewsArticle]:
        """Search for news articles."""
        if not self._api_key:
            return self._get_mock_search_results(query, page_size)

        url = f"{self._base_url}/everything"
        params = {
            "q": query,
            "pageSize": page_size,
            "sortBy": sort_by,
            "language": language,
            "apiKey": self._api_key
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_articles(data.get("articles", []), "search")
                else:
                    self._logger.error(f"Search API error: {response.status}")
                    return self._get_mock_search_results(query, page_size)

    async def get_tech_news(
        self,
        page_size: int = 10
    ) -> List[NewsArticle]:
        """Get technology news from tech sources."""
        if not self._api_key:
            return self._get_mock_headlines("technology", page_size)

        url = f"{self._base_url}/top-headlines"
        sources = ",".join(self._tech_sources[:3])
        params = {
            "sources": sources,
            "pageSize": page_size,
            "apiKey": self._api_key
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_articles(
                        data.get("articles", []),
                        "technology"
                    )
                else:
                    self._logger.error(f"Tech news error: {response.status}")
                    return self._get_mock_headlines("technology", page_size)

    def _parse_articles(
        self,
        articles: List[dict],
        category: str
    ) -> List[NewsArticle]:
        """Parse API response into NewsArticle objects."""
        parsed = []

        for article in articles:
            source = article.get("source", {})
            parsed.append(NewsArticle(
                title=article.get("title", "No Title"),
                description=article.get("description", ""),
                content=article.get("content", ""),
                author=article.get("author", "Unknown"),
                source=source.get("name", "Unknown"),
                url=article.get("url", ""),
                image_url=article.get("urlToImage"),
                published_at=article.get("publishedAt", ""),
                category=category
            ))

        return parsed

    def _get_mock_headlines(
        self,
        category: str,
        count: int
    ) -> List[NewsArticle]:
        """Return mock headlines when API unavailable."""
        mock_articles = [
            NewsArticle(
                title=f"Breaking: Major development in {category}",
                description=f"Latest news and updates in the {category} sector.",
                content=f"In-depth analysis of recent {category} developments...",
                author="News Editor",
                source="Tech News Daily",
                url="https://example.com/news/1",
                image_url=None,
                published_at=datetime.utcnow().isoformat(),
                category=category
            ),
            NewsArticle(
                title=f"Industry Report: {category.title()} Trends for 2024",
                description=f"Comprehensive overview of {category} market trends.",
                content=f"Analysts predict significant growth in {category}...",
                author="Market Analyst",
                source="Business Insider",
                url="https://example.com/news/2",
                image_url=None,
                published_at=(datetime.utcnow() - timedelta(hours=2)).isoformat(),
                category=category
            ),
            NewsArticle(
                title=f"Innovation Spotlight: New {category.title()} Solutions",
                description=f"Revolutionary approaches to {category} challenges.",
                content=f"A new wave of innovation is transforming {category}...",
                author="Tech Reporter",
                source="Wired",
                url="https://example.com/news/3",
                image_url=None,
                published_at=(datetime.utcnow() - timedelta(hours=4)).isoformat(),
                category=category
            ),
            NewsArticle(
                title=f"Expert Opinion: The Future of {category.title()}",
                description=f"Industry leaders share their vision for {category}.",
                content=f"Top experts weigh in on where {category} is heading...",
                author="Columnist",
                source="The Verge",
                url="https://example.com/news/4",
                image_url=None,
                published_at=(datetime.utcnow() - timedelta(hours=6)).isoformat(),
                category=category
            ),
            NewsArticle(
                title=f"Data Analysis: {category.title()} by the Numbers",
                description=f"Statistical overview of the {category} landscape.",
                content=f"New data reveals key insights about {category}...",
                author="Data Team",
                source="Reuters",
                url="https://example.com/news/5",
                image_url=None,
                published_at=(datetime.utcnow() - timedelta(hours=8)).isoformat(),
                category=category
            )
        ]

        return mock_articles[:count]

    def _get_mock_search_results(
        self,
        query: str,
        count: int
    ) -> List[NewsArticle]:
        """Return mock search results when API unavailable."""
        return [
            NewsArticle(
                title=f"Search Result: {query} - Latest Updates",
                description=f"Comprehensive coverage of {query} developments.",
                content=f"Analysis of recent events related to {query}...",
                author="Research Team",
                source="News Aggregator",
                url=f"https://example.com/search?q={query}",
                image_url=None,
                published_at=datetime.utcnow().isoformat(),
                category="search"
            )
        ]

    async def on_command(self, command: str, args: Optional[Dict] = None) -> Optional[str]:
        """Handle news commands."""
        if command == "news":
            category = args.get("category", "general") if args else "general"
            articles = await self.get_headlines(category)

            lines = [f"Latest {category} news:"]
            for i, article in enumerate(articles[:5], 1):
                lines.append(f"{i}. {article.title}")
                lines.append(f"   {article.description[:100]}...")
                lines.append(f"   Source: {article.source}")
                lines.append("")

            return "\n".join(lines)

        elif command == "technews":
            articles = await self.get_tech_news()

            lines = ["Technology news:"]
            for i, article in enumerate(articles[:5], 1):
                lines.append(f"{i}. {article.title}")
                lines.append(f"   {article.description[:100]}...")
                lines.append("")

            return "\n".join(lines)

        elif command == "searchnews":
            query = args.get("query", "") if args else ""
            if not query:
                return "Please provide a search query"

            articles = await self.search_news(query)

            lines = [f"News results for '{query}':"]
            for i, article in enumerate(articles[:5], 1):
                lines.append(f"{i}. {article.title}")
                lines.append(f"   {article.description[:100]}...")
                lines.append(f"   {article.url}")
                lines.append("")

            return "\n".join(lines)

        return None
