"""
End-to-end integration test for the Hermes bridge.
Uses mock Hermes client and STARK to verify the full inbound→predict→reply loop,
mention-gate filtering, and proactive dispatch.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from agents.hermes_agent import HermesAgent, HermesMessage, parse_hermes_event
from agents.mention_gate import MentionGate
from agents.hermes_commands import HermesCommandRouter
from memory.proactive_dispatcher import ProactiveDispatcher


def _make_event(conv_id: str, text: str, user_id: str = "u1",
                is_dm: bool = True) -> dict:
    return {
        "type": "message",
        "message": {
            "conversation_id": conv_id,
            "content": text,
            "sender_id": user_id,
            "platform": "telegram",
            "is_dm": is_dm,
        },
    }


class TestFullLoop:
    @pytest.mark.asyncio
    async def test_five_messages_from_user_a(self):
        """5 DM messages → 5 predict calls → 5 replies."""
        hermes = AsyncMock()
        hermes.messages_send = AsyncMock()
        hermes.events_wait = AsyncMock(return_value=[
            _make_event("dm-a", f"message {i}", user_id="user-a")
            for i in range(5)
        ])

        stark = MagicMock()
        stark.predict = MagicMock(return_value={"response": "reply"})

        mention_gate = MentionGate(ollama_client=None)

        with patch("agents.hermes_agent.HERMES_ENABLED", True):
            agent = HermesAgent(stark=stark, hermes_client=hermes,
                                mention_gate=mention_gate)
            await agent._poll_cycle()

        assert stark.predict.call_count == 5
        assert hermes.messages_send.call_count == 5

    @pytest.mark.asyncio
    async def test_three_messages_from_user_b(self):
        hermes = AsyncMock()
        hermes.messages_send = AsyncMock()
        hermes.events_wait = AsyncMock(return_value=[
            _make_event("dm-b", f"hi {i}", user_id="user-b")
            for i in range(3)
        ])
        stark = MagicMock()
        stark.predict = MagicMock(return_value={"response": "ok"})
        mention_gate = MentionGate(ollama_client=None)

        with patch("agents.hermes_agent.HERMES_ENABLED", True):
            agent = HermesAgent(stark=stark, hermes_client=hermes,
                                mention_gate=mention_gate)
            await agent._poll_cycle()

        assert stark.predict.call_count == 3

    @pytest.mark.asyncio
    async def test_group_incidental_mention_dropped_by_gate(self):
        """Group chat message without @stark prefix → dropped by mention-gate."""
        hermes = AsyncMock()
        hermes.messages_send = AsyncMock()
        incidental = {
            "type": "message",
            "message": {
                "conversation_id": "group-1",
                "content": "I heard STARK is a good project",
                "sender_id": "u3",
                "platform": "telegram",
                "is_dm": False,
                "bot_mentioned": False,
            },
        }
        hermes.events_wait = AsyncMock(return_value=[incidental])
        stark = MagicMock()
        # LLM gate returns low score → not addressed
        ollama = AsyncMock()
        ollama.generate = AsyncMock(return_value={"response": "0.1"})
        mention_gate = MentionGate(ollama_client=ollama)

        with patch("agents.hermes_agent.HERMES_ENABLED", True):
            agent = HermesAgent(stark=stark, hermes_client=hermes,
                                mention_gate=mention_gate)
            await agent._poll_cycle()

        stark.predict.assert_not_called()
        hermes.messages_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_group_explicit_mention_handled(self):
        """Group chat with @stark prefix → handled."""
        hermes = AsyncMock()
        hermes.messages_send = AsyncMock()
        addressed = {
            "type": "message",
            "message": {
                "conversation_id": "group-2",
                "content": "@stark what is 2+2?",
                "sender_id": "u4",
                "platform": "telegram",
                "is_dm": False,
                "bot_mentioned": True,
            },
        }
        hermes.events_wait = AsyncMock(return_value=[addressed])
        stark = MagicMock()
        stark.predict = MagicMock(return_value={"response": "4"})
        mention_gate = MentionGate(ollama_client=None)

        with patch("agents.hermes_agent.HERMES_ENABLED", True):
            agent = HermesAgent(stark=stark, hermes_client=hermes,
                                mention_gate=mention_gate)
            await agent._poll_cycle()

        stark.predict.assert_called_once()
        hermes.messages_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_proactive_dispatch_on_reflection(self):
        """Reflection completing with high goal_relevance → message pushed."""
        hermes = AsyncMock()
        hermes.messages_send = AsyncMock()

        diary = {
            "emotion_vector": {"goal_relevance": 0.95, "novelty": 0.9},
            "insights": ["You consistently study best in mornings."],
            "tags": ["habits"],
        }

        with (
            patch("memory.proactive_dispatcher.HERMES_ENABLED", True),
            patch("memory.proactive_dispatcher.HERMES_PROACTIVE_CHANNELS", ("daily-ch",)),
        ):
            dispatcher = ProactiveDispatcher(hermes_client=hermes)
            await dispatcher.on_reflection_complete(diary)

        hermes.messages_send.assert_called_once()
        text = hermes.messages_send.call_args[0][1]
        assert "morning" in text.lower() or "insight" in text.lower()
