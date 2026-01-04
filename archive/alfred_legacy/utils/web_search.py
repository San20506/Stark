"""
ALFRED Web Search Module
Provides internet access capabilities: searching Google and extracting web content.
"""

import logging
import requests
from bs4 import BeautifulSoup
import html2text
from typing import List, Dict, Optional
from duckduckgo_search import DDGS

# Configure logging
logger = logging.getLogger("Alfred.WebSearch")

class WebSearcher:
    """Handles web searching and content extraction."""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = True
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = True
        self.html_converter.body_width = 0  # No wrapping
        self.ddgs = DDGS()
        
    def search(self, query: str, num_results: int = 3) -> List[str]:
        """Perform a Web search and return a list of URLs."""
        try:
            logger.info(f"🔍 Searching Web for: '{query}'")
            # DuckDuckGo Search
            results = self.ddgs.text(query, max_results=num_results)
            
            # Extract just the URLs
            urls = []
            if results:
                for result in results:
                    # DDGS returns dicts with 'href'
                    if 'href' in result:
                        urls.append(result['href'])
                    
            logger.info(f"Found URLs: {urls}")
            return urls[:num_results]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def extract_content(self, url: str, max_chars: int = 2000) -> str:
        """Fetch URL and extract main text content converted to Markdown."""
        try:
            logger.debug(f"🌐 Fetching: {url}")
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove clutter
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'ads', 'noscript']):
                tag.decompose()
            
            # Convert to Markdown
            text = self.html_converter.handle(str(soup))
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Truncate
            if len(text) > max_chars:
                text = text[:max_chars] + "... [truncated]"
                
            return text
        except Exception as e:
            logger.warning(f"Failed to extract content from {url}: {e}")
            return ""

    def get_web_context(self, query: str) -> str:
        """High-level function: Search -> Scrape -> Aggregate Context."""
        urls = self.search(query, num_results=3)
        if not urls:
            return "No search results found."
        
        context_parts = [f"Web Search Results for '{query}':\n"]
        
        for i, url in enumerate(urls, 1):
            content = self.extract_content(url)
            if content:
                context_parts.append(f"--- RESULT {i} ({url}) ---\n{content}\n")
        
        full_context = "\n".join(context_parts)
        return full_context
