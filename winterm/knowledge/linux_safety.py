r"""LinuxSafetyGuard: Deterministic destructive-command classification for Linux & WSL environments.

Protects against catastrophic agent actions in Linux / WSL environments:
  - Recursive root or system deletions (rm -rf /)
  - Raw drive overwrites and formatting (dd, mkfs, wipefs, fdisk)
  - Fork bombs (:(){ :|:& };:)
  - Catastrophic permission destruction (chmod -R 777 /, chown)
  - Critical system termination (kill -9 1, shutdown, init 0)
  - Security and firewall deactivations (ufw disable, iptables -F)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class LinuxSafetyVerdict:
    """A deterministic safety classification for a Linux/POSIX command."""
    label: str                       # destructive | privileged | network_sensitive | safe
    is_dangerous: bool
    warning: str = ""
    matched_pattern: Optional[str] = None
    matched_target: Optional[str] = None


# Protected system paths in POSIX/Linux filesystem hierarchy
PROTECTED_LINUX_PATHS: List[re.Pattern] = [
    re.compile(r"^/(bin|boot|dev|etc|lib|lib64|opt|proc|root|sbin|sys|usr|var)($|/)", re.IGNORECASE),
    re.compile(r"^/etc/(shadow|passwd|sudoers|fstab|crontab)", re.IGNORECASE),
    re.compile(r"^/dev/(sd[a-z]|nvme\d+n\d+|vd[a-z]|hd[a-z]|mem|kmem)", re.IGNORECASE),
    re.compile(r"^/$"),                    # root filesystem
    re.compile(r"^/\*$"),                  # wildcard root
    re.compile(r"^~$"),                    # whole user home
]

# Explicitly destructive patterns on Linux
DESTRUCTIVE_LINUX_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # 1. Recursive deletions of root or vital directories.
    #    Matches any recursive `rm` aimed at an absolute path, the home/root
    #    glob, or a wildcard. Relative sub-directory deletes (e.g. `rm -rf build/`)
    #    are intentionally *not* escalated unless they resolve to a glob.
    (
        re.compile(
            r"\brm\b[^\n;|]*?(?:-[a-z]*r[a-z]*\b|--recursive\b)[^\n;|]*?("
            r"--no-preserve-root"
            r"|\s/\*"
            r"|\s/(?:\s|$|;|\|)"
            r"|\s~(?:\s|$|/)"
            r"|\s/(?:bin|boot|dev|etc|lib|lib64|opt|proc|root|sbin|sys|usr|var)(?:/|\s|$|\*)"
            r"|\s/(?:home|mnt|media|srv|data|tmp|run)(?:/|\s|$|\*)"
            r"|\s\*(?:\s|$|;|\|)"
            r"|\s\.\*(?:\s|$|;|\|)"
            r")",
            re.IGNORECASE,
        ),
        "Recursive deletion targeting root or vital system directories.",
    ),
    (
        re.compile(r"\brm\s+-[a-zA-Z]*[rf][a-zA-Z]*\s+--no-preserve-root", re.IGNORECASE),
        "Explicit --no-preserve-root flag passed to rm.",
    ),
    # 1b. Indirect recursive deletion via find/xargs
    (
        re.compile(r"\bfind\s+[^\n;|]*\s-delete\b", re.IGNORECASE),
        "Recursive 'find -delete' operation can purge entire directory trees.",
    ),
    (
        re.compile(r"\bxargs\b[^\n;|]*\brm\b[^\n;|]*-[a-zA-Z]*r", re.IGNORECASE),
        "xargs piped into recursive 'rm' deletion.",
    ),
    (
        re.compile(r"\bmv\b\s+[^\s;|]+\s+/(?:\s|$|;)|\bmv\b[^\n;|]*\s+/\*", re.IGNORECASE),
        "Moving a filesystem overflow into root/hierarchy.",
    ),
    # 2. Classic Bash fork bomb
    (
        re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", re.IGNORECASE),
        "Bash fork bomb detected: will exhaust process table and hang kernel.",
    ),
    # 3. Raw disk block wiping or direct writing
    (
        re.compile(r"\bdd\s+.*of=/dev/(sd[a-z]|nvme\d+n\d+|vd[a-z]|hd[a-z]|loop\d+)", re.IGNORECASE),
        "Direct block overwrite of disk partition or storage device with dd.",
    ),
    (
        re.compile(r">\s*/dev/(sd[a-z]|nvme\d+n\d+|vd[a-z]|hd[a-z])", re.IGNORECASE),
        "Direct redirection into block storage device.",
    ),
    # 4. Filesystem formatting and partitioning
    (
        re.compile(r"\bmkfs(\.[a-zA-Z0-9_-]+)?\s+/dev/", re.IGNORECASE),
        "Filesystem creation / format command (mkfs) targeting block device.",
    ),
    (
        re.compile(r"\b(wipefs|shred|fdisk|parted|sfdisk)\s+.*(/dev/|--all)", re.IGNORECASE),
        "Destructive disk partitioning or secure erase targeting drive.",
    ),
    # 5. Global permission destruction
    (
        re.compile(r"\bchmod\s+(-[a-zA-Z]*R[a-zA-Z]*\s+)?(777|000)\s+(/|/\*|/etc|/boot|/bin|/usr)", re.IGNORECASE),
        "Recursive permission destruction (777/000) on system hierarchy.",
    ),
    (
        re.compile(r"\bchown\s+(-[a-zA-Z]*R[a-zA-Z]*\s+).*?\s+(/|/\*|/etc|/boot)", re.IGNORECASE),
        "Recursive ownership override on root system hierarchy.",
    ),
    # 6. Critical process termination
    (
        re.compile(r"\bkill\s+(-9|-KILL)\s+1\b", re.IGNORECASE),
        "Attempted SIGKILL of init/systemd (PID 1), causing immediate kernel panic.",
    ),
    # 7. Unscheduled power off or reboot
    (
        re.compile(r"\b(shutdown|poweroff|halt|init\s+0)\b", re.IGNORECASE),
        "Immediate system shutdown or halt will terminate the agent host environment.",
    ),
]

# Network and firewall disruptive operations
NETWORK_SENSITIVE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(r"\biptables\s+(-F|-X|--flush)\b", re.IGNORECASE),
        "Flushing iptables firewall rules drops active security policies.",
    ),
    (
        re.compile(r"\bufw\s+(disable|reset)\b", re.IGNORECASE),
        "Disabling UFW host firewall leaves network ports unguarded.",
    ),
    (
        re.compile(r"\bnft\s+flush\s+ruleset\b", re.IGNORECASE),
        "Flushing nftables ruleset removes network isolation rules.",
    ),
    (
        re.compile(r"\bip\s+link\s+set\s+(eth\d+|en[a-z0-9]+|wlan\d+)\s+down\b", re.IGNORECASE),
        "Bringing primary network interface down will disconnect agent session.",
    ),
]

# Privileged operations requiring sudo / root
PRIVILEGED_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(r"\b(sudo|doas|pkexec)\b", re.IGNORECASE),
        "Execution with elevated superuser privileges.",
    ),
    (
        re.compile(r"\buserdel\s+.*", re.IGNORECASE),
        "User account deletion.",
    ),
    (
        re.compile(r"\b(systemctl|service)\s+(stop|restart|disable)\s+(sshd|ssh|systemd-journald|docker)", re.IGNORECASE),
        "Stopping or disabling critical system service.",
    ),
]


class LinuxSafetyGuard:
    """Evaluates Linux and WSL bash commands for safety before execution."""

    @classmethod
    def evaluate(cls, command: str) -> LinuxSafetyVerdict:
        """Classifies a proposed Linux command into a deterministic safety verdict."""
        cmd_clean = command.strip()
        if not cmd_clean:
            return LinuxSafetyVerdict(label="safe", is_dangerous=False)

        # 1. Check Destructive Patterns first
        for pattern, warning in DESTRUCTIVE_LINUX_PATTERNS:
            match = pattern.search(cmd_clean)
            if match:
                return LinuxSafetyVerdict(
                    label="destructive",
                    is_dangerous=True,
                    warning=warning,
                    matched_pattern=pattern.pattern,
                    matched_target=match.group(0),
                )

        # 2. Check Network Sensitive Patterns
        for pattern, warning in NETWORK_SENSITIVE_PATTERNS:
            match = pattern.search(cmd_clean)
            if match:
                return LinuxSafetyVerdict(
                    label="network_sensitive",
                    is_dangerous=True,
                    warning=warning,
                    matched_pattern=pattern.pattern,
                    matched_target=match.group(0),
                )

        # 3. Check Privileged Patterns
        for pattern, warning in PRIVILEGED_PATTERNS:
            match = pattern.search(cmd_clean)
            if match:
                return LinuxSafetyVerdict(
                    label="privileged",
                    # Aligned with the Windows SafetyGuard: privileged operations
                    # require elevation and are treated as dangerous so a
                    # sandboxed agent cannot silently escalate to root.
                    is_dangerous=True,
                    warning=warning,
                    matched_pattern=pattern.pattern,
                    matched_target=match.group(0),
                )

        # 4. Safe by default
        return LinuxSafetyVerdict(
            label="safe",
            is_dangerous=False,
            warning="",
        )

    @classmethod
    def make_non_interactive(cls, command: str) -> str:
        """Injects non-interactive switches to standard Linux package managers and tools."""
        cmd = command.strip()

        # apt / apt-get: inject -y and DEBIAN_FRONTEND=noninteractive
        if re.search(r"\bapt(-get)?\s+(install|upgrade|dist-upgrade|remove|purge|autoremove)\b", cmd, re.IGNORECASE):
            if "-y" not in cmd and "--yes" not in cmd:
                cmd = re.sub(
                    r"(\bapt(-get)?\s+(install|upgrade|dist-upgrade|remove|purge|autoremove)\b)",
                    r"\1 -y",
                    cmd,
                    flags=re.IGNORECASE,
                )
            if "DEBIAN_FRONTEND" not in cmd:
                cmd = f"DEBIAN_FRONTEND=noninteractive {cmd}"

        # dnf / yum: inject -y
        elif re.search(r"\b(dnf|yum)\s+(install|update|upgrade|remove)\b", cmd, re.IGNORECASE):
            if "-y" not in cmd:
                cmd = re.sub(
                    r"(\b(dnf|yum)\s+(install|update|upgrade|remove)\b)",
                    r"\1 -y",
                    cmd,
                    flags=re.IGNORECASE,
                )

        # pacman: inject --noconfirm immediately after the sub-command so a
        # compound tail (e.g. `pacman -S foo && reboot`) is not corrupted.
        elif re.search(r"\bpacman\s+-S[a-zA-Z]*\b", cmd, re.IGNORECASE):
            if "--noconfirm" not in cmd:
                cmd = re.sub(r"(\bpacman\s+-S[a-zA-Z]*)", r"\1 --noconfirm", cmd, count=1, flags=re.IGNORECASE)

        # apk: inject --no-cache
        elif re.search(r"\bapk\s+add\b", cmd, re.IGNORECASE):
            if "--no-cache" not in cmd:
                cmd = re.sub(r"(\bapk\s+add\b)", r"\1 --no-cache", cmd, flags=re.IGNORECASE)

        return cmd

    classify = evaluate
