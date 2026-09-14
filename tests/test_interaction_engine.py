"""
Comprehensive unit tests for the Windows Operations & Interaction Subsystem, Cognition Learner, and Agent GUI capabilities.
Tests:
- KeyboardEngine (escaping, type command, Win hotkeys, SendKeys hotkeys, press key)
- MouseEngine (move cursor, smooth move, clicks, drag and drop, wheel scrolling)
- PenTouchEngine (parametric circle, rectangle, line generators, continuous pointer stroke)
- WindowsAppManager (appsfolder/registry/start menu search, win32/uwp/uri launch, graceful/force close)
- WindowManager (window enumeration, force foreground, resize & move, close)
- UIAutomationEngine (element inspection, invoke/coordinate clicking, text setting)
- AppLearner (multi-strategy local probing, KG cross-referencing, web learning guidance, comprehensive learn)
- DesktopGuiSubsystem (PlanStep generation & multi-step plans)
- WinTermAgent (convenience GUI methods with dry_run support, planner intent routing)
"""

import pytest
from winterm.interaction.keyboard import KeyboardEngine
from winterm.interaction.mouse import MouseEngine
from winterm.interaction.pen_touch import PenTouchEngine
from winterm.interaction.app_manager import WindowsAppManager
from winterm.interaction.window_manager import WindowManager
from winterm.interaction.ui_automation import UIAutomationEngine
from winterm.cognition.app_learner import AppLearner
from winterm.subsystems.desktop_gui import DesktopGuiSubsystem
from winterm.agent.winterm_agent import WinTermAgent


# ==============================================================================
# 1. KeyboardEngine Tests
# ==============================================================================

def test_keyboard_escape_sendkeys():
    engine = KeyboardEngine()
    raw = "Hello + World ^ 100% {Test} ~ (Ok)"
    escaped = engine.escape_for_sendkeys(raw)
    assert "{+}" in escaped
    assert "{^}" in escaped
    assert "{%}" in escaped
    assert "{~}" in escaped
    assert "{(}" in escaped
    assert "{)}" in escaped
    # Also test alias
    assert engine.escape_sendkeys(raw) == escaped


def test_keyboard_type_text():
    engine = KeyboardEngine()
    script = engine.build_type_text_command("notepad.exe", delay_ms=20)
    assert "TypeUnicode" in script
    assert "notepad.exe" in script
    # Test alias
    script_alias = engine.build_type_command("notepad.exe", interval_ms=20)
    assert "TypeUnicode" in script_alias


def test_keyboard_hotkeys():
    engine = KeyboardEngine()
    ctrl_c = engine.build_hotkey_command(["ctrl", "c"])
    assert "SendHotkey" in ctrl_c
    assert "ctrl" in ctrl_c

    # Win+R combination via SendHotkey / keybd_event
    win_r = engine.build_hotkey_command(["win", "r"])
    assert "SendHotkey" in win_r
    assert "win" in win_r

    # Single-key repetition
    enter_script = engine.build_press_key_command("enter", count=3)
    assert "{ENTER 3}" in enter_script


# ==============================================================================
# 2. MouseEngine Tests
# ==============================================================================

def test_mouse_move():
    engine = MouseEngine()
    direct_move = engine.build_move_command(500, 300, smooth=False)
    assert "SetPos(500, 300)" in direct_move

    smooth_move = engine.build_move_command(800, 600, smooth=True, steps=15)
    assert "SetPos(800, 600)" in smooth_move


def test_mouse_click_and_drag():
    engine = MouseEngine()
    # Left click at current position
    click_script = engine.build_click_command(button="left")
    assert "Win32MouseCore]::Click" in click_script
    assert "0x0002" in click_script  # MOUSEEVENTF_LEFTDOWN

    # Right double click at specific coordinates
    rclick = engine.build_click_command(x=400, y=200, button="right", double_click=True)
    assert "400, 200" in rclick
    assert "0x0008" in rclick  # MOUSEEVENTF_RIGHTDOWN
    assert "2" in rclick  # 2 clicks

    # Drag
    drag = engine.build_drag_and_drop_command(100, 100, 300, 300, steps=10)
    assert "mouse_event" in drag
    assert "SetCursorPos" in drag


def test_mouse_scroll():
    engine = MouseEngine()
    v_scroll = engine.build_scroll_command(amount=-1)
    assert "mouse_event(0x0800" in v_scroll

    h_scroll = engine.build_scroll_command(amount=1, horizontal=True)
    assert "mouse_event(0x1000" in h_scroll


# ==============================================================================
# 3. PenTouchEngine Tests
# ==============================================================================

def test_pen_touch_parametric_geometry():
    engine = PenTouchEngine()

    # Circle points
    circle = engine.generate_circle_points(500, 500, radius=100, steps=32)
    assert len(circle) == 33  # 32 steps closes loop
    assert circle[0] == (600, 500)  # cos(0)=1 -> cx + r = 600

    # Rectangle points
    rect = engine.generate_rectangle_points(100, 100, 200, 100)
    assert len(rect) == 5
    assert rect[0] == (100, 100)
    assert rect[-1] == (100, 100)

    # Line points
    line = engine.generate_line_points(0, 0, 100, 100, steps=10)
    assert len(line) == 11
    assert line[0] == (0, 0)
    assert line[-1] == (100, 100)


def test_pen_touch_stroke_generation():
    engine = PenTouchEngine()
    points = [(100, 100), (120, 120), (150, 150)]
    stroke_script = engine.build_stroke_command(points, delay_ms=10)
    assert "mouse_event(0x0002" in stroke_script  # Pen touch down
    assert "SetCursorPos(100, 100)" in stroke_script
    assert "SetCursorPos(120, 120)" in stroke_script
    assert "SetCursorPos(150, 150)" in stroke_script
    assert "mouse_event(0x0004" in stroke_script  # Pen touch up


# ==============================================================================
# 4. WindowsAppManager Tests
# ==============================================================================

def test_app_manager_search():
    mgr = WindowsAppManager()
    script = mgr.build_search_command("paint")
    assert "shell:AppsFolder" in script
    assert "App Paths" in script
    assert "paint" in script.lower()


def test_app_manager_launch():
    mgr = WindowsAppManager()
    # Win32/Executable
    win32_launch = mgr.build_launch_command("notepad.exe", arguments="file.txt")
    assert "Start-Process" in win32_launch
    assert "notepad.exe" in win32_launch
    assert "file.txt" in win32_launch

    # UWP AUMID
    uwp_launch = mgr.build_launch_command("Microsoft.Paint_8wekyb3d8bbwe!App")
    assert "shell:AppsFolder" in uwp_launch
    assert "Microsoft.Paint_8wekyb3d8bbwe!App" in uwp_launch

    # Protocol URI
    uri_launch = mgr.build_launch_command("ms-settings:sound")
    assert "ms-settings:sound" in uri_launch


def test_app_manager_close():
    mgr = WindowsAppManager()
    graceful = mgr.build_close_command("notepad")
    assert "CloseMainWindow()" in graceful
    assert "notepad" in graceful

    forced = mgr.build_close_command("notepad", force=True)
    assert "Stop-Process -Force" in forced


# ==============================================================================
# 5. WindowManager Tests
# ==============================================================================

def test_window_manager_list():
    mgr = WindowManager()
    script = mgr.build_list_windows_command()
    assert "EnumDesktopWindows" in script
    assert "OpenInputDesktop" in script
    assert "GetWindowText" in script
    assert "GetWindowRect" in script


def test_window_manager_focus():
    mgr = WindowManager()
    script_by_name = mgr.build_focus_command("Paint")
    assert "Paint" in script_by_name
    assert "ForceForeground" in script_by_name

    script_by_handle = mgr.build_focus_command(65536)
    assert "65536" in script_by_handle


def test_window_manager_resize_move():
    mgr = WindowManager()
    script = mgr.build_resize_move_command("Paint", 100, 100, 1024, 768)
    assert "ResizeMoveWindow" in script
    assert "100" in script
    assert "1024" in script
    assert "768" in script


# ==============================================================================
# 6. UIAutomationEngine Tests
# ==============================================================================

def test_ui_automation_inspect():
    uia = UIAutomationEngine()
    script = uia.build_inspect_elements_command("Calculator", max_items=50)
    assert "System.Windows.Automation" in script
    assert "Calculator" in script
    assert "max_items" not in script  # formatted as number
    assert "50" in script


def test_ui_automation_click():
    uia = UIAutomationEngine()
    script = uia.build_click_element_command("Calculator", element_query="Five")
    assert "System.Windows.Automation" in script
    assert "InvokePattern" in script
    assert "mouse_event" in script  # Coordinate fallback


def test_ui_automation_set_text():
    uia = UIAutomationEngine()
    script = uia.build_set_element_text_command("Notepad", "Edit", "Automated Agent Output")
    assert "System.Windows.Automation" in script
    assert "ValuePattern" in script
    assert "Automated Agent Output" in script


# ==============================================================================
# 7. AppLearner Tests
# ==============================================================================

def test_app_learner_local_probe():
    learner = AppLearner()
    # Test on a core built-in tool that always outputs fast help on Windows: 'where'
    info = learner.probe_local_help("where")
    assert info is not None
    assert info.target == "where"
    assert len(info.raw_help) > 0
    assert len(info.options) > 0


def test_app_learner_graph_cross_reference():
    learner = AppLearner()
    results = learner.cross_reference_knowledge_graph("netsh")
    assert "is_indexed_in_graph" in results
    assert "alternatives" in results


def test_app_learner_web_guidance():
    learner = AppLearner()
    guidance = learner.generate_web_learning_guidance("mspaint", topic="automation shortcuts")
    assert guidance["target"] == "mspaint"
    assert len(guidance["recommended_queries"]) >= 3
    assert any("mspaint" in q for q in guidance["recommended_queries"])


def test_app_learner_comprehensive_learn():
    learner = AppLearner()
    learning = learner.learn("ping")
    assert learning["target"] == "ping"
    assert learning["local_help"]["available"] is True
    assert "knowledge_graph_matches" in learning
    assert "web_learning" in learning


# ==============================================================================
# 8. DesktopGuiSubsystem Integration Tests
# ==============================================================================

def test_desktop_gui_subsystem_plans():
    gui = DesktopGuiSubsystem()

    # App discovery plan
    find_steps = gui.plan_find_apps("code")
    assert len(find_steps) == 1
    assert "code" in find_steps[0].command

    # Launch plan
    launch_steps = gui.plan_launch_app("calc.exe")
    assert len(launch_steps) == 1
    assert "calc.exe" in launch_steps[0].command

    # Window management plan
    win_steps = gui.plan_list_windows()
    assert len(win_steps) == 1
    assert "EnumDesktopWindows" in win_steps[0].command

    # Focus plan
    focus_steps = gui.plan_focus_window("Edge")
    assert len(focus_steps) == 1
    assert "ResolveWindow" in focus_steps[0].command

    # Typing plan
    type_steps = gui.plan_type_text("echo test")
    assert len(type_steps) == 1
    assert "TypeUnicode" in type_steps[0].command

    # Geometric drawing plan
    draw_steps = gui.plan_draw_shape("circle", cx=400, cy=400, radius=50)
    assert len(draw_steps) == 1
    assert "mouse_event" in draw_steps[0].command


# ==============================================================================
# 9. WinTermAgent Convenience Methods & Planner Routing Tests
# ==============================================================================

def test_agent_interaction_methods_dry_run():
    agent = WinTermAgent()

    # find_applications dry run
    res, _, _ = agent.find_applications("notepad", dry_run=True)
    assert res.success is True
    assert "[DRY-RUN]" in res.stdout

    # launch_application dry run
    res, _, _ = agent.launch_application("notepad.exe", dry_run=True)
    assert res.success is True
    assert "[DRY-RUN]" in res.stdout

    # list_windows dry run
    res, _, _ = agent.list_windows(dry_run=True)
    assert res.success is True
    assert "[DRY-RUN]" in res.stdout

    # mouse_click dry run
    res, _, _ = agent.mouse_click(100, 100, "left", dry_run=True)
    assert res.success is True
    assert "[DRY-RUN]" in res.stdout

    # pen_draw_path dry run
    res, _, _ = agent.pen_draw_path([(10, 10), (20, 20)], dry_run=True)
    assert res.success is True
    assert "[DRY-RUN]" in res.stdout

    # learn_application (real dynamic learning on built-in tool)
    learned = agent.learn_application("ipconfig")
    assert learned["target"] == "ipconfig"
    assert learned["local_help"]["available"] is True


def test_agent_intent_planner_routing():
    agent = WinTermAgent()

    # Test that high-level GUI intents route to DesktopGuiSubsystem
    plan_find = agent.plan("find app chrome")
    assert any("chrome" in step.command.lower() for step in plan_find.steps)

    plan_launch = agent.plan("launch app calc.exe")
    assert any("calc.exe" in step.command.lower() for step in plan_launch.steps)

    plan_list = agent.plan("list windows")
    assert any("enumdesktopwindows" in step.command.lower() for step in plan_list.steps)

    plan_focus = agent.plan("focus window Terminal")
    assert any("resolvewindow" in step.command.lower() for step in plan_focus.steps)

    plan_type = agent.plan("type text Hello World")
    assert any("typeunicode" in step.command.lower() for step in plan_type.steps)

    plan_circle = agent.plan("draw a circle at 300 300 radius 50")
    assert any("mouse_event" in step.command.lower() for step in plan_circle.steps)


def test_interaction_mcp_wrappers():
    """Validates that all interaction MCP wrapper functions execute and return valid Dict schemas."""
    from winterm.tools.tool_definitions import (
        winterm_app_learn,
        winterm_app_find,
        winterm_window_list,
        winterm_screen_state,
        winterm_window_close,
        winterm_ui_inspect,
    )

    learn_res = winterm_app_learn("ping")
    assert isinstance(learn_res, dict)
    assert learn_res.get("target") == "ping"

    # Test that functions returning Dict[str, Any] have the required keys
    find_res = winterm_app_find("notepad", limit=5)
    assert isinstance(find_res, dict)
    assert "exit_code" in find_res
    assert "output" in find_res
    assert "error" in find_res

    win_res = winterm_window_list()
    assert isinstance(win_res, dict)
    assert "exit_code" in win_res
    assert "output" in win_res
    assert "error" in win_res

    screen_res = winterm_screen_state()
    assert isinstance(screen_res, dict)
    assert "exit_code" in screen_res

