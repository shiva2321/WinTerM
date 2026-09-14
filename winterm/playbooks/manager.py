"""Playbook Manager: Recurrence detection, quota enforcement, LRU eviction, and execution."""

from __future__ import annotations

import os
import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from winterm.models.context import ShellType
from winterm.models.result import ExecutionResult
from winterm.engine.executor import WindowsShellExecutor
from winterm.knowledge.safety_guard import SafetyGuard
from winterm.knowledge.linux_safety import LinuxSafetyGuard
from winterm.playbooks.models import Playbook, PlaybookParameter, CandidateTaskRecord, PlaybookMatchResult
from winterm.playbooks.generalizer import ScriptGeneralizer
from winterm.playbooks.gate import ScriptJustificationGate, ScriptNotJustifiedError


class PlaybookManager:
    """Manages reusable task playbooks, detects recurring tasks, generalizes routines, and enforces quotas."""

    RECURRENCE_THRESHOLD: int = 2
    MAX_PLAYBOOKS_CAP: int = 50

    def __init__(self, storage_dir: Optional[str] = None, executor: Optional[WindowsShellExecutor] = None):
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path.cwd() / ".winterm" / "playbooks"

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.executor = executor or WindowsShellExecutor()
        self.safety_guard = SafetyGuard()
        self.linux_safety_guard = LinuxSafetyGuard()

        self._candidates: Dict[str, CandidateTaskRecord] = {}
        self._playbooks: Dict[str, Playbook] = {}
        self._load_playbooks()

    # =========================================================================
    # 1. RECURRENCE DETECTION & PROMOTION
    # =========================================================================

    def record_task_execution(
        self,
        goal: str,
        commands: List[str],
        shell: ShellType = ShellType.POWERSHELL_51,
        auto_promote: bool = True,
    ) -> Optional[Playbook]:
        """Registers a completed task in the candidate buffer.
        
        Enforces the ScriptJustificationGate: Drops atomic one-liners so they are never
        tracked or promoted into unnecessary script clutter.
        Promotes to a persistent Playbook if recurrence threshold is reached.
        """
        # Script Justification Gate: Do not track atomic commands
        justification = ScriptJustificationGate.evaluate(goal, commands, shell=shell)
        if not justification.is_justified:
            return None

        signature, params = ScriptGeneralizer.extract_signature_and_params(goal, commands)

        # Check if already a persistent playbook
        for pb in self._playbooks.values():
            if pb.pattern_signature == signature:
                pb.execution_count += 1
                pb.last_executed_at = time.time()
                self._save_index()
                return pb

        # Update candidate buffer
        if signature in self._candidates:
            candidate = self._candidates[signature]
            candidate.hit_count += 1
            candidate.last_seen = time.time()
            if candidate.commands != commands and commands:
                candidate.commands = commands

            # Promote if hit threshold
            if auto_promote and candidate.hit_count >= self.RECURRENCE_THRESHOLD:
                playbook = self.create_playbook_from_task(
                    goal=goal,
                    commands=candidate.commands,
                    shell=candidate.shell,
                    signature=signature,
                    params=params,
                )
                del self._candidates[signature]
                return playbook
            return None
        else:
            # Ephemeral ring buffer: enforce max 50 candidate tasks to avoid memory leaks
            if len(self._candidates) >= 50:
                oldest_key = min(self._candidates.keys(), key=lambda k: self._candidates[k].last_seen)
                del self._candidates[oldest_key]

            self._candidates[signature] = CandidateTaskRecord(
                signature=signature,
                raw_goal=goal,
                commands=commands,
                shell=shell,
                hit_count=1,
            )
            return None

    def create_playbook_from_task(
        self,
        goal: str,
        commands: List[str],
        shell: ShellType = ShellType.POWERSHELL_51,
        signature: Optional[str] = None,
        params: Optional[List[PlaybookParameter]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        force_script: bool = False,
    ) -> Playbook:
        """Explicitly generalizes a sequence of task commands into a persistent playbook.
        
        Raises ScriptNotJustifiedError if the task does not warrant a script and force_script is False.
        """
        justification = ScriptJustificationGate.evaluate(goal, commands, shell=shell, force_script=force_script)
        if not justification.is_justified:
            raise ScriptNotJustifiedError(justification.reason)
        if signature is None or params is None:
            sig, prms = ScriptGeneralizer.extract_signature_and_params(goal, commands)
            signature = signature or sig
            params = params or prms

        # Safety audit
        combined_cmds = "\n".join(commands)
        safety_tier = "safe"
        if shell in (ShellType.WSL_BASH, ShellType.BASH):
            verdict = self.linux_safety_guard.classify(combined_cmds)
            if verdict and verdict.is_dangerous:
                safety_tier = "destructive"
        else:
            v = self.safety_guard.classify(combined_cmds)
            if v and v.is_dangerous:
                safety_tier = "destructive"

        script_body = ScriptGeneralizer.synthesize_playbook_script(commands, params, shell)

        playbook_id = f"pb-{uuid.uuid4().hex[:8]}"
        display_name = name or signature.replace("_", " ").title()
        desc = description or f"Auto-generalized routine for: {goal}"

        playbook = Playbook(
            playbook_id=playbook_id,
            name=display_name,
            description=desc,
            pattern_signature=signature,
            target_shell=shell,
            parameters=params,
            script_body=script_body,
            sample_goals=[goal],
            execution_count=1,
            success_count=1,
            created_at=time.time(),
            last_executed_at=time.time(),
            is_promoted=True,
            safety_tier=safety_tier,
        )

        # Enforce quota before adding
        self._enforce_quota()

        self._playbooks[playbook_id] = playbook
        self._persist_playbook_file(playbook)
        self._save_index()
        return playbook

    # =========================================================================
    # 2. MATCHING & FAST-PATH EXECUTION
    # =========================================================================

    def match_playbook(self, goal: str) -> PlaybookMatchResult:
        """Finds a matching generalized playbook for a given user goal and extracts parameters."""
        return ScriptGeneralizer.match_goal(goal, list(self._playbooks.values()))

    def execute_playbook(
        self,
        playbook_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        background: bool = False,
    ) -> ExecutionResult:
        """Executes a generalized playbook with supplied or extracted parameters."""
        if playbook_id not in self._playbooks:
            return ExecutionResult(
                step_id=f"exec-{playbook_id}",
                command=f"Playbook '{playbook_id}'",
                shell=ShellType.POWERSHELL_51,
                success=False,
                exit_code=-1,
                stderr=f"Playbook '{playbook_id}' not found in local catalog.",
            )

        playbook = self._playbooks[playbook_id]
        params = parameters or {}

        # Fill in default parameter values if omitted
        for p in playbook.parameters:
            if p.name not in params and p.default_value is not None:
                params[p.name] = p.default_value

        # Build execution command
        script_path = self.storage_dir / f"{playbook.playbook_id}.ps1" if playbook.target_shell in (
            ShellType.POWERSHELL_51, ShellType.POWERSHELL_7
        ) else self.storage_dir / f"{playbook.playbook_id}.sh"

        if not script_path.exists():
            self._persist_playbook_file(playbook)

        if playbook.target_shell in (ShellType.POWERSHELL_51, ShellType.POWERSHELL_7):
            arg_str = " ".join([f"-{k.capitalize()} '{v}'" for k, v in params.items()])
            exec_command = f"& '{str(script_path)}' {arg_str}".strip()
        elif playbook.target_shell in (ShellType.WSL_BASH, ShellType.BASH):
            arg_str = " ".join([f"'{v}'" for v in params.values()])
            exec_command = f"bash '{str(script_path)}' {arg_str}".strip()
        else:
            arg_str = " ".join([f'"{v}"' for v in params.values()])
            exec_command = f'cmd.exe /c "{str(script_path)}" {arg_str}'.strip()

        # Update telemetry
        playbook.execution_count += 1
        playbook.last_executed_at = time.time()

        res = self.executor.execute(
            command=exec_command,
            shell=playbook.target_shell,
            timeout_seconds=60,
        )

        if res.success:
            playbook.success_count += 1
        self._save_index()

        return res

    # =========================================================================
    # 3. QUOTA MANAGEMENT & LRU PRUNING
    # =========================================================================

    def list_playbooks(self) -> List[Playbook]:
        """Returns all registered playbooks sorted by last executed timestamp descending."""
        return sorted(self._playbooks.values(), key=lambda p: p.last_executed_at, reverse=True)

    def prune_playbooks(self, max_items: int = 30) -> int:
        """Prunes least recently used playbooks down to max_items. Returns count of purged items."""
        if len(self._playbooks) <= max_items:
            return 0

        # Sort by (last_executed_at, execution_count) ascending (oldest and least used first)
        sorted_pbs = sorted(self._playbooks.values(), key=lambda p: (p.last_executed_at, p.execution_count))
        purge_count = len(self._playbooks) - max_items
        to_purge = sorted_pbs[:purge_count]

        for pb in to_purge:
            del self._playbooks[pb.playbook_id]
            # Remove script files on disk
            for ext in (".ps1", ".sh", ".cmd"):
                p = self.storage_dir / f"{pb.playbook_id}{ext}"
                if p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass

        self._save_index()
        return len(to_purge)

    def _enforce_quota(self) -> None:
        """Ensures the repository never exceeds MAX_PLAYBOOKS_CAP."""
        if len(self._playbooks) >= self.MAX_PLAYBOOKS_CAP:
            self.prune_playbooks(max_items=self.MAX_PLAYBOOKS_CAP - 1)

    # =========================================================================
    # 4. PERSISTENCE HELPERS
    # =========================================================================

    def _persist_playbook_file(self, playbook: Playbook) -> None:
        """Writes the standalone script file to the playbook storage directory."""
        ext = ".ps1" if playbook.target_shell in (ShellType.POWERSHELL_51, ShellType.POWERSHELL_7) else (
            ".sh" if playbook.target_shell in (ShellType.WSL_BASH, ShellType.BASH) else ".cmd"
        )
        script_file = self.storage_dir / f"{playbook.playbook_id}{ext}"
        try:
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(playbook.script_body)
        except Exception:
            pass

    def _save_index(self) -> None:
        """Saves playbooks metadata index to disk."""
        index_file = self.storage_dir / "playbooks.json"
        try:
            data = {pb_id: pb.model_dump() for pb_id, pb in self._playbooks.items()}
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load_playbooks(self) -> None:
        """Loads existing playbooks from the storage directory index."""
        index_file = self.storage_dir / "playbooks.json"
        if not index_file.exists():
            return
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for pb_id, pb_dict in data.items():
                    self._playbooks[pb_id] = Playbook.model_validate(pb_dict)
        except Exception:
            pass
