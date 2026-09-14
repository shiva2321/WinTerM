# OPENCODE.md: OpenCode Agent Guidelines for WinTerM

Welcome OpenCode agent! When interacting with the Windows Terminal, operating system, or desktop applications, you must use the **WinTerM** execution engine.

---

## WinTerM MCP Tool Suite

WinTerM provides 32 production-grade MCP tools configured in `opencode.json`:

### 1. Terminal Execution & 5W Cognition
- `plan_terminal_task`: Decompose natural language goals into DAG steps.
- `explain_terminal_command`: 5W decision trace (What, How, When, Why, After).
- `predict_command_impact`: Pre-execution state diff simulation and rollback synthesis.
- `execute_terminal_command`: Hardened PowerShell/CMD execution with UTF-8 safety and auto-healing.
- `diagnose_terminal_error`: Root-cause diagnosis and remediation proposals for Windows error codes.
- `undo_last_terminal_action`: Rollback last mutating state change.

### 2. Desktop GUI & UI Automation
- `winterm_app_find`: Discovers installed apps across Start Menu, Registry, and AppsFolder.
- `winterm_app_launch`: Launches Win32 apps, Store apps, or protocol URIs (`ms-paint:`, `calc:`).
- `winterm_window_list`: Lists all top-level windows with HWNDs, bounds, and titles.
- `winterm_window_focus`: Unlocks UIPI focus locks and brings window to foreground.
- `winterm_ui_inspect`: Traverses native UI Automation tree to locate buttons, edits, and bounds.
- `winterm_ui_click`: Native `InvokePattern` click with mouse coordinate fallback.
- `winterm_ui_set_text`: Sets edit box text via native `ValuePattern`.
- `winterm_input_type`: Types keyboard text via SendKeys.
- `winterm_input_hotkey`: Presses key combinations (`ctrl+s`, `alt+f4`, `win+r`).
- `winterm_screen_state`: Live screen resolution, cursor position, and foreground window info.
- `winterm_screen_capture`: Visual screenshot capture of full desktop or target window.

---

## The 4 Golden Rules for OpenCode

1. **Inspect Before Interacting**: Never execute blind mouse clicks. Call `winterm_ui_inspect` to discover the exact UI elements and coordinates.
2. **Focus Before Typing**: Always bring the target window to the foreground via `winterm_window_focus` before injecting keystrokes.
3. **Verify State Transitions**: After performing an action, confirm success with `winterm_ui_inspect` or `winterm_screen_capture`.
4. **Never Write Hardcoded Scripts**: Avoid writing temporary `.py` scripts containing hardcoded pixel coordinates or assumptions about system paths.
5. **Target by Handle (HWND), Not Title, After the First Lookup**: Window titles can change dynamically (unsaved-changes markers, the document's own content appearing in the title), so a title matched in step 1 can stop matching a few steps later in the same task. `winterm_window_list`/`winterm_ui_inspect` return a numeric `Handle` -- reuse that Handle for every subsequent call in the task instead of re-matching by title.
