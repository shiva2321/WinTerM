"""Windows Command Ontology: Database of commands, modern alternatives, and recipes."""

from typing import Dict, Any, List, Optional
from winterm.models.intent import ActionCategory
from winterm.models.context import ShellType, ElevationLevel


class CommandTemplate:
    """Represents a canonical Windows command recipe with metadata and rationale."""

    def __init__(
        self,
        intent_key: str,
        category: ActionCategory,
        powershell_template: str,
        cmd_template: Optional[str] = None,
        elevation: ElevationLevel = ElevationLevel.STANDARD,
        why: str = "",
        modern_alternative_to: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        flags_explained: Optional[Dict[str, str]] = None,
    ):
        self.intent_key = intent_key
        self.category = category
        self.powershell_template = powershell_template
        self.cmd_template = cmd_template
        self.elevation = elevation
        self.why = why
        self.modern_alternative_to = modern_alternative_to
        self.rejection_reason = rejection_reason
        self.flags_explained = flags_explained or {}


class WindowsCommandDatabase:
    """Catalog of canonical Windows commands across all major subsystems."""

    CATALOG: Dict[str, CommandTemplate] = {
        # --- PROCESS MANAGEMENT ---
        "find_process_by_port": CommandTemplate(
            intent_key="find_process_by_port",
            category=ActionCategory.PROCESS,
            powershell_template=(
                "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
                "Select-Object -Property LocalAddress,LocalPort,OwningProcess,State | "
                "ForEach-Object {{ $proc = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
                "[PSCustomObject]@{{ Port = $_.LocalPort; PID = $_.OwningProcess; Name = $proc.ProcessName; Path = $proc.Path }} }} | "
                "ConvertTo-Json -Depth 5"
            ),
            cmd_template="netstat -ano | findstr :{port}",
            why="Get-NetTCPConnection directly returns typed objects linking port to PID without brittle text parsing.",
            modern_alternative_to="netstat -ano | findstr",
            rejection_reason="Parsing netstat requires regex/token splitting and cannot resolve process names directly.",
        ),
        "kill_process_by_pid": CommandTemplate(
            intent_key="kill_process_by_pid",
            category=ActionCategory.PROCESS,
            powershell_template="Stop-Process -Id {pid} -Force -ErrorAction Stop",
            cmd_template="taskkill /F /PID {pid}",
            why="Stop-Process -Force cleanly terminates the target PID and reports errors through standard exception channels.",
            flags_explained={"-Force": "Overrides confirmation prompts and terminates unresponsive processes."},
        ),
        "kill_process_by_name": CommandTemplate(
            intent_key="kill_process_by_name",
            category=ActionCategory.PROCESS,
            powershell_template="Get-Process -Name '{name}' -ErrorAction SilentlyContinue | Stop-Process -Force",
            cmd_template="taskkill /F /IM {name}.exe",
            why="Pipes filtered processes into Stop-Process, gracefully ignoring if none are currently running.",
            flags_explained={"-Force": "Suppresses prompts and terminates all matching instances."},
        ),
        "list_top_memory_processes": CommandTemplate(
            intent_key="list_top_memory_processes",
            category=ActionCategory.PROCESS,
            powershell_template=(
                "Get-Process | Sort-Object -Property WorkingSet64 -Descending | "
                "Select-Object -First {count} -Property Id,ProcessName,@{{Name='MemoryMB';Expression={{[math]::Round($_.WorkingSet64 / 1MB, 2) }}}} | "
                "ConvertTo-Json -Depth 5"
            ),
            cmd_template="tasklist /FI \"MEMUSAGE gt 100000\"",
            why="Get-Process returns rich memory metrics (WorkingSet64) with precise sorting and JSON serialization.",
        ),

        # --- SERVICES ---
        "get_service_status": CommandTemplate(
            intent_key="get_service_status",
            category=ActionCategory.SERVICE,
            powershell_template="Get-Service -Name '{service_name}' | Select-Object -Property Name,DisplayName,Status,StartType | ConvertTo-Json -Depth 5",
            cmd_template="sc.exe query {service_name}",
            why="Get-Service provides structured status and startup configuration directly.",
        ),
        "restart_service": CommandTemplate(
            intent_key="restart_service",
            category=ActionCategory.SERVICE,
            powershell_template="Restart-Service -Name '{service_name}' -Force",
            cmd_template="net stop {service_name} && net start {service_name}",
            elevation=ElevationLevel.ADMIN,
            why="Restart-Service handles stop and start atomically with dependency resolution.",
            flags_explained={"-Force": "Restarts even if dependent services are present."},
        ),

        # --- NETWORKING ---
        "test_port_connectivity": CommandTemplate(
            intent_key="test_port_connectivity",
            category=ActionCategory.NETWORK,
            powershell_template="Test-NetConnection -ComputerName '{host}' -Port {port} -WarningAction SilentlyContinue | Select-Object -Property ComputerName,RemotePort,TcpTestSucceeded | ConvertTo-Json",
            why="Test-NetConnection performs an actual TCP handshake, unlike ping which only tests ICMP.",
            modern_alternative_to="telnet / ping",
            rejection_reason="Telnet is disabled by default on modern Windows; Ping only checks ICMP echo, not port accessibility.",
        ),
        "get_active_ip_adapters": CommandTemplate(
            intent_key="get_active_ip_adapters",
            category=ActionCategory.NETWORK,
            powershell_template="Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' } | Select-Object -Property InterfaceAlias,IPAddress,IPv4Address | ConvertTo-Json -Depth 5",
            cmd_template="ipconfig",
            why="Get-NetIPAddress provides structured filtering for active IPv4 interfaces without screen scraping ipconfig.",
        ),

        # --- REGISTRY ---
        "get_registry_value": CommandTemplate(
            intent_key="get_registry_value",
            category=ActionCategory.REGISTRY,
            powershell_template="Get-ItemProperty -Path '{path}' -Name '{name}' -ErrorAction Stop | Select-Object -Property '{name}' | ConvertTo-Json",
            cmd_template="reg query \"{path}\" /v \"{name}\"",
            why="Get-ItemProperty integrates registry hives as native PowerShell filesystem drives.",
        ),
        "set_registry_value": CommandTemplate(
            intent_key="set_registry_value",
            category=ActionCategory.REGISTRY,
            powershell_template="Set-ItemProperty -Path '{path}' -Name '{name}' -Value '{value}' -Force",
            cmd_template="reg add \"{path}\" /v \"{name}\" /d \"{value}\" /f",
            elevation=ElevationLevel.ADMIN,
            why="Set-ItemProperty creates or updates registry properties safely within .NET types.",
        ),

        # --- ENVIRONMENT VARIABLES ---
        "set_persistent_env_var": CommandTemplate(
            intent_key="set_persistent_env_var",
            category=ActionCategory.ENVIRONMENT,
            powershell_template="[Environment]::SetEnvironmentVariable('{name}', '{value}', '{target}')",
            cmd_template="setx {name} \"{value}\"",
            why="[Environment]::SetEnvironmentVariable directly persists variables to User or Machine registry scopes.",
            flags_explained={"target": "'User' or 'Machine' persistence scope"},
        ),

        # --- FILESYSTEM ---
        "safe_delete_directory": CommandTemplate(
            intent_key="safe_delete_directory",
            category=ActionCategory.FILESYSTEM,
            powershell_template="if (Test-Path '{path}') {{ Remove-Item -Path '{path}' -Recurse -Force -Confirm:$false }}",
            cmd_template="if exist \"{path}\" rmdir /s /q \"{path}\"",
            why="Guards existence with Test-Path first to prevent error throwing on non-existent targets.",
            flags_explained={
                "-Recurse": "Recursively deletes subdirectories and files.",
                "-Force": "Deletes read-only or hidden items.",
                "-Confirm:$false": "Suppresses interactive prompt.",
            },
        ),
        "robust_copy": CommandTemplate(
            intent_key="robust_copy",
            category=ActionCategory.FILESYSTEM,
            powershell_template="robocopy '{source}' '{destination}' /E /Z /R:2 /W:3 /NP /NDL",
            why="Robocopy is the gold standard on Windows for multi-threaded, resilient copying with automatic retry on locked files.",
            modern_alternative_to="Copy-Item / xcopy",
            rejection_reason="Copy-Item can fail silently on deep folder structures and lacks retry mechanisms for locked files.",
        ),

        # --- WMI VS CIM ---
        "query_system_hardware": CommandTemplate(
            intent_key="query_system_hardware",
            category=ActionCategory.DIAGNOSTIC,
            powershell_template="Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object -Property Manufacturer,Model,TotalPhysicalMemory | ConvertTo-Json",
            why="Get-CimInstance uses modern WSMAN (WS-Management) standards and is supported in both PS 5.1 and PS 7+.",
            modern_alternative_to="Get-WmiObject",
            rejection_reason="Get-WmiObject is deprecated and completely removed in PowerShell 7+.",
        ),

        # --- LAYER 0: KERNEL & BOOT ---
        "query_boot_configuration": CommandTemplate(
            intent_key="query_boot_configuration",
            category=ActionCategory.SYSTEM,
            powershell_template="bcdedit.exe /enum '{current}'",
            cmd_template="bcdedit.exe /enum {current}",
            elevation=ElevationLevel.ADMIN,
            why="bcdedit directly inspects the Windows Boot Configuration Data (BCD) firmware store.",
        ),
        "query_power_schemes": CommandTemplate(
            intent_key="query_power_schemes",
            category=ActionCategory.SYSTEM,
            powershell_template="powercfg.exe /list",
            cmd_template="powercfg /list",
            why="powercfg enumerates ACPI power plans and sleep state capabilities directly from kernel driver.",
        ),
        "query_tpm_status": CommandTemplate(
            intent_key="query_tpm_status",
            category=ActionCategory.SECURITY,
            powershell_template="Get-Tpm | Select-Object -Property TpmPresent,TpmReady,TpmEnabled,TpmActivated | ConvertTo-Json",
            elevation=ElevationLevel.ADMIN,
            why="Get-Tpm accesses the hardware security crypto-processor status directly.",
        ),

        # --- LAYER 1: STORAGE & NTFS ---
        "list_physical_disks": CommandTemplate(
            intent_key="list_physical_disks",
            category=ActionCategory.STORAGE,
            powershell_template="Get-Disk | Select-Object -Property Number,FriendlyName,OperationalStatus,HealthStatus,PartitionStyle,Size | ConvertTo-Json -Depth 5",
            elevation=ElevationLevel.ADMIN,
            why="Get-Disk provides structured hardware partition style and health metrics.",
        ),
        "list_volumes": CommandTemplate(
            intent_key="list_volumes",
            category=ActionCategory.STORAGE,
            powershell_template="Get-Volume | Select-Object -Property DriveLetter,FileSystemLabel,FileSystem,HealthStatus,SizeRemaining,Size | ConvertTo-Json -Depth 5",
            why="Get-Volume retrieves filesystem metadata and capacity without screen-scraping diskpart.",
        ),
        "query_bitlocker_status": CommandTemplate(
            intent_key="query_bitlocker_status",
            category=ActionCategory.STORAGE,
            powershell_template="Get-BitLockerVolume -MountPoint 'C:' | Select-Object -Property MountPoint,VolumeStatus,ProtectionStatus,LockStatus | ConvertTo-Json -Depth 5",
            elevation=ElevationLevel.ADMIN,
            why="Get-BitLockerVolume reports full-disk encryption and key protector status.",
        ),
        "list_shadow_copies": CommandTemplate(
            intent_key="list_shadow_copies",
            category=ActionCategory.STORAGE,
            powershell_template="vssadmin.exe list shadows",
            cmd_template="vssadmin list shadows",
            elevation=ElevationLevel.ADMIN,
            why="vssadmin queries Volume Shadow Copies for point-in-time snapshot recovery.",
        ),
        "inspect_acls": CommandTemplate(
            intent_key="inspect_acls",
            category=ActionCategory.STORAGE,
            powershell_template="(Get-Acl -Path '{path}').Access | Select-Object -Property IdentityReference,FileSystemRights,AccessControlType | ConvertTo-Json -Depth 5",
            why="Get-Acl parses Windows Security Descriptors (DACLs) into structured authorization entries.",
            modern_alternative_to="icacls text parsing",
            rejection_reason="icacls outputs SDDL shorthand text that is error-prone for agents to interpret.",
        ),

        # --- LAYER 2: PROCESS & MEMORY ---
        "inspect_loaded_modules": CommandTemplate(
            intent_key="inspect_loaded_modules",
            category=ActionCategory.PROCESS,
            powershell_template="(Get-Process -Id {pid}).Modules | Select-Object -Property ModuleName,FileName,Size | ConvertTo-Json -Depth 5",
            why="Accesses process PEB (Process Environment Block) to inspect loaded DLLs.",
        ),

        # --- LAYER 3: SERVICES & TASKS ---
        "configure_service_recovery": CommandTemplate(
            intent_key="configure_service_recovery",
            category=ActionCategory.SERVICE,
            powershell_template="sc.exe failure '{service_name}' reset= 86400 actions= restart/5000/restart/10000/restart/60000",
            elevation=ElevationLevel.ADMIN,
            why="sc.exe failure directly configures the SCM service failure actions table.",
        ),
        "list_scheduled_tasks": CommandTemplate(
            intent_key="list_scheduled_tasks",
            category=ActionCategory.SYSTEM,
            powershell_template="Get-ScheduledTask | Select-Object -First 30 -Property TaskName,TaskPath,State | ConvertTo-Json -Depth 5",
            why="Get-ScheduledTask provides structured Task Scheduler V2 COM integration.",
        ),

        # --- LAYER 5: SECURITY & CRYPTO ---
        "audit_user_privileges": CommandTemplate(
            intent_key="audit_user_privileges",
            category=ActionCategory.SECURITY,
            powershell_template="whoami.exe /priv",
            cmd_template="whoami /priv",
            why="whoami /priv lists active user token privileges (e.g. SeDebugPrivilege).",
        ),
        "list_local_users": CommandTemplate(
            intent_key="list_local_users",
            category=ActionCategory.SECURITY,
            powershell_template="Get-LocalUser | Select-Object -Property Name,Enabled,LastLogon | ConvertTo-Json -Depth 5",
            elevation=ElevationLevel.ADMIN,
            why="Get-LocalUser queries the SAM database safely via PowerShell without NetUser API wrappers.",
        ),
        "list_certificates": CommandTemplate(
            intent_key="list_certificates",
            category=ActionCategory.SECURITY,
            powershell_template="Get-ChildItem -Path 'Cert:\\LocalMachine\\My' -ErrorAction SilentlyContinue | Select-Object -Property Subject,Thumbprint,NotAfter | ConvertTo-Json -Depth 5",
            why="PowerShell Certificate Provider exposes the Windows CryptoAPI certificate store as a native drive.",
        ),
        "query_defender_status": CommandTemplate(
            intent_key="query_defender_status",
            category=ActionCategory.SECURITY,
            powershell_template="Get-MpComputerStatus | Select-Object -Property AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureLastUpdated | ConvertTo-Json",
            elevation=ElevationLevel.ADMIN,
            why="Get-MpComputerStatus queries Defender engine and real-time security state.",
        ),

        # --- LAYER 6: NETWORK & FIREWALL ---
        "list_network_adapters": CommandTemplate(
            intent_key="list_network_adapters",
            category=ActionCategory.NETWORK,
            powershell_template="Get-NetAdapter | Select-Object -Property Name,Status,LinkSpeed,MacAddress | ConvertTo-Json -Depth 5",
            why="Get-NetAdapter provides hardware physical and virtual NIC attributes directly.",
        ),
        "flush_dns_cache": CommandTemplate(
            intent_key="flush_dns_cache",
            category=ActionCategory.NETWORK,
            powershell_template="Clear-DnsClientCache",
            cmd_template="ipconfig /flushdns",
            why="Clear-DnsClientCache purges the local DNS resolver cache.",
        ),

        # --- LAYER 7: DIAGNOSTICS & HEALTH ---
        "query_event_log_errors": CommandTemplate(
            intent_key="query_event_log_errors",
            category=ActionCategory.DIAGNOSTIC,
            powershell_template="Get-WinEvent -FilterHashtable @{{ LogName = 'System'; Level = 1, 2 }} -MaxEvents 10 -ErrorAction SilentlyContinue | Select-Object -Property TimeCreated,Id,ProviderName,Message | ConvertTo-Json -Depth 5",
            why="Get-WinEvent uses high-performance ETW (Event Tracing for Windows) log queries.",
        ),
        "sample_performance_counters": CommandTemplate(
            intent_key="sample_performance_counters",
            category=ActionCategory.DIAGNOSTIC,
            powershell_template="Get-Counter -Counter @('\\Processor(_Total)\\% Processor Time', '\\Memory\\Available MBytes') -MaxSamples 1 | Select-Object -ExpandProperty CounterSamples | Select-Object -Property Path,CookedValue | ConvertTo-Json -Depth 5",
            why="Get-Counter accesses Windows Kernel Performance Counter APIs.",
        ),

        # --- LAYER 8: VIRTUALIZATION & PACKAGES ---
        "list_wsl_distros": CommandTemplate(
            intent_key="list_wsl_distros",
            category=ActionCategory.VIRTUALIZATION,
            powershell_template="wsl.exe --list --verbose",
            cmd_template="wsl.exe --list --verbose",
            why="wsl.exe provides Linux virtualization status, WSL version (1 vs 2), and active distros.",
        ),
        "list_hyperv_vms": CommandTemplate(
            intent_key="list_hyperv_vms",
            category=ActionCategory.VIRTUALIZATION,
            powershell_template="Get-VM -ErrorAction SilentlyContinue | Select-Object -Property Name,State,CPUUsage,MemoryAssigned | ConvertTo-Json -Depth 5",
            elevation=ElevationLevel.ADMIN,
            why="Get-VM queries the Hyper-V hypervisor WMI provider for virtual machines.",
        ),
        "winget_upgrade_all": CommandTemplate(
            intent_key="winget_upgrade_all",
            category=ActionCategory.PACKAGE,
            powershell_template="winget.exe upgrade --all --include-unknown --accept-source-agreements --accept-package-agreements --disable-interactivity",
            cmd_template="winget.exe upgrade --all --include-unknown --accept-source-agreements --accept-package-agreements --disable-interactivity",
            why="Automates system-wide software updates via official Windows Package Manager.",
        ),
    }

    @classmethod
    def get_template(cls, intent_key: str) -> Optional[CommandTemplate]:
        """Retrieves a command template by intent key."""
        return cls.CATALOG.get(intent_key)

    @classmethod
    def find_by_category(cls, category: ActionCategory) -> List[CommandTemplate]:
        """Finds all commands within a subsystem category."""
        return [cmd for cmd in cls.CATALOG.values() if cmd.category == category]
