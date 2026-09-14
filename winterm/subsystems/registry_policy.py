"""Layer 4: Windows Registry Hives, Data Types & Group Policy Subsystem."""

from typing import Dict, Any, List, Optional
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import PlanStep, ActionCategory


class RegistryPolicySubsystem:
    """Manages low-level Windows Registry (HKLM, HKCU, HKCR, HKU), typed values, and Group Policy."""

    VALID_REG_TYPES = ["String", "ExpandString", "Binary", "DWord", "MultiString", "QWord"]

    @classmethod
    def set_typed_registry_value(
        cls,
        path: str,
        name: str,
        value: Any,
        prop_type: str = "DWord",
    ) -> PlanStep:
        """Sets a strictly-typed registry property (DWord, QWord, String, etc.)."""
        reg_type = prop_type if prop_type in cls.VALID_REG_TYPES else "DWord"
        requires_admin = "hklm" in path.lower() or "hkey_local_machine" in path.lower()
        return PlanStep(
            step_id=f"reg-set-{name}",
            title=f"Set Registry [{path}] {name}={value} ({reg_type})",
            category=ActionCategory.REGISTRY,
            raw_intent=f"set registry {path} {name}",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN if requires_admin else ElevationLevel.STANDARD,
            command=(
                f"if (-not (Test-Path '{path}')) {{ New-Item -Path '{path}' -Force | Out-Null }}; "
                f"Set-ItemProperty -Path '{path}' -Name '{name}' -Value {value} -Type {reg_type} -Force"
            ),
            metadata={"subsystem": "registry_policy", "path": path, "name": name, "type": reg_type},
        )

    @classmethod
    def query_registry_tree(cls, path: str) -> PlanStep:
        """Recursively queries a registry key and all child values."""
        return PlanStep(
            step_id="reg-tree-query",
            title=f"Inspect Registry Subtree: {path}",
            category=ActionCategory.REGISTRY,
            raw_intent=f"query registry tree {path}",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                f"Get-ItemProperty -Path '{path}' -ErrorAction Stop | "
                f"Select-Object -Property * -ExcludeProperty PSPath,PSParentPath,PSChildName,PSDrive,PSProvider | "
                f"ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "registry_policy", "path": path},
        )

    @classmethod
    def force_group_policy_update(cls) -> PlanStep:
        """Forces an immediate synchronization and refresh of Windows Group Policy settings."""
        return PlanStep(
            step_id="gpupdate-force",
            title="Force Windows Group Policy Synchronization (gpupdate /force)",
            category=ActionCategory.SYSTEM,
            raw_intent="force group policy update",
            target_shell=ShellType.CMD,
            command="gpupdate /force",
            metadata={"subsystem": "registry_policy", "action": "gpupdate"},
        )

    @classmethod
    def generate_policy_result_summary(cls) -> PlanStep:
        """Summarizes applied computer and user Group Policy objects via gpresult."""
        return PlanStep(
            step_id="gpresult-summary",
            title="Inspect Applied Group Policy Objects (gpresult /r)",
            category=ActionCategory.DIAGNOSTIC,
            raw_intent="query applied group policies",
            target_shell=ShellType.CMD,
            command="gpresult /r",
            metadata={"subsystem": "registry_policy", "action": "gpresult"},
        )
