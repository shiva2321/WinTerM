"""Linux Error Catalog: POSIX error codes, exit codes, failure signatures, and automated remedies."""

import re
from typing import Optional, Dict, Any, List
from winterm.models.result import SelfHealingProposal
from winterm.models.context import ShellType


class LinuxErrorDiagnosis:
    """Diagnostic signature for a Linux or POSIX terminal failure."""

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


class LinuxErrorCatalog:
    """Catalog of standard Linux / POSIX error signatures and self-healing recommendations."""

    DIAGNOSES: List[LinuxErrorDiagnosis] = [
        # --- COMMAND NOT FOUND (EXIT 127) ---
        LinuxErrorDiagnosis(
            pattern=r"(command not found|127\b.*not found|No such file or directory.*exec)",
            signature_name="LINUX_COMMAND_NOT_FOUND_EXIT_127",
            root_cause="The requested binary or command is not in the system $PATH, or is not installed.",
            remedy_explanation="Install the missing package via apt/dnf/apk or verify command spelling and $PATH.",
            suggested_fix_template="command -v {command} || which {command}",
            requires_elevation=False,
        ),

        # --- PERMISSION DENIED (EXIT 126 / EACCES) ---
        LinuxErrorDiagnosis(
            pattern=r"(Permission denied|EACCES|error:\s*13\b|exit\s+status\s+126)",
            signature_name="LINUX_PERMISSION_DENIED_EACCES_126",
            root_cause="File lacks executable permissions (+x), or current user has insufficient read/write rights.",
            remedy_explanation="Grant execution permissions using chmod +x or rerun command with sudo if appropriate.",
            suggested_fix_template="chmod +x {target} || sudo {failed_command}",
            requires_elevation=True,
        ),

        # --- OUT OF MEMORY (EXIT 137 / SIGKILL) ---
        LinuxErrorDiagnosis(
            pattern=r"(Killed\b|exit\s+status\s+137|Out of memory|OOM command killed)",
            signature_name="LINUX_OOM_KILLED_EXIT_137",
            root_cause="Linux kernel Out-Of-Memory (OOM) killer terminated the process due to system RAM exhaustion.",
            remedy_explanation="Inspect memory consumption with 'free -h' or dmesg, and reduce process memory limit.",
            suggested_fix_template="dmesg -T | grep -i -E 'oom|killed process' | tail -n 5",
            requires_elevation=False,
        ),

        # --- SEGMENTATION FAULT (EXIT 139 / SIGSEGV) ---
        LinuxErrorDiagnosis(
            pattern=r"(Segmentation fault|exit\s+status\s+139|SIGSEGV|core dumped)",
            signature_name="LINUX_SEGFAULT_EXIT_139",
            root_cause="Process attempted an invalid memory access or null-pointer dereference.",
            remedy_explanation="Check for binary incompatibility, missing shared libraries, or invalid architecture build.",
            suggested_fix_template="ldd {target} || strace -f -e trace=memory {failed_command}",
            requires_elevation=False,
        ),

        # --- PORT ALREADY IN USE (EADDRINUSE) ---
        LinuxErrorDiagnosis(
            pattern=r"(Address already in use|EADDRINUSE|errno:\s*98\b)",
            signature_name="LINUX_PORT_IN_USE_EADDRINUSE_98",
            root_cause="Another daemon or process is already bound to the specified TCP/UDP network port.",
            remedy_explanation="Identify the listening PID using ss/fuser and terminate it or bind to a different port.",
            suggested_fix_template="ss -tulpn | grep :{port} || fuser -k {port}/tcp",
            requires_elevation=True,
        ),

        # --- DPKG / APT DATABASE LOCK ---
        LinuxErrorDiagnosis(
            pattern=r"(Could not get lock /var/lib/dpkg/lock|Could not open lock file /var/lib/apt/lists/lock|Resource temporarily unavailable.*dpkg)",
            signature_name="LINUX_APT_DPKG_LOCK_HELD",
            root_cause="Another apt, unattended-upgrades, or dpkg process is currently holding the package database lock.",
            remedy_explanation="Identify the locking process using lsof or fuser, wait for completion or kill stale apt PID.",
            suggested_fix_template="fuser -v /var/lib/dpkg/lock-frontend || ps aux | grep -i apt",
            requires_elevation=True,
        ),

        # --- NO SPACE LEFT ON DEVICE (ENOSPC) ---
        LinuxErrorDiagnosis(
            pattern=r"(No space left on device|ENOSPC|errno:\s*28\b)",
            signature_name="LINUX_NO_SPACE_ENOSPC_28",
            root_cause="Storage filesystem or inode capacity has been completely exhausted (100% full).",
            remedy_explanation="Free disk space by clearing /tmp, package caches (apt clean), or removing old logs.",
            suggested_fix_template="df -h && apt-get clean && journalctl --vacuum-time=1d",
            requires_elevation=True,
        ),

        # --- READ-ONLY FILESYSTEM (EROFS) ---
        LinuxErrorDiagnosis(
            pattern=r"(Read-only file system|EROFS|errno:\s*30\b)",
            signature_name="LINUX_READ_ONLY_FS_EROFS_30",
            root_cause="The target filesystem was mounted read-only (ro) or remounted ro due to storage corruption.",
            remedy_explanation="Check mount status with mount | grep 'ro,' and remount rw if appropriate.",
            suggested_fix_template="mount -o remount,rw {mountpoint}",
            requires_elevation=True,
        ),

        # --- PYTHON EXTERNALLY MANAGED ENVIRONMENT (PEP 668) ---
        LinuxErrorDiagnosis(
            pattern=r"(externally-managed-environment|PEP 668|This environment is externally managed)",
            signature_name="LINUX_PEP668_EXTERNALLY_MANAGED",
            root_cause="Modern Linux distributions (Ubuntu 23.04+, Debian 12+) restrict global pip installations.",
            remedy_explanation="Use a virtual environment (python -m venv .venv) or install via pipx or distro package.",
            suggested_fix_template="python3 -m venv .venv && source .venv/bin/activate && pip install {package}",
            requires_elevation=False,
        ),
    ]

    @classmethod
    def diagnose(
        cls,
        stdout: str,
        stderr: str,
        exit_code: int = 0,
        failed_command: str = "",
    ) -> Optional[SelfHealingProposal]:
        """Scans combined terminal output and exit code for known Linux error signatures."""
        if exit_code == 0 and not (stderr and stderr.strip()):
            return None

        combined_text = f"{stdout}\n{stderr}\nExit code: {exit_code}"

        for diag in cls.DIAGNOSES:
            if diag.pattern.search(combined_text):
                fix = diag.suggested_fix_template
                if fix:
                    fix = fix.replace("{failed_command}", failed_command)
                    fix = fix.replace("{command}", failed_command.split()[0] if failed_command else "command")
                    fix = fix.replace("{target}", failed_command.split()[-1] if failed_command else ".")
                    fix = fix.replace("{port}", "8080")
                    fix = fix.replace("{package}", failed_command.split()[-1] if failed_command else "pkg")
                    fix = fix.replace("{mountpoint}", "/")

                return SelfHealingProposal(
                    error_signature=diag.signature_name,
                    root_cause=diag.root_cause,
                    healing_command=fix or "",
                    healing_shell=ShellType.WSL_BASH,
                    remedy_explanation=diag.remedy_explanation,
                    requires_elevation=diag.requires_elevation,
                )

        return None
