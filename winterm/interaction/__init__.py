"""Windows Interaction & GUI Automation Module.

Provides robust keyboard input, mouse movements/clicks/scrolls, pen/touch continuous parametric paths,
universal application discovery and lifecycle management, Win32 window positioning/state control,
and .NET System.Windows.Automation element inspection and interaction.
"""

from winterm.interaction.keyboard import KeyboardEngine
from winterm.interaction.mouse import MouseEngine
from winterm.interaction.pen_touch import PenTouchEngine
from winterm.interaction.app_manager import WindowsAppManager
from winterm.interaction.window_manager import WindowManager
from winterm.interaction.ui_automation import UIAutomationEngine

__all__ = [
    "KeyboardEngine",
    "MouseEngine",
    "PenTouchEngine",
    "WindowsAppManager",
    "WindowManager",
    "UIAutomationEngine",
]
