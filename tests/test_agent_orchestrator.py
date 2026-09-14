"""Tests for Master WinTermAgent and End-to-End 5W Lifecycle."""

import pytest
from winterm.agent.winterm_agent import WinTermAgent
from winterm.models.intent import StepStatus
from winterm.models.impact import RiskLevel


def test_agent_plan_and_explain():
    agent = WinTermAgent()
    plan = agent.plan("Find process on port 8080 and terminate it")
    assert len(plan.steps) >= 2

    step1 = plan.steps[0]
    trace = agent.explain(step1)

    assert "Get-NetTCPConnection" in trace.what
    assert len(trace.why.command_justification) > 0
    assert any("netstat" in alt.alternative for alt in trace.why.alternatives_rejected)


def test_agent_dry_run():
    agent = WinTermAgent()
    plan = agent.plan("Query top 5 memory processes")
    step = plan.steps[0]

    res, verif, trace = agent.execute_step(step, dry_run=True)
    assert res.success is True
    assert "[DRY-RUN]" in res.stdout


def test_safety_gate_refuses_destructive_without_confirmation():
    """HIGH_DESTRUCTIVE commands must be refused unless explicitly confirmed."""
    agent = WinTermAgent()
    from winterm.models.intent import PlanStep, ActionCategory
    from winterm.models.context import ShellType, ElevationLevel

    step = PlanStep(
        step_id="destructive-test",
        title="Delete system folder",
        category=ActionCategory.CUSTOM,
        raw_intent="delete system32",
        command="Remove-Item -Recurse -Force C:\\Windows\\System32",
        target_shell=ShellType.POWERSHELL_51,
        required_elevation=ElevationLevel.STANDARD,
    )

    # Without confirmation -> refused, nothing executed
    res, verif, trace = agent.execute_step(step, dry_run=False, confirm_high_risk=False)
    assert res.success is False
    assert "SAFETY GATE" in res.stderr
    assert res.exit_code == -100


def test_safety_gate_allows_safe_commands():
    """Read-only commands execute normally through the gate."""
    agent = WinTermAgent()
    from winterm.models.intent import PlanStep, ActionCategory
    from winterm.models.context import ShellType, ElevationLevel

    step = PlanStep(
        step_id="safe-test",
        title="Query processes",
        category=ActionCategory.CUSTOM,
        raw_intent="list processes",
        command="Get-Process | Select-Object -First 1 Name",
        target_shell=ShellType.POWERSHELL_51,
        required_elevation=ElevationLevel.STANDARD,
    )

    res, verif, trace = agent.execute_step(step, dry_run=False, confirm_high_risk=False)
    assert res.success is True
    assert res.exit_code == 0


def test_agent_live_execution_and_session_recording():
    agent = WinTermAgent()
    plan = agent.plan("Query system hardware info")
    step = plan.steps[0]

    res, verif, trace = agent.execute_step(step, dry_run=False)
    assert res.success is True
    assert len(agent.session.history) == 1
    record = agent.session.history[0]
    assert record.step.step_id == step.step_id
    assert record.execution_result.success is True


def test_agent_rollback_stack():
    agent = WinTermAgent()
    from winterm.models.intent import PlanStep, ActionCategory
    from winterm.models.context import ShellType

    # Step that creates a temporary directory
    step = PlanStep(
        step_id="test-rollback",
        title="Create temp test directory",
        category=ActionCategory.FILESYSTEM,
        raw_intent="create dir",
        command="New-Item -ItemType Directory -Path 'C:\\temp\\winterm_rollback_test' -Force",
        target_shell=ShellType.POWERSHELL_51,
    )

    res, verif, trace = agent.execute_step(step, dry_run=False)
    assert res.success is True
    assert len(agent.session.rollback_stack) >= 1

    # Undo
    undo_res = agent.undo_last_action()
    assert undo_res is not None
    assert undo_res.success is True
    assert len(agent.session.rollback_stack) == 0


def test_agent_audio_troubleshooting_plan_and_execution():
    """Agent creates a staged multi-step audio plan, records session history, and queries Knowledge Graph."""
    agent = WinTermAgent()
    plan = agent.plan("troubleshoot audio problem")
    assert len(plan.steps) == 4
    step_ids = [s.step_id for s in plan.steps]
    assert "audio-svc-audit" in step_ids
    assert "audio-hw-probe" in step_ids
    assert "audio-pnp-audit" in step_ids

    # Knowledge Graph verification
    blast = agent.calculate_blast_radius("Audiosrv")
    assert blast.risk_score == "LOW"
    ep_blast = agent.calculate_blast_radius("AudioEndpointBuilder")
    assert "Audiosrv" in ep_blast.direct_dependents

    # Execute first step and verify session recording
    res, verif, trace = agent.execute_step(plan.steps[0], dry_run=False)
    assert res.success is True
    assert len(agent.session.history) >= 1
    assert agent.session.history[-1].step.step_id == "audio-svc-audit"

