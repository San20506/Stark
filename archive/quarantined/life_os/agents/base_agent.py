"""
Life OS Base Agent
==================
Shared Ollama HTTP client and prompt builder for all life_os agents.

This is distinct from ``agents/base_agent.py`` (the STARK orchestrator base).
This class is a thin, synchronous Ollama caller designed for the deterministic
linear flows used by the life_os module.
"""
import json
import logging
from typing import Any

import requests

from core.constants import LIFE_OS_MODEL, OLLAMA_BASE_URL, REQUEST_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

_CHAT_ENDPOINT: str = f"{OLLAMA_BASE_URL}/api/chat"


class LifeOsBaseAgent:
    """
    Thin wrapper around the Ollama /api/chat endpoint.

    Provides prompt building and error-safe inference for all life_os agents.
    Never raises — returns an error string on failure (R4: inference path never crashes).
    """

    def __init__(
        self,
        model: str = LIFE_OS_MODEL,
        timeout: int = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        """
        Args:
            model: Ollama model tag to use for inference.
            timeout: HTTP request timeout in seconds.
        """
        self._model = model
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def call(self, system: str, user: str) -> str:
        """
        Send a chat request to Ollama and return the assistant reply.

        Args:
            system: System prompt string.
            user: User turn content.

        Returns:
            Assistant reply text, or an error string prefixed with
            ``[life_os error: ...]`` if Ollama is unavailable.
        """
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        try:
            resp = requests.post(_CHAT_ENDPOINT, json=payload, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()
        except requests.RequestException as exc:
            logger.error("Ollama request failed: %s", exc)
            return f"[life_os error: Ollama unavailable — {exc}]"
        except (KeyError, ValueError) as exc:
            logger.error("Ollama response parse error: %s", exc)
            return "[life_os error: unexpected Ollama response format]"

    def call_json(self, system: str, user: str) -> dict[str, Any]:
        """
        Like ``call()`` but expects a JSON-formatted assistant response.

        Strips markdown code fences if present.  Returns ``{"raw_response": ...}``
        on JSON parse failure so callers always receive a dict.

        Args:
            system: System prompt string.
            user: User turn content.

        Returns:
            Parsed JSON dict, or ``{"raw_response": <text>}`` on failure.
        """
        raw = self.call(system, user)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            inner = lines[1:-1] if len(lines) > 2 else lines[1:]
            cleaned = "\n".join(inner).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Non-JSON response from Ollama (%.200s)", raw)
            return {"raw_response": raw}
