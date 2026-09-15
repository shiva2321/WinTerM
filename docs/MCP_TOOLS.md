# WinTerM: 54 Model Context Protocol (MCP) Tools Reference

WinTerM exposes **54 production tools** via the standard Model Context Protocol (MCP) JSON-RPC server (`python -m winterm.tools.mcp_server`). These tools provide complete sensory perception, deterministic execution, and cognitive safeguards for any MCP-compliant AI client (Claude Code, Antigravity, Cursor, Windsurf, OpenCode).

---

## Tool Categories Index

| Category | Count | Primary Focus |
| :--- | :---: | :--- |
| **1. Core 5W Cognitive Pipeline** | 6 | Planning, command explanation, impact simulation, execution, diagnostics, rollback. |
| **2. Linux & WSL2 Subsystem** | 5 | Path conversion, bash execution, distro management, safety audits, error diagnosis. |
| **3. Knowledge Graph Engine** | 6 | Blast radius calculation, parameter validation, error remediation, alternatives, safety. |
| **4. Application Lifecycle** | 4 | Discovery across AppsFolder/StartMenu/Registry, launch, learning, graceful/forceful close. |
| **5. Window Management** | 4 | Top-level enumeration, foreground focus with verified restoration, resizing, close. |
| **6. UI Automation & Hardware Input** | 9 | Semantic tree inspection, native clicks, text value injection, mouse clicks/drag, hotkeys. |
| **7. Advanced UI Perception & Mental Grounding** | 8 | Screen Mental Map, WinRT OCR, Set-of-Mark badges, smart cascading clicks, hover, scroll-to-view, wait-change. |
| **8. Playbooks & Reusable Tasks** | 4 | Defensive script synthesis, fast-path LRU execution, pruning, catalog listing. |
| **9. Multi-Agent Swarm** | 5 | Scoped sub-agent dispatching, shared message board post/read, proactive suggestions, telemetry. |
| **Total** | **54** | Complete operating system mastery. |

---

## 1. Core 5W Cognitive Pipeline

### `plan_terminal_task`
Decomposes a natural language goal into an ordered Directed Acyclic Graph (DAG) of atomic terminal actions.
- **Parameters**: `goal` (string, required)
- **Output**: JSON execution plan with step IDs, titles, shells, and dependencies.

### `explain_terminal_command`
Explains any PowerShell or CMD command across the 5W model (What, How, When, Why, After).
- **Parameters**: `command` (string, required), `shell` (string, optional: `powershell_51`, `pwsh`, `cmd`)

### `predict_command_impact`
Simulates command blast radius, risk scoring, state diff predictions, and rollback requirements.
- **Parameters**: `command` (string, required), `shell` (string, optional)

### `execute_terminal_command`
Executes a terminal command safely with quoting normalization, call operators, and non-interactive guards.
- **Parameters**: `command` (string, required), `shell` (string, optional), `elevated` (bool, default `false`), `dry_run` (bool, default `false`), `confirm_high_risk` (bool, default `false`)

### `diagnose_terminal_error`
Translates Windows HRESULTs, Win32 error codes, and exception traces into actionable recovery steps.
- **Parameters**: `error_output` (string, required), `command` (string, optional)

### `undo_last_terminal_action`
Rolls back the most recent state mutation using compensating actions recorded in the session ledger.
- **Parameters**: `session_id` (string, optional)

---

## 2. Linux & WSL2 Subsystem

### `winterm_linux_execute`
Executes bash or POSIX shell commands inside WSL2 Linux with deterministic safety audits and non-interactive flag injection.
- **Parameters**: `command` (string, required), `distro` (string, optional), `user` (string, optional)

### `winterm_linux_path_convert`
Translates filesystem paths between Windows (`C:\...`) and Linux (`/mnt/c/...`).
- **Parameters**: `path` (string, required), `to_linux` (bool, default `true`), `distro` (string, optional)

### `winterm_linux_distro_list`
Lists installed WSL distributions, running states, and default distribution.
- **Parameters**: None

### `winterm_linux_safety_check`
Audits a proposed bash command against destructive patterns (`rm -rf /`, fork bombs, raw block writes).
- **Parameters**: `command` (string, required)

### `winterm_linux_diagnose_error`
Analyzes Linux exit codes (126, 127, 137 OOM) and generates remediation templates.
- **Parameters**: `command` (string, required), `exit_code` (int, required), `stderr` (string, required)

---

## 3. Knowledge Graph Engine

### `winterm_graph_blast_radius`
Calculates cascading direct and transitive service/resource dependencies using the 10,374-node graph.
- **Parameters**: `service_name` (string, required), `depth` (int, default `2`)

### `winterm_graph_validate_command`
Validates command parameters against Microsoft documentation, flagging deprecated or hallucinated switches.
- **Parameters**: `command` (string, required)

### `winterm_graph_remedy_error`
Queries the graph for verified multi-step recovery procedures for a specific error code.
- **Parameters**: `error_code` (string, required)

### `winterm_graph_alternatives`
Finds equivalent commands across shells (e.g. PowerShell cmdlet vs. native Win32 binary).
- **Parameters**: `command` (string, required)

### `winterm_graph_command_docs`
Retrieves official Microsoft syntax specifications and parameter descriptions.
- **Parameters**: `binary_name` (string, required)

### `winterm_graph_safety_check`
Classifies commands into safety tiers (`SAFE`, `DESTRUCTIVE`, `CREDENTIAL_SENSITIVE`, `PRIVILEGED`).
- **Parameters**: `command` (string, required)

---

## 4. Application Lifecycle

### `winterm_app_find`
Searches installed applications across `shell:AppsFolder`, Start Menu shortcuts, and Registry App Paths.
- **Parameters**: `query` (string, optional), `limit` (int, default `50`)

### `winterm_app_launch`
Launches any Win32 executable, UWP packaged app, or protocol URI.
- **Parameters**: `target` (string, required), `arguments` (string, optional), `elevated` (bool, default `false`)

### `winterm_app_close`
Closes applications gracefully via `WM_CLOSE` / `CloseMainWindow` or forcefully via `Stop-Process`.
- **Parameters**: `target` (string, required), `force` (bool, default `false`)

### `winterm_app_learn`
Records launching parameters, binary locations, and window characteristics for an application into memory.
- **Parameters**: `name` (string, required), `binary_path` (string, required)

---

## 5. Window Management

### `winterm_window_list`
Lists visible top-level windows with title, PID, numeric HWND handle, bounds `(X, Y, W, H)`, and state (`Normal`, `Minimized`, `Maximized`).
- **Parameters**: `query` (string, optional)

### `winterm_window_focus`
Restores minimized windows (`SW_RESTORE`), brings window to top, and verifies foreground lock via `OpenInputDesktop`. Always target by numeric `Handle` (HWND).
- **Parameters**: `identifier` (string, required: window title or numeric HWND)

### `winterm_window_resize`
Reposition and size any window on screen.
- **Parameters**: `identifier` (string, required), `x` (int, required), `y` (int, required), `width` (int, required), `height` (int, required)

### `winterm_window_close`
Closes a target window via native `WM_CLOSE`.
- **Parameters**: `identifier` (string, required)

---

## 6. UI Automation & Hardware Input

### `winterm_ui_inspect`
Enumerates UIAutomation elements (buttons, edit controls, menus) with AutomationId and center coordinates.
- **Parameters**: `window` (string, required), `max_depth` (int, default `3`)

### `winterm_ui_click`
Clicks a control using native UIAutomation `InvokePattern` with mouse click fallback.
- **Parameters**: `window` (string, required), `control_name` (string, required)

### `winterm_ui_set_text`
Sets text inside an edit control using `ValuePattern` with `SendKeys` fallback.
- **Parameters**: `window` (string, required), `control_name` (string, required), `text` (string, required)

### `winterm_input_type`
Dispatches hardware-level Unicode keystrokes using Win32 `SendInput` (safe for modern WinUI3 and Notepad apps).
- **Parameters**: `text` (string, required), `interval_ms` (int, default `10`)

### `winterm_input_hotkey`
Presses key combinations and system hotkeys (`win r`, `ctrl l`, `alt tab`, `ctrl shift p`).
- **Parameters**: `keys` (string or array of strings, required)

### `winterm_input_mouse_click`
Executes a window-contained coordinate click, validating that point lies inside target HWND (`ClickInWindow`).
- **Parameters**: `x` (int, required), `y` (int, required), `button` (string, default `left`), `window` (string, optional)

### `winterm_input_mouse_drag`
Simulates mouse drag from start coordinates to destination coordinates.
- **Parameters**: `start_x` (int), `start_y` (int), `end_x` (int), `end_y` (int)

### `winterm_screen_state`
Inspects display metrics, virtual screen size, DPI scale, and active cursor position.
- **Parameters**: None

### `winterm_screen_capture`
Captures a full-resolution PNG screenshot of the desktop or scoped to a specific target window.
- **Parameters**: `output_path` (string, required), `window_query` (string, optional)

---

## 7. Advanced UI Perception & Grounding

### `winterm_ui_ocr`
Executes hardware-accelerated **WinRT Native Windows OCR** directly against the target window's GDI canvas. Zero external dependencies.
- **Parameters**: `window` (string, required), `language` (string, default `en-US`)

### `winterm_ui_som_annotate`
Generates **Set-of-Mark (SoM)** visual grounding overlays by drawing numbered badge tags (`[1]`, `[2]`, `[3]`) directly over interactive controls and OCR word boxes.
- **Parameters**: `window` (string, required), `output_path` (string, required), `max_marks` (int, default `50`)

### `winterm_ui_smart_click`
Multi-strategy cascading click: tries UIAutomation first, cascades to Native Windows OCR text matching, and falls back to coordinate click.
- **Parameters**: `window` (string, required), `query` (string, required)

### `winterm_ui_perceive`
Generates a structured Markdown perception map combining OCR text blocks and UIAutomation hierarchy.
- **Parameters**: `window` (string, required)

### `winterm_ui_wait_change`
Asynchronously polls window visual hash to confirm when a UI state transition or page load has completed, eliminating race conditions.
- **Parameters**: `window` (string, required), `timeout_ms` (int, default `3000`), `min_diff_pct` (number, default `0.5`)

### `winterm_screen_mental_map`
Builds and maintains a persistent, multi-layered cognitive mental map of the target window or desktop. Fuses UIAutomation and WinRT OCR into spatial layers (`desktop`, `inactive_windows`, `active_workspace`, `modals`) and functional zones (`header`, `navigation`, `content`, `sidebar`, `footer`), infers semantic roles (`BUTTON`, `INPUT`, `SEARCH_BOX`, `TAB`, `LINK`), and derives prioritized Action Affordances (`CLICK`, `TYPE`, `SCROLL`).
- **Parameters**: `window_identifier` (string, optional), `max_items` (int, default `60`), `include_ocr` (bool, default `true`)

### `winterm_ui_hover`
Performs smooth cubic Bezier mouse movement to hover over a target UI element (via UIA/OCR query) or relative window coordinates to trigger dynamic hover menus, tooltips, or preview cards. Enforces `WindowFromPoint` containment safety.
- **Parameters**: `window_identifier` (string, required), `element_query` (string, optional), `rel_x` (int, optional), `rel_y` (int, optional), `dwell_ms` (int, default `500`), `control_type` (string, optional)

### `winterm_ui_scroll_into_view`
Calibrates and dispatches mouse wheel ticks to bring off-screen or off-center elements cleanly into the viewport center. Eliminates blind mouse scrolling.
- **Parameters**: `window_identifier` (string, required), `target_rel_y` (int, required), `viewport_center_y` (int, default `400`)

---

## 8. Playbooks & Reusable Tasks

### `winterm_playbook_create`
Compiles multi-step tasks requiring loops, branches, or compensation logic into parameterized defensive scripts.
- **Parameters**: `task_name` (string, required), `intent` (string, required), `steps` (array, required)

### `winterm_playbook_match_run`
Matches recurring goals against stored playbooks and executes the compiled script without re-planning.
- **Parameters**: `situation` (string, required), `dry_run` (bool, default `false`)

### `winterm_playbook_list`
Lists all cached playbooks, parameter schemas, safety classifications, and hit counts.
- **Parameters**: None

### `winterm_playbook_prune`
Prunes stale playbooks down to quota limits using Least Recently Used (LRU) eviction.
- **Parameters**: `max_items` (int, default `50`)

---

## 9. Multi-Agent Swarm Subsystem

### `winterm_swarm_dispatch`
Spawns specialized autonomous sub-agents bounded by privilege scopes:
- `READ_ONLY_AUDIT`: Strictly diagnostics; process kills and file modifications blocked.
- `UI_OPERATOR`: GUI interaction and clicking allowed; terminal execution restricted.
- `TERMINAL_EXECUTOR`: Command execution allowed with safety bounds.
- `NETWORK_INSPECTOR`: Network diagnostics and port inspection only.
- `FULL_SUPERVISOR`: Unrestricted administrative oversight.
- **Parameters**: `name` (string, required), `privilege` (string, required), `goal` (string, required)

### `winterm_swarm_board_post`
Posts an instruction, directive, or announcement from the supervising agent to the shared blackboard.
- **Parameters**: `content` (string, required), `message_type` (string, default `DIRECTIVE`)

### `winterm_swarm_board_read`
Reads messages, progress updates, and telemetry from all active sub-agents.
- **Parameters**: `limit` (int, default `20`), `filter_type` (string, optional)

### `winterm_swarm_suggestions`
Inspects, approves, or rejects proactive recommendations submitted by sub-agents.
- **Parameters**: `action` (string: `review`, `approve`, `reject`), `suggestion_id` (string, optional)

### `winterm_swarm_status`
Returns swarm operational telemetry, active sub-agents, circuit-breaker states, and fault records.
- **Parameters**: None
