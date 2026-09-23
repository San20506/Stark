"""
Evening Agent
=============
Processes Sandy's end-of-day intake and returns structured update data.

The agent extracts:
- completed_tasks  → used to update projects.md
- habits_done      → used to update habit streaks in habits.md
- reflection       → appended to weekly_review.md
- carryover        → flagged for tomorrow's morning briefing
"""
import logging
from datetime import date, datetime
from typing import Any

from modules.life_os.agents.base_agent import LifeOsBaseAgent
from core.constants import LIFE_OS_LOG_DIR, LIFE_OS_MODEL

logger = logging.getLogger(__name__)

_EVENING_SYSTEM = """You are STARK running Sandy's evening review.

Today's log:
{today_log}

Sandy's intake:
{intake}

Tasks:
1. Extract completed items from the intake → list of task titles
2. Extract habit completions → list of habit names Sandy did today
3. Write a 3-sentence reflection (what went well, what was blocked, key insight)
4. Flag anything that needs to carry over to tomorrow

Respond with ONLY valid JSON — no markdown fences, no extra text:
{{
  "completed_tasks": ["task 1", "task 2"],
  "habits_done": ["habit name 1"],
  "reflection": "Three-sentence reflection text.",
  "carryover": ["item to carry over to tomorrow"]
}}
"""


class EveningAgent(LifeOsBaseAgent):
    """Processes end-of-day review and returns structured update data."""

    def __init__(self) -> None:
        super().__init__(model=LIFE_OS_MODEL)

    def run(self, intake: str, today_log: str = "") -> dict[str, Any]:
        """
        Process the evening intake.

        Args:
            intake: Sandy's free-text description of the day.
            today_log: Content of today's morning log file (optional).

        Returns:
            Dict with keys: completed_tasks, habits_done, reflection, carryover.
            Also appends an evening section to ``logs/life_os/YYYY-MM-DD.md``.
        """
        system = _EVENING_SYSTEM.format(
            today_log=today_log or "(no morning log available)",
            intake=intake,
        )
        user = "Please process my end-of-day review based on the intake above."
        result = self.call_json(system, user)
        self._append_log(result)
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _append_log(result: dict[str, Any]) -> None:
        today = date.today()
        log_path = LIFE_OS_LOG_DIR / f"{today.isoformat()}.md"
        timestamp = datetime.now().strftime("%H:%M")
        completed = ", ".join(result.get("completed_tasks", [])) or "—"
        carryover = ", ".join(result.get("carryover", [])) or "—"
        section = (
            f"\n## Evening Review\n_{timestamp}_\n\n"
            f"**Reflection:** {result.get('reflection', '')}\n\n"
            f"**Completed:** {completed}\n\n"
            f"**Habits done:** {', '.join(result.get('habits_done', [])) or '—'}\n\n"
            f"**Carryover:** {carryover}\n"
        )
        if log_path.exists():
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(section)
        else:
            LIFE_OS_LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_path.write_text(
                f"# Daily Log — {today.isoformat()}\n{section}",
                encoding="utf-8",
            )
        logger.info("Evening review appended to %s", log_path)
