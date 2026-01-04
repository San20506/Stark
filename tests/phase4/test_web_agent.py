"""
Test Web Agent
==============
Tests for web searching and scraping.
"""

# import pytest
import asyncio
import json
from agents.web_agent import WebAgent

@pytest.mark.asyncio
async def test_web_agent_search():
    """Test DuckDuckGo search."""
    agent = WebAgent()
    # Execute normally runs in a new loop via asyncio.run, 
    # but we can test the internal _async_execute if we want more control.
    result = await agent._async_execute("Python programming language", context={"operation": "search"})
    
    assert result.success
    data = json.loads(result.output)
    assert "query" in data
    assert len(data["results"]) > 0
    assert "Python" in data["results"][0]["title"]

@pytest.mark.asyncio
async def test_web_agent_scrape():
    """Test web scraping."""
    agent = WebAgent()
    # Using a stable URL for testing
    url = "https://example.com"
    result = await agent._async_execute(f"scrape {url}", context={"operation": "scrape", "url": url})
    
    assert result.success
    assert "Example Domain" in result.output
    assert len(result.output) > 50

if __name__ == "__main__":
    # Workaround for running async tests manually
    agent = WebAgent()
    loop = asyncio.get_event_loop()
    
    print("Testing search...")
    search_res = loop.run_until_complete(agent._async_execute("STARK AI"))
    print(search_res.output)
    
    print("\nTesting scrape...")
    scrape_res = loop.run_until_complete(agent._async_execute("https://example.com"))
    print(scrape_res.output)
