"""Agent Tool Definitions: Standardized tools for LLM agent integration (Gemini, Claude, OpenAI, LangChain)."""

import json
from typing import Dict, Any, List, Optional
from winterm.agent.winterm_agent import WinTermAgent
from winterm.models.context import ShellType
from winterm.models.intent import PlanStep, ActionCategory
from winterm.knowledge.commands_db import WindowsCommandDatabase
from winterm.knowledge.error_catalog import WindowsErrorCatalog
from winterm.knowledge.shell_matrix import ShellMatrix
from winterm.knowledge.reliability_rules import ReliabilityRules


# Shared singleton agent instance for tool executions
_agent_instance = WinTermAgent()


def plan_terminal_task(goal: str) -> Dict[str, Any]:
    """Decomposes a high-level goal into a staged execution plan (WHAT to do).
    
    Args:
        goal: The natural language task or objective on Windows (e.g. 'kill process on port 8080').
    """
    plan = _agent_instance.plan(goal)
    return plan.model_dump()


def explain_terminal_command(
    intent: str,
    command: str,
    target_shell: str = "powershell_51",
) -> Dict[str, Any]:
    """Analyzes a command and generates a 5W Decision Trace explaining What, How, When, Why, and What Happens After.
    
    Args:
        intent: The objective of the command.
        command: The concrete command or cmdlet string.
        target_shell: Shell type ('powershell_51', 'pwsh', or 'cmd').
    """
    shell_enum = ShellType(target_shell) if target_shell in [s.value for s in ShellType] else ShellType.POWERSHELL_51
    step = PlanStep(
        step_id="query",
        title=intent,
        category=ActionCategory.CUSTOM,
        raw_intent=intent,
        command=command,
        target_shell=shell_enum,
    )
    trace = _agent_instance.explain(step)
    return trace.model_dump()


def predict_command_impact(command: str, target_shell: str = "powershell_51") -> Dict[str, Any]:
    """Forecasts state diff (files, registry, processes, ports), risk score, and rollback command before execution.
    
    Args:
        command: The command line to simulate.
        target_shell: Shell environment ('powershell_51', 'pwsh', or 'cmd').
    """
    shell_enum = ShellType(target_shell) if target_shell in [s.value for s in ShellType] else ShellType.POWERSHELL_51
    step = PlanStep(
        step_id="predict",
        title="Simulated step",
        category=ActionCategory.CUSTOM,
        raw_intent=command,
        command=command,
        target_shell=shell_enum,
    )
    impact = _agent_instance.predictor.predict_step_impact(step)
    return impact.model_dump()


def execute_terminal_command(
    command: str,
    target_shell: str = "powershell_51",
    dry_run: bool = False,
    timeout_seconds: int = 60,
    auto_heal: bool = True,
    confirm_high_risk: bool = False,
) -> Dict[str, Any]:
    """Executes a terminal command on Windows with strict reliability, UTF-8 safety, and self-healing.

    Args:
        command: The command string to execute.
        target_shell: Target shell ('powershell_51', 'pwsh', or 'cmd').
        dry_run: If True, simulates execution without modifying system state.
        timeout_seconds: Max execution duration before terminating process tree.
        auto_heal: If True, automatically attempts remediation if command fails with known error.
        confirm_high_risk: If True, allows high-risk/destructive commands to run (DANGEROUS).
    """
    shell_enum = ShellType(target_shell) if target_shell in [s.value for s in ShellType] else ShellType.POWERSHELL_51
    step = PlanStep(
        step_id="exec",
        title="Direct execution",
        category=ActionCategory.CUSTOM,
        raw_intent=command,
        command=command,
        target_shell=shell_enum,
        timeout_seconds=timeout_seconds,
    )
    exec_res, verif_res, trace = _agent_instance.execute_step(
        step, dry_run=dry_run, auto_heal=auto_heal, confirm_high_risk=confirm_high_risk
    )
    return {
        "execution": exec_res.model_dump(),
        "verification": verif_res.model_dump() if verif_res else None,
        "decision_trace": trace.model_dump(),
    }


def diagnose_terminal_error(
    stderr: str,
    exit_code: int = 1,
    command: str = "",
) -> Dict[str, Any]:
    """Analyzes a failed command's output, identifies the Windows error signature, and generates a self-healing proposal.
    
    Args:
        stderr: The captured standard error string.
        exit_code: Process return code.
        command: The command that failed.
    """
    proposal = WindowsErrorCatalog.diagnose(
        stderr=stderr,
        stdout="",
        exit_code=exit_code,
        failed_command=command,
    )
    if proposal:
        return {"matched": True, "proposal": proposal.model_dump()}
    return {"matched": False, "message": "No matching self-healing pattern found."}


def query_windows_knowledge(query: str) -> Dict[str, Any]:
    """Queries the built-in Windows Terminal knowledge base for canonical commands, shell rules, and pitfalls.
    
    Args:
        query: Topic to search (e.g. 'quoting', 'encoding', 'ports', 'cim', 'services').
    """
    q = query.lower()
    matches = []
    for key, cmd in WindowsCommandDatabase.CATALOG.items():
        if q in key or q in cmd.why.lower() or q in cmd.category.value:
            matches.append({
                "key": key,
                "category": cmd.category.value,
                "powershell": cmd.powershell_template,
                "cmd": cmd.cmd_template,
                "why": cmd.why,
                "alternative_to": cmd.modern_alternative_to,
            })
    return {
        "query": query,
        "results_count": len(matches),
        "results": matches,
    }


def undo_last_terminal_action() -> Dict[str, Any]:
    """Rolls back the most recent state-modifying action from the undo stack."""
    res = _agent_instance.undo_last_action()
    if res:
        return {"undone": True, "result": res.model_dump()}
    return {"undone": False, "message": "No reversible actions found in rollback stack."}


# =============================================================================
# KNOWLEDGE GRAPH TOOLS
# =============================================================================

def winterm_graph_blast_radius(resource: str, depth: int = 2) -> Dict[str, Any]:
    """Calculates cascading downstream dependents and blast radius if a service or resource is modified.
    
    Args:
        resource: Target Windows service or state primitive (e.g. 'RpcSs', 'LanmanServer', 'Winmgmt').
        depth: Graph cascade traversal depth (default 2).
    """
    report = _agent_instance.calculate_blast_radius(resource, depth=depth)
    return report.model_dump()


def winterm_graph_validate_command(command: str) -> Dict[str, Any]:
    """Validates command syntax and parameters against the Windows Knowledge Graph to prevent LLM hallucinations.
    
    Args:
        command: Full command or cmdlet string with parameters (e.g. 'Get-Process -Name svchost -Id 1234').
    """
    res = _agent_instance.validate_command(command)
    return res.model_dump()


def winterm_graph_remedy_error(error_code: str) -> Dict[str, Any]:
    """Resolves an HRESULT, Win32 error code, or exception name to an ordered multi-step remediation path.
    
    Args:
        error_code: Windows error signature (e.g. '0x80070005', '10048', 'ERROR_SHARING_VIOLATION').
    """
    path = _agent_instance.find_error_remedy(error_code)
    if path:
        return {"matched": True, "remediation": path.model_dump()}
    return {"matched": False, "message": f"No remediation path indexed for '{error_code}'."}


def winterm_graph_alternatives(command: str) -> Dict[str, Any]:
    """Discovers equivalent native Win32 tools or PowerShell cmdlets for a given command.
    
    Args:
        command: Command or cmdlet name (e.g. 'Stop-Process', 'reg.exe', 'robocopy.exe').
    """
    alts = _agent_instance.find_alternatives(command)
    return {
        "command": command,
        "alternatives": alts,
    }


def winterm_graph_info() -> Dict[str, Any]:
    """Returns topological metrics and ontological breakdown of the Windows Knowledge Graph."""
    return _agent_instance.knowledge_graph.get_metrics()


def winterm_graph_search_intent(query: str, top_k: int = 5) -> Dict[str, Any]:
    """Resolves natural language intents to real Windows commands from the command dataset.
    
    Args:
        query: Natural language query (e.g. 'find text files', 'kill process by port').
        top_k: Maximum number of matches to return (default 5).
    """
    matches = _agent_instance.search_intent(query, top_k=top_k)
    return {
        "query": query,
        "count": len(matches),
        "matches": matches,
    }


def winterm_graph_command_docs(command: str) -> Dict[str, Any]:
    """Retrieves official Microsoft documentation, syntax, and parameter definitions for a Windows command.
    
    Args:
        command: Windows command name (e.g. 'robocopy', 'fsutil', 'reg', 'netsh').
    """
    docs = _agent_instance.get_command_docs(command)
    if docs:
        return {"matched": True, "documentation": docs}
    return {"matched": False, "message": f"No documentation indexed for '{command}'."}


def winterm_graph_safety_check(command: str) -> Dict[str, Any]:
    """Classifies command safety tier, credential sensitivity, and warnings using the SFT safety corpus.
    
    Args:
        command: Command or cmdlet string to evaluate (e.g. 'Format-Volume', 'reg delete HKLM\\Software').
    """
    safety = _agent_instance.check_command_safety(command)
    return safety


def winterm_app_find(query: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """Discovers installed Windows applications across shell:AppsFolder, Start Menu, and Registry.
    
    CRITICAL AGENT INSTRUCTION:
    ALWAYS call this tool BEFORE attempting to launch an unfamiliar application to confirm it is actually installed.
    Never assume an executable exists. If not found, inform the user or propose installing it via winget.
    """
    exec_res, _, _ = _agent_instance.find_applications(query=query, limit=limit)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_app_launch(target: str, arguments: Optional[str] = None, elevated: bool = False) -> Dict[str, Any]:
    """Launches any Windows application (Win32 executable, UWP Store app, or protocol URI like ms-paint:).
    
    Args:
        target: Executable path, Start menu app name, UWP AppID, or protocol URI (e.g. 'notepad.exe', 'calc.exe', 'ms-settings:').
        arguments: Optional command-line arguments to pass to the launched process.
        elevated: If True, launches process with Administrator privileges (RunAs).
    """
    exec_res, _, _ = _agent_instance.launch_application(target=target, arguments=arguments, elevated=elevated)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_app_close(target: str, force: bool = False) -> Dict[str, Any]:
    """Gracefully closes or forcefully terminates a running application."""
    exec_res, _, _ = _agent_instance.close_application(target=target, force=force)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_app_learn(target: str) -> Dict[str, Any]:
    """Probes local help (--help, /?), parses options, cross-references Knowledge Graph, and generates operational guide."""
    return _agent_instance.learn_application(target)


def winterm_window_list(query: Optional[str] = None) -> Dict[str, Any]:
    """Lists visible top-level windows with title, PID, handle (HWND), bounds, and state."""
    exec_res, _, _ = _agent_instance.list_windows(query=query)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_window_focus(identifier: str) -> Dict[str, Any]:
    """Brings an application window to the foreground and restores it if minimized.
    
    Args:
        identifier: Window title substring or numeric window handle (HWND).
    """
    exec_res, _, _ = _agent_instance.focus_window(identifier=identifier)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_window_resize(identifier: str, x: int, y: int, width: int, height: int) -> Dict[str, Any]:
    """Repositions and resizes an application window."""
    exec_res, _, _ = _agent_instance.resize_window(identifier, x, y, width, height)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_window_close(identifier: str) -> Dict[str, Any]:
    """Sends a native Win32 WM_CLOSE message to gracefully close an application window.
    
    Args:
        identifier: Window title substring or numeric window handle (HWND).
    """
    exec_res, _, _ = _agent_instance.close_window(identifier)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_ui_inspect(window_identifier: str, max_items: int = 100) -> Dict[str, Any]:
    """Inspects all UI Automation elements (buttons, inputs, menus) inside a window.
    
    CRITICAL AGENT INSTRUCTION:
    ALWAYS inspect the UI tree before clicking or typing. Discover real button names, ControlTypes,
    AutomationIds, and bounding boxes rather than guessing blind screen coordinates.
    """
    exec_res, _, _ = _agent_instance.inspect_window_elements(window_identifier, max_items=max_items)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_ui_click(window_identifier: str, element_query: str) -> Dict[str, Any]:
    """Clicks an element by name or automation ID using native UIAutomation InvokePattern with mouse fallback."""
    exec_res, _, _ = _agent_instance.click_ui_element(window_identifier, element_query)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_ui_set_text(window_identifier: str, element_query: str, text: str) -> Dict[str, Any]:
    """Sets text inside an input or edit control using native UIAutomation ValuePattern with SendKeys fallback."""
    exec_res, _, _ = _agent_instance.set_ui_element_text(window_identifier, element_query, text)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_input_type(text: str, interval_ms: int = 10) -> Dict[str, Any]:
    """Simulates typing text via Windows SendKeys."""
    exec_res, _, _ = _agent_instance.type_text(text, interval_ms=interval_ms)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_input_hotkey(keys: List[str]) -> Dict[str, Any]:
    """Simulates pressing a keyboard hotkey or key combination (e.g. ['ctrl', 's'], ['win', 'r'])."""
    exec_res, _, _ = _agent_instance.press_hotkey(keys)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_input_mouse_click(x: int, y: int, button: str = "left", double: bool = False) -> Dict[str, Any]:
    """Moves cursor to (X, Y) and performs mouse click. Use coordinates obtained from winterm_ui_inspect."""
    exec_res, _, _ = _agent_instance.mouse_click(x, y, button=button, double=double)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_input_mouse_drag(start_x: int, start_y: int, end_x: int, end_y: int) -> Dict[str, Any]:
    """Performs a drag-and-drop mouse gesture from start to end coordinates."""
    exec_res, _, _ = _agent_instance.mouse_drag(start_x, start_y, end_x, end_y)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_screen_state() -> Dict[str, Any]:
    """Inspects live display metrics, screen resolution, active cursor position, and foreground window info.
    
    CRITICAL AGENT INSTRUCTION:
    Call this at the beginning of a desktop interaction session to establish screen bounds and verify interactive desktop session.
    """
    exec_res, _, _ = _agent_instance.get_screen_state()
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_screen_capture(output_path: str, window_query: Optional[str] = None) -> Dict[str, Any]:
    """Captures a high-resolution visual screenshot of the full desktop or a target window and saves as PNG.
    
    CRITICAL AGENT INSTRUCTION:
    Use this tool to visually verify UI state after actions, or to perceive apps that lack UIAutomation trees (Canvas, games, etc.).
    
    Args:
        output_path: Absolute file path to save the PNG screenshot (e.g. 'd:\\Agent_toolkit\\perception.png').
        window_query: Optional window title substring to capture only that window.
    """
    exec_res, _, _ = _agent_instance.capture_screen(output_path, window_query=window_query)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_linux_execute(
    command: str,
    distro: Optional[str] = None,
    timeout_seconds: int = 60,
) -> Dict[str, Any]:
    """Executes a bash or POSIX command in Linux or WSL2 with deterministic safety validation and self-healing.
    
    Args:
        command: Linux bash command line to execute.
        distro: Optional WSL distribution name (e.g. 'Ubuntu', 'Debian').
        timeout_seconds: Subprocess timeout in seconds (default 60).
    """
    from winterm.knowledge.linux_safety import LinuxSafetyGuard
    from winterm.knowledge.linux_errors import LinuxErrorCatalog

    # 1. Deterministic safety evaluation
    verdict = LinuxSafetyGuard.evaluate(command)
    if verdict.label == "destructive":
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"BLOCKED BY LINUX SAFETY GUARD: {verdict.warning} (Target: {verdict.matched_target})",
            "safety_verdict": {
                "label": verdict.label,
                "is_dangerous": verdict.is_dangerous,
                "warning": verdict.warning,
            },
        }

    # 2. Non-interactive switch enforcement
    sanitized_cmd = LinuxSafetyGuard.make_non_interactive(command)
    exec_res = _agent_instance.executor.execute(
        command=sanitized_cmd,
        shell=ShellType.WSL_BASH,
        timeout_seconds=timeout_seconds,
        auto_diagnose=True,
    )

    # 3. Linux error diagnosis fallback
    linux_healing = None
    if not exec_res.success:
        healing = LinuxErrorCatalog.diagnose(
            stdout=exec_res.stdout,
            stderr=exec_res.stderr,
            exit_code=exec_res.exit_code,
            failed_command=command,
        )
        if healing:
            linux_healing = healing.model_dump()

    return {
        "success": exec_res.success,
        "exit_code": exec_res.exit_code,
        "stdout": exec_res.stdout,
        "stderr": exec_res.stderr,
        "duration_ms": exec_res.duration_ms,
        "safety_verdict": {
            "label": verdict.label,
            "is_dangerous": verdict.is_dangerous,
            "warning": verdict.warning,
        },
        "healing_proposal": linux_healing or (exec_res.healing_proposal.model_dump() if exec_res.healing_proposal else None),
    }


def winterm_linux_path_convert(path: str, to_linux: bool = True) -> Dict[str, Any]:
    """Converts file and directory paths between Windows format (C:\\...) and Linux format (/mnt/c/...).
    
    Args:
        path: Path string to translate.
        to_linux: If True converts Windows to Linux path; if False converts Linux to Windows path.
    """
    from winterm.subsystems.linux_subsystem import LinuxSubsystem
    converted = LinuxSubsystem.convert_path(path, to_linux=to_linux)
    return {
        "input_path": path,
        "to_linux": to_linux,
        "converted_path": converted,
    }


def winterm_linux_distro_list() -> Dict[str, Any]:
    """Enumerates installed WSL Linux distributions, current running states, and WSL version."""
    from winterm.subsystems.linux_subsystem import LinuxSubsystem
    step = LinuxSubsystem.list_wsl_distros()
    exec_res = _agent_instance.executor.execute(command=step.command, shell=step.target_shell)
    return {
        "success": exec_res.success,
        "exit_code": exec_res.exit_code,
        "raw_output": exec_res.stdout,
    }


def winterm_linux_safety_check(command: str) -> Dict[str, Any]:
    """Evaluates a proposed Linux or bash command against deterministic safety rules without executing.
    
    Args:
        command: The Linux / bash command string to audit.
    """
    from winterm.knowledge.linux_safety import LinuxSafetyGuard
    verdict = LinuxSafetyGuard.evaluate(command)
    return {
        "command": command,
        "label": verdict.label,
        "is_dangerous": verdict.is_dangerous,
        "warning": verdict.warning,
        "matched_pattern": verdict.matched_pattern,
        "matched_target": verdict.matched_target,
        "non_interactive_command": LinuxSafetyGuard.make_non_interactive(command),
    }


def winterm_linux_diagnose_error(
    output: str,
    exit_code: int = 1,
    failed_command: str = "",
) -> Dict[str, Any]:
    """Diagnoses Linux and POSIX terminal failure outputs and recommends an automated recovery remedy.
    
    Args:
        output: Stderr or console output from the failed Linux command.
        exit_code: Non-zero exit status code (e.g. 127, 126, 137, 139).
        failed_command: The command string that produced the failure.
    """
    from winterm.knowledge.linux_errors import LinuxErrorCatalog
    healing = LinuxErrorCatalog.diagnose(
        stdout="",
        stderr=output,
        exit_code=exit_code,
        failed_command=failed_command,
    )
    if healing:
        return {"diagnosed": True, "proposal": healing.model_dump()}
    return {"diagnosed": False, "message": "No specific Linux error signature matched."}


# Tool JSON Schema for LLM Function Calling (OpenAI / Gemini / Anthropic)
EXPORTED_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "plan_terminal_task",
            "description": "Decomposes a high-level goal into a staged execution plan (WHAT to do) for Windows Terminal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "The natural language task or goal on Windows."}
                },
                "required": ["goal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explain_terminal_command",
            "description": "Generates a 5W Decision Trace explaining What, How, When, Why, and What Happens After.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {"type": "string", "description": "The goal of the command."},
                    "command": {"type": "string", "description": "The concrete command to analyze."},
                    "target_shell": {"type": "string", "enum": ["powershell_51", "pwsh", "cmd"], "default": "powershell_51"},
                },
                "required": ["intent", "command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_command_impact",
            "description": "Forecasts state diff (files, registry, processes, ports), risk score, and rollback command before execution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command line to simulate."},
                    "target_shell": {"type": "string", "enum": ["powershell_51", "pwsh", "cmd"], "default": "powershell_51"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_terminal_command",
            "description": "Executes a terminal command on Windows with strict reliability, UTF-8 safety, and self-healing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to execute."},
                    "target_shell": {"type": "string", "enum": ["powershell_51", "pwsh", "cmd"], "default": "powershell_51"},
                    "dry_run": {"type": "boolean", "default": False},
                    "timeout_seconds": {"type": "integer", "default": 60},
                    "auto_heal": {"type": "boolean", "default": True},
                    "confirm_high_risk": {"type": "boolean", "default": False, "description": "Allow high-risk/destructive commands to run (DANGEROUS)."},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_terminal_error",
            "description": "Analyzes a failed command's output, identifies the Windows error signature, and generates a self-healing proposal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stderr": {"type": "string", "description": "Captured error message."},
                    "exit_code": {"type": "integer", "default": 1},
                    "command": {"type": "string", "description": "Failed command."},
                },
                "required": ["stderr"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_windows_knowledge",
            "description": "Searches the built-in Windows knowledge base for commands, shell rules, and pitfalls.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword or topic."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "undo_last_terminal_action",
            "description": "Rolls back the most recent state-modifying action from the undo stack.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_graph_blast_radius",
            "description": "Calculates cascading downstream dependents and blast radius if a service or resource is modified.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource": {"type": "string", "description": "Target service or resource (e.g. 'RpcSs', 'LanmanServer')."},
                    "depth": {"type": "integer", "default": 2, "description": "Cascade traversal depth."},
                },
                "required": ["resource"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_graph_validate_command",
            "description": "Validates command syntax and parameters against the Windows Knowledge Graph to prevent hallucinations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Full command with parameters (e.g. 'Get-Process -Name svchost')."}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_graph_remedy_error",
            "description": "Resolves an HRESULT or Win32 error code to an ordered multi-step remediation path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "error_code": {"type": "string", "description": "Error code (e.g. '0x80070005', '10048')."}
                },
                "required": ["error_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_graph_alternatives",
            "description": "Discovers equivalent native Win32 tools or PowerShell cmdlets for a given command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command or cmdlet name (e.g. 'Stop-Process', 'reg.exe')."}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_graph_info",
            "description": "Returns topological metrics and ontological breakdown of the Windows Knowledge Graph.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_graph_search_intent",
            "description": "Resolves natural language intents to real Windows commands using the indexed command dataset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query or intent."},
                    "top_k": {"type": "integer", "default": 5, "description": "Maximum number of command suggestions."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_graph_command_docs",
            "description": "Retrieves official Microsoft documentation, syntax, and parameter definitions for a Windows command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Windows command or binary name (e.g. 'robocopy', 'fsutil')."},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_graph_safety_check",
            "description": "Classifies command safety tier, credential sensitivity, and warnings using the SFT safety corpus.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command string to evaluate for safety risks."},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_app_find",
            "description": "Discovers installed Windows applications across shell:AppsFolder, Start Menu, and Registry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional search term (e.g. 'Notepad', 'Excel')."},
                    "limit": {"type": "integer", "default": 50, "description": "Max results to return."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_app_launch",
            "description": "Launches any Windows application (Win32, UWP Store app, or protocol URI).",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Application executable, AUMID, shortcut, or URI."},
                    "arguments": {"type": "string", "description": "Optional command-line arguments."},
                    "elevated": {"type": "boolean", "default": False, "description": "Whether to request Administrator elevation."},
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_app_close",
            "description": "Gracefully closes or forcefully terminates a running application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Process name, window title, or PID."},
                    "force": {"type": "boolean", "default": False, "description": "Force termination."},
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_app_learn",
            "description": "Discovers help, options, Knowledge Graph context, and operational guides for any app or command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Application or command to learn."},
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_window_list",
            "description": "Lists visible top-level windows with title, PID, handle, bounds, and state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional filter for window title or process name."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_window_focus",
            "description": "Brings an application window to the foreground and restores it if minimized.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "Window title, process name, or HWND."},
                },
                "required": ["identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_window_resize",
            "description": "Repositions and resizes an application window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "Window title, process name, or HWND."},
                    "x": {"type": "integer", "description": "Screen X coordinate."},
                    "y": {"type": "integer", "description": "Screen Y coordinate."},
                    "width": {"type": "integer", "description": "Window width in pixels."},
                    "height": {"type": "integer", "description": "Window height in pixels."},
                },
                "required": ["identifier", "x", "y", "width", "height"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_ui_inspect",
            "description": "Inspects all UI Automation elements (buttons, inputs, menus) inside a window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_identifier": {"type": "string", "description": "Target window title, process name, or HWND."},
                    "max_items": {"type": "integer", "default": 100, "description": "Maximum number of elements to inspect."},
                },
                "required": ["window_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_ui_click",
            "description": "Clicks an element by name or automation ID using InvokePattern or coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_identifier": {"type": "string", "description": "Target window title, process name, or HWND."},
                    "element_query": {"type": "string", "description": "Name or AutomationId of the element to click."},
                },
                "required": ["window_identifier", "element_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_ui_set_text",
            "description": "Sets text inside an input or edit control using ValuePattern or SendKeys.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_identifier": {"type": "string", "description": "Target window title, process name, or HWND."},
                    "element_query": {"type": "string", "description": "Name or AutomationId of the input element."},
                    "text": {"type": "string", "description": "Text to set."},
                },
                "required": ["window_identifier", "element_query", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_input_type",
            "description": "Simulates typing text via Windows SendKeys.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text string to type."},
                    "interval_ms": {"type": "integer", "default": 10, "description": "Delay between keystrokes in milliseconds."},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_input_hotkey",
            "description": "Simulates pressing a keyboard hotkey or key combination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key sequence (e.g. ['ctrl', 'c'], ['win', 'r']).",
                    },
                },
                "required": ["keys"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_input_mouse_click",
            "description": "Moves cursor to (X, Y) and performs mouse click.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Screen X coordinate."},
                    "y": {"type": "integer", "description": "Screen Y coordinate."},
                    "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                    "double": {"type": "boolean", "default": False, "description": "Double click."},
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_input_mouse_drag",
            "description": "Performs a drag-and-drop mouse gesture from start to end coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_x": {"type": "integer", "description": "Starting screen X coordinate."},
                    "start_y": {"type": "integer", "description": "Starting screen Y coordinate."},
                    "end_x": {"type": "integer", "description": "Ending screen X coordinate."},
                    "end_y": {"type": "integer", "description": "Ending screen Y coordinate."},
                },
                "required": ["start_x", "start_y", "end_x", "end_y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_window_close",
            "description": "Sends native Win32 WM_CLOSE message to gracefully close a window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "Window title substring or numeric handle (HWND)."},
                },
                "required": ["identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_screen_state",
            "description": "Queries live display resolution, active cursor position, and foreground window info on the interactive desktop.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_screen_capture",
            "description": "Captures a high-resolution visual screenshot of the full desktop or target window as PNG for visual perception and verification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "Absolute destination path for PNG file (e.g. 'd:\\Agent_toolkit\\screen.png')."},
                    "window_query": {"type": "string", "description": "Optional window title filter to capture only a specific window."},
                },
                "required": ["output_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_linux_execute",
            "description": "Executes a bash or POSIX command in Linux or WSL2 with deterministic safety validation, non-interactive flags, and self-healing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Linux bash command line to execute."},
                    "distro": {"type": "string", "description": "Optional WSL distribution name (e.g. 'Ubuntu', 'Debian')."},
                    "timeout_seconds": {"type": "integer", "default": 60, "description": "Timeout in seconds."},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_linux_path_convert",
            "description": "Converts file and directory paths between Windows format (C:\\...) and Linux / WSL format (/mnt/c/...).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path string to translate."},
                    "to_linux": {"type": "boolean", "default": True, "description": "If true converts Windows to Linux; if false Linux to Windows."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_linux_distro_list",
            "description": "Enumerates installed WSL Linux distributions, current running states, and default distro.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_linux_safety_check",
            "description": "Evaluates a proposed Linux or bash command against deterministic safety rules without executing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The Linux / bash command string to audit."},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_linux_diagnose_error",
            "description": "Diagnoses Linux and POSIX terminal failure outputs and recommends an automated recovery remedy.",
            "parameters": {
                "type": "object",
                "properties": {
                    "output": {"type": "string", "description": "Stderr or console output from the failed Linux command."},
                    "exit_code": {"type": "integer", "default": 1, "description": "Non-zero exit status code."},
                    "failed_command": {"type": "string", "default": "", "description": "The command string that produced the failure."},
                },
                "required": ["output"],
            },
        },
    },
]

