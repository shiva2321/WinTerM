"""Script Justification Gate: Enforces the architectural rule that scripts must ONLY be built
for tasks that strictly require scripted orchestration (multi-step flows, control flow, loops,
error recovery). Prevents script clutter, disk waste, and overhead for atomic single commands.
"""

from __future__ import annotations

import re
from typing import List, Optional
from pydantic import BaseModel, Field

from winterm.models.context import ShellType


class JustificationResult(BaseModel):
    """Evaluation outcome explaining whether a task qualifies for script synthesis."""
    is_justified: bool
    requires_script: bool = Field(default=False, description="Alias for is_justified")
    reason: str
    suggested_action: str  # "execute_direct" | "synthesize_script"
    complexity_score: int = Field(default=0, description="Heuristic score from 0 (trivial) to 10 (complex)")

    def model_post_init(self, __context: object) -> None:
        # Keep the documented alias consistent regardless of how the model is built.
        self.requires_script = self.is_justified


class ScriptNotJustifiedError(ValueError):
    """Raised when an attempt is made to generate a script for an operation that does not justify one."""
    pass


class ScriptJustificationGate:
    """Deterministic gate that evaluates whether a task truly requires a script.
    
    Guiding Principle:
    - Never write a script for atomic one-liners (e.g. `ipconfig`, `Get-Process`, `ls`, `docker ps`).
      These must be executed directly in the terminal to avoid disk I/O, cache clutter, and latency.
    - Only write scripts for tasks that strictly require programmatic orchestration:
      1. Multi-step workflows (>= 2 interdependent sequential commands).
      2. Conditional branching (if/else, switch, case).
      3. Iterative processing (loops: for, foreach, while).
      4. Error handling, compensation, or transactional rollback (try/catch, trap, || exit).
      5. Multi-line scripted routines.
    """

    # Regex patterns matching control-flow constructs *in statement position*.
    # The anchors matter: bare ``\bif\b`` matched file arguments such as
    # ``Get-Item if.txt`` or ``findstr TRY`` and wrongly justified a script.
    _CONTROL_FLOW_PATTERNS = [
        r"(?:^|[;{}(}\n]\s*)(?:if|elif|elseif|else)\b\s*[\(\{]",
        r"(?:^|[;{}(}\n]\s*)(?:for|foreach|while|until)\b\s*[\(\{]",
        r"(?:^|[;{}(}\n]\s*)(?:switch|case|trap|function)\b",
        r"(?:^|[;{}(}\n]\s*)(?:try|catch|finally)\b",
        r"\|\|\s*(?:exit|return|throw|echo|Write-Error)",
        r"&&\s*",
        r";\s*[\$\w]",
    ]
    _RE_CONTROL = re.compile("|".join(_CONTROL_FLOW_PATTERNS), re.IGNORECASE)

    @classmethod
    def evaluate(
        cls,
        goal: str,
        commands: List[str],
        shell: ShellType = ShellType.POWERSHELL_51,
        force_script: bool = False,
    ) -> JustificationResult:
        """Evaluates if the task strictly warrants creating a standalone script file.
        
        Args:
            goal: Natural language description of what the task accomplishes.
            commands: List of shell command strings intended for the task.
            shell: The target shell environment.
            force_script: Optional override flag if an agent or user explicitly forces script creation.
            
        Returns:
            JustificationResult with evaluation verdict, justification reason, and suggested action.
        """
        if force_script:
            return JustificationResult(
                is_justified=True,
                requires_script=True,
                reason="Explicit force_script override requested by agent or operator.",
                suggested_action="synthesize_script",
                complexity_score=5,
            )

        clean_cmds = [c.strip() for c in commands if c and c.strip()]

        if not clean_cmds:
            return JustificationResult(
                is_justified=False,
                requires_script=False,
                reason="No commands provided in task definition.",
                suggested_action="execute_direct",
                complexity_score=0,
            )

        # 1. Multiple command steps strictly warrant a script
        if len(clean_cmds) >= 2:
            return JustificationResult(
                is_justified=True,
                requires_script=True,
                reason=f"Task consists of {len(clean_cmds)} interdependent sequential commands requiring orchestrated script execution.",
                suggested_action="synthesize_script",
                complexity_score=min(10, 3 + len(clean_cmds)),
            )

        # 2. Single command analysis: Check for multi-line scripts or control flow
        single_cmd = clean_cmds[0]
        active_lines = [
            ln.strip() for ln in single_cmd.splitlines()
            if ln.strip() and not ln.strip().startswith("#") and not ln.strip().startswith("rem")
        ]

        if len(active_lines) >= 2:
            return JustificationResult(
                is_justified=True,
                requires_script=True,
                reason="Task command contains multiple lines of scripted logic.",
                suggested_action="synthesize_script",
                complexity_score=5,
            )

        # Check for control flow keywords
        if cls._RE_CONTROL.search(single_cmd):
            return JustificationResult(
                is_justified=True,
                requires_script=True,
                reason="Task command contains conditional branching, loop constructs, or structured error handling.",
                suggested_action="synthesize_script",
                complexity_score=6,
            )

        # 3. If none of the above match, it's an atomic single-line command!
        truncated_cmd = single_cmd if len(single_cmd) <= 60 else single_cmd[:57] + "..."
        return JustificationResult(
            is_justified=False,
            requires_script=False,
            reason=(
                f"Command '{truncated_cmd}' is an atomic single-step operation. "
                "Standard commands should be executed directly via execute_terminal_command or "
                "winterm_linux_execute rather than synthesized into script files, avoiding resource waste and catalog clutter."
            ),
            suggested_action="execute_direct",
            complexity_score=1,
        )
