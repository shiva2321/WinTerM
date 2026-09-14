"""Sub-Agent Worker: Autonomous agent running bounded by privilege scopes, coordinating
via the Message Board, and proposing proactive suggestions.
"""

from __future__ import annotations

import time
import uuid
from typing import Dict, Any, List, Optional

from winterm.models.context import ShellType
from winterm.models.intent import ActionCategory
from winterm.models.result import ExecutionResult
from winterm.engine.executor import WindowsShellExecutor
from winterm.swarm.models import (
    AgentPrivilege,
    AgentScope,
    SubAgentStatus,
    MessageType,
    SubAgentTelemetry,
    SwarmSuggestion,
)
from winterm.swarm.board import SwarmMessageBoard
from winterm.swarm.sandbox import SubAgentSandbox, SafeExecutionResult


class SubAgentWorker:
    """An autonomous worker operating strictly within its assigned privilege boundaries."""

    def __init__(
        self,
        name: str,
        privilege: AgentPrivilege = AgentPrivilege.READ_ONLY_AUDIT,
        scope: Optional[AgentScope] = None,
        board: Optional[SwarmMessageBoard] = None,
        executor: Optional[WindowsShellExecutor] = None,
        agent_id: Optional[str] = None,
    ):
        self.agent_id = agent_id or f"sub-{uuid.uuid4().hex[:8]}"
        self.name = name
        self.privilege = privilege
        self.scope = scope or AgentScope.from_privilege(privilege)
        self.board = board or SwarmMessageBoard()
        self.executor = executor or WindowsShellExecutor()
        self.sandbox = SubAgentSandbox(
            agent_id=self.agent_id,
            agent_name=self.name,
            scope=self.scope,
            board=self.board,
        )

        self.status = SubAgentStatus.IDLE
        self.current_goal = ""
        self.created_at = time.time()
        self.last_heartbeat = time.time()

    # =========================================================================
    # 1. AUTONOMOUS COMMAND EXECUTION (GUARDED)
    # =========================================================================

    def execute_command(
        self,
        command: str,
        shell: ShellType = ShellType.POWERSHELL_51,
        category: ActionCategory = ActionCategory.DIAGNOSTIC,
    ) -> SafeExecutionResult:
        """Executes a terminal command within the layered safety sandbox."""
        self.last_heartbeat = time.time()
        self.status = SubAgentStatus.RUNNING

        def _do_execute() -> ExecutionResult:
            return self.executor.execute(
                command=command,
                shell=shell,
                timeout_seconds=int(self.scope.timeout_seconds),
            )

        safe_res = self.sandbox.execute_guarded(
            action_name=f"Execute: {command[:50]}",
            func=_do_execute,
            category=category,
            shell=shell,
            command=command,
            is_desktop_interaction=False,
        )

        # Notify board of milestone or failure
        if not safe_res.success:
            self.board.post_message(
                sender_id=self.agent_id,
                message_type=MessageType.TASK_FAILED,
                content=f"Sub-agent '{self.name}' failed executing command: {safe_res.error}",
                payload={"command": command, "error": safe_res.error},
            )
        else:
            self.board.post_message(
                sender_id=self.agent_id,
                message_type=MessageType.PROGRESS_UPDATE,
                content=f"Sub-agent '{self.name}' successfully executed: {command[:60]}",
            )

        self.status = SubAgentStatus.IDLE
        return safe_res

    # =========================================================================
    # 2. AUTONOMOUS UI / DESKTOP AUTOMATION (GUARDED)
    # =========================================================================

    def execute_ui_action(
        self,
        action_name: str,
        ui_func: Any,
        *args: Any,
        **kwargs: Any,
    ) -> SafeExecutionResult:
        """Executes a desktop GUI or UI Automation action within the layered sandbox."""
        self.last_heartbeat = time.time()
        self.status = SubAgentStatus.RUNNING

        safe_res = self.sandbox.execute_guarded(
            action_name=action_name,
            func=ui_func,
            *args,
            category=ActionCategory.DIAGNOSTIC if "inspect" in action_name.lower() else ActionCategory.SYSTEM,
            is_desktop_interaction=True,
            **kwargs,
        )

        self.status = SubAgentStatus.IDLE
        return safe_res

    # =========================================================================
    # 3. PROACTIVE SUGGESTIONS PIPELINE
    # =========================================================================

    def propose_suggestion(
        self,
        title: str,
        reasoning: str,
        proposed_action: str,
        target_shell: ShellType = ShellType.POWERSHELL_51,
        required_privilege: AgentPrivilege = AgentPrivilege.TERMINAL_EXECUTOR,
    ) -> SwarmSuggestion:
        """Proactively formulates a recommendation for main agent oversight."""
        self.last_heartbeat = time.time()
        return self.board.submit_suggestion(
            proposing_agent_id=self.agent_id,
            proposing_agent_name=self.name,
            title=title,
            reasoning=reasoning,
            proposed_action=proposed_action,
            target_shell=target_shell,
            required_privilege=required_privilege,
        )

    # =========================================================================
    # 4. TASK LIFECYCLE & TELEMETRY
    # =========================================================================

    def run_subtask(self, goal: str, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Runs a staged sequence of commands for an assigned sub-goal."""
        self.current_goal = goal
        self.status = SubAgentStatus.RUNNING
        self.board.post_message(
            sender_id=self.agent_id,
            message_type=MessageType.PROGRESS_UPDATE,
            content=f"Sub-agent '{self.name}' started task: {goal}",
        )

        results: List[SafeExecutionResult] = []
        for item in commands:
            cmd = item.get("command", "")
            shell_val = item.get("shell", ShellType.POWERSHELL_51)
            cat_val = item.get("category", ActionCategory.DIAGNOSTIC)

            res = self.execute_command(command=cmd, shell=shell_val, category=cat_val)
            results.append(res)
            if not res.success:
                self.status = SubAgentStatus.FAILED
                return {
                    "agent_id": self.agent_id,
                    "name": self.name,
                    "goal": goal,
                    "success": False,
                    "error": res.error,
                    "steps_completed": len(results),
                }

        self.status = SubAgentStatus.COMPLETED
        self.board.post_message(
            sender_id=self.agent_id,
            message_type=MessageType.TASK_COMPLETED,
            content=f"Sub-agent '{self.name}' completed task: {goal}",
        )
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "goal": goal,
            "success": True,
            "steps_completed": len(results),
        }

    def get_telemetry(self) -> SubAgentTelemetry:
        """Returns the current operational telemetry of this sub-agent."""
        return SubAgentTelemetry(
            agent_id=self.agent_id,
            name=self.name,
            privilege=self.privilege,
            status=SubAgentStatus.ISOLATED if self.sandbox.circuit_breaker.is_isolated else self.status,
            current_goal=self.current_goal,
            steps_executed=self.sandbox.steps_executed,
            faults_count=self.sandbox.circuit_breaker.consecutive_failures,
            is_isolated=self.sandbox.circuit_breaker.is_isolated,
            created_at=self.created_at,
            last_heartbeat=self.last_heartbeat,
        )
