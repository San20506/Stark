"""
Hermes Slash Command Router
============================
Dispatches /slash commands received via Hermes to the appropriate STARK agent.
Untrusted users are rejected before any agent call occurs.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import TYPE_CHECKING, Any

from core.constants import HERMES_TRUSTED_USER_IDS

if TYPE_CHECKING:
    from agents.hermes_agent import HermesMessage

logger = logging.getLogger(__name__)

_DENY = "Sorry, you don't have permission to run commands."
_UNKNOWN = "Unknown command. Try /status or ask me naturally."


class HermesCommandRouter:
    """
    Parses /command [args] and dispatches to STARK capabilities.

    Registered commands:
        /run  <code>   — execute code via CodeAgent    (trusted only)
        /file <path>   — read file via FileAgent        (trusted only)
        /search <q>    — web search via WebAgent        (any)
        /recall <q>    — memory recall                  (trusted only)
        /status        — health snapshot               (any)
        /voice on|off  — toggle TTS replies per thread  (any)
    """

    def __init__(self, stark: Any, voice_state: dict[str, bool] | None = None) -> None:
        self._stark = stark
        # Mutable per-thread voice flag: conversation_id → bool
        self._voice_state: dict[str, bool] = voice_state if voice_state is not None else {}
        self._handlers = {
            "run": self._cmd_run,
            "file": self._cmd_file,
            "search": self._cmd_search,
            "recall": self._cmd_recall,
            "status": self._cmd_status,
            "voice": self._cmd_voice,
        }

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def dispatch(self, msg: "HermesMessage") -> str:
        """Parse and route a /command message. Always returns a string."""
        text = msg.text.strip()
        if not text.startswith("/"):
            return _UNKNOWN

        parts = text[1:].split(None, 1)
        name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handler = self._handlers.get(name)
        if handler is None:
            return _UNKNOWN

        return await handler(msg, args)

    def voice_enabled(self, conversation_id: str) -> bool:
        from core.constants import HERMES_VOICE_REPLY_DEFAULT
        return self._voice_state.get(conversation_id, HERMES_VOICE_REPLY_DEFAULT)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    async def _cmd_run(self, msg: "HermesMessage", args: str) -> str:
        if not self._is_trusted(msg.user_id):
            return _DENY
        if not args.strip():
            return "Usage: /run <code>"
        try:
            result = await self._call_agent("code", args)
            return f"```\n{result}\n```"
        except Exception as exc:
            logger.error("/run error: %s", exc)
            return f"Error running code: {exc}"

    async def _cmd_file(self, msg: "HermesMessage", args: str) -> str:
        if not self._is_trusted(msg.user_id):
            return _DENY
        path = args.strip()
        if not path:
            return "Usage: /file <path>"
        try:
            result = await self._call_agent("file", path)
            # Truncate long files in chat
            if len(result) > 2000:
                result = result[:2000] + "\n… (truncated)"
            return f"```\n{result}\n```"
        except Exception as exc:
            logger.error("/file error: %s", exc)
            return f"Error reading file: {exc}"

    async def _cmd_search(self, msg: "HermesMessage", args: str) -> str:
        query = args.strip()
        if not query:
            return "Usage: /search <query>"
        try:
            return await self._call_agent("web_search", query)
        except Exception as exc:
            logger.error("/search error: %s", exc)
            return f"Search failed: {exc}"

    async def _cmd_recall(self, msg: "HermesMessage", args: str) -> str:
        if not self._is_trusted(msg.user_id):
            return _DENY
        query = args.strip()
        if not query:
            return "Usage: /recall <query>"
        try:
            return await self._call_agent("memory_recall", query)
        except Exception as exc:
            logger.error("/recall error: %s", exc)
            return f"Recall failed: {exc}"

    async def _cmd_status(self, msg: "HermesMessage", args: str) -> str:
        try:
            if hasattr(self._stark, "get_status"):
                loop = asyncio.get_event_loop()
                status = await loop.run_in_executor(None, self._stark.get_status)
            else:
                status = {"status": "running"}
            lines = [f"{k}: {v}" for k, v in status.items()]
            return "STARK Status\n" + "\n".join(lines)
        except Exception as exc:
            logger.error("/status error: %s", exc)
            return f"Status unavailable: {exc}"

    async def _cmd_voice(self, msg: "HermesMessage", args: str) -> str:
        flag = args.strip().lower()
        if flag == "on":
            self._voice_state[msg.conversation_id] = True
            return "Voice replies enabled for this conversation."
        if flag == "off":
            self._voice_state[msg.conversation_id] = False
            return "Voice replies disabled."
        return "Usage: /voice on|off"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_trusted(self, user_id: str) -> bool:
        if not HERMES_TRUSTED_USER_IDS:
            return False
        return user_id in HERMES_TRUSTED_USER_IDS

    async def _call_agent(self, task_type: str, payload: str) -> str:
        """Delegate to STARK's predict() with a structured task context."""
        context = {"task_type": task_type, "hermes_command": True}
        loop = asyncio.get_event_loop()
        if inspect.iscoroutinefunction(self._stark.predict):
            result = await self._stark.predict(payload, context=context)
        else:
            result = await loop.run_in_executor(
                None, lambda: self._stark.predict(payload, context=context)
            )
        if isinstance(result, dict):
            return result.get("response") or result.get("text") or str(result)
        return str(result)
