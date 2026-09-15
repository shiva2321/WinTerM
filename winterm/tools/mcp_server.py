"""WinTerm MCP Server: Model Context Protocol server exposing Windows Terminal capabilities to AI agents."""

import sys
import json
from typing import Any, Dict
from winterm.tools.tool_definitions import (
    plan_terminal_task,
    explain_terminal_command,
    predict_command_impact,
    execute_terminal_command,
    diagnose_terminal_error,
    query_windows_knowledge,
    undo_last_terminal_action,
    winterm_graph_blast_radius,
    winterm_graph_validate_command,
    winterm_graph_remedy_error,
    winterm_graph_alternatives,
    winterm_graph_info,
    winterm_graph_search_intent,
    winterm_graph_command_docs,
    winterm_graph_safety_check,
    winterm_app_find,
    winterm_app_launch,
    winterm_app_close,
    winterm_app_learn,
    winterm_window_list,
    winterm_window_focus,
    winterm_window_resize,
    winterm_window_close,
    winterm_ui_inspect,
    winterm_ui_click,
    winterm_ui_set_text,
    winterm_ui_perceive,
    winterm_ui_ocr,
    winterm_ui_som_annotate,
    winterm_ui_smart_click,
    winterm_ui_wait_change,
    winterm_input_type,
    winterm_input_hotkey,
    winterm_input_mouse_click,
    winterm_input_mouse_drag,
    winterm_screen_state,
    winterm_screen_capture,
    winterm_linux_execute,
    winterm_linux_path_convert,
    winterm_linux_distro_list,
    winterm_linux_safety_check,
    winterm_linux_diagnose_error,
    winterm_playbook_create,
    winterm_playbook_match_run,
    winterm_playbook_list,
    winterm_playbook_prune,
    winterm_swarm_dispatch,
    winterm_swarm_board_read,
    winterm_swarm_board_post,
    winterm_swarm_suggestions,
    winterm_swarm_status,
    EXPORTED_TOOLS_SCHEMA,
)

SYSTEM_AGENT_INSTRUCTIONS = """You are an autonomous AI agent operating on a Microsoft Windows system with the WinTerm Agent Toolkit.

Follow the 4-phase Closed-Loop Execution Protocol for every task:

1. SENSE & DISCOVER:
   - Before launching an unfamiliar application, ALWAYS check if it is installed using `winterm_app_find`.
   - If the application is NOT installed, do not guess or write hardcoded scripts. Inform the user or suggest installing it via `winget install <id>`.
   - Check screen bounds and active foreground state with `winterm_screen_state`.

2. FOCUS & INSPECT:
   - Bring the application window to the foreground using `winterm_window_focus`.
   - Inspect the live UI element tree using `winterm_ui_inspect` to retrieve real element names, AutomationIds, ControlTypes, and bounding coordinates.
   - NEVER guess raw pixel coordinates when an element can be located dynamically via UIAutomation.

3. ACT & INTERACT:
   - Prefer semantic UIAutomation invocation: use `winterm_ui_click(window, element_query)` and `winterm_ui_set_text(window, element_query, text)`.
   - For keyboard navigation and shortcuts, use `winterm_input_hotkey` (e.g. ['ctrl', 's'], ['alt', 'f4']).
   - For canvas-based or non-standard apps (games, Flutter, DirectX), use `winterm_input_mouse_click` and `winterm_input_mouse_drag` based on visual analysis.

4. VERIFY & SELF-HEAL:
   - Visually verify results after state changes using `winterm_screen_capture` or by re-inspecting elements with `winterm_ui_inspect`.
   - If a terminal command fails, pass the stderr to `diagnose_terminal_error` to receive automated Windows HRESULT / exit code remediation.
   - NEVER write temporary, hardcoded Python scripts to disk with blind coordinates. Always operate through the atomic MCP tools.
"""


class WinTermMCPServer:
    """Implements JSON-RPC 2.0 MCP protocol over standard IO."""

    def __init__(self):
        self.tools = {
            "plan_terminal_task": plan_terminal_task,
            "explain_terminal_command": explain_terminal_command,
            "predict_command_impact": predict_command_impact,
            "execute_terminal_command": execute_terminal_command,
            "diagnose_terminal_error": diagnose_terminal_error,
            "query_windows_knowledge": query_windows_knowledge,
            "undo_last_terminal_action": undo_last_terminal_action,
            "winterm_graph_blast_radius": winterm_graph_blast_radius,
            "winterm_graph_validate_command": winterm_graph_validate_command,
            "winterm_graph_remedy_error": winterm_graph_remedy_error,
            "winterm_graph_alternatives": winterm_graph_alternatives,
            "winterm_graph_info": winterm_graph_info,
            "winterm_graph_search_intent": winterm_graph_search_intent,
            "winterm_graph_command_docs": winterm_graph_command_docs,
            "winterm_graph_safety_check": winterm_graph_safety_check,
            "winterm_app_find": winterm_app_find,
            "winterm_app_launch": winterm_app_launch,
            "winterm_app_close": winterm_app_close,
            "winterm_app_learn": winterm_app_learn,
            "winterm_window_list": winterm_window_list,
            "winterm_window_focus": winterm_window_focus,
            "winterm_window_resize": winterm_window_resize,
            "winterm_window_close": winterm_window_close,
            "winterm_ui_inspect": winterm_ui_inspect,
            "winterm_ui_click": winterm_ui_click,
            "winterm_ui_set_text": winterm_ui_set_text,
            "winterm_ui_perceive": winterm_ui_perceive,
            "winterm_ui_ocr": winterm_ui_ocr,
            "winterm_ui_som_annotate": winterm_ui_som_annotate,
            "winterm_ui_smart_click": winterm_ui_smart_click,
            "winterm_ui_wait_change": winterm_ui_wait_change,
            "winterm_input_type": winterm_input_type,
            "winterm_input_hotkey": winterm_input_hotkey,
            "winterm_input_mouse_click": winterm_input_mouse_click,
            "winterm_input_mouse_drag": winterm_input_mouse_drag,
            "winterm_screen_state": winterm_screen_state,
            "winterm_screen_capture": winterm_screen_capture,
            "winterm_linux_execute": winterm_linux_execute,
            "winterm_linux_path_convert": winterm_linux_path_convert,
            "winterm_linux_distro_list": winterm_linux_distro_list,
            "winterm_linux_safety_check": winterm_linux_safety_check,
            "winterm_linux_diagnose_error": winterm_linux_diagnose_error,
            "winterm_playbook_create": winterm_playbook_create,
            "winterm_playbook_match_run": winterm_playbook_match_run,
            "winterm_playbook_list": winterm_playbook_list,
            "winterm_playbook_prune": winterm_playbook_prune,
            "winterm_swarm_dispatch": winterm_swarm_dispatch,
            "winterm_swarm_board_read": winterm_swarm_board_read,
            "winterm_swarm_board_post": winterm_swarm_board_post,
            "winterm_swarm_suggestions": winterm_swarm_suggestions,
            "winterm_swarm_status": winterm_swarm_status,
        }

    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Processes an incoming JSON-RPC request."""
        method = req.get("method")
        msg_id = req.get("id")

        # In JSON-RPC 2.0, notifications (no id) must NOT be responded to
        if msg_id is None:
            return None

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "winterm",
                        "version": "0.3.0",
                    },
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "prompts": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                    },
                },
            }

        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {},
            }

        elif method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "prompts": [
                        {
                            "name": "windows_agent_instructions",
                            "description": "Standard operating guidelines, Sense-Decide-Act-Verify loop, and safety rules for AI agents on Windows.",
                            "arguments": [],
                        }
                    ]
                },
            }

        elif method == "prompts/get":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "description": "WinTerm Agent Instructions",
                    "messages": [
                        {
                            "role": "user",
                            "content": {
                                "type": "text",
                                "text": SYSTEM_AGENT_INSTRUCTIONS,
                            },
                        }
                    ],
                },
            }

        elif method == "tools/list":
            mcp_tools = []
            for item in EXPORTED_TOOLS_SCHEMA:
                fn = item["function"]
                mcp_tools.append({
                    "name": fn["name"],
                    "description": fn["description"],
                    "inputSchema": fn["parameters"],
                })
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": mcp_tools},
            }

        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"resources": []},
            }

        elif method == "resources/templates/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"resourceTemplates": []},
            }

        elif method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in self.tools:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"},
                }

            try:
                result = self.tools[tool_name](**arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, indent=2, default=str)}
                        ]
                    },
                }
            except Exception as ex:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32000, "message": str(ex)},
                }

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method '{method}' not implemented"},
        }

    def run(self):
        """Runs the MCP server loop reading from stdin and writing to stdout."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                resp = self.handle_request(req)
                if resp is not None:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
            except Exception as ex:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(ex)}"},
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()


def main():
    server = WinTermMCPServer()
    server.run()


if __name__ == "__main__":
    main()
