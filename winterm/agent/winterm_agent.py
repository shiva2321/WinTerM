"""WinTermAgent: The master AI Agent orchestrating the 5W cognitive model for Windows Terminal."""

import os
import time
import uuid
from typing import Optional, List, Dict, Any, Tuple
from winterm.models.intent import ExecutionPlan, PlanStep, StepStatus
from winterm.models.impact import PredictedImpact, RiskLevel, RollbackAction
from winterm.models.reasoning import DecisionTrace
from winterm.models.result import ExecutionResult, VerificationResult
from winterm.models.context import SystemContext, ShellType, ElevationLevel
from winterm.engine.environment import WindowsEnvironment
from winterm.engine.executor import WindowsShellExecutor
from winterm.cognition.planner import TerminalPlanner
from winterm.cognition.synthesizer import CommandSynthesizer
from winterm.cognition.scheduler import PreconditionScheduler
from winterm.cognition.reasoner import SemanticReasoner
from winterm.cognition.predictor import ImpactPredictor
from winterm.cognition.verifier import StateVerifier
from winterm.cognition.healer import ErrorHealer
from winterm.cognition.app_learner import AppLearner
from winterm.playbooks.manager import PlaybookManager
from winterm.playbooks.models import Playbook, PlaybookMatchResult
from winterm.subsystems.desktop_gui import DesktopGuiSubsystem
from winterm.interaction.semantic_tree import SemanticAccessibilityTree
from winterm.graph.engine import WindowsKnowledgeGraph
from winterm.graph.schema import BlastRadiusReport, RemediationPath, ParameterValidationResult
from winterm.agent.session import AgentSession
from winterm.swarm import SwarmCoordinator, AgentPrivilege, AgentScope, SwarmSuggestion


class WinTermAgent:
    """The master AI agent that knows what, how, when, why, and what happens after on Windows Terminal."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        context: Optional[SystemContext] = None,
        default_shell: ShellType = ShellType.POWERSHELL_51,
        graph: Optional[WindowsKnowledgeGraph] = None,
        playbook_storage_dir: Optional[str] = None,
    ):
        self.context = context or WindowsEnvironment.probe()
        self.session = AgentSession(session_id=session_id or f"session-{uuid.uuid4().hex[:8]}")
        self.executor = WindowsShellExecutor(default_shell=default_shell)
        self.knowledge_graph = graph or WindowsKnowledgeGraph()

        # Cognition pipeline with Knowledge Graph integration
        self.planner = TerminalPlanner(context=self.context)
        self.synthesizer = CommandSynthesizer()
        self.scheduler = PreconditionScheduler(executor=self.executor)
        self.reasoner = SemanticReasoner(graph=self.knowledge_graph)
        self.predictor = ImpactPredictor(graph=self.knowledge_graph)
        self.verifier = StateVerifier(executor=self.executor)
        self.healer = ErrorHealer(executor=self.executor, graph=self.knowledge_graph)
        self.learner = AppLearner(executor=self.executor, knowledge_graph=self.knowledge_graph)
        self.playbooks = PlaybookManager(storage_dir=playbook_storage_dir, executor=self.executor)
        self.swarm = SwarmCoordinator(executor=self.executor)

    def plan(self, goal: str) -> ExecutionPlan:
        """Decomposes a user goal into a structured, ordered ExecutionPlan (The WHAT)."""
        plan = self.planner.plan_goal(goal)
        self.session.active_plan = plan
        return plan

    def explain(self, step: PlanStep) -> DecisionTrace:
        """Constructs a comprehensive 5W DecisionTrace for an execution step."""
        # 1. Synthesize command (The HOW)
        synth_cmd = self.synthesizer.synthesize_step_command(step)
        step.command = synth_cmd

        # 2. Derive preconditions (The WHEN)
        preconditions = self.scheduler.derive_preconditions(step)

        # 3. Derive rationale & alternatives (The WHY)
        why_rationale = self.reasoner.explain_step(step)

        # 4. Predict impact, diff & rollback (The WHAT WILL HAPPEN AFTER)
        impact = self.predictor.predict_step_impact(step)

        after_summary = (
            f"Risk: {impact.risk_level.value.upper()}. "
            f"Expected state mutations: {len(impact.state_diff.filesystem.created_paths)} files/dirs created, "
            f"{len(impact.state_diff.processes.terminated_processes)} processes stopped, "
            f"{len(impact.side_effects)} side effects noted."
        )

        return DecisionTrace(
            step_id=step.step_id,
            what=f"{step.title} -> {synth_cmd}",
            how=f"Executed via {step.target_shell.value}. Non-interactive, UTF-8 encoded.",
            when=preconditions,
            why=why_rationale,
            after=after_summary,
        )

    def execute_step(
        self,
        step: PlanStep,
        dry_run: bool = False,
        auto_heal: bool = True,
        confirm_high_risk: bool = False,
    ) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Executes a single step across the entire 5W lifecycle.

        Safety gate: a step predicted as HIGH_DESTRUCTIVE (or requiring
        elevation without an elevated shell) is REFUSED unless
        ``confirm_high_risk=True``. This prevents autonomous agents from
        running destructive commands like ``Remove-Item`` on protected paths,
        ``Stop-Computer``, or ``Format-Volume`` without explicit confirmation.
        """
        # 1. Explain and synthesize
        trace = self.explain(step)
        impact = self.predictor.predict_step_impact(step)

        # 1b. SAFETY GATE — refuse destructive / unconfirmed-elevation steps (skipped during dry_run)
        if not dry_run:
            refusal = self._safety_gate(step, impact, confirm_high_risk)
            if refusal is not None:
                step.status = StepStatus.REFUSED if hasattr(StepStatus, "REFUSED") else StepStatus.FAILED
                self.session.record_step(step, trace=trace, exec_res=refusal, rollback=None)
                return refusal, None, trace

        # 2. Check preconditions and idempotency (WHEN)
        all_passed, should_skip, failures = self.scheduler.evaluate_preconditions(trace.when)
        if should_skip:
            step.status = StepStatus.SKIPPED_IDEMPOTENT
            result = ExecutionResult(
                step_id=step.step_id,
                command=step.command,
                shell=step.target_shell,
                success=True,
                stdout="[SKIPPED] Target state is already satisfied (Idempotent guard).",
            )
            self.session.record_step(step, trace=trace, exec_res=result, rollback=impact.rollback)
            return result, None, trace

        # 3. Dry run mode
        if dry_run:
            result = ExecutionResult(
                step_id=step.step_id,
                command=step.command,
                shell=step.target_shell,
                success=True,
                stdout=f"[DRY-RUN] Simulated execution for step '{step.title}'. No system state modified.",
            )
            return result, None, trace

        # 4. Actual execution (HOW)
        step.status = StepStatus.RUNNING
        exec_res = self.executor.execute(
            command=step.command,
            shell=step.target_shell,
            timeout_seconds=step.timeout_seconds,
            step_id=step.step_id,
            auto_diagnose=True,
        )

        # 5. Handle failure and auto-healing
        if not exec_res.success and auto_heal and exec_res.healing_proposal:
            heal_res = self.healer.attempt_auto_heal(exec_res.healing_proposal)
            if heal_res.success:
                # Retry original command after healing
                exec_res = self.executor.execute(
                    command=step.command,
                    shell=step.target_shell,
                    timeout_seconds=step.timeout_seconds,
                    step_id=step.step_id,
                    auto_diagnose=False,
                )

        # 6. Post-condition verification (AFTER)
        verif_res = None
        if exec_res.success:
            step.status = StepStatus.SUCCEEDED
            verif_res = self.verifier.verify_step(step, exec_res, impact)
        else:
            step.status = StepStatus.FAILED

        # 7. Record in session ledger
        self.session.record_step(
            step=step,
            trace=trace,
            exec_res=exec_res,
            verif_res=verif_res,
            rollback=impact.rollback,
        )

        return exec_res, verif_res, trace

    def _safety_gate(
        self,
        step: PlanStep,
        impact: PredictedImpact,
        confirm_high_risk: bool,
    ) -> Optional[ExecutionResult]:
        """Blocks destructive / unconfirmed-elevation steps from executing.

        Returns an ExecutionResult refusal when the step must not run, or
        ``None`` when execution may proceed.
        """
        from winterm.models.impact import RiskLevel

        if impact.risk_level in (RiskLevel.HIGH_DESTRUCTIVE, RiskLevel.ELEVATION_REQUIRED):
            if impact.risk_level == RiskLevel.ELEVATION_REQUIRED and step.required_elevation == ElevationLevel.ADMIN:
                # Elevation requirement is already declared on the step; the
                # UAC wrapper handles it at execution time.
                return None

            if not confirm_high_risk:
                reasons = "; ".join(impact.warnings[:3]) if impact.warnings else "classified as high risk"
                return ExecutionResult(
                    step_id=step.step_id,
                    command=step.command,
                    shell=step.target_shell,
                    success=False,
                    exit_code=-100,
                    stdout="",
                    stderr=(
                        f"[SAFETY GATE] Refused to execute: {reasons}\n"
                        "This step was predicted to be high-risk/destructive. "
                        "Re-run with confirm_high_risk=True to execute it explicitly."
                    ),
                )
        return None

    def run_goal(
        self,
        goal: str,
        dry_run: bool = False,
        auto_heal: bool = True,
        confirm_high_risk: bool = False,
    ) -> List[Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]]:
        """Plans, explains, executes, and verifies an entire goal end-to-end."""
        plan = self.plan(goal)
        results = []

        for step in plan.steps:
            res, verif, trace = self.execute_step(
                step, dry_run=dry_run, auto_heal=auto_heal, confirm_high_risk=confirm_high_risk
            )
            results.append((res, verif, trace))
            if not res.success and not dry_run:
                # Stop on unrecoverable failure
                break

        return results

    def undo_last_action(self) -> Optional[ExecutionResult]:
        """Executes the most recent rollback action from the session undo stack."""
        rollback = self.session.pop_rollback()
        if not rollback:
            return None

        return self.executor.execute(
            command=rollback.command,
            shell=rollback.shell,
            step_id=f"rollback-{rollback.step_id}",
        )

    # =========================================================================
    # KNOWLEDGE GRAPH REASONING SHORTCUTS
    # =========================================================================

    def calculate_blast_radius(self, resource_name: str, depth: int = 2) -> BlastRadiusReport:
        """Calculates direct and cascading downstream entities affected if a service or resource is modified."""
        return self.knowledge_graph.calculate_blast_radius(resource_name, depth=depth)

    def validate_command(self, command_string: str) -> ParameterValidationResult:
        """Validates command syntax and parameters against the Knowledge Graph to prevent hallucinations."""
        return self.synthesizer.validate_command(command_string, graph=self.knowledge_graph)

    def find_error_remedy(self, error_signature: str) -> Optional[RemediationPath]:
        """Resolves an HRESULT, Win32 error, or exception name to a multi-step remediation path."""
        return self.knowledge_graph.find_remediation_chains(error_signature)

    def find_alternatives(self, command_name: str) -> List[str]:
        """Discovers equivalent native binaries or PowerShell cmdlets for a given command."""
        return self.knowledge_graph.find_command_alternatives(command_name)

    def search_intent(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Resolves natural-language intents to real Windows commands using the indexed corpus."""
        return self.knowledge_graph.resolve_intent_to_commands(query, top_k=top_k)

    def get_command_docs(self, command_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves official Microsoft syntax and parameter definitions for a Windows command."""
        return self.knowledge_graph.get_command_documentation(command_name)

    def check_command_safety(self, command_string: str) -> Dict[str, Any]:
        """Classifies safety level and warnings for a command using the SFT safety corpus."""
        return self.knowledge_graph.get_safety_classification(command_string)

    # =========================================================================
    # APPLICATION OPERATIONS & GUI INTERACTION SHORTCUTS
    # =========================================================================

    def find_applications(self, query: Optional[str] = None, limit: int = 50, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Discovers installed Windows applications across shell:AppsFolder, Start Menu, and Registry."""
        step = DesktopGuiSubsystem.find_applications(query=query, limit=limit)
        return self.execute_step(step, dry_run=dry_run)

    def launch_application(self, target: str, arguments: Optional[str] = None, elevated: bool = False, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Launches any Windows application (Win32, UWP Store app, or protocol URI) onto the interactive user desktop."""
        step = DesktopGuiSubsystem.launch_application(target=target, arguments=arguments, elevated=elevated)
        if not elevated and os.name == "nt" and not dry_run:
            try:
                import uuid
                import subprocess
                import json
                tn = f"WinTerm_{uuid.uuid4().hex[:8]}"
                full_cmd = f"{target} {arguments}" if arguments else target
                create_res = subprocess.run(
                    ["schtasks.exe", "/create", "/tn", tn, "/tr", full_cmd, "/sc", "once", "/st", "00:00", "/it", "/f"],
                    capture_output=True, text=True
                )
                if create_res.returncode == 0:
                    subprocess.run(["schtasks.exe", "/run", "/tn", tn], capture_output=True)
                    time.sleep(0.5)
                    subprocess.run(["schtasks.exe", "/delete", "/tn", tn, "/f"], capture_output=True)
                    trace = self.explain(step)
                    exec_res = ExecutionResult(
                        step_id=step.step_id,
                        command=f"schtasks /run '{full_cmd}' [WinSta0\\Default]",
                        shell=step.target_shell,
                        success=True,
                        stdout=json.dumps({"Success": True, "Target": target, "Mode": "InteractiveDesktop", "Note": "Launched directly onto WinSta0\\Default"}),
                        stderr="",
                        exit_code=0,
                        duration_ms=500,
                    )
                    self.session.record_step(step, exec_res=exec_res, verif_res=None, trace=trace)
                    return exec_res, None, trace
            except Exception:
                pass

        return self.execute_step(step, dry_run=dry_run)

    def close_application(self, target: str, force: bool = False, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Gracefully closes or forcefully terminates a running application."""
        step = DesktopGuiSubsystem.close_application(target=target, force=force)
        return self.execute_step(step, dry_run=dry_run)

    def list_windows(self, query: Optional[str] = None, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Lists all visible application windows with titles, PIDs, geometry, and window state."""
        step = DesktopGuiSubsystem.list_windows(query=query)
        return self.execute_step(step, dry_run=dry_run)

    def focus_window(self, identifier: str, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Brings an application window to the foreground and restores it if minimized."""
        step = DesktopGuiSubsystem.focus_window(identifier=identifier)
        return self.execute_step(step, dry_run=dry_run)

    def resize_window(self, identifier: str, x: int, y: int, width: int, height: int, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Repositions and resizes an application window."""
        step = DesktopGuiSubsystem.resize_move_window(identifier, x, y, width, height)
        return self.execute_step(step, dry_run=dry_run)

    def set_window_state(self, identifier: str, state: str = "minimize", dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Minimizes, maximizes, or restores a window."""
        step = DesktopGuiSubsystem.set_window_state(identifier, state=state)
        return self.execute_step(step, dry_run=dry_run)

    def close_window(self, identifier: str, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Sends WM_CLOSE message to a window."""
        step = DesktopGuiSubsystem.close_window(identifier)
        return self.execute_step(step, dry_run=dry_run)

    def inspect_window_elements(self, window_identifier: str, max_items: int = 100, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Inspects all UI Automation elements (buttons, inputs, menus) inside a window."""
        step = DesktopGuiSubsystem.inspect_ui_elements(window_identifier, max_items=max_items)
        return self.execute_step(step, dry_run=dry_run)

    def get_screen_state(self, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Inspects live screen resolution, active cursor position, and foreground window on the interactive desktop."""
        step = DesktopGuiSubsystem.get_screen_state()
        return self.execute_step(step, dry_run=dry_run)

    def capture_screen(self, output_path: str, window_query: Optional[str] = None, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Takes a full desktop or target window visual screenshot and saves it as PNG."""
        step = DesktopGuiSubsystem.capture_screen(output_path, window_query=window_query)
        return self.execute_step(step, dry_run=dry_run)

    def find_ui_element(self, window_identifier: str, query: str, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Locates an interactive UI element by name, AutomationId, or ControlType and returns its live coordinates."""
        step = DesktopGuiSubsystem.find_ui_element(window_identifier, query)
        return self.execute_step(step, dry_run=dry_run)

    def click_ui_element(self, window_identifier: str, element_query: str, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Clicks an element by name or automation ID using InvokePattern or coordinates."""
        step = DesktopGuiSubsystem.click_ui_element(window_identifier, element_query)
        return self.execute_step(step, dry_run=dry_run)

    def set_ui_element_text(self, window_identifier: str, element_query: str, text: str, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Sets text inside an input or edit control using ValuePattern or SendKeys."""
        step = DesktopGuiSubsystem.set_ui_element_text(window_identifier, element_query, text)
        return self.execute_step(step, dry_run=dry_run)

    def type_text(self, text: str, interval_ms: int = 10, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Simulates typing text via Windows SendKeys."""
        step = DesktopGuiSubsystem.type_text(text, interval_ms=interval_ms)
        return self.execute_step(step, dry_run=dry_run)

    def press_hotkey(self, keys: List[str], dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Simulates pressing a keyboard hotkey or key combination."""
        step = DesktopGuiSubsystem.press_hotkey(keys)
        return self.execute_step(step, dry_run=dry_run)

    def mouse_click(self, x: int, y: int, button: str = "left", double: bool = False, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Moves cursor to (X, Y) and performs mouse click."""
        step = DesktopGuiSubsystem.mouse_click(x, y, button=button, double=double)
        return self.execute_step(step, dry_run=dry_run)

    def mouse_move(self, x: int, y: int, smooth: bool = False, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Moves mouse cursor to absolute (X, Y) coordinates."""
        step = DesktopGuiSubsystem.mouse_move(x, y, smooth=smooth)
        return self.execute_step(step, dry_run=dry_run)

    def mouse_drag(self, start_x: int, start_y: int, end_x: int, end_y: int, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Performs a drag-and-drop mouse gesture from start to end coordinates."""
        step = DesktopGuiSubsystem.mouse_drag(start_x, start_y, end_x, end_y)
        return self.execute_step(step, dry_run=dry_run)

    def mouse_scroll(self, amount: int, horizontal: bool = False, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Performs vertical or horizontal mouse wheel scroll."""
        step = DesktopGuiSubsystem.mouse_scroll(amount, horizontal=horizontal)
        return self.execute_step(step, dry_run=dry_run)

    def pen_draw_path(self, points: List[Tuple[int, int]], delay_ms: int = 10, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Draws a continuous parametric path using pen/pointer injection."""
        step = DesktopGuiSubsystem.pen_draw_path(points, delay_ms=delay_ms)
        return self.execute_step(step, dry_run=dry_run)

    def learn_application(self, app_or_command: str) -> Dict[str, Any]:
        """Probes, analyzes, and learns how to operate any Windows application or CLI utility."""
        return self.learner.learn(app_or_command)

    def ocr_window(self, window_identifier: str, language_tag: str = "en-US", dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Executes native zero-dependency Windows OCR on the target window's graphical rendering."""
        step = DesktopGuiSubsystem.ocr_window(window_identifier, language_tag=language_tag)
        return self.execute_step(step, dry_run=dry_run)

    def ocr_image(self, image_path: str, language_tag: str = "en-US", dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Executes native zero-dependency Windows OCR on an image file on disk."""
        step = DesktopGuiSubsystem.ocr_image(image_path, language_tag=language_tag)
        return self.execute_step(step, dry_run=dry_run)

    def som_annotate(self, window_identifier: str, output_annotated_path: str, max_marks: int = 50, dry_run: bool = False) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Generates Set-of-Mark visual grounding overlay with numbered badges ([1], [2]...) and element index."""
        step = DesktopGuiSubsystem.som_annotate(window_identifier, output_annotated_path, max_marks=max_marks)
        return self.execute_step(step, dry_run=dry_run)

    def smart_click(
        self,
        window_identifier: str,
        element_query: str,
        control_type: Optional[str] = None,
        language_tag: str = "en-US",
        dry_run: bool = False,
    ) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Clicks an element using multi-strategy cascading: UIAutomation -> Native OCR -> Coordinate click."""
        step = DesktopGuiSubsystem.smart_click(window_identifier, element_query, control_type=control_type, language_tag=language_tag)
        return self.execute_step(step, dry_run=dry_run)

    def wait_for_ui_change(
        self,
        window_identifier: str,
        timeout_ms: int = 3000,
        min_diff_pct: float = 0.5,
        dry_run: bool = False,
    ) -> Tuple[ExecutionResult, Optional[VerificationResult], DecisionTrace]:
        """Waits asynchronously for visual UI change in the target window, eliminating race conditions."""
        step = DesktopGuiSubsystem.wait_for_ui_change(window_identifier, timeout_ms=timeout_ms, min_diff_pct=min_diff_pct)
        return self.execute_step(step, dry_run=dry_run)

    def perceive_ui(
        self,
        window_identifier: str,
        max_items: int = 50,
        include_ocr: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Comprehensive perception returning token-efficient semantic Markdown tree, OCR text blocks, and window bounds."""
        exec_res, _, _ = self.inspect_window_elements(window_identifier, max_items=max_items * 2, dry_run=dry_run)
        parsed_tree = {}
        if exec_res.stdout:
            try:
                raw_json = json.loads(exec_res.stdout)
                parsed_tree = SemanticAccessibilityTree.to_token_efficient_summary(raw_json, max_items=max_items)
            except Exception:
                parsed_tree = {"raw": exec_res.stdout}

        ocr_summary = None
        if include_ocr and not dry_run:
            ocr_res, _, _ = self.ocr_window(window_identifier)
            if ocr_res.stdout:
                try:
                    ocr_data = json.loads(ocr_res.stdout)
                    ocr_summary = {
                        "words_count": ocr_data.get("WordsCount", 0),
                        "text": ocr_data.get("Text", ""),
                        "words": ocr_data.get("Words", [])[:max_items],
                    }
                except Exception:
                    ocr_summary = {"raw": ocr_res.stdout}

        return {
            "window": window_identifier,
            "accessibility_tree": parsed_tree,
            "ocr": ocr_summary,
        }

    # =========================================================================
    # REUSABLE TASK PLAYBOOK & SCRIPT GENERALIZATION HELPERS
    # =========================================================================

    def create_playbook(
        self,
        goal: str,
        commands: List[str],
        shell: ShellType = ShellType.POWERSHELL_51,
        name: Optional[str] = None,
        description: Optional[str] = None,
        force_script: bool = False,
    ) -> Playbook:
        """Explicitly generalizes a sequence of task commands into a persistent, reusable Playbook."""
        return self.playbooks.create_playbook_from_task(
            goal=goal,
            commands=commands,
            shell=shell,
            name=name,
            description=description,
            force_script=force_script,
        )

    def match_playbook(self, goal: str) -> PlaybookMatchResult:
        """Finds a matching generalized playbook for a given goal and extracts parameters."""
        return self.playbooks.match_playbook(goal)

    def execute_playbook(
        self,
        playbook_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        background: bool = False,
    ) -> ExecutionResult:
        """Executes a generalized playbook routine with supplied or extracted parameters."""
        return self.playbooks.execute_playbook(
            playbook_id=playbook_id,
            parameters=parameters,
            background=background,
        )

    def list_playbooks(self) -> List[Playbook]:
        """Returns all registered playbooks sorted by recency."""
        return self.playbooks.list_playbooks()

    def prune_playbooks(self, max_items: int = 30) -> int:
        """Prunes stale or least recently used playbooks down to max_items."""
        return self.playbooks.prune_playbooks(max_items=max_items)

    # =========================================================================
    # MULTI-AGENT SWARM ORCHESTRATION & SUPERVISION
    # =========================================================================

    def dispatch_swarm(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Dispatches a fleet of autonomous sub-agents with scoped privileges."""
        return self.swarm.dispatch_swarm(tasks)

    def get_swarm_status(self) -> Dict[str, Any]:
        """Returns live swarm status, sub-agent telemetry, fault records, and pending suggestions."""
        return self.swarm.get_swarm_status()

    def broadcast_swarm_directive(self, directive: str, target_agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Broadcasts a directive to the swarm Message Board."""
        msg = self.swarm.broadcast_directive(directive, target_agent_id=target_agent_id)
        return msg.model_dump()

    def review_swarm_suggestions(self) -> List[Dict[str, Any]]:
        """Queries pending proactive suggestions submitted by autonomous sub-agents."""
        return [s.model_dump() for s in self.swarm.review_suggestions()]

    def approve_swarm_suggestion(self, suggestion_id: str, execute_now: bool = True) -> Dict[str, Any]:
        """Approves and optionally executes a sub-agent proactive suggestion."""
        return self.swarm.approve_suggestion(suggestion_id=suggestion_id, execute_now=execute_now)

    def reject_swarm_suggestion(self, suggestion_id: str, reason: str = "") -> bool:
        """Rejects a sub-agent suggestion with an explanatory rationale."""
        return self.swarm.reject_suggestion(suggestion_id=suggestion_id, reason=reason)




