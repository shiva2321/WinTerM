# GEMINI.md: Native Operating Instructions for Google Gemini Agents

This document defines native operating guidelines, tool call patterns, and multimodal execution workflows for **Google Gemini Agents** (Google Antigravity, Gemini CLI, Vertex AI / Google AI Studio agents) utilizing **WinTerM**.

---

## Mission & Role
You are an autonomous AI Agent powered by Google Gemini. With WinTerM, you have deterministic control over Windows Terminal (PowerShell 5.1/7, CMD), Linux/WSL2 environments, and interactive desktop applications.

---

## Tool Calling & Setup

### Connecting via Antigravity / Gemini CLI (`mcp_config.json`)
Add WinTerM to your Gemini agent's MCP configuration:
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

WinTerM exposes **46 production tools** covering:
- **Core 5W Pipeline**: `plan_terminal_task`, `explain_terminal_command`, `predict_command_impact`, `execute_terminal_command`, `diagnose_terminal_error`, `undo_last_terminal_action`.
- **Linux & WSL2**: `winterm_linux_execute`, `winterm_linux_path_convert`, `winterm_linux_distro_list`, `winterm_linux_safety_check`, `winterm_linux_diagnose_error`.
- **Knowledge Graph**: `winterm_graph_blast_radius`, `winterm_graph_validate_command`, `winterm_graph_remedy_error`, `winterm_graph_alternatives`, `winterm_graph_command_docs`, `winterm_graph_safety_check`.
- **Desktop Application Lifecycle**: `winterm_app_find`, `winterm_app_launch`, `winterm_app_close`, `winterm_app_learn`.
- **Window Management**: `winterm_window_list`, `winterm_window_focus`, `winterm_window_resize`, `winterm_window_close`.
- **UI Automation & Input**: `winterm_ui_inspect`, `winterm_ui_click`, `winterm_ui_set_text`, `winterm_input_type`, `winterm_input_hotkey`, `winterm_input_mouse_click`, `winterm_input_mouse_drag`, `winterm_screen_state`, `winterm_screen_capture`.
- **Playbooks & Reusable Scripts**: `winterm_playbook_create`, `winterm_playbook_match_run`, `winterm_playbook_list`, `winterm_playbook_prune`.
- **Multi-Agent Swarm**: `winterm_swarm_dispatch`, `winterm_swarm_board_read`, `winterm_swarm_board_post`, `winterm_swarm_suggestions`, `winterm_swarm_status`.

---

## Multimodal Visual Perception Grounding (Gemini Superpower)

Gemini models possess state-of-the-art native vision. WinTerM provides visual feedback tools tailored for multimodal reasoning:

1. **Verify Visual State After Key Actions**:
   ```json
   winterm_screen_capture({
     "output_path": "d:\\Agent_toolkit\\gemini_audit.png",
     "window_query": "Calculator"
   })
   ```
2. **Handle Non-Standard Windows (Canvas / Direct2D / Games)**:
   - For Win32, WPF, and UWP apps: Prefer semantic `winterm_ui_inspect` and `winterm_ui_click`.
   - For apps lacking UI Automation trees: Capture screenshot with `winterm_screen_capture`, compute relative coordinates inside the window, and invoke `winterm_input_mouse_click`.

---

## Linux & WSL2 Execution Protocol

When executing bash, shell scripts, or container operations:
1. **Safety Audit**: Run `winterm_linux_safety_check(command)` to detect destructive patterns (`rm -rf /`, raw disk blocks, fork bombs).
2. **Execute**: Run `winterm_linux_execute(command)` — non-interactive switches (`-y`, `DEBIAN_FRONTEND=noninteractive`) are automatically injected.
3. **Path Translation**: Use `winterm_linux_path_convert(path, to_linux=True)` when sharing file paths between Windows (`C:\...`) and WSL (`/mnt/c/...`).
4. **Self-Healing**: If a command fails (e.g. exit code 127, 126, 137 OOM), pass output to `winterm_linux_diagnose_error` for automated recovery templates.

---

## Multi-Agent Coexistence (Simultaneous Operation)

When multiple agents (Gemini, DeepSeek, Claude Code, OpenCode) are operating concurrently on the same host:
- **Resource Locking**: Acquire a lease on sensitive windows or network ports:
  `AgentSessionCoordinator.acquire_resource_lock(resource_id="port:8080", session_id="gemini-run-1", framework="gemini")`
- **Window Courtesy**: Do not close or minimize windows owned by other active agents. Inspect `winterm_window_list` before modifying window state.
- **Session Ledger**: WinTerM maintains state timelines per session; avoid clobbering other agents' active undo stacks.

---

## Script Justification Protocol (Direct Terminal Execution vs. Playbooks)

To maximize runtime efficiency and prevent script sprawl:
1. **Direct Execution for Atomic Commands**:
   - Never build or request a script for atomic commands (`Get-Process`, `ipconfig`, `ls -la`, `docker ps`, `Stop-Process -Id 1234`). Execute them directly with `execute_terminal_command` or `winterm_linux_execute`.
2. **Script Synthesis Strict Criteria**:
   - Only call `winterm_playbook_create` for tasks requiring multi-step orchestration ($\ge 2$ interdependent commands), conditional branches (`if/else`), loops (`for/while`), or transactional recovery (`try/catch`).
3. **Automated Enforcement**:
   - `ScriptJustificationGate` rejects atomic commands from being scripted, guiding you to direct execution while auto-promoting recurring multi-step tasks into parameter-generalized playbooks.

---

## Multi-Agent Swarm Orchestration & Scoped Supervision

Gemini agents can orchestrate autonomous sub-agent swarms across Windows:
- **Dispatch Scoped Specialists**:
  ```json
  winterm_swarm_dispatch({
    "name": "AuditBot",
    "privilege": "read_only_audit",
    "goal": "Verify service statuses and network listening ports"
  })
  ```
- **Coordinate on the Message Board**:
  Post directives and monitor reports using `winterm_swarm_board_read` and `winterm_swarm_board_post`.
- **Suggestions Review**:
  Inspect proactive ideas generated by sub-agents:
  ```json
  winterm_swarm_suggestions({"action": "review"})
  ```
  Approve or reject with deterministic oversight:
  ```json
  winterm_swarm_suggestions({"action": "approve", "suggestion_id": "sug-..."})
  ```
- **Layered Fluke Containment**:
  Sub-agents run under circuit-breaker sandboxes. If a sub-agent throws an unhandled OS error or crashes, it is contained (`fluke_contained=True`), leaving your main loop completely stable and responsive.

