---
name: winterm
description: AI Agent Toolkit for Windows Terminal and Desktop GUI Automation (Sense-Decide-Act-Verify)
---

# WinTerM Skill for Claude Code

When you need to interact with Windows, execute PowerShell/CMD commands safely, or control desktop applications (Notepad, Calculator, Paint, Chrome, etc.), use the **WinTerM MCP Tools**:

## Available Tools Reference
- **Perception**: `winterm_screen_state`, `winterm_screen_capture`, `winterm_ui_inspect`
- **Application Lifecycle**: `winterm_app_find`, `winterm_app_launch`, `winterm_app_close`, `winterm_app_learn`
- **Window Control**: `winterm_window_list`, `winterm_window_focus`, `winterm_window_resize`, `winterm_window_close`
- **Input Synthesis**: `winterm_ui_click`, `winterm_ui_set_text`, `winterm_input_type`, `winterm_input_hotkey`, `winterm_input_mouse_click`, `winterm_input_mouse_drag`
- **Cognition & Terminal**: `plan_terminal_task`, `execute_terminal_command`, `diagnose_terminal_error`, `predict_command_impact`, `undo_last_terminal_action`

## Operating Guidelines
1. **Never guess blind coordinates**: Call `winterm_ui_inspect(window_title)` to find exact control names, bounding boxes, and AutomationIds.
2. **Always focus first**: Call `winterm_window_focus(window_title)` before sending keystrokes or mouse clicks.
3. **Verify after action**: Call `winterm_screen_capture` or re-inspect the UI tree to confirm the action succeeded.
