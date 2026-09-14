"""Data models for Reusable Task Playbooks and Script Generalization."""

from __future__ import annotations

import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from winterm.models.context import ShellType


class PlaybookParameter(BaseModel):
    """Defines a typed, configurable parameter for a generalized playbook."""
    name: str
    param_type: str = "string"          # int | string | bool | path
    default_value: Any = None
    description: str = ""
    required: bool = False


class Playbook(BaseModel):
    """A parameterized, reusable operational routine compiled from recurring tasks."""
    playbook_id: str
    name: str
    description: str
    pattern_signature: str
    target_shell: ShellType = ShellType.POWERSHELL_51
    parameters: List[PlaybookParameter] = Field(default_factory=list)
    script_body: str
    sample_goals: List[str] = Field(default_factory=list)
    execution_count: int = 0
    success_count: int = 0
    last_executed_at: float = Field(default_factory=time.time)
    created_at: float = Field(default_factory=time.time)
    is_promoted: bool = True
    safety_tier: str = "safe"           # safe | privileged | destructive


class CandidateTaskRecord(BaseModel):
    """Ephemeral record tracking recurring task attempts before promoting to persistent playbook."""
    signature: str
    raw_goal: str
    commands: List[str] = Field(default_factory=list)
    shell: ShellType = ShellType.POWERSHELL_51
    hit_count: int = 1
    first_seen: float = Field(default_factory=time.time)
    last_seen: float = Field(default_factory=time.time)


class PlaybookMatchResult(BaseModel):
    """Result of matching a natural language goal against stored playbooks."""
    matched: bool
    playbook: Optional[Playbook] = None
    confidence: float = 0.0
    extracted_params: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
