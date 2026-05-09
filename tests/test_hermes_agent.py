"""Tests for agents/hermes_agent.py"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.hermes_agent import HermesAgent, HermesMessage, parse_hermes_event


# ---------------------------------------------------------------------------
# parse_hermes_event
# ---------------------------------------------------------------------------

class TestParseHermesEvent:
    def test_parses_standard_message_event(self):
        event = {
            "type": "message",
            "message": {
                "conversation_id": "conv-123",
                "content": "Hello STARK",
                "sender_id": "user-42",
                "platform": "telegram",
            },
        }
        msg = parse_hermes_event(event)
        assert msg is not None
        assert msg.conversation_id == "conv-123"
        assert msg.text == "Hello STARK"
        assert msg.user_id == "user-42"
        assert msg.platform == "telegram"

    def test_parses_message_created_type(self):
        event = {
            "type": "message_created",
            "data": {
                "conversation_id": "conv-456",
                "text": "hey",
                "user_id": "u1",
            },
        }
        msg = parse_hermes_event(event)
        assert msg is not None
        assert msg.conversation_id == "conv-456"

    def test_returns_none_for_non_message_type(self):
        assert parse_hermes_event({"type": "presence_update"}) is None

    def test_returns_none_when_no_conversation_id(self):
        event = {"type": "message", "message": {"content": "hello"}}
        assert parse_hermes_event(event) is None

    def test_detects_voice_flag(self):
        event = {
            "type": "message",
            "message": {
                "conversation_id": "c1",
                "is_voice": True,
                "attachment_ids": ["att-1"],
            },
        }
        msg = parse_hermes_event(event)
        assert msg.is_voice is True
        assert "att-1" in msg.attachment_ids

    def test_detects_dm_flag(self):
        event = {
            "type": "message",
            "message": {
                "conversation_id": "dm-1",
                "is_dm": True,
            },
        }
        msg = parse_hermes_event(event)
        assert msg.is_dm is True

    def test_gracefully_handles_malformed_event(self):
        assert parse_hermes_event({"type": "message", "message": None}) is None
        assert parse_hermes_event({}) is None


# ---------------------------------------------------------------------------
# HermesAgent — startup
# ---------------------------------------------------------------------------

class TestHermesAgentStartup:
    def _make_agent(self, enabled=True):
        hermes = AsyncMock()
        hermes.events_wait = AsyncMock(return_value=[])
        stark = MagicMock()
        stark.predict = MagicMock(return_value={"response": "ok"})
        with patch("agents.hermes_agent.HERMES_ENABLED", enabled):
            agent = HermesAgent(stark=stark, hermes_client=hermes)
        return agent, stark, hermes

    def test_stop_before_run_is_safe(self):
        agent, _, _ = self._make_agent()
        agent.stop()  # should not raise

    @pytest.mark.asyncio
    async def test_does_not_start_when_flag_disabled(self):
        hermes = AsyncMock()
        stark = MagicMock()
        with patch("agents.hermes_agent.HERMES_ENABLED", False):
            agent = HermesAgent(stark=stark, hermes_client=hermes)
            await agent.run()  # should return immediately
        hermes.events_wait.assert_not_called()


# ---------------------------------------------------------------------------
# HermesAgent — reply round-trip
# ---------------------------------------------------------------------------

class TestHermesAgentReply:
    def _make_agent(self):
        hermes = AsyncMock()
        hermes.messages_send = AsyncMock()
        stark = MagicMock()
        stark.predict = MagicMock(return_value={"response": "pong"})
        mention_gate = AsyncMock()
        mention_gate.is_addressed = AsyncMock(return_value=True)
        with patch("agents.hermes_agent.HERMES_ENABLED", True):
            agent = HermesAgent(
                stark=stark,
                hermes_client=hermes,
                mention_gate=mention_gate,
            )
        return agent, stark, hermes

    @pytest.mark.asyncio
    async def test_predict_called_and_reply_sent(self):
        agent, stark, hermes = self._make_agent()
        msg = HermesMessage(
            conversation_id="c1",
            user_id="u1",
            text="ping",
            platform="telegram",
            received_at=time.time(),
            is_dm=True,
        )
        await agent._handle_message(msg)
        stark.predict.assert_called_once()
        hermes.messages_send.assert_called_once_with("c1", "pong")

    @pytest.mark.asyncio
    async def test_predict_failure_does_not_crash_loop(self):
        agent, stark, hermes = self._make_agent()
        stark.predict.side_effect = RuntimeError("boom")
        msg = HermesMessage(
            conversation_id="c1", user_id="u1", text="hi",
            platform="telegram", received_at=time.time(), is_dm=True,
        )
        # Should not raise
        await agent._handle_message(msg)
        hermes.messages_send.assert_called_once()
        reply = hermes.messages_send.call_args[0][1]
        assert "wrong" in reply.lower() or "sorry" in reply.lower()

    @pytest.mark.asyncio
    async def test_mention_gate_drop_prevents_predict(self):
        agent, stark, hermes = self._make_agent()
        agent._mention_gate.is_addressed = AsyncMock(return_value=False)
        msg = HermesMessage(
            conversation_id="c1", user_id="u1", text="incidental mention",
            platform="discord", received_at=time.time(),
        )
        await agent._handle_message(msg)
        stark.predict.assert_not_called()
        hermes.messages_send.assert_not_called()
