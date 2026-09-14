"""Unified domain models for WinTermAgent."""

from winterm.models.context import ShellType, ElevationLevel, SystemContext
from winterm.models.intent import ActionCategory, PlanStep, ExecutionPlan, StepStatus
from winterm.models.impact import (
    RiskLevel,
    StateDiff,
    FileDiff,
    RegDiff,
    ServiceDiff,
    ProcessDiff,
    NetworkDiff,
    RollbackAction,
    PredictedImpact,
)
from winterm.models.reasoning import (
    PreconditionType,
    PreconditionCheck,
    AlternativeRejected,
    WhyRationale,
    DecisionTrace,
)
from winterm.models.result import (
    StreamOutput,
    SelfHealingProposal,
    ExecutionResult,
    VerificationResult,
)

__all__ = [
    "ShellType",
    "ElevationLevel",
    "SystemContext",
    "ActionCategory",
    "PlanStep",
    "ExecutionPlan",
    "StepStatus",
    "RiskLevel",
    "StateDiff",
    "FileDiff",
    "RegDiff",
    "ServiceDiff",
    "ProcessDiff",
    "NetworkDiff",
    "RollbackAction",
    "PredictedImpact",
    "PreconditionType",
    "PreconditionCheck",
    "AlternativeRejected",
    "WhyRationale",
    "DecisionTrace",
    "StreamOutput",
    "SelfHealingProposal",
    "ExecutionResult",
    "VerificationResult",
]
