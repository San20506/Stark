"""Tests for memory/channel_index.py"""

import tempfile
from pathlib import Path

import pytest

from memory.channel_index import ChannelIndex


@pytest.fixture
def idx(tmp_path):
    return ChannelIndex(db_path=tmp_path / "channel_index.db")


class TestGetOrCreateThread:
    def test_new_conversation_gets_thread_id(self, idx):
        tid = idx.get_or_create_thread("conv-1", platform="telegram")
        assert "conv-1" in tid

    def test_same_conversation_id_returns_same_thread(self, idx):
        t1 = idx.get_or_create_thread("conv-2", platform="telegram")
        t2 = idx.get_or_create_thread("conv-2", platform="telegram")
        assert t1 == t2

    def test_different_conversations_get_different_threads(self, idx):
        t1 = idx.get_or_create_thread("conv-A")
        t2 = idx.get_or_create_thread("conv-B")
        assert t1 != t2

    def test_thread_id_encodes_platform(self, idx):
        tid = idx.get_or_create_thread("c1", platform="discord")
        assert "discord" in tid

    def test_get_thread_returns_none_for_unknown(self, idx):
        assert idx.get_thread("nonexistent") is None

    def test_get_thread_returns_existing(self, idx):
        tid = idx.get_or_create_thread("c99", platform="matrix")
        assert idx.get_thread("c99") == tid


class TestPersonaAliases:
    def test_register_and_resolve_persona(self, idx):
        idx.register_persona_alias("sandy", "telegram", "tg-999")
        tid = idx.get_or_create_thread("conv-x", platform="telegram", user_id="tg-999")
        persona = idx.get_persona("conv-x")
        assert persona == "sandy"

    def test_unknown_user_persona_is_user_id(self, idx):
        idx.get_or_create_thread("conv-y", platform="discord", user_id="dc-123")
        persona = idx.get_persona("conv-y")
        assert persona == "dc-123"

    def test_empty_user_id_gives_empty_persona(self, idx):
        idx.get_or_create_thread("conv-z", platform="telegram", user_id="")
        persona = idx.get_persona("conv-z")
        assert persona == ""


class TestAllEntries:
    def test_all_entries_returns_created(self, idx):
        idx.get_or_create_thread("c1", platform="telegram")
        idx.get_or_create_thread("c2", platform="discord")
        entries = idx.all_entries()
        ids = {e.conversation_id for e in entries}
        assert "c1" in ids
        assert "c2" in ids
