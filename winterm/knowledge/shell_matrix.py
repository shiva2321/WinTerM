"""Windows Shell Matrix: Capabilities, syntax rules, and optimal shell selection."""

import shutil
from typing import Dict, Any, List
from winterm.models.context import ShellType


class ShellMatrix:
    """Matrix of Windows shell capabilities, nuances, and routing rules."""

    SHELL_PROFILES: Dict[ShellType, Dict[str, Any]] = {
        ShellType.POWERSHELL_51: {
            "name": "Windows PowerShell 5.1 (Desktop)",
            "binary": "powershell.exe",
            "flags": ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command"],
            "native_objects": True,
            "pipeline_chain_operators": False,  # && and || not supported natively in PS 5.1
            "default_output_encoding": "UTF-16LE",
            "redirection_byte_safe": False,     # Older PS redirection can corrupt raw byte streams
            "strengths": [
                "Pre-installed on every Windows 10/11 system",
                "Direct .NET Framework & CIM access",
                "Deep OS management (Services, Registry, WMI/CIM, Event Log)",
            ],
            "limitations": [
                "No native && / || chaining (requires try/catch or -and grouping)",
                "Redirection rewriting byte streams unless UTF-8 is explicitly forced",
                "JSON depth defaults to 2 without -Depth parameter",
            ],
        },
        ShellType.POWERSHELL_7: {
            "name": "PowerShell 7+ (Core / pwsh)",
            "binary": "pwsh.exe",
            "flags": ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command"],
            "native_objects": True,
            "pipeline_chain_operators": True,   # Supports && and ||
            "default_output_encoding": "UTF-8",
            "redirection_byte_safe": True,      # PS 7.4+ preserves byte stream
            "strengths": [
                "Modern cross-platform .NET runtime",
                "Native && and || operators",
                "Clean UTF-8 stream handling",
                "High performance object pipelines",
            ],
            "limitations": [
                "Not installed by default; requires winget / msi installation",
            ],
        },
        ShellType.CMD: {
            "name": "Classic Windows Command Prompt (cmd.exe)",
            "binary": "cmd.exe",
            "flags": ["/d", "/s", "/c"],
            "native_objects": False,
            "pipeline_chain_operators": True,   # Supports && and ||
            "default_output_encoding": "OEM (e.g. CP437/CP850)",
            "redirection_byte_safe": True,
            "strengths": [
                "Universal availability on all Windows versions",
                "Zero startup overhead / instant execution",
                "Direct compatibility with legacy .bat and .cmd scripts",
            ],
            "limitations": [
                "Plain text only (no structured objects)",
                "Cryptic escaping (^, %, !)",
                "No native JSON or XML parsing",
                "Primitive error handling via %errorlevel%",
            ],
        },
    }

    @classmethod
    def recommend_shell(cls, category: str, command_intent: str, pwsh_installed: bool = False) -> ShellType:
        """Determines the most reliable shell for a given task category and intent."""
        # Structured system queries prefer PowerShell
        structured_categories = {
            "service", "registry", "diagnostic", "network", "process", "environment"
        }
        
        if category in structured_categories:
            return ShellType.POWERSHELL_7 if pwsh_installed else ShellType.POWERSHELL_51

        # Check for legacy batch scripts or simple exe triggers
        if command_intent.strip().endswith((".bat", ".cmd")):
            return ShellType.CMD

        # Default to available modern PowerShell, falling back to PS 5.1
        return ShellType.POWERSHELL_7 if pwsh_installed else ShellType.POWERSHELL_51

    @classmethod
    def get_shell_binary(cls, shell: ShellType) -> str:
        """Returns executable binary for the shell, resolved to absolute path if available."""
        if shell == ShellType.POWERSHELL_7:
            return shutil.which("pwsh") or "pwsh.exe"
        elif shell == ShellType.CMD:
            return shutil.which("cmd") or r"C:\Windows\System32\cmd.exe"
        else:
            return shutil.which("powershell") or r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

    @classmethod
    def build_command_args(cls, shell: ShellType, script_body: str) -> List[str]:
        """Wraps a script body with the shell binary and standard non-interactive flags."""
        binary = cls.get_shell_binary(shell)
        profile = cls.SHELL_PROFILES.get(shell, cls.SHELL_PROFILES[ShellType.POWERSHELL_51])
        base_flags = [binary] + list(profile["flags"])
        base_flags.append(script_body)
        return base_flags
