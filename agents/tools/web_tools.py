"""Web-related tools for JARVIS AI agent system."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


@tool
def web_search(query: str, num_results: int = 5) -> str:
    """Search the web using DuckDuckGo and return summarized results.

    Args:
        query: The search query string.
        num_results: Number of results to return (1-20). Defaults to 5.

    Returns:
        A formatted string of search results with titles, URLs, and snippets.
    """
    if not query or not query.strip():
        return "Error: Search query cannot be empty."

    num_results = max(1, min(20, num_results))

    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))

        if not results:
            return f"No results found for: {query}"

        formatted = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            url = result.get("href", result.get("link", "No URL"))
            snippet = result.get("body", result.get("snippet", "No description"))
            formatted.append(f"{i}. **{title}**\n   URL: {url}\n   {snippet}\n")

        return "\n".join(formatted)

    except ImportError:
        return _fallback_search(query, num_results)
    except Exception as e:
        logger.error("Web search failed: %s", e)
        return f"Search error: {e}"


def _fallback_search(query: str, num_results: int) -> str:
    """Fallback search using direct HTTP request to DuckDuckGo HTML."""
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": _USER_AGENT}
        data = {"q": query, "b": ""}

        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.post(url, data=data, headers=headers)
            resp.raise_for_status()

        from html.parser import HTMLParser

        class ResultParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results: list[dict[str, str]] = []
                self._current: dict[str, str] = {}
                self._in_result = False
                self._in_title = False
                self._in_snippet = False
                self._tag_stack: list[str] = []

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                cls = attrs_dict.get("class", "")
                if tag == "a" and "result__a" in cls:
                    self._in_title = True
                    self._current["url"] = attrs_dict.get("href", "")
                    self._current["title"] = ""
                elif tag == "a" and "result__snippet" in cls:
                    self._in_snippet = True
                    self._current["snippet"] = ""
                self._tag_stack.append(tag)

            def handle_endtag(self, tag):
                if self._tag_stack:
                    self._tag_stack.pop()
                if tag == "a" and self._in_title:
                    self._in_title = False
                elif tag == "a" and self._in_snippet:
                    self._in_snippet = False
                    if self._current.get("title"):
                        self.results.append(dict(self._current))
                    self._current = {}

            def handle_data(self, data):
                if self._in_title:
                    self._current["title"] = self._current.get("title", "") + data
                elif self._in_snippet:
                    self._current["snippet"] = self._current.get("snippet", "") + data

        parser = ResultParser()
        parser.feed(resp.text)
        results = parser.results[:num_results]

        if not results:
            return f"No results found for: {query}"

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"{i}. **{r.get('title', 'No title')}**\n"
                f"   URL: {r.get('url', 'No URL')}\n"
                f"   {r.get('snippet', 'No description')}\n"
            )
        return "\n".join(formatted)

    except Exception as e:
        return f"Fallback search failed: {e}. Install duckduckgo-search: pip install duckduckgo-search"


@tool
def fetch_webpage(url: str, max_length: int = 5000) -> str:
    """Fetch and parse the text content of a webpage.

    Args:
        url: The URL to fetch. Must be a valid HTTP/HTTPS URL.
        max_length: Maximum characters to return. Defaults to 5000.

    Returns:
        The extracted text content of the page, truncated to max_length.
    """
    if not url or not url.strip():
        return "Error: URL cannot be empty."

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return f"Cannot parse content type: {content_type}"

        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            _SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript"}

            def __init__(self):
                super().__init__()
                self._text_parts: list[str] = []
                self._skip_depth = 0

            def handle_starttag(self, tag, attrs):
                if tag in self._SKIP_TAGS:
                    self._skip_depth += 1

            def handle_endtag(self, tag):
                if tag in self._SKIP_TAGS and self._skip_depth > 0:
                    self._skip_depth -= 1

            def handle_data(self, data):
                if self._skip_depth == 0:
                    stripped = data.strip()
                    if stripped:
                        self._text_parts.append(stripped)

            def get_text(self) -> str:
                return " ".join(self._text_parts)

        extractor = TextExtractor()
        extractor.feed(resp.text)
        text = extractor.get_text()

        if len(text) > max_length:
            text = text[:max_length] + "... [truncated]"

        return text if text else "No readable text content found on the page."

    except httpx.TimeoutException:
        return f"Timeout fetching {url}. The server took too long to respond."
    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code} fetching {url}"
    except Exception as e:
        logger.error("Failed to fetch webpage %s: %s", url, e)
        return f"Error fetching webpage: {e}"


@tool
def search_youtube(query: str, num_results: int = 5) -> str:
    """Search YouTube for videos matching the query.

    Args:
        query: The search query for YouTube videos.
        num_results: Number of results to return (1-20). Defaults to 5.

    Returns:
        A formatted list of YouTube video results with titles, URLs, and descriptions.
    """
    if not query or not query.strip():
        return "Error: Search query cannot be empty."

    num_results = max(1, min(20, num_results))

    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(f"site:youtube.com {query}", max_results=num_results))

        if not results:
            return f"No YouTube results found for: {query}"

        formatted = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            url = result.get("href", result.get("link", "No URL"))
            snippet = result.get("body", result.get("snippet", ""))
            formatted.append(f"{i}. **{title}**\n   URL: {url}\n   {snippet}\n")

        return "\n".join(formatted)

    except ImportError:
        return (
            "YouTube search requires duckduckgo-search. "
            "Install it: pip install duckduckgo-search"
        )
    except Exception as e:
        logger.error("YouTube search failed: %s", e)
        return f"YouTube search error: {e}"


@tool
def fetch_url_content(url: str) -> str:
    """Fetch raw content from a URL (APIs, JSON endpoints, plain text).

    Args:
        url: The URL to fetch content from.

    Returns:
        The raw response content as a string.
    """
    if not url or not url.strip():
        return "Error: URL cannot be empty."

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        headers = {"User-Agent": _USER_AGENT, "Accept": "*/*"}

        with httpx.Client(timeout=20, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()

        text = resp.text
        if len(text) > 10000:
            text = text[:10000] + "... [truncated]"

        return text

    except httpx.TimeoutException:
        return f"Timeout fetching {url}"
    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code} fetching {url}"
    except Exception as e:
        return f"Error: {e}"


web_tools = [web_search, fetch_webpage, search_youtube, fetch_url_content]
