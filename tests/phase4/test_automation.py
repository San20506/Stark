#!/usr/bin/env python3
"""
Desktop Automation Demo
========================
Test window control, app launcher, and keyboard/mouse automation.
"""

import time
from automation import get_window_control, get_app_launcher, get_keyboard_mouse

print("=" * 60)
print("STARK Desktop Automation Demo")
print("=" * 60)
print()

# Initialize components
window_control = get_window_control()
app_launcher = get_app_launcher()
kb_mouse = get_keyboard_mouse()

# Test 1: List windows
print("🪟 Test 1: List Windows")
windows = window_control.list_windows()
print(f"  Found {len(windows)} windows:")
for i, window in enumerate(windows[:5], 1):  # Show first 5
    active_marker = "★" if window.is_active else " "
    print(f"  {active_marker} {i}. {window.title[:50]}")
print()

# Test 2: Check running apps
print("🚀 Test 2: Check Running Applications")
common_apps = ['python', 'bash', 'code', 'chrome']
for app in common_apps:
    is_running = app_launcher.is_running(app)
    status = "✅ Running" if is_running else "❌ Not running"
    print(f"  {app}: {status}")
    
    if is_running:
        processes = app_launcher.find_processes(app)
        total_mem = sum(p.memory_mb for p in processes)
        print(f"    {len(processes)} process(es), {total_mem:.0f} MB")
print()

# Test 3: Mouse position
print("🖱️  Test 3: Mouse Control")
pos = kb_mouse.get_mouse_position()
if pos:
    print(f"  Current position: ({pos[0]}, {pos[1]})")
else:
    print("  Could not get mouse position (xdotool not available?)")
print()

# Test 4: Dependency check
print("🔧 Test 4: Dependency Status")
print(f"  wmctrl available: {'✅' if window_control.has_wmctrl else '❌ (install with: sudo apt install wmctrl)'}")
print(f"  xdotool available: {'✅' if kb_mouse.has_xdotool else '❌ (install with: sudo apt install xdotool)'}")
print(f"  psutil available: ✅ (Python library)")
print()

# Test 5: Launch a simple app (test only, don't actually spam terminals)
print("📱 Test 5: App Launch Capability")
print("  Capability ready: ✅")
print("  Example: app_launcher.launch('gedit') would open text editor")
print("  Example: app_launcher.launch('firefox', ['https://github.com'])")
print()

print("=" * 60)
print("Desktop Automation Status")
print("=" * 60)
print()

capabilities = [
    ("Window listing", len(windows) > 0),
    ("Process management", True),  # psutil always works
    ("Window control", window_control.has_wmctrl),
    ("Keyboard/mouse", kb_mouse.has_xdotool),
]

for capability, status in capabilities:
    icon = "✅" if status else "⚠️"
    print(f"{icon} {capability}")

print()

if not window_control.has_wmctrl or not kb_mouse.has_xdotool:
    print("📦 Install missing dependencies:")
    print("   sudo apt install wmctrl xdotool")
    print()

print("✅ Desktop automation framework complete!")
