"""Reasoning and precondition models (The WHEN and WHY of 5W)."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from winterm.models.context import ShellType


class PreconditionType(str, Enum):
    """Types of system state checks evaluated before running a command."""
    PATH_EXISTS = "path_exists"
    PATH_NOT_EXISTS = "path_not_exists"
    PROCESS_RUNNING = "process_running"
    PROCESS_NOT_RUNNING = "process_not_running"
    PORT_FREE = "port_free"
    PORT_LISTENING = "port_listening"
    SERVICE_RUNNING = "service_running"
    SERVICE_STOPPED = "service_stopped"
    REGISTRY_KEY_EXISTS = "registry_key_exists"
    COMMAND_AVAILABLE = "command_available"
    IS_ADMIN = "is_admin"
    IDEMPOTENT_TARGET_STATE = "idempotent_target_state"


class PreconditionCheck(BaseModel):
    """An individual state guard evaluated prior to step execution (The WHEN)."""
    check_id: str = Field(description="Unique check identifier")
    check_type: PreconditionType = Field(description="Subsystem condition type")
    target: str = Field(description="Target path, process name, port number, etc.")
    expected_state: Any = Field(description="Expected boolean or status value")
    probe_command: str = Field(description="Defensive probe command to evaluate the condition")
    probe_shell: ShellType = Field(default=ShellType.POWERSHELL_51, description="Shell for probe")
    is_satisfied: Optional[bool] = Field(default=None, description="Result of probe check")
    skip_if_already_satisfied: bool = Field(
        default=False,
        description="If True and condition is satisfied, the step is skipped (idempotent)"
    )
    failure_message: str = Field(default="", description="Explanation if precondition fails")


class AlternativeRejected(BaseModel):
    """An alternative approach or command considered and rejected."""
    alternative: str = Field(description="Alternative command or tool, e.g. 'Get-WmiObject'")
    reason: str = Field(description="Why it was rejected, e.g. 'Deprecated in PS 6+, replaced by Get-CimInstance'")


class WhyRationale(BaseModel):
    """Transparent semantic justification of the chosen command (The WHY)."""
    intent_clarification: str = Field(description="Clear explanation of the agent's intent")
    command_justification: str = Field(description="Why this specific cmdlet / executable was selected")
    flags_justification: Dict[str, str] = Field(
        default_factory=dict,
        description="Explanation for each flag or switch added (e.g. -Force, -Confirm:$false)"
    )
    alternatives_rejected: List[AlternativeRejected] = Field(
        default_factory=list,
        description="Commands or tools considered but rejected"
    )
    windows_pitfall_mitigations: List[str] = Field(
        default_factory=list,
        description="Windows-specific quirks handled (e.g. path escaping, UTF-8 byte corruption)"
    )


class DecisionTrace(BaseModel):
    """Unified 5W epistemological envelope for a terminal action."""
    step_id: str = Field(description="Step ID")
    what: str = Field(description="What to do: Atomic intent and synthesized command")
    how: str = Field(description="How to do: Shell selection, escaping, quoting, parameters")
    when: List[PreconditionCheck] = Field(default_factory=list, description="When to do: Preconditions & state guards")
    why: WhyRationale = Field(description="Why to do: Semantic justification & alternatives")
    after: str = Field(description="What will happen after: Predicted state diff, side effects & rollback")
