"""Tests for Mid-Level Windows Subsystems: Layer 3 (Services/Tasks), Layer 4 (Registry/Policy), Layer 5 (Security/Crypto)."""

import pytest
from winterm.subsystems.services_tasks import ServicesTasksSubsystem
from winterm.subsystems.registry_policy import RegistryPolicySubsystem
from winterm.subsystems.security_crypto import SecurityCryptoSubsystem
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import ActionCategory


def test_services_tasks_subsystem_plans():
    # SCM Failure auto-restart configuration
    step_rec = ServicesTasksSubsystem.configure_service_recovery("spooler")
    assert "sc.exe failure" in step_rec.command
    assert "reset= 86400" in step_rec.command
    assert step_rec.required_elevation == ElevationLevel.ADMIN

    # Startup type
    step_start = ServicesTasksSubsystem.set_startup_type("wuauserv", "Manual")
    assert "Set-Service -Name 'wuauserv' -StartupType Manual" in step_start.command

    # Scheduled Task creation
    step_task = ServicesTasksSubsystem.create_scheduled_task(
        task_name="AgentSync",
        executable_path=r"C:\Tools\sync.exe",
        arguments="--silent",
    )
    assert "schtasks /create" in step_task.command
    assert "AgentSync" in step_task.command


def test_registry_policy_subsystem_plans():
    # Set typed DWord value
    step_reg = RegistryPolicySubsystem.set_typed_registry_value(
        path=r"HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem",
        name="LongPathsEnabled",
        value=1,
        prop_type="DWord",
    )
    assert step_reg.category == ActionCategory.REGISTRY
    assert "LongPathsEnabled" in step_reg.command
    assert "Set-ItemProperty" in step_reg.command
    assert step_reg.required_elevation == ElevationLevel.ADMIN

    # Group policy sync
    step_gp = RegistryPolicySubsystem.force_group_policy_update()
    assert "gpupdate /force" in step_gp.command


def test_security_crypto_subsystem_plans():
    # Privilege audit
    step_priv = SecurityCryptoSubsystem.audit_user_privileges()
    assert "whoami /priv" in step_priv.command

    # Local users
    step_users = SecurityCryptoSubsystem.list_local_users()
    assert "Get-LocalUser" in step_users.command
    assert step_users.required_elevation == ElevationLevel.ADMIN

    # Certificate Store
    step_certs = SecurityCryptoSubsystem.list_certificates_in_store("LocalMachine", "My")
    assert "Cert:\\LocalMachine\\My" in step_certs.command

    # Windows Defender
    step_def = SecurityCryptoSubsystem.query_defender_status()
    assert "Get-MpComputerStatus" in step_def.command

    # Defender exclusion
    step_excl = SecurityCryptoSubsystem.add_defender_exclusion(r"C:\AgentWorkspace")
    assert "Add-MpPreference -ExclusionPath 'C:\\AgentWorkspace'" in step_excl.command
    assert step_excl.required_elevation == ElevationLevel.ADMIN
