"""Tests for the WinTerM CLI interface, UI commands, and universal tool runner."""

import json
from typer.testing import CliRunner
from winterm.cli.main import app

runner = CliRunner()


def test_cli_info():
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "Windows Terminal Environment Snapshot" in result.output


def test_cli_tools_list():
    result = runner.invoke(app, ["tools"])
    assert result.exit_code == 0
    assert "WinTerM Universal Agent Tools" in result.output
    assert "winterm_ui_smart_click" in result.output
    assert "winterm_app_launch" in result.output


def test_cli_tool_execute_json():
    result = runner.invoke(app, ["tool", "winterm_window_list", '{"query": "nonexistent_unique_query_123"}', "--raw"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["exit_code"] == 0
    assert "output" in data


def test_cli_tool_execute_key_val():
    result = runner.invoke(app, ["tool", "winterm_window_list", "query=nonexistent_unique_query_123", "--raw"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["exit_code"] == 0


from unittest.mock import patch, MagicMock


def test_cli_tool_execute_unquoted_array():
    with patch("winterm.tools.tool_definitions._agent_instance.press_hotkey") as mock_hotkey:
        mock_hotkey.return_value = (MagicMock(exit_code=0, stdout="{}", stderr=""), None, None)
        result = runner.invoke(app, ["tool", "winterm_input_hotkey", "{keys: [win, d]}", "--raw"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["exit_code"] == 0
        mock_hotkey.assert_called_once_with(["win", "d"])


def test_cli_tool_unknown():
    result = runner.invoke(app, ["tool", "nonexistent_tool"])
    assert result.exit_code == 1
    assert "Unknown tool" in result.output


def test_cli_ui_help():
    result = runner.invoke(app, ["ui", "--help"])
    assert result.exit_code == 0
    assert "inspect" in result.output
    assert "smart-click" in result.output
    assert "ocr" in result.output
    assert "perceive" in result.output
