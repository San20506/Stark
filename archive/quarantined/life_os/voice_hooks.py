"""
Life OS Voice Hooks
===================
Intent handlers wired into STARK's voice/intent pipeline.
Handler names are registered in ``data/intent_library.json``.

Each handler takes ``(query: str, context: dict | None)`` and returns
a response string for TTS/display.  All errors are caught and logged —
the voice pipeline must never crash (R4).
"""
import logging
from datetime import date
from typing import Any

from core.constants import LIFE_OS_LOG_DIR

logger = logging.getLogger(__name__)

# Trigger prefixes to strip from the query before passing as intake.
_EVENING_TRIGGERS: tuple[str, ...] = (
    "evening review",
    "end of day",
    "daily review",
    "how was today",
)


def handle_morning(query: str, context: dict[str, Any] | None = None) -> str:
    """
    Trigger a morning briefing on demand (voice or CLI).

    Registered intent: ``morning_briefing``
    """
    try:
        from modules.life_os.agents.morning_agent import MorningAgent
        from modules.life_os.connectors.gcal_connector import GCalConnector
        from modules.life_os.connectors.notion_connector import NotionConnector
        from modules.life_os.context_manager import get_context_manager, store_episode

        ctx = get_context_manager().read_all()
        events: list[dict] = []
        tasks: list[dict] = []

        try:
            events = GCalConnector().get_events()
        except Exception:
            logger.debug("GCal not available for on-demand morning briefing")
        try:
            tasks = NotionConnector().get_due_tasks()
        except Exception:
            logger.debug("Notion not available for on-demand morning briefing")

        briefing = MorningAgent().run(ctx, events, tasks)
        store_episode("morning_briefing", briefing, tags=["morning", "on_demand"])
        return briefing
    except Exception as exc:
        logger.error("handle_morning failed: %s", exc)
        return f"[life_os] Morning briefing failed: {exc}"


def handle_evening(query: str, context: dict[str, Any] | None = None) -> str:
    """
    Submit end-of-day intake and run evening review.

    Strips the trigger phrase from ``query`` to extract just Sandy's intake.
    Registered intent: ``evening_review``
    """
    try:
        from modules.life_os.agents.evening_agent import EveningAgent
        from modules.life_os.context_manager import store_episode

        intake = query.strip()
        for trigger in _EVENING_TRIGGERS:
            if intake.lower().startswith(trigger):
                intake = intake[len(trigger):].strip()
                break

        today = date.today()
        today_log_path = LIFE_OS_LOG_DIR / f"{today.isoformat()}.md"
        today_log = (
            today_log_path.read_text(encoding="utf-8")
            if today_log_path.exists()
            else ""
        )

        result = EveningAgent().run(intake=intake, today_log=today_log)
        _apply_evening_updates(result)
        store_episode("evening_review", str(result), tags=["evening", "daily"])
        return result.get("reflection", "Evening review complete.")
    except Exception as exc:
        logger.error("handle_evening failed: %s", exc)
        return f"[life_os] Evening review failed: {exc}"


def handle_weekly(query: str, context: dict[str, Any] | None = None) -> str:
    """
    Trigger the weekly goal audit on demand.

    Registered intent: ``weekly_review``
    """
    try:
        from modules.life_os.scheduler import run_weekly

        run_weekly()
        return "Weekly review complete. Check logs/life_os/ for the full report."
    except Exception as exc:
        logger.error("handle_weekly failed: %s", exc)
        return f"[life_os] Weekly review failed: {exc}"


def handle_habit_update(query: str, context: dict[str, Any] | None = None) -> str:
    """
    Log a habit completion from voice (e.g. "I did weight training").

    Full streak recalculation happens in the next evening review.
    Registered intent: ``update_habit``
    """
    try:
        from modules.life_os.context_manager import store_episode

        store_episode(
            "habit_update",
            f"Voice habit update: {query}",
            tags=["habit", "voice"],
        )
        return "Got it — habit logged. Streaks will update during tonight's evening review."
    except Exception as exc:
        logger.error("handle_habit_update failed: %s", exc)
        return f"[life_os] Habit update failed: {exc}"


# ==============================================================================
# Private helpers
# ==============================================================================


def _apply_evening_updates(result: dict[str, Any]) -> None:
    """Update context files based on the evening agent's structured output."""
    try:
        from modules.life_os.context_manager import get_context_manager

        cm = get_context_manager()
        today = date.today().isoformat()
        reflection = result.get("reflection", "").strip()

        if reflection:
            data = cm.read("weekly_review.md")
            existing_body = data.get("body", "").rstrip()
            new_entry = f"\n\n### {today}\n{reflection}"
            cm.update("weekly_review.md", existing_body + new_entry)
    except Exception:
        logger.exception("_apply_evening_updates failed — continuing without context update")
