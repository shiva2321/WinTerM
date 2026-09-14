"""WinTerM Multi-Agent Swarm Subsystem: Scoped sub-agent dispatching,
Message Board coordination, and layered fault-tolerant safety.
"""

from winterm.swarm.models import (
    AgentPrivilege,
    AgentScope,
    MessageType,
    SuggestionStatus,
    SubAgentStatus,
    SwarmMessage,
    SwarmSuggestion,
    SwarmFaultRecord,
    SubAgentTelemetry,
)
from winterm.swarm.board import SwarmMessageBoard
from winterm.swarm.sandbox import (
    SubAgentSandbox,
    CircuitBreaker,
    SafeExecutionResult,
    ScopeViolationError,
    StepLimitExceededError,
    CircuitBreakerTrippedError,
)
from winterm.swarm.subagent import SubAgentWorker
from winterm.swarm.coordinator import SwarmCoordinator

__all__ = [
    "AgentPrivilege",
    "AgentScope",
    "MessageType",
    "SuggestionStatus",
    "SubAgentStatus",
    "SwarmMessage",
    "SwarmSuggestion",
    "SwarmFaultRecord",
    "SubAgentTelemetry",
    "SwarmMessageBoard",
    "SubAgentSandbox",
    "CircuitBreaker",
    "SafeExecutionResult",
    "ScopeViolationError",
    "StepLimitExceededError",
    "CircuitBreakerTrippedError",
    "SubAgentWorker",
    "SwarmCoordinator",
]
