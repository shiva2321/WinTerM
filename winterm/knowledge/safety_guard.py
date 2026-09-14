r"""SafetyGuard: deterministic destructive-command classification for Windows.

The SFT-safety Knowledge Graph (mshojaei77/terminal-command-execution-sft) is
sparse: only a handful of commands carry a ``has_safety_rule`` edge, and the
classifier fails open to ``safe`` whenever nothing matches. That means
``Remove-Item -Recurse -Force C:\Windows\\System32`` or ``Stop-Computer -Force``
can be reported as *not dangerous*.

This module adds a curated, deterministic first-pass guard that runs BEFORE the
graph fallback. It recognises destructive verbs (deletion, formatting, power
control, registry surgery) and protected targets (system directories, boot
files, partition roots, registry hives) and never lets them fall through to
``safe``.

Design rules:
  * If a destructive verb touches a protected target      -> ``destructive``
  * If a destructive verb touches an arbitrary path       -> ``destructive`` (conservative)
  * Read-only / query verbs are never escalated.
  * The final ``is_dangerous`` is always decided by the guard when it fires.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SafetyVerdict:
    """A deterministic safety classification produced by the guard."""
    label: str                       # destructive | privileged | network_sensitive | safe
    is_dangerous: bool
    warning: str = ""
    skill: str = "general"
    matched_pattern: Optional[str] = None
    matched_target: Optional[str] = None


# ---------------------------------------------------------------------------
# Protected locations: touching these with a destructive verb is always risky.
# ---------------------------------------------------------------------------
PROTECTED_PATHS: List[re.Pattern] = [
    re.compile(r"C:\\windows(\\|$)", re.IGNORECASE),
    re.compile(r"C:\\windows\\system32(\\|$)", re.IGNORECASE),
    re.compile(r"C:\\windows\\syswow64(\\|$)", re.IGNORECASE),
    re.compile(r"C:\\program files(\\|$)", re.IGNORECASE),
    re.compile(r"C:\\program files \(x86\)(\\|$)", re.IGNORECASE),
    re.compile(r"C:\\programdata(\\|$)", re.IGNORECASE),
    re.compile(r"C:\\boot(\\|$)", re.IGNORECASE),
    re.compile(r"C:\\", re.IGNORECASE),                    # partition root
    re.compile(r"\$env:windir", re.IGNORECASE),
    re.compile(r"\$env:systemroot", re.IGNORECASE),
    re.compile(r"\$env:programfiles", re.IGNORECASE),
    re.compile(r"HKEY_LOCAL_MACHINE", re.IGNORECASE),
    re.compile(r"HKLM(\\|:|\b)", re.IGNORECASE),
    re.compile(r"HKEY_CLASSES_ROOT", re.IGNORECASE),
    re.compile(r"HKCR(\\|:|\b)", re.IGNORECASE),
    re.compile(r"\\boot\\.*\.ini", re.IGNORECASE),
    re.compile(r"ntldr|bootmgr|boot\.ini|winload", re.IGNORECASE),
    re.compile(r"pagefile\.sys|hiberfil\.sys", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Destructive verbs (PowerShell cmdlets, cmd built-ins, and native binaries).
# ---------------------------------------------------------------------------
DESTRUCTIVE_VERBS: List[re.Pattern] = [
    # PowerShell filesystem / volume
    re.compile(r"\bremove-item\b", re.IGNORECASE),
    re.compile(r"\bremove-items\b", re.IGNORECASE),
    re.compile(r"\brm\b", re.IGNORECASE),
    re.compile(r"\bri\b", re.IGNORECASE),
    re.compile(r"\bdel\b", re.IGNORECASE),
    re.compile(r"\berase\b", re.IGNORECASE),
    re.compile(r"\brmdir\b", re.IGNORECASE),
    re.compile(r"\brd\b", re.IGNORECASE),
    re.compile(r"\bformat-volume\b", re.IGNORECASE),
    re.compile(r"\bclear-recyclebin\b", re.IGNORECASE),
    re.compile(r"\bdiskpart\b", re.IGNORECASE),
    re.compile(r"\bclean\b", re.IGNORECASE),                # diskpart clean
    re.compile(r"\bformat\b", re.IGNORECASE),
    re.compile(r"\bnew-partition\b", re.IGNORECASE),
    re.compile(r"\bremove-partition\b", re.IGNORECASE),
    re.compile(r"\bformat-volume\b", re.IGNORECASE),
    # Power control
    re.compile(r"\bstop-computer\b", re.IGNORECASE),
    re.compile(r"\brestart-computer\b", re.IGNORECASE),
    re.compile(r"\bshutdown\b", re.IGNORECASE),
    re.compile(r"\breboot\b", re.IGNORECASE),
    re.compile(r"\blogoff\b", re.IGNORECASE),
    re.compile(r"\bwmic\s+shutdown", re.IGNORECASE),
    # Registry surgery
    re.compile(r"\bremove-itemproperty\b", re.IGNORECASE),
    re.compile(r"\breg\s+delete\b", re.IGNORECASE),
    re.compile(r"\breg\s+add\b", re.IGNORECASE),
    re.compile(r"\bremove-item\b", re.IGNORECASE),
    re.compile(r"\bclear-itemproperty\b", re.IGNORECASE),
    # ACL / ownership changes on system targets
    re.compile(r"\btakeown\b", re.IGNORECASE),
    re.compile(r"\bicacls\b", re.IGNORECASE),
    re.compile(r"\bremove-acl\b", re.IGNORECASE),
    re.compile(r"\bset-acl\b", re.IGNORECASE),
    re.compile(r"\bsc\s+delete\b", re.IGNORECASE),
    re.compile(r"\bschtasks\s+/delete\b", re.IGNORECASE),
    # Boot / recovery
    re.compile(r"\bbcdedit\s+/set\b", re.IGNORECASE),
    re.compile(r"\bbcdedit\s+/delete\b", re.IGNORECASE),
    re.compile(r"\bdiskpart\s+/s\b", re.IGNORECASE),
    re.compile(r"\bbootrec\s+/fixboot\b", re.IGNORECASE),
    re.compile(r"\bbootrec\s+/fixmbr\b", re.IGNORECASE),
    re.compile(r"\bsfc\s+/scannow\b", re.IGNORECASE),
    re.compile(r"\bdism\s+/online\s+/cleanup-image", re.IGNORECASE),
    # Disable critical security / system features
    re.compile(r"\bdisable-windowsoptionalfeature\b", re.IGNORECASE),
    re.compile(r"\bremove-windowsoptionalfeature\b", re.IGNORECASE),
    re.compile(r"\bset-mpPreference\s+-DisableRealtimeMonitoring", re.IGNORECASE),
    re.compile(r"\bset-mppreference\s+-disable\b", re.IGNORECASE),
    re.compile(r"\buninstall-windowsfeature\b", re.IGNORECASE),
]

# Destructive verbs that are ONLY dangerous when aimed at a protected path
# (used to avoid over-flagging benign uses like ``rm file.txt`` in a project).
# For safety we are conservative: most deletions of arbitrary paths are still
# destructive by nature, so the main list already escalates them.
CONDITIONAL_VERBS: List[re.Pattern] = [
    re.compile(r"\b(?:del|erase|rmdir|rd)\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Privileged operations: require elevation but are not necessarily destructive.
# ---------------------------------------------------------------------------
PRIVILEGED_VERBS: List[re.Pattern] = [
    re.compile(r"\binstall-windowsfeature\b", re.IGNORECASE),
    re.compile(r"\benable-windowsoptionalfeature\b", re.IGNORECASE),
    re.compile(r"\benable-bitlocker\b", re.IGNORECASE),
    re.compile(r"\bnew-netfirewallrule\b", re.IGNORECASE),
    re.compile(r"\bremove-netfirewallrule\b", re.IGNORECASE),
    re.compile(r"\bnew-service\b", re.IGNORECASE),
    re.compile(r"\bset-service\b", re.IGNORECASE),
    re.compile(r"\bsc\s+config\b", re.IGNORECASE),
    re.compile(r"\bgpupdate\s+/force\b", re.IGNORECASE),
    re.compile(r"\breg\s+add\b", re.IGNORECASE),
    re.compile(r"\breg\s+delete\b", re.IGNORECASE),
    re.compile(r"\bbcdedit\b", re.IGNORECASE),
    re.compile(r"\bchkdsk\b", re.IGNORECASE),
    re.compile(r"\bsfc\b", re.IGNORECASE),
    re.compile(r"\bdism\b", re.IGNORECASE),
    re.compile(r"\btakeown\b", re.IGNORECASE),
    re.compile(r"\bicacls\b", re.IGNORECASE),
    re.compile(r"\bset-executionpolicy\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Network-sensitive verbs.
# ---------------------------------------------------------------------------
NETWORK_VERBS: List[re.Pattern] = [
    re.compile(r"\binvoke-webrequest\b", re.IGNORECASE),
    re.compile(r"\binvoke-restmethod\b", re.IGNORECASE),
    re.compile(r"\bcurl\b", re.IGNORECASE),
    re.compile(r"\bwget\b", re.IGNORECASE),
    re.compile(r"\bssh\b", re.IGNORECASE),
    re.compile(r"\bnet\s+use\b", re.IGNORECASE),
    re.compile(r"\bnet\s+user\b", re.IGNORECASE),
    re.compile(r"\bnet\s+localgroup\b", re.IGNORECASE),
    re.compile(r"\bscp\b", re.IGNORECASE),
    re.compile(r"\bsftp\b", re.IGNORECASE),
    re.compile(r"\bftp\b", re.IGNORECASE),
    re.compile(r"\bwsl\s+--set-default-version\b", re.IGNORECASE),
    re.compile(r"\bpsexec\b", re.IGNORECASE),
]

# Read-only / query verbs that must never be escalated.
READ_ONLY_VERBS: List[re.Pattern] = [
    re.compile(r"\bget-\b", re.IGNORECASE),
    re.compile(r"\bselect-\b", re.IGNORECASE),
    re.compile(r"\btest-\b", re.IGNORECASE),
    re.compile(r"\bwhere-\b", re.IGNORECASE),
    re.compile(r"\bfindstr\b", re.IGNORECASE),
    re.compile(r"\bdir\b", re.IGNORECASE),
    re.compile(r"\btype\b", re.IGNORECASE),
    re.compile(r"\blist\b", re.IGNORECASE),
    re.compile(r"\bquery\b", re.IGNORECASE),
    re.compile(r"\bwhoami\b", re.IGNORECASE),
    re.compile(r"\bipconfig\b", re.IGNORECASE),
    re.compile(r"\bping\b", re.IGNORECASE),
    re.compile(r"\btracert\b", re.IGNORECASE),
    re.compile(r"\bnetstat\b", re.IGNORECASE),
    re.compile(r"\bnet\s+statistics\b", re.IGNORECASE),
    re.compile(r"\bmeasure-command\b", re.IGNORECASE),
    re.compile(r"\bmeasure-object\b", re.IGNORECASE),
    re.compile(r"\bsort-object\b", re.IGNORECASE),
    re.compile(r"\bget-netipaddress\b", re.IGNORECASE),
    re.compile(r"\bget-process\b", re.IGNORECASE),
    re.compile(r"\bget-service\b", re.IGNORECASE),
    re.compile(r"\bget-eventlog\b", re.IGNORECASE),
    re.compile(r"\bget-win-event\b", re.IGNORECASE),
    re.compile(r"\bget-counter\b", re.IGNORECASE),
    re.compile(r"\bget-ciminstance\b", re.IGNORECASE),
    re.compile(r"\bget-volume\b", re.IGNORECASE),
    re.compile(r"\bget-disk\b", re.IGNORECASE),
    re.compile(r"\bget-physicaldisk\b", re.IGNORECASE),
    re.compile(r"\bget-acl\b", re.IGNORECASE),
    re.compile(r"\bget-windowsoptionalfeature\b", re.IGNORECASE),
    re.compile(r"\bget-scheduledtask\b", re.IGNORECASE),
    re.compile(r"\bget-netfirewallrule\b", re.IGNORECASE),
    re.compile(r"\bget-mppreference\b", re.IGNORECASE),
    re.compile(r"\bget-bitlockervolume\b", re.IGNORECASE),
    re.compile(r"\bquery user\b", re.IGNORECASE),
    re.compile(r"\bquery session\b", re.IGNORECASE),
]


class SafetyGuard:
    """Deterministic destructive/privileged/network classification of a command."""

    def classify(self, command: str) -> Optional[SafetyVerdict]:
        """Returns a verdict if this guard has a definitive classification.

        Returns ``None`` when the command is not clearly destructive/privileged
        or network-sensitive — the caller may then fall back to graph rules.
        """
        cmd = command.strip()
        if not cmd:
            return None
        low = cmd.lower()

        # NOTE: destructive/privileged/network checks run BEFORE the read-only
        # check. A pipeline such as
        #   Get-Service | Where-Object {$_.Status -eq 'Stopped'} | Stop-Computer -Force
        # contains a read-only verb (Get-Service) *and* a destructive one
        # (Stop-Computer). If the read-only check ran first it would
        # short-circuit to "safe" and the destructive tail of the pipeline
        # would never be evaluated -- exactly the fail-open behaviour this
        # guard exists to prevent, and (confirmed empirically against
        # WinTermAgent.execute_step()) it silently defeats the confirm_high_risk
        # safety gate for this class of command: risk_level stays READ_ONLY,
        # so the gate never triggers and the command runs unconfirmed. Severity
        # must win over position in the command string.

        # 1. Destructive verb against protected path -> destructive.
        for verb_pat in DESTRUCTIVE_VERBS:
            if verb_pat.search(low):
                target = self._find_protected_target(low)
                warning = (
                    f"Destructive operation '{verb_pat.pattern}' on protected "
                    f"path '{target}'. Verify target, scope, and intent before running."
                    if target
                    else f"Destructive operation '{verb_pat.pattern}'. This "
                        "permanently alters filesystem, volume, registry, or "
                        "power state and cannot be undone."
                )
                return SafetyVerdict(
                    label="destructive",
                    is_dangerous=True,
                    warning=warning,
                    skill="file_management",
                    matched_pattern=verb_pat.pattern,
                    matched_target=target,
                )

        # 3. Protected-target deletion with conditional verb (del/rd/rmdir/erase)
        target = self._find_protected_target(low)
        if target and self._matches_any(CONDITIONAL_VERBS, low):
            return SafetyVerdict(
                label="destructive",
                is_dangerous=True,
                warning=(
                    f"Deletion of protected path '{target}'. This operation is "
                    "permanent and cannot be recovered from the Recycle Bin."
                ),
                skill="file_management",
                matched_target=target,
            )

        # 4. Privileged operations.
        for verb_pat in PRIVILEGED_VERBS:
            if verb_pat.search(low):
                return SafetyVerdict(
                    label="privileged",
                    is_dangerous=True,
                    warning=(
                        f"Privileged operation '{verb_pat.pattern}' requires "
                        "Administrative elevation. Verify scope and intent."
                    ),
                    skill="system_administration",
                    matched_pattern=verb_pat.pattern,
                )

        # 5. Network-sensitive.
        for verb_pat in NETWORK_VERBS:
            if verb_pat.search(low):
                return SafetyVerdict(
                    label="network_sensitive",
                    is_dangerous=False,
                    warning=(
                        f"Command '{verb_pat.pattern}' performs network access. "
                        "Only run it against systems you are allowed to access."
                    ),
                    skill="networking",
                    matched_pattern=verb_pat.pattern,
                )

        # 6. Read-only queries are safe -- but only once nothing more severe
        # matched above, so a piped destructive tail can never hide behind a
        # read-only head.
        if self._matches_any(READ_ONLY_VERBS, low):
            return SafetyVerdict(
                label="safe",
                is_dangerous=False,
                skill="diagnostics",
                warning="Read-only query. No system state modified.",
            )

        return None

    # ------------------------------------------------------------------
    @staticmethod
    def _matches_any(patterns: List[re.Pattern], low: str) -> bool:
        return any(p.search(low) for p in patterns)

    @staticmethod
    def _find_protected_target(low: str) -> Optional[str]:
        for pat in PROTECTED_PATHS:
            m = pat.search(low)
            if m:
                return m.group(0)
        return None