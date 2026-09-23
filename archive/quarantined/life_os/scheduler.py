"""
Life OS Scheduler
=================
APScheduler hooks for automated daily/weekly triggers.

Trigger times are read from ``core/constants.py``:
- ``LIFE_OS_MORNING_HOUR``  (default 07:00)
- ``LIFE_OS_EVENING_HOUR``  (default 21:00)
- ``LIFE_OS_WEEKLY_HOUR``   (default 10:00, Sundays)

Usage:
    from modules.life_os.scheduler import start_scheduler
    start_scheduler()  # call once at STARK startup
"""
import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from core.constants import (
    LIFE_OS_EVENING_HOUR,
    LIFE_OS_LOG_DIR,
    LIFE_OS_MORNING_HOUR,
    LIFE_OS_WEEKLY_DAY,
    LIFE_OS_WEEKLY_HOUR,
)

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


# ==============================================================================
# Job functions
# ==============================================================================


def run_morning() -> None:
    """Scheduled morning briefing — fires at LIFE_OS_MORNING_HOUR daily."""
    from modules.life_os.agents.morning_agent import MorningAgent
    from modules.life_os.connectors.gcal_connector import GCalConnector
    from modules.life_os.connectors.notion_connector import NotionConnector
    from modules.life_os.context_manager import get_context_manager, store_episode

    logger.info("Running scheduled morning briefing")
    ctx = get_context_manager().read_all()

    events: list[dict] = []
    tasks: list[dict] = []

    try:
        events = GCalConnector().get_events()
    except Exception:
        logger.warning("GCal unavailable — running morning briefing without calendar events")

    try:
        tasks = NotionConnector().get_due_tasks()
    except Exception:
        logger.warning("Notion unavailable — running morning briefing without task list")

    briefing = MorningAgent().run(ctx, events, tasks)
    store_episode("morning_briefing", briefing, tags=["morning", "daily", "scheduled"])
    logger.info("Morning briefing complete")


def run_evening() -> None:
    """
    Scheduled evening trigger — fires at LIFE_OS_EVENING_HOUR daily.

    Stores a PENDING_INTAKE placeholder so the web panel knows to prompt Sandy.
    Full processing happens when Sandy provides intake via voice or the web UI.
    """
    from modules.life_os.context_manager import store_episode

    logger.info("Evening review scheduled trigger — storing pending intake marker")
    store_episode(
        "evening_review",
        "PENDING_INTAKE",
        tags=["evening", "daily", "pending"],
    )


def run_weekly() -> None:
    """Scheduled weekly goal audit — fires on LIFE_OS_WEEKLY_DAY at LIFE_OS_WEEKLY_HOUR."""
    from modules.life_os.agents.weekly_agent import WeeklyAgent
    from modules.life_os.connectors.notion_connector import NotionConnector
    from modules.life_os.context_manager import get_context_manager, store_episode

    logger.info("Running scheduled weekly review")
    ctx = get_context_manager().read_all()

    last_7_logs = _collect_daily_logs(days=7)
    review = WeeklyAgent().run(ctx, last_7_logs)
    store_episode("weekly_review", review, tags=["weekly", "goals", "scheduled"])

    today = date.today()
    week = today.isocalendar().week
    try:
        NotionConnector().create_weekly_page(
            title=f"Week {week} Review — {today.year}",
            content_md=review,
        )
    except Exception:
        logger.warning("Notion push failed — weekly review stored locally only")

    logger.info("Weekly review complete")


# ==============================================================================
# Scheduler lifecycle
# ==============================================================================


def start_scheduler() -> None:
    """
    Start the APScheduler background scheduler with all life_os jobs.

    Safe to call at STARK startup — idempotent if already running.
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.warning("Life OS scheduler already running — skipping start")
        return

    _scheduler = BackgroundScheduler()

    _scheduler.add_job(
        run_morning,
        CronTrigger(hour=LIFE_OS_MORNING_HOUR, minute=0),
        id="life_os_morning",
        replace_existing=True,
    )
    _scheduler.add_job(
        run_evening,
        CronTrigger(hour=LIFE_OS_EVENING_HOUR, minute=0),
        id="life_os_evening",
        replace_existing=True,
    )
    _scheduler.add_job(
        run_weekly,
        CronTrigger(day_of_week=LIFE_OS_WEEKLY_DAY, hour=LIFE_OS_WEEKLY_HOUR, minute=0),
        id="life_os_weekly",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Life OS scheduler started — morning=%02d:00 daily, evening=%02d:00 daily, "
        "weekly=%s %02d:00",
        LIFE_OS_MORNING_HOUR,
        LIFE_OS_EVENING_HOUR,
        LIFE_OS_WEEKLY_DAY,
        LIFE_OS_WEEKLY_HOUR,
    )


def stop_scheduler() -> None:
    """Stop the life_os background scheduler."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Life OS scheduler stopped")
    _scheduler = None


def get_scheduler() -> BackgroundScheduler | None:
    """Return the current scheduler instance (None if not started)."""
    return _scheduler


# ==============================================================================
# Private helpers
# ==============================================================================


def _collect_daily_logs(days: int) -> list[str]:
    """Return the last ``days`` daily log file contents (most recent first)."""
    logs: list[str] = []
    for days_back in range(1, days + 1):
        day = date.today() - timedelta(days=days_back)
        log_path = LIFE_OS_LOG_DIR / f"{day.isoformat()}.md"
        if log_path.exists():
            logs.append(log_path.read_text(encoding="utf-8"))
    return logs
