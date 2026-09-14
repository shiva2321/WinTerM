"""Tests for Windows Shell Executor."""

import pytest
from winterm.engine.executor import WindowsShellExecutor
from winterm.models.context import ShellType


def test_executor_powershell_success():
    executor = WindowsShellExecutor(default_shell=ShellType.POWERSHELL_51)
    res = executor.execute("Write-Output 'WinTerm-OK'")
    assert res.success is True
    assert res.exit_code == 0
    assert "WinTerm-OK" in res.stdout


def test_executor_cmd_success():
    executor = WindowsShellExecutor(default_shell=ShellType.CMD)
    res = executor.execute("echo CMD-OK", shell=ShellType.CMD)
    assert res.success is True
    assert res.exit_code == 0
    assert "CMD-OK" in res.stdout


def test_executor_powershell_failure_and_auto_diagnosis():
    executor = WindowsShellExecutor(default_shell=ShellType.POWERSHELL_51)
    res = executor.execute("Get-Item 'C:\\NonExistentPath123456789' -ErrorAction Stop")
    assert res.success is False
    assert res.exit_code != 0
    assert len(res.stderr) > 0
    # Auto diagnosis should identify path not found
    assert res.healing_proposal is not None
    assert "PATH_NOT_FOUND" in res.healing_proposal.error_signature


def test_executor_timeout_handling():
    executor = WindowsShellExecutor(default_shell=ShellType.POWERSHELL_51)
    # Run sleep for 5 seconds with 1 second timeout
    res = executor.execute("Start-Sleep -Seconds 5", timeout_seconds=1)
    assert res.timed_out is True
    assert res.success is False
