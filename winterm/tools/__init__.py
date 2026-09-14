"""Agent tool interfaces and MCP server."""

from winterm.tools.tool_definitions import (
    plan_terminal_task,
    explain_terminal_command,
    predict_command_impact,
    execute_terminal_command,
    diagnose_terminal_error,
    query_windows_knowledge,
    undo_last_terminal_action,
    EXPORTED_TOOLS_SCHEMA,
)
from winterm.tools.mcp_server import WinTermMCPServer

__all__ = [
    "plan_terminal_task",
    "explain_terminal_command",
    "predict_command_impact",
    "execute_terminal_command",
    "diagnose_terminal_error",
    "query_windows_knowledge",
    "undo_last_terminal_action",
    "EXPORTED_TOOLS_SCHEMA",
    "WinTermMCPServer",
]
