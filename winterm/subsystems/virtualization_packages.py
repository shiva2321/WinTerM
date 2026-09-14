"""Layer 8: Virtualization (WSL / Hyper-V), Windows Features & Package Management Subsystem."""

from typing import Dict, Any, List, Optional
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import PlanStep, ActionCategory


class VirtualizationPackagesSubsystem:
    """Manages WSL distributions, Hyper-V VMs, Windows Optional Features, and package managers (Winget/Choco)."""

    @classmethod
    def list_wsl_distributions(cls) -> PlanStep:
        """Enumerates installed WSL distributions, running states, and WSL versions."""
        return PlanStep(
            step_id="virt-wsl-list",
            title="Enumerate WSL Linux Distributions and States",
            category=ActionCategory.VIRTUALIZATION,
            raw_intent="list wsl distros",
            target_shell=ShellType.CMD,
            command="wsl.exe --list --verbose",
            metadata={"subsystem": "virtualization", "action": "wsl_list"},
        )

    @classmethod
    def shutdown_wsl(cls) -> PlanStep:
        """Immediately terminates all running WSL distributions and frees virtual memory."""
        return PlanStep(
            step_id="virt-wsl-shutdown",
            title="Shutdown All Running WSL Distributions",
            category=ActionCategory.VIRTUALIZATION,
            raw_intent="shutdown wsl",
            target_shell=ShellType.CMD,
            command="wsl.exe --shutdown",
            metadata={"subsystem": "virtualization", "action": "wsl_shutdown"},
        )

    @classmethod
    def list_hyperv_vms(cls) -> PlanStep:
        """Lists Hyper-V virtual machines, states, CPU usage, and assigned RAM."""
        return PlanStep(
            step_id="virt-hyperv-vms-list",
            title="Enumerate Hyper-V Virtual Machines",
            category=ActionCategory.VIRTUALIZATION,
            raw_intent="list hyperv vms",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=(
                "Get-VM -ErrorAction SilentlyContinue | "
                "Select-Object -Property Name,State,CPUUsage,MemoryAssigned,Uptime | "
                "ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "virtualization", "action": "hyperv_list"},
        )

    @classmethod
    def query_windows_optional_features(cls, filter_name: Optional[str] = None) -> PlanStep:
        """Queries Windows optional features (e.g. Hyper-V, Containers, TelnetClient, Sandbox)."""
        cmd = "Get-WindowsOptionalFeature -Online"
        if filter_name:
            cmd += f" -FeatureName '*{filter_name}*'"
        cmd += " | Select-Object -Property FeatureName,State | ConvertTo-Json -Depth 5"
        return PlanStep(
            step_id="virt-features-query",
            title="Inspect Windows Optional Features State",
            category=ActionCategory.SYSTEM,
            raw_intent="query optional features",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=cmd,
            metadata={"subsystem": "virtualization", "filter": filter_name},
        )

    @classmethod
    def winget_install(cls, package_id: str) -> PlanStep:
        """Installs software via Windows Package Manager (winget) silently with agreement acceptance."""
        return PlanStep(
            step_id=f"pkg-winget-install-{package_id.replace('.', '_')}",
            title=f"Install Package via Winget: {package_id}",
            category=ActionCategory.PACKAGE,
            raw_intent=f"winget install {package_id}",
            target_shell=ShellType.CMD,
            timeout_seconds=300,
            command=(
                f"winget.exe install --exact --id {package_id} "
                "--accept-source-agreements --accept-package-agreements --disable-interactivity"
            ),
            metadata={"subsystem": "packages", "package_id": package_id},
        )

    @classmethod
    def winget_upgrade_all(cls) -> PlanStep:
        """Upgrades all installed applications that have newer versions available via winget."""
        return PlanStep(
            step_id="pkg-winget-upgrade-all",
            title="Upgrade All Installed Applications via Winget",
            category=ActionCategory.PACKAGE,
            raw_intent="winget upgrade all",
            target_shell=ShellType.CMD,
            timeout_seconds=600,
            command=(
                "winget.exe upgrade --all --include-unknown "
                "--accept-source-agreements --accept-package-agreements --disable-interactivity"
            ),
            metadata={"subsystem": "packages", "action": "upgrade_all"},
        )
