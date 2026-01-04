"""
STARK Health Monitor
=====================
Monitor user wellbeing with posture detection, break reminders, and activity tracking.

Module 7 of 9 - Capabilities
"""

import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class PostureStatus(Enum):
    """Posture classification."""
    GOOD = "good"
    NEUTRAL = "neutral"
    POOR = "poor"
    UNKNOWN = "unknown"


class AlertType(Enum):
    """Types of health alerts."""
    POSTURE = "posture"
    BREAK = "break"
    EYE_STRAIN = "eye_strain"
    SCREEN_TIME = "screen_time"
    FATIGUE = "fatigue"
    HYDRATION = "hydration"


@dataclass
class HealthAlert:
    """A health-related alert."""
    alert_type: AlertType
    message: str
    severity: str = "info"  # info, warning, critical
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.alert_type.value,
            "message": self.message,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
        }


@dataclass
class HealthStats:
    """Daily health statistics."""
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    screen_time_minutes: float = 0
    breaks_taken: int = 0
    posture_alerts: int = 0
    good_posture_percent: float = 0.0
    last_break_time: Optional[datetime] = None
    session_start: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "screen_time_minutes": round(self.screen_time_minutes, 1),
            "breaks_taken": self.breaks_taken,
            "posture_alerts": self.posture_alerts,
            "good_posture_percent": round(self.good_posture_percent, 1),
            "session_duration_minutes": round(
                (datetime.now() - self.session_start).total_seconds() / 60, 1
            ),
        }


class HealthMonitor:
    """
    Monitor user health and wellness.
    
    Features:
    - Posture status tracking
    - Break reminders (Pomodoro-style)
    - Screen time tracking
    - 20-20-20 eye strain prevention
    - Daily health summaries
    
    Usage:
        monitor = HealthMonitor()
        monitor.start_session()
        
        # Periodically update
        alert = monitor.update()
        if alert:
            print(alert.message)
        
        # Get summary
        print(monitor.get_daily_summary())
    """
    
    # Configuration
    BREAK_INTERVAL_MINUTES = 50
    BREAK_DURATION_MINUTES = 10
    EYE_STRAIN_INTERVAL_MINUTES = 20
    POSTURE_CHECK_INTERVAL_SECONDS = 300  # 5 minutes
    
    def __init__(
        self,
        break_interval: int = BREAK_INTERVAL_MINUTES,
        posture_check_interval: int = POSTURE_CHECK_INTERVAL_SECONDS,
    ):
        """
        Initialize health monitor.
        
        Args:
            break_interval: Minutes between break reminders
            posture_check_interval: Seconds between posture checks
        """
        self.break_interval = break_interval * 60  # Convert to seconds
        self.posture_check_interval = posture_check_interval
        
        # State
        self._active = False
        self._session_start: Optional[datetime] = None
        self._last_break: Optional[datetime] = None
        self._last_posture_check: Optional[datetime] = None
        self._last_eye_reminder: Optional[datetime] = None
        
        # Tracking
        self._posture_history: deque = deque(maxlen=100)
        self._alerts: List[HealthAlert] = []
        self._daily_stats = HealthStats()
        
        # Posture state
        self._current_posture = PostureStatus.UNKNOWN
        self._poor_posture_start: Optional[datetime] = None
        
        logger.info("HealthMonitor initialized")
    
    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================
    
    def start_session(self) -> None:
        """Start a new monitoring session."""
        self._active = True
        self._session_start = datetime.now()
        self._last_break = datetime.now()
        self._last_eye_reminder = datetime.now()
        self._daily_stats = HealthStats()
        
        logger.info("Health monitoring session started")
    
    def end_session(self) -> Dict[str, Any]:
        """End session and return summary."""
        self._active = False
        summary = self.get_daily_summary()
        logger.info("Health monitoring session ended")
        return summary
    
    def is_active(self) -> bool:
        """Check if monitoring is active."""
        return self._active
    
    # =========================================================================
    # UPDATE LOOP
    # =========================================================================
    
    def update(self, posture_status: Optional[PostureStatus] = None) -> Optional[HealthAlert]:
        """
        Update health monitoring and check for alerts.
        
        Args:
            posture_status: Current posture from camera/sensor (optional)
            
        Returns:
            HealthAlert if one should be shown, else None
        """
        if not self._active:
            return None
        
        now = datetime.now()
        
        # Update screen time
        if self._session_start:
            self._daily_stats.screen_time_minutes = (
                now - self._session_start
            ).total_seconds() / 60
        
        # Check for break reminder
        alert = self._check_break_reminder(now)
        if alert:
            return alert
        
        # Check for 20-20-20 eye reminder
        alert = self._check_eye_strain_reminder(now)
        if alert:
            return alert
        
        # Update posture if provided
        if posture_status:
            alert = self._update_posture(posture_status, now)
            if alert:
                return alert
        
        return None
    
    def _check_break_reminder(self, now: datetime) -> Optional[HealthAlert]:
        """Check if user needs a break."""
        if self._last_break is None:
            self._last_break = now
            return None
        
        time_since_break = (now - self._last_break).total_seconds()
        
        if time_since_break >= self.break_interval:
            alert = HealthAlert(
                alert_type=AlertType.BREAK,
                message=f"You've been working for {int(time_since_break/60)} minutes. "
                        f"Time for a {self.BREAK_DURATION_MINUTES}-minute break!",
                severity="warning",
            )
            self._alerts.append(alert)
            return alert
        
        return None
    
    def _check_eye_strain_reminder(self, now: datetime) -> Optional[HealthAlert]:
        """Check for 20-20-20 eye strain prevention."""
        if self._last_eye_reminder is None:
            self._last_eye_reminder = now
            return None
        
        time_since_reminder = (now - self._last_eye_reminder).total_seconds()
        
        if time_since_reminder >= self.EYE_STRAIN_INTERVAL_MINUTES * 60:
            self._last_eye_reminder = now
            
            alert = HealthAlert(
                alert_type=AlertType.EYE_STRAIN,
                message="👁️ 20-20-20: Look at something 20 feet away for 20 seconds",
                severity="info",
            )
            self._alerts.append(alert)
            return alert
        
        return None
    
    def _update_posture(
        self,
        status: PostureStatus,
        now: datetime,
    ) -> Optional[HealthAlert]:
        """Update posture tracking and check for alerts."""
        self._current_posture = status
        self._posture_history.append({
            "status": status,
            "timestamp": now,
        })
        
        # Calculate good posture percentage
        if self._posture_history:
            good_count = sum(
                1 for p in self._posture_history
                if p["status"] == PostureStatus.GOOD
            )
            self._daily_stats.good_posture_percent = (
                good_count / len(self._posture_history) * 100
            )
        
        # Track poor posture duration
        if status == PostureStatus.POOR:
            if self._poor_posture_start is None:
                self._poor_posture_start = now
            else:
                poor_duration = (now - self._poor_posture_start).total_seconds()
                
                # Alert after 5 minutes of poor posture
                if poor_duration >= 300:
                    self._daily_stats.posture_alerts += 1
                    self._poor_posture_start = now  # Reset
                    
                    alert = HealthAlert(
                        alert_type=AlertType.POSTURE,
                        message="⚠️ Your posture has been poor for 5+ minutes. "
                                "Try sitting up straight with shoulders back.",
                        severity="warning",
                    )
                    self._alerts.append(alert)
                    return alert
        else:
            self._poor_posture_start = None
        
        return None
    
    # =========================================================================
    # USER ACTIONS
    # =========================================================================
    
    def take_break(self) -> str:
        """Record that user is taking a break."""
        self._last_break = datetime.now()
        self._daily_stats.breaks_taken += 1
        self._daily_stats.last_break_time = datetime.now()
        
        return f"Break started! You've taken {self._daily_stats.breaks_taken} breaks today. 🎉"
    
    def set_posture(self, status: str) -> str:
        """Manually set posture status."""
        try:
            posture = PostureStatus(status.lower())
            self._update_posture(posture, datetime.now())
            return f"Posture recorded as: {posture.value}"
        except ValueError:
            return f"Unknown posture status: {status}"
    
    def acknowledge_alert(self) -> str:
        """Acknowledge the latest alert."""
        if self._alerts:
            self._alerts[-1].acknowledged = True
            return "Alert acknowledged"
        return "No alerts to acknowledge"
    
    # =========================================================================
    # REPORTING
    # =========================================================================
    
    def get_daily_summary(self) -> Dict[str, Any]:
        """Get daily health summary."""
        return {
            "stats": self._daily_stats.to_dict(),
            "status": {
                "current_posture": self._current_posture.value,
                "session_active": self._active,
            },
            "recommendations": self._get_recommendations(),
        }
    
    def _get_recommendations(self) -> List[str]:
        """Generate personalized recommendations."""
        recs = []
        
        if self._daily_stats.screen_time_minutes > 240:  # 4 hours
            recs.append("Consider taking longer breaks - you've had over 4 hours of screen time")
        
        if self._daily_stats.breaks_taken < 3 and self._daily_stats.screen_time_minutes > 120:
            recs.append("Try to take more frequent breaks - aim for one every 50 minutes")
        
        if self._daily_stats.good_posture_percent < 50:
            recs.append("Focus on maintaining better posture - try a standing desk or ergonomic chair")
        
        if self._daily_stats.posture_alerts > 3:
            recs.append("Multiple posture alerts today - consider stretching exercises")
        
        if not recs:
            recs.append("Great job! Keep up the healthy habits 🌟")
        
        return recs
    
    def get_quick_status(self) -> str:
        """Get quick status message for user queries."""
        stats = self._daily_stats
        
        parts = []
        parts.append(f"📊 **Today's Health Summary**")
        parts.append(f"- Screen time: {stats.screen_time_minutes:.0f} minutes")
        parts.append(f"- Breaks taken: {stats.breaks_taken}")
        parts.append(f"- Posture score: {stats.good_posture_percent:.0f}%")
        
        if stats.last_break_time:
            mins_since = (datetime.now() - stats.last_break_time).total_seconds() / 60
            parts.append(f"- Last break: {mins_since:.0f} minutes ago")
        
        return "\n".join(parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        return {
            "active": self._active,
            "total_alerts": len(self._alerts),
            "daily_stats": self._daily_stats.to_dict(),
            "current_posture": self._current_posture.value,
        }


# =============================================================================
# FACTORY
# =============================================================================

_monitor_instance: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get or create the global health monitor."""
    global _monitor_instance
    
    if _monitor_instance is None:
        _monitor_instance = HealthMonitor()
    
    return _monitor_instance
