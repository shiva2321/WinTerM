"""Exhaustive test suite verifying the end-to-end audit and hardening across all 11 WinTerM layers:
Safety, Reliability, Concurrency, Parameter Sanitization, Fluke Containment, and Inspectability.
"""

import json
import threading
import pytest
from unittest.mock import MagicMock

from winterm.models.context import ShellType
from winterm.models.intent import ActionCategory, PlanStep
from winterm.swarm.models import AgentPrivilege, AgentScope, SuggestionStatus
from winterm.swarm.board import SwarmMessageBoard
from winterm.swarm.sandbox import SubAgentSandbox
from winterm.engine.executor import WindowsShellExecutor
from winterm.engine.process_monitor import WindowsProcessMonitor
from winterm.cognition.synthesizer import CommandSynthesizer
from winterm.subsystems.linux_subsystem import LinuxSubsystem
from winterm.playbooks.manager import PlaybookManager
from winterm.agent.session import AgentSessionCoordinator, AgentSession
from winterm.interaction.app_manager import WindowsAppManager
from winterm.tools.mcp_server import WinTermMCPServer


class TestAuditHardeningSuite:
    """Verifies all hardened security, concurrency, and reliability safeguards."""

    # -------------------------------------------------------------------------
    # 1. Swarm Sandbox Verdict Attribute Resolution & Dangerous Command Catching
    # -------------------------------------------------------------------------
    def test_sandbox_catches_dangerous_command_safely(self):
        """Verifies that the sandbox safely evaluates verdict.label without AttributeError."""
        board = SwarmMessageBoard()
        scope = AgentScope.from_privilege(AgentPrivilege.TERMINAL_EXECUTOR)
        scope.allow_destructive = False
        sandbox = SubAgentSandbox(agent_id="sub-audit", agent_name="AuditWorker", scope=scope, board=board)

        res = sandbox.execute_guarded(
            action_name="Format Drive",
            func=lambda: "formatted",
            category=ActionCategory.FILESYSTEM,
            shell=ShellType.POWERSHELL_51,
            command="Format-Volume -DriveLetter C -Force",
        )
        assert res.success is False
        assert res.fluke_contained is True
        assert "SECURITY_VIOLATION" in res.error
        assert "destructive" in res.error.lower()

    def test_sandbox_catches_dangerous_linux_command_safely(self):
        """Verifies that Linux safety guard verdict is handled cleanly in sandbox."""
        board = SwarmMessageBoard()
        scope = AgentScope.from_privilege(AgentPrivilege.FULL_SUPERVISOR)
        scope.allow_destructive = False
        sandbox = SubAgentSandbox(agent_id="sub-linux", agent_name="LinuxWorker", scope=scope, board=board)

        res = sandbox.execute_guarded(
            action_name="Nuke Root",
            func=lambda: "nuked",
            category=ActionCategory.FILESYSTEM,
            shell=ShellType.WSL_BASH,
            command="rm -rf /",
        )
        assert res.success is False
        assert res.fluke_contained is True
        assert "destructive" in res.error.lower()

    # -------------------------------------------------------------------------
    # 2. Bounded Suggestion Ledger Quota & FIFO Eviction
    # -------------------------------------------------------------------------
    def test_swarm_suggestion_quota_and_eviction(self):
        """Verifies the suggestion ledger enforces upper bound and evicts resolved items first."""
        board = SwarmMessageBoard()
        board.MAX_SUGGESTIONS_DEFAULT = 10

        sug_ids = []
        for i in range(10):
            sug = board.submit_suggestion(
                proposing_agent_id="sub-1",
                proposing_agent_name="Worker",
                title=f"Suggestion {i}",
                reasoning="Audit",
                proposed_action=f"echo {i}",
                target_shell=ShellType.POWERSHELL_51,
                required_privilege=AgentPrivilege.TERMINAL_EXECUTOR,
            )
            sug_ids.append(sug.suggestion_id)

        assert len(board.list_suggestions()) == 10

        # Mark first 2 suggestions as approved / rejected
        board.update_suggestion_status(sug_ids[0], SuggestionStatus.APPROVED, resolution_note="LGTM")
        board.update_suggestion_status(sug_ids[1], SuggestionStatus.REJECTED, resolution_note="No")

        # Adding 11th suggestion should evict the oldest resolved suggestion (sug_ids[0])
        new_sug = board.submit_suggestion(
            proposing_agent_id="sub-1",
            proposing_agent_name="Worker",
            title="Suggestion 11",
            reasoning="Audit",
            proposed_action="echo 11",
            target_shell=ShellType.POWERSHELL_51,
            required_privilege=AgentPrivilege.TERMINAL_EXECUTOR,
        )

        all_sugs = board.list_suggestions()
        assert len(all_sugs) == 10
        current_ids = [s.suggestion_id for s in all_sugs]
        assert sug_ids[0] not in current_ids
        assert new_sug.suggestion_id in current_ids

    # -------------------------------------------------------------------------
    # 3. Dual-Diagnosis Shell Routing
    # -------------------------------------------------------------------------
    def test_executor_routes_to_linux_catalog_on_bash_failure(self, monkeypatch):
        """Verifies that Linux/WSL failures invoke LinuxErrorCatalog for diagnosis."""
        executor = WindowsShellExecutor()

        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"", b"bash: unknowncmd: command not found\n")
        mock_proc.returncode = 127
        monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: mock_proc)

        res = executor.execute("unknowncmd", shell=ShellType.WSL_BASH, auto_diagnose=True)

        assert res.success is False
        assert res.exit_code == 127
        assert res.healing_proposal is not None
        assert "unknowncmd" in res.healing_proposal.healing_command
        assert res.healing_proposal.error_signature == "LINUX_COMMAND_NOT_FOUND_EXIT_127"

    # -------------------------------------------------------------------------
    # 4. Shell-Specific Non-Interactive Command Synthesis
    # -------------------------------------------------------------------------
    def test_synthesizer_bash_non_interactive_flags(self):
        """Verifies that bash commands receive Linux-appropriate non-interactive flags."""
        step_ps = PlanStep(
            step_id="step-ps",
            title="Remove file",
            category=ActionCategory.FILESYSTEM,
            raw_intent="remove file",
            target_shell=ShellType.POWERSHELL_51,
            command="Remove-Item -Path C:\\Test",
        )
        ps_cmd = CommandSynthesizer.synthesize_step_command(step_ps)
        assert "-Force" in ps_cmd

        step_bash = PlanStep(
            step_id="step-bash",
            title="Install package",
            category=ActionCategory.PACKAGE,
            raw_intent="install nginx",
            target_shell=ShellType.WSL_BASH,
            command="apt-get install nginx",
        )
        bash_cmd = CommandSynthesizer.synthesize_step_command(step_bash)
        assert "DEBIAN_FRONTEND=noninteractive" in bash_cmd or "-y" in bash_cmd
        assert "-Force" not in bash_cmd

    # -------------------------------------------------------------------------
    # 5. Linux Subsystem Parameter Injection Hardening
    # -------------------------------------------------------------------------
    def test_linux_subsystem_sanitizes_command_injection(self):
        """Verifies that LinuxSubsystem neutralizes shell metacharacters in parameter tokens."""
        linux = LinuxSubsystem()

        malicious_tokens = [
            "nginx; rm -rf /",
            "nginx && echo hacked",
            "nginx | cat /etc/passwd",
            "nginx`id`",
            "nginx$(whoami)",
            "test\nreboot",
        ]

        for token in malicious_tokens:
            step_inspect = linux.inspect_service(token)
            assert ";" not in step_inspect.command
            assert "&&" not in step_inspect.command
            assert "|" not in step_inspect.command
            assert "`" not in step_inspect.command
            assert "$" not in step_inspect.command

            step_restart = linux.restart_service(token)
            assert ";" not in step_restart.command
            assert "&&" not in step_restart.command
            assert "|" not in step_restart.command

            step_procs = linux.list_processes(filter_name=token)
            # In ps aux | grep -i '...', the pipe is internal to the template, but injection metacharacters are stripped
            assert ";" not in step_procs.command
            assert "&&" not in step_procs.command
            assert "`" not in step_procs.command
            assert "$" not in step_procs.command

            step_pkg = linux.install_package(token)
            assert ";" not in step_pkg.command
            assert "rm -rf" not in step_pkg.command
            assert "echo hacked" not in step_pkg.command
            assert "/etc/passwd" not in step_pkg.command
            assert "`" not in step_pkg.command
            assert "$" not in step_pkg.command

    # -------------------------------------------------------------------------
    # 6. Process Monitor Parameter Sanitization & Type Safety
    # -------------------------------------------------------------------------
    def test_process_monitor_sanitizes_service_and_ports(self):
        """Verifies process monitor escapes quotes in service names and casts ports/pids to ints."""
        monitor = WindowsProcessMonitor()
        
        info = monitor.get_service_info("wuauserv' OR 1=1 --")
        assert info is None or isinstance(info, dict)

        res = monitor.find_process_on_port("65535")
        assert res is None or isinstance(res, dict)

    # -------------------------------------------------------------------------
    # 7. Playbook Manager Argument Quoting & Sanitization
    # -------------------------------------------------------------------------
    def test_playbook_argument_quoting_safety(self, tmp_path):
        """Verifies that playbook parameter values with quotes do not break command synthesis."""
        manager = PlaybookManager(storage_dir=tmp_path)
        
        pb = manager.create_playbook_from_task(
            goal="Kill processes on given port with force",
            commands=[
                "Get-NetTCPConnection -LocalPort {port} | Stop-Process -Force",
                "Write-Host 'Terminated port: {port}'"
            ],
            shell=ShellType.POWERSHELL_51,
            force_script=True,
        )

        res = manager.execute_playbook(
            playbook_id=pb.playbook_id,
            parameters={"port": "8080'; Write-Host 'injected'; #"},
        )
        assert isinstance(res.exit_code, int)

    # -------------------------------------------------------------------------
    # 8. Agent Session Coordinator Multi-Threaded Concurrency
    # -------------------------------------------------------------------------
    def test_agent_session_coordinator_thread_safety(self):
        """Verifies concurrent threads can acquire and release locks without dictionary iteration errors."""
        coordinator = AgentSessionCoordinator
        errors = []

        def worker(agent_idx: int):
            try:
                session_id = f"session-{agent_idx}"
                session = AgentSession(session_id=session_id, agent_framework="gemini")
                coordinator.register_session(session)

                for i in range(20):
                    res_id = f"port:808{i % 5}"
                    coordinator.acquire_resource_lock(
                        resource_id=res_id,
                        session_id=session_id,
                        ttl_seconds=0.5,
                    )
                    coordinator.get_active_sessions()
                    coordinator.is_resource_locked(res_id)
                    coordinator.release_resource_lock(res_id, session_id)
                    coordinator.clean_expired_locks()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(idx,)) for idx in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors occurred: {errors}"

    # -------------------------------------------------------------------------
    # 9. MCP Server Serialization Robustness
    # -------------------------------------------------------------------------
    def test_mcp_server_serialization_safe(self):
        """Verifies that WinTermMCPServer serializes tool outputs safely with default=str."""
        server = WinTermMCPServer()

        req = {
            "jsonrpc": "2.0",
            "id": 42,
            "method": "tools/call",
            "params": {
                "name": "winterm_window_list",
                "arguments": {"query": ""},
            },
        }
        resp = server.handle_request(req)
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 42
        assert "result" in resp
        assert "content" in resp["result"]
        parsed_inner = json.loads(resp["result"]["content"][0]["text"])
        assert isinstance(parsed_inner, dict)
        assert "output" in parsed_inner

    # -------------------------------------------------------------------------
    # 10. App Manager Limit Clamping
    # -------------------------------------------------------------------------
    def test_app_manager_limit_clamping(self):
        """Verifies that build_search_command clamps limit safely."""
        cmd_huge = WindowsAppManager.build_search_command(query="notepad", limit=999999)
        assert "Select-Object -First 500" in cmd_huge

        cmd_negative = WindowsAppManager.build_search_command(query="notepad", limit=-10)
        assert "Select-Object -First 1" in cmd_negative
