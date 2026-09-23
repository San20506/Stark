"""
Life OS Module
==============
STARK's daily life operating system.

Provides:
- Automated morning briefings (07:00)
- Evening review processing (21:00)
- Weekly goal audits (Sunday 10:00)
- Habit tracking and streak management
- Google Calendar + Notion integration
- Voice and web hooks for manual triggers

Use ``from modules.life_os.scheduler import start_scheduler`` to enable
auto-scheduling.
"""
from modules.life_os.context_manager import get_context_manager, store_episode
from modules.life_os.scheduler import start_scheduler, stop_scheduler

__all__ = [
    "get_context_manager",
    "store_episode",
    "start_scheduler",
    "stop_scheduler",
]
