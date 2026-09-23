"""
Weekly Agent
============
Generates Sandy's Sunday goal audit: wins/failures, updated goal status,
next week's top 3, and one uncomfortable truth.

Output is written to ``logs/life_os/weekly-YYYY-Www.md`` and returned as a string.
"""
import logging
from datetime import date
from typing import Any

from modules.life_os.agents.base_agent import LifeOsBaseAgent
from core.constants import LIFE_OS_LOG_DIR, LIFE_OS_MODEL

logger = logging.getLogger(__name__)

_WEEKLY_SYSTEM = """You are STARK running Sandy's weekly review.
Today is {date} (ISO week {week}).

You have Sandy's full life context and the last 7 daily logs.

Tasks:
1. Assess each goal: still relevant? on track? update status.
2. Identify the single biggest win and single biggest failure of the week.
3. Write 3 priorities for next week based on what's behind or at risk.
4. Give Sandy one direct, uncomfortable truth about the week — no hedging.

Output format (strict):
## Week {week} Review

### Wins & Failures
**Win:** [specific achievement with evidence]
**Failure:** [specific failure with root cause]

### Goal Status Updates
[one line per goal: goal name — updated status — one-sentence reason]

### Next Week's Top 3
1. [priority] — [reason]
2. [priority] — [reason]
3. [priority] — [reason]

### Uncomfortable Truth
[one direct statement, no hedging, no softening]
"""


class WeeklyAgent(LifeOsBaseAgent):
    """Generates weekly goal audits from context and daily logs."""

    def __init__(self) -> None:
        super().__init__(model=LIFE_OS_MODEL)

    def run(
        self,
        context: dict[str, Any],
        last_7_logs: list[str],
    ) -> str:
        """
        Generate a weekly review.

        Args:
            context: Output of ``ContextManager.read_all()``.
            last_7_logs: List of daily log file contents (most recent first).

        Returns:
            Review text string. Also writes to ``logs/life_os/weekly-YYYY-Www.md``.
        """
        today = date.today()
        week = today.isocalendar().week
        system = _WEEKLY_SYSTEM.format(date=today.isoformat(), week=week)
        user = self._build_user_prompt(context, last_7_logs)
        review = self.call(system, user)
        self._write_log(today, week, review)
        return review

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_user_prompt(
        context: dict[str, Any],
        last_7_logs: list[str],
    ) -> str:
        context_sections = "\n\n".join(
            f"### {key.title()}\n{val['body']}"
            for key, val in context.items()
            if val.get("body", "").strip()
        )
        log_summary = (
            "\n\n---\n\n".join(last_7_logs)
            if last_7_logs
            else "(no daily logs found for this week)"
        )
        return f"## Life Context\n\n{context_sections}\n\n## Last 7 Days\n\n{log_summary}"

    @staticmethod
    def _write_log(today: date, week: int, review: str) -> None:
        log_dir = LIFE_OS_LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"weekly-{today.year}-W{week:02d}.md"
        header = (
            f"# Weekly Review — {today.year} W{week:02d}\n"
            f"_{today.isoformat()}_\n\n"
        )
        log_path.write_text(header + review + "\n", encoding="utf-8")
        logger.info("Weekly review written to %s", log_path)
