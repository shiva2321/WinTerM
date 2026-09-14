"""Tests for Windows Knowledge Base, Shell Matrix, Reliability Rules, and Error Catalog."""

import pytest
from winterm.models.context import ShellType
from winterm.knowledge.shell_matrix import ShellMatrix
from winterm.knowledge.reliability_rules import ReliabilityRules
from winterm.knowledge.encoding_expert import EncodingExpert
from winterm.knowledge.error_catalog import WindowsErrorCatalog
from winterm.knowledge.elevation_rules import ElevationRules


def test_shell_matrix_recommendation():
    # Structured system categories should recommend PowerShell
    rec = ShellMatrix.recommend_shell("service", "restart service spooler")
    assert rec in (ShellType.POWERSHELL_51, ShellType.POWERSHELL_7)

    # Legacy script extensions should recommend CMD
    rec_cmd = ShellMatrix.recommend_shell("custom", "build.bat")
    assert rec_cmd == ShellType.CMD


def test_reliability_rules_unicode_sanitization():
    raw = "Build completed ✓ with 0 errors ❌. ⚠️ Warning in line 12."
    sanitized = ReliabilityRules.sanitize_for_windows_console(raw)
    assert "✓" not in sanitized
    assert "❌" not in sanitized
    assert "[OK]" in sanitized
    assert "[X]" in sanitized
    assert "[WARN]" in sanitized


def test_reliability_rules_quoting_and_call_operator():
    # Path with spaces
    path = r"C:\Program Files\nodejs\node.exe"
    quoted = ReliabilityRules.quote_path_if_needed(path)
    assert quoted == r'"C:\Program Files\nodejs\node.exe"'

    # Call operator insertion for PowerShell
    cmd = r'"C:\Program Files\dotnet\dotnet.exe" --version'
    formatted = ReliabilityRules.format_executable_invocation(cmd, ShellType.POWERSHELL_51)
    assert formatted.startswith("& ")


def test_reliability_rules_ps_condition_parentheses():
    # Flawed PS expression without parentheses
    bad_expr = "if (Test-Path a -or Test-Path b)"
    fixed = ReliabilityRules.ensure_parentheses_in_ps_conditions(bad_expr)
    assert "(Test-Path a) -or (Test-Path b)" in fixed


def test_reliability_rules_non_interactive_switches():
    cmd = "Remove-Item C:\\temp\\old -Recurse"
    safe_cmd = ReliabilityRules.make_non_interactive(cmd)
    assert "-Confirm:$false" in safe_cmd
    assert "-Force" in safe_cmd

    winget_cmd = "winget install Git.Git"
    safe_winget = ReliabilityRules.make_non_interactive(winget_cmd)
    assert "--accept-source-agreements" in safe_winget
    assert "--accept-package-agreements" in safe_winget


def test_encoding_expert_decoding():
    # UTF-8 decode
    b_utf8 = "Hello Windows 终端".encode("utf-8")
    assert "终端" in EncodingExpert.decode_stream(b_utf8)

    # CP1252 / ANSI decode fallback
    b_ansi = "Café résumé".encode("cp1252")
    assert "Café" in EncodingExpert.decode_stream(b_ansi)


def test_error_catalog_diagnosis():
    # Test 0x80070005 Access Denied
    diag_access = WindowsErrorCatalog.diagnose(
        stderr="Error: 0x80070005 Access is denied.",
        stdout="",
        exit_code=5,
        failed_command="Set-ItemProperty HKLM:\\Software\\Test",
    )
    assert diag_access is not None
    assert diag_access.error_signature == "ACCESS_DENIED_0x80070005"
    assert diag_access.requires_elevation is True

    # Test ExecutionPolicy
    diag_exec = WindowsErrorCatalog.diagnose(
        stderr="File script.ps1 cannot be loaded because running scripts is disabled on this system.",
        stdout="",
        exit_code=1,
    )
    assert diag_exec is not None
    assert diag_exec.error_signature == "EXECUTION_POLICY_RESTRICTED"
    assert "Bypass" in diag_exec.healing_command


def test_elevation_rules_check():
    assert ElevationRules.requires_elevation("Set-ItemProperty -Path 'HKLM:\\System'") is True
    assert ElevationRules.requires_elevation("Restart-Service spooler") is True
    assert ElevationRules.requires_elevation("Get-Process") is False
