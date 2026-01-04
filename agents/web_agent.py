"""
Web Agent
=========
Agent specialized in web searching and information extraction.

Capabilities:
- Search the web (DuckDuckGo)
- Scrape page content and convert to Markdown
- Analyze and summarize web information
"""

import logging
import json
import asyncio
import re
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import html2text

from agents.base_agent import BaseAgent, AgentResult, AgentType
from utils.browser_manager import get_browser_manager

logger = logging.getLogger(__name__)

class WebAgent(BaseAgent):
    """
    Agent for web-based research and data extraction.
    """
    
    def __init__(self, name: str = "WebAgent"):
        super().__init__(
            name=name,
            agent_type=AgentType.WEB,
            description="Web searching, scraping, and research",
        )
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = True
        self.h2t.body_width = 0  # No wrapping

    def execute(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        """
        Execute web operation.
        
        Args:
            task: Task description or search query
            context: Optional context with:
                - operation: 'search' | 'scrape' | 'summarize'
                - url: URL to scrape
        """
        return asyncio.run(self._async_execute(task, context))

    async def _async_execute(self, task: str, context: Dict[str, Any] = None) -> AgentResult:
        context = context or {}
        steps = []
        
        operation = context.get('operation')
        if not operation:
            # Heuristic to detect operation from task
            if task.lower().startswith(('http://', 'https://')):
                operation = 'scrape'
            else:
                operation = 'search'

        try:
            if operation == 'search':
                return await self._search(task, steps)
            elif operation == 'scrape':
                url = context.get('url') or self._extract_url(task)
                if not url:
                    return AgentResult(success=False, output="", error="No URL provided for scraping", steps_taken=steps)
                return await self._scrape(url, steps)
            else:
                return AgentResult(success=False, output="", error=f"Unknown operation: {operation}", steps_taken=steps)
        
        except Exception as e:
            logger.error(f"WebAgent error: {e}", exc_info=True)
            return AgentResult(success=False, output="", error=str(e), steps_taken=steps)

    async def _search(self, query: str, steps: List[str]) -> AgentResult:
        steps.append(f"Searching for: {query}")
        
        # Using DuckDuckGo HTML/Lite search to avoid JS heavy pages during search
        # Or better yet, just use a simple request if possible, but BrowserManager is more robust
        search_url = f"https://duckduckgo.com/html/?q={query}"
        
        bm = get_browser_manager()
        html = await bm.get_page_content(search_url)
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        for result in soup.select('.result'):
            title_node = result.select_one('.result__title a')
            snippet_node = result.select_one('.result__snippet')
            
            if title_node and snippet_node:
                results.append({
                    "title": title_node.text.strip(),
                    "link": title_node['href'],
                    "snippet": snippet_node.text.strip()
                })
        
        if not results:
            # Fallback for Lite version
            for result in soup.select('.links_main'):
                title_node = result.select_one('.result-link')
                snippet_node = result.select_one('.result-snippet')
                if title_node:
                    results.append({
                        "title": title_node.text.strip(),
                        "link": title_node['href'],
                        "snippet": snippet_node.text.strip() if snippet_node else ""
                    })

        steps.append(f"Found {len(results)} results")
        
        output = json.dumps({"query": query, "results": results[:5]}, indent=2)
        return AgentResult(success=True, output=output, steps_taken=steps)

    async def _scrape(self, url: str, steps: List[str]) -> AgentResult:
        steps.append(f"Scraping URL: {url}")
        
        bm = get_browser_manager()
        html = await bm.get_page_content(url)
        
        markdown = self.h2t.handle(html)
        
        # Basic cleaning of multiple empty lines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        steps.append(f"Extracted {len(markdown)} characters of content")
        
        return AgentResult(
            success=True,
            output=markdown,
            steps_taken=steps
        )

    def _extract_url(self, text: str) -> Optional[str]:
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text)
        return urls[0] if urls else None
