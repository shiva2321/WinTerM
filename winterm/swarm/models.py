"""Data models for the WinTerM Multi-Agent Swarm system:
Capability scopes, message board communication, proactive suggestions, and fault telemetry.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field

from winterm.models.context import ShellType
from winterm.models.intent import ActionCategory


class AgentPrivilege(str, Enum):
    """Hierarchical privilege tiers for sub-agents."""
    READ_ONLY_AUDIT = "read_only_audit"       # System queries, diagnostics, log inspection, non-modifying
    UI_OPERATOR = "ui_operator"               # Window management, UI automation, mouse/keyboard, screenshots
    TERMINAL_EXECUTOR = "terminal_executor"   # Hardened shell/terminal commands within standard safety bounds
    NETWORK_INSPECTOR = "network_inspector"   # Port audits, network connections, ping, curl, firewall queries
    FULL_SUPERVISOR = "full_supervisor"       # Unrestricted execution within WinTerM safety gates


class MessageType(str, Enum):
    """Categorization of messages posted to the Swarm Message Board."""
    TASK_ASSIGNMENT = "task_assignment"
    PROGRESS_UPDATE = "progress_update"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    SUGGESTION = "suggestion"
    ALERT = "alert"
    DIRECTIVE = "directive"


class SuggestionStatus(str, Enum):
    """Lifecycle status of a proactive suggestion proposed by a sub-agent."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class SubAgentStatus(str, Enum):
    """Operational lifecycle state of a sub-agent."""
    INITIALIZING = "initializing"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ISOLATED = "isolated"


class AgentScope(BaseModel):
    """Defines deterministic boundaries and capability limits for a sub-agent."""
    privilege: AgentPrivilege = AgentPrivilege.READ_ONLY_AUDIT
    allowed_action_categories: List[ActionCategory] = Field(
        default_factory=lambda: [ActionCategory.DIAGNOSTIC, ActionCategory.PROCESS, ActionCategory.NETWORK]
    )
    allowed_shells: List[ShellType] = Field(
        default_factory=lambda: [ShellType.POWERSHELL_51, ShellType.CMD]
    )
    allow_desktop_interaction: bool = False
    allow_file_write: bool = False
    allow_destructive: bool = False
    max_steps: int = 20
    timeout_seconds: float = 30.0
    rate_limit_per_minute: int = 60

    @classmethod
    def from_privilege(cls, privilege: AgentPrivilege) -> "AgentScope":
        """Factory creating standard scope profiles tailored to each privilege tier."""
        if privilege == AgentPrivilege.READ_ONLY_AUDIT:
            return cls(
                privilege=privilege,
                allowed_action_categories=[ActionCategory.DIAGNOSTIC, ActionCategory.PROCESS, ActionCategory.NETWORK, ActionCategory.SERVICE],
                allowed_shells=[ShellType.POWERSHELL_51, ShellType.CMD, ShellType.WSL_BASH],
                allow_desktop_interaction=False,
                allow_file_write=False,
                allow_destructive=False,
                max_steps=20,
                timeout_seconds=30.0,
            )
        elif privilege == AgentPrivilege.UI_OPERATOR:
            return cls(
                privilege=privilege,
                allowed_action_categories=[
                    ActionCategory.DIAGNOSTIC,
                    ActionCategory.PROCESS,
                    ActionCategory.SYSTEM,
                    ActionCategory.CUSTOM,
                ],
                allowed_shells=[ShellType.POWERSHELL_51],
                allow_desktop_interaction=True,
                allow_file_write=False,
                allow_destructive=False,
                max_steps=30,
                timeout_seconds=45.0,
            )
        elif privilege == AgentPrivilege.NETWORK_INSPECTOR:
            return cls(
                privilege=privilege,
                allowed_action_categories=[
                    ActionCategory.DIAGNOSTIC,
                    ActionCategory.NETWORK,
                ],
                allowed_shells=[ShellType.POWERSHELL_51, ShellType.CMD, ShellType.WSL_BASH],
                allow_desktop_interaction=False,
                allow_file_write=False,
                allow_destructive=False,
                max_steps=25,
                timeout_seconds=30.0,
            )
        elif privilege == AgentPrivilege.TERMINAL_EXECUTOR:
            return cls(
                privilege=privilege,
                allowed_action_categories=[
                    ActionCategory.DIAGNOSTIC,
                    ActionCategory.PROCESS,
                    ActionCategory.SERVICE,
                    ActionCategory.FILESYSTEM,
                    ActionCategory.PACKAGE,
                    ActionCategory.NETWORK,
                    ActionCategory.GIT,
                    ActionCategory.ENVIRONMENT,
                ],
                allowed_shells=[ShellType.POWERSHELL_51, ShellType.POWERSHELL_7, ShellType.CMD, ShellType.WSL_BASH],
                allow_desktop_interaction=False,
                allow_file_write=True,
                allow_destructive=False,
                max_steps=40,
                timeout_seconds=60.0,
            )
        else:  # FULL_SUPERVISOR
            return cls(
                privilege=privilege,
                allowed_action_categories=list(ActionCategory),
                allowed_shells=list(ShellType),
                allow_desktop_interaction=True,
                allow_file_write=True,
                allow_destructive=True,
                max_steps=100,
                timeout_seconds=120.0,
            )


class SwarmMessage(BaseModel):
    """A communication record posted to the shared Swarm Message Board."""
    message_id: str = Field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:8]}")
    sender_id: str
    sender_role: str = "sub_agent"       # "main_agent" | "sub_agent" | "system"
    recipient_id: str = "broadcast"      # "broadcast" or target agent_id
    message_type: MessageType
    content: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class SwarmSuggestion(BaseModel):
    """Proactive recommendation formulated by a sub-agent for main agent oversight."""
    suggestion_id: str = Field(default_factory=lambda: f"sug-{uuid.uuid4().hex[:8]}")
    proposing_agent_id: str
    proposing_agent_name: str
    title: str
    reasoning: str
    proposed_action: str
    target_shell: ShellType = ShellType.POWERSHELL_51
    required_privilege: AgentPrivilege = AgentPrivilege.TERMINAL_EXECUTOR
    status: SuggestionStatus = SuggestionStatus.PENDING
    resolution_note: str = ""
    created_at: float = Field(default_factory=time.time)
    resolved_at: Optional[float] = None


class SwarmFaultRecord(BaseModel):
    """Diagnostic telemetry captured when a sub-agent encounters an exception or security breach."""
    fault_id: str = Field(default_factory=lambda: f"flt-{uuid.uuid4().hex[:8]}")
    agent_id: str
    agent_name: str
    timestamp: float = Field(default_factory=time.time)
    exception_type: str
    error_message: str
    attempted_action: str
    was_isolated: bool = False
    context: Dict[str, Any] = Field(default_factory=dict)


class SubAgentTelemetry(BaseModel):
    """Live operational telemetry of a sub-agent in the swarm."""
    agent_id: str
    name: str
    privilege: AgentPrivilege
    status: SubAgentStatus = SubAgentStatus.IDLE
    current_goal: str = ""
    steps_executed: int = 0
    faults_count: int = 0
    is_isolated: bool = False
    created_at: float = Field(default_factory=time.time)
    last_heartbeat: float = Field(default_factory=time.time)
