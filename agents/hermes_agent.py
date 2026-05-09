"""
Hermes Bridge Agent
===================
Bidirectional adapter between the Hermes MCP messaging bridge and STARK's
predict() loop. Hermes is a transport only — all cognition stays in core/main.py.

Supports: Telegram, Discord, Slack, WhatsApp, Signal, Matrix (whatever Hermes exposes).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from core.constants import (
    HERMES_ENABLED,
    HERMES_MAX_EVENTS_PER_CYCLE,
    HERMES_MAX_REPLY_TOKENS,
    HERMES_POLL_TIMEOUT_SEC,
    HERMES_RECONNECT_BACKOFF_MAX_SEC,
    HERMES_REPLY_CONCURRENCY_PER_CHANNEL,
    HERMES_REPLY_TIMEOUT_SEC,
    HERMES_VOICE_REPLY_DEFAULT,
)

if TYPE_CHECKING:
    from agents.mention_gate import MentionGate
    from agents.hermes_commands import HermesCommandRouter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HermesMessage:
    """Normalised inbound message from any Hermes platform."""

    conversation_id: str
    user_id: str
    text: str
    platform: str           # "telegram" | "discord" | "matrix" | etc.
    received_at: float
    is_voice: bool = False
    attachment_ids: tuple[str, ...] = field(default_factory=tuple)
    is_dm: bool = False
    bot_mentioned: bool = False
    reply_to_bot: bool = False


def parse_hermes_event(event: dict[str, Any]) -> HermesMessage | None:
    """
    Convert a raw Hermes MCP event dict into a HermesMessage.
    Returns None if the event is not a parseable message.
    """
    try:
        msg_type = event.get("type", "")
        if msg_type not in ("message", "message_created"):
            return None

        payload = event.get("message") or event.get("data") or event
        text = payload.get("content") or payload.get("text") or ""
        conversation_id = (
            payload.get("conversation_id")
            or payload.get("channel_id")
            or payload.get("chat_id")
            or ""
        )
        user_id = (
            payload.get("sender_id")
            or payload.get("user_id")
            or payload.get("from", {}).get("id", "")
            or ""
        )
        platform = payload.get("platform") or event.get("platform") or "unknown"
        attachments = tuple(payload.get("attachment_ids") or [])
        is_voice = bool(payload.get("is_voice") or payload.get("voice"))
        is_dm = bool(payload.get("is_dm") or payload.get("direct_message"))
        bot_mentioned = bool(payload.get("bot_mentioned") or payload.get("mentioned"))
        reply_to_bot = bool(payload.get("reply_to_bot") or payload.get("is_reply_to_bot"))

        if not conversation_id:
            return None

        return HermesMessage(
            conversation_id=conversation_id,
            user_id=user_id,
            text=text,
            platform=platform,
            received_at=time.time(),
            is_voice=is_voice,
            attachment_ids=attachments,
            is_dm=is_dm,
            bot_mentioned=bot_mentioned,
            reply_to_bot=reply_to_bot,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse Hermes event: %s — %s", event, exc)
        return None


class HermesAgent:
    """
    Main Hermes ↔ STARK bridge.

    Usage (from core/main.py when HERMES_ENABLED):
        agent = HermesAgent(stark=get_stark(), hermes_client=HermesMCPClient())
        asyncio.create_task(agent.run())
    """

    def __init__(
        self,
        stark: Any,
        hermes_client: Any,
        mention_gate: "MentionGate | None" = None,
        command_router: "HermesCommandRouter | None" = None,
    ) -> None:
        self._stark = stark
        self._hermes = hermes_client
        self._mention_gate = mention_gate
        self._command_router = command_router
        self._running = False
        self._channel_semaphores: dict[str, asyncio.Semaphore] = {}
        self._backoff_sec = 1.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Long-running inbound event loop. Call as asyncio task."""
        if not HERMES_ENABLED:
            logger.info("HermesAgent: HERMES_ENABLED=False — not starting")
            return

        self._running = True
        logger.info("HermesAgent started")

        while self._running:
            try:
                await self._poll_cycle()
                self._backoff_sec = 1.0  # reset on success
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                logger.error("HermesAgent poll error: %s", exc, exc_info=True)
                await asyncio.sleep(min(self._backoff_sec, HERMES_RECONNECT_BACKOFF_MAX_SEC))
                self._backoff_sec = min(self._backoff_sec * 2, HERMES_RECONNECT_BACKOFF_MAX_SEC)

        logger.info("HermesAgent stopped")

    def stop(self) -> None:
        self._running = False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _poll_cycle(self) -> None:
        """Fetch one batch of events and handle each."""
        events = await self._hermes.events_wait(timeout=HERMES_POLL_TIMEOUT_SEC)
        if not events:
            return

        tasks = []
        for raw_event in events[:HERMES_MAX_EVENTS_PER_CYCLE]:
            msg = parse_hermes_event(raw_event)
            if msg is None:
                continue
            tasks.append(asyncio.create_task(self._handle_message(msg)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_message(self, msg: HermesMessage) -> None:
        """Process one inbound message end-to-end."""
        # Mention-gate: drop incidental group-chat noise
        if self._mention_gate is not None:
            addressed = await self._mention_gate.is_addressed(msg)
            if not addressed:
                logger.debug("MentionGate dropped message from %s", msg.conversation_id)
                return

        # Slash command dispatch
        if self._command_router is not None and msg.text.startswith("/"):
            response = await self._command_router.dispatch(msg)
        else:
            response = await self._predict(msg)

        if response:
            await self._send_reply(msg.conversation_id, response)

    async def _predict(self, msg: HermesMessage) -> str:
        """Route message through STARK predict(), handling voice transcription."""
        text = msg.text

        if msg.is_voice and msg.attachment_ids:
            text = await self._transcribe_voice(msg.attachment_ids[0])
            if not text:
                return "Sorry, I couldn't transcribe that voice message."

        try:
            # Thread continuity: use conversation_id as thread_id
            context: dict[str, Any] = {
                "thread_id": msg.conversation_id,
                "platform": msg.platform,
                "user_id": msg.user_id,
                "max_tokens": HERMES_MAX_REPLY_TOKENS,
            }
            result = await asyncio.wait_for(
                self._run_predict(text, context),
                timeout=HERMES_REPLY_TIMEOUT_SEC,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning("predict() timed out for thread %s", msg.conversation_id)
            return "Sorry, that took too long. Try a shorter question."
        except Exception as exc:  # noqa: BLE001
            logger.error("predict() error for %s: %s", msg.conversation_id, exc)
            return "Something went wrong. Please try again."

    async def _run_predict(self, text: str, context: dict[str, Any]) -> str:
        """Async wrapper around STARK's (potentially sync) predict()."""
        loop = asyncio.get_event_loop()
        if inspect.iscoroutinefunction(self._stark.predict):
            result = await self._stark.predict(text, context=context)
        else:
            result = await loop.run_in_executor(
                None, lambda: self._stark.predict(text, context=context)
            )
        if isinstance(result, dict):
            return result.get("response") or result.get("text") or str(result)
        return str(result)

    async def _transcribe_voice(self, attachment_id: str) -> str:
        """Fetch voice attachment and transcribe via STARK's STT module."""
        try:
            audio_data = await self._hermes.attachments_fetch(attachment_id)
            # Delegate to STARK voice if available
            if hasattr(self._stark, "transcribe"):
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, lambda: self._stark.transcribe(audio_data)
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Voice transcription failed: %s", exc)
        return ""

    async def _send_reply(self, conversation_id: str, text: str) -> None:
        """Send reply with per-channel concurrency limit (R3 safety)."""
        sem = self._channel_semaphores.setdefault(
            conversation_id,
            asyncio.Semaphore(HERMES_REPLY_CONCURRENCY_PER_CHANNEL),
        )
        async with sem:
            try:
                await self._hermes.messages_send(conversation_id, text)
                logger.debug("Sent reply to %s (%d chars)", conversation_id, len(text))
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to send reply to %s: %s", conversation_id, exc)
