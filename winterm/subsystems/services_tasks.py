"""Layer 3: Services (SCM), Task Scheduler & Background Execution Subsystem."""

from typing import Dict, Any, List, Optional
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import PlanStep, ActionCategory
from winterm.knowledge.param_safety import (
    ps_literal,
    cmd_quote,
    safe_identifier,
    validated_choice,
    int_in_range,
)

_STARTUP_TYPES = ("Automatic", "Manual", "Disabled", "Boot", "System")
_SCHEDULE_TYPES = ("ONLOGON", "ONSTART", "ONCE", "DAILY", "WEEKLY", "MONTHLY")


class ServicesTasksSubsystem:
    """Manages Windows Service Control Manager (SCM), Task Scheduler, and background asynchronous jobs."""

    @classmethod
    def configure_service_recovery(cls, service_name: str, reset_period_sec: int = 86400) -> PlanStep:
        """Configures Windows SCM to automatically restart the service upon failure via sc.exe."""
        safe_service = safe_identifier(service_name, fallback="spooler")
        reset = int_in_range(reset_period_sec, 0, 999999, 86400)
        return PlanStep(
            step_id=f"svc-recovery-{safe_service}",
            title=f"Configure Auto-Restart Failure Recovery for Service '{safe_service}'",
            category=ActionCategory.SERVICE,
            raw_intent=f"configure service recovery {safe_service}",
            target_shell=ShellType.CMD,
            required_elevation=ElevationLevel.ADMIN,
            command=f'sc.exe failure "{safe_service}" reset= {reset} actions= restart/5000/restart/10000/restart/60000',
            metadata={"subsystem": "services_tasks", "service_name": safe_service},
        )

    @classmethod
    def set_startup_type(cls, service_name: str, startup_type: str = "Automatic") -> PlanStep:
        """Configures service startup type (Automatic, Manual, Disabled)."""
        safe_service = safe_identifier(service_name, fallback="wuauserv")
        safe_type = validated_choice(startup_type, _STARTUP_TYPES, "Manual")
        return PlanStep(
            step_id=f"svc-starttype-{safe_service}",
            title=f"Set Service '{safe_service}' Startup Type to {safe_type}",
            category=ActionCategory.SERVICE,
            raw_intent=f"set startup {safe_service} {safe_type}",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=f"Set-Service -Name {ps_literal(safe_service)} -StartupType {safe_type}",
            metadata={"subsystem": "services_tasks", "service_name": safe_service, "type": safe_type},
        )

    @classmethod
    def create_scheduled_task(
        cls,
        task_name: str,
        executable_path: str,
        arguments: str = "",
        schedule_type: str = "ONLOGON",
    ) -> PlanStep:
        """Registers a persistent task in the Windows Task Scheduler using schtasks."""
        safe_task = safe_identifier(task_name, fallback="WinTermTask")
        safe_schedule = validated_choice(schedule_type, _SCHEDULE_TYPES, "ONLOGON")
        tr_value = f'"{executable_path}" {arguments}'.strip()
        safe_tr = cmd_quote(tr_value, allow_inner_quotes=True)
        cmd = f'schtasks /create /tn {cmd_quote(safe_task)} /tr {safe_tr} /sc {safe_schedule} /f'
        return PlanStep(
            step_id=f"task-create-{safe_task}",
            title=f"Register Scheduled Task: {safe_task}",
            category=ActionCategory.SYSTEM,
            raw_intent=f"create task {safe_task}",
            target_shell=ShellType.CMD,
            required_elevation=ElevationLevel.ADMIN,
            command=cmd,
            metadata={"subsystem": "services_tasks", "task_name": safe_task},
        )

    @classmethod
    def query_scheduled_task(cls, task_name: str) -> PlanStep:
        """Queries status, next run time, and author of a scheduled task."""
        safe_task = safe_identifier(task_name, fallback="WinTermTask")
        return PlanStep(
            step_id=f"task-query-{safe_task}",
            title=f"Query Scheduled Task: {safe_task}",
            category=ActionCategory.SYSTEM,
            raw_intent=f"query task {safe_task}",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                f"Get-ScheduledTask -TaskName {ps_literal(safe_task)} -ErrorAction Stop | "
                f"Select-Object -Property TaskName,TaskPath,State | ConvertTo-Json"
            ),
            metadata={"subsystem": "services_tasks", "task_name": safe_task},
        )

    @classmethod
    def delete_scheduled_task(cls, task_name: str) -> PlanStep:
        """Removes a task from Task Scheduler."""
        safe_task = safe_identifier(task_name, fallback="WinTermTask")
        return PlanStep(
            step_id=f"task-del-{safe_task}",
            title=f"Delete Scheduled Task: {safe_task}",
            category=ActionCategory.SYSTEM,
            raw_intent=f"delete task {safe_task}",
            target_shell=ShellType.CMD,
            required_elevation=ElevationLevel.ADMIN,
            command=f'schtasks /delete /tn {cmd_quote(safe_task)} /f',
            metadata={"subsystem": "services_tasks", "task_name": safe_task},
        )
