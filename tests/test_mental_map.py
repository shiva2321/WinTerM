"""Unit and integration tests for the Cognitive Screen Mental Map and Advanced UI Operations."""

import pytest
import json
from winterm.interaction.mental_map import (
    SpatialScreenLayer,
    FunctionalZone,
    SemanticRole,
    SemanticUIElement,
    AttentionState,
    ScreenMentalMap,
)
from winterm.interaction.mouse import MouseEngine
from winterm.interaction.keyboard import KeyboardEngine
from winterm.interaction.smart_resolver import SmartUIResolver
from winterm.subsystems.desktop_gui import DesktopGuiSubsystem
from winterm.tools.mcp_server import WinTermMCPServer
from winterm.tools.tool_definitions import EXPORTED_TOOLS_SCHEMA


def test_zone_classification():
    """Tests spatial zone partitioning for different coordinates."""
    win_w = 1920
    win_h = 1080

    # Header: top 12% (y < 129)
    assert ScreenMentalMap.classify_zone(y=50, height=30, x=100, width=200, win_w=win_w, win_h=win_h) == FunctionalZone.HEADER

    # Navigation / Omnibox: between 12% and 24% (130 <= y < 259)
    assert ScreenMentalMap.classify_zone(y=160, height=40, x=300, width=600, win_w=win_w, win_h=win_h) == FunctionalZone.NAVIGATION

    # Footer / Status bar: bottom 7% (y + h > 93% of 1080 = 1004)
    assert ScreenMentalMap.classify_zone(y=1040, height=30, x=100, width=400, win_w=win_w, win_h=win_h) == FunctionalZone.FOOTER

    # Sidebar: left 18% (x < 345) and width < 25%
    assert ScreenMentalMap.classify_zone(y=400, height=500, x=50, width=200, win_w=win_w, win_h=win_h) == FunctionalZone.SIDEBAR

    # Content: center area
    assert ScreenMentalMap.classify_zone(y=400, height=400, x=500, width=800, win_w=win_w, win_h=win_h) == FunctionalZone.CONTENT


def test_semantic_role_inference():
    """Tests role deduction from text, control type, and shape."""
    bounds = {"x": 100, "y": 100, "width": 80, "height": 30}

    assert ScreenMentalMap.infer_role("Button", "Submit", bounds) == SemanticRole.BUTTON
    assert ScreenMentalMap.infer_role("ControlType.Button", "Cancel", bounds) == SemanticRole.BUTTON
    assert ScreenMentalMap.infer_role("Edit", "Search Google or type a URL", bounds) == SemanticRole.SEARCH_BOX
    assert ScreenMentalMap.infer_role("Edit", "Username", bounds) == SemanticRole.INPUT
    assert ScreenMentalMap.infer_role("TabItem", "General Settings", bounds) == SemanticRole.TAB
    assert ScreenMentalMap.infer_role("Hyperlink", "Learn More", bounds) == SemanticRole.LINK
    assert ScreenMentalMap.infer_role("MenuItem", "File", bounds) == SemanticRole.MENU_ITEM


def test_mental_map_build_and_affordances():
    """Tests complete mental map synthesis from mock perceptions."""
    mock_windows = [
        {"Handle": 12345, "Title": "Google Chrome", "Bounds": {"x": 0, "y": 0, "width": 1920, "height": 1080}},
        {"Handle": 99999, "Title": "Taskbar", "Bounds": {"x": 0, "y": 1040, "width": 1920, "height": 40}},
    ]

    mock_uia = [
        {
            "Name": "Search",
            "ControlType": "ControlType.Edit",
            "AutomationId": "search_box",
            "BoundingRectangle": {"X": 400, "Y": 150, "Width": 600, "Height": 35},
            "HasKeyboardFocus": True,
        },
        {
            "Name": "Google Search",
            "ControlType": "ControlType.Button",
            "AutomationId": "btn_search",
            "BoundingRectangle": {"X": 600, "Y": 300, "Width": 120, "Height": 40},
            "HasKeyboardFocus": False,
        },
    ]

    mock_ocr = [
        "Welcome to Chrome",
        "Sign in to sync your bookmarks",
    ]

    mental_map = ScreenMentalMap.build_from_perceptions(
        windows=mock_windows,
        target_hwnd=12345,
        uia_elements=mock_uia,
        ocr_lines=mock_ocr,
    )

    # Validate layers
    assert mental_map.active_window["handle"] == 12345
    assert len(mental_map.inactive_windows) == 1
    assert len(mental_map.elements) >= 3

    # Validate attention & affordances
    assert mental_map.attention.focused_element_id == "elem-uia-1"
    affordance_actions = [a["action"] for a in mental_map.attention.action_affordances]
    assert "TYPE" in affordance_actions
    assert "CLICK" in affordance_actions
    assert "SCROLL" in affordance_actions

    # Test dictionary export
    map_dict = mental_map.to_dict()
    assert "spatial_layers" in map_dict
    assert "attention" in map_dict
    assert map_dict["element_count"] == len(mental_map.elements)

    # Test Markdown summary
    md_summary = mental_map.to_markdown_summary()
    assert "Cognitive Screen Mental Map: Google Chrome" in md_summary
    assert "Next Action Affordances" in md_summary


def test_mental_map_diff():
    """Tests perceptual delta calculation between two mental map snapshots."""
    win = {"handle": 100, "title": "Dashboard", "bounds": {"width": 1000, "height": 800, "x": 0, "y": 0}}
    el1 = SemanticUIElement("1", SemanticRole.BUTTON, "Submit", {"x": 10, "y": 10, "width": 50, "height": 20}, FunctionalZone.CONTENT)
    el2 = SemanticUIElement("2", SemanticRole.TEXT, "Status: Idle", {"x": 10, "y": 40, "width": 100, "height": 20}, FunctionalZone.CONTENT)

    map1 = ScreenMentalMap(active_window=win, elements=[el1, el2])

    win2 = {"handle": 100, "title": "Dashboard - Loaded", "bounds": {"width": 1000, "height": 800, "x": 0, "y": 0}}
    el3 = SemanticUIElement("3", SemanticRole.TEXT, "Status: Done", {"x": 10, "y": 40, "width": 100, "height": 20}, FunctionalZone.CONTENT)
    map2 = ScreenMentalMap(active_window=win2, elements=[el1, el3])

    delta = map2.diff(map1)
    assert delta["title_changed"] is True
    assert delta["appeared_count"] == 1
    assert "Status: Done" in delta["appeared_samples"]
    assert delta["disappeared_count"] == 1
    assert "Status: Idle" in delta["disappeared_samples"]


def test_mouse_natural_movement_and_hover():
    """Tests C# / PowerShell command generation for smooth Bezier curves and hovering."""
    smooth_cmd = MouseEngine.build_move_smooth_command(0, 0, 500, 300, steps=25)
    assert "[Win32MouseCore]::MoveSmooth(0, 0, 500, 300, 25)" in smooth_cmd
    assert "Bezier" in MouseEngine.WIN32_MOUSE_HEADER

    hover_cmd = MouseEngine.build_hover_command(250, 150, hwnd=1234, dwell_ms=600)
    assert "[Win32MouseCore]::HoverInWindow" in hover_cmd
    assert "600" in hover_cmd

    scroll_cmd = MouseEngine.build_scroll_into_view_command(0, 700, viewport_center_y=400)
    assert "[Win32MouseCore]::Scroll(" in scroll_cmd


def test_keyboard_type_with_clear():
    """Tests build_type_with_clear_command generates Ctrl+A and Backspace sequence."""
    cmd = KeyboardEngine.build_type_with_clear_command("Fresh Search Query", delay_ms=20)
    assert "^a" in cmd or "SendWait('^a')" in cmd or "0x11" in cmd  # Ctrl+A
    assert "{BACKSPACE}" in cmd or "0x08" in cmd  # Backspace
    assert "Fresh Search Query" in cmd


def test_smart_resolver_hover_command():
    """Tests SmartUIResolver.build_smart_hover_command generation for queries and coordinates."""
    # Query hover
    query_cmd = SmartUIResolver.build_smart_hover_command("Notepad", element_query="File", dwell_ms=400)
    assert "ResolveWindow('Notepad'" in query_cmd
    assert "$query = 'File'" in query_cmd
    assert "[Win32MouseCore]::HoverInWindow" in query_cmd

    # Coordinate hover
    coord_cmd = SmartUIResolver.build_smart_hover_command("Notepad", rel_x=50, rel_y=25, dwell_ms=300)
    assert "[Win32MouseCore]::HoverInWindow($hWnd, 50, 25, 300)" in coord_cmd


def test_desktop_gui_subsystem_plan_steps():
    """Tests DesktopGuiSubsystem methods return valid PlanSteps."""
    step_hover = DesktopGuiSubsystem.hover_element("Calculator", element_query="One")
    assert step_hover.category.value == "custom"
    assert "Hover" in step_hover.title

    step_scroll = DesktopGuiSubsystem.scroll_into_view("Edge", target_rel_y=650)
    assert "Scroll Into View" in step_scroll.title
    assert step_scroll.metadata["target_y"] == 650

    step_type = DesktopGuiSubsystem.type_with_clear("Hello World")
    assert "Type with Clear" in step_type.title
    assert step_type.metadata["length"] == len("Hello World")


def test_mcp_server_has_54_tools():
    """Verifies that WinTermMCPServer registers all 54 production tools."""
    server = WinTermMCPServer()
    assert len(server.tools) == 54
    assert "winterm_screen_mental_map" in server.tools
    assert "winterm_ui_hover" in server.tools
    assert "winterm_ui_scroll_into_view" in server.tools

    schema_names = [t["function"]["name"] for t in EXPORTED_TOOLS_SCHEMA]
    assert len(schema_names) == 54
    assert "winterm_screen_mental_map" in schema_names
    assert "winterm_ui_hover" in schema_names
    assert "winterm_ui_scroll_into_view" in schema_names
