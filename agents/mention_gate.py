"""
Mention Gate
============
Cheap classifier that decides whether a message is addressed to STARK
or is an incidental mention in a group chat.

Cascade (cheapest check first):
  1. DM / 1:1 conversation → always addressed
  2. Explicit "@stark" prefix or "/" slash command → addressed
  3. Reply-to-bot message → addressed
  4. Fall through to lightweight LLM classifier (fast:latest / qwen3:8b)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from core.constants import (
    HERMES_MENTION_GATE_MODEL,
    HERMES_MENTION_GATE_THRESHOLD,
)

if TYPE_CHECKING:
    from agents.hermes_agent import HermesMessage

logger = logging.getLogger(__name__)

_GATE_PROMPT = (
    "You are a message router. Decide if the following message is DIRECTLY addressed "
    "to an AI assistant named STARK (score ≥ 0.6 → True) or is only mentioning it "
    "incidentally (score < 0.6 → False).\n"
    "Respond with a single float between 0 and 1, nothing else.\n\n"
    "Message: {text}"
)

_BOT_NAMES = ("stark", "@stark", "hey stark", "ok stark")


class MentionGate:
    """
    Determines whether an inbound HermesMessage is actually addressed to STARK.

    Args:
        ollama_client: object with .generate(model, prompt) → {"response": str}
                       Pass None to skip LLM fallback (treat unknown = addressed).
    """

    def __init__(self, ollama_client: Any | None = None) -> None:
        self._ollama = ollama_client

    async def is_addressed(self, msg: "HermesMessage") -> bool:
        """
        Return True if this message should be forwarded to STARK predict().
        Fast-path rules are checked first; LLM is only called as last resort.
        """
        # Rule 1: DMs are always addressed
        if msg.is_dm:
            return True

        # Rule 2: Explicit bot mention flag from Hermes metadata
        if msg.bot_mentioned:
            return True

        # Rule 3: Reply-to-bot flag
        if msg.reply_to_bot:
            return True

        # Rule 4: Slash command prefix
        if msg.text.strip().startswith("/"):
            return True

        # Rule 5: Case-insensitive name prefix
        lower = msg.text.lower().strip()
        if any(lower.startswith(name) for name in _BOT_NAMES):
            return True

        # Rule 6: LLM classifier (expensive — only reached in group chats)
        if self._ollama is None:
            # Without LLM fallback, default to addressed so nothing is silently dropped
            logger.debug("MentionGate: no LLM client, defaulting to addressed=True")
            return True

        return await self._llm_classify(msg.text)

    async def _llm_classify(self, text: str) -> bool:
        try:
            prompt = _GATE_PROMPT.format(text=text[:500])
            response = await self._ollama.generate(HERMES_MENTION_GATE_MODEL, prompt)
            raw = (response.get("response") or "").strip()
            score = float(raw)
            result = score >= HERMES_MENTION_GATE_THRESHOLD
            logger.debug("MentionGate LLM score=%.2f → %s", score, result)
            return result
        except Exception as exc:  # noqa: BLE001
            logger.warning("MentionGate LLM error: %s — defaulting addressed=True", exc)
            return True  # fail open: don't silently drop messages
