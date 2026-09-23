"""
Morning Agent
=============
Generates Sandy's daily briefing: top 3 priorities, risk flag, habit alert,
and evening check-in questions.

Output is written to ``logs/life_os/YYYY-MM-DD.md`` and returned as a string.
"""
import logging
from datetime import date, datetime
from typing import Any

from modules.life_os.agents.base_agent import LifeOsBaseAgent
from core.constants import LIFE_OS_LOG_DIR, LIFE_OS_MODEL

logger = logging.getLogger(__name__)

_MORNING_SYSTEM = """You are STARK, Sandy's personal AI operating system.
You have full context of Sandy's life, goals, habits, and projects.
Today is {date}.

Rules:
- Be direct. No generic advice. Reference Sandy's actual data.
- Every output must be immediately actionable.
- Flag any goal with zero progress for 7+ days.
- If a habit streak is broken, name it explicitly.

Output format (strict — do not add extra sections):
## Today's top 3
1. [specific task] — [why it matters today]
2. [specific task] — [why it matters today]
3. [specific task] — [why it matters today]

## Watch out for
[one specific risk or blocker based on data]

## Habit alert
[name the one habit most at risk right now, with streak data]

## Evening check-in
[2 questions to ask Sandy at 9pm based on today's focus]
"""


class MorningAgent(LifeOsBaseAgent):
    """Generates daily morning briefings from life context + calendar + tasks."""

    def __init__(self) -> None:
        super().__init__(model=LIFE_OS_MODEL)

    def run(
        self,
        context: dict[str, Any],
        events: list[dict[str, Any]] | None = None,
        tasks: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Generate a morning briefing.

        Args:
            context: Output of ``ContextManager.read_all()``.
            events: List of GCal event dicts (summary, start, end).
            tasks: List of Notion task dicts (title, due, status).

        Returns:
            Briefing text string. Also writes to ``logs/life_os/YYYY-MM-DD.md``.
        """
        today = date.today()
        system = _MORNING_SYSTEM.format(date=today.isoformat())
        user = self._build_user_prompt(context, events or [], tasks or [])
        briefing = self.call(system, user)
        self._write_log(today, briefing)
        return briefing

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_user_prompt(
        context: dict[str, Any],
        events: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
    ) -> str:
        parts: list[str] = []

        for key in ("profile", "goals", "habits", "projects"):
            body = context.get(key, {}).get("body", "").strip()
            if body:
                parts.append(f"## {key.title()}\n{body}")

        if events:
            lines = "\n".join(
                f"- {e.get('summary', 'Event')} "
                f"@ {e.get('start', '?')} – {e.get('end', '?')}"
                for e in events
            )
            parts.append(f"## Today's calendar\n{lines}")
        else:
            parts.append("## Today's calendar\nNo calendar events found.")

        if tasks:
            lines = "\n".join(
                f"- [{t.get('status', '?')}] {t.get('title', '?')} "
                f"(due: {t.get('due', 'N/A')})"
                for t in tasks
            )
            parts.append(f"## Overdue / due-today tasks\n{lines}")
        else:
            parts.append("## Overdue / due-today tasks\nNo tasks due today.")

        return "\n\n".join(parts)

    @staticmethod
    def _write_log(today: date, briefing: str) -> None:
        log_dir = LIFE_OS_LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{today.isoformat()}.md"
        timestamp = datetime.now().strftime("%H:%M")
        header = f"# Daily Log — {today.isoformat()}\n\n## Morning Briefing\n_{timestamp}_\n\n"
        log_path.write_text(header + briefing + "\n", encoding="utf-8")
        logger.info("Morning briefing written to %s", log_path)
