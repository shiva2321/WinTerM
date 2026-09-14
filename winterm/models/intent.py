"""Intent and plan models for terminal task planning (The WHAT of 5W)."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from winterm.models.context import ShellType, ElevationLevel


class ActionCategory(str, Enum):
    """Categorization of Windows terminal operations."""
    FILESYSTEM = "filesystem"        # File/folder creation, copying, removal, permission
    PROCESS = "process"              # Start, stop, query, kill processes
    SERVICE = "service"              # Query, start, stop, configure Windows services
    NETWORK = "network"              # Port inspection, DNS, adapter, ping, firewall
    REGISTRY = "registry"            # Registry keys, values (HKLM, HKCU)
    ENVIRONMENT = "environment"      # System & user environment variables
    PACKAGE = "package"              # Winget, Chocolatey, Scoop package operations
    GIT = "git"                      # Source control operations
    DIAGNOSTIC = "diagnostic"        # Event viewer, systeminfo, resource monitoring
    SYSTEM = "system"                # Reboot, shutdown, power plan, task scheduler
    SECURITY = "security"            # Local users, groups, privileges, certificates, defender
    STORAGE = "storage"              # Disks, partitions, volumes, VHD, VSS, ACLs
    VIRTUALIZATION = "virtualization"# WSL, Hyper-V, containers, Windows sandbox
    CUSTOM = "custom"                # Arbitrary scripting / commands


class StepStatus(str, Enum):
    """Lifecycle status of an execution step."""
    PENDING = "pending"
    PRECONDITION_CHECK = "precondition_check"
    SKIPPED_IDEMPOTENT = "skipped_idempotent"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class PlanStep(BaseModel):
    """An individual atomic step in an execution plan."""
    step_id: str = Field(description="Unique step identifier, e.g. step-1")
    title: str = Field(description="Human-readable summary of the step")
    category: ActionCategory = Field(description="Subsystem category")
    raw_intent: str = Field(description="Semantic intent of this action")
    target_shell: ShellType = Field(default=ShellType.POWERSHELL_51, description="Recommended shell")
    command: str = Field(default="", description="Concrete synthesized command string")
    required_elevation: ElevationLevel = Field(
        default=ElevationLevel.STANDARD,
        description="Required elevation level"
    )
    timeout_seconds: int = Field(default=60, description="Step execution timeout")
    depends_on: List[str] = Field(
        default_factory=list,
        description="IDs of steps that must succeed before this step runs"
    )
    status: StepStatus = Field(default=StepStatus.PENDING, description="Current execution status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata / parameters")


class ExecutionPlan(BaseModel):
    """A staged Directed Acyclic Graph (DAG) plan of terminal actions."""
    plan_id: str = Field(description="Unique plan identifier")
    goal: str = Field(description="User's original goal / query")
    summary: str = Field(description="Overview of the execution strategy")
    steps: List[PlanStep] = Field(default_factory=list, description="Ordered execution steps")
    total_estimated_seconds: int = Field(default=0, description="Estimated total execution duration")
    requires_admin: bool = Field(default=False, description="Whether any step requires administrator privilege")
