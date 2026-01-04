"""
STARK Desktop Automation - Keyboard & Mouse
============================================
Simulated keyboard and mouse input for Linux.

Capabilities:
- Type text
- Press keys/shortcuts
- Move mouse
- Click mouse buttons
- Scroll
"""

import logging
import subprocess
import time
from typing import Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class MouseButton(Enum):
    """Mouse button identifiers."""
    LEFT = 1
    MIDDLE = 2
    RIGHT = 3
    SCROLL_UP = 4
    SCROLL_DOWN = 5


class KeyboardMouse:
    """
    Keyboard and mouse automation using xdotool.
    
    Requires xdotool to be installed:
        sudo apt install xdotool
    """
    
    def __init__(self):
        """Initialize keyboard/mouse controller."""
        self._check_dependencies()
        logger.info("KeyboardMouse initialized")
    
    def _check_dependencies(self):
        """Check if xdotool is available."""
        try:
            subprocess.run(['xdotool', '--version'], capture_output=True, check=True)
            self.has_xdotool = True
        except (FileNotFoundError, subprocess.CalledProcessError):
            self.has_xdotool = False
            logger.error("xdotool not found - keyboard/mouse automation unavailable")
    
    # =========================================================================
    # KEYBOARD
    # =========================================================================
    
    def type_text(self, text: str, delay_ms: int = 12) -> bool:
        """
        Type text as if from keyboard.
        
        Args:
            text: Text to type
            delay_ms: Delay between keystrokes (milliseconds)
            
        Returns:
            True if successful
        """
        if not self.has_xdotool:
            return False
        
        try:
            subprocess.run(
                ['xdotool', 'type', '--delay', str(delay_ms), text],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to type text: {e}")
            return False
    
    def press_key(self, key: str) -> bool:
        """
        Press a key or key combination.
        
        Args:
            key: Key name or combination (e.g., 'Return', 'ctrl+c', 'alt+Tab')
            
        Returns:
            True if successful
        """
        if not self.has_xdotool:
            return False
        
        try:
            subprocess.run(
                ['xdotool', 'key', key],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to press key {key}: {e}")
            return False
    
    def press_keys(self, *keys: str, delay_ms: int = 100) -> bool:
        """
        Press multiple keys in sequence.
        
        Args:
            *keys: Key names to press
            delay_ms: Delay between key presses
            
        Returns:
            True if all successful
        """
        success = True
        for key in keys:
            if not self.press_key(key):
                success = False
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)
        return success
    
    # =========================================================================
    # MOUSE
    # =========================================================================
    
    def move_mouse(self, x: int, y: int, relative: bool = False) -> bool:
        """
        Move mouse cursor.
        
        Args:
            x, y: Target position
            relative: Move relative to current position
            
        Returns:
            True if successful
        """
        if not self.has_xdotool:
            return False
        
        try:
            if relative:
                subprocess.run(
                    ['xdotool', 'mousemove_relative', str(x), str(y)],
                    check=True,
                    capture_output=True
                )
            else:
                subprocess.run(
                    ['xdotool', 'mousemove', str(x), str(y)],
                    check=True,
                    capture_output=True
                )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to move mouse: {e}")
            return False
    
    def click(self, button: MouseButton = MouseButton.LEFT, repeat: int = 1) -> bool:
        """
        Click mouse button.
        
        Args:
            button: Mouse button to click
            repeat: Number of clicks
            
        Returns:
            True if successful
        """
        if not self.has_xdotool:
            return False
        
        try:
            subprocess.run(
                ['xdotool', 'click', '--repeat', str(repeat), str(button.value)],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to click: {e}")
            return False
    
    def double_click(self) -> bool:
        """Double-click left mouse button."""
        return self.click(MouseButton.LEFT, repeat=2)
    
    def right_click(self) -> bool:
        """Right-click mouse button."""
        return self.click(MouseButton.RIGHT)
    
    def scroll(self, direction: str, amount: int = 1) -> bool:
        """
        Scroll mouse wheel.
        
        Args:
            direction: 'up' or 'down'
            amount: Number of scroll units
            
        Returns:
            True if successful
        """
        button = MouseButton.SCROLL_UP if direction == 'up' else MouseButton.SCROLL_DOWN
        return self.click(button, repeat=amount)
    
    def get_mouse_position(self) -> Optional[Tuple[int, int]]:
        """
        Get current mouse position.
        
        Returns:
            (x, y) tuple or None
        """
        if not self.has_xdotool:
            return None
        
        try:
            result = subprocess.run(
                ['xdotool', 'getmouselocation', '--shell'],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output: X=123\nY=456\n...
            lines = result.stdout.strip().split('\n')
            x = int(lines[0].split('=')[1])
            y = int(lines[1].split('=')[1])
            
            return (x, y)
        except (subprocess.CalledProcessError, IndexError, ValueError) as e:
            logger.error(f"Failed to get mouse position: {e}")
            return None
    
    # =========================================================================
    # HIGH-LEVEL ACTIONS
    # =========================================================================
    
    def click_at(self, x: int, y: int, button: MouseButton = MouseButton.LEFT) -> bool:
        """
        Move to position and click.
        
        Args:
            x, y: Position to click
            button: Mouse button
            
        Returns:
            True if successful
        """
        if self.move_mouse(x, y):
            time.sleep(0.05)  # Brief pause
            return self.click(button)
        return False
    
    def open_app_menu(self) -> bool:
        """Open application menu (Super key)."""
        return self.press_key('super')
    
    def switch_window(self) -> bool:
        """Switch windows (Alt+Tab)."""
        return self.press_key('alt+Tab')
    
    def copy(self) -> bool:
        """Copy to clipboard (Ctrl+C)."""
        return self.press_key('ctrl+c')
    
    def paste(self) -> bool:
        """Paste from clipboard (Ctrl+V)."""
        return self.press_key('ctrl+v')
    
    def save(self) -> bool:
        """Save current file (Ctrl+S)."""
        return self.press_key('ctrl+s')


# =============================================================================
# SINGLETON
# =============================================================================

_keyboard_mouse_instance: Optional[KeyboardMouse] = None


def get_keyboard_mouse() -> KeyboardMouse:
    """Get or create the global keyboard/mouse controller."""
    global _keyboard_mouse_instance
    
    if _keyboard_mouse_instance is None:
        _keyboard_mouse_instance = KeyboardMouse()
    
    return _keyboard_mouse_instance
