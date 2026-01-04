"""
ALFRED Skill Searcher
Searches GitHub and Stack Overflow for code solutions.
"""

import logging
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger("Alfred.SkillSearcher")

@dataclass
class SearchResult:
    """Represents a code search result."""
    source: str  # "github" or "stackoverflow"
    title: str
    url: str
    code: str
    score: float  # Quality score
    metadata: Dict[str, Any]

class SkillSearcher:
    """Searches for code solutions from multiple sources."""
    
    def __init__(self):
        self.github_api = "https://api.github.com"
        self.so_api = "https://api.stackexchange.com/2.3"
        logger.info("✅ SkillSearcher initialized")
    
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search all sources and return ranked results."""
        results = []
        
        # Search GitHub
        try:
            gh_results = self._search_github(query, max_results=3)
            results.extend(gh_results)
        except Exception as e:
            logger.warning(f"GitHub search failed: {e}")
        
        # Search Stack Overflow
        try:
            so_results = self._search_stackoverflow(query, max_results=3)
            results.extend(so_results)
        except Exception as e:
            logger.warning(f"Stack Overflow search failed: {e}")
        
        # Rank and return top results
        ranked = self._rank_results(results)
        return ranked[:max_results]
    
    def _search_github(self, query: str, max_results: int = 3) -> List[SearchResult]:
        """Search GitHub repositories."""
        results = []
        
        # GitHub code search
        search_query = f"{query} language:python"
        url = f"{self.github_api}/search/repositories"
        params = {
            "q": search_query,
            "sort": "stars",
            "order": "desc",
            "per_page": max_results
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            for item in data.get("items", [])[:max_results]:
                # Get README for code extraction
                readme_url = f"{self.github_api}/repos/{item['full_name']}/readme"
                readme_resp = requests.get(readme_url, timeout=10)
                
                code = ""
                if readme_resp.status_code == 200:
                    readme_data = readme_resp.json()
                    # README is base64 encoded
                    import base64
                    code = base64.b64decode(readme_data.get("content", "")).decode("utf-8")
                
                results.append(SearchResult(
                    source="github",
                    title=item["name"],
                    url=item["html_url"],
                    code=code,
                    score=item["stargazers_count"] / 1000.0,  # Normalize
                    metadata={
                        "stars": item["stargazers_count"],
                        "description": item.get("description", ""),
                        "language": item.get("language", "Python")
                    }
                ))
                
                time.sleep(0.5)  # Rate limiting
        
        except Exception as e:
            logger.error(f"GitHub API error: {e}")
        
        return results
    
    def _search_stackoverflow(self, query: str, max_results: int = 3) -> List[SearchResult]:
        """Search Stack Overflow answers."""
        results = []
        
        url = f"{self.so_api}/search/advanced"
        params = {
            "order": "desc",
            "sort": "votes",
            "q": query,
            "accepted": "True",
            "site": "stackoverflow",
            "filter": "withbody",
            "pagesize": max_results
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            for item in data.get("items", [])[:max_results]:
                # Extract code from answer body
                code = self._extract_code_from_html(item.get("body", ""))
                
                results.append(SearchResult(
                    source="stackoverflow",
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    code=code,
                    score=item.get("score", 0) / 100.0,  # Normalize
                    metadata={
                        "votes": item.get("score", 0),
                        "answered": item.get("is_answered", False),
                        "tags": item.get("tags", [])
                    }
                ))
        
        except Exception as e:
            logger.error(f"Stack Overflow API error: {e}")
        
        return results
    
    def _extract_code_from_html(self, html: str) -> str:
        """Extract code blocks from HTML."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            code_blocks = soup.find_all('code')
            return "\n\n".join([block.get_text() for block in code_blocks])
        except Exception as e:
            logger.debug(f"Code extraction failed: {e}")
            return ""
    
    def _rank_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Rank results by quality score."""
        return sorted(results, key=lambda x: x.score, reverse=True)

# Global instance
skill_searcher = SkillSearcher()
