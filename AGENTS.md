# AGENTS.md: Universal Autonomous Agent Instructions for WinTerM

This file defines universal operating instructions for all autonomous AI agents (Claude Code, OpenCode, Google Antigravity, Cursor, OpenAI Swarm) operating on Windows.

---

## Mission
WinTerM equips AI agents with deterministic Windows Terminal mastery, interactive desktop GUI control, and a 5W cognitive pipeline (What, How, When, Why, After).

---

## Tool Availability
When executing actions on Windows, use the 32 MCP tools provided by WinTerM (`python -m winterm.tools.mcp_server`):
- **Core 5W**: `plan_terminal_task`, `explain_terminal_command`, `predict_command_impact`, `execute_terminal_command`, `diagnose_terminal_error`, `undo_last_terminal_action`.
- **Knowledge Graph**: `winterm_graph_blast_radius`, `winterm_graph_validate_command`, `winterm_graph_remedy_error`, `winterm_graph_alternatives`, `winterm_graph_command_docs`, `winterm_graph_safety_check`.
- **Application Lifecycle**: `winterm_app_find`, `winterm_app_launch`, `winterm_app_close`, `winterm_app_learn`.
- **Window Management**: `winterm_window_list`, `winterm_window_focus`, `winterm_window_resize`, `winterm_window_close`.
- **UI Automation & Input**: `winterm_ui_inspect`, `winterm_ui_click`, `winterm_ui_set_text`, `winterm_input_type`, `winterm_input_hotkey`, `winterm_input_mouse_click`, `winterm_input_mouse_drag`, `winterm_screen_state`, `winterm_screen_capture`.

---

## Operational Protocol: Sense -> Decide -> Act -> Verify
1. **SENSE**:
   - Check if an app is installed: `winterm_app_find(query)`.
   - Check running windows: `winterm_window_list()`.
   - Inspect UI controls: `winterm_ui_inspect(window)`.
   - Query screen metrics: `winterm_screen_state()`.
2. **DECIDE**:
   - Class A (Win32/WPF/UWP): Use `AutomationId` or element names.
   - Class B (Electron/Chromium): Use standard keyboard shortcuts (`Ctrl+P`, `Ctrl+Shift+P`).
   - Class C (Canvas/DirectX): Calculate relative offsets inside the target window's bounding box, never blind global screen coordinates.
3. **ACT**:
   - Focus the target window: `winterm_window_focus(window)`.
   - Execute the action using generic toolkit tools (`winterm_ui_click`, `winterm_input_type`, etc.).
4. **VERIFY**:
   - Re-inspect UI tree or capture screenshot: `winterm_screen_capture()`.
   - If failed, diagnose with `diagnose_terminal_error` or query `winterm_graph_remedy_error`.
