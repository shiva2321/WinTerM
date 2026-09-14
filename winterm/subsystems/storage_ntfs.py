"""Layer 1: Storage, Disks, Volumes, VHD, VSS & NTFS Internals Subsystem."""

import os
from typing import Dict, Any, List, Optional
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import PlanStep, ActionCategory


class StorageNTFSSubsystem:
    """Manages low-level Windows storage: Disks, Partitions, Volumes, VHDs, Shadow Copies, and ACLs."""

    @classmethod
    def list_physical_disks(cls) -> PlanStep:
        """Enumerates physical disks with partition style, bus type, and health status."""
        return PlanStep(
            step_id="storage-disks-list",
            title="Enumerate Physical Storage Disks",
            category=ActionCategory.STORAGE,
            raw_intent="list disks",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=(
                "Get-Disk | Select-Object -Property Number,FriendlyName,OperationalStatus,"
                "HealthStatus,PartitionStyle,Size | ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "storage", "action": "list_disks"},
        )

    @classmethod
    def list_volumes(cls) -> PlanStep:
        """Lists filesystem volumes, drive letters, labels, and free space."""
        return PlanStep(
            step_id="storage-volumes-list",
            title="Inspect Filesystem Volumes and Free Space",
            category=ActionCategory.STORAGE,
            raw_intent="list volumes",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                "Get-Volume | Select-Object -Property DriveLetter,FileSystemLabel,FileSystem,"
                "DriveType,HealthStatus,SizeRemaining,Size | ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "storage", "action": "list_volumes"},
        )

    @classmethod
    def query_bitlocker_status(cls, drive_letter: str = "C:") -> PlanStep:
        """Inspects BitLocker encryption status, key protectors, and lock state."""
        return PlanStep(
            step_id=f"bitlocker-query-{drive_letter[0]}",
            title=f"Inspect BitLocker Encryption for {drive_letter}",
            category=ActionCategory.STORAGE,
            raw_intent=f"query bitlocker {drive_letter}",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=(
                f"Get-BitLockerVolume -MountPoint '{drive_letter}' | "
                f"Select-Object -Property MountPoint,VolumeStatus,EncryptionMethod,ProtectionStatus,LockStatus | "
                f"ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "storage", "drive": drive_letter},
        )

    @classmethod
    def list_shadow_copies(cls) -> PlanStep:
        """Enumerates Volume Shadow Copies (VSS snapshots)."""
        return PlanStep(
            step_id="storage-vss-list",
            title="Enumerate Volume Shadow Copies (VSS)",
            category=ActionCategory.STORAGE,
            raw_intent="list shadow copies",
            target_shell=ShellType.CMD,
            required_elevation=ElevationLevel.ADMIN,
            command="vssadmin list shadows",
            metadata={"subsystem": "storage", "action": "vss_list"},
        )

    @classmethod
    def create_symbolic_link(cls, link_path: str, target_path: str, is_directory: bool = False) -> PlanStep:
        """Creates an NTFS symbolic link or directory junction."""
        item_type = "SymbolicLink" if not is_directory else "Junction"
        return PlanStep(
            step_id="storage-symlink-create",
            title=f"Create NTFS {item_type}: {link_path} -> {target_path}",
            category=ActionCategory.STORAGE,
            raw_intent=f"create symlink {link_path} {target_path}",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN if item_type == "SymbolicLink" else ElevationLevel.STANDARD,
            command=f"New-Item -ItemType {item_type} -Path '{link_path}' -Target '{target_path}' -Force",
            metadata={"subsystem": "storage", "link": link_path, "target": target_path},
        )

    @classmethod
    def inspect_acls(cls, file_or_folder_path: str) -> PlanStep:
        """Retrieves exact NTFS Access Control List (ACL) permissions."""
        return PlanStep(
            step_id="storage-acl-inspect",
            title=f"Inspect NTFS ACLs for {file_or_folder_path}",
            category=ActionCategory.STORAGE,
            raw_intent=f"inspect acl {file_or_folder_path}",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                f"(Get-Acl -Path '{file_or_folder_path}').Access | "
                f"Select-Object -Property IdentityReference,FileSystemRights,AccessControlType,IsInherited | "
                f"ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "storage", "path": file_or_folder_path},
        )

    @classmethod
    def grant_full_control_acl(cls, target_path: str, identity: str = "Everyone") -> PlanStep:
        """Grants Full Control on a folder/file using icacls with inheritance."""
        return PlanStep(
            step_id="storage-acl-grant",
            title=f"Grant Full Control ACL on {target_path} to {identity}",
            category=ActionCategory.STORAGE,
            raw_intent=f"grant acl {identity} {target_path}",
            target_shell=ShellType.CMD,
            required_elevation=ElevationLevel.ADMIN,
            command=f'icacls "{target_path}" /grant "{identity}:(OI)(CI)F" /T /C /Q',
            metadata={"subsystem": "storage", "path": target_path, "identity": identity},
        )

    @classmethod
    def take_ownership(cls, target_path: str) -> PlanStep:
        """Recursively takes ownership of locked or access-denied filesystem objects."""
        return PlanStep(
            step_id="storage-takeown",
            title=f"Take Ownership of {target_path}",
            category=ActionCategory.STORAGE,
            raw_intent=f"take ownership {target_path}",
            target_shell=ShellType.CMD,
            required_elevation=ElevationLevel.ADMIN,
            command=f'takeown /F "{target_path}" /R /D Y',
            metadata={"subsystem": "storage", "path": target_path},
        )
