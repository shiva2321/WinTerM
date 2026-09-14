"""Execution and verification outcome models."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from winterm.models.context import ShellType


class StreamOutput(BaseModel):
    """Raw and decoded process stream output."""
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    exit_code: int = Field(default=0, description="Process exit code")
    duration_ms: int = Field(default=0, description="Execution time in milliseconds")


class SelfHealingProposal(BaseModel):
    """Diagnosis and automated remedy for terminal command failures."""
    error_signature: str = Field(description="Matched error code or message pattern")
    root_cause: str = Field(description="Explanation of why the failure occurred")
    remedy_explanation: str = Field(description="How the proposed remedy fixes the issue")
    healing_command: str = Field(description="Concrete command to execute to heal or recover")
    healing_shell: ShellType = Field(default=ShellType.POWERSHELL_51, description="Shell for healing command")
    requires_elevation: bool = Field(default=False, description="Whether healing requires elevation")


class ExecutionResult(BaseModel):
    """Full outcome record of a command execution."""
    step_id: str = Field(description="Step ID")
    command: str = Field(description="Exact executed command string")
    shell: ShellType = Field(description="Shell used")
    success: bool = Field(description="Whether execution succeeded (typically exit code 0)")
    exit_code: int = Field(default=0, description="Exit code")
    stdout: str = Field(default="", description="Captured stdout")
    stderr: str = Field(default="", description="Captured stderr")
    duration_ms: int = Field(default=0, description="Duration in ms")
    timed_out: bool = Field(default=False, description="Whether the process timed out")
    healing_proposal: Optional[SelfHealingProposal] = Field(
        default=None,
        description="Suggested self-healing remedy if execution failed"
    )


class VerificationResult(BaseModel):
    """Post-execution state audit result."""
    step_id: str = Field(description="Step ID")
    verified: bool = Field(description="Whether expected post-conditions are fully met")
    actual_state_diff: Dict[str, Any] = Field(
        default_factory=dict,
        description="Observed state changes vs predicted"
    )
    unmatched_expectations: List[str] = Field(
        default_factory=list,
        description="Conditions that were expected but did not materialize"
    )
    details: str = Field(default="", description="Human-readable verification summary")
