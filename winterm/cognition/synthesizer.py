"""Command Synthesizer: Constructs hardened, defensive Windows terminal commands (The HOW of 5W)."""

import re
from typing import Optional
from winterm.models.intent import PlanStep
from winterm.models.context import ShellType, ElevationLevel
from winterm.knowledge.reliability_rules import ReliabilityRules
from winterm.knowledge.elevation_rules import ElevationRules


class CommandSynthesizer:
    """Synthesizes fully quoted, hardened, defensive Windows commands adhering to reliability rules."""

    @classmethod
    def synthesize_step_command(cls, step: PlanStep, defensive_wrap: bool = False) -> str:
        """Transforms a PlanStep command into a hardened executable string."""
        cmd = step.command or step.raw_intent
        target_shell = step.target_shell

        # 1. Inject non-interactive switches to prevent terminal hangs
        if target_shell in (ShellType.WSL_BASH, ShellType.BASH):
            from winterm.knowledge.linux_safety import LinuxSafetyGuard
            cmd = LinuxSafetyGuard.make_non_interactive(cmd)
        else:
            cmd = ReliabilityRules.make_non_interactive(cmd)

        # 2. Fix PowerShell condition syntax if present
        if target_shell in (ShellType.POWERSHELL_51, ShellType.POWERSHELL_7):
            cmd = ReliabilityRules.ensure_parentheses_in_ps_conditions(cmd)

            # Ensure ConvertTo-Json has -Depth 10
            if "ConvertTo-Json" in cmd and "-Depth" not in cmd:
                cmd = re.sub(r'\bConvertTo-Json\b', 'ConvertTo-Json -Depth 10', cmd)

            # Ensure call operator (&) if command starts with quotes
            cmd = ReliabilityRules.format_executable_invocation(cmd, target_shell)

            # Optionally wrap in defensive try/catch
            if defensive_wrap:
                cmd = ReliabilityRules.wrap_defensive_powershell(cmd)

        # 3. Apply UAC RunAs wrapper if elevation is strictly required
        if step.required_elevation == ElevationLevel.ADMIN:
            cmd = ElevationRules.wrap_with_runas(cmd, target_shell)

        # 4. Console ASCII safety
        cmd = ReliabilityRules.sanitize_for_windows_console(cmd)

        return cmd.strip()

    @classmethod
    def validate_command(
        cls,
        command_string: str,
        graph: Optional["WindowsKnowledgeGraph"] = None,
    ) -> "ParameterValidationResult":
        """Validates a command string against the Windows Knowledge Graph to prevent hallucinations."""
        from winterm.graph.engine import WindowsKnowledgeGraph
        from winterm.graph.schema import ParameterValidationResult

        kg = graph or WindowsKnowledgeGraph()
        tokens = command_string.strip().split()
        if not tokens:
            return ParameterValidationResult(
                command="",
                is_valid=False,
                unknown_parameters=[],
            )

        cmd_token = tokens[0]
        # Remove leading call operator & if present
        if cmd_token == "&" and len(tokens) > 1:
            cmd_token = tokens[1]
            tokens = tokens[1:]

        # Extract flags/switches (-Param, /Flag, etc.)
        param_tokens = [t for t in tokens[1:] if t.startswith("-") or t.startswith("/")]
        return kg.validate_command_parameters(cmd_token, param_tokens)

    @classmethod
    def synthesize_raw_command(
        cls,
        raw_cmd: str,
        shell: ShellType = ShellType.POWERSHELL_51,
        require_admin: bool = False,
        defensive_wrap: bool = False,
    ) -> str:
        """Hardens an arbitrary raw command string."""
        dummy_step = PlanStep(
            step_id="raw",
            title="Raw execution",
            category="custom",
            raw_intent=raw_cmd,
            command=raw_cmd,
            target_shell=shell,
            required_elevation=ElevationLevel.ADMIN if require_admin else ElevationLevel.STANDARD,
        )
        return cls.synthesize_step_command(dummy_step, defensive_wrap=defensive_wrap)
