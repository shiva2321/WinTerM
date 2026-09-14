"""WinTerM Playbook Subsystem: Task script generalization, recurrence detection, and execution."""

from winterm.playbooks.models import (
    PlaybookParameter,
    Playbook,
    CandidateTaskRecord,
    PlaybookMatchResult,
)
from winterm.playbooks.gate import (
    ScriptJustificationGate,
    JustificationResult,
    ScriptNotJustifiedError,
)
from winterm.playbooks.generalizer import ScriptGeneralizer
from winterm.playbooks.manager import PlaybookManager

__all__ = [
    "PlaybookParameter",
    "Playbook",
    "CandidateTaskRecord",
    "PlaybookMatchResult",
    "ScriptJustificationGate",
    "JustificationResult",
    "ScriptNotJustifiedError",
    "ScriptGeneralizer",
    "PlaybookManager",
]
