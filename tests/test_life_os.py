"""
Tests for the life_os module — Phase 1 & 2.

Covers:
- ContextManager read/write/update_section
- store_episode writes correct schema fields
- MorningAgent prompt building (no Ollama required)
- EveningAgent log appending
- Voice hook error handling
"""
import json
import sqlite3
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modules.life_os.context_manager import ContextManager, store_episode


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture()
def tmp_context_dir(tmp_path: Path) -> Path:
    return tmp_path / "context"


@pytest.fixture()
def ctx_manager(tmp_context_dir: Path) -> ContextManager:
    return ContextManager(context_dir=tmp_context_dir)


@pytest.fixture()
def populated_ctx(ctx_manager: ContextManager) -> ContextManager:
    """Context manager with all 5 files pre-created."""
    files = {
        "profile.md": "---\nlast_updated: 2026-03-29\n---\n## Identity\nSandy, builder.",
        "goals.md": "---\nlast_updated: 2026-03-29\n---\n## Short-term\n- [ ] Ship STARK v0.2.0",
        "habits.md": "---\nlast_updated: 2026-03-29\n---\n| Habit | Target | Streak |\n|---|---|---|\n| Training | Daily | 4 |",
        "projects.md": "---\nlast_updated: 2026-03-29\n---\n## STARK v0.2.0\nStatus: in progress",
        "weekly_review.md": "---\nlast_updated: 2026-03-29\n---\n",
    }
    for fname, content in files.items():
        (ctx_manager._dir / fname).mkdir(parents=True, exist_ok=True) if False else None
        ctx_manager._dir.mkdir(parents=True, exist_ok=True)
        (ctx_manager._dir / fname).write_text(content, encoding="utf-8")
    return ctx_manager


# ==============================================================================
# ContextManager — read
# ==============================================================================


class TestContextManagerRead:
    def test_read_all_returns_all_keys(self, populated_ctx: ContextManager) -> None:
        result = populated_ctx.read_all()
        assert set(result.keys()) == {"profile", "goals", "habits", "projects", "weekly_review"}

    def test_read_missing_file_returns_empty(self, ctx_manager: ContextManager) -> None:
        result = ctx_manager.read("nonexistent.md")
        assert result == {"metadata": {}, "body": ""}

    def test_read_parses_frontmatter(self, populated_ctx: ContextManager) -> None:
        data = populated_ctx.read("goals.md")
        assert data["metadata"]["last_updated"] == "2026-03-29"
        assert "Ship STARK" in data["body"]


# ==============================================================================
# ContextManager — write
# ==============================================================================


class TestContextManagerWrite:
    def test_update_bumps_last_updated(self, ctx_manager: ContextManager) -> None:
        ctx_manager._dir.mkdir(parents=True, exist_ok=True)
        ctx_manager.update("goals.md", "## Short-term\n- [ ] New goal")
        data = ctx_manager.read("goals.md")
        assert data["metadata"]["last_updated"] == date.today().isoformat()
        assert "New goal" in data["body"]

    def test_update_preserves_existing_metadata(self, populated_ctx: ContextManager) -> None:
        populated_ctx.update("profile.md", "## Identity\nUpdated.", extra_meta={"version": "2"})
        data = populated_ctx.read("profile.md")
        assert data["metadata"]["version"] == "2"
        assert "Updated." in data["body"]

    def test_update_section_replaces_existing(self, populated_ctx: ContextManager) -> None:
        populated_ctx.update_section("goals.md", "## Short-term", "- [ ] Replaced goal")
        data = populated_ctx.read("goals.md")
        assert "Replaced goal" in data["body"]
        assert "Ship STARK" not in data["body"]

    def test_update_section_appends_when_not_found(self, populated_ctx: ContextManager) -> None:
        populated_ctx.update_section("goals.md", "## New Section", "Some content")
        data = populated_ctx.read("goals.md")
        assert "New Section" in data["body"]
        assert "Some content" in data["body"]


# ==============================================================================
# store_episode
# ==============================================================================


class TestStoreEpisode:
    def test_writes_row_to_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "episodic.db"
        episode_id = store_episode(
            "morning_briefing",
            "Test briefing content",
            tags=["morning", "test"],
            db_path=db_path,
        )
        assert len(episode_id) == 36  # UUID format

        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT content, metadata, tags FROM episodes WHERE id = ?",
                (episode_id,),
            ).fetchone()

        assert row is not None
        assert row[0] == "Test briefing content"
        meta = json.loads(row[1])
        assert meta["episode_type"] == "morning_briefing"
        assert meta["source"] == "life_os"
        tags = json.loads(row[2])
        assert "morning" in tags

    def test_stores_without_tags(self, tmp_path: Path) -> None:
        db_path = tmp_path / "episodic.db"
        episode_id = store_episode("habit_update", "did training", db_path=db_path)
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT tags FROM episodes WHERE id = ?", (episode_id,)
            ).fetchone()
        assert json.loads(row[0]) == []


# ==============================================================================
# MorningAgent — prompt building (no Ollama)
# ==============================================================================


class TestMorningAgentPrompt:
    def test_build_user_prompt_with_no_events_or_tasks(self) -> None:
        from modules.life_os.agents.morning_agent import MorningAgent

        agent = MorningAgent()
        context = {
            "goals": {"body": "- [ ] Ship STARK v0.2.0", "metadata": {}},
            "habits": {"body": "Training: streak 4", "metadata": {}},
        }
        prompt = agent._build_user_prompt(context, events=[], tasks=[])
        assert "Ship STARK" in prompt
        assert "No calendar events found" in prompt
        assert "No tasks due today" in prompt

    def test_build_user_prompt_includes_events(self) -> None:
        from modules.life_os.agents.morning_agent import MorningAgent

        agent = MorningAgent()
        events = [{"summary": "Team meeting", "start": "09:00", "end": "10:00"}]
        prompt = agent._build_user_prompt({}, events=events, tasks=[])
        assert "Team meeting" in prompt

    def test_run_writes_log_file(self, tmp_path: Path) -> None:
        from modules.life_os.agents.morning_agent import MorningAgent

        with (
            patch("modules.life_os.agents.morning_agent.LIFE_OS_LOG_DIR", tmp_path),
            patch.object(MorningAgent, "call", return_value="## Today's top 3\n1. Ship it"),
        ):
            agent = MorningAgent()
            result = agent.run(context={})

        assert "Ship it" in result
        log_path = tmp_path / f"{date.today().isoformat()}.md"
        assert log_path.exists()
        assert "Morning Briefing" in log_path.read_text(encoding="utf-8")


# ==============================================================================
# EveningAgent — log appending
# ==============================================================================


class TestEveningAgent:
    def test_run_returns_dict(self, tmp_path: Path) -> None:
        from modules.life_os.agents.evening_agent import EveningAgent

        mock_result = {
            "completed_tasks": ["Wrote tests"],
            "habits_done": ["Training"],
            "reflection": "Good day. Tests pass. Sleep.",
            "carryover": [],
        }
        with (
            patch("modules.life_os.agents.evening_agent.LIFE_OS_LOG_DIR", tmp_path),
            patch.object(EveningAgent, "call_json", return_value=mock_result),
        ):
            agent = EveningAgent()
            result = agent.run(intake="I finished writing tests. Did training.", today_log="")

        assert result["completed_tasks"] == ["Wrote tests"]
        assert result["habits_done"] == ["Training"]

    def test_run_appends_to_existing_log(self, tmp_path: Path) -> None:
        from modules.life_os.agents.evening_agent import EveningAgent

        today = date.today().isoformat()
        existing_log = tmp_path / f"{today}.md"
        existing_log.write_text("# Daily Log\n## Morning Briefing\n_07:02_\n\nBriefing text.\n")

        mock_result = {
            "completed_tasks": [],
            "habits_done": [],
            "reflection": "Decent day overall.",
            "carryover": ["Finish docs"],
        }
        with (
            patch("modules.life_os.agents.evening_agent.LIFE_OS_LOG_DIR", tmp_path),
            patch.object(EveningAgent, "call_json", return_value=mock_result),
        ):
            EveningAgent().run(intake="Decent day.", today_log="")

        content = existing_log.read_text(encoding="utf-8")
        assert "Evening Review" in content
        assert "Decent day overall." in content
        assert "Finish docs" in content


# ==============================================================================
# Voice hooks — error handling
# ==============================================================================


class TestVoiceHooks:
    def test_handle_morning_returns_error_string_on_failure(self) -> None:
        from modules.life_os.voice_hooks import handle_morning

        with patch(
            "modules.life_os.voice_hooks.MorningAgent",
            side_effect=RuntimeError("boom"),
        ):
            result = handle_morning("morning briefing")
        assert "[life_os]" in result
        assert "boom" in result

    def test_handle_evening_strips_trigger_phrase(self, tmp_path: Path) -> None:
        from modules.life_os.agents.evening_agent import EveningAgent
        from modules.life_os import voice_hooks

        captured: list[str] = []

        def fake_run(self: EveningAgent, intake: str, today_log: str = "") -> dict:
            captured.append(intake)
            return {"reflection": "ok", "completed_tasks": [], "habits_done": [], "carryover": []}

        with (
            patch("modules.life_os.voice_hooks.LIFE_OS_LOG_DIR", tmp_path),
            patch.object(EveningAgent, "run", fake_run),
            patch("modules.life_os.voice_hooks.store_episode"),
            patch("modules.life_os.voice_hooks._apply_evening_updates"),
        ):
            voice_hooks.handle_evening("evening review I trained and shipped the context manager")

        assert captured[0] == "I trained and shipped the context manager"
