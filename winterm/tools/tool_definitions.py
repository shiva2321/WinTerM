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
from winterm.playbooks.gate import ScriptJustificationGate
from winterm.swarm.models import MessageType, AgentPrivilege


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


def winterm_ui_perceive(window_identifier: str, max_items: int = 50, include_ocr: bool = True) -> Dict[str, Any]:
    """Generates a complete semantic UI perception map including compact Markdown tree, OCR text blocks, and coordinates.
    
    CRITICAL AGENT INSTRUCTION:
    Use this tool instead of raw JSON inspection to observe active desktop applications with maximum token efficiency.
    """
    res = _agent_instance.perceive_ui(window_identifier, max_items=max_items, include_ocr=include_ocr)
    return {"exit_code": 0, "output": json.dumps(res, default=str), "error": ""}


def winterm_ui_ocr(window_identifier: str, language_tag: str = "en-US") -> Dict[str, Any]:
    """Executes native zero-dependency Windows OCR on the target window's graphical rendering.
    
    CRITICAL AGENT INSTRUCTION:
    Use this tool to read text, buttons, and links in Canvas, Electron, Flutter, or game windows that lack UI Automation trees.
    """
    exec_res, _, _ = _agent_instance.ocr_window(window_identifier, language_tag=language_tag)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_ui_som_annotate(window_identifier: str, output_annotated_path: str, max_marks: int = 50) -> Dict[str, Any]:
    """Generates Set-of-Mark (SoM) visual grounding annotations with high-contrast numbered badges ([1], [2]...).
    
    CRITICAL AGENT INSTRUCTION:
    Use this tool to produce visual annotated screenshots for multimodal reasoning models (Gemini, Claude, GPT-4o).
    """
    exec_res, _, _ = _agent_instance.som_annotate(window_identifier, output_annotated_path, max_marks=max_marks)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_ui_smart_click(window_identifier: str, element_query: str, control_type: Optional[str] = None) -> Dict[str, Any]:
    """Clicks an element using multi-strategy cascading: UIAutomation -> Native Windows OCR -> Coordinate click.
    
    CRITICAL AGENT INSTRUCTION:
    Use this tool to reliably click buttons or controls even when the application renders custom UI or uses dynamic IDs.
    """
    exec_res, _, _ = _agent_instance.smart_click(window_identifier, element_query, control_type=control_type)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_ui_wait_change(window_identifier: str, timeout_ms: int = 3000, min_diff_pct: float = 0.5) -> Dict[str, Any]:
    """Waits asynchronously for visual UI change in the target window, eliminating race conditions.
    
    CRITICAL AGENT INSTRUCTION:
    Call this tool immediately after clicking a button or submitting a form to ensure the UI state transition has completed.
    """
    exec_res, _, _ = _agent_instance.wait_for_ui_change(window_identifier, timeout_ms=timeout_ms, min_diff_pct=min_diff_pct)
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_screen_mental_map(window_identifier: Optional[str] = None, max_items: int = 60, include_ocr: bool = True) -> Dict[str, Any]:
    """Generates a structured multi-layered cognitive mental map of the window or desktop.

    Fuses UIAutomation and WinRT OCR into spatial layers (desktop, inactive, active workspace, modals)
    and functional zones (header, navigation, content, sidebar, footer), infers semantic roles, and
    derives next action affordances (CLICK, TYPE, SCROLL) to guide the agent's attention.
    """
    map_dict = _agent_instance.get_screen_mental_map(window_identifier)
    return {"exit_code": 0, "mental_map": map_dict, "error": ""}


def winterm_ui_hover(
    window_identifier: str,
    element_query: Optional[str] = None,
    rel_x: Optional[int] = None,
    rel_y: Optional[int] = None,
    dwell_ms: int = 500,
    control_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Hovers the mouse cursor over a target UI element or coordinates to trigger tooltips or menus.

    Uses cubic Bezier smooth mouse interpolation and window-contained safety validation.
    """
    exec_res, _, _ = _agent_instance.hover_element(
        window_identifier,
        rel_x=rel_x,
        rel_y=rel_y,
        element_query=element_query,
        dwell_ms=dwell_ms,
        control_type=control_type,
    )
    return {"exit_code": exec_res.exit_code, "output": exec_res.stdout, "error": exec_res.stderr}


def winterm_ui_scroll_into_view(
    window_identifier: str,
    target_rel_y: int,
    viewport_center_y: int = 400,
) -> Dict[str, Any]:
    """Calibrates and dispatches mouse wheel ticks to bring an off-screen or off-center element into view."""
    exec_res, _, _ = _agent_instance.scroll_to_element(
        window_identifier,
        target_rel_y=target_rel_y,
        viewport_center_y=viewport_center_y,
    )
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


# =============================================================================
# REUSABLE TASK PLAYBOOKS & SCRIPT GENERALIZATION TOOLS
# =============================================================================

def winterm_playbook_create(
    goal: str,
    commands: List[str],
    target_shell: str = "powershell_51",
    name: Optional[str] = None,
    description: Optional[str] = None,
    auto_promote: bool = True,
    force_script: bool = False,
) -> Dict[str, Any]:
    """Generates a defensive task script and registers it in the playbook engine.
    
    Enforces the ScriptJustificationGate: Drops atomic one-liners, requiring direct execution
    instead. Only creates scripts for multi-step workflows, control flow, loops, or rollback routines.
    """
    shell_enum = ShellType(target_shell) if target_shell in [s.value for s in ShellType] else ShellType.POWERSHELL_51
    justification = ScriptJustificationGate.evaluate(goal, commands, shell=shell_enum, force_script=force_script)
    if not justification.is_justified:
        return {
            "created": False,
            "requires_script": False,
            "reason": justification.reason,
            "suggested_action": justification.suggested_action,
            "guidance": (
                "Atomic single-step commands must be run directly via execute_terminal_command or "
                "winterm_linux_execute. Standalone scripts should only be synthesized for multi-step workflows, "
                "branching logic, loops, or transactional rollbacks."
            ),
        }

    if auto_promote:
        playbook = _agent_instance.playbooks.create_playbook_from_task(
            goal=goal,
            commands=commands,
            shell=shell_enum,
            name=name,
            description=description,
            force_script=force_script,
        )
        return {
            "created": True,
            "requires_script": True,
            "playbook_id": playbook.playbook_id,
            "name": playbook.name,
            "parameters": [p.model_dump() for p in playbook.parameters],
            "script_body": playbook.script_body,
            "safety_tier": playbook.safety_tier,
        }
    else:
        pb = _agent_instance.playbooks.record_task_execution(
            goal=goal,
            commands=commands,
            shell=shell_enum,
            auto_promote=False,
        )
        return {
            "created": pb is not None,
            "requires_script": True,
            "recorded_in_candidate_buffer": True,
            "playbook_id": pb.playbook_id if pb else None,
        }


def winterm_playbook_match_run(
    goal: str,
    parameters: Optional[Dict[str, Any]] = None,
    background: bool = False,
    confirm_high_risk: bool = False,
) -> Dict[str, Any]:
    """Matches a recurring situation against the playbook catalog, extracts parameters, and executes the generalized script.

    Args:
        goal: The natural language objective (e.g. 'kill process using port 9000').
        parameters: Optional explicit parameter overrides (e.g. {'port': 9000}).
        background: If True runs command in background.
        confirm_high_risk: Required True to run a playbook recorded as destructive when it
            was created. A playbook's safety classification is checked on every replay, not
            only once at creation time.
    """
    match_res = _agent_instance.playbooks.match_playbook(goal)
    if not match_res.matched or not match_res.playbook:
        return {
            "matched": False,
            "reason": match_res.reason,
            "executed": False,
        }

    merged_params = match_res.extracted_params.copy()
    if parameters:
        merged_params.update(parameters)

    exec_res = _agent_instance.playbooks.execute_playbook(
        playbook_id=match_res.playbook.playbook_id,
        parameters=merged_params,
        background=background,
        confirm_high_risk=confirm_high_risk,
    )
    gate_refused = exec_res.exit_code == -100 and "SAFETY GATE" in (exec_res.stderr or "")
    return {
        "matched": True,
        "playbook_id": match_res.playbook.playbook_id,
        "playbook_name": match_res.playbook.name,
        "parameters_used": merged_params,
        "executed": not gate_refused,
        "success": exec_res.success,
        "exit_code": exec_res.exit_code,
        "stdout": exec_res.stdout,
        "stderr": exec_res.stderr,
    }


def winterm_playbook_list() -> List[Dict[str, Any]]:
    """Lists all stored, reusable task playbooks with parameter schemas, safety tiers, and execution counts."""
    playbooks = _agent_instance.playbooks.list_playbooks()
    return [
        {
            "playbook_id": pb.playbook_id,
            "name": pb.name,
            "description": pb.description,
            "signature": pb.pattern_signature,
            "target_shell": pb.target_shell.value,
            "parameters": [p.model_dump() for p in pb.parameters],
            "execution_count": pb.execution_count,
            "success_count": pb.success_count,
            "safety_tier": pb.safety_tier,
        }
        for pb in playbooks
    ]


def winterm_playbook_prune(max_items: int = 30) -> Dict[str, Any]:
    """Prunes stale, least recently used playbooks down to max_items to prevent disk and resource waste.
    
    Args:
        max_items: The target maximum number of active playbooks to retain.
    """
    purged = _agent_instance.playbooks.prune_playbooks(max_items=max_items)
    remaining = len(_agent_instance.playbooks.list_playbooks())
    return {
        "purged_count": purged,
        "remaining_playbooks": remaining,
        "max_items": max_items,
    }


# =============================================================================
# MULTI-AGENT SWARM & MESSAGE BOARD COORDINATION TOOLS
# =============================================================================

def winterm_swarm_dispatch(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Dispatches a fleet of autonomous sub-agents with scoped capability privileges.
    
    Args:
        tasks: List of sub-agent task definitions, each with 'name', 'goal', and 'privilege'
               ('read_only_audit', 'ui_operator', 'terminal_executor', 'network_inspector', 'full_supervisor').
    """
    return _agent_instance.dispatch_swarm(tasks)


def winterm_swarm_board_read(filter_type: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
    """Reads recent messages, updates, and alerts from the shared Swarm Message Board.
    
    Args:
        filter_type: Optional message filter ('task_assignment', 'progress_update', 'task_completed',
                     'task_failed', 'suggestion', 'alert', 'directive').
        limit: Max number of recent messages to return.
    """
    f_type = None
    if filter_type:
        try:
            f_type = MessageType(filter_type)
        except ValueError:
            pass
    messages = _agent_instance.swarm.board.get_messages(filter_type=f_type, limit=limit)
    return [m.model_dump() for m in messages]


def winterm_swarm_board_post(directive: str, recipient_id: str = "broadcast") -> Dict[str, Any]:
    """Posts an instruction, directive, or announcement from the main agent to the Swarm Message Board.
    
    Args:
        directive: The instruction text or command payload.
        recipient_id: 'broadcast' for all sub-agents, or a specific sub-agent ID.
    """
    msg = _agent_instance.swarm.broadcast_directive(
        directive=directive,
        target_agent_id=None if recipient_id == "broadcast" else recipient_id,
    )
    return msg.model_dump()


def winterm_swarm_suggestions(
    action: str = "list",
    suggestion_id: Optional[str] = None,
    execute_now: bool = True,
    reason: str = "",
    confirm_high_risk: bool = False,
) -> Dict[str, Any]:
    """Supervises, reviews, approves, or rejects proactive suggestions submitted by autonomous sub-agents.

    Args:
        action: 'list' (view pending suggestions), 'approve' (approve suggestion), or 'reject' (reject suggestion).
        suggestion_id: ID of the suggestion to approve or reject.
        execute_now: If True and action is 'approve', executes the proposed action immediately.
        reason: Optional explanation if rejecting a suggestion.
        confirm_high_risk: Required True to execute a suggestion classified high-risk/destructive
            by the safety gate. A sub-agent's proposed_action is agent-authored free text and is
            checked exactly like any other command -- approving a suggestion does not bypass this.
    """
    if action == "list":
        return {
            "pending_suggestions": _agent_instance.review_swarm_suggestions()
        }
    elif action == "approve":
        if not suggestion_id:
            return {"approved": False, "error": "suggestion_id is required for approval."}
        return _agent_instance.approve_swarm_suggestion(
            suggestion_id=suggestion_id, execute_now=execute_now, confirm_high_risk=confirm_high_risk
        )
    elif action == "reject":
        if not suggestion_id:
            return {"rejected": False, "error": "suggestion_id is required for rejection."}
        success = _agent_instance.reject_swarm_suggestion(suggestion_id=suggestion_id, reason=reason)
        return {"rejected": success, "suggestion_id": suggestion_id}
    else:
        return {"error": f"Unknown action '{action}'. Valid actions: 'list', 'approve', 'reject'."}


def winterm_swarm_status() -> Dict[str, Any]:
    """Returns the operational telemetry of the swarm, active sub-agents, circuit-breaker states, and fault records."""
    return _agent_instance.get_swarm_status()


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
    {
        "type": "function",
        "function": {
            "name": "winterm_playbook_create",
            "description": "Generates a defensive task script and registers it in the playbook engine. Generalizes literals into typed parameters if requested.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "The natural language objective of the routine."},
                    "commands": {"type": "array", "items": {"type": "string"}, "description": "List of commands constituting the task."},
                    "target_shell": {"type": "string", "default": "powershell_51", "description": "Target shell (powershell_51, pwsh, cmd, or bash)."},
                    "name": {"type": "string", "description": "Optional human-readable title for the playbook."},
                    "description": {"type": "string", "description": "Optional detailed description."},
                    "auto_promote": {"type": "boolean", "default": True, "description": "If True, compiles and saves immediately as a persistent Playbook."},
                    "force_script": {"type": "boolean", "default": False, "description": "If True, overrides the ScriptJustificationGate to synthesize a script even for atomic commands."},
                },
                "required": ["goal", "commands"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_playbook_match_run",
            "description": "Matches a recurring situation against the playbook catalog, extracts parameters, and executes the generalized script.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "The natural language goal describing the task to execute."},
                    "parameters": {"type": "object", "description": "Optional explicit parameter overrides dictionary."},
                    "background": {"type": "boolean", "default": False, "description": "If True, runs the playbook in the background."},
                    "confirm_high_risk": {
                        "type": "boolean",
                        "default": False,
                        "description": "Required True to run a playbook recorded as destructive when it was created. Checked on every replay, not only once at creation time.",
                    },
                },
                "required": ["goal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_playbook_list",
            "description": "Lists all stored, reusable task playbooks with parameter schemas, safety tiers, and execution telemetry.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_playbook_prune",
            "description": "Prunes stale, least recently used playbooks down to max_items to prevent disk and resource waste.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_items": {"type": "integer", "default": 30, "description": "The target maximum number of active playbooks to retain."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_swarm_dispatch",
            "description": "Dispatches a fleet of autonomous sub-agents with scoped capability privileges for parallel or sequenced execution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Human-readable name of the sub-agent."},
                                "goal": {"type": "string", "description": "Specific sub-goal assigned to the sub-agent."},
                                "privilege": {
                                    "type": "string",
                                    "enum": ["read_only_audit", "ui_operator", "terminal_executor", "network_inspector", "full_supervisor"],
                                    "default": "read_only_audit",
                                    "description": "Authorized privilege boundary tier.",
                                },
                            },
                            "required": ["name", "goal"],
                        },
                        "description": "List of sub-agent specifications.",
                    },
                },
                "required": ["tasks"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_swarm_board_read",
            "description": "Reads recent messages, status reports, and alerts from the shared Swarm Message Board.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_type": {
                        "type": "string",
                        "enum": ["task_assignment", "progress_update", "task_completed", "task_failed", "suggestion", "alert", "directive"],
                        "description": "Optional filter for message category.",
                    },
                    "limit": {"type": "integer", "default": 30, "description": "Maximum number of recent messages to return."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_swarm_board_post",
            "description": "Posts an instruction, directive, or announcement from the main agent to the Swarm Message Board.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directive": {"type": "string", "description": "The instruction text or command payload."},
                    "recipient_id": {"type": "string", "default": "broadcast", "description": "'broadcast' or specific target sub-agent ID."},
                },
                "required": ["directive"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_swarm_suggestions",
            "description": "Supervises, reviews, approves, or rejects proactive suggestions submitted by autonomous sub-agents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "approve", "reject"],
                        "default": "list",
                        "description": "Action to perform on suggestions.",
                    },
                    "suggestion_id": {"type": "string", "description": "ID of the suggestion to approve or reject."},
                    "execute_now": {"type": "boolean", "default": True, "description": "If True and approving, immediately executes the suggestion."},
                    "reason": {"type": "string", "description": "Optional explanation when rejecting a suggestion."},
                    "confirm_high_risk": {
                        "type": "boolean",
                        "default": False,
                        "description": "Required True to execute a suggestion the safety gate classifies as high-risk/destructive. Approving a suggestion does not bypass this check -- a sub-agent's proposed_action is checked exactly like any other command.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_swarm_status",
            "description": "Returns operational telemetry of the swarm, active sub-agents, circuit-breaker states, and fault records.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_ui_perceive",
            "description": "Generates a complete semantic UI perception map including compact Markdown tree, OCR text blocks, and coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_identifier": {"type": "string", "description": "Window title substring or numeric window handle (HWND)."},
                    "max_items": {"type": "integer", "default": 50, "description": "Maximum number of interactive elements to retain."},
                    "include_ocr": {"type": "boolean", "default": True, "description": "Whether to include native Windows OCR text recognition."},
                },
                "required": ["window_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_ui_ocr",
            "description": "Executes native zero-dependency Windows OCR on the target window's graphical rendering.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_identifier": {"type": "string", "description": "Window title substring or numeric window handle (HWND)."},
                    "language_tag": {"type": "string", "default": "en-US", "description": "BCP-47 language tag (e.g. 'en-US')."},
                },
                "required": ["window_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_ui_som_annotate",
            "description": "Generates Set-of-Mark (SoM) visual grounding annotations with high-contrast numbered badges ([1], [2]...).",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_identifier": {"type": "string", "description": "Window title substring or numeric window handle (HWND)."},
                    "output_annotated_path": {"type": "string", "description": "Absolute destination path for the annotated PNG image."},
                    "max_marks": {"type": "integer", "default": 50, "description": "Maximum number of marked element tags to overlay."},
                },
                "required": ["window_identifier", "output_annotated_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_ui_smart_click",
            "description": "Clicks an element using multi-strategy cascading: UIAutomation -> Native Windows OCR -> Coordinate click.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_identifier": {"type": "string", "description": "Window title substring or numeric window handle (HWND)."},
                    "element_query": {"type": "string", "description": "Name, label, text, or AutomationId of the element to click."},
                    "control_type": {"type": "string", "description": "Optional ControlType constraint (e.g. 'Button', 'MenuItem')."},
                },
                "required": ["window_identifier", "element_query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_ui_wait_change",
            "description": "Waits asynchronously for visual UI change in the target window, eliminating race conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_identifier": {"type": "string", "description": "Window title substring or numeric window handle (HWND)."},
                    "timeout_ms": {"type": "integer", "default": 3000, "description": "Maximum time to wait for state transition in milliseconds."},
                    "min_diff_pct": {"type": "number", "default": 0.5, "description": "Minimum percentage visual difference to consider changed."},
                },
                "required": ["window_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_screen_mental_map",
            "description": "Constructs a multi-layered cognitive mental map of the screen/window with spatial layers, functional zones, and action affordances.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_identifier": {"type": "string", "description": "Optional window title substring or HWND. If omitted, maps all desktop windows."},
                    "max_items": {"type": "integer", "default": 60, "description": "Maximum number of semantic elements to retain."},
                    "include_ocr": {"type": "boolean", "default": True, "description": "Whether to include native Windows OCR text recognition."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_ui_hover",
            "description": "Hovers mouse cursor smoothly over a UI element or coordinates to reveal tooltips or hover menus.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_identifier": {"type": "string", "description": "Window title substring or numeric window handle (HWND)."},
                    "element_query": {"type": "string", "description": "Name, label, text, or AutomationId of element to hover."},
                    "rel_x": {"type": "integer", "description": "Optional relative X coordinate inside window."},
                    "rel_y": {"type": "integer", "description": "Optional relative Y coordinate inside window."},
                    "dwell_ms": {"type": "integer", "default": 500, "description": "Hover dwell duration in milliseconds."},
                    "control_type": {"type": "string", "description": "Optional ControlType constraint."},
                },
                "required": ["window_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "winterm_ui_scroll_into_view",
            "description": "Calibrates and dispatches mouse wheel ticks to bring an off-screen or off-center element into view.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window_identifier": {"type": "string", "description": "Window title substring or numeric window handle (HWND)."},
                    "target_rel_y": {"type": "integer", "description": "Relative Y coordinate of target element in window space."},
                    "viewport_center_y": {"type": "integer", "default": 400, "description": "Desired viewport center Y coordinate."},
                },
                "required": ["window_identifier", "target_rel_y"],
            },
        },
    },
]


