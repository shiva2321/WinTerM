"""Layer 0: Kernel, Boot, Power, Drivers & Firmware Subsystem."""

from typing import Dict, Any, List, Optional
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import PlanStep, ActionCategory


class KernelBootSubsystem:
    """Manages low-level Windows kernel, boot configuration (BCD), power schemes, drivers, and TPM."""

    @classmethod
    def query_boot_configuration(cls) -> PlanStep:
        """Queries the Windows Boot Configuration Data (BCD) store."""
        return PlanStep(
            step_id="boot-config-query",
            title="Inspect Windows Boot Configuration Data (BCD)",
            category=ActionCategory.SYSTEM,
            raw_intent="query bcd",
            target_shell=ShellType.CMD,
            required_elevation=ElevationLevel.ADMIN,
            command="bcdedit /enum {current}",
            metadata={"subsystem": "kernel_boot", "action": "bcd_query"},
        )

    @classmethod
    def query_power_schemes(cls) -> PlanStep:
        """Lists active and available Windows power schemes and sleep states."""
        return PlanStep(
            step_id="power-schemes-query",
            title="Query Windows Power Schemes and Sleep Capabilities",
            category=ActionCategory.SYSTEM,
            raw_intent="query power schemes",
            target_shell=ShellType.CMD,
            command="powercfg /list && powercfg /availablesleepstates",
            metadata={"subsystem": "kernel_boot", "action": "powercfg_query"},
        )

    @classmethod
    def set_active_power_scheme(cls, scheme_guid: str) -> PlanStep:
        """Sets the active power scheme (e.g. High Performance or Balanced)."""
        return PlanStep(
            step_id=f"power-scheme-set-{scheme_guid[:8]}",
            title=f"Set Active Power Scheme ({scheme_guid})",
            category=ActionCategory.SYSTEM,
            raw_intent=f"set power scheme {scheme_guid}",
            target_shell=ShellType.CMD,
            required_elevation=ElevationLevel.ADMIN,
            command=f"powercfg /setactive {scheme_guid}",
            metadata={"subsystem": "kernel_boot", "scheme_guid": scheme_guid},
        )

    @classmethod
    def query_installed_drivers(cls, driver_class: Optional[str] = None) -> PlanStep:
        """Queries 3rd-party and OEM device drivers via pnputil."""
        cmd = "pnputil /enum-drivers"
        if driver_class:
            cmd += f" /class {driver_class}"
        return PlanStep(
            step_id="drivers-query",
            title="Enumerate Third-Party Drivers via PnPUtil",
            category=ActionCategory.DIAGNOSTIC,
            raw_intent="query drivers",
            target_shell=ShellType.CMD,
            command=cmd,
            metadata={"subsystem": "kernel_boot", "action": "driver_query"},
        )

    @classmethod
    def query_tpm_status(cls) -> PlanStep:
        """Queries the hardware Trusted Platform Module (TPM) chip status."""
        return PlanStep(
            step_id="tpm-status-query",
            title="Inspect Hardware TPM Security Status",
            category=ActionCategory.SECURITY,
            raw_intent="query tpm",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command="Get-Tpm | Select-Object -Property TpmPresent,TpmReady,TpmEnabled,TpmActivated,ManufacturerIdTxt | ConvertTo-Json",
            metadata={"subsystem": "kernel_boot", "action": "tpm_query"},
        )

    @classmethod
    def query_uefi_firmware_type(cls) -> PlanStep:
        """Determines whether the system booted via UEFI or Legacy BIOS."""
        return PlanStep(
            step_id="firmware-type-query",
            title="Inspect Firmware Boot Mode (UEFI vs BIOS)",
            category=ActionCategory.DIAGNOSTIC,
            raw_intent="query firmware type",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                "$pe = $env:PEFirmwareType; "
                "if (-not $pe) { $pe = (Get-CimInstance -ClassName Win32_ComputerSystem).SystemType }; "
                "[PSCustomObject]@{ Firmware = $pe; SecureBoot = (Confirm-SecureBootUEFI -ErrorAction SilentlyContinue) } | ConvertTo-Json"
            ),
            metadata={"subsystem": "kernel_boot", "action": "firmware_query"},
        )
