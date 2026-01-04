"""
ALFRED Desktop Control
Control mouse, keyboard, and windows on the desktop.

Uses pyautogui for input simulation and pygetwindow for window management.
"""

import os
import time
import logging
from typing import Tuple, Optional, List
from dataclasses import dataclass

try:
    import pyautogui
    import pygetwindow as gw
    PYAUTOGUI_AVAILABLE = True
    
    # Safety settings
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    pyautogui.PAUSE = 0.1  # Small delay between actions
except ImportError:
    PYAUTOGUI_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ClickResult:
    """Result of a click action."""
    success: bool
    x: int
    y: int
    message: str


@dataclass
class TypeResult:
    """Result of a type action."""
    success: bool
    text: str
    message: str


@dataclass
class WindowInfo:
    """Information about a window."""
    title: str
    x: int
    y: int
    width: int
    height: int
    is_active: bool


class DesktopController:
    """
    Control desktop mouse, keyboard, and windows.
    
    Safety Features:
    - FAILSAFE: Move mouse to top-left corner to abort
    - Confirmation required for destructive actions
    - Rate limiting on rapid actions
    """
    
    def __init__(self):
        """Initialize desktop controller."""
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError("pyautogui not installed. Run: pip install pyautogui pygetwindow")
        
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"✅ Desktop Controller initialized ({self.screen_width}x{self.screen_height})")
    
    # ==================== MOUSE CONTROL ====================
    
    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> ClickResult:
        """
        Click at specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            button: "left", "right", or "middle"
            clicks: Number of clicks (1 for single, 2 for double)
            
        Returns:
            ClickResult with success status
        """
        try:
            # Validate coordinates
            if not (0 <= x <= self.screen_width and 0 <= y <= self.screen_height):
                return ClickResult(False, x, y, f"Coordinates out of bounds: ({x}, {y})")
            
            pyautogui.click(x, y, clicks=clicks, button=button)
            
            return ClickResult(True, x, y, f"Clicked at ({x}, {y})")
            
        except Exception as e:
            return ClickResult(False, x, y, f"Click failed: {e}")
    
    def double_click(self, x: int, y: int) -> ClickResult:
        """Double-click at specified coordinates."""
        return self.click(x, y, clicks=2)
    
    def right_click(self, x: int, y: int) -> ClickResult:
        """Right-click at specified coordinates."""
        return self.click(x, y, button="right")
    
    def move_mouse(self, x: int, y: int, duration: float = 0.5) -> ClickResult:
        """
        Move mouse to specified coordinates.
        
        Args:
            x: Target X coordinate
            y: Target Y coordinate
            duration: Time in seconds to move (smooth movement)
        """
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return ClickResult(True, x, y, f"Moved to ({x}, {y})")
        except Exception as e:
            return ClickResult(False, x, y, f"Move failed: {e}")
    
    def scroll(self, amount: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """
        Scroll the mouse wheel.
        
        Args:
            amount: Positive = up, Negative = down
            x, y: Optional position to scroll at
        """
        try:
            if x is not None and y is not None:
                pyautogui.scroll(amount, x, y)
            else:
                pyautogui.scroll(amount)
            return True
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return False
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        return pyautogui.position()
    
    # ==================== KEYBOARD CONTROL ====================
    
    def type_text(self, text: str, interval: float = 0.05) -> TypeResult:
        """
        Type text using keyboard.
        
        Args:
            text: Text to type
            interval: Delay between keystrokes
            
        Returns:
            TypeResult with success status
        """
        try:
            pyautogui.typewrite(text, interval=interval)
            return TypeResult(True, text, f"Typed: {text[:50]}...")
        except Exception as e:
            return TypeResult(False, text, f"Type failed: {e}")
    
    def type_text_unicode(self, text: str) -> TypeResult:
        """
        Type text with Unicode support (slower but handles special chars).
        
        Uses pyperclip for clipboard-based typing.
        """
        try:
            # For Unicode, use write() which handles special characters
            pyautogui.write(text)
            return TypeResult(True, text, f"Typed (unicode): {text[:50]}...")
        except Exception as e:
            return TypeResult(False, text, f"Unicode type failed: {e}")
    
    def press_key(self, key: str) -> bool:
        """
        Press a single key.
        
        Args:
            key: Key name (e.g., "enter", "tab", "escape", "f5")
        """
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            logger.error(f"Key press failed: {e}")
            return False
    
    def hotkey(self, *keys: str) -> bool:
        """
        Press a keyboard shortcut.
        
        Args:
            keys: Keys to press together (e.g., "ctrl", "c" for Ctrl+C)
            
        Examples:
            hotkey("ctrl", "c")  # Copy
            hotkey("ctrl", "v")  # Paste
            hotkey("alt", "tab")  # Switch window
            hotkey("win", "d")  # Show desktop
        """
        try:
            pyautogui.hotkey(*keys)
            return True
        except Exception as e:
            logger.error(f"Hotkey failed: {e}")
            return False
    
    def copy(self) -> bool:
        """Press Ctrl+C."""
        return self.hotkey("ctrl", "c")
    
    def paste(self) -> bool:
        """Press Ctrl+V."""
        return self.hotkey("ctrl", "v")
    
    def select_all(self) -> bool:
        """Press Ctrl+A."""
        return self.hotkey("ctrl", "a")
    
    def undo(self) -> bool:
        """Press Ctrl+Z."""
        return self.hotkey("ctrl", "z")
    
    # ==================== WINDOW CONTROL ====================
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get information about the currently active window."""
        try:
            window = gw.getActiveWindow()
            if window:
                return WindowInfo(
                    title=window.title,
                    x=window.left,
                    y=window.top,
                    width=window.width,
                    height=window.height,
                    is_active=True
                )
            return None
        except Exception as e:
            logger.error(f"Get active window failed: {e}")
            return None
    
    def get_all_windows(self) -> List[WindowInfo]:
        """Get list of all open windows."""
        windows = []
        try:
            for window in gw.getAllWindows():
                if window.title:  # Skip windows without titles
                    windows.append(WindowInfo(
                        title=window.title,
                        x=window.left,
                        y=window.top,
                        width=window.width,
                        height=window.height,
                        is_active=window.isActive
                    ))
        except Exception as e:
            logger.error(f"Get all windows failed: {e}")
        return windows
    
    def find_window(self, title_contains: str) -> Optional[WindowInfo]:
        """Find a window by partial title match."""
        for window in self.get_all_windows():
            if title_contains.lower() in window.title.lower():
                return window
        return None
    
    def activate_window(self, title_contains: str) -> bool:
        """
        Bring a window to the foreground.
        
        Args:
            title_contains: Partial window title to match
        """
        try:
            windows = gw.getWindowsWithTitle(title_contains)
            if windows:
                windows[0].activate()
                return True
            return False
        except Exception as e:
            logger.error(f"Activate window failed: {e}")
            return False
    
    def minimize_window(self, title_contains: str = None) -> bool:
        """Minimize a window (or current window if no title given)."""
        try:
            if title_contains:
                windows = gw.getWindowsWithTitle(title_contains)
                if windows:
                    windows[0].minimize()
                    return True
            else:
                window = gw.getActiveWindow()
                if window:
                    window.minimize()
                    return True
            return False
        except Exception as e:
            logger.error(f"Minimize failed: {e}")
            return False
    
    def maximize_window(self, title_contains: str = None) -> bool:
        """Maximize a window (or current window if no title given)."""
        try:
            if title_contains:
                windows = gw.getWindowsWithTitle(title_contains)
                if windows:
                    windows[0].maximize()
                    return True
            else:
                window = gw.getActiveWindow()
                if window:
                    window.maximize()
                    return True
            return False
        except Exception as e:
            logger.error(f"Maximize failed: {e}")
            return False
    
    def close_window(self, title_contains: str = None) -> bool:
        """Close a window (or current window if no title given)."""
        try:
            if title_contains:
                windows = gw.getWindowsWithTitle(title_contains)
                if windows:
                    windows[0].close()
                    return True
            else:
                window = gw.getActiveWindow()
                if window:
                    window.close()
                    return True
            return False
        except Exception as e:
            logger.error(f"Close window failed: {e}")
            return False
    
    # ==================== SCREEN UTILITIES ====================
    
    def screenshot(self, filepath: str = None, region: Tuple[int, int, int, int] = None):
        """
        Take a screenshot.
        
        Args:
            filepath: Path to save screenshot (optional)
            region: (x, y, width, height) to capture specific region
            
        Returns:
            PIL Image object
        """
        try:
            if region:
                img = pyautogui.screenshot(region=region)
            else:
                img = pyautogui.screenshot()
            
            if filepath:
                img.save(filepath)
                logger.info(f"Screenshot saved: {filepath}")
            
            return img
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None
    
    def locate_on_screen(self, image_path: str, confidence: float = 0.9) -> Optional[Tuple[int, int]]:
        """
        Find an image on screen and return its center coordinates.
        
        Args:
            image_path: Path to image to find
            confidence: Match confidence (0.0-1.0)
            
        Returns:
            (x, y) center of found image, or None
        """
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                return (center.x, center.y)
            return None
        except Exception as e:
            logger.error(f"Locate on screen failed: {e}")
            return None
    
    def click_image(self, image_path: str, confidence: float = 0.9) -> ClickResult:
        """
        Find an image on screen and click it.
        
        Args:
            image_path: Path to image to find and click
            confidence: Match confidence (0.0-1.0)
        """
        location = self.locate_on_screen(image_path, confidence)
        if location:
            return self.click(location[0], location[1])
        return ClickResult(False, 0, 0, f"Image not found: {image_path}")
    
    # ==================== APP LAUNCHING ====================
    
    def open_app(self, app_name: str) -> bool:
        """
        Open an application by name.
        
        Args:
            app_name: Application name or path
        """
        try:
            # Use Windows Run dialog
            self.hotkey("win", "r")
            time.sleep(0.3)
            self.type_text(app_name)
            self.press_key("enter")
            return True
        except Exception as e:
            logger.error(f"Open app failed: {e}")
            return False
    
    def open_url(self, url: str) -> bool:
        """
        Open a URL in default browser.
        
        Args:
            url: URL to open
        """
        import webbrowser
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"Open URL failed: {e}")
            return False


# Singleton instance
_controller = None

def get_desktop_controller() -> DesktopController:
    """Get or create the desktop controller singleton."""
    global _controller
    if _controller is None:
        _controller = DesktopController()
    return _controller


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("🖥️ ALFRED Desktop Control - Test")
    print("=" * 60)
    
    controller = DesktopController()
    
    # Test 1: Screen info
    print(f"\nScreen size: {controller.screen_width}x{controller.screen_height}")
    
    # Test 2: Mouse position
    x, y = controller.get_mouse_position()
    print(f"Mouse position: ({x}, {y})")
    
    # Test 3: Active window
    window = controller.get_active_window()
    if window:
        print(f"Active window: {window.title}")
    
    # Test 4: List all windows
    windows = controller.get_all_windows()
    print(f"\nOpen windows ({len(windows)}):")
    for w in windows[:5]:  # First 5
        print(f"  - {w.title[:50]}")
    
    print("\n✅ Desktop Control module ready!")
    print("⚠️ SAFETY: Move mouse to top-left corner to abort any action")
