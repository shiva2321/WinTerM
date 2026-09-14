# CLAUDE.md: Instructions for Claude Code in WinTerM

## Project Overview
**WinTerM** is the AI Agent Toolkit for Windows Terminal & Desktop automation. It provides a 5W cognitive pipeline (What, How, When, Why, After), 10 subsystem layers (Layers 0–9), a 10,374-node Knowledge Graph, and a 32-tool Model Context Protocol (MCP) server.

---

## Connecting Claude Code to WinTerM MCP Tools

To give Claude Code access to all 32 WinTerM tools, run:

```bash
claude mcp add winterm python -m winterm.tools.mcp_server
```

Or add to your Claude Code configuration (`~/.claude.json` or project `.claude.json`):

```json
{
  "mcpServers": {
    "winterm": {
      "command": "python",
      "args": ["-m", "winterm.tools.mcp_server"]
    }
  }
}
```

---

## Agent Guidelines for Claude Code on Windows

When tasked with executing commands or automating desktop applications on Windows, follow these rules:

1. **Use WinTerM MCP Tools First**:
   - For application discovery: use `winterm_app_find` before launching.
   - For UI interaction: use `winterm_ui_inspect` to locate UI Automation elements, bounding boxes, and AutomationIds. Never guess blind screen pixel coordinates!
   - For window focus: always call `winterm_window_focus` before typing or clicking.
   - For desktop perception: use `winterm_screen_state` and `winterm_screen_capture`.
   - For terminal execution: use `execute_terminal_command` with built-in UTF-8 safety, quoting, and error self-healing.

2. **The 4-Phase Closed Loop Protocol**:
   - **SENSE**: Inspect app existence (`winterm_app_find`), window state (`winterm_window_list`), and controls (`winterm_ui_inspect`).
   - **DECIDE**: Categorize app (Class A: Win32/UIA, Class B: Electron/hotkeys, Class C: Canvas/relative bounding box).
   - **ACT**: Focus target window and execute guarded toolkit primitives (`winterm_ui_click`, `winterm_input_type`, `winterm_input_hotkey`).
   - **VERIFY**: Check post-conditions with `winterm_ui_inspect` or `winterm_screen_capture`.

3. **Anti-Pattern Warning**:
   - **DO NOT** write temporary `.py` scripts that call raw `pyautogui` or blind Win32 mouse clicks.
   - **DO NOT** hardcode fixed paths like `C:\Windows\System32\mspaint.exe`.
   - Use the generic toolkit MCP tools instead.

---

## Common Development Commands

### Install in Editable Mode
```powershell
python -m pip install -e ".[dev,mcp]"
```

### Run Tests
```powershell
python -m pytest tests/ -v
```

### Run WinTerM CLI
```powershell
winterm info
winterm subsystems
winterm app find "notepad"
winterm window list
winterm screen state
```

### Run MCP Server (Stdio)
```powershell
python -m winterm.tools.mcp_server
```
