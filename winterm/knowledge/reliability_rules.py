"""Windows Shell Reliability Rules: Hardened formatting, escaping, and quoting standards."""

import re
from typing import List, Tuple
from winterm.models.context import ShellType


class ReliabilityRules:
    """Enforces safety, quoting, escaping, and reliability rules for Windows terminal execution."""

    # Unicode emoji translation table for ASCII-safe Windows console output
    UNICODE_TO_ASCII_MAP = {
        "✓": "[OK]",
        "✔": "[OK]",
        "✅": "[OK]",
        "❌": "[X]",
        "✗": "[X]",
        "🔴": "[X]",
        "⚠️": "[WARN]",
        "⚡": "[!]",
        "ℹ️": "[INFO]",
        "ℹ": "[INFO]",
        "🔵": "[INFO]",
        "⏳": "[...]",
        "⏱️": "[...]",
        "➜": "->",
        "→": "->",
    }

    @classmethod
    def sanitize_for_windows_console(cls, text: str, ascii_only: bool = False) -> str:
        """Replaces problematic Unicode emojis with ASCII-safe tokens.

        Non-emoji Unicode (e.g. accented letters or CJK in paths/arguments) is
        **preserved** by default: commands are passed to the shell as native
        Unicode via ``CreateProcessW``. The previous unconditional
        ``encode("ascii", "replace")`` silently corrupted any non-ASCII path or
        argument into ``?``. Pass ``ascii_only=True`` for display/log strings
        that must survive a legacy OEM console.
        """
        sanitized = text
        for uni, ascii_repl in cls.UNICODE_TO_ASCII_MAP.items():
            sanitized = sanitized.replace(uni, ascii_repl)
        if ascii_only:
            sanitized = sanitized.encode("ascii", errors="replace").decode("ascii")
        return sanitized

    @classmethod
    def format_executable_invocation(cls, command: str, shell: ShellType = ShellType.POWERSHELL_51) -> str:
        """Ensures that executable paths starting with quotes use the PowerShell call operator (&)."""
        stripped = command.strip()
        if shell in (ShellType.POWERSHELL_51, ShellType.POWERSHELL_7):
            # If command starts with " or ' and doesn't already start with &, prepend &
            if (stripped.startswith('"') or stripped.startswith("'")) and not stripped.startswith("&"):
                return f"& {stripped}"
        return stripped

    @classmethod
    def quote_path_if_needed(cls, path: str) -> str:
        """Quotes a path if it contains spaces and is not already quoted."""
        p = path.strip()
        if (" " in p or "\t" in p) and not ((p.startswith('"') and p.endswith('"')) or (p.startswith("'") and p.endswith("'"))):
            return f'"{p}"'
        return p

    @classmethod
    def format_long_path(cls, path: str) -> str:
        """Applies Win32 extended-length path prefix (\\\\?\\) if path exceeds 240 chars."""
        cleaned = path.strip().strip('"').strip("'")
        if len(cleaned) > 240 and not cleaned.startswith("\\\\?\\"):
            # Check for drive letter path like C:\
            if re.match(r"^[A-Za-z]:\\", cleaned):
                return f'\\\\?\\{cleaned}'
        return path

    @classmethod
    def wrap_defensive_powershell(cls, script_body: str, fail_fast: bool = True) -> str:
        """Wraps PowerShell script body in standard strict, defensive boilerplate."""
        err_pref = "Stop" if fail_fast else "Continue"
        return (
            f"$ErrorActionPreference = '{err_pref}'; "
            f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            f"try {{ {script_body} }} catch {{ Write-Error $_; exit 1 }}"
        )

    @classmethod
    def ensure_parentheses_in_ps_conditions(cls, condition_expr: str) -> str:
        """Detects and fixes missing parentheses in PowerShell -and / -or conditions.
        
        Rule: In PowerShell, `if (Test-Path a -or Test-Path b)` throws an error.
        It must be written as `if ((Test-Path a) -or (Test-Path b))`.
        """
        # Checks if expressions around -and or -or are missing parentheses
        pattern = re.compile(
            r'\b(Test-Path|Get-Item|Get-ChildItem)\s+'
            r'("[^"]*"|\'[^\']*\'|[^\s()]+)\s+'
            r'(-and|-or)\s+'
            r'(Test-Path|Get-Item|Get-ChildItem)\s+'
            r'("[^"]*"|\'[^\']*\'|[^\s()]+)',
            re.IGNORECASE,
        )
        def replacer(match):
            cmd1, arg1, op, cmd2, arg2 = match.groups()
            return f"({cmd1.strip()} {arg1.strip()}) {op} ({cmd2.strip()} {arg2.strip()})"
        return pattern.sub(replacer, condition_expr)

    @classmethod
    def make_non_interactive(cls, command: str) -> str:
        """Injects non-interactive switches to common Windows tools to prevent terminal hangs."""
        cmd = command.strip()
        
        # Check if command is a compound multi-statement script
        is_compound = any(c in cmd for c in (";", "\n", "{", "}"))
        
        # PowerShell cmdlets
        if re.search(r'\b(Remove-Item|Restart-Computer|Stop-Process|Clear-RecycleBin)\b', cmd, re.IGNORECASE):
            if not is_compound:
                if "-Confirm:$false" not in cmd and "-Confirm" not in cmd:
                    cmd += " -Confirm:$false"
                if "-Force" not in cmd:
                    cmd += " -Force"
            else:
                # Appending '-Confirm:$false' to a compound statement would attach
                # to the wrong cmdlet. Suppress confirmation globally instead so
                # multi-statement scripts cannot hang on an interactive prompt.
                if "$ConfirmPreference" not in cmd and "-Confirm" not in cmd:
                    cmd = "$ConfirmPreference = 'None'; " + cmd
                
        # winget
        if "winget install" in cmd.lower() or "winget upgrade" in cmd.lower():
            if "--accept-source-agreements" not in cmd:
                cmd += " --accept-source-agreements"
            if "--accept-package-agreements" not in cmd:
                cmd += " --accept-package-agreements"
            if "--disable-interactivity" not in cmd:
                cmd += " --disable-interactivity"
                
        # choco
        if "choco install" in cmd.lower() or "choco upgrade" in cmd.lower():
            if "-y" not in cmd.lower() and "--yes" not in cmd.lower():
                cmd += " -y"
                
        # cmd.exe del / rmdir
        if re.match(r'^(del|erase)\b', cmd, re.IGNORECASE):
            if "/q" not in cmd.lower():
                cmd += " /q"
            if "/f" not in cmd.lower():
                cmd += " /f"
        elif re.match(r'^(rmdir|rd)\b', cmd, re.IGNORECASE):
            if "/q" not in cmd.lower():
                cmd += " /q"

        return cmd
