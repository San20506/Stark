"""
ALFRED AUTONOMOUS RESEARCHER (Tier 2/4)
- Autonomous Web Research with Parallel Execution
- Document Processing
- Synthesis
"""

import logging
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from benchmark_tools import web_search

logger = logging.getLogger("Alfred.Researcher")

class ResearchAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def conduct_research(self, topic: str, depth: int = 3) -> str:
        """
        Execute full research loop: Plan -> Search (PARALLEL) -> Read -> Synthesize.
        Tier 2 Benchmark: 'Autonomously produce a research plan'
        """
        logger.info(f"🔎 Starting research on: {topic}")
        
        # 1. Generate Queries
        prompt = f"Generate 3 distinct search queries to research: '{topic}'. Return as bullet points."
        response = self.llm.generate(prompt)
        queries = [line.strip("- *") for line in response.split('\n') if line.strip().startswith(("-", "*"))]
        if not queries: queries = [topic]
        
        logger.info(f"🔎 Queries: {queries[:depth]}")
        
        # 2. Search & Aggregate (PARALLEL - 2-3x FASTER)
        aggregated_info = []
        
        def fetch_query(q):
            """Helper to fetch single query results."""
            logger.info(f"🌐 Searching: {q}")
            res = web_search(q, num_results=2)
            results = []
            if "results" in res:
                for item in res["results"]:
                    snippet = item.get("snippet", "")
                    title = item.get("title", "")
                    url = item.get("url", "")
                    results.append(f"Source: {title} ({url})\nContent: {snippet}\n")
            return results
        
        # Parallel execution
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(fetch_query, q): q for q in queries[:depth]}
            for future in as_completed(futures):
                try:
                    results = future.result()
                    aggregated_info.extend(results)
                except Exception as e:
                    logger.error(f"Search failed: {e}")
        
        if not aggregated_info:
            return "No information found."
            
        full_text = "\n".join(aggregated_info)
        
        # 3. Synthesize Report
        logger.info("📝 Synthesizing Report...")
        report_prompt = f"""
        Research Topic: {topic}
        Sources:
        {full_text[:3000]}
        
        Write a concise research report. 
        Structure:
        - Executive Summary
        - Key Findings
        - Sources
        """
        
        report = self.llm.generate(report_prompt)
        return report

# Standalone run
if __name__ == "__main__":
    from modules.llm import LLMClient
    logging.basicConfig(level=logging.INFO)
    agent = ResearchAgent(LLMClient())
    print(agent.conduct_research("latest advancements in solid state batteries"))
