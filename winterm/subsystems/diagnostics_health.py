"""Layer 7: Diagnostics, Event Logging, Performance Counters & OS Health Subsystem."""

from typing import Dict, Any, List, Optional
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import PlanStep, ActionCategory


class DiagnosticsHealthSubsystem:
    """Manages Windows Event Logs (ETW/wevtutil), Performance Counters, SFC, and DISM servicing."""

    @classmethod
    def query_recent_system_errors(cls, max_events: int = 15) -> PlanStep:
        """Queries critical and error level events from the Windows System Event Log via Get-WinEvent."""
        return PlanStep(
            step_id="diag-eventlog-errors",
            title=f"Query Top {max_events} Recent System Event Log Errors",
            category=ActionCategory.DIAGNOSTIC,
            raw_intent="query system errors",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                f"Get-WinEvent -FilterHashtable @{{ LogName = 'System'; Level = 1, 2 }} -MaxEvents {max_events} -ErrorAction SilentlyContinue | "
                f"Select-Object -Property TimeCreated,Id,ProviderName,Message | "
                f"ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "diagnostics_health", "max_events": max_events},
        )

    @classmethod
    def query_live_performance_metrics(cls) -> PlanStep:
        """Samples real-time CPU, Memory, and Disk performance counters."""
        return PlanStep(
            step_id="diag-perf-counters",
            title="Sample Real-Time Windows Performance Counters",
            category=ActionCategory.DIAGNOSTIC,
            raw_intent="query performance counters",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                "Get-Counter -Counter @("
                "'\\Processor(_Total)\\% Processor Time',"
                "'\\Memory\\Available MBytes',"
                "'\\PhysicalDisk(_Total)\\% Disk Time'"
                ") -SampleInterval 1 -MaxSamples 1 | "
                "Select-Object -ExpandProperty CounterSamples | "
                "Select-Object -Property Path,CookedValue | ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "diagnostics_health", "action": "perf_sample"},
        )

    @classmethod
    def scan_system_file_integrity(cls) -> PlanStep:
        """Executes Windows System File Checker (sfc /scannow) to verify and repair corrupted OS files."""
        return PlanStep(
            step_id="diag-sfc-scannow",
            title="Scan and Repair Windows System Files (sfc /scannow)",
            category=ActionCategory.SYSTEM,
            raw_intent="scan system file integrity",
            target_shell=ShellType.CMD,
            required_elevation=ElevationLevel.ADMIN,
            timeout_seconds=600,
            command="sfc /scannow",
            metadata={"subsystem": "diagnostics_health", "action": "sfc"},
        )

    @classmethod
    def dism_health_check(cls) -> PlanStep:
        """Checks the Windows Component Store for corruption via DISM."""
        return PlanStep(
            step_id="diag-dism-checkhealth",
            title="Check Windows Component Store Health (DISM /CheckHealth)",
            category=ActionCategory.SYSTEM,
            raw_intent="check component store health",
            target_shell=ShellType.CMD,
            required_elevation=ElevationLevel.ADMIN,
            command="dism.exe /Online /Cleanup-Image /CheckHealth",
            metadata={"subsystem": "diagnostics_health", "action": "dism_check"},
        )

    @classmethod
    def query_reliability_history(cls, count: int = 10) -> PlanStep:
        """Queries Windows Reliability Monitor crash and hang history records via CIM."""
        return PlanStep(
            step_id="diag-reliability-records",
            title=f"Query Last {count} Windows Reliability Stability Records",
            category=ActionCategory.DIAGNOSTIC,
            raw_intent="query reliability records",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                f"Get-CimInstance -ClassName Win32_ReliabilityRecords -ErrorAction SilentlyContinue | "
                f"Select-Object -First {count} -Property TimeGenerated,EventIdentifier,ProductName,Message | "
                f"ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "diagnostics_health", "count": count},
        )

    @classmethod
    def audit_audio_services(cls) -> PlanStep:
        """Probes Windows Audio (Audiosrv) and Audio Endpoint Builder (AudioEndpointBuilder) service health."""
        return PlanStep(
            step_id="audio-svc-audit",
            title="Inspect Windows Audio Services Health & Startup Status",
            category=ActionCategory.SERVICE,
            raw_intent="check audio services",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                "Get-Service -Name AudioEndpointBuilder, Audiosrv -ErrorAction SilentlyContinue | "
                "Select-Object Name, DisplayName, Status, StartType | ConvertTo-Json -Compress"
            ),
            metadata={"subsystem": "diagnostics_health", "component": "audio_services"},
        )

    @classmethod
    def probe_sound_hardware(cls) -> PlanStep:
        """Queries sound controllers and multimedia hardware devices via CIM Win32_SoundDevice."""
        return PlanStep(
            step_id="audio-hw-probe",
            title="Probe Sound Controllers and Hardware Devices via CIM",
            category=ActionCategory.DIAGNOSTIC,
            raw_intent="probe sound hardware",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                "Get-CimInstance Win32_SoundDevice -ErrorAction SilentlyContinue | "
                "Select-Object Name, Manufacturer, Status, DeviceID | ConvertTo-Json -Compress"
            ),
            metadata={"subsystem": "diagnostics_health", "component": "sound_hardware"},
        )

    @classmethod
    def audit_pnp_media_devices(cls) -> PlanStep:
        """Enumerates Media class PnP devices to detect driver issues or device manager error codes."""
        return PlanStep(
            step_id="audio-pnp-audit",
            title="Audit Media PnP Devices and Driver Problem Codes",
            category=ActionCategory.DIAGNOSTIC,
            raw_intent="check audio pnp devices",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                "Get-PnpDevice -Class Media -ErrorAction SilentlyContinue | "
                "Select-Object -First 10 FriendlyName, Status, ConfigManagerErrorCode | ConvertTo-Json -Compress"
            ),
            metadata={"subsystem": "diagnostics_health", "component": "pnp_media"},
        )

    @classmethod
    def query_audio_event_logs(cls, max_events: int = 10) -> PlanStep:
        """Queries Windows System event log for recent critical or error events."""
        return PlanStep(
            step_id="audio-eventlog-query",
            title=f"Query Recent System Event Log for Audio Driver and Service Faults",
            category=ActionCategory.DIAGNOSTIC,
            raw_intent="query audio error logs",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                f"Get-WinEvent -FilterHashtable @{{ LogName = 'System'; Level = 1, 2 }} -MaxEvents {max_events} -ErrorAction SilentlyContinue | "
                "Select-Object -First 5 TimeCreated, Id, ProviderName | ConvertTo-Json -Compress"
            ),
            metadata={"subsystem": "diagnostics_health", "component": "audio_eventlog"},
        )
