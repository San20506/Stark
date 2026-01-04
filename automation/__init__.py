"""
STARK Desktop Automation Module
================================
Linux desktop automation capabilities.
"""

from automation.window_control import WindowControl, WindowInfo, get_window_control
from automation.app_launcher import AppLauncher, AppProcess, get_app_launcher
from automation.keyboard_mouse import KeyboardMouse, MouseButton, get_keyboard_mouse

__all__ = [
    'WindowControl',
    'WindowInfo',
    'get_window_control',
    'AppLauncher',
    'AppProcess',
    'get_app_launcher',
    'KeyboardMouse',
    'MouseButton',
    'get_keyboard_mouse',
]
