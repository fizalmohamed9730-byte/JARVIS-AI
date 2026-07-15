"""Browser automation manager using Playwright for web interaction."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages a Playwright browser instance for web automation tasks.

    Supports headless and headed modes, page content extraction, form filling,
    element clicking, file downloading, and history tracking.
    """

    def __init__(self) -> None:
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None
        self._history: List[str] = []
        self._initialized = False

    async def initialize(self, headless: bool = True) -> None:
        """Launch the browser and create a new context.

        Args:
            headless: Run without visible GUI when *True*.
        """
        if self._initialized:
            return

        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            self._context = await self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
            )
            self._page = await self._context.new_page()
            self._initialized = True
            logger.info("Browser initialized (headless=%s)", headless)
        except ImportError:
            raise RuntimeError(
                "Playwright is required for browser automation. "
                "Install with: pip install playwright && playwright install chromium"
            )
        except Exception as exc:
            logger.exception("Failed to initialize browser")
            raise RuntimeError(f"Browser initialization failed: {exc}") from exc

    async def _ensure_initialized(self) -> None:
        if not self._initialized:
            await self.initialize()

    async def _get_page(self) -> Any:
        """Return a usable page, creating one if necessary."""
        await self._ensure_initialized()
        if self._page is None or self._page.is_closed():
            self._page = await self._context.new_page()
        return self._page

    async def open_url(self, url: str) -> Dict[str, Any]:
        """Navigate to *url* and return page title."""
        page = await self._get_page()
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = await page.title()
            self._history.append(url)
            return {
                "success": True,
                "url": page.url,
                "title": title,
                "status": response.status if response else None,
            }
        except Exception as exc:
            logger.exception("Failed to open URL: %s", url)
            return {"success": False, "error": str(exc)}

    async def search_google(self, query: str) -> Dict[str, Any]:
        """Perform a Google search and return top results."""
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        page = await self._get_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self._history.append(url)
            await page.wait_for_timeout(2000)

            results: List[Dict[str, str]] = []
            search_results = await page.query_selector_all("div.g")
            for i, result in enumerate(search_results[:10]):
                try:
                    title_el = await result.query_selector("h3")
                    link_el = await result.query_selector("a")
                    snippet_el = await result.query_selector("div.VwiC3b")

                    title = await title_el.inner_text() if title_el else ""
                    href = await link_el.get_attribute("href") if link_el else ""
                    snippet = await snippet_el.inner_text() if snippet_el else ""

                    if title and href:
                        results.append({
                            "position": i + 1,
                            "title": title,
                            "url": href,
                            "snippet": snippet,
                        })
                except Exception:
                    continue

            return {"success": True, "query": query, "results": results}
        except Exception as exc:
            logger.exception("Google search failed for: %s", query)
            return {"success": False, "error": str(exc), "results": []}

    async def search_youtube(self, query: str) -> Dict[str, Any]:
        """Search YouTube and return video results."""
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        page = await self._get_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self._history.append(url)
            await page.wait_for_timeout(3000)

            results: List[Dict[str, str]] = []
            video_elements = await page.query_selector_all("ytd-video-renderer")
            for i, video in enumerate(video_elements[:10]):
                try:
                    title_el = await video.query_selector("#video-title")
                    channel_el = await video.query_selector("#channel-name a")
                    meta_el = await video.query_selector("#metadata-line span")

                    title = await title_el.inner_text() if title_el else ""
                    href = await title_el.get_attribute("href") if title_el else ""
                    channel = await channel_el.inner_text() if channel_el else ""
                    meta = await meta_el.inner_text() if meta_el else ""

                    if title:
                        results.append({
                            "position": i + 1,
                            "title": title.strip(),
                            "url": f"https://www.youtube.com{href}" if href else "",
                            "channel": channel.strip(),
                            "meta": meta.strip(),
                        })
                except Exception:
                    continue

            return {"success": True, "query": query, "results": results}
        except Exception as exc:
            logger.exception("YouTube search failed for: %s", query)
            return {"success": False, "error": str(exc), "results": []}

    async def read_page_content(self, url: Optional[str] = None) -> Dict[str, Any]:
        """Read and return text content of the current or specified page."""
        page = await self._get_page()
        try:
            if url and (page.url != url):
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                self._history.append(url)

            title = await page.title()
            text_content = await page.evaluate("""
                () => {
                    const article = document.querySelector('article')
                        || document.querySelector('main')
                        || document.querySelector('[role="main"]')
                        || document.body;
                    return article ? article.innerText : document.body.innerText;
                }
            """)
            url_final = page.url

            return {
                "success": True,
                "url": url_final,
                "title": title,
                "content": text_content[:50000],
            }
        except Exception as exc:
            logger.exception("Failed to read page content")
            return {"success": False, "error": str(exc)}

    async def fill_form(
        self, url: str, form_data: Dict[str, str], submit: bool = False
    ) -> Dict[str, Any]:
        """Navigate to *url* and fill form fields specified by *form_data*.

        Args:
            url: Target URL.
            form_data: Mapping of CSS selectors to values.
            submit: Click the submit button after filling.
        """
        page = await self._get_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self._history.append(url)
            await page.wait_for_timeout(1000)

            filled_fields: List[str] = []
            for selector, value in form_data.items():
                try:
                    element = await page.query_selector(selector)
                    if element:
                        await element.fill(value)
                        filled_fields.append(selector)
                    else:
                        logger.warning("Form element not found: %s", selector)
                except Exception as field_exc:
                    logger.warning("Failed to fill %s: %s", selector, field_exc)

            if submit:
                try:
                    await page.keyboard.press("Enter")
                except Exception:
                    pass

            return {
                "success": bool(filled_fields),
                "filled_fields": filled_fields,
                "total_fields": len(form_data),
            }
        except Exception as exc:
            logger.exception("Form fill failed")
            return {"success": False, "error": str(exc)}

    async def click_element(self, selector: str, url: Optional[str] = None) -> Dict[str, Any]:
        """Click an element matching *selector*, optionally after navigating to *url*."""
        page = await self._get_page()
        try:
            if url and (page.url != url):
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                self._history.append(url)

            element = await page.wait_for_selector(selector, timeout=10000)
            if element:
                await element.click()
                await page.wait_for_timeout(1000)
                return {"success": True, "clicked": selector, "url": page.url}
            return {"success": False, "error": f"Element not found: {selector}"}
        except Exception as exc:
            logger.exception("Click failed for selector: %s", selector)
            return {"success": False, "error": str(exc)}

    async def download_file(
        self, url: str, save_path: str, timeout: int = 60000
    ) -> Dict[str, Any]:
        """Download a file from *url* to *save_path*."""
        page = await self._get_page()
        try:
            save_dir = os.path.dirname(save_path)
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)

            async with page.expect_download(timeout=timeout) as download_info:
                await page.goto(url, wait_until="commit", timeout=timeout)

            download = await download_info.value
            await download.path()  # Wait for download to complete

            # Move from temp to target
            import shutil
            temp_path = await download.path()
            if temp_path:
                shutil.copy2(temp_path, save_path)
            else:
                # Fallback: use requests
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            with open(save_path, "wb") as f:
                                f.write(content)

            return {"success": True, "path": save_path, "filename": download.suggested_filename}
        except Exception as exc:
            logger.exception("Download failed for: %s", url)
            # Fallback using urllib
            try:
                import urllib.request
                urllib.request.urlretrieve(url, save_path)
                return {"success": True, "path": save_path, "note": "Downloaded via urllib fallback"}
            except Exception:
                return {"success": False, "error": str(exc)}

    async def get_history(self) -> List[str]:
        """Return list of URLs visited in this session."""
        return list(self._history)

    async def close(self) -> None:
        """Close the browser and clean up resources."""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            self._initialized = False
            self._browser = None
            self._context = None
            self._page = None
            logger.info("Browser closed")
        except Exception as exc:
            logger.warning("Error closing browser: %s", exc)
