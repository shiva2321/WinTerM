"""WinTermAgent - AI Agent Toolkit for Windows Terminal.

Empowers AI agents to master Windows Terminal handling through the 5W Cognitive Model:
- What to do: Intent decomposition & task planning
- How to do: Windows Shell reliability & syntax synthesis (PS 5.1/7+, CMD, Win32)
- When to do: Precondition checks, state guards & idempotency
- Why to do: Semantic justification & alternative rejection
- What happens after: State diff prediction, rollback generation, verification & self-healing
"""

__version__ = "0.4.0"
__author__ = "WinTerm AI Team"

from winterm.agent.winterm_agent import WinTermAgent
from winterm.engine.executor import WindowsShellExecutor
from winterm.cognition.planner import TerminalPlanner
from winterm.cognition.synthesizer import CommandSynthesizer
from winterm.cognition.predictor import ImpactPredictor
from winterm.cognition.scheduler import PreconditionScheduler
from winterm.cognition.reasoner import SemanticReasoner
from winterm.cognition.verifier import StateVerifier
from winterm.cognition.healer import ErrorHealer

__all__ = [
    "WinTermAgent",
    "WindowsShellExecutor",
    "TerminalPlanner",
    "CommandSynthesizer",
    "ImpactPredictor",
    "PreconditionScheduler",
    "SemanticReasoner",
    "StateVerifier",
    "ErrorHealer",
]
