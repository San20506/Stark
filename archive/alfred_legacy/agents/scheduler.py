"""
ALFRED Proactive Scheduler
Enables automatic task execution, cron-style scheduling, and event triggers.

Based on APScheduler for robust background task management.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """Represents a scheduled task."""
    task_id: str
    action: str  # Natural language action to execute
    trigger_type: str  # 'cron', 'date', 'interval'
    trigger_config: Dict  # Trigger-specific configuration
    enabled: bool = True
    created_at: str = None
    last_run: str = None
    next_run: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class ALFREDScheduler:
    """
    Proactive task scheduler for ALFRED.
    
    Enables:
    - Cron-style recurring tasks ("every day at 9 AM")
    - One-time scheduled tasks ("remind me in 2 hours")
    - Interval-based tasks ("check email every 30 minutes")
    - Event-based triggers (via EventMonitor)
    """
    
    def __init__(self, brain=None, storage_path: str = "data/scheduled_tasks.json"):
        """
        Initialize scheduler.
        
        Args:
            brain: ALFRED's brain/MCP for executing actions
            storage_path: Path to persist scheduled tasks
        """
        self.brain = brain
        self.storage_path = storage_path
        self.scheduler = BackgroundScheduler()
        self.tasks: Dict[str, ScheduledTask] = {}
        
        # Load persisted tasks
        self._load_tasks()
        
        # Start scheduler
        self.scheduler.start()
        logger.info("✅ ALFRED Scheduler started")
    
    def add_cron_task(
        self,
        task_id: str,
        action: str,
        cron: str = None,
        hour: int = None,
        minute: int = None,
        day_of_week: str = None
    ) -> bool:
        """
        Add a cron-style recurring task.
        
        Args:
            task_id: Unique task identifier
            action: Natural language action to execute
            cron: Cron expression (e.g., "0 9 * * *" for 9 AM daily)
            hour: Hour (0-23) for simple scheduling
            minute: Minute (0-59) for simple scheduling
            day_of_week: Day of week (mon, tue, etc.)
            
        Returns:
            True if task added successfully
            
        Examples:
            # Every day at 9 AM
            add_cron_task("morning_weather", "what's the weather?", hour=9, minute=0)
            
            # Every Monday at 10 AM
            add_cron_task("weekly_report", "generate weekly report", 
                         hour=10, minute=0, day_of_week="mon")
            
            # Using cron expression
            add_cron_task("hourly_check", "check for updates", cron="0 * * * *")
        """
        try:
            # Create trigger
            if cron:
                trigger = CronTrigger.from_crontab(cron)
                trigger_config = {"cron": cron}
            else:
                trigger = CronTrigger(
                    hour=hour,
                    minute=minute,
                    day_of_week=day_of_week
                )
                trigger_config = {
                    "hour": hour,
                    "minute": minute,
                    "day_of_week": day_of_week
                }
            
            # Add to scheduler
            self.scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                args=[task_id, action],
                id=task_id,
                replace_existing=True
            )
            
            # Store task metadata
            task = ScheduledTask(
                task_id=task_id,
                action=action,
                trigger_type="cron",
                trigger_config=trigger_config
            )
            self.tasks[task_id] = task
            
            # Persist
            self._save_tasks()
            
            logger.info(f"✅ Added cron task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add cron task {task_id}: {e}")
            return False
    
    def add_one_time_task(
        self,
        task_id: str,
        action: str,
        run_date: datetime = None,
        delay_seconds: int = None,
        delay_minutes: int = None,
        delay_hours: int = None
    ) -> bool:
        """
        Add a one-time scheduled task.
        
        Args:
            task_id: Unique task identifier
            action: Natural language action to execute
            run_date: Specific datetime to run
            delay_seconds: Run after N seconds
            delay_minutes: Run after N minutes
            delay_hours: Run after N hours
            
        Returns:
            True if task added successfully
            
        Examples:
            # Run in 2 hours
            add_one_time_task("reminder", "remind me about meeting", delay_hours=2)
            
            # Run at specific time
            add_one_time_task("appointment", "meeting in 5 minutes", 
                            run_date=datetime(2025, 12, 18, 15, 0))
        """
        try:
            # Calculate run date
            if run_date is None:
                run_date = datetime.now()
                if delay_seconds:
                    run_date += timedelta(seconds=delay_seconds)
                if delay_minutes:
                    run_date += timedelta(minutes=delay_minutes)
                if delay_hours:
                    run_date += timedelta(hours=delay_hours)
            
            # Create trigger
            trigger = DateTrigger(run_date=run_date)
            
            # Add to scheduler
            self.scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                args=[task_id, action],
                id=task_id,
                replace_existing=True
            )
            
            # Store task metadata
            task = ScheduledTask(
                task_id=task_id,
                action=action,
                trigger_type="date",
                trigger_config={"run_date": run_date.isoformat()}
            )
            self.tasks[task_id] = task
            
            # Persist
            self._save_tasks()
            
            logger.info(f"✅ Added one-time task: {task_id} at {run_date}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add one-time task {task_id}: {e}")
            return False
    
    def add_interval_task(
        self,
        task_id: str,
        action: str,
        seconds: int = None,
        minutes: int = None,
        hours: int = None
    ) -> bool:
        """
        Add an interval-based recurring task.
        
        Args:
            task_id: Unique task identifier
            action: Natural language action to execute
            seconds: Repeat every N seconds
            minutes: Repeat every N minutes
            hours: Repeat every N hours
            
        Returns:
            True if task added successfully
            
        Examples:
            # Every 30 minutes
            add_interval_task("email_check", "check for new emails", minutes=30)
            
            # Every 2 hours
            add_interval_task("backup", "backup important files", hours=2)
        """
        try:
            # Create trigger
            trigger = IntervalTrigger(
                seconds=seconds or 0,
                minutes=minutes or 0,
                hours=hours or 0
            )
            
            # Add to scheduler
            self.scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                args=[task_id, action],
                id=task_id,
                replace_existing=True
            )
            
            # Store task metadata
            task = ScheduledTask(
                task_id=task_id,
                action=action,
                trigger_type="interval",
                trigger_config={
                    "seconds": seconds,
                    "minutes": minutes,
                    "hours": hours
                }
            )
            self.tasks[task_id] = task
            
            # Persist
            self._save_tasks()
            
            logger.info(f"✅ Added interval task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add interval task {task_id}: {e}")
            return False
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        try:
            self.scheduler.remove_job(task_id)
            if task_id in self.tasks:
                del self.tasks[task_id]
            self._save_tasks()
            logger.info(f"✅ Removed task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to remove task {task_id}: {e}")
            return False
    
    def pause_task(self, task_id: str) -> bool:
        """Pause a scheduled task."""
        try:
            self.scheduler.pause_job(task_id)
            if task_id in self.tasks:
                self.tasks[task_id].enabled = False
            self._save_tasks()
            logger.info(f"⏸️ Paused task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to pause task {task_id}: {e}")
            return False
    
    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        try:
            self.scheduler.resume_job(task_id)
            if task_id in self.tasks:
                self.tasks[task_id].enabled = True
            self._save_tasks()
            logger.info(f"▶️ Resumed task: {task_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to resume task {task_id}: {e}")
            return False
    
    def list_tasks(self) -> List[ScheduledTask]:
        """List all scheduled tasks."""
        return list(self.tasks.values())
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a specific task."""
        return self.tasks.get(task_id)
    
    def _execute_task(self, task_id: str, action: str):
        """
        Execute a scheduled task.
        
        Args:
            task_id: Task identifier
            action: Natural language action to execute
        """
        try:
            logger.info(f"🔄 Executing scheduled task: {task_id}")
            logger.info(f"   Action: {action}")
            
            # Update last run time
            if task_id in self.tasks:
                self.tasks[task_id].last_run = datetime.now().isoformat()
                self._save_tasks()
            
            # Execute through brain/MCP
            if self.brain:
                result = self.brain.process(action)
                logger.info(f"✅ Task completed: {task_id}")
                logger.info(f"   Result: {result.final_answer[:100]}...")
            else:
                logger.warning(f"⚠️ No brain configured, task not executed: {task_id}")
            
        except Exception as e:
            logger.error(f"❌ Task execution failed: {task_id}")
            logger.error(f"   Error: {e}")
    
    def _save_tasks(self):
        """Persist tasks to disk."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            tasks_data = {
                task_id: asdict(task)
                for task_id, task in self.tasks.items()
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(tasks_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Failed to save tasks: {e}")
    
    def _load_tasks(self):
        """Load persisted tasks from disk."""
        try:
            if not os.path.exists(self.storage_path):
                return
            
            with open(self.storage_path, 'r') as f:
                tasks_data = json.load(f)
            
            for task_id, task_dict in tasks_data.items():
                task = ScheduledTask(**task_dict)
                self.tasks[task_id] = task
                
                # Re-add to scheduler
                if task.enabled:
                    self._restore_task(task)
            
            logger.info(f"✅ Loaded {len(self.tasks)} persisted tasks")
            
        except Exception as e:
            logger.error(f"❌ Failed to load tasks: {e}")
    
    def _restore_task(self, task: ScheduledTask):
        """Restore a task to the scheduler after loading."""
        try:
            if task.trigger_type == "cron":
                config = task.trigger_config
                if "cron" in config:
                    trigger = CronTrigger.from_crontab(config["cron"])
                else:
                    trigger = CronTrigger(
                        hour=config.get("hour"),
                        minute=config.get("minute"),
                        day_of_week=config.get("day_of_week")
                    )
            elif task.trigger_type == "interval":
                config = task.trigger_config
                trigger = IntervalTrigger(
                    seconds=config.get("seconds") or 0,
                    minutes=config.get("minutes") or 0,
                    hours=config.get("hours") or 0
                )
            else:
                # Don't restore one-time tasks (they're in the past)
                return
            
            self.scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                args=[task.task_id, task.action],
                id=task.task_id,
                replace_existing=True
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to restore task {task.task_id}: {e}")
    
    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        self.scheduler.shutdown()
        logger.info("🛑 ALFRED Scheduler stopped")


# Singleton
_scheduler = None

def get_scheduler(brain=None) -> ALFREDScheduler:
    """Get or create the scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ALFREDScheduler(brain)
    return _scheduler


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    
    scheduler = ALFREDScheduler()
    
    # Test cron task
    scheduler.add_cron_task(
        "test_daily",
        "what's the weather?",
        hour=9,
        minute=0
    )
    
    # Test one-time task
    scheduler.add_one_time_task(
        "test_reminder",
        "test reminder",
        delay_seconds=5
    )
    
    # Test interval task
    scheduler.add_interval_task(
        "test_interval",
        "check status",
        minutes=1
    )
    
    print("\n📋 Scheduled Tasks:")
    for task in scheduler.list_tasks():
        print(f"  - {task.task_id}: {task.action}")
        print(f"    Type: {task.trigger_type}")
        print(f"    Config: {task.trigger_config}")
    
    import time
    print("\n⏳ Waiting 10 seconds to test execution...")
    time.sleep(10)
    
    scheduler.shutdown()
