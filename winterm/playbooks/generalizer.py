"""Script Generalization Engine: Extracts signatures, parameterizes commands, and synthesizes scripts."""

from __future__ import annotations

import re
from typing import Dict, Any, List, Tuple, Optional
from winterm.models.context import ShellType
from winterm.playbooks.models import PlaybookParameter, Playbook, PlaybookMatchResult


# Regular expressions for identifying common parameterized entities
_RE_PORT = re.compile(r"\b(port\s+)?([1-9]\d{1,4})\b", re.IGNORECASE)
_RE_WIN_PATH = re.compile(r"([A-Za-z]:\\[^ \t\r\n'\",;]+)", re.IGNORECASE)
_RE_POSIX_PATH = re.compile(r"(/[\w\.\-]+(?:/[\w\.\-]+)+)", re.IGNORECASE)
_RE_PID = re.compile(r"\b(?:pid|process\s*id)\s*[:=]?\s*(\d+)\b", re.IGNORECASE)
_RE_SERVICE = re.compile(r"\b(?:service|daemon)\s+['\"]?([a-zA-Z0-9_\-]+)['\"]?", re.IGNORECASE)
_RE_APP = re.compile(r"\b(?:process|app|application|program)\s+['\"]?([a-zA-Z0-9_\-]+)['\"]?", re.IGNORECASE)


class ScriptGeneralizer:
    """Analyzes task commands and natural goals to abstract literals into typed parameters."""

    @staticmethod
    def _substitute_literal(command: str, value: Any, replacement: str) -> str:
        """Replaces a literal parameter value with ``replacement`` without corrupting
        longer tokens.

        A naive global ``re.sub(str(value), ...)`` turns ``-Id 1234`` into
        ``-Id $Pid234`` when the default is ``1`` and ``findstr 8080`` into
        ``findstr $Port80`` when the default is ``80``. Boundary-aware anchors
        prevent both.
        """
        val = str(value)
        if val == "":
            return command
        escaped = re.escape(val)
        if re.fullmatch(r"-?\d+", val):
            pattern = r"(?<![\w.])" + escaped + r"(?![\w.])"
        elif re.fullmatch(r"[A-Za-z0-9_\-]+", val):
            pattern = r"(?<![\w\-])" + escaped + r"(?![\w\-])"
        else:
            # Paths / complex values: don't match inside a longer path or identifier.
            pattern = r"(?<![\w\\/.\-])" + escaped + r"(?![\w\\/.\-])"
        return re.sub(pattern, replacement, command)

    @classmethod
    def extract_signature_and_params(cls, goal: str, commands: List[str]) -> Tuple[str, List[PlaybookParameter]]:
        """Extracts a normalized pattern signature and identified parameters from a goal and commands."""
        normalized_goal = goal.strip().lower()
        params: List[PlaybookParameter] = []
        param_names: set = set()

        combined_text = f"{goal} " + " ".join(commands)

        # 1. Port detection
        port_match = _RE_PORT.search(combined_text)
        if port_match:
            port_val = int(port_match.group(2))
            if 1 <= port_val <= 65535:
                normalized_goal = _RE_PORT.sub("{port}", normalized_goal)
                if "port" not in param_names:
                    params.append(
                        PlaybookParameter(
                            name="port",
                            param_type="int",
                            default_value=port_val,
                            description="Network TCP/UDP port number",
                            required=True,
                        )
                    )
                    param_names.add("port")

        # 2. Windows Path detection
        win_path_match = _RE_WIN_PATH.search(combined_text)
        if win_path_match:
            path_val = win_path_match.group(1).strip()
            normalized_goal = _RE_WIN_PATH.sub("{path}", normalized_goal)
            if "path" not in param_names:
                params.append(
                    PlaybookParameter(
                        name="path",
                        param_type="path",
                        default_value=path_val,
                        description="Target Windows filesystem path",
                        required=True,
                    )
                )
                param_names.add("path")

        # 3. POSIX Path detection
        posix_path_match = _RE_POSIX_PATH.search(combined_text)
        if posix_path_match and not win_path_match:
            path_val = posix_path_match.group(1).strip()
            normalized_goal = _RE_POSIX_PATH.sub("{path}", normalized_goal)
            if "path" not in param_names:
                params.append(
                    PlaybookParameter(
                        name="path",
                        param_type="path",
                        default_value=path_val,
                        description="Target POSIX filesystem path",
                        required=True,
                    )
                )
                param_names.add("path")

        # 4. Service name detection
        svc_match = _RE_SERVICE.search(combined_text)
        if svc_match:
            svc_name = svc_match.group(1).strip()
            normalized_goal = _RE_SERVICE.sub("service {service_name}", normalized_goal)
            if "service_name" not in param_names:
                params.append(
                    PlaybookParameter(
                        name="service_name",
                        param_type="string",
                        default_value=svc_name,
                        description="Name of the service",
                        required=True,
                    )
                )
                param_names.add("service_name")

        # 5. PID detection
        pid_match = _RE_PID.search(combined_text)
        if pid_match:
            pid_val = int(pid_match.group(1))
            normalized_goal = _RE_PID.sub("pid {pid}", normalized_goal)
            if "pid" not in param_names:
                params.append(
                    PlaybookParameter(
                        name="pid",
                        param_type="int",
                        default_value=pid_val,
                        description="Target Process Identifier (PID)",
                        required=True,
                    )
                )
                param_names.add("pid")

        # 6. Normalize signature string
        signature = re.sub(r"[^a-zA-Z0-9_{}]", "_", normalized_goal)
        signature = re.sub(r"_+", "_", signature).strip("_")

        return signature, params

    @classmethod
    def synthesize_playbook_script(
        cls,
        commands: List[str],
        parameters: Optional[List[PlaybookParameter]] = None,
        shell: ShellType = ShellType.POWERSHELL_51,
        params: Optional[List[PlaybookParameter]] = None,
    ) -> str:
        """Generates a standalone, defensive parameterized script."""
        resolved_params = parameters if parameters is not None else (params or [])
        if shell in (ShellType.POWERSHELL_51, ShellType.POWERSHELL_7):
            return cls._synthesize_powershell_script(commands, resolved_params)
        elif shell in (ShellType.WSL_BASH, ShellType.BASH):
            return cls._synthesize_bash_script(commands, resolved_params)
        else:
            return cls._synthesize_cmd_script(commands, resolved_params)

    @classmethod
    def _synthesize_powershell_script(
        cls,
        commands: List[str],
        parameters: List[PlaybookParameter],
    ) -> str:
        """Synthesizes a robust PowerShell (.ps1) script with CmdletBinding and param block."""
        lines = [
            "# Auto-generalized Playbook synthesized by WinTerM",
            "[CmdletBinding()]",
            "param (",
        ]

        param_lines = []
        for p in parameters:
            type_tag = "[int]" if p.param_type == "int" else "[string]"
            ps_param_name = p.name.capitalize()
            if p.default_value is not None:
                if isinstance(p.default_value, str):
                    default_repr = f"'{p.default_value}'"
                else:
                    default_repr = str(p.default_value)
                param_lines.append(f"    {type_tag}${ps_param_name} = {default_repr}")
            else:
                param_lines.append(f"    {type_tag}${ps_param_name}")

        lines.append(",\n".join(param_lines))
        lines.append(")")
        lines.append("")
        lines.append("$ErrorActionPreference = 'Stop'")
        lines.append("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8")
        lines.append("")

        for cmd in commands:
            generalized_cmd = cmd
            for p in parameters:
                if p.default_value is not None:
                    # Replace literal default with variable
                    generalized_cmd = cls._substitute_literal(
                        generalized_cmd, p.default_value, f"${p.name.capitalize()}"
                    )
            lines.append(generalized_cmd)

        return "\n".join(lines)

    @classmethod
    def _synthesize_bash_script(
        cls,
        commands: List[str],
        parameters: List[PlaybookParameter],
    ) -> str:
        """Synthesizes a robust POSIX Bash (.sh) script with non-interactive flags."""
        lines = [
            "#!/usr/bin/env bash",
            "# Auto-generalized Playbook synthesized by WinTerM",
            "set -eo pipefail",
            "export DEBIAN_FRONTEND=noninteractive",
            "",
        ]

        for idx, p in enumerate(parameters, start=1):
            env_var = p.name.upper()
            default_val = p.default_value if p.default_value is not None else ""
            lines.append(f'{env_var}="${{{idx}:-{default_val}}}"')

        lines.append("")
        for cmd in commands:
            generalized_cmd = cmd
            for p in parameters:
                if p.default_value is not None:
                    generalized_cmd = cls._substitute_literal(
                        generalized_cmd, p.default_value, f"${{{p.name.upper()}}}"
                    )
            lines.append(generalized_cmd)

        return "\n".join(lines)

    @classmethod
    def _synthesize_cmd_script(
        cls,
        commands: List[str],
        parameters: List[PlaybookParameter],
    ) -> str:
        """Synthesizes a standard Windows batch (.cmd) script."""
        lines = [
            "@echo off",
            "rem Auto-generalized Playbook synthesized by WinTerM",
            "",
        ]
        for idx, p in enumerate(parameters, start=1):
            var_name = p.name.upper()
            default_val = p.default_value if p.default_value is not None else ""
            lines.append(f'if "%~{idx}"=="" (set "{var_name}={default_val}") else (set "{var_name}=%~{idx}")')

        lines.append("")
        for cmd in commands:
            generalized_cmd = cmd
            for p in parameters:
                if p.default_value is not None:
                    generalized_cmd = cls._substitute_literal(
                        generalized_cmd, p.default_value, f"%{p.name.upper()}%"
                    )
            lines.append(generalized_cmd)

        return "\n".join(lines)

    @classmethod
    def match_goal(cls, goal: str, playbooks: List[Playbook]) -> PlaybookMatchResult:
        """Matches a user goal against a catalog of playbooks and extracts parameter values."""
        goal_clean = goal.strip().lower()

        best_match: Optional[Playbook] = None
        best_score: float = 0.0
        extracted_params: Dict[str, Any] = {}

        for playbook in playbooks:
            # Check direct sample goals
            for sample in playbook.sample_goals:
                if sample.lower() == goal_clean:
                    return PlaybookMatchResult(
                        matched=True,
                        playbook=playbook,
                        confidence=1.0,
                        extracted_params=cls._extract_params_from_goal(goal, playbook),
                        reason=f"Exact match on sample goal: '{sample}'",
                    )

            # Score based on token overlap against signature and description
            sig_tokens = set(playbook.pattern_signature.split("_"))
            goal_tokens = set(re.findall(r"\w+", goal_clean))

            overlap = len(sig_tokens.intersection(goal_tokens))
            score = overlap / max(len(sig_tokens), 1)

            if score > best_score:
                best_score = score
                best_match = playbook

        if best_match and best_score >= 0.5:
            params = cls._extract_params_from_goal(goal, best_match)
            return PlaybookMatchResult(
                matched=True,
                playbook=best_match,
                confidence=round(best_score, 2),
                extracted_params=params,
                reason=f"Matched signature '{best_match.pattern_signature}' with confidence {round(best_score, 2)}",
            )

        return PlaybookMatchResult(
            matched=False,
            playbook=None,
            confidence=round(best_score, 2),
            extracted_params={},
            reason="No playbook matched the goal with sufficient confidence.",
        )

    @classmethod
    def _extract_params_from_goal(cls, goal: str, playbook: Playbook) -> Dict[str, Any]:
        """Extracts concrete parameter values from the goal based on expected playbook parameters."""
        extracted: Dict[str, Any] = {}
        for p in playbook.parameters:
            if p.name == "pid":
                m = _RE_PID.search(goal)
                if m:
                    extracted[p.name] = int(m.group(1))
                elif p.default_value is not None:
                    extracted[p.name] = p.default_value
            elif p.name == "port" or p.param_type == "int":
                m = _RE_PORT.search(goal)
                if m:
                    extracted[p.name] = int(m.group(2))
                elif p.default_value is not None:
                    extracted[p.name] = p.default_value
            elif p.name == "path" or p.param_type == "path":
                m = _RE_WIN_PATH.search(goal) or _RE_POSIX_PATH.search(goal)
                if m:
                    extracted[p.name] = m.group(1).strip()
                elif p.default_value is not None:
                    extracted[p.name] = p.default_value
            elif p.name == "service_name":
                m = _RE_SERVICE.search(goal)
                if m:
                    extracted[p.name] = m.group(1).strip()
                elif p.default_value is not None:
                    extracted[p.name] = p.default_value
            else:
                if p.default_value is not None:
                    extracted[p.name] = p.default_value

        return extracted
