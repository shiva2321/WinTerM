"""Impact prediction and state diff models (The WHAT HAPPENS AFTER of 5W)."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from winterm.models.context import ShellType, ElevationLevel


class RiskLevel(str, Enum):
    """Safety and risk assessment tiers for terminal commands."""
    READ_ONLY = "read_only"              # Queries, listing, diagnostics (no state mutation)
    SAFE = "safe"                        # Harmless mutations (creating a temp folder, reading log)
    LOW = "low"                          # Minor non-destructive mutations (installing a local tool)
    MEDIUM = "medium"                    # Moderate impact (stopping a service, modifying user env)
    HIGH_DESTRUCTIVE = "high_destructive"# High risk (recursively deleting files, modifying HKLM, killall)
    ELEVATION_REQUIRED = "elevation_req" # Requires UAC / Administrative privileges


class FileDiff(BaseModel):
    """File and directory level state mutations."""
    created_paths: List[str] = Field(default_factory=list, description="Paths expected to be created")
    modified_paths: List[str] = Field(default_factory=list, description="Paths expected to be modified")
    deleted_paths: List[str] = Field(default_factory=list, description="Paths expected to be deleted")


class RegDiff(BaseModel):
    """Windows Registry mutations."""
    keys_added: List[str] = Field(default_factory=list, description="Registry keys added")
    keys_deleted: List[str] = Field(default_factory=list, description="Registry keys deleted")
    values_modified: Dict[str, Any] = Field(default_factory=dict, description="Registry values changed")


class ServiceDiff(BaseModel):
    """Windows Service state mutations."""
    services_started: List[str] = Field(default_factory=list, description="Services started")
    services_stopped: List[str] = Field(default_factory=list, description="Services stopped")
    services_modified: List[str] = Field(default_factory=list, description="Service startup types modified")


class ProcessDiff(BaseModel):
    """Process lifecycle mutations."""
    spawned_processes: List[str] = Field(default_factory=list, description="Processes or binaries launched")
    terminated_processes: List[str] = Field(default_factory=list, description="Processes targeted for termination")


class NetworkDiff(BaseModel):
    """Network connection & port mutations."""
    ports_opened: List[int] = Field(default_factory=list, description="TCP/UDP ports expected to listen")
    firewall_rules_altered: List[str] = Field(default_factory=list, description="Firewall rules added or altered")


class StateDiff(BaseModel):
    """Comprehensive projected state delta across Windows subsystems."""
    filesystem: FileDiff = Field(default_factory=FileDiff)
    registry: RegDiff = Field(default_factory=RegDiff)
    services: ServiceDiff = Field(default_factory=ServiceDiff)
    processes: ProcessDiff = Field(default_factory=ProcessDiff)
    network: NetworkDiff = Field(default_factory=NetworkDiff)
    environment_mutations: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables created or updated"
    )


class RollbackAction(BaseModel):
    """A compensatory action to revert or undo command effects."""
    step_id: str = Field(description="Step ID being rolled back")
    description: str = Field(description="Summary of the rollback operation")
    command: str = Field(description="Synthesized rollback command")
    shell: ShellType = Field(default=ShellType.POWERSHELL_51, description="Shell to run rollback in")
    required_elevation: ElevationLevel = Field(
        default=ElevationLevel.STANDARD,
        description="Elevation required for rollback"
    )


class PredictedImpact(BaseModel):
    """Full impact assessment for a planned command or entire plan."""
    step_id: str = Field(description="Associated step identifier")
    risk_level: RiskLevel = Field(description="Assessed risk level")
    state_diff: StateDiff = Field(default_factory=StateDiff, description="Projected state changes")
    side_effects: List[str] = Field(default_factory=list, description="Potential unintentional side effects")
    warnings: List[str] = Field(default_factory=list, description="Critical warnings or potential pitfalls")
    is_reversible: bool = Field(default=True, description="Whether this command can be cleanly undone")
    rollback: Optional[RollbackAction] = Field(default=None, description="Compensatory rollback recipe")
    blast_radius: Optional[Dict[str, Any]] = Field(default=None, description="Graph-computed cascading blast radius")
