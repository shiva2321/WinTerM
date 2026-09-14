"""Precondition and Idempotency Scheduler (The WHEN of 5W)."""

import re
from typing import List, Optional, Dict, Any, Tuple
from winterm.models.intent import PlanStep, ActionCategory
from winterm.models.reasoning import PreconditionCheck, PreconditionType
from winterm.models.context import ElevationLevel, ShellType
from winterm.engine.executor import WindowsShellExecutor
from winterm.knowledge.elevation_rules import ElevationRules


class PreconditionScheduler:
    """Derives and evaluates system pre-conditions, state guards, and idempotency checks (The WHEN)."""

    def __init__(self, executor: Optional[WindowsShellExecutor] = None):
        self.executor = executor or WindowsShellExecutor(default_shell=ShellType.POWERSHELL_51)

    def derive_preconditions(self, step: PlanStep) -> List[PreconditionCheck]:
        """Infers necessary pre-condition checks and idempotency guards for a given step."""
        checks: List[PreconditionCheck] = []
        cmd = step.command.lower()

        # 1. Elevation check
        if step.required_elevation == ElevationLevel.ADMIN:
            checks.append(
                PreconditionCheck(
                    check_id=f"{step.step_id}-chk-admin",
                    check_type=PreconditionType.IS_ADMIN,
                    target="Administrator Token",
                    expected_state=True,
                    probe_command=(
                        "[Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()"
                        ".IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)"
                    ),
                    failure_message="Step requires elevated Administrator permissions, but current process is unprivileged.",
                )
            )

        # 2. Port listening checks (e.g. kill process on port X)
        port = step.metadata.get("port")
        if port:
            checks.append(
                PreconditionCheck(
                    check_id=f"{step.step_id}-chk-port-{port}",
                    check_type=PreconditionType.PORT_LISTENING,
                    target=str(port),
                    expected_state=True,
                    probe_command=f"[bool](Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue)",
                    skip_if_already_satisfied=False,
                    failure_message=f"No active process or connection found listening on port {port}.",
                )
            )

        # 3. Process running checks
        proc_name = step.metadata.get("process_name")
        if proc_name:
            checks.append(
                PreconditionCheck(
                    check_id=f"{step.step_id}-chk-proc-{proc_name}",
                    check_type=PreconditionType.PROCESS_RUNNING,
                    target=proc_name,
                    expected_state=True,
                    probe_command=f"[bool](Get-Process -Name '{proc_name}' -ErrorAction SilentlyContinue)",
                    skip_if_already_satisfied=False,
                    failure_message=f"Process '{proc_name}' is not currently running.",
                )
            )

        # 4. Service existence and state
        service_name = step.metadata.get("service_name")
        if service_name:
            checks.append(
                PreconditionCheck(
                    check_id=f"{step.step_id}-chk-svc-{service_name}",
                    check_type=PreconditionType.SERVICE_RUNNING,
                    target=service_name,
                    expected_state=True,
                    probe_command=f"[bool](Get-Service -Name '{service_name}' -ErrorAction SilentlyContinue)",
                    failure_message=f"Windows service '{service_name}' does not exist on this machine.",
                )
            )

        # 5. Directory creation idempotency check
        if "new-item" in cmd and "-itemtype directory" in cmd:
            path_m = re.search(r"-path\s+['\"]?([^'\"]+)['\"]?", cmd, re.IGNORECASE)
            if path_m:
                target_dir = path_m.group(1).strip()
                checks.append(
                    PreconditionCheck(
                        check_id=f"{step.step_id}-chk-dir-exists",
                        check_type=PreconditionType.PATH_NOT_EXISTS,
                        target=target_dir,
                        expected_state=False,
                        probe_command=f"Test-Path -Path '{target_dir}'",
                        skip_if_already_satisfied=True,  # Idempotent skip if folder already exists
                        failure_message=f"Directory '{target_dir}' already exists. Skipping redundant creation.",
                    )
                )

        return checks

    def evaluate_preconditions(self, checks: List[PreconditionCheck]) -> Tuple[bool, bool, List[str]]:
        """Evaluates precondition checks against the live system.
        
        Returns:
            (all_passed: bool, should_skip_idempotent: bool, error_reasons: List[str])
        """
        all_passed = True
        should_skip = False
        failures = []

        for check in checks:
            # Special-case admin check in-memory
            if check.check_type == PreconditionType.IS_ADMIN:
                is_admin = ElevationRules.is_current_process_admin()
                check.is_satisfied = is_admin
                if not is_admin:
                    all_passed = False
                    failures.append(check.failure_message)
                continue

            # Run probe command
            res = self.executor.execute(
                check.probe_command,
                shell=check.probe_shell,
                timeout_seconds=10,
                step_id=check.check_id,
                auto_diagnose=False,
            )

            out = res.stdout.strip().lower()
            probe_bool = (out == "true")

            if check.check_type in (PreconditionType.PORT_LISTENING, PreconditionType.PROCESS_RUNNING, PreconditionType.SERVICE_RUNNING):
                check.is_satisfied = probe_bool
                # If target is not present, we record it
                if not probe_bool and not check.skip_if_already_satisfied:
                    # Note: for terminating actions, not running might mean it's already satisfied
                    pass

            elif check.check_type == PreconditionType.PATH_NOT_EXISTS:
                # Expected false (path does not exist)
                path_exists = probe_bool
                check.is_satisfied = not path_exists
                if path_exists and check.skip_if_already_satisfied:
                    should_skip = True

        return all_passed, should_skip, failures
