"""Tests for Command Synthesizer."""

from winterm.cognition.synthesizer import CommandSynthesizer
from winterm.models.intent import PlanStep, ActionCategory
from winterm.models.context import ShellType, ElevationLevel


def test_synthesizer_basic():
    step = PlanStep(
        step_id="step-1",
        title="Remove old logs",
        category=ActionCategory.FILESYSTEM,
        raw_intent="delete logs",
        command="Remove-Item C:\\Logs\\*.log",
        target_shell=ShellType.POWERSHELL_51,
    )
    res = CommandSynthesizer.synthesize_step_command(step)
    assert "-Confirm:$false" in res
    assert "-Force" in res


def test_synthesizer_json_depth():
    step = PlanStep(
        step_id="step-2",
        title="Export config",
        category=ActionCategory.CUSTOM,
        raw_intent="export json",
        command="Get-Service | ConvertTo-Json",
        target_shell=ShellType.POWERSHELL_51,
    )
    res = CommandSynthesizer.synthesize_step_command(step)
    assert "ConvertTo-Json -Depth 10" in res


def test_synthesizer_call_operator():
    step = PlanStep(
        step_id="step-3",
        title="Run git",
        category=ActionCategory.GIT,
        raw_intent="check status",
        command='"C:\\Program Files\\Git\\bin\\git.exe" status',
        target_shell=ShellType.POWERSHELL_51,
    )
    res = CommandSynthesizer.synthesize_step_command(step)
    assert res.startswith("& ")


def test_synthesizer_elevation_wrap():
    step = PlanStep(
        step_id="step-4",
        title="Admin task",
        category=ActionCategory.SYSTEM,
        raw_intent="restart computer",
        command="Restart-Computer",
        target_shell=ShellType.POWERSHELL_51,
        required_elevation=ElevationLevel.ADMIN,
    )
    res = CommandSynthesizer.synthesize_step_command(step)
    assert "Start-Process" in res
    assert "-Verb RunAs" in res
