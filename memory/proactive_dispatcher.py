"""
Proactive Dispatcher
=====================
Decides WHEN to push an unprompted Hermes message and routes it.
Called by reflection_loop.py after each reflection completes.

Gate logic (all must pass):
  1. HERMES_ENABLED and proactive channels configured
  2. appraisal goal_relevance >= HERMES_PROACTIVE_GOAL_THRESHOLD
  3. appraisal novelty >= HERMES_PROACTIVE_NOVELTY_THRESHOLD
  4. cooldown: last send was > HERMES_PROACTIVE_COOLDOWN_SEC ago
  5. Not in quiet hours (if configured)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from core.constants import (
    HERMES_ENABLED,
    HERMES_PROACTIVE_CHANNELS,
    HERMES_PROACTIVE_COOLDOWN_SEC,
    HERMES_PROACTIVE_GOAL_THRESHOLD,
    HERMES_PROACTIVE_NOVELTY_THRESHOLD,
)
from memory.proactive_templates import format_for_chat, from_diary_entry

logger = logging.getLogger(__name__)


class ProactiveDispatcher:
    """
    Evaluates diary entries against appraisal thresholds and pushes
    proactive messages to designated Hermes channels when warranted.

    Args:
        hermes_client: object with async messages_send(channel_id, text).
        quiet_hours: optional (start_hour, end_hour) in 24h local time.
    """

    def __init__(
        self,
        hermes_client: Any,
        quiet_hours: tuple[int, int] | None = None,
    ) -> None:
        self._hermes = hermes_client
        self._quiet_hours = quiet_hours  # e.g. (23, 7) = 11pm–7am
        self._last_send: dict[str, float] = {}  # channel_id → timestamp

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def on_reflection_complete(self, diary_entry: dict[str, Any]) -> None:
        """
        Called by reflection_loop after each diary write.
        Evaluates thresholds and dispatches if all gates pass.
        """
        if not HERMES_ENABLED:
            return
        if not HERMES_PROACTIVE_CHANNELS:
            return

        emotion = diary_entry.get("emotion_vector") or {}
        goal_relevance = float(emotion.get("goal_relevance") or 0.0)
        novelty = float(emotion.get("novelty") or 0.0)

        if goal_relevance < HERMES_PROACTIVE_GOAL_THRESHOLD:
            logger.debug(
                "Proactive gate: goal_relevance %.2f < %.2f — skip",
                goal_relevance,
                HERMES_PROACTIVE_GOAL_THRESHOLD,
            )
            return
        if novelty < HERMES_PROACTIVE_NOVELTY_THRESHOLD:
            logger.debug(
                "Proactive gate: novelty %.2f < %.2f — skip",
                novelty,
                HERMES_PROACTIVE_NOVELTY_THRESHOLD,
            )
            return

        payload = from_diary_entry(diary_entry)
        if payload is None:
            return

        message = format_for_chat(payload)

        for channel_id in HERMES_PROACTIVE_CHANNELS:
            await self._maybe_send(channel_id, message)

    async def push_daily_summary(
        self, channel_id: str, promoted: int, conflicts: int, top_insight: str = ""
    ) -> None:
        """Called by consolidation.py after nightly run."""
        if not HERMES_ENABLED:
            return
        from memory.proactive_templates import format_for_chat, render_daily_summary
        payload = render_daily_summary(promoted, conflicts, top_insight)
        await self._maybe_send(channel_id, format_for_chat(payload), bypass_cooldown=True)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _maybe_send(
        self, channel_id: str, message: str, bypass_cooldown: bool = False
    ) -> None:
        if not bypass_cooldown and not self._cooldown_ok(channel_id):
            logger.debug("Proactive suppressed by cooldown for %s", channel_id)
            return
        if self._in_quiet_hours():
            logger.debug("Proactive suppressed by quiet hours")
            return
        try:
            await self._hermes.messages_send(channel_id, message)
            self._last_send[channel_id] = time.time()
            logger.info("Proactive push → %s", channel_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Proactive send failed to %s: %s", channel_id, exc)

    def _cooldown_ok(self, channel_id: str) -> bool:
        last = self._last_send.get(channel_id, 0.0)
        return (time.time() - last) >= HERMES_PROACTIVE_COOLDOWN_SEC

    def _in_quiet_hours(self) -> bool:
        if self._quiet_hours is None:
            return False
        import datetime
        now_hour = datetime.datetime.now().hour
        start, end = self._quiet_hours
        if start <= end:
            return start <= now_hour < end
        # wraps midnight e.g. (23, 7)
        return now_hour >= start or now_hour < end
