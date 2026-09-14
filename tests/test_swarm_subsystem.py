"""Unit tests for the WinTerM Multi-Agent Swarm subsystem:
Scoped privileges, Message Board coordination, autonomous suggestions, and layered fault-tolerant safety.
"""

import pytest
from winterm.models.context import ShellType
from winterm.models.intent import ActionCategory
from winterm.swarm.models import (
    AgentPrivilege,
    AgentScope,
    MessageType,
    SuggestionStatus,
    SubAgentStatus,
)
from winterm.swarm.board import SwarmMessageBoard
from winterm.swarm.sandbox import (
    SubAgentSandbox,
    CircuitBreaker,
    ScopeViolationError,
    StepLimitExceededError,
    CircuitBreakerTrippedError,
)
from winterm.swarm.subagent import SubAgentWorker
from winterm.swarm.coordinator import SwarmCoordinator
from winterm.tools.tool_definitions import (
    winterm_swarm_dispatch,
    winterm_swarm_board_read,
    winterm_swarm_board_post,
    winterm_swarm_suggestions,
    winterm_swarm_status,
)


class TestLayeredSafetySandbox:
    """Tests the multi-layered sandbox ensuring sub-agents stay strictly within bounds."""

    def test_scope_blocks_unauthorized_category(self):
        board = SwarmMessageBoard()
        scope = AgentScope.from_privilege(AgentPrivilege.READ_ONLY_AUDIT)
        sandbox = SubAgentSandbox(agent_id="sub-1", agent_name="Auditor", scope=scope, board=board)

        # READ_ONLY_AUDIT cannot execute REGISTRY
        res = sandbox.execute_guarded(
            action_name="Modify registry",
            func=lambda: "modified",
            category=ActionCategory.REGISTRY,
        )
        assert res.success is False
        assert res.fluke_contained is True
        assert "SECURITY_VIOLATION" in res.error
        assert "is NOT permitted" in res.error

        # Verify fault was logged to Message Board
        faults = board.get_fault_records()
        assert len(faults) == 1
        assert faults[0].exception_type == "ScopeViolationError"

    def test_scope_blocks_unauthorized_shell(self):
        board = SwarmMessageBoard()
        scope = AgentScope.from_privilege(AgentPrivilege.UI_OPERATOR)
        # UI_OPERATOR only has POWERSHELL_51
        sandbox = SubAgentSandbox(agent_id="sub-2", agent_name="UIOp", scope=scope, board=board)

        res = sandbox.execute_guarded(
            action_name="Bash script",
            func=lambda: "ran",
            category=ActionCategory.DIAGNOSTIC,
            shell=ShellType.WSL_BASH,
        )
        assert res.success is False
        assert "NOT authorized" in res.error

    def test_scope_blocks_desktop_interaction_when_disabled(self):
        board = SwarmMessageBoard()
        scope = AgentScope.from_privilege(AgentPrivilege.READ_ONLY_AUDIT)
        sandbox = SubAgentSandbox(agent_id="sub-3", agent_name="Auditor", scope=scope, board=board)

        res = sandbox.execute_guarded(
            action_name="Click window",
            func=lambda: "clicked",
            is_desktop_interaction=True,
        )
        assert res.success is False
        assert "Desktop GUI interaction is denied" in res.error

    def test_step_limit_fences(self):
        board = SwarmMessageBoard()
        scope = AgentScope(max_steps=2)
        sandbox = SubAgentSandbox(agent_id="sub-4", agent_name="Looper", scope=scope, board=board)

        r1 = sandbox.execute_guarded("Step 1", lambda: 1)
        r2 = sandbox.execute_guarded("Step 2", lambda: 2)
        r3 = sandbox.execute_guarded("Step 3", lambda: 3)

        assert r1.success is True
        assert r2.success is True
        assert r3.success is False
        assert "exceeded maximum permitted execution quota" in r3.error

    def test_fluke_containment_and_circuit_breaker(self):
        board = SwarmMessageBoard()
        scope = AgentScope.from_privilege(AgentPrivilege.FULL_SUPERVISOR)
        sandbox = SubAgentSandbox(agent_id="sub-5", agent_name="CrashTest", scope=scope, board=board)

        def buggy_os_call():
            raise OSError("Win32 Fluke: Unexpected device communication error (0x8007001F)")

        # 1st and 2nd failure: caught, logged, fluke contained
        res1 = sandbox.execute_guarded("Call 1", buggy_os_call)
        assert res1.success is False
        assert res1.fluke_contained is True
        assert "FLUKE_CONTAINED" in res1.error

        res2 = sandbox.execute_guarded("Call 2", buggy_os_call)
        assert res2.success is False

        # 3rd failure: trips circuit breaker
        res3 = sandbox.execute_guarded("Call 3", buggy_os_call)
        assert res3.success is False
        assert sandbox.circuit_breaker.is_isolated is True

        # 4th call: immediately rejected because circuit breaker is tripped
        res4 = sandbox.execute_guarded("Call 4", lambda: "ok")
        assert res4.success is False
        assert "Circuit breaker is TRIPPED" in res4.error


class TestSwarmMessageBoard:
    """Tests coordination message bus, suggestions, and fault log retention."""

    def test_post_and_get_messages(self):
        board = SwarmMessageBoard(max_messages=10)
        board.post_message("sub-1", MessageType.PROGRESS_UPDATE, "Starting port audit")
        board.post_message("sub-2", MessageType.ALERT, "Port 8080 busy", recipient_id="main_agent")

        msgs = board.get_messages()
        assert len(msgs) == 2

        filtered = board.get_messages(filter_type=MessageType.ALERT)
        assert len(filtered) == 1
        assert filtered[0].content == "Port 8080 busy"

    def test_suggestions_lifecycle(self):
        board = SwarmMessageBoard()
        sug = board.submit_suggestion(
            proposing_agent_id="sub-1",
            proposing_agent_name="Auditor-1",
            title="Clean stale temp files",
            reasoning="Temp folder contains 500MB old logs",
            proposed_action="Remove-Item 'C:\\Temp\\*.log'",
            target_shell=ShellType.POWERSHELL_51,
            required_privilege=AgentPrivilege.TERMINAL_EXECUTOR,
        )

        assert sug.status == SuggestionStatus.PENDING
        pending = board.get_pending_suggestions()
        assert len(pending) == 1
        assert pending[0].suggestion_id == sug.suggestion_id

        # Update status
        updated = board.update_suggestion_status(sug.suggestion_id, SuggestionStatus.APPROVED, "Approved by admin")
        assert updated is True
        assert len(board.get_pending_suggestions()) == 0


class TestSubAgentWorker:
    """Tests autonomous worker capabilities within scopes and suggestion formulation."""

    def test_worker_executes_within_scope(self):
        board = SwarmMessageBoard()
        worker = SubAgentWorker(
            name="NetworkAuditor",
            privilege=AgentPrivilege.NETWORK_INSPECTOR,
            board=board,
        )
        res = worker.execute_command(
            command="echo 'Audit network'",
            shell=ShellType.POWERSHELL_51,
            category=ActionCategory.DIAGNOSTIC,
        )
        assert res.success is True

        # Telemetry check
        telemetry = worker.get_telemetry()
        assert telemetry.name == "NetworkAuditor"
        assert telemetry.steps_executed == 1
        assert telemetry.is_isolated is False

    def test_worker_proposes_suggestion(self):
        board = SwarmMessageBoard()
        worker = SubAgentWorker(name="Scanner", privilege=AgentPrivilege.READ_ONLY_AUDIT, board=board)
        sug = worker.propose_suggestion(
            title="Restart Spooler",
            reasoning="Print spooler service is hanging",
            proposed_action="Restart-Service spooler",
        )
        assert sug.proposing_agent_name == "Scanner"
        assert len(board.get_pending_suggestions()) == 1


class TestSwarmCoordinator:
    """Tests swarm orchestration, overseer directives, and suggestion reviews."""

    def test_dispatch_and_status(self):
        coord = SwarmCoordinator()
        worker1 = coord.dispatch_subagent(name="Auditor", goal="Audit memory", privilege=AgentPrivilege.READ_ONLY_AUDIT)
        worker2 = coord.dispatch_subagent(name="UIBot", goal="Inspect Notepad", privilege=AgentPrivilege.UI_OPERATOR)

        status = coord.get_swarm_status()
        assert status["active_agents_count"] == 2
        agent_names = [a["name"] for a in status["agents"]]
        assert "Auditor" in agent_names
        assert "UIBot" in agent_names

    def test_broadcast_directive(self):
        coord = SwarmCoordinator()
        msg = coord.broadcast_directive("Pause all audits for maintenance")
        assert msg.sender_role == "main_agent"
        assert msg.recipient_id == "broadcast"

    def test_approve_and_reject_suggestion(self):
        coord = SwarmCoordinator()
        worker = coord.dispatch_subagent(name="Worker", privilege=AgentPrivilege.READ_ONLY_AUDIT)
        sug = worker.propose_suggestion(
            title="Echo test",
            reasoning="Test execution",
            proposed_action="echo 'Approved Action'",
        )

        pending = coord.review_suggestions()
        assert len(pending) == 1

        # Approve and execute
        res = coord.approve_suggestion(sug.suggestion_id, execute_now=True)
        assert res["approved"] is True
        assert res["executed"] is True

        # Check suggestions list is now empty of pending
        assert len(coord.review_suggestions()) == 0


class TestSwarmMCPTools:
    """Tests the 5 Swarm MCP tools exposed to AI agents."""

    def test_swarm_mcp_tools(self):
        # 1. Dispatch
        dispatch_res = winterm_swarm_dispatch(
            tasks=[
                {"name": "AuditBot", "goal": "Check disk space", "privilege": "read_only_audit"},
                {"name": "NetBot", "goal": "Inspect open ports", "privilege": "network_inspector"},
            ]
        )
        assert dispatch_res["dispatched_count"] == 2

        # 2. Board Read
        msgs = winterm_swarm_board_read(limit=10)
        assert isinstance(msgs, list)
        assert len(msgs) >= 2

        # 3. Board Post
        post_res = winterm_swarm_board_post(directive="Swarm standing by")
        assert "message_id" in post_res

        # 4. Status
        status = winterm_swarm_status()
        assert status["active_agents_count"] >= 2

        # 5. Suggestions
        sug_res = winterm_swarm_suggestions(action="list")
        assert "pending_suggestions" in sug_res
