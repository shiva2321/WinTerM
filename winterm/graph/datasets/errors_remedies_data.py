"""Factual Windows Error Catalog & Multi-Step Remediation Dataset: HRESULT, Win32, and exceptions."""

from typing import Dict, Any, List

# Factual Windows error codes mapped to causes, required privileges, and multi-step remediation commands
ERRORS_REMEDIES_DATA: Dict[str, Dict[str, Any]] = {
    "0x80070005": {
        "symbol": "E_ACCESSDENIED",
        "win32_code": 5,
        "name": "Access is denied",
        "subsystem": "SecurityCrypto",
        "description": "The active user token lacks the necessary discretionary access control list (DACL) permissions or requires elevated Administrator privileges.",
        "requires_privilege": "Administrator",
        "contributing_factors": [
            "Process executed in unelevated (standard user) shell context",
            "Target file or registry key owned by TrustedInstaller or SYSTEM",
            "Inherited NTFS permissions deny access to current principal",
        ],
        "remediation_chain": [
            {
                "step": 1,
                "action": "Check shell elevation level",
                "command": "([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)",
                "expected": "True",
            },
            {
                "step": 2,
                "action": "Relaunch with administrative elevation if unelevated",
                "command": "Start-Process powershell.exe -Verb RunAs",
                "condition": "If step 1 is False",
            },
            {
                "step": 3,
                "action": "Take file ownership and grant FullControl if target is file/directory",
                "command": "takeown /F '{target}' /A ; icacls '{target}' /grant 'Administrators:F'",
                "condition": "If file ACL is restricted",
            },
        ],
    },
    "0x80070020": {
        "symbol": "ERROR_SHARING_VIOLATION",
        "win32_code": 32,
        "name": "The process cannot access the file because it is being used by another process",
        "subsystem": "StorageNTFS",
        "description": "An exclusive lock or read/write share conflict is held on the target file handle by another active process.",
        "requires_privilege": "StandardUser",
        "contributing_factors": [
            "File opened with FILE_SHARE_READ only while write is attempted",
            "Anti-virus scanning process holds active handle",
            "Previous instance of application did not terminate cleanly",
        ],
        "remediation_chain": [
            {
                "step": 1,
                "action": "Locate process holding open file lock",
                "command": "$locked = '{target}'; Get-Process | Where-Object { try { $_.Modules.FileName -contains $locked } catch { $false } } | Select-Object Id, ProcessName",
            },
            {
                "step": 2,
                "action": "Terminate locking process with force",
                "command": "Stop-Process -Id {pid} -Force",
            },
            {
                "step": 3,
                "action": "Verify file availability",
                "command": "Test-Path -Path '{target}'",
                "expected": "True",
            },
        ],
    },
    "0x80070422": {
        "symbol": "ERROR_SERVICE_DISABLED",
        "win32_code": 1058,
        "name": "The service cannot be started, either because it is disabled or because it has no enabled devices associated with it",
        "subsystem": "ServicesTasks",
        "description": "The target Windows service's StartType in the Service Control Manager is set to Disabled (4), preventing startup requests.",
        "requires_privilege": "Administrator",
        "contributing_factors": [
            "Service disabled manually or by hardening Group Policy",
            "Dependency service is disabled",
        ],
        "remediation_chain": [
            {
                "step": 1,
                "action": "Change service startup type to Automatic",
                "command": "Set-Service -Name '{service}' -StartupType Automatic",
            },
            {
                "step": 2,
                "action": "Start the service",
                "command": "Start-Service -Name '{service}'",
            },
            {
                "step": 3,
                "action": "Verify service state is Running",
                "command": "(Get-Service -Name '{service}').Status",
                "expected": "Running",
            },
        ],
    },
    "0x800706BA": {
        "symbol": "RPC_S_SERVER_UNAVAILABLE",
        "win32_code": 1722,
        "name": "The RPC server is unavailable",
        "subsystem": "ServicesTasks",
        "description": "The Remote Procedure Call (RPC) endpoint cannot be reached because RpcSs is stopped, DcomLaunch failed, or firewall blocks port 135.",
        "requires_privilege": "Administrator",
        "contributing_factors": [
            "RpcSs or RpcEptMapper service is stopped",
            "Windows Firewall blocks Remote Administration / RPC dynamic ports",
            "Network name resolution failure",
        ],
        "remediation_chain": [
            {
                "step": 1,
                "action": "Check status of RpcSs and start if stopped",
                "command": "Get-Service -Name RpcSs | Where-Object Status -ne 'Running' | Start-Service",
            },
            {
                "step": 2,
                "action": "Enable RPC inbound rules in Windows Firewall",
                "command": "Enable-NetFirewallRule -DisplayGroup 'Remote Service Management'",
            },
            {
                "step": 3,
                "action": "Test RPC port 135 connectivity",
                "command": "Test-NetConnection -ComputerName '127.0.0.1' -Port 135",
                "expected": "TcpTestSucceeded : True",
            },
        ],
    },
    "0x80072EE7": {
        "symbol": "WININET_E_NAME_NOT_RESOLVED",
        "win32_code": 12007,
        "name": "The server name or address could not be resolved",
        "subsystem": "NetworkFirewall",
        "description": "DNS resolution failed to return an IP address for the requested hostname.",
        "requires_privilege": "StandardUser",
        "contributing_factors": [
            "DNS Client cache is corrupted or stale",
            "Network adapter has no active gateway or DNS servers configured",
            "Dnscache service is stopped",
        ],
        "remediation_chain": [
            {
                "step": 1,
                "action": "Flush and clear local DNS client cache",
                "command": "Clear-DnsClientCache",
            },
            {
                "step": 2,
                "action": "Query DNS resolution directly using Resolve-DnsName",
                "command": "Resolve-DnsName -Name '{hostname}' -Type A",
            },
            {
                "step": 3,
                "action": "Test reachability via ping or HTTP",
                "command": "Test-Connection -TargetName '{hostname}' -Count 1 -Quiet",
                "expected": "True",
            },
        ],
    },
    "0x80041002": {
        "symbol": "WBEM_E_NOT_FOUND",
        "win32_code": None,
        "name": "WMI object or namespace not found",
        "subsystem": "DiagnosticsHealth",
        "description": "Windows Management Instrumentation (WMI) cannot locate the requested namespace, class, or instance.",
        "requires_privilege": "Administrator",
        "contributing_factors": [
            "Target WMI namespace is misspelled or not installed",
            "WMI repository corruption",
        ],
        "remediation_chain": [
            {
                "step": 1,
                "action": "Verify WMI repository integrity",
                "command": "winmgmt /verifyrepository",
            },
            {
                "step": 2,
                "action": "Salvage WMI repository if inconsistencies detected",
                "command": "winmgmt /salvagerepository",
            },
            {
                "step": 3,
                "action": "Restart Windows Management Instrumentation service",
                "command": "Restart-Service -Name Winmgmt -Force",
            },
        ],
    },
    "0x800700CE": {
        "symbol": "ERROR_FILENAME_EXCED_RANGE",
        "win32_code": 206,
        "name": "The filename or extension is too long (PathTooLongException)",
        "subsystem": "StorageNTFS",
        "description": "The fully qualified file path exceeds the Win32 MAX_PATH limit of 260 characters.",
        "requires_privilege": "Administrator",
        "contributing_factors": [
            "Win32 LongPathsEnabled registry setting is 0 (disabled)",
            "Command executed without extended path '\\\\?\\' prefix",
        ],
        "remediation_chain": [
            {
                "step": 1,
                "action": "Enable LongPaths in the system registry",
                "command": "Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem' -Name 'LongPathsEnabled' -Value 1 -Type DWord",
            },
            {
                "step": 2,
                "action": "Use extended-length Unicode path syntax in commands",
                "command": r"$resolved = if ('{path}' -notmatch '^\\\\\\\\\?\\\\') { '\\\\?\\' + (Resolve-Path '{path}') } else { '{path}' }",
            },
        ],
    },
    "0x80131515": {
        "symbol": "PSSecurityException",
        "win32_code": None,
        "name": "File cannot be loaded because running scripts is disabled on this system",
        "subsystem": "SecurityCrypto",
        "description": "PowerShell ExecutionPolicy restricts running unsigned or untrusted script files.",
        "requires_privilege": "StandardUser",
        "contributing_factors": [
            "ExecutionPolicy is Restricted or AllSigned",
            "Script downloaded from the internet has Zone.Identifier Mark of the Web",
        ],
        "remediation_chain": [
            {
                "step": 1,
                "action": "Unblock script file to remove Mark of the Web",
                "command": "Unblock-File -Path '{script}'",
            },
            {
                "step": 2,
                "action": "Set ExecutionPolicy for the current process scope",
                "command": "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force",
            },
            {
                "step": 3,
                "action": "Verify current process execution policy",
                "command": "Get-ExecutionPolicy -Scope Process",
                "expected": "Bypass",
            },
        ],
    },
    "10048": {
        "symbol": "WSAEADDRINUSE",
        "win32_code": 10048,
        "name": "Only one usage of each socket address (protocol/network address/port) is normally permitted",
        "subsystem": "NetworkFirewall",
        "description": "A socket bind failed because the local TCP/UDP port is already claimed by an active listening process.",
        "requires_privilege": "StandardUser",
        "contributing_factors": [
            "Stale instance of a dev server or daemon bound to port",
            "Socket in TIME_WAIT state",
        ],
        "remediation_chain": [
            {
                "step": 1,
                "action": "Identify PID holding the target port",
                "command": "(Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue).OwningProcess",
            },
            {
                "step": 2,
                "action": "Terminate owning process by PID",
                "command": "Stop-Process -Id {pid} -Force",
            },
            {
                "step": 3,
                "action": "Confirm port is now free",
                "command": "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue",
                "expected": "$null",
            },
        ],
    },
    "ROBOCOPY_FATAL_ERROR": {
        "symbol": "ROBOCOPY_ERROR_GE_8",
        "win32_code": None,
        "name": "Robocopy encountered a fatal error (exit code >= 8)",
        "subsystem": "StorageNTFS",
        "description": "Robocopy failed to copy some files due to sharing locks, access denied, insufficient disk space, or network failure.",
        "requires_privilege": "StandardUser",
        "contributing_factors": [
            "Source or destination path unreachable or lacks write permission",
            "File locked exclusively by another program",
        ],
        "remediation_chain": [
            {
                "step": 1,
                "action": "Run Robocopy with Restartable backup mode and retry limit",
                "command": "robocopy '{source}' '{dest}' /E /ZB /R:3 /W:5 /NP /LOG:'{log_file}'",
            },
            {
                "step": 2,
                "action": "Check exit code (0-7 represents success/partial copy, >=8 is fatal)",
                "command": "$exitCode = $LASTEXITCODE; if ($exitCode -ge 8) { throw 'Fatal robocopy error: ' + $exitCode }",
            },
        ],
    },
}
