"""Tests for Precondition Scheduler and Idempotency Guards."""

from winterm.cognition.scheduler import PreconditionScheduler
from winterm.models.intent import PlanStep, ActionCategory
from winterm.models.reasoning import PreconditionType
from winterm.models.context import ShellType, ElevationLevel


def test_scheduler_derives_preconditions():
    scheduler = PreconditionScheduler()

    # Step requiring admin
    step_admin = PlanStep(
        step_id="step-adm",
        title="Admin task",
        category=ActionCategory.SERVICE,
        raw_intent="restart service",
        command="Restart-Service spooler",
        target_shell=ShellType.POWERSHELL_51,
        required_elevation=ElevationLevel.ADMIN,
        metadata={"service_name": "spooler"},
    )
    checks = scheduler.derive_preconditions(step_admin)
    check_types = [c.check_type for c in checks]
    assert PreconditionType.IS_ADMIN in check_types
    assert PreconditionType.SERVICE_RUNNING in check_types


def test_scheduler_idempotent_directory():
    scheduler = PreconditionScheduler()

    step_mkdir = PlanStep(
        step_id="step-dir",
        title="Create folder",
        category=ActionCategory.FILESYSTEM,
        raw_intent="mkdir",
        command="New-Item -ItemType Directory -Path 'C:\\temp\\idempotent_test'",
        target_shell=ShellType.POWERSHELL_51,
    )
    checks = scheduler.derive_preconditions(step_mkdir)
    dir_chk = next(c for c in checks if c.check_type == PreconditionType.PATH_NOT_EXISTS)
    assert dir_chk.skip_if_already_satisfied is True
