"""Tests for agents/mention_gate.py"""

import time
import pytest
from unittest.mock import AsyncMock

from agents.hermes_agent import HermesMessage
from agents.mention_gate import MentionGate


def _msg(**kwargs) -> HermesMessage:
    defaults = dict(
        conversation_id="c1", user_id="u1", text="hello",
        platform="telegram", received_at=time.time(),
    )
    defaults.update(kwargs)
    return HermesMessage(**defaults)


class TestMentionGateRules:
    @pytest.mark.asyncio
    async def test_dm_always_addressed(self):
        gate = MentionGate()
        assert await gate.is_addressed(_msg(is_dm=True, text="anything"))

    @pytest.mark.asyncio
    async def test_bot_mentioned_flag(self):
        gate = MentionGate()
        assert await gate.is_addressed(_msg(bot_mentioned=True))

    @pytest.mark.asyncio
    async def test_reply_to_bot(self):
        gate = MentionGate()
        assert await gate.is_addressed(_msg(reply_to_bot=True))

    @pytest.mark.asyncio
    async def test_slash_prefix(self):
        gate = MentionGate()
        assert await gate.is_addressed(_msg(text="/status"))
        assert await gate.is_addressed(_msg(text="/run print('hi')"))

    @pytest.mark.asyncio
    async def test_stark_name_prefix(self):
        gate = MentionGate()
        assert await gate.is_addressed(_msg(text="stark what time is it"))
        assert await gate.is_addressed(_msg(text="@stark help"))
        assert await gate.is_addressed(_msg(text="hey stark!"))

    @pytest.mark.asyncio
    async def test_name_prefix_case_insensitive(self):
        gate = MentionGate()
        assert await gate.is_addressed(_msg(text="STARK do something"))

    @pytest.mark.asyncio
    async def test_incidental_mention_no_llm_defaults_true(self):
        gate = MentionGate(ollama_client=None)
        # Without LLM, fail-open: unknown group message is treated as addressed
        result = await gate.is_addressed(_msg(text="I heard that STARK is good"))
        assert result is True


class TestMentionGateLLMFallback:
    @pytest.mark.asyncio
    async def test_llm_high_score_returns_true(self):
        ollama = AsyncMock()
        ollama.generate = AsyncMock(return_value={"response": "0.85"})
        gate = MentionGate(ollama_client=ollama)
        result = await gate.is_addressed(_msg(text="some group chat text"))
        assert result is True
        ollama.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_low_score_returns_false(self):
        ollama = AsyncMock()
        ollama.generate = AsyncMock(return_value={"response": "0.2"})
        gate = MentionGate(ollama_client=ollama)
        result = await gate.is_addressed(_msg(text="random chatter"))
        assert result is False

    @pytest.mark.asyncio
    async def test_llm_error_defaults_to_addressed(self):
        ollama = AsyncMock()
        ollama.generate = AsyncMock(side_effect=RuntimeError("network error"))
        gate = MentionGate(ollama_client=ollama)
        result = await gate.is_addressed(_msg(text="might be for the bot"))
        assert result is True

    @pytest.mark.asyncio
    async def test_llm_not_called_for_dm(self):
        ollama = AsyncMock()
        gate = MentionGate(ollama_client=ollama)
        await gate.is_addressed(_msg(is_dm=True))
        ollama.generate.assert_not_called()
