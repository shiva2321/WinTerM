"""Windows Error Catalog: Codes, HRESULTs, signatures, and automated remedies."""

import re
from typing import Optional, Dict, Any, List
from winterm.models.result import SelfHealingProposal
from winterm.models.context import ShellType


class ErrorDiagnosis:
    """Diagnostic blueprint for a specific Windows terminal failure."""

    def __init__(
        self,
        pattern: str,
        signature_name: str,
        root_cause: str,
        remedy_explanation: str,
        suggested_fix_template: Optional[str] = None,
        requires_elevation: bool = False,
    ):
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.signature_name = signature_name
        self.root_cause = root_cause
        self.remedy_explanation = remedy_explanation
        self.suggested_fix_template = suggested_fix_template
        self.requires_elevation = requires_elevation


class WindowsErrorCatalog:
    """Catalog of Windows error codes, HRESULTs, and self-healing rules."""

    DIAGNOSES: List[ErrorDiagnosis] = [
        # --- ACCESS DENIED / ELEVATION ---
        ErrorDiagnosis(
            pattern=r"(0x80070005|Access is denied|UnauthorizedAccessException|E_ACCESSDENIED|error:\s*5\b)",
            signature_name="ACCESS_DENIED_0x80070005",
            root_cause="Operation attempted to modify a protected system resource, registry hive (HKLM), or file without administrator privileges.",
            remedy_explanation="Rerun command with elevated privileges using RunAs / Administrator token.",
            suggested_fix_template="Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile', '-Command', \"{failed_command}\"",
            requires_elevation=True,
        ),

        # --- EXECUTION POLICY RESTRICTION ---
        ErrorDiagnosis(
            pattern=r"(PSSecurityException|File .* cannot be loaded because running scripts is disabled|AuthorizationManager check failed)",
            signature_name="EXECUTION_POLICY_RESTRICTED",
            root_cause="PowerShell ExecutionPolicy is set to Restricted or AllSigned by default on Windows.",
            remedy_explanation="Bypass ExecutionPolicy for the current process scope without altering system-wide policy.",
            suggested_fix_template="powershell.exe -ExecutionPolicy Bypass -NoProfile -Command \"{failed_command}\"",
            requires_elevation=False,
        ),

        # --- FILE LOCKED / SHARING VIOLATION ---
        ErrorDiagnosis(
            pattern=r"(0x80070020|The process cannot access the file because it is being used by another process|Sharing violation|ERROR_SHARING_VIOLATION)",
            signature_name="FILE_LOCKED_SHARING_VIOLATION_0x80070020",
            root_cause="Another active process has an exclusive lock on the target file or directory.",
            remedy_explanation="Identify the locking process using OpenFiles or Get-Process, terminate it or wait for release.",
            suggested_fix_template="Get-Process | Where-Object {{ $_.Modules.FileName -like '*{target}*' }} | Select-Object Id, ProcessName",
            requires_elevation=False,
        ),

        # --- FILE BLOCKED / UNTRUSTED ZONE ---
        ErrorDiagnosis(
            pattern=r"(0x80131515|This file came from another computer and might be blocked|Attachment Manager)",
            signature_name="ATTACHMENT_MANAGER_ZONE_BLOCKED",
            root_cause="Windows Attachment Manager flagged the file as downloaded from the internet (Zone.Identifier stream).",
            remedy_explanation="Unblock the file stream using PowerShell Unblock-File cmdlet.",
            suggested_fix_template="Unblock-File -Path '{target_file}'",
            requires_elevation=False,
        ),

        # --- COMMAND NOT FOUND / PATH MISMATCH ---
        ErrorDiagnosis(
            pattern=r"(CommandNotFoundException|is not recognized as an internal or external command|The term '.*?' is not recognized)",
            signature_name="COMMAND_NOT_FOUND",
            root_cause="The specified binary or cmdlet is not in PATH or not registered in the current shell session.",
            remedy_explanation="Check if tool is installed in Program Files or LocalAppData, or refresh environment PATH.",
            suggested_fix_template="$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User'); Get-Command '{target}' -ErrorAction SilentlyContinue",
            requires_elevation=False,
        ),

        # --- PATH NOT FOUND / DIRECTORY MISSING ---
        ErrorDiagnosis(
            pattern=r"(0x80070003|ItemNotFoundException|Cannot find path|The system cannot find the path specified)",
            signature_name="PATH_NOT_FOUND_0x80070003",
            root_cause="The target parent folder does not exist or was typed with an invalid path separator.",
            remedy_explanation="Ensure parent directory structure exists with New-Item -ItemType Directory.",
            suggested_fix_template="New-Item -ItemType Directory -Path '{parent_dir}' -Force",
            requires_elevation=False,
        ),

        # --- MAX_PATH EXCEEDED ---
        ErrorDiagnosis(
            pattern=r"(PathTooLongException|The specified path, file name, or both are too long|0x800700CE)",
            signature_name="PATH_TOO_LONG_MAX_PATH",
            root_cause="Path exceeds Windows 260-character legacy MAX_PATH limit.",
            remedy_explanation="Prefix the absolute path with \\\\?\\ or enable LongPathsEnabled in registry.",
            suggested_fix_template="Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem' -Name 'LongPathsEnabled' -Value 1",
            requires_elevation=True,
        ),

        # --- PORT ALREADY IN USE ---
        ErrorDiagnosis(
            pattern=r"(address already in use|WSAEADDRINUSE|10048|Only one usage of each socket address)",
            signature_name="PORT_ALREADY_IN_USE_10048",
            root_cause="A process is already bound to the specified TCP/UDP port.",
            remedy_explanation="Find the PID holding the port using Get-NetTCPConnection and terminate it.",
            suggested_fix_template="Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force }}",
            requires_elevation=False,
        ),

        # --- SERVICE DISABLED ---
        ErrorDiagnosis(
            pattern=r"(0x80070422|ERROR_SERVICE_DISABLED|The service cannot be started, either because it is disabled|service is disabled)",
            signature_name="SERVICE_DISABLED_0x80070422",
            root_cause="The target Windows Service has its startup type set to Disabled in SCM.",
            remedy_explanation="Change service startup type to Automatic or Manual and restart it.",
            suggested_fix_template="Set-Service -Name '{service}' -StartupType Automatic; Start-Service -Name '{service}'",
            requires_elevation=True,
        ),

        # --- RPC SERVER UNAVAILABLE ---
        ErrorDiagnosis(
            pattern=r"(0x800706BA|The RPC server is unavailable|RPC_S_SERVER_UNAVAILABLE)",
            signature_name="RPC_SERVER_UNAVAILABLE_0x800706BA",
            root_cause="Remote Procedure Call (RpcSs) or Windows Management Instrumentation (Winmgmt) service is stopped.",
            remedy_explanation="Start the RPC Subsystem and WMI services.",
            suggested_fix_template="Start-Service RpcSs; Start-Service Winmgmt",
            requires_elevation=True,
        ),

        # --- WMI OBJECT NOT FOUND ---
        ErrorDiagnosis(
            pattern=r"(0x80041002|WBEM_E_NOT_FOUND|Invalid class|ManagementException)",
            signature_name="WMI_CLASS_NOT_FOUND_0x80041002",
            root_cause="The requested WMI/CIM class is not registered or supported on this Windows release.",
            remedy_explanation="Query Get-CimClass to discover supported provider classes.",
            suggested_fix_template="Get-CimClass -ClassName '*{target}*'",
            requires_elevation=False,
        ),

        # --- DNS RESOLUTION FAILURE ---
        ErrorDiagnosis(
            pattern=r"(0x80072EE7|The server name or address could not be resolved|Resolve-DnsName : .* : Resource record does not exist)",
            signature_name="DNS_RESOLUTION_FAILURE_0x80072EE7",
            root_cause="DNS query failed to resolve the hostname or client cache is stale.",
            remedy_explanation="Flush DNS client resolver cache and re-test connection.",
            suggested_fix_template="ipconfig /flushdns",
            requires_elevation=False,
        ),

        # --- ROBOCOPY FATAL ERROR (handled explicitly in diagnose(); a synthetic
        # "ExitCode:" sentinel here would self-match and misfire). ---
    ]

    _PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

    @staticmethod
    def _derive_placeholders(failed_command: str) -> Dict[str, str]:
        """Best-effort extraction of template placeholders from the failed command."""
        fc = failed_command or ""
        out: Dict[str, str] = {}
        quoted_paths = re.findall(r"['\"]([^'\"]+)['\"]", fc)
        bare_paths = re.findall(r"([A-Za-z]:\\[^\s'\"]+)", fc)
        paths = quoted_paths or bare_paths
        if paths:
            out["path"] = paths[0]
            out["target"] = paths[0]
            out["target_file"] = paths[0]
            out["parent_dir"] = paths[0]
        svc = re.search(r"(?:-Name|stop|start|restart|sc(?:\.exe)?)\s+['\"]?([\w\-.]+)", fc, re.IGNORECASE)
        if svc:
            out["service"] = svc.group(1)
        port = re.search(r"\b(\d{2,5})\b", fc)
        if port:
            out["port"] = port.group(1)
        quoted = re.findall(r'"([^"]+)"', fc)
        if len(quoted) >= 2:
            out["source"], out["dest"] = quoted[0], quoted[1]
        # Fallback for command-not-found style templates: the first token.
        if "target" not in out:
            first = fc.strip().split()
            if first:
                out["target"] = first[0]
        return out

    @classmethod
    def _render_fix(cls, template: str, failed_command: str) -> str:
        """Substitutes all placeholders; returns an empty string if any remain unresolved."""
        if not template:
            return ""
        placeholders = cls._derive_placeholders(failed_command)
        rendered = template.replace("{failed_command}", (failed_command or "").replace('"', '`"'))
        for key, value in placeholders.items():
            rendered = rendered.replace("{" + key + "}", str(value))
        if cls._PLACEHOLDER_RE.search(rendered):
            # Unresolved placeholder -> executing this would be a broken command.
            # Return empty so the healer does not run a malformed command.
            return ""
        return rendered

    @classmethod
    def diagnose(cls, stderr: str, stdout: str, exit_code: int, failed_command: str = "") -> Optional[SelfHealingProposal]:
        """Analyzes command failure output and generates a precise self-healing proposal."""
        # Fast exit on clean execution
        if exit_code == 0 and not (stderr and stderr.strip()):
            return None

        # Robocopy has a distinctive exit-code contract (>=8 means failures) that
        # is not encoded in its text output; evaluate it explicitly against the
        # failed command rather than a synthetic string.
        if "robocopy" in (failed_command or "").lower() and isinstance(exit_code, int) and 8 <= exit_code <= 16:
            robocopy_diag = None
            for d in cls.DIAGNOSES:
                if d.signature_name == "ROBOCOPY_FATAL_ERROR":
                    robocopy_diag = d
                    break
            if robocopy_diag is None:
                robocopy_diag = ErrorDiagnosis(
                    pattern=r"robocopy",
                    signature_name="ROBOCOPY_FATAL_ERROR",
                    root_cause="Robocopy encountered unrecoverable errors (exit code >= 8 indicates at least one file was not copied).",
                    remedy_explanation="Check read/write permissions on destination volume, disk space, and locked files.",
                    suggested_fix_template='robocopy "{source}" "{dest}" /E /Z /R:1 /W:1 /V',
                    requires_elevation=False,
                )
            return SelfHealingProposal(
                error_signature=robocopy_diag.signature_name,
                root_cause=robocopy_diag.root_cause,
                remedy_explanation=robocopy_diag.remedy_explanation,
                healing_command=cls._render_fix(robocopy_diag.suggested_fix_template or "", failed_command),
                healing_shell=ShellType.POWERSHELL_51,
                requires_elevation=robocopy_diag.requires_elevation,
            )

        combined_text = f"{stderr}\n{stdout}"

        for diagnosis in cls.DIAGNOSES:
            match = diagnosis.pattern.search(combined_text)
            if match:
                fix_cmd = cls._render_fix(diagnosis.suggested_fix_template or "", failed_command)
                return SelfHealingProposal(
                    error_signature=diagnosis.signature_name,
                    root_cause=diagnosis.root_cause,
                    remedy_explanation=diagnosis.remedy_explanation,
                    healing_command=fix_cmd,
                    healing_shell=ShellType.POWERSHELL_51,
                    requires_elevation=diagnosis.requires_elevation,
                )

        # Fallback to Linux / POSIX error catalog
        try:
            from winterm.knowledge.linux_errors import LinuxErrorCatalog
            linux_diag = LinuxErrorCatalog.diagnose(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                failed_command=failed_command,
            )
            if linux_diag:
                return linux_diag
        except Exception:
            pass

        return None
