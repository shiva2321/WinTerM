"""Layer 3: Services (SCM), Task Scheduler & Background Execution Subsystem."""

from typing import Dict, Any, List, Optional
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import PlanStep, ActionCategory


class ServicesTasksSubsystem:
    """Manages Windows Service Control Manager (SCM), Task Scheduler, and background asynchronous jobs."""

    @classmethod
    def configure_service_recovery(cls, service_name: str, reset_period_sec: int = 86400) -> PlanStep:
        """Configures Windows SCM to automatically restart the service upon failure via sc.exe."""
        return PlanStep(
            step_id=f"svc-recovery-{service_name}",
            title=f"Configure Auto-Restart Failure Recovery for Service '{service_name}'",
            category=ActionCategory.SERVICE,
            raw_intent=f"configure service recovery {service_name}",
            target_shell=ShellType.CMD,
            required_elevation=ElevationLevel.ADMIN,
            command=f'sc.exe failure "{service_name}" reset= {reset_period_sec} actions= restart/5000/restart/10000/restart/60000',
            metadata={"subsystem": "services_tasks", "service_name": service_name},
        )

    @classmethod
    def set_startup_type(cls, service_name: str, startup_type: str = "Automatic") -> PlanStep:
        """Configures service startup type (Automatic, Manual, Disabled)."""
        return PlanStep(
            step_id=f"svc-starttype-{service_name}",
            title=f"Set Service '{service_name}' Startup Type to {startup_type}",
            category=ActionCategory.SERVICE,
            raw_intent=f"set startup {service_name} {startup_type}",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=f"Set-Service -Name '{service_name}' -StartupType {startup_type}",
            metadata={"subsystem": "services_tasks", "service_name": service_name, "type": startup_type},
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
        cmd = f'schtasks /create /tn "{task_name}" /tr "\"{executable_path}\" {arguments}" /sc {schedule_type} /f'
        return PlanStep(
            step_id=f"task-create-{task_name.replace(' ', '_')}",
            title=f"Register Scheduled Task: {task_name}",
            category=ActionCategory.SYSTEM,
            raw_intent=f"create task {task_name}",
            target_shell=ShellType.CMD,
            required_elevation=ElevationLevel.ADMIN,
            command=cmd,
            metadata={"subsystem": "services_tasks", "task_name": task_name},
        )

    @classmethod
    def query_scheduled_task(cls, task_name: str) -> PlanStep:
        """Queries status, next run time, and author of a scheduled task."""
        return PlanStep(
            step_id=f"task-query-{task_name.replace(' ', '_')}",
            title=f"Query Scheduled Task: {task_name}",
            category=ActionCategory.SYSTEM,
            raw_intent=f"query task {task_name}",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                f"Get-ScheduledTask -TaskName '{task_name}' -ErrorAction Stop | "
                f"Select-Object -Property TaskName,TaskPath,State | ConvertTo-Json"
            ),
            metadata={"subsystem": "services_tasks", "task_name": task_name},
        )

    @classmethod
    def delete_scheduled_task(cls, task_name: str) -> PlanStep:
        """Removes a task from Task Scheduler."""
        return PlanStep(
            step_id=f"task-del-{task_name.replace(' ', '_')}",
            title=f"Delete Scheduled Task: {task_name}",
            category=ActionCategory.SYSTEM,
            raw_intent=f"delete task {task_name}",
            target_shell=ShellType.CMD,
            required_elevation=ElevationLevel.ADMIN,
            command=f'schtasks /delete /tn "{task_name}" /f',
            metadata={"subsystem": "services_tasks", "task_name": task_name},
        )
