"""Tests for Low-Level Windows Subsystems: Layer 0 (Kernel/Boot), Layer 1 (Storage/NTFS/ACL), Layer 2 (Process/Memory)."""

import pytest
from winterm.subsystems.kernel_boot import KernelBootSubsystem
from winterm.subsystems.storage_ntfs import StorageNTFSSubsystem
from winterm.subsystems.process_memory import ProcessMemorySubsystem
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import ActionCategory


def test_kernel_boot_subsystem_plans():
    # BCD Query
    step_bcd = KernelBootSubsystem.query_boot_configuration()
    assert step_bcd.category == ActionCategory.SYSTEM
    assert "bcdedit" in step_bcd.command
    assert step_bcd.required_elevation == ElevationLevel.ADMIN

    # Power Schemes
    step_power = KernelBootSubsystem.query_power_schemes()
    assert "powercfg" in step_power.command

    # TPM Status
    step_tpm = KernelBootSubsystem.query_tpm_status()
    assert "Get-Tpm" in step_tpm.command
    assert step_tpm.required_elevation == ElevationLevel.ADMIN

    # Firmware Mode (UEFI/BIOS)
    step_fw = KernelBootSubsystem.query_uefi_firmware_type()
    assert "PEFirmwareType" in step_fw.command or "Win32_ComputerSystem" in step_fw.command


def test_storage_ntfs_subsystem_plans():
    # Disks list
    step_disks = StorageNTFSSubsystem.list_physical_disks()
    assert step_disks.category == ActionCategory.STORAGE
    assert "Get-Disk" in step_disks.command
    assert step_disks.required_elevation == ElevationLevel.ADMIN

    # Volumes
    step_vols = StorageNTFSSubsystem.list_volumes()
    assert "Get-Volume" in step_vols.command

    # BitLocker
    step_bit = StorageNTFSSubsystem.query_bitlocker_status("C:")
    assert "Get-BitLockerVolume" in step_bit.command

    # VSS Shadow copies
    step_vss = StorageNTFSSubsystem.list_shadow_copies()
    assert "vssadmin" in step_vss.command

    # ACL inspection
    step_acl = StorageNTFSSubsystem.inspect_acls(r"C:\Windows")
    assert "Get-Acl" in step_acl.command

    # Grant Full Control via icacls
    step_grant = StorageNTFSSubsystem.grant_full_control_acl(r"C:\temp\data", "Everyone")
    assert "icacls" in step_grant.command
    assert "(OI)(CI)F" in step_grant.command


def test_process_memory_subsystem_plans():
    # Priority
    step_prio = ProcessMemorySubsystem.set_process_priority(pid=1234, priority="High")
    assert "PriorityClass = 'High'" in step_prio.command

    # Affinity
    step_aff = ProcessMemorySubsystem.set_cpu_affinity(pid=1234, core_mask=3)
    assert "ProcessorAffinity = [IntPtr]3" in step_aff.command

    # Loaded modules
    step_mod = ProcessMemorySubsystem.inspect_loaded_modules(pid=1234)
    assert ".Modules" in step_mod.command

    # Threads
    step_th = ProcessMemorySubsystem.inspect_process_threads(pid=1234)
    assert ".Threads" in step_th.command
