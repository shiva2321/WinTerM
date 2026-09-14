"""Knowledge Graph Schema: Ontological node types, edge relations, and graph models."""

from enum import Enum
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Ontological node types in the Windows Terminal Knowledge Graph."""
    COMMAND = "command"                  # Cmdlet or executable (e.g. Stop-Process, bcdedit)
    PARAMETER = "parameter"              # Flag, switch, or parameter (e.g. -Force, /enum)
    SUBSYSTEM = "subsystem"              # Windows subsystem layer (e.g. StorageNTFS, KernelBoot)
    SERVICE_RESOURCE = "service_resource"# Named Windows Service (e.g. RpcSs, Winmgmt, Spooler)
    STATE_ENTITY = "state_entity"        # Subsystem state primitive (e.g. TCP_Port, RegistryKey, ACL)
    ERROR_CODE = "error_code"            # Win32 error, HRESULT, or exception (e.g. 0x80070005)
    PRIVILEGE = "privilege"              # Security token privilege or role (e.g. Administrator)
    INTENT = "intent"                    # Natural language task intent (from command-dataset)
    SAFETY_RULE = "safety_rule"          # Safety tier and guard (from terminal-command-execution-sft)


class RelationType(str, Enum):
    """Directional semantic relationships in the Windows Terminal Knowledge Graph."""
    HAS_PARAMETER = "has_parameter"           # (Command) -> HAS_PARAMETER -> (Parameter)
    REQUIRES_PRIVILEGE = "requires_privilege" # (Command) -> REQUIRES_PRIVILEGE -> (Privilege)
    MUTATES_STATE = "mutates_state"           # (Command) -> MUTATES_STATE -> (StateEntity)
    READS_STATE = "reads_state"               # (Command) -> READS_STATE -> (StateEntity)
    DEPENDS_ON = "depends_on"                 # (ServiceA) -> DEPENDS_ON -> (ServiceB)
    DEPENDENCY_OF = "dependency_of"           # Inverse: (ServiceB) -> DEPENDENCY_OF -> (ServiceA)
    REMEDIATES_ERROR = "remediates_error"     # (Command) -> REMEDIATES_ERROR -> (ErrorCode)
    CAUSES_ERROR = "causes_error"             # (State / MissingPrivilege) -> CAUSES_ERROR -> (ErrorCode)
    ALTERNATIVE_TO = "alternative_to"         # (CommandA) -> ALTERNATIVE_TO -> (CommandB)
    INCOMPATIBLE_WITH = "incompatible_with"   # (Command/Flag) -> INCOMPATIBLE_WITH -> (Shell/OS)
    PART_OF_SUBSYSTEM = "part_of_subsystem"   # (Command) -> PART_OF_SUBSYSTEM -> (Subsystem)
    OUTPUTS_PROPERTY = "outputs_property"     # (Command) -> OUTPUTS_PROPERTY -> (StateEntity)
    PIPED_INTO = "piped_into"                 # (CommandA) -> PIPED_INTO -> (CommandB)
    MAPS_TO_COMMAND = "maps_to_command"       # (Intent) -> MAPS_TO_COMMAND -> (Command)
    HAS_SAFETY_RULE = "has_safety_rule"       # (Command) -> HAS_SAFETY_RULE -> (SafetyRule)



class GraphNode(BaseModel):
    """A typed entity node in the Windows Terminal Knowledge Graph."""
    node_id: str = Field(description="Unique node identifier (e.g. 'cmdlet:Get-Service')")
    name: str = Field(description="Human readable name or symbol")
    node_type: NodeType = Field(description="Categorical entity type")
    description: str = Field(default="", description="Detailed factual documentation")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Custom subsystem attributes")


class GraphEdge(BaseModel):
    """A directed semantic relationship between two graph nodes."""
    source_id: str = Field(description="Origin node ID")
    target_id: str = Field(description="Destination node ID")
    relation: RelationType = Field(description="Semantic relationship type")
    weight: float = Field(default=1.0, description="Edge weight for path traversal")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Relationship metadata")


class BlastRadiusReport(BaseModel):
    """Assessment of direct and cascading blast radius for a command or resource modification."""
    root_node_id: str = Field(description="Target entity being stopped, altered, or deleted")
    direct_dependents: List[str] = Field(default_factory=list, description="Immediate downstream entities affected")
    cascading_dependents: List[str] = Field(default_factory=list, description="Multi-hop transitive dependents affected")
    mutated_states: List[str] = Field(default_factory=list, description="System state entities modified")
    risk_score: str = Field(default="LOW", description="Risk assessment: SAFE, LOW, MEDIUM, HIGH, CRITICAL")
    blast_radius_depth: int = Field(default=0, description="Max depth of cascading impact")
    impact_summary: str = Field(default="", description="Executive impact explanation")


class RemediationPath(BaseModel):
    """Graph-resolved multi-step remediation path for an error code or system failure."""
    error_code: str = Field(description="Error signature or HRESULT")
    root_cause: str = Field(description="Graph-indexed root cause explanation")
    remediation_steps: List[Dict[str, Any]] = Field(default_factory=list, description="Ordered recovery actions")
    required_privileges: List[str] = Field(default_factory=list, description="Privileges needed for recovery")


class ParameterValidationResult(BaseModel):
    """Result of validating a command and its parameters against the Knowledge Graph."""
    command: str = Field(description="Command or cmdlet name")
    is_valid: bool = Field(description="Whether command and all parameters exist in graph")
    valid_parameters: List[str] = Field(default_factory=list, description="Parameters confirmed legitimate")
    unknown_parameters: List[str] = Field(default_factory=list, description="Hallucinated or invalid parameters")
    suggestions: Dict[str, str] = Field(default_factory=dict, description="Correction suggestions for typos")
