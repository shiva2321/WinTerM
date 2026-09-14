"""End-to-end smoke test for the WinTerm MCP server as an actual subprocess.

tests/test_graph_reasoning.py already exercises WinTermMCPServer.handle_request()
in-process, which is good coverage for the JSON-RPC method dispatch logic --
but it can't catch the class of bug that only shows up when the server is
launched the way a real MCP client (Claude Code, OpenCode, Claude Desktop)
actually launches it: `python -m winterm.tools.mcp_server`, talking newline-
delimited JSON-RPC over stdin/stdout. A stray `print()`, an import-time
warning written to stdout instead of stderr, or an entry-point/packaging
problem would break every one of those clients while leaving the in-process
test green. This test spawns the real subprocess and speaks the protocol to
it, matching what CLAUDE.md/AGENTS.md/OPENCODE.md tell agents to run.
"""

import json
import subprocess
import sys

import pytest

from winterm.tools.tool_definitions import EXPORTED_TOOLS_SCHEMA


def _rpc(proc, request, timeout=15):
    """Writes one JSON-RPC request line and reads back one response line."""
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    assert line, (
        "MCP server produced no output for request "
        f"{request!r} (stderr: {proc.stderr.read()!r})"
    )
    return json.loads(line)


@pytest.fixture()
def mcp_server_process():
    proc = subprocess.Popen(
        [sys.executable, "-m", "winterm.tools.mcp_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        yield proc
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_mcp_server_subprocess_initialize_and_list_tools(mcp_server_process):
    """The real `python -m winterm.tools.mcp_server` subprocess must speak
    clean, newline-delimited JSON-RPC on stdout -- no stray stdout output
    (print statements, warnings, banner text) may appear before or between
    JSON-RPC responses, or every real MCP client's line-based JSON parser
    breaks."""
    proc = mcp_server_process

    init_resp = _rpc(proc, {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "smoke-test", "version": "0.0.0"},
            "capabilities": {},
        },
    })
    assert init_resp["id"] == 1
    assert init_resp["result"]["serverInfo"]["name"] == "winterm"

    tools_resp = _rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = tools_resp["result"]["tools"]
    # Compare against the schema rather than a hardcoded count so this test
    # doesn't need updating every time a tool is added -- it still catches a
    # tool silently failing to reach the real subprocess.
    assert len(tools) == len(EXPORTED_TOOLS_SCHEMA)
    tool_names = {t["name"] for t in tools}
    # Spot-check a few tools from each subsystem named in AGENTS.md/OPENCODE.md
    # so a refactor that silently drops a tool from the exported schema fails
    # this test rather than surfacing as "the agent says a tool doesn't exist".
    for expected in (
        "execute_terminal_command",
        "winterm_graph_safety_check",
        "winterm_app_find",
        "winterm_window_focus",
        "winterm_ui_inspect",
        "winterm_input_type",
        "winterm_screen_state",
    ):
        assert expected in tool_names, f"'{expected}' missing from tools/list"

    # A real tool call round-trips through the same subprocess without
    # crashing the server or emitting anything but the one JSON-RPC line.
    call_resp = _rpc(proc, {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "winterm_graph_safety_check", "arguments": {"command": "Get-Process"}},
    })
    assert call_resp["id"] == 3
    assert "result" in call_resp, call_resp
