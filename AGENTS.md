# AGENTS.md: Universal Autonomous Agent Instructions for WinTerM

This file defines universal operating instructions for all autonomous AI agents (Claude Code, OpenCode, Google Gemini / Antigravity, DeepSeek, Cursor, OpenAI Swarm) operating on Windows and Linux/WSL.

---

## Mission
WinTerM equips AI agents with deterministic Windows Terminal and Linux/WSL2 mastery, interactive desktop GUI control, a 5W cognitive pipeline (What, How, When, Why, After), and multi-agent concurrency coordination.

---

## Tool Availability
When executing actions, use the **37 MCP tools** provided by WinTerM (`python -m winterm.tools.mcp_server`):
- **Core 5W Pipeline**: `plan_terminal_task`, `explain_terminal_command`, `predict_command_impact`, `execute_terminal_command`, `diagnose_terminal_error`, `undo_last_terminal_action`.
- **Linux & WSL2 Subsystem**: `winterm_linux_execute`, `winterm_linux_path_convert`, `winterm_linux_distro_list`, `winterm_linux_safety_check`, `winterm_linux_diagnose_error`.
- **Knowledge Graph**: `winterm_graph_blast_radius`, `winterm_graph_validate_command`, `winterm_graph_remedy_error`, `winterm_graph_alternatives`, `winterm_graph_command_docs`, `winterm_graph_safety_check`.
- **Application Lifecycle**: `winterm_app_find`, `winterm_app_launch`, `winterm_app_close`, `winterm_app_learn`.
- **Window Management**: `winterm_window_list`, `winterm_window_focus`, `winterm_window_resize`, `winterm_window_close`.
- **UI Automation & Input**: `winterm_ui_inspect`, `winterm_ui_click`, `winterm_ui_set_text`, `winterm_input_type`, `winterm_input_hotkey`, `winterm_input_mouse_click`, `winterm_input_mouse_drag`, `winterm_screen_state`, `winterm_screen_capture`.

---

## Operational Protocol: Sense -> Decide -> Act -> Verify

### Windows Desktop & Terminal:
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

### Linux & WSL2:
1. **SENSE & AUDIT**: Audit safety with `winterm_linux_safety_check(command)` (blocks `rm -rf /`, fork bombs, raw block writes).
2. **TRANSLATE**: Translate paths between Windows (`C:\...`) and Linux (`/mnt/c/...`) with `winterm_linux_path_convert(path)`.
3. **ACT**: Execute bash commands via `winterm_linux_execute(command)`. Non-interactive flags are automatically injected.
4. **VERIFY & RECOVER**: If non-zero exit code occurs, pass output to `winterm_linux_diagnose_error` for automated recovery.

---

## Multi-Agent Coexistence (Simultaneous Operation)
When running alongside other agents (e.g. Gemini, DeepSeek, Claude Code, OpenCode):
1. **Resource Locking**: Acquire a lease on shared resources (e.g. ports, exclusive windows) using `AgentSessionCoordinator`.
2. **Window Courtesy**: Never arbitrarily close or minimize windows opened by another agent.
3. **Isolated Undo Stacks**: Each agent maintains a dedicated session ID to ensure rollback actions don't interfere with other running agents.
