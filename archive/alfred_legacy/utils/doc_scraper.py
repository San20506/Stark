"""
ALFRED Documentation Scraper
On-demand documentation scraping for Code Brain context.

Features:
- Scrape any URL for documentation
- PyPI package docs
- GitHub README/docs
- Caching for repeated requests
"""

import os
import re
import json
import hashlib
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger("DocScraper")

# Lazy imports
requests = None
BeautifulSoup = None


def _load_deps():
    global requests, BeautifulSoup
    if requests is None:
        import requests as _requests
        requests = _requests
    if BeautifulSoup is None:
        from bs4 import BeautifulSoup as _bs
        BeautifulSoup = _bs


class DocScraper:
    """
    On-demand documentation scraper.
    
    Usage:
        scraper = DocScraper()
        docs = scraper.scrape("https://docs.python.org/3/library/json.html")
        
        # Or for PyPI packages
        docs = scraper.scrape_pypi("requests")
    """
    
    CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "doc_cache")
    CACHE_TTL_HOURS = 24  # Cache expires after 24 hours
    
    def __init__(self):
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        _load_deps()
    
    def _get_cache_path(self, url: str) -> str:
        """Generate cache file path for URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return os.path.join(self.CACHE_DIR, f"{url_hash}.json")
    
    def _get_cached(self, url: str) -> Optional[str]:
        """Get cached content if still valid."""
        cache_path = self._get_cache_path(url)
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            # Check TTL
            cached_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cached_time > timedelta(hours=self.CACHE_TTL_HOURS):
                return None
            
            logger.debug(f"Cache hit: {url[:50]}...")
            return cached['content']
        except:
            return None
    
    def _set_cache(self, url: str, content: str):
        """Cache content for URL."""
        cache_path = self._get_cache_path(url)
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'content': content
                }, f)
            logger.debug(f"Cached: {url[:50]}...")
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
    
    def scrape(self, url: str, max_length: int = 8000) -> str:
        """
        Scrape documentation from URL.
        
        Args:
            url: Documentation URL
            max_length: Maximum content length to return
            
        Returns:
            Cleaned documentation text
        """
        # Check cache first
        cached = self._get_cached(url)
        if cached:
            return cached[:max_length]
        
        try:
            # Fetch page
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'ALFRED-DocScraper/1.0'
            })
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove scripts, styles, nav, footer
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            
            # Try to find main content
            main_content = (
                soup.find('main') or 
                soup.find('article') or 
                soup.find(class_=re.compile(r'content|docs|documentation', re.I)) or
                soup.find('body')
            )
            
            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)
            
            # Clean up whitespace
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            cleaned = '\n'.join(lines)
            
            # Cache result
            self._set_cache(url, cleaned)
            
            logger.info(f"Scraped: {url[:50]}... ({len(cleaned)} chars)")
            return cleaned[:max_length]
            
        except Exception as e:
            logger.error(f"Scrape failed for {url}: {e}")
            return f"[Error scraping {url}: {e}]"
    
    def scrape_pypi(self, package: str) -> str:
        """Get documentation for a PyPI package."""
        # Try PyPI page
        url = f"https://pypi.org/project/{package}/"
        content = self.scrape(url)
        
        # Also try readthedocs
        rtd_url = f"https://{package}.readthedocs.io/en/latest/"
        try:
            rtd_content = self.scrape(rtd_url)
            if not rtd_content.startswith("[Error"):
                content += f"\n\n--- ReadTheDocs ---\n{rtd_content}"
        except:
            pass
        
        return content
    
    def scrape_github(self, repo: str) -> str:
        """
        Get README from GitHub repo.
        
        Args:
            repo: Format "owner/repo" (e.g., "microsoft/playwright-python")
        """
        # GitHub raw README
        raw_url = f"https://raw.githubusercontent.com/{repo}/main/README.md"
        
        try:
            response = requests.get(raw_url, timeout=10)
            if response.status_code == 200:
                return response.text[:8000]
        except:
            pass
        
        # Try master branch
        raw_url = f"https://raw.githubusercontent.com/{repo}/master/README.md"
        try:
            response = requests.get(raw_url, timeout=10)
            if response.status_code == 200:
                return response.text[:8000]
        except:
            pass
        
        return f"[Could not fetch README for {repo}]"
    
    def clear_cache(self):
        """Clear all cached documentation."""
        import shutil
        if os.path.exists(self.CACHE_DIR):
            shutil.rmtree(self.CACHE_DIR)
            os.makedirs(self.CACHE_DIR)
            logger.info("Doc cache cleared")


# Singleton
_scraper = None

def get_doc_scraper() -> DocScraper:
    global _scraper
    if _scraper is None:
        _scraper = DocScraper()
    return _scraper


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("   ALFRED Doc Scraper Test")
    print("=" * 60)
    
    scraper = get_doc_scraper()
    
    # Test PyPI
    print("\n📦 Scraping PyPI: requests")
    content = scraper.scrape_pypi("requests")
    print(f"   Got {len(content)} chars")
    print(f"   Preview: {content[:200]}...")
    
    # Test GitHub
    print("\n📁 Scraping GitHub: psf/requests")
    content = scraper.scrape_github("psf/requests")
    print(f"   Got {len(content)} chars")
    
    # Test URL
    print("\n🌐 Scraping URL: Python json docs")
    content = scraper.scrape("https://docs.python.org/3/library/json.html")
    print(f"   Got {len(content)} chars")
    
    print("\n✅ Done!")
