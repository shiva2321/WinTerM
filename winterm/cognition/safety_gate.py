"""Centralized safety gate: the single choke point every 'run this command outside
the normal plan -> execute_step flow' path must pass through before invoking the
raw executor.

WinTermAgent.execute_step() has always refused HIGH_DESTRUCTIVE / unconfirmed-
elevation steps unless confirm_high_risk=True. That protection only covered
execute_step's own call to the executor. Several other places in the codebase
also call WindowsShellExecutor.execute() directly -- swarm suggestion approval,
playbook replay, auto-heal remediation, action rollback -- and none of them
consulted the gate at all, which meant a destructive command routed through any
of those paths ran completely unchecked regardless of confirm_high_risk.

This module extracts the gate's decision logic into a standalone function
(`evaluate_gate_decision`) reused by WinTermAgent._safety_gate, and adds
`gate_command`, a convenience wrapper for callers that only have a raw command
string (not an already-built PlanStep + PredictedImpact) -- which is every one
of the call sites listed above. Any new code that executes an arbitrary command
outside of execute_step's own flow should call `gate_command` first.
"""

from __future__ import annotations

from typing import List, Optional

from winterm.models.context import ShellType, ElevationLevel
from winterm.models.impact import RiskLevel
from winterm.models.result import ExecutionResult


def evaluate_gate_decision(
    risk_level: RiskLevel,
    warnings: List[str],
    required_elevation: ElevationLevel,
    command: str,
    shell: ShellType,
    step_id: str,
    confirm_high_risk: bool,
) -> Optional[ExecutionResult]:
    """Decides whether a command classified with `risk_level` may proceed.

    Returns an ExecutionResult refusal when it must not run, or ``None`` when
    execution may proceed. This is the exact decision WinTermAgent._safety_gate
    has always made for the primary execute_step path; it is factored out here
    so every other execution path in the codebase makes the identical decision
    instead of inventing its own (weaker) check.
    """
    if risk_level in (RiskLevel.HIGH_DESTRUCTIVE, RiskLevel.ELEVATION_REQUIRED):
        if risk_level == RiskLevel.ELEVATION_REQUIRED and required_elevation == ElevationLevel.ADMIN:
            # Elevation requirement is already declared; the UAC wrapper handles
            # it at execution time -- this is not a "block outright" condition.
            return None

        if not confirm_high_risk:
            reasons = "; ".join(warnings[:3]) if warnings else "classified as high risk"
            return ExecutionResult(
                step_id=step_id,
                command=command,
                shell=shell,
                success=False,
                exit_code=-100,
                stdout="",
                stderr=(
                    f"[SAFETY GATE] Refused to execute: {reasons}\n"
                    "This command was predicted to be high-risk/destructive. "
                    "Re-run with confirm_high_risk=True to execute it explicitly."
                ),
            )
    return None


def gate_command(
    command: str,
    shell: ShellType = ShellType.POWERSHELL_51,
    confirm_high_risk: bool = False,
    step_id: str = "gate-check",
    graph=None,
) -> Optional[ExecutionResult]:
    """Classifies `command` and applies the same gate execute_step uses.

    For callers that only have a raw command string -- swarm suggestion
    approval, playbook replay, auto-heal, rollback -- rather than an
    already-planned PlanStep. Returns an ExecutionResult refusal if the
    command must not run, or ``None`` if it's clear to proceed.
    """
    from winterm.models.intent import PlanStep, ActionCategory
    from winterm.cognition.predictor import ImpactPredictor

    step = PlanStep(
        step_id=step_id,
        title="Ad-hoc gated command",
        category=ActionCategory.CUSTOM,
        raw_intent=command,
        command=command,
        target_shell=shell,
    )
    impact = ImpactPredictor.predict_step_impact(step, graph=graph)
    return evaluate_gate_decision(
        risk_level=impact.risk_level,
        warnings=impact.warnings,
        required_elevation=step.required_elevation,
        command=command,
        shell=shell,
        step_id=step_id,
        confirm_high_risk=confirm_high_risk,
    )
