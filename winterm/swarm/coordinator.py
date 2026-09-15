"""Swarm Coordinator: Orchestrates sub-agent dispatching, supervises the Message Board,
evaluates proactive suggestions, and commands the sub-agent fleet.
"""

from __future__ import annotations

import time
import threading
from typing import Dict, Any, List, Optional

from winterm.models.context import ShellType
from winterm.engine.executor import WindowsShellExecutor
from winterm.swarm.models import (
    AgentPrivilege,
    AgentScope,
    SubAgentStatus,
    MessageType,
    SuggestionStatus,
    SwarmMessage,
    SwarmSuggestion,
    SubAgentTelemetry,
)
from winterm.swarm.board import SwarmMessageBoard
from winterm.swarm.subagent import SubAgentWorker


class SwarmCoordinator:
    """Overseer that dispatches and commands autonomous sub-agents on Windows."""

    MAX_SUBAGENTS_CAP: int = 8

    def __init__(
        self,
        board: Optional[SwarmMessageBoard] = None,
        executor: Optional[WindowsShellExecutor] = None,
    ):
        self._lock = threading.RLock()
        self.board = board or SwarmMessageBoard()
        self.executor = executor or WindowsShellExecutor()
        self._subagents: Dict[str, SubAgentWorker] = {}

    # =========================================================================
    # 1. SUB-AGENT DISPATCHING & LIFECYCLE
    # =========================================================================

    def dispatch_subagent(
        self,
        name: str,
        goal: str = "",
        privilege: AgentPrivilege = AgentPrivilege.READ_ONLY_AUDIT,
        custom_scope: Optional[AgentScope] = None,
    ) -> SubAgentWorker:
        """Dispatches an autonomous sub-agent with a deterministic capability scope."""
        with self._lock:
            # Enforce max active sub-agents quota
            active_count = len([a for a in self._subagents.values() if a.status != SubAgentStatus.COMPLETED])
            if active_count >= self.MAX_SUBAGENTS_CAP:
                # Prune completed or idle agents to make room
                for aid, a in list(self._subagents.items()):
                    if a.status in (SubAgentStatus.COMPLETED, SubAgentStatus.FAILED, SubAgentStatus.ISOLATED):
                        del self._subagents[aid]

            worker = SubAgentWorker(
                name=name,
                privilege=privilege,
                scope=custom_scope or AgentScope.from_privilege(privilege),
                board=self.board,
                executor=self.executor,
            )
            worker.current_goal = goal
            self._subagents[worker.agent_id] = worker

            # Announce dispatch to Message Board
            self.board.post_message(
                sender_id="main_agent",
                sender_role="main_agent",
                recipient_id="broadcast",
                message_type=MessageType.DIRECTIVE,
                content=f"Dispatched sub-agent '{name}' ({worker.agent_id}) with privilege '{privilege.value}'. Goal: {goal}",
                payload={"agent_id": worker.agent_id, "privilege": privilege.value, "goal": goal},
            )

            return worker

    def dispatch_swarm(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Dispatches a fleet of sub-agents for multiple objectives."""
        dispatched = []
        for task in tasks:
            name = task.get("name", "Worker")
            goal = task.get("goal", "")
            priv_str = task.get("privilege", "read_only_audit")
            try:
                priv = AgentPrivilege(priv_str)
            except ValueError:
                priv = AgentPrivilege.READ_ONLY_AUDIT

            worker = self.dispatch_subagent(name=name, goal=goal, privilege=priv)
            dispatched.append(worker.get_telemetry().model_dump())

        return {
            "dispatched_count": len(dispatched),
            "agents": dispatched,
        }

    # =========================================================================
    # 2. COMMAND & BROADCAST
    # =========================================================================

    def broadcast_directive(
        self,
        directive: str,
        target_agent_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> SwarmMessage:
        """Broadcasts an instruction or command from the main agent to the swarm."""
        return self.board.post_message(
            sender_id="main_agent",
            sender_role="main_agent",
            recipient_id=target_agent_id or "broadcast",
            message_type=MessageType.DIRECTIVE,
            content=directive,
            payload=payload or {},
        )

    # =========================================================================
    # 3. SUGGESTIONS OVERSIGHT
    # =========================================================================

    def review_suggestions(self) -> List[SwarmSuggestion]:
        """Retrieves all pending proactive suggestions proposed by sub-agents."""
        return self.board.get_pending_suggestions()

    def approve_suggestion(
        self,
        suggestion_id: str,
        execute_now: bool = True,
        resolution_note: str = "Approved by main agent.",
    ) -> Dict[str, Any]:
        """Approves and optionally executes a sub-agent suggestion."""
        sug = self.board.get_suggestion(suggestion_id)
        if not sug:
            return {"approved": False, "error": f"Suggestion '{suggestion_id}' not found."}

        self.board.update_suggestion_status(
            suggestion_id=suggestion_id,
            status=SuggestionStatus.APPROVED,
            resolution_note=resolution_note,
        )

        exec_res = None
        if execute_now:
            # Main agent executes approved proposal with full capability
            exec_res = self.executor.execute(
                command=sug.proposed_action,
                shell=sug.target_shell,
            )
            self.board.update_suggestion_status(
                suggestion_id=suggestion_id,
                status=SuggestionStatus.EXECUTED,
                resolution_note=f"Executed with exit code {exec_res.exit_code}.",
            )
            # Post notice to board
            self.board.post_message(
                sender_id="main_agent",
                sender_role="main_agent",
                recipient_id="broadcast",
                message_type=MessageType.TASK_COMPLETED,
                content=f"Approved and executed suggestion '{sug.title}': {sug.proposed_action}",
                payload={"exit_code": exec_res.exit_code, "success": exec_res.success},
            )

        return {
            "approved": True,
            "suggestion_id": suggestion_id,
            "executed": execute_now,
            "result": exec_res.model_dump() if exec_res else None,
        }

    def reject_suggestion(self, suggestion_id: str, reason: str = "Rejected by main agent.") -> bool:
        """Rejects a proposed sub-agent suggestion with an explanatory rationale."""
        return self.board.update_suggestion_status(
            suggestion_id=suggestion_id,
            status=SuggestionStatus.REJECTED,
            resolution_note=reason,
        )

    def review_suggestion(
        self,
        suggestion_id: str,
        action: str = "approve",
        feedback: str = "",
        execute_now: bool = False,
    ) -> Dict[str, Any]:
        """Reviews a suggestion with 'approve' or 'reject' action, mirroring the MCP tool pattern."""
        if str(action).lower() == "approve":
            note = feedback or "Approved by main agent."
            return self.approve_suggestion(suggestion_id=suggestion_id, execute_now=execute_now, resolution_note=note)
        else:
            note = feedback or "Rejected by main agent."
            rejected = self.reject_suggestion(suggestion_id=suggestion_id, reason=note)
            return {"approved": False, "rejected": rejected, "suggestion_id": suggestion_id}

    # =========================================================================
    # 4. SWARM TELEMETRY & STATUS
    # =========================================================================

    def get_swarm_status(self) -> Dict[str, Any]:
        """Returns the full operational status, agent scopes, and fault telemetry of the swarm."""
        with self._lock:
            agents_telemetry = [a.get_telemetry().model_dump() for a in self._subagents.values()]
            pending_suggestions = [s.model_dump() for s in self.board.get_pending_suggestions()]
            all_suggestions = self.board.list_suggestions()
            fault_records = [f.model_dump() for f in self.board.get_fault_records()[-10:]]
            isolated_count = len([
                a for a in self._subagents.values()
                if a.status == SubAgentStatus.ISOLATED or a.sandbox.circuit_breaker.is_isolated
            ])

            return {
                "active_agents_count": len(self._subagents),
                "max_capacity": self.MAX_SUBAGENTS_CAP,
                "agents": agents_telemetry,
                "pending_suggestions_count": len(pending_suggestions),
                "total_suggestions_count": len(all_suggestions),
                "pending_suggestions": pending_suggestions,
                "recent_faults_count": len(fault_records),
                "isolated_agents_count": isolated_count,
                "recent_faults": fault_records,
            }

    def terminate_subagent(self, agent_id: str) -> bool:
        """Terminates and unregisters a sub-agent."""
        with self._lock:
            if agent_id in self._subagents:
                self._subagents[agent_id].status = SubAgentStatus.COMPLETED
                del self._subagents[agent_id]
                self.board.post_message(
                    sender_id="main_agent",
                    sender_role="main_agent",
                    recipient_id="broadcast",
                    message_type=MessageType.DIRECTIVE,
                    content=f"Sub-agent '{agent_id}' terminated by main agent.",
                )
                return True
            return False

    def shutdown_swarm(self) -> None:
        """Gracefully shuts down all sub-agents in the swarm."""
        with self._lock:
            for aid in list(self._subagents.keys()):
                self.terminate_subagent(aid)
            self._subagents.clear()
