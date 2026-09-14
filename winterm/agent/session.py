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
    active_plan: Optional[ExecutionPlan] = None
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
        if rollback and exec_res and exec_res.success:
            self.rollback_stack.append(rollback)

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
