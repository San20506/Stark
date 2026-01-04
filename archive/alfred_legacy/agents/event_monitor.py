"""
ALFRED Event Monitor
Monitors system events and triggers scheduled actions.

Supports:
- File system changes (watchdog)
- Email monitoring (IMAP)
- Calendar events (future)
- Custom event hooks
"""

import os
import logging
from typing import Dict, Callable, Optional
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

logger = logging.getLogger(__name__)


class FileWatcher(FileSystemEventHandler):
    """Watch file system for changes."""
    
    def __init__(self, path: str, action: Callable, event_types: list = None):
        """
        Initialize file watcher.
        
        Args:
            path: Path to watch
            action: Callback function to execute on event
            event_types: List of event types to watch ('created', 'modified', 'deleted')
        """
        self.path = path
        self.action = action
        self.event_types = event_types or ['created', 'modified']
        logger.info(f"📁 Watching: {path}")
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation."""
        if 'created' in self.event_types and not event.is_directory:
            logger.info(f"📄 File created: {event.src_path}")
            self._execute_action(event, 'created')
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification."""
        if 'modified' in self.event_types and not event.is_directory:
            logger.info(f"✏️ File modified: {event.src_path}")
            self._execute_action(event, 'modified')
    
    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion."""
        if 'deleted' in self.event_types and not event.is_directory:
            logger.info(f"🗑️ File deleted: {event.src_path}")
            self._execute_action(event, 'deleted')
    
    def _execute_action(self, event: FileSystemEvent, event_type: str):
        """Execute the action callback."""
        try:
            self.action(event.src_path, event_type)
        except Exception as e:
            logger.error(f"❌ Action execution failed: {e}")


class EventMonitor:
    """
    Monitor system events and trigger actions.
    
    Integrates with ALFREDScheduler to execute scheduled tasks
    based on external events.
    """
    
    def __init__(self, scheduler=None):
        """
        Initialize event monitor.
        
        Args:
            scheduler: ALFREDScheduler instance for executing actions
        """
        self.scheduler = scheduler
        self.file_observers: Dict[str, Observer] = {}
        self.email_monitors: Dict[str, dict] = {}
        self.calendar_monitors: Dict[str, dict] = {}
        
        logger.info("✅ Event Monitor initialized")
    
    def watch_file(
        self,
        path: str,
        action: str,
        event_types: list = None,
        recursive: bool = False
    ) -> str:
        """
        Watch a file or directory for changes.
        
        Args:
            path: Path to watch
            action: Natural language action to execute on event
            event_types: Types of events to watch ('created', 'modified', 'deleted')
            recursive: Watch subdirectories recursively
            
        Returns:
            Watch ID for later removal
            
        Examples:
            # Watch for new files in downloads
            watch_file("~/Downloads", "process new download", event_types=['created'])
            
            # Watch config file for changes
            watch_file("~/.alfred/config.json", "reload configuration", event_types=['modified'])
        """
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            logger.error(f"❌ Path does not exist: {path}")
            return None
        
        # Create callback that executes through scheduler
        def callback(file_path: str, event_type: str):
            logger.info(f"🔔 Event triggered: {event_type} on {file_path}")
            if self.scheduler:
                # Execute action through scheduler
                self.scheduler._execute_task(
                    f"file_event_{event_type}",
                    action.replace("{file}", file_path).replace("{event}", event_type)
                )
        
        # Create file watcher
        event_handler = FileWatcher(path, callback, event_types)
        observer = Observer()
        observer.schedule(event_handler, path, recursive=recursive)
        observer.start()
        
        # Store observer
        watch_id = f"file_{len(self.file_observers)}"
        self.file_observers[watch_id] = observer
        
        logger.info(f"✅ File watch started: {watch_id}")
        return watch_id
    
    def watch_email(
        self,
        email_address: str,
        filter_from: str = None,
        filter_subject: str = None,
        action: str = None,
        check_interval: int = 300
    ) -> str:
        """
        Monitor email inbox for new messages.
        
        Args:
            email_address: Email address to monitor
            filter_from: Only trigger for emails from this sender
            filter_subject: Only trigger for emails with this subject
            action: Natural language action to execute
            check_interval: Check interval in seconds (default: 5 minutes)
            
        Returns:
            Monitor ID for later removal
            
        Examples:
            # Alert on emails from boss
            watch_email(
                "user@gmail.com",
                filter_from="boss@company.com",
                action="notify about urgent email from boss"
            )
        """
        monitor_id = f"email_{len(self.email_monitors)}"
        
        # Store monitor config
        self.email_monitors[monitor_id] = {
            'email': email_address,
            'filter_from': filter_from,
            'filter_subject': filter_subject,
            'action': action,
            'interval': check_interval,
            'last_check': None
        }
        
        # Schedule periodic check through scheduler
        if self.scheduler:
            self.scheduler.add_interval_task(
                monitor_id,
                f"check email {email_address}",
                seconds=check_interval
            )
        
        logger.info(f"✅ Email monitor started: {monitor_id}")
        return monitor_id
    
    def watch_calendar(
        self,
        calendar_name: str,
        minutes_before: int,
        action: str
    ) -> str:
        """
        Trigger action before calendar events.
        
        Args:
            calendar_name: Name of calendar to monitor
            minutes_before: Minutes before event to trigger
            action: Natural language action to execute
            
        Returns:
            Monitor ID for later removal
            
        Examples:
            # Remind 15 minutes before meetings
            watch_calendar(
                "Work Calendar",
                minutes_before=15,
                action="remind about upcoming meeting"
            )
        """
        monitor_id = f"calendar_{len(self.calendar_monitors)}"
        
        # Store monitor config
        self.calendar_monitors[monitor_id] = {
            'calendar': calendar_name,
            'minutes_before': minutes_before,
            'action': action
        }
        
        # TODO: Integrate with Google Calendar API or local calendar
        logger.warning(f"⚠️ Calendar monitoring not yet implemented: {monitor_id}")
        logger.info(f"   Placeholder created for future implementation")
        
        return monitor_id
    
    def remove_watch(self, watch_id: str) -> bool:
        """Remove a watch/monitor."""
        # Check file observers
        if watch_id in self.file_observers:
            observer = self.file_observers[watch_id]
            observer.stop()
            observer.join()
            del self.file_observers[watch_id]
            logger.info(f"✅ File watch removed: {watch_id}")
            return True
        
        # Check email monitors
        if watch_id in self.email_monitors:
            if self.scheduler:
                self.scheduler.remove_task(watch_id)
            del self.email_monitors[watch_id]
            logger.info(f"✅ Email monitor removed: {watch_id}")
            return True
        
        # Check calendar monitors
        if watch_id in self.calendar_monitors:
            del self.calendar_monitors[watch_id]
            logger.info(f"✅ Calendar monitor removed: {watch_id}")
            return True
        
        logger.error(f"❌ Watch not found: {watch_id}")
        return False
    
    def list_watches(self) -> dict:
        """List all active watches."""
        return {
            'file_watches': list(self.file_observers.keys()),
            'email_monitors': list(self.email_monitors.keys()),
            'calendar_monitors': list(self.calendar_monitors.keys())
        }
    
    def shutdown(self):
        """Shutdown all monitors."""
        # Stop file observers
        for observer in self.file_observers.values():
            observer.stop()
            observer.join()
        
        logger.info("🛑 Event Monitor stopped")


# Singleton
_monitor = None

def get_event_monitor(scheduler=None):
    """Get or create the event monitor singleton."""
    global _monitor
    if _monitor is None:
        _monitor = EventMonitor(scheduler)
    return _monitor


if __name__ == "__main__":
    # Quick test
    import time
    logging.basicConfig(level=logging.INFO)
    
    monitor = EventMonitor()
    
    # Test file watching
    test_dir = "test_watch"
    os.makedirs(test_dir, exist_ok=True)
    
    print("\n📋 Testing Event Monitor")
    print("=" * 60)
    
    # Watch test directory
    watch_id = monitor.watch_file(
        test_dir,
        "File event detected: {event} on {file}",
        event_types=['created', 'modified', 'deleted']
    )
    
    print(f"\n✅ Watching: {test_dir}")
    print("   Create/modify/delete files to test...")
    print("   Press Ctrl+C to stop\n")
    
    try:
        # Create test file
        time.sleep(2)
        test_file = os.path.join(test_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Hello ALFRED!")
        
        time.sleep(2)
        
        # Modify test file
        with open(test_file, 'a') as f:
            f.write("\nEvent monitoring works!")
        
        time.sleep(2)
        
        # Delete test file
        os.remove(test_file)
        
        time.sleep(2)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
    
    finally:
        monitor.shutdown()
        os.rmdir(test_dir)
        print("✅ Cleanup complete")
