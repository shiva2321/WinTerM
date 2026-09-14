"""Tests for Impact Predictor and State Diff Simulation."""

from winterm.cognition.predictor import ImpactPredictor
from winterm.models.intent import PlanStep, ActionCategory
from winterm.models.impact import RiskLevel
from winterm.models.context import ShellType


def test_predictor_read_only():
    step = PlanStep(
        step_id="step-read",
        title="List files",
        category=ActionCategory.FILESYSTEM,
        raw_intent="list dir",
        command="Get-ChildItem -Path C:\\",
        target_shell=ShellType.POWERSHELL_51,
    )
    impact = ImpactPredictor.predict_step_impact(step)
    assert impact.risk_level == RiskLevel.READ_ONLY
    assert impact.is_reversible is True


def test_predictor_directory_creation():
    step = PlanStep(
        step_id="step-mkdir",
        title="Make directory",
        category=ActionCategory.FILESYSTEM,
        raw_intent="create dir",
        command="New-Item -ItemType Directory -Path C:\\temp\\agent_data",
        target_shell=ShellType.POWERSHELL_51,
    )
    impact = ImpactPredictor.predict_step_impact(step)
    assert impact.risk_level == RiskLevel.SAFE
    assert r"C:\temp\agent_data" in impact.state_diff.filesystem.created_paths
    assert impact.rollback is not None
    assert "Remove-Item" in impact.rollback.command


def test_predictor_process_kill():
    step = PlanStep(
        step_id="step-kill",
        title="Kill node",
        category=ActionCategory.PROCESS,
        raw_intent="terminate node",
        command="Stop-Process -Id 1234 -Force",
        target_shell=ShellType.POWERSHELL_51,
        metadata={"process_name": "node"},
    )
    impact = ImpactPredictor.predict_step_impact(step)
    assert impact.risk_level == RiskLevel.MEDIUM
    assert any("node" in p for p in impact.state_diff.processes.terminated_processes)
    assert impact.is_reversible is False


def test_predictor_destructive_file_removal():
    step = PlanStep(
        step_id="step-del",
        title="Delete temp files",
        category=ActionCategory.FILESYSTEM,
        raw_intent="delete temp",
        command="Remove-Item -Path C:\\temp\\agent_data -Recurse -Force",
        target_shell=ShellType.POWERSHELL_51,
    )
    impact = ImpactPredictor.predict_step_impact(step)
    assert impact.risk_level == RiskLevel.HIGH_DESTRUCTIVE
    assert impact.is_reversible is False
