# DEEPSEEK.md: Native Operating Instructions for DeepSeek Agents

This document defines native operating guidelines, chain-of-thought grounding patterns, and deterministic terminal execution workflows for **DeepSeek Agents** (DeepSeek-V3, DeepSeek-R1, and DeepSeek-Coder) utilizing **WinTerM**.

---

## Mission & Architecture
DeepSeek reasoning models excel at complex multi-step reasoning and algorithmic deduction. WinTerM provides DeepSeek with a deterministic Windows and Linux execution ground truth, eliminating parameter hallucinations and shell syntax errors.

---

## Connecting DeepSeek to WinTerM

Add WinTerM to your DeepSeek agent configuration (via MCP or OpenAI-compatible tool definitions):
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

WinTerM exports **37 production tools** organized into 5 functional layers:
1. **5W Cognitive Primitives**: `plan_terminal_task`, `explain_terminal_command`, `predict_command_impact`, `execute_terminal_command`, `diagnose_terminal_error`, `undo_last_terminal_action`.
2. **Linux & WSL2 Subsystem**: `winterm_linux_execute`, `winterm_linux_path_convert`, `winterm_linux_distro_list`, `winterm_linux_safety_check`, `winterm_linux_diagnose_error`.
3. **Knowledge Graph & Anti-Hallucination**: `winterm_graph_blast_radius`, `winterm_graph_validate_command`, `winterm_graph_remedy_error`, `winterm_graph_alternatives`, `winterm_graph_command_docs`, `winterm_graph_safety_check`.
4. **Desktop GUI & Perception**: `winterm_app_find`, `winterm_app_launch`, `winterm_app_close`, `winterm_app_learn`, `winterm_window_list`, `winterm_window_focus`, `winterm_window_resize`, `winterm_window_close`.
5. **UI Automation & Synthetic Input**: `winterm_ui_inspect`, `winterm_ui_click`, `winterm_ui_set_text`, `winterm_input_type`, `winterm_input_hotkey`, `winterm_input_mouse_click`, `winterm_input_mouse_drag`, `winterm_screen_state`, `winterm_screen_capture`.

---

## DeepSeek-R1 Chain-of-Thought (CoT) Alignment

When formulating reasoning traces in your `<think>` blocks, structure your deductions following WinTerM's **5W Cognitive Model**:

```
<think>
1. WHAT: Identify exact intent, target shell (PowerShell 5.1/7 vs WSL_BASH), and blast radius.
2. HOW: Validate cmdlet parameters with winterm_graph_validate_command to prevent hallucinations.
3. WHEN: Ensure preconditions (services started, paths created, ports free) are met.
4. WHY: Justify why this command is safer or more reliable than alternatives.
5. AFTER: Predict state diff and formulate an automated rollback command.
</think>
```

---

## Critical Execution Rules for DeepSeek Agents

1. **Anti-Hallucination Check**:
   - Before executing unfamiliar PowerShell cmdlets, query `winterm_graph_validate_command(cmdlet, params)`. If parameters are invalid, the graph suggests valid alternatives and types.
2. **Deterministic Shell Quoting**:
   - In PowerShell, paths with spaces MUST use the call operator: `& "C:\Program Files\..."`.
   - In Bash/WSL, paths MUST be escaped or single-quoted: `'/mnt/c/Program Files/...'`.
3. **No Headless Hanging**:
   - Never run interactive commands that wait for stdin (e.g. `rm -i`, `apt-get install` without `-y`, or `git push` without credentials).
   - WinTerM automatically injects non-interactive switches.
4. **UI Automation Tree First**:
   - When automating desktop applications, NEVER calculate blind screen coordinates.
   - Use `winterm_ui_inspect(window)` to get real `AutomationId` or element names.
   - Click semantically with `winterm_ui_click(window, element_query)`.

---

## Multi-Agent Coexistence (Simultaneous Operation)

DeepSeek agents frequently collaborate with **Gemini**, **Claude Code**, or **OpenCode** on the same machine:
- **Resource Locking**: Before binding a network port or focusing an app window, check or acquire a lease via `AgentSessionCoordinator`.
- **Independent Sessions**: DeepSeek instances should pass a unique `session_id` (e.g. `deepseek-worker-1`) to isolate undo stacks and execution history.
- **Shared Knowledge Graph**: All agents share the cached 10,374-node Windows Knowledge Graph in memory for zero-overhead validation.
