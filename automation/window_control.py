"""
STARK Desktop Automation - Window Control
==========================================
Linux window management (X11 and Wayland support).

Capabilities:
- List windows
- Focus/activate windows
- Move/resize windows
- Get window info
- Close windows
"""

import logging
import subprocess
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WindowInfo:
    """Information about a window."""
    window_id: str
    title: str
    app_name: str
    desktop: int
    geometry: Tuple[int, int, int, int]  # x, y, width, height
    is_active: bool = False


class WindowControl:
    """
    Control windows on Linux desktop.
    
    Uses wmctrl for X11 and some Wayland compositors.
    Fallback methods for pure Wayland environments.
    """
    
    def __init__(self):
        """Initialize window controller."""
        self._check_dependencies()
        self.display_server = self._detect_display_server()
        logger.info(f"WindowControl initialized ({self.display_server})")
    
    def _check_dependencies(self):
        """Check if required tools are available."""
        try:
            subprocess.run(['wmctrl', '-h'], capture_output=True, check=False)
            self.has_wmctrl = True
        except FileNotFoundError:
            self.has_wmctrl = False
            logger.warning("wmctrl not found - limited window control")
        
        try:
            subprocess.run(['xdotool', '--version'], capture_output=True, check=False)
            self.has_xdotool = True
        except FileNotFoundError:
            self.has_xdotool = False
            logger.warning("xdotool not found - limited input control")
    
    def _detect_display_server(self) -> str:
        """Detect if running X11 or Wayland."""
        import os
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        
        if 'wayland' in session_type:
            return 'wayland'
        elif 'x11' in session_type or os.environ.get('DISPLAY'):
            return 'x11'
        else:
            return 'unknown'
    
    def list_windows(self) -> List[WindowInfo]:
        """
        List all windows.
        
        Returns:
            List of WindowInfo objects
        """
        if not self.has_wmctrl:
            logger.error("wmctrl not available")
            return []
        
        try:
            result = subprocess.run(
                ['wmctrl', '-l', '-G', '-p'],
                capture_output=True,
                text=True,
                check=True
            )
            
            windows = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                # Parse wmctrl output
                # Format: window_id desktop pid x y w h hostname title
                parts = line.split(None, 8)
                if len(parts) < 9:
                    continue
                
                window = WindowInfo(
                    window_id=parts[0],
                    desktop=int(parts[1]),
                    geometry=(int(parts[3]), int(parts[4]), int(parts[5]), int(parts[6])),
                    app_name=parts[7],
                    title=parts[8],
                )
                windows.append(window)
            
            # Mark active window
            active_id = self.get_active_window_id()
            for window in windows:
                window.is_active = (window.window_id == active_id)
            
            return windows
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list windows: {e}")
            return []
    
    def get_active_window_id(self) -> Optional[str]:
        """Get the active window ID."""
        if not self.has_xdotool:
            return None
        
        try:
            result = subprocess.run(
                ['xdotool', 'getactivewindow'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def focus_window(self, window_id: str) -> bool:
        """
        Focus a window by ID.
        
        Args:
            window_id: Window ID (hex format)
            
        Returns:
            True if successful
        """
        if not self.has_wmctrl:
            return False
        
        try:
            subprocess.run(
                ['wmctrl', '-i', '-a', window_id],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to focus window: {e}")
            return False
    
    def focus_window_by_title(self, title: str, partial: bool = True) -> bool:
        """
        Focus a window by title.
        
        Args:
            title: Window title (or part of it)
            partial: Allow partial match
            
        Returns:
            True if successful
        """
        windows = self.list_windows()
        
        for window in windows:
            if partial:
                if title.lower() in window.title.lower():
                    return self.focus_window(window.window_id)
            else:
                if title == window.title:
                    return self.focus_window(window.window_id)
        
        return False
    
    def close_window(self, window_id: str, graceful: bool = True) -> bool:
        """
        Close a window.
        
        Args:
            window_id: Window ID
            graceful: Use graceful close (True) or force kill (False)
            
        Returns:
            True if successful
        """
        if not self.has_wmctrl:
            return False
        
        try:
            if graceful:
                subprocess.run(
                    ['wmctrl', '-i', '-c', window_id],
                    check=True,
                    capture_output=True
                )
            else:
                # Get PID and kill
                windows = self.list_windows()
                for window in windows:
                    if window.window_id == window_id:
                        subprocess.run(['kill', '-9', str(window.desktop)], check=True)
                        return True
                return False
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to close window: {e}")
            return False
    
    def move_window(self, window_id: str, x: int, y: int) -> bool:
        """
        Move window to position.
        
        Args:
            window_id: Window ID
            x, y: New position
            
        Returns:
            True if successful
        """
        if not self.has_wmctrl:
            return False
        
        try:
            subprocess.run(
                ['wmctrl', '-i', '-r', window_id, '-e', f'0,{x},{y},-1,-1'],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to move window: {e}")
            return False
    
    def resize_window(self, window_id: str, width: int, height: int) -> bool:
        """
        Resize window.
        
        Args:
            window_id: Window ID
            width, height: New size
            
        Returns:
            True if successful
        """
        if not self.has_wmctrl:
            return False
        
        try:
            subprocess.run(
                ['wmctrl', '-i', '-r', window_id, '-e', f'0,-1,-1,{width},{height}'],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to resize window: {e}")
            return False
    
    def get_window_info(self, window_id: str) -> Optional[WindowInfo]:
        """
        Get info for a specific window.
        
        Args:
            window_id: Window ID
            
        Returns:
            WindowInfo or None
        """
        windows = self.list_windows()
        for window in windows:
            if window.window_id == window_id:
                return window
        return None


# =============================================================================
# SINGLETON
# =============================================================================

_window_control_instance: Optional[WindowControl] = None


def get_window_control() -> WindowControl:
    """Get or create the global window controller."""
    global _window_control_instance
    
    if _window_control_instance is None:
        _window_control_instance = WindowControl()
    
    return _window_control_instance
