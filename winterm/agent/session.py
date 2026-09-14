"""Terminal Agent Session: Tracks multi-turn history, state diff timeline, and undo log."""

import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from winterm.models.intent import ExecutionPlan, PlanStep
from winterm.models.impact import RollbackAction, StateDiff
from winterm.models.result import ExecutionResult, VerificationResult
from winterm.models.reasoning import DecisionTrace


class SessionStepRecord(BaseModel):
    """Historical ledger entry for a single executed step."""
    step: PlanStep
    decision_trace: Optional[DecisionTrace] = None
    execution_result: Optional[ExecutionResult] = None
    verification_result: Optional[VerificationResult] = None
    rollback_action: Optional[RollbackAction] = None
    timestamp: float = Field(default_factory=time.time)


class AgentSession(BaseModel):
    """Maintains conversation context, executed history, and rollback stack for WinTermAgent."""
    session_id: str
    agent_framework: str = Field(default="generic", description="Agent runtime identifier (e.g. claude-code, opencode, gemini, deepseek)")
    active_plan: Optional[ExecutionPlan] = None
    max_history_steps: int = Field(default=500, description="Upper bound on historical ledger entries to prevent memory leaks in long-running sessions")
    history: List[SessionStepRecord] = Field(default_factory=list)
    rollback_stack: List[RollbackAction] = Field(default_factory=list)

    def record_step(
        self,
        step: PlanStep,
        trace: Optional[DecisionTrace] = None,
        exec_res: Optional[ExecutionResult] = None,
        verif_res: Optional[VerificationResult] = None,
        rollback: Optional[RollbackAction] = None,
    ) -> None:
        """Records an executed step in session history and pushes rollback action if available."""
        record = SessionStepRecord(
            step=step,
            decision_trace=trace,
            execution_result=exec_res,
            verification_result=verif_res,
            rollback_action=rollback,
        )
        self.history.append(record)
        # Prevent memory leaks in long-running autonomous sessions
        if len(self.history) > self.max_history_steps:
            self.history = self.history[-self.max_history_steps:]

        if rollback and exec_res and exec_res.success:
            self.rollback_stack.append(rollback)
            if len(self.rollback_stack) > 100:
                self.rollback_stack = self.rollback_stack[-100:]

    def pop_rollback(self) -> Optional[RollbackAction]:
        """Pops the most recent rollback action from the undo stack."""
        if self.rollback_stack:
            return self.rollback_stack.pop()
        return None

    def export_ledger(self, filepath: Optional[str] = None) -> str:
        """Exports the entire session execution history, 5W traces, and results as formatted JSON."""
        json_data = self.model_dump_json(indent=2)
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_data)
        return json_data


class ResourceLock(BaseModel):
    """Represents a cooperative lock held by an agent on a shared resource."""
    resource_id: str
    owner_session_id: str
    owner_framework: str
    acquired_at: float = Field(default_factory=time.time)
    expires_at: float


class AgentSessionCoordinator:
    """Coordinates simultaneous agent sessions (Claude Code, OpenCode, DeepSeek, Gemini) and prevents collisions."""

    _sessions: Dict[str, AgentSession] = {}
    _locks: Dict[str, ResourceLock] = {}

    @classmethod
    def register_session(cls, session: AgentSession) -> None:
        """Registers an active agent session in the coordinator registry."""
        cls._sessions[session.session_id] = session

    @classmethod
    def get_active_sessions(cls) -> List[Dict[str, Any]]:
        """Returns metadata of all currently registered agent sessions."""
        return [
            {
                "session_id": s.session_id,
                "agent_framework": s.agent_framework,
                "steps_executed": len(s.history),
                "has_active_plan": s.active_plan is not None,
            }
            for s in cls._sessions.values()
        ]

    @classmethod
    def acquire_resource_lock(
        cls,
        resource_id: str,
        session_id: str,
        framework: str = "generic",
        ttl_seconds: float = 60.0,
    ) -> bool:
        """Acquires a cooperative lock on a shared resource (window, port, file) for an agent session."""
        cls.clean_expired_locks()
        now = time.time()

        if resource_id in cls._locks:
            lock = cls._locks[resource_id]
            # Re-entrant for the same session
            if lock.owner_session_id == session_id:
                lock.expires_at = now + ttl_seconds
                return True
            return False

        cls._locks[resource_id] = ResourceLock(
            resource_id=resource_id,
            owner_session_id=session_id,
            owner_framework=framework,
            acquired_at=now,
            expires_at=now + ttl_seconds,
        )
        return True

    @classmethod
    def release_resource_lock(cls, resource_id: str, session_id: str) -> bool:
        """Releases a cooperative resource lock held by the specified session."""
        if resource_id in cls._locks:
            if cls._locks[resource_id].owner_session_id == session_id:
                del cls._locks[resource_id]
                return True
        return False

    @classmethod
    def is_resource_locked(cls, resource_id: str) -> Optional[ResourceLock]:
        """Checks if a resource is currently locked by another active agent."""
        cls.clean_expired_locks()
        return cls._locks.get(resource_id)

    @classmethod
    def clean_expired_locks(cls) -> int:
        """Removes expired locks and returns the count of purged locks."""
        now = time.time()
        expired = [k for k, v in cls._locks.items() if v.expires_at < now]
        for k in expired:
            del cls._locks[k]
        return len(expired)
