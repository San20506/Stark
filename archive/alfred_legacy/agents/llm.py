"""
ALFRED LLM CLIENT
Abstraction for Tier 1 Reliability & Tier 7 Safety
"""

import logging
from typing import List, Dict, Optional, Generator

logger = logging.getLogger("Alfred.LLM")

class LLMClient:
    def __init__(self, model_name: str = "deepseek-r1:1.5b"):
        self.model_name = model_name
        self.client = None
        self._connect()

    def _connect(self):
        try:
            import ollama
            self.client = ollama
            logger.info(f"✅ LLM Client connected: {self.model_name}")
        except ImportError:
            logger.error("❌ Ollama not installed")
            self.client = None

    def generate(self, prompt: str, system_prompt: str = "You are Alfred, a capable autonomous AI agent.", stream: bool = False):
        """Generation with optional streaming."""
        if not self.client:
            return "Error: LLM not connected"
        
        try:
            if stream:
                return self._stream_generate(prompt, system_prompt)
            
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"LLM Generation failed: {e}")
            return f"Error: {e}"

    def _stream_generate(self, prompt: str, system_prompt: str) -> Generator[str, None, None]:
        """Internal streaming generator."""
        try:
            stream = self.client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                stream=True
            )
            for chunk in stream:
                yield chunk['message']['content']
        except Exception as e:
            yield f"Error: {e}"

    def chat_stream(self, messages: List[Dict]) -> Generator[str, None, None]:
        """Stream response for conversation."""
        if not self.client:
            yield "LLM Offline"
            return

        try:
            stream = self.client.chat(
                model=self.model_name,
                messages=messages,
                stream=True
            )
            for chunk in stream:
                yield chunk['message']['content']
        except Exception as e:
            yield f"Error: {e}"
