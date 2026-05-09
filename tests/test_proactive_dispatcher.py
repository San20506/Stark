"""Tests for memory/proactive_dispatcher.py"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch

from memory.proactive_dispatcher import ProactiveDispatcher


def _hermes():
    h = AsyncMock()
    h.messages_send = AsyncMock()
    return h


def _diary(goal_relevance=0.9, novelty=0.8, insights=None):
    return {
        "emotion_vector": {
            "goal_relevance": goal_relevance,
            "novelty": novelty,
        },
        "insights": insights or ["interesting insight"],
        "tags": ["study"],
        "summary": "Today I learned something useful.",
    }


class TestProactiveGates:
    @pytest.mark.asyncio
    async def test_fires_when_thresholds_met(self):
        hermes = _hermes()
        with (
            patch("memory.proactive_dispatcher.HERMES_ENABLED", True),
            patch("memory.proactive_dispatcher.HERMES_PROACTIVE_CHANNELS", ("ch-1",)),
        ):
            d = ProactiveDispatcher(hermes_client=hermes)
            await d.on_reflection_complete(_diary(goal_relevance=0.9, novelty=0.8))
        hermes.messages_send.assert_called_once()
        args = hermes.messages_send.call_args[0]
        assert args[0] == "ch-1"
        assert len(args[1]) > 0

    @pytest.mark.asyncio
    async def test_skips_when_goal_below_threshold(self):
        hermes = _hermes()
        with (
            patch("memory.proactive_dispatcher.HERMES_ENABLED", True),
            patch("memory.proactive_dispatcher.HERMES_PROACTIVE_CHANNELS", ("ch-1",)),
        ):
            d = ProactiveDispatcher(hermes_client=hermes)
            await d.on_reflection_complete(_diary(goal_relevance=0.3, novelty=0.9))
        hermes.messages_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_novelty_below_threshold(self):
        hermes = _hermes()
        with (
            patch("memory.proactive_dispatcher.HERMES_ENABLED", True),
            patch("memory.proactive_dispatcher.HERMES_PROACTIVE_CHANNELS", ("ch-1",)),
        ):
            d = ProactiveDispatcher(hermes_client=hermes)
            await d.on_reflection_complete(_diary(goal_relevance=0.9, novelty=0.2))
        hermes.messages_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_hermes_disabled(self):
        hermes = _hermes()
        with (
            patch("memory.proactive_dispatcher.HERMES_ENABLED", False),
            patch("memory.proactive_dispatcher.HERMES_PROACTIVE_CHANNELS", ("ch-1",)),
        ):
            d = ProactiveDispatcher(hermes_client=hermes)
            await d.on_reflection_complete(_diary())
        hermes.messages_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_no_channels_configured(self):
        hermes = _hermes()
        with (
            patch("memory.proactive_dispatcher.HERMES_ENABLED", True),
            patch("memory.proactive_dispatcher.HERMES_PROACTIVE_CHANNELS", ()),
        ):
            d = ProactiveDispatcher(hermes_client=hermes)
            await d.on_reflection_complete(_diary())
        hermes.messages_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_cooldown_suppresses_back_to_back(self):
        hermes = _hermes()
        with (
            patch("memory.proactive_dispatcher.HERMES_ENABLED", True),
            patch("memory.proactive_dispatcher.HERMES_PROACTIVE_CHANNELS", ("ch-1",)),
            patch("memory.proactive_dispatcher.HERMES_PROACTIVE_COOLDOWN_SEC", 3600),
        ):
            d = ProactiveDispatcher(hermes_client=hermes)
            d._last_send["ch-1"] = time.time()  # fake recent send
            await d.on_reflection_complete(_diary())
        hermes.messages_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_cooldown_allows_after_elapsed(self):
        hermes = _hermes()
        with (
            patch("memory.proactive_dispatcher.HERMES_ENABLED", True),
            patch("memory.proactive_dispatcher.HERMES_PROACTIVE_CHANNELS", ("ch-1",)),
            patch("memory.proactive_dispatcher.HERMES_PROACTIVE_COOLDOWN_SEC", 10),
        ):
            d = ProactiveDispatcher(hermes_client=hermes)
            d._last_send["ch-1"] = time.time() - 20  # 20s ago, cooldown is 10s
            await d.on_reflection_complete(_diary())
        hermes.messages_send.assert_called_once()


class TestQuietHours:
    @pytest.mark.asyncio
    async def test_quiet_hours_block_send(self):
        hermes = _hermes()
        import datetime
        current_hour = datetime.datetime.now().hour
        # Quiet hours = all day
        quiet = (0, 23)
        with (
            patch("memory.proactive_dispatcher.HERMES_ENABLED", True),
            patch("memory.proactive_dispatcher.HERMES_PROACTIVE_CHANNELS", ("ch-1",)),
        ):
            d = ProactiveDispatcher(hermes_client=hermes, quiet_hours=quiet)
            await d.on_reflection_complete(_diary())
        hermes.messages_send.assert_not_called()


class TestDailySummaryPush:
    @pytest.mark.asyncio
    async def test_push_daily_summary(self):
        hermes = _hermes()
        with patch("memory.proactive_dispatcher.HERMES_ENABLED", True):
            d = ProactiveDispatcher(hermes_client=hermes)
            await d.push_daily_summary("ch-1", promoted=3, conflicts=1, top_insight="X")
        hermes.messages_send.assert_called_once()
        text = hermes.messages_send.call_args[0][1]
        assert "3" in text
        assert "X" in text
