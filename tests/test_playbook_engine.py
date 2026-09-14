"""Unit tests for the Reusable Task Playbook subsystem, Script Justification Gate,
and script generalization engine.
"""

import tempfile
import pytest
from pathlib import Path

from winterm.models.context import ShellType
from winterm.playbooks.models import Playbook, PlaybookParameter
from winterm.playbooks.gate import ScriptJustificationGate, ScriptNotJustifiedError
from winterm.playbooks.generalizer import ScriptGeneralizer
from winterm.playbooks.manager import PlaybookManager
from winterm.tools.tool_definitions import (
    winterm_playbook_create,
    winterm_playbook_match_run,
    winterm_playbook_list,
    winterm_playbook_prune,
)


class TestScriptJustificationGate:
    """Tests the architectural gate ensuring scripts are ONLY built when strictly needed."""

    def test_rejects_empty_commands(self):
        result = ScriptJustificationGate.evaluate("Do nothing", [])
        assert not result.is_justified
        assert not result.requires_script
        assert "No commands provided" in result.reason
        assert result.suggested_action == "execute_direct"

    def test_rejects_atomic_single_commands(self):
        atomic_cases = [
            "Get-Process",
            "ipconfig /all",
            "ls -la",
            "docker ps",
            "Stop-Process -Id 1234",
            "git status",
            "curl https://api.example.com/health",
        ]
        for cmd in atomic_cases:
            res = ScriptJustificationGate.evaluate(f"Run {cmd}", [cmd])
            assert not res.is_justified, f"Command '{cmd}' should have been rejected by gate"
            assert not res.requires_script
            assert res.suggested_action == "execute_direct"
            assert "atomic" in res.reason.lower()

    def test_approves_multi_step_workflow(self):
        cmds = [
            "Get-NetTCPConnection -LocalPort 8080",
            "Stop-Process -Id 4321 -Force",
        ]
        res = ScriptJustificationGate.evaluate("Kill process on port 8080", cmds)
        assert res.is_justified
        assert res.requires_script
        assert res.suggested_action == "synthesize_script"
        assert "2 interdependent sequential commands" in res.reason

    def test_approves_single_command_with_control_flow(self):
        control_cmds = [
            "if (Test-Path 'C:\\Logs') { Remove-Item 'C:\\Logs' -Recurse }",
            "for ($i=0; $i -lt 5; $i++) { Write-Host $i }",
            "try { Restart-Service wuauserv } catch { Write-Error 'Failed' }",
            "systemctl restart nginx || exit 1",
            "mkdir -p /tmp/build && cd /tmp/build",
        ]
        for cmd in control_cmds:
            res = ScriptJustificationGate.evaluate("Execute logic", [cmd])
            assert res.is_justified, f"Command '{cmd}' should be justified due to control flow"
            assert res.requires_script
            assert res.suggested_action == "synthesize_script"

    def test_approves_multiline_script_block(self):
        multiline = """
        $p = Get-Process -Name node -ErrorAction SilentlyContinue
        if ($p) {
            $p | Stop-Process -Force
        }
        """
        res = ScriptJustificationGate.evaluate("Clean node", [multiline])
        assert res.is_justified
        assert res.requires_script

    def test_force_script_override(self):
        res = ScriptJustificationGate.evaluate(
            "Quick process query",
            ["Get-Process"],
            force_script=True,
        )
        assert res.is_justified
        assert res.requires_script
        assert "override" in res.reason.lower()


class TestScriptGeneralizer:
    """Tests literal abstraction, parameter schemas, and script synthesis."""

    def test_extract_port_parameter(self):
        sig, params = ScriptGeneralizer.extract_signature_and_params(
            goal="Kill process occupying port 9090",
            commands=["Get-NetTCPConnection -LocalPort 9090 | Stop-Process"],
        )
        assert "{port}" in sig
        assert any(p.name == "port" and p.default_value == 9090 for p in params)

    def test_extract_windows_path_parameter(self):
        sig, params = ScriptGeneralizer.extract_signature_and_params(
            goal="Archive log directory C:\\MyApp\\Logs",
            commands=["Compress-Archive -Path C:\\MyApp\\Logs -Destination C:\\Archive.zip"],
        )
        assert "{path}" in sig
        assert any(p.name == "path" and "C:\\MyApp\\Logs" in str(p.default_value) for p in params)

    def test_synthesize_powershell_script(self):
        params = [
            PlaybookParameter(name="port", param_type="int", default_value=8080, description="Port number"),
        ]
        script = ScriptGeneralizer.synthesize_playbook_script(
            commands=["Get-NetTCPConnection -LocalPort {port}", "Stop-Process -Force"],
            params=params,
            shell=ShellType.POWERSHELL_51,
        )
        assert "[CmdletBinding()]" in script
        assert "param" in script
        assert "$Port = 8080" in script
        assert "$ErrorActionPreference = 'Stop'" in script

    def test_synthesize_bash_script(self):
        params = [
            PlaybookParameter(name="port", param_type="int", default_value=3000, description="Port number"),
        ]
        script = ScriptGeneralizer.synthesize_playbook_script(
            commands=["fuser -k {port}/tcp"],
            params=params,
            shell=ShellType.WSL_BASH,
        )
        assert "#!/usr/bin/env bash" in script
        assert "set -eo pipefail" in script
        assert "PORT=\"${1:-3000}\"" in script


class TestPlaybookManager:
    """Tests the lifecycle: gate enforcement, recurrence tracking, auto-promotion, and LRU pruning."""

    def test_atomic_command_not_tracked_in_candidates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = PlaybookManager(storage_dir=tmpdir)
            # Repeated atomic one-liners should NOT be added to candidates
            res1 = mgr.record_task_execution(
                goal="Check network",
                commands=["ipconfig /all"],
                shell=ShellType.CMD,
            )
            assert res1 is None
            assert len(mgr._candidates) == 0

    def test_candidate_recurrence_and_promotion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = PlaybookManager(storage_dir=tmpdir)
            cmds = [
                "Get-NetTCPConnection -LocalPort 8080",
                "Stop-Process -Id 1234 -Force",
            ]
            goal = "Free port 8080"

            # 1st execution: enters candidate buffer
            res1 = mgr.record_task_execution(goal, cmds, shell=ShellType.POWERSHELL_51)
            assert res1 is None
            assert len(mgr._candidates) == 1

            # 2nd execution: reaches recurrence threshold (2) -> promoted to Playbook
            res2 = mgr.record_task_execution(goal, cmds, shell=ShellType.POWERSHELL_51)
            assert res2 is not None
            assert isinstance(res2, Playbook)
            assert len(mgr._candidates) == 0
            assert len(mgr._playbooks) == 1
            assert (Path(tmpdir) / f"{res2.playbook_id}.ps1").exists()

    def test_create_playbook_gate_enforcement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = PlaybookManager(storage_dir=tmpdir)
            # Attempting to create a playbook for an atomic command must raise ScriptNotJustifiedError
            with pytest.raises(ScriptNotJustifiedError):
                mgr.create_playbook_from_task(
                    goal="Check process",
                    commands=["Get-Process"],
                    shell=ShellType.POWERSHELL_51,
                )

            # Unless force_script=True is explicitly passed
            forced_pb = mgr.create_playbook_from_task(
                goal="Check process",
                commands=["Get-Process"],
                shell=ShellType.POWERSHELL_51,
                force_script=True,
            )
            assert forced_pb is not None
            assert forced_pb.playbook_id in mgr._playbooks

    def test_lru_quota_pruning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = PlaybookManager(storage_dir=tmpdir)
            # Create 3 multi-step playbooks
            for i in range(3):
                mgr.create_playbook_from_task(
                    goal=f"Workflow step {i}",
                    commands=[f"echo step1_{i}", f"echo step2_{i}"],
                    shell=ShellType.POWERSHELL_51,
                    name=f"Workflow {i}",
                )

            assert len(mgr.list_playbooks()) == 3
            purged = mgr.prune_playbooks(max_items=1)
            assert purged == 2
            assert len(mgr.list_playbooks()) == 1


class TestPlaybookMCPTools:
    """Tests the 4 MCP tools exposed to AI agents."""

    def test_winterm_playbook_create_rejects_atomic_command(self):
        res = winterm_playbook_create(
            goal="Get active processes",
            commands=["Get-Process"],
        )
        assert res["created"] is False
        assert res["requires_script"] is False
        assert "atomic" in res["reason"].lower()
        assert "execute_direct" in res["suggested_action"]

    def test_winterm_playbook_create_accepts_multi_step_workflow(self):
        res = winterm_playbook_create(
            goal="Free port 5000",
            commands=[
                "netstat -ano | findstr :5000",
                "taskkill /PID 9999 /F",
            ],
            target_shell="cmd",
        )
        assert res["created"] is True
        assert res["requires_script"] is True
        assert "playbook_id" in res
        assert "pb-" in res["playbook_id"]

    def test_winterm_playbook_list_and_prune(self):
        # List tools
        catalog = winterm_playbook_list()
        assert isinstance(catalog, list)

        # Prune tool
        prune_res = winterm_playbook_prune(max_items=10)
        assert "purged_count" in prune_res
        assert "remaining_playbooks" in prune_res
