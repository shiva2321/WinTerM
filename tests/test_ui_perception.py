"""Tests for WinTerM Advanced UI Perception, Native Windows OCR, Set-of-Mark Grounding & Smart Resolution."""

import json
import pytest
from winterm.interaction.ocr_engine import WindowsOCREngine
from winterm.interaction.visual_grounding import SetOfMarkEngine
from winterm.interaction.semantic_tree import SemanticAccessibilityTree
from winterm.interaction.smart_resolver import SmartUIResolver
from winterm.interaction.visual_diff import VisualStateVerifier
from winterm.interaction.screen import ScreenPerceptionEngine
from winterm.subsystems.desktop_gui import DesktopGuiSubsystem
from winterm.agent.winterm_agent import WinTermAgent
from winterm.tools.mcp_server import WinTermMCPServer
from winterm.tools.tool_definitions import (
    winterm_ui_perceive,
    winterm_ui_ocr,
    winterm_ui_som_annotate,
    winterm_ui_smart_click,
    winterm_ui_wait_change,
    EXPORTED_TOOLS_SCHEMA,
)


class TestWindowsOCREngine:
    def test_build_ocr_image_command_structure(self):
        cmd = WindowsOCREngine.build_ocr_image_command("C:\\test\\image.png", language_tag="en-US")
        assert "Windows.Media.Ocr.OcrEngine" in cmd
        assert "Windows.Graphics.Imaging.BitmapDecoder" in cmd
        assert "C:\\test\\image.png" in cmd
        assert "en-US" in cmd
        assert "RecognizeAsync" in cmd

    def test_build_ocr_window_command_structure(self):
        cmd = WindowsOCREngine.build_ocr_window_command("Calculator", language_tag="en-US")
        assert "Win32WindowCore" in cmd
        assert "CaptureScreen" in cmd
        assert "Windows.Media.Ocr.OcrEngine" in cmd
        assert "Calculator" in cmd

    def test_build_find_text_command_structure(self):
        cmd = WindowsOCREngine.build_find_text_command("Notepad", "Save", language_tag="en-US")
        assert "Save" in cmd
        assert "Matches" in cmd
        assert "BestMatch" in cmd


class TestSetOfMarkEngine:
    def test_build_annotate_window_command_structure(self):
        cmd = SetOfMarkEngine.build_annotate_window_command(
            window_identifier="Notepad",
            output_annotated_path="C:\\out\\som.png",
            max_marks=25,
        )
        assert "Draw-SetOfMarkAnnotations" in cmd
        assert "System.Drawing.Graphics" in cmd
        assert "Notepad" in cmd
        assert "C:\\out\\som.png" in cmd
        assert "max_marks" in str(cmd) or "25" in cmd


class TestSemanticAccessibilityTree:
    def test_prune_invisible_and_zero_dimension_elements(self):
        raw = [
            {"Name": "Invisible", "ControlType": "Button", "Width": 0, "Height": 0, "CenterX": 10, "CenterY": 10},
            {"Name": "TinyArtifact", "ControlType": "Pane", "Width": 2, "Height": 2, "CenterX": 20, "CenterY": 20},
            {"Name": "RealButton", "ControlType": "Button", "Width": 80, "Height": 30, "CenterX": 100, "CenterY": 50},
        ]
        pruned = SemanticAccessibilityTree.prune_elements(raw, filter_invisible=True, min_dimension=4)
        assert len(pruned) == 1
        assert pruned[0]["name"] == "RealButton"

    def test_prune_nameless_layout_containers(self):
        raw = [
            {"Name": "", "AutomationId": "", "ControlType": "Pane", "Width": 500, "Height": 400, "CenterX": 250, "CenterY": 200},
            {"Name": "", "AutomationId": "", "ControlType": "Group", "Width": 200, "Height": 100, "CenterX": 100, "CenterY": 50},
            {"Name": "Submit", "AutomationId": "btn_submit", "ControlType": "Button", "Width": 100, "Height": 35, "CenterX": 50, "CenterY": 20},
        ]
        pruned = SemanticAccessibilityTree.prune_elements(raw)
        assert len(pruned) == 1
        assert pruned[0]["name"] == "Submit"

    def test_prune_deduplicates_identical_coordinates(self):
        raw = [
            {"Name": "Button1", "ControlType": "Button", "Width": 80, "Height": 30, "CenterX": 100, "CenterY": 50},
            {"Name": "Button1Duplicate", "ControlType": "Button", "Width": 80, "Height": 30, "CenterX": 100, "CenterY": 50},
            {"Name": "Button2", "ControlType": "Button", "Width": 80, "Height": 30, "CenterX": 200, "CenterY": 50},
        ]
        pruned = SemanticAccessibilityTree.prune_elements(raw)
        assert len(pruned) == 2
        assert pruned[0]["name"] == "Button1"
        assert pruned[1]["name"] == "Button2"

    def test_to_markdown_table_formatting(self):
        elements = [
            {
                "name": "Save File",
                "control_type": "Button",
                "automation_id": "saveBtn",
                "is_enabled": True,
                "center_x": 120,
                "center_y": 45,
                "bounds": "80x30",
            }
        ]
        md = SemanticAccessibilityTree.to_markdown_table(elements, title="Editor")
        assert "### UI Elements in 'Editor'" in md
        assert "| [1] | Button | Save File | saveBtn | (120, 45) | 80x30 | Enabled |" in md

    def test_to_token_efficient_summary(self):
        raw = {
            "Success": True,
            "WindowTitle": "TextApp",
            "WindowHandle": 12345,
            "Elements": [
                {"Name": "OK", "ControlType": "Button", "Width": 60, "Height": 25, "CenterX": 50, "CenterY": 30},
                {"Name": "", "ControlType": "Pane", "Width": 0, "Height": 0},
            ]
        }
        summary = SemanticAccessibilityTree.to_token_efficient_summary(raw, max_items=10)
        assert summary["success"] is True
        assert summary["total_elements_found"] == 2
        assert summary["pruned_elements_count"] == 1
        assert "OK" in summary["markdown_tree"]


class TestSmartUIResolver:
    def test_build_smart_click_command_structure(self):
        cmd = SmartUIResolver.build_smart_click_command("Notepad", "Save", control_type="Button")
        # Strategy 1: UIAutomation
        assert "STRATEGY 1: UIAutomation Tree Search" in cmd
        assert "InvokePattern" in cmd
        assert "CoordinateClick" in cmd
        # Strategy 2: OCR Fallback
        assert "STRATEGY 2: Native Windows OCR Fallback" in cmd
        assert "Windows.Media.Ocr.OcrEngine" in cmd
        assert "Button" in cmd


class TestVisualStateVerifier:
    def test_build_wait_for_ui_change_command_structure(self):
        cmd = VisualStateVerifier.build_wait_for_ui_change_command(
            window_identifier="Notepad",
            timeout_ms=2500,
            min_diff_pct=1.0,
            poll_interval_ms=75,
        )
        assert "Compare-WindowBitmaps" in cmd
        assert "Stopwatch" in cmd
        assert "2500" in cmd
        assert "1.0" in cmd
        assert "75" in cmd


class TestScreenPerceptionEnhancements:
    def test_coordinate_normalization_and_denormalization(self):
        bounds = {"window_left": 100, "window_top": 200, "window_width": 1000, "window_height": 500}
        norm = ScreenPerceptionEngine.normalize_to_window(
            screen_x=600,
            screen_y=450,
            **bounds,
        )
        assert norm["u"] == 0.5
        assert norm["v"] == 0.5
        assert norm["rel_x"] == 500
        assert norm["rel_y"] == 250

        denorm = ScreenPerceptionEngine.denormalize_from_window(
            u=norm["u"],
            v=norm["v"],
            **bounds,
        )
        assert denorm["screen_x"] == 600
        assert denorm["screen_y"] == 450

    def test_get_screen_state_command_contains_virtual_desktop(self):
        cmd = ScreenPerceptionEngine.build_get_screen_state_command()
        assert "VirtualDesktop" in cmd
        assert "MonitorCount" in cmd
        assert "SetProcessDpiAwarenessContext" in ScreenPerceptionEngine.WIN32_SCREEN_HEADER


class TestSubsystemAndAgentPerceptionIntegration:
    def test_desktop_gui_subsystem_plan_steps(self):
        ocr_step = DesktopGuiSubsystem.ocr_window("Calculator")
        assert ocr_step.metadata["action"] == "ocr_window"
        assert "Windows.Media.Ocr" in ocr_step.command

        som_step = DesktopGuiSubsystem.som_annotate("Notepad", "out.png")
        assert som_step.metadata["action"] == "som_annotate"
        assert "Draw-SetOfMarkAnnotations" in som_step.command

        smart_step = DesktopGuiSubsystem.smart_click("Notepad", "File")
        assert smart_step.metadata["action"] == "smart_click"

        wait_step = DesktopGuiSubsystem.wait_for_ui_change("Notepad")
        assert wait_step.metadata["action"] == "wait_ui_change"

    def test_agent_perceive_ui_dry_run(self):
        agent = WinTermAgent()
        res = agent.perceive_ui("Notepad", max_items=10, dry_run=True)
        assert "accessibility_tree" in res
        assert "window" in res
        assert res["window"] == "Notepad"


class TestUIPerceptionMCPTools:
    def test_mcp_server_registers_all_51_tools(self):
        server = WinTermMCPServer()
        assert len(server.tools) == 51
        assert "winterm_ui_perceive" in server.tools
        assert "winterm_ui_ocr" in server.tools
        assert "winterm_ui_som_annotate" in server.tools
        assert "winterm_ui_smart_click" in server.tools
        assert "winterm_ui_wait_change" in server.tools
        assert len(EXPORTED_TOOLS_SCHEMA) == 51

    def test_mcp_server_list_tools_contains_perception_tools(self):
        server = WinTermMCPServer()
        res = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert res["id"] == 1
        tools = res["result"]["tools"]
        assert len(tools) == 51
        tool_names = [t["name"] for t in tools]
        assert "winterm_ui_perceive" in tool_names
        assert "winterm_ui_ocr" in tool_names
        assert "winterm_ui_som_annotate" in tool_names
        assert "winterm_ui_smart_click" in tool_names
        assert "winterm_ui_wait_change" in tool_names
