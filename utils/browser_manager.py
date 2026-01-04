"""
Browser Manager
================
Lifecyle management for headless Chromium using Playwright.
"""

import logging
import asyncio
from typing import Optional, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Manages Playwright browser instances for the WebAgent.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw = None
        self._browser = None
        self._context = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self):
        """Lazy initialization of browser."""
        async with self._lock:
            if self._pw is None:
                self._pw = await async_playwright().start()
                self._browser = await self._pw.chromium.launch(headless=self.headless)
                # Set a standard viewport and user agent
                self._context = await self._browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1280, 'height': 800}
                )

    async def new_page(self) -> Page:
        """Create a new page in the managed context."""
        await self._ensure_browser()
        return await self._context.new_page()

    async def close(self):
        """Cleanup resources."""
        async with self._lock:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
            self._pw = None
            self._browser = None
            self._context = None

    async def get_page_content(self, url: str, wait_until: str = "networkidle", timeout: int = 30000) -> str:
        """
        Navigate to a URL and return the HTML content.
        """
        page = await self.new_page()
        try:
            # Block unnecessary resources to speed up
            await page.route("**/*.{png,jpg,jpeg,gif,css,woff,woff2,ttf,otf,svg,ico}", lambda route: route.abort())
            
            await page.goto(url, wait_until=wait_until, timeout=timeout)
            return await page.content()
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise
        finally:
            await page.close()

# Global instance for easy reuse within the process
_instance = None

def get_browser_manager() -> BrowserManager:
    global _instance
    if _instance is None:
        _instance = BrowserManager()
    return _instance
