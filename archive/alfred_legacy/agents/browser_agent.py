"""
ALFRED Browser Automation
Control web browsers using Playwright.

Enables ALFRED to navigate, fill forms, click elements, and scrape web pages.
"""

import os
import time
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install")


@dataclass
class BrowserResult:
    """Result of a browser action."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class BrowserAgent:
    """
    Browser automation agent using Playwright.
    
    Capabilities:
    - Navigate to URLs
    - Click elements by selector or text
    - Fill forms
    - Extract text and data
    - Take screenshots
    - Handle popups and dialogs
    """
    
    def __init__(self, headless: bool = False):
        """
        Initialize browser agent.
        
        Args:
            headless: Run browser in headless mode (no visible window)
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright not installed. Run: pip install playwright && playwright install")
        
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._started = False
    
    def start(self) -> BrowserResult:
        """Start the browser."""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.page = self.browser.new_page()
            self._started = True
            logger.info("✅ Browser started")
            return BrowserResult(True, "Browser started successfully")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return BrowserResult(False, f"Failed to start browser: {e}")
    
    def stop(self) -> BrowserResult:
        """Stop the browser."""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            self._started = False
            logger.info("Browser stopped")
            return BrowserResult(True, "Browser stopped")
        except Exception as e:
            return BrowserResult(False, f"Failed to stop browser: {e}")
    
    def _ensure_started(self):
        """Ensure browser is started."""
        if not self._started:
            self.start()
    
    # ==================== NAVIGATION ====================
    
    def goto(self, url: str, wait_until: str = "load") -> BrowserResult:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            wait_until: When to consider navigation done ("load", "domcontentloaded", "networkidle")
        """
        self._ensure_started()
        try:
            self.page.goto(url, wait_until=wait_until)
            return BrowserResult(True, f"Navigated to {url}", {"url": self.page.url, "title": self.page.title()})
        except Exception as e:
            return BrowserResult(False, f"Navigation failed: {e}")
    
    def back(self) -> BrowserResult:
        """Go back in browser history."""
        self._ensure_started()
        try:
            self.page.go_back()
            return BrowserResult(True, "Went back", {"url": self.page.url})
        except Exception as e:
            return BrowserResult(False, f"Back failed: {e}")
    
    def forward(self) -> BrowserResult:
        """Go forward in browser history."""
        self._ensure_started()
        try:
            self.page.go_forward()
            return BrowserResult(True, "Went forward", {"url": self.page.url})
        except Exception as e:
            return BrowserResult(False, f"Forward failed: {e}")
    
    def reload(self) -> BrowserResult:
        """Reload the current page."""
        self._ensure_started()
        try:
            self.page.reload()
            return BrowserResult(True, "Page reloaded", {"url": self.page.url})
        except Exception as e:
            return BrowserResult(False, f"Reload failed: {e}")
    
    # ==================== INTERACTION ====================
    
    def click(self, selector: str) -> BrowserResult:
        """
        Click an element by CSS selector.
        
        Args:
            selector: CSS selector (e.g., "button.submit", "#login-btn")
        """
        self._ensure_started()
        try:
            self.page.click(selector)
            return BrowserResult(True, f"Clicked {selector}")
        except Exception as e:
            return BrowserResult(False, f"Click failed: {e}")
    
    def click_text(self, text: str) -> BrowserResult:
        """
        Click an element containing specific text.
        
        Args:
            text: Text to find and click
        """
        self._ensure_started()
        try:
            self.page.click(f"text={text}")
            return BrowserResult(True, f"Clicked element with text '{text}'")
        except Exception as e:
            return BrowserResult(False, f"Click text failed: {e}")
    
    def fill(self, selector: str, value: str) -> BrowserResult:
        """
        Fill a text input field.
        
        Args:
            selector: CSS selector for input field
            value: Text to fill
        """
        self._ensure_started()
        try:
            self.page.fill(selector, value)
            return BrowserResult(True, f"Filled {selector} with value")
        except Exception as e:
            return BrowserResult(False, f"Fill failed: {e}")
    
    def type_text(self, selector: str, text: str, delay: int = 50) -> BrowserResult:
        """
        Type text into an element (simulates keystrokes).
        
        Args:
            selector: CSS selector for input field
            text: Text to type
            delay: Delay between keystrokes in ms
        """
        self._ensure_started()
        try:
            self.page.type(selector, text, delay=delay)
            return BrowserResult(True, f"Typed text into {selector}")
        except Exception as e:
            return BrowserResult(False, f"Type failed: {e}")
    
    def press(self, key: str) -> BrowserResult:
        """
        Press a keyboard key.
        
        Args:
            key: Key to press (e.g., "Enter", "Tab", "Escape")
        """
        self._ensure_started()
        try:
            self.page.keyboard.press(key)
            return BrowserResult(True, f"Pressed {key}")
        except Exception as e:
            return BrowserResult(False, f"Press failed: {e}")
    
    def select(self, selector: str, value: str) -> BrowserResult:
        """
        Select an option from a dropdown.
        
        Args:
            selector: CSS selector for select element
            value: Value to select
        """
        self._ensure_started()
        try:
            self.page.select_option(selector, value)
            return BrowserResult(True, f"Selected {value} in {selector}")
        except Exception as e:
            return BrowserResult(False, f"Select failed: {e}")
    
    def scroll(self, direction: str = "down", amount: int = 500) -> BrowserResult:
        """
        Scroll the page.
        
        Args:
            direction: "up" or "down"
            amount: Pixels to scroll
        """
        self._ensure_started()
        try:
            delta = amount if direction == "down" else -amount
            self.page.mouse.wheel(0, delta)
            return BrowserResult(True, f"Scrolled {direction} by {amount}px")
        except Exception as e:
            return BrowserResult(False, f"Scroll failed: {e}")
    
    # ==================== DATA EXTRACTION ====================
    
    def get_text(self, selector: str) -> BrowserResult:
        """
        Get text content of an element.
        
        Args:
            selector: CSS selector
        """
        self._ensure_started()
        try:
            text = self.page.text_content(selector)
            return BrowserResult(True, "Text extracted", {"text": text})
        except Exception as e:
            return BrowserResult(False, f"Get text failed: {e}")
    
    def get_all_text(self, selector: str) -> BrowserResult:
        """
        Get text from all matching elements.
        
        Args:
            selector: CSS selector
        """
        self._ensure_started()
        try:
            elements = self.page.query_selector_all(selector)
            texts = [el.text_content() for el in elements]
            return BrowserResult(True, f"Found {len(texts)} elements", {"texts": texts})
        except Exception as e:
            return BrowserResult(False, f"Get all text failed: {e}")
    
    def get_attribute(self, selector: str, attribute: str) -> BrowserResult:
        """
        Get an attribute value from an element.
        
        Args:
            selector: CSS selector
            attribute: Attribute name (e.g., "href", "src", "class")
        """
        self._ensure_started()
        try:
            value = self.page.get_attribute(selector, attribute)
            return BrowserResult(True, "Attribute extracted", {"attribute": attribute, "value": value})
        except Exception as e:
            return BrowserResult(False, f"Get attribute failed: {e}")
    
    def get_page_content(self) -> BrowserResult:
        """Get the full page HTML content."""
        self._ensure_started()
        try:
            content = self.page.content()
            return BrowserResult(True, "Page content extracted", {"html": content[:5000] + "..." if len(content) > 5000 else content})
        except Exception as e:
            return BrowserResult(False, f"Get content failed: {e}")
    
    def get_page_info(self) -> BrowserResult:
        """Get current page URL and title."""
        self._ensure_started()
        try:
            return BrowserResult(True, "Page info", {"url": self.page.url, "title": self.page.title()})
        except Exception as e:
            return BrowserResult(False, f"Get page info failed: {e}")
    
    # ==================== SCREENSHOTS ====================
    
    def screenshot(self, filepath: str = None, full_page: bool = False) -> BrowserResult:
        """
        Take a screenshot.
        
        Args:
            filepath: Path to save screenshot (optional)
            full_page: Capture full scrollable page
        """
        self._ensure_started()
        try:
            if not filepath:
                filepath = f"screenshot_{int(time.time())}.png"
            
            self.page.screenshot(path=filepath, full_page=full_page)
            return BrowserResult(True, f"Screenshot saved to {filepath}", {"filepath": filepath})
        except Exception as e:
            return BrowserResult(False, f"Screenshot failed: {e}")
    
    # ==================== WAITING ====================
    
    def wait_for_selector(self, selector: str, timeout: int = 10000) -> BrowserResult:
        """
        Wait for an element to appear.
        
        Args:
            selector: CSS selector to wait for
            timeout: Max wait time in ms
        """
        self._ensure_started()
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return BrowserResult(True, f"Element {selector} found")
        except Exception as e:
            return BrowserResult(False, f"Wait failed: {e}")
    
    def wait_for_navigation(self, timeout: int = 30000) -> BrowserResult:
        """Wait for page navigation to complete."""
        self._ensure_started()
        try:
            self.page.wait_for_load_state("load", timeout=timeout)
            return BrowserResult(True, "Navigation complete", {"url": self.page.url})
        except Exception as e:
            return BrowserResult(False, f"Wait for navigation failed: {e}")
    
    # ==================== CONTEXT MANAGER ====================
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# Singleton for convenience
_browser_agent = None

def get_browser_agent(headless: bool = False) -> BrowserAgent:
    """Get or create the browser agent singleton."""
    global _browser_agent
    if _browser_agent is None:
        _browser_agent = BrowserAgent(headless=headless)
    return _browser_agent


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("ALFRED Browser Automation - Test")
    print("=" * 60)
    
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright not installed")
        print("   Run: pip install playwright && playwright install")
        exit(1)
    
    with BrowserAgent(headless=False) as browser:
        # Test 1: Navigate
        print("\n1. Navigating to Google...")
        result = browser.goto("https://www.google.com")
        print(f"   {result.message}")
        
        # Test 2: Get page info
        print("\n2. Getting page info...")
        result = browser.get_page_info()
        print(f"   Title: {result.data['title']}")
        print(f"   URL: {result.data['url']}")
        
        # Test 3: Screenshot
        print("\n3. Taking screenshot...")
        result = browser.screenshot("browser_test.png")
        print(f"   {result.message}")
        
        print("\n✅ Browser automation working!")
        input("\nPress Enter to close browser...")
