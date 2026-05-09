"""Tests for agents/hermes_commands.py"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.hermes_agent import HermesMessage
from agents.hermes_commands import HermesCommandRouter


def _msg(text: str, user_id: str = "u1", conv_id: str = "c1") -> HermesMessage:
    return HermesMessage(
        conversation_id=conv_id, user_id=user_id, text=text,
        platform="telegram", received_at=time.time(), is_dm=True,
    )


def _router(trusted_ids=("trusted-1",)):
    stark = MagicMock()
    stark.predict = MagicMock(return_value={"response": "result"})
    stark.get_status = MagicMock(return_value={"status": "ok", "model": "qwen3"})
    with patch("agents.hermes_commands.HERMES_TRUSTED_USER_IDS", trusted_ids):
        router = HermesCommandRouter(stark=stark)
    router._stark = stark
    return router, stark


class TestAuthGuard:
    @pytest.mark.asyncio
    async def test_untrusted_user_denied_for_run(self):
        router, _ = _router(trusted_ids=("trusted-1",))
        reply = await router.dispatch(_msg("/run print('x')", user_id="hacker"))
        assert "permission" in reply.lower()

    @pytest.mark.asyncio
    async def test_untrusted_user_denied_for_file(self):
        router, _ = _router(trusted_ids=("trusted-1",))
        reply = await router.dispatch(_msg("/file /etc/passwd", user_id="bad"))
        assert "permission" in reply.lower()

    @pytest.mark.asyncio
    async def test_untrusted_user_denied_for_recall(self):
        router, _ = _router(trusted_ids=("trusted-1",))
        reply = await router.dispatch(_msg("/recall secrets", user_id="bad"))
        assert "permission" in reply.lower()

    @pytest.mark.asyncio
    async def test_empty_trusted_list_denies_all(self):
        router, _ = _router(trusted_ids=())
        reply = await router.dispatch(_msg("/run x", user_id="anyone"))
        assert "permission" in reply.lower()


class TestCommandDispatch:
    @pytest.mark.asyncio
    async def test_run_calls_predict(self):
        router, stark = _router()
        with patch("agents.hermes_commands.HERMES_TRUSTED_USER_IDS", ("trusted-1",)):
            router._stark = stark
            reply = await router.dispatch(_msg("/run print('hi')", user_id="trusted-1"))
        stark.predict.assert_called_once()
        assert "result" in reply

    @pytest.mark.asyncio
    async def test_status_returns_data_for_any_user(self):
        router, stark = _router()
        reply = await router.dispatch(_msg("/status", user_id="anonymous"))
        assert "ok" in reply.lower() or "stark" in reply.lower()

    @pytest.mark.asyncio
    async def test_voice_on_enables_flag(self):
        router, _ = _router()
        await router.dispatch(_msg("/voice on", conv_id="c-voice"))
        assert router.voice_enabled("c-voice") is True

    @pytest.mark.asyncio
    async def test_voice_off_disables_flag(self):
        router, _ = _router()
        await router.dispatch(_msg("/voice on", conv_id="c2"))
        await router.dispatch(_msg("/voice off", conv_id="c2"))
        assert router.voice_enabled("c2") is False

    @pytest.mark.asyncio
    async def test_unknown_command_returns_hint(self):
        router, _ = _router()
        reply = await router.dispatch(_msg("/doesnotexist"))
        assert "unknown" in reply.lower() or "status" in reply.lower()

    @pytest.mark.asyncio
    async def test_run_without_args_shows_usage(self):
        stark = MagicMock()
        stark.predict = MagicMock(return_value={"response": "result"})
        stark.get_status = MagicMock(return_value={"status": "ok"})
        with patch("agents.hermes_commands.HERMES_TRUSTED_USER_IDS", ("u1",)):
            router = HermesCommandRouter(stark=stark)
            reply = await router.dispatch(_msg("/run", user_id="u1"))
        assert "usage" in reply.lower()
        stark.predict.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_slash_returns_unknown(self):
        router, _ = _router()
        reply = await router.dispatch(_msg("plain text message"))
        assert "unknown" in reply.lower()
