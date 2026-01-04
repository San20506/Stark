"""
STARK Notifications
====================
Desktop notifications with toast and HUD support.

Module 13 of Phase 2 - Communication
"""

import logging
import threading
import time
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Notification priority levels."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ALERT = "alert"


@dataclass
class Notification:
    """Notification data."""
    title: str
    message: str
    notification_type: NotificationType = NotificationType.INFO
    timestamp: datetime = field(default_factory=datetime.now)
    timeout_seconds: float = 5.0
    sound: bool = False


class ToastNotifier:
    """
    Desktop toast notifications.
    
    Uses plyer for cross-platform support.
    """
    
    def __init__(self):
        self._available = False
        
        try:
            from plyer import notification
            self._plyer = notification
            self._available = True
        except ImportError:
            self._plyer = None
            logger.warning("plyer not installed. Toast notifications disabled.")
    
    def is_available(self) -> bool:
        return self._available
    
    def show(self, notification: Notification) -> bool:
        """Show a toast notification."""
        if not self._available:
            logger.info(f"[TOAST] {notification.title}: {notification.message}")
            return False
        
        try:
            # Map notification type to icon
            icon_map = {
                NotificationType.INFO: None,
                NotificationType.SUCCESS: None,
                NotificationType.WARNING: None,
                NotificationType.ERROR: None,
                NotificationType.ALERT: None,
            }
            
            self._plyer.notify(
                title=notification.title,
                message=notification.message,
                timeout=int(notification.timeout_seconds),
                app_name="STARK",
            )
            return True
        except Exception as e:
            logger.error(f"Toast notification failed: {e}")
            return False


class HUDOverlay:
    """
    Heads-Up Display overlay (backup for toast).
    
    Creates a simple overlay window for notifications.
    Note: Requires GUI framework (tkinter).
    """
    
    def __init__(self):
        self._available = False
        self._window = None
        
        try:
            import tkinter as tk
            self._tk = tk
            self._available = True
        except ImportError:
            self._tk = None
            logger.debug("tkinter not available. HUD overlay disabled.")
    
    def is_available(self) -> bool:
        return self._available
    
    def show(self, notification: Notification) -> bool:
        """Show HUD overlay notification."""
        if not self._available:
            return False
        
        def _show_hud():
            try:
                # Create overlay window
                root = self._tk.Tk()
                root.overrideredirect(True)
                root.attributes('-topmost', True)
                root.attributes('-alpha', 0.9)
                
                # Position at top-right
                screen_width = root.winfo_screenwidth()
                root.geometry(f"300x80+{screen_width - 320}+20")
                
                # Style based on type
                bg_colors = {
                    NotificationType.INFO: "#2196F3",
                    NotificationType.SUCCESS: "#4CAF50",
                    NotificationType.WARNING: "#FF9800",
                    NotificationType.ERROR: "#F44336",
                    NotificationType.ALERT: "#9C27B0",
                }
                bg = bg_colors.get(notification.notification_type, "#333")
                
                # Create content
                frame = self._tk.Frame(root, bg=bg, padx=10, pady=10)
                frame.pack(fill='both', expand=True)
                
                title_label = self._tk.Label(
                    frame,
                    text=notification.title,
                    font=('Arial', 12, 'bold'),
                    fg='white',
                    bg=bg,
                )
                title_label.pack(anchor='w')
                
                msg_label = self._tk.Label(
                    frame,
                    text=notification.message[:100],
                    font=('Arial', 10),
                    fg='white',
                    bg=bg,
                    wraplength=280,
                )
                msg_label.pack(anchor='w')
                
                # Auto-close after timeout
                root.after(int(notification.timeout_seconds * 1000), root.destroy)
                
                root.mainloop()
            except Exception as e:
                logger.error(f"HUD overlay failed: {e}")
        
        # Run in separate thread to not block
        thread = threading.Thread(target=_show_hud, daemon=True)
        thread.start()
        return True


class NotificationManager:
    """
    Unified notification manager.
    
    Features:
    - Toast notifications (primary)
    - HUD overlay (backup)
    - Notification history
    - Proactive alerts
    
    Usage:
        notifier = get_notifier()
        notifier.notify("Hello", "STARK is ready!")
        notifier.alert("Warning", "High CPU usage detected")
    """
    
    def __init__(self, prefer_hud: bool = False):
        """
        Initialize notification manager.
        
        Args:
            prefer_hud: Prefer HUD over toast notifications
        """
        self.toast = ToastNotifier()
        self.hud = HUDOverlay()
        self.prefer_hud = prefer_hud
        
        self._history: List[Notification] = []
        self._max_history = 100
        
        logger.info(f"NotificationManager initialized (toast={self.toast.is_available()}, hud={self.hud.is_available()})")
    
    def notify(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        timeout: float = 5.0,
        sound: bool = False,
    ) -> bool:
        """
        Send a notification.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Priority level
            timeout: Auto-dismiss timeout in seconds
            sound: Play notification sound
        """
        notification = Notification(
            title=title,
            message=message,
            notification_type=notification_type,
            timeout_seconds=timeout,
            sound=sound,
        )
        
        # Add to history
        self._history.append(notification)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        # Show notification
        if self.prefer_hud and self.hud.is_available():
            return self.hud.show(notification)
        elif self.toast.is_available():
            return self.toast.show(notification)
        elif self.hud.is_available():
            return self.hud.show(notification)
        else:
            # Fallback to logging
            logger.info(f"[NOTIFICATION] {title}: {message}")
            return False
    
    def info(self, title: str, message: str) -> bool:
        """Send info notification."""
        return self.notify(title, message, NotificationType.INFO)
    
    def success(self, title: str, message: str) -> bool:
        """Send success notification."""
        return self.notify(title, message, NotificationType.SUCCESS)
    
    def warning(self, title: str, message: str) -> bool:
        """Send warning notification."""
        return self.notify(title, message, NotificationType.WARNING)
    
    def error(self, title: str, message: str) -> bool:
        """Send error notification."""
        return self.notify(title, message, NotificationType.ERROR)
    
    def alert(self, title: str, message: str, sound: bool = True) -> bool:
        """Send alert notification (high priority)."""
        return self.notify(title, message, NotificationType.ALERT, timeout=10.0, sound=sound)
    
    def get_history(self, limit: int = 10) -> List[Notification]:
        """Get recent notification history."""
        return self._history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics."""
        return {
            "toast_available": self.toast.is_available(),
            "hud_available": self.hud.is_available(),
            "prefer_hud": self.prefer_hud,
            "history_count": len(self._history),
        }


# =============================================================================
# FACTORY
# =============================================================================

_notifier_instance: Optional[NotificationManager] = None


def get_notifier(prefer_hud: bool = False) -> NotificationManager:
    """Get or create the global notification manager."""
    global _notifier_instance
    
    if _notifier_instance is None:
        _notifier_instance = NotificationManager(prefer_hud=prefer_hud)
    
    return _notifier_instance
