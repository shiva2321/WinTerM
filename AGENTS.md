# AGENTS.md: Universal Autonomous Agent Instructions for WinTerM

This file defines universal operating instructions for all autonomous AI agents (Claude Code, OpenCode, Google Gemini / Antigravity, DeepSeek, Cursor, OpenAI Swarm) operating on Windows and Linux/WSL.

---

## Mission
WinTerM equips AI agents with deterministic Windows Terminal and Linux/WSL2 mastery, interactive desktop GUI control, a 5W cognitive pipeline (What, How, When, Why, After), and multi-agent concurrency coordination.

---

## Tool Availability
When executing actions, use the **46 MCP tools** provided by WinTerM (`python -m winterm.tools.mcp_server`):
- **Core 5W Pipeline**: `plan_terminal_task`, `explain_terminal_command`, `predict_command_impact`, `execute_terminal_command`, `diagnose_terminal_error`, `undo_last_terminal_action`.
- **Linux & WSL2 Subsystem**: `winterm_linux_execute`, `winterm_linux_path_convert`, `winterm_linux_distro_list`, `winterm_linux_safety_check`, `winterm_linux_diagnose_error`.
- **Knowledge Graph**: `winterm_graph_blast_radius`, `winterm_graph_validate_command`, `winterm_graph_remedy_error`, `winterm_graph_alternatives`, `winterm_graph_command_docs`, `winterm_graph_safety_check`.
- **Application Lifecycle**: `winterm_app_find`, `winterm_app_launch`, `winterm_app_close`, `winterm_app_learn`.
- **Window Management**: `winterm_window_list`, `winterm_window_focus`, `winterm_window_resize`, `winterm_window_close`.
- **UI Automation & Input**: `winterm_ui_inspect`, `winterm_ui_click`, `winterm_ui_set_text`, `winterm_input_type`, `winterm_input_hotkey`, `winterm_input_mouse_click`, `winterm_input_mouse_drag`, `winterm_screen_state`, `winterm_screen_capture`.
- **Playbooks & Reusable Scripts**: `winterm_playbook_create`, `winterm_playbook_match_run`, `winterm_playbook_list`, `winterm_playbook_prune`.
- **Multi-Agent Swarm Subsystem**: `winterm_swarm_dispatch`, `winterm_swarm_board_read`, `winterm_swarm_board_post`, `winterm_swarm_suggestions`, `winterm_swarm_status`.

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
   - **After the first SENSE step resolves a window, target it by the numeric `Handle` (HWND) for every later call in the same task, not by title.** Window titles can change dynamically (unsaved-changes markers, the document's own content appearing in the title bar), so a title that matched during SENSE can silently stop matching by the time ACT/VERIFY run. Every window/UI tool accepts a `Handle` wherever it accepts a title.
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

---

## Script Justification Protocol (Direct Execution vs. Script Synthesis)
To conserve system resources, minimize disk I/O, and eliminate script bloat:
1. **Never build scripts for atomic one-liners**:
   - Single commands (e.g. `ipconfig`, `Get-Process`, `ls -la`, `docker ps`, `Stop-Process -Id 1234`, `git status`) MUST be executed directly via `execute_terminal_command` or `winterm_linux_execute`.
2. **Only synthesize scripts when strictly necessary**:
   - A task qualifies for script generation (`winterm_playbook_create`) **only and strictly if**:
     - It requires multi-step workflow sequencing ($\ge 2$ interdependent commands).
     - It requires conditional branching (`if/else`, `switch`, `case`).
     - It requires iterative loops (`foreach`, `while`, `for`).
     - It requires transactional error handling or compensation rollback (`try/catch/finally`, `trap`).
3. **Automated Enforcement**:
   - WinTerM's `ScriptJustificationGate` automatically intercepts single atomic commands, rejects script creation, and instructs direct terminal execution.
   - For recurring multi-step tasks, the candidate buffer auto-detects recurrence ($\ge 2$ runs) and compiles defensive playbooks with LRU quota management (max 50).

---

## Multi-Agent Swarm Orchestration & Layered Safety

WinTerM provides a decentralized sub-agent swarm coordinated by the main agent with strict capability scoping and a shared blackboard message board:

1. **Sub-Agent Dispatching & Privilege Scopes**:
   - Dispatch sub-agents dynamically with `winterm_swarm_dispatch(name, privilege, goal)`.
   - **Scopes**:
     - `READ_ONLY_AUDIT`: Strictly diagnostic inspection; filesystem modifications and process kills blocked.
     - `UI_OPERATOR`: Desktop UI automation and interaction; terminal shells restricted.
     - `TERMINAL_EXECUTOR`: PowerShell and CMD command execution with safety bounds.
     - `NETWORK_INSPECTOR`: Network diagnostics and port scanning; no desktop clicks.
     - `FULL_SUPERVISOR`: Unrestricted administrative oversight across terminal and GUI.
2. **Shared Message Board (Blackboard Architecture)**:
   - All sub-agents and the main agent share an in-memory message bus (`winterm_swarm_board_read`, `winterm_swarm_board_post`).
   - Message types: `DIRECTIVE`, `PROGRESS_UPDATE`, `TASK_COMPLETED`, `TASK_FAILED`, `SUGGESTION_PROPOSED`, `ALERT`, `STATUS_REPORT`.
   - Main agent broadcasts high-level directives; sub-agents report progress and post structured telemetry.
3. **Proactive Suggestions Pipeline**:
   - Sub-agents autonomously identify optimizations, potential hazards, and needed remediations.
   - Suggestions are submitted to the board for main agent oversight (`winterm_swarm_suggestions(action="review")`).
   - Main agent retains deterministic approval authority (`action="approve"` or `action="reject"`).
4. **Layered Fault-Tolerant Safety & Fluke Containment**:
   - **SubAgentSandbox**: Every sub-agent action is bounded by maximum step quotas, execution timeouts, and action category fences.
   - **Fluke Containment**: Unhandled OS exceptions, API timeouts, or unexpected glitches are caught and isolated (`fluke_contained=True`). An isolated sub-agent fluke **never crashes the main agent or sister sub-agents**.
   - **Circuit Breakers**: Repeated failures trip the circuit breaker, automatically isolating the faulty sub-agent, logging a diagnostic fault record to the message board, and alerting the supervisor.

