"""Factual Windows Native Binaries Dataset: Win32 administrative tools, flags, elevation, and mutations."""

from typing import Dict, Any, List

# Catalog of core Win32 administration utilities across all 9 Windows subsystems
NATIVE_BINARIES_DATA: Dict[str, Dict[str, Any]] = {
    # --- LAYER 0: KERNEL & BOOT ---
    "bcdedit.exe": {
        "subsystem": "KernelBoot",
        "description": "Boot Configuration Data Editor for Windows boot parameters, hypervisor, safe boot, and recovery.",
        "requires_privilege": "Administrator",
        "parameters": [
            "/enum", "/v", "/set", "/deletevalue", "/create", "/delete",
            "/copy", "/timeout", "/bootsequence", "/default", "/displayorder",
            "/export", "/import", "/sysstore",
        ],
        "subcommands": ["ACTIVE", "ALL", "{current}", "{bootmgr}", "{default}"],
        "mutates_state": True,
        "mutates_entity": "BootConfigurationData",
    },
    "powercfg.exe": {
        "subsystem": "KernelBoot",
        "description": "Configures power settings, sleep states, processor throttle, battery reports, and hibernate configuration.",
        "requires_privilege": "StandardUser", # /hibernate and /setactive require Admin
        "parameters": [
            "/list", "/query", "/change", "/setactive", "/hibernate",
            "/batteryreport", "/energy", "/devicequery", "/waketimers",
            "/requests", "/availablesleepstates", "/sleepstudy", "/export", "/import",
        ],
        "mutates_state": True,
        "mutates_entity": "PowerSchemeConfiguration",
    },
    "fltmc.exe": {
        "subsystem": "KernelBoot",
        "description": "Manages file system mini-filter drivers, attachments, and altitude stacks.",
        "requires_privilege": "Administrator",
        "parameters": [
            "filters", "instances", "volumes", "attach", "detach", "load", "unload",
        ],
        "mutates_state": True,
        "mutates_entity": "MinifilterDriverStack",
    },

    # --- LAYER 1: STORAGE & NTFS ---
    "diskpart.exe": {
        "subsystem": "StorageNTFS",
        "description": "Disk Partition management command interpreter for disks, partitions, and volumes.",
        "requires_privilege": "Administrator",
        "parameters": ["/s"],
        "mutates_state": True,
        "mutates_entity": "DiskPartitionTable",
    },
    "vssadmin.exe": {
        "subsystem": "StorageNTFS",
        "description": "Volume Shadow Copy Service administrative tool for shadow copies and shadow storage.",
        "requires_privilege": "Administrator",
        "parameters": [
            "list", "create", "delete", "resize",
            "shadows", "shadowstorage", "writers", "providers",
            "/for=", "/on=", "/maxsize=", "/quiet",
        ],
        "mutates_state": True,
        "mutates_entity": "VolumeShadowCopy",
    },
    "icacls.exe": {
        "subsystem": "StorageNTFS",
        "description": "Displays or modifies discretionary access control lists (DACLs) on NTFS files and directories.",
        "requires_privilege": "StandardUser", # Administrator for system paths or ownership takeovers
        "parameters": [
            "/grant", "/grant:r", "/deny", "/remove", "/inheritance:e", "/inheritance:d", "/inheritance:r",
            "/reset", "/setowner", "/setintegritylevel", "/T", "/C", "/Q", "/L",
        ],
        "mutates_state": True,
        "mutates_entity": "FileDACL",
    },
    "takeown.exe": {
        "subsystem": "StorageNTFS",
        "description": "Recovers access to a file or directory by making the active user the file owner.",
        "requires_privilege": "Administrator",
        "parameters": ["/F", "/A", "/R", "/D", "/SKIPSL"],
        "mutates_state": True,
        "mutates_entity": "FileOwner",
    },
    "robocopy.exe": {
        "subsystem": "StorageNTFS",
        "description": "Robust File and Folder Copy for Windows with NTFS metadata, ACL, and retry preservation.",
        "requires_privilege": "StandardUser",
        "parameters": [
            "/S", "/E", "/LEV:", "/Z", "/B", "/ZB", "/COPY:", "/COPYALL", "/NOCOPY", "/SEC",
            "/MIR", "/MOV", "/MOVE", "/A", "/M", "/A+:", "/A-:", "/CREATE",
            "/R:", "/W:", "/REG", "/TBD", "/MT:", "/XF", "/XD", "/NFL", "/NDL",
            "/NJH", "/NJS", "/LOG:", "/LOG+:", "/UNILOG:", "/UNILOG+:",
        ],
        "mutates_state": True,
        "mutates_entity": "FileSystemHierarchy",
    },

    # --- LAYER 2: PROCESS & MEMORY ---
    "tasklist.exe": {
        "subsystem": "ProcessMemory",
        "description": "Displays a list of currently running processes on the local or remote computer.",
        "requires_privilege": "StandardUser",
        "parameters": [
            "/S", "/U", "/P", "/FO", "/NH", "/FI", "/PID", "/M", "/V", "/APPS",
        ],
        "mutates_state": False,
    },
    "taskkill.exe": {
        "subsystem": "ProcessMemory",
        "description": "Terminates tasks by process id (PID) or image name.",
        "requires_privilege": "StandardUser", # Administrator for elevated processes
        "parameters": [
            "/S", "/U", "/P", "/F", "/PID", "/IM", "/T", "/FI",
        ],
        "mutates_state": True,
        "mutates_entity": "ProcessState",
    },

    # --- LAYER 3: SERVICES & TASKS ---
    "sc.exe": {
        "subsystem": "ServicesTasks",
        "description": "Service Control Manager interface for creating, configuring, querying, and controlling services.",
        "requires_privilege": "Administrator", # query works for standard user
        "parameters": [
            "query", "queryex", "start", "stop", "pause", "continue",
            "config", "description", "failure", "qc", "qfailure",
            "delete", "create", "control", "sdshow", "sdset",
        ],
        "mutates_state": True,
        "mutates_entity": "ServiceControllerConfiguration",
    },
    "schtasks.exe": {
        "subsystem": "ServicesTasks",
        "description": "Schedules commands and programs to run periodically or at a specified time.",
        "requires_privilege": "StandardUser", # Administrator for system-level tasks
        "parameters": [
            "/Create", "/Delete", "/Query", "/Change", "/Run", "/End", "/ShowSid",
            "/TN", "/TR", "/SC", "/MO", "/D", "/M", "/I", "/ST", "/RI", "/ET",
            "/DU", "/K", "/SD", "/ED", "/RU", "/RP", "/RL", "/F", "/V", "/FO", "/NH",
        ],
        "mutates_state": True,
        "mutates_entity": "ScheduledTask",
    },

    # --- LAYER 4: REGISTRY & POLICY ---
    "reg.exe": {
        "subsystem": "RegistryPolicy",
        "description": "Command-line Registry console tool for querying, adding, deleting, and saving registry entries.",
        "requires_privilege": "StandardUser", # HKLM requires Administrator
        "parameters": [
            "QUERY", "ADD", "DELETE", "COPY", "SAVE", "RESTORE", "LOAD", "UNLOAD",
            "COMPARE", "EXPORT", "IMPORT", "FLAGS",
            "/v", "/ve", "/s", "/se", "/f", "/d", "/t", "/c", "/reg:32", "/reg:64",
        ],
        "mutates_state": True,
        "mutates_entity": "RegistryKey",
    },
    "gpupdate.exe": {
        "subsystem": "RegistryPolicy",
        "description": "Updates Group Policy settings across computer and user scopes.",
        "requires_privilege": "StandardUser",
        "parameters": [
            "/Target:Computer", "/Target:User", "/Force", "/Wait:", "/Logoff", "/Boot", "/Sync",
        ],
        "mutates_state": True,
        "mutates_entity": "GroupPolicyState",
    },
    "gpresult.exe": {
        "subsystem": "RegistryPolicy",
        "description": "Displays the Resultant Set of Policy (RSoP) information for a target user and computer.",
        "requires_privilege": "StandardUser",
        "parameters": [
            "/R", "/V", "/Z", "/Scope:User", "/Scope:Computer", "/H", "/X", "/F",
        ],
        "mutates_state": False,
    },

    # --- LAYER 5: SECURITY & CRYPTO ---
    "whoami.exe": {
        "subsystem": "SecurityCrypto",
        "description": "Displays current user, security identifiers (SID), group memberships, and assigned privileges.",
        "requires_privilege": "StandardUser",
        "parameters": [
            "/user", "/groups", "/priv", "/logonid", "/all", "/fo", "/nh",
        ],
        "mutates_state": False,
    },
    "certutil.exe": {
        "subsystem": "SecurityCrypto",
        "description": "Certificate Services utility for dumping and displaying CA configuration, verifying certs, and hash computation.",
        "requires_privilege": "StandardUser", # Installing into LocalMachine root requires Administrator
        "parameters": [
            "-dump", "-store", "-addstore", "-delstore", "-verify", "-repairstore",
            "-hashfile", "-encode", "-decode", "-pulse", "-ping", "-urlcache",
        ],
        "mutates_state": True,
        "mutates_entity": "CertificateStore",
    },

    # --- LAYER 6: NETWORK & FIREWALL ---
    "netsh.exe": {
        "subsystem": "NetworkFirewall",
        "description": "Network Command Shell for configuring network interfaces, Windows Firewall, routing, and WinHTTP.",
        "requires_privilege": "Administrator",
        "parameters": [
            "advfirewall", "interface", "wlan", "winhttp", "firewall",
            "show", "set", "add", "delete", "reset", "dump", "export", "import",
            "rule", "profile", "allprofiles", "currentprofile",
        ],
        "mutates_state": True,
        "mutates_entity": "NetworkFirewallConfiguration",
    },
    "ipconfig.exe": {
        "subsystem": "NetworkFirewall",
        "description": "Displays all current TCP/IP network configuration values and refreshes DHCP/DNS settings.",
        "requires_privilege": "StandardUser",
        "parameters": [
            "/all", "/release", "/release6", "/renew", "/renew6",
            "/flushdns", "/registerdns", "/displaydns", "/showclassid",
        ],
        "mutates_state": True,
        "mutates_entity": "DnsClientCache",
    },
    "route.exe": {
        "subsystem": "NetworkFirewall",
        "description": "Manipulates network routing tables.",
        "requires_privilege": "Administrator",
        "parameters": [
            "print", "add", "delete", "change",
            "-f", "-p", "-4", "-6", "mask", "metric", "if",
        ],
        "mutates_state": True,
        "mutates_entity": "RoutingTable",
    },

    # --- LAYER 7: DIAGNOSTICS & HEALTH ---
    "sfc.exe": {
        "subsystem": "DiagnosticsHealth",
        "description": "System File Checker scans integrity of all protected system files and replaces corrupted versions.",
        "requires_privilege": "Administrator",
        "parameters": [
            "/scannow", "/verifyonly", "/scanfile=", "/verifyfile=",
            "/offbootdir=", "/offwindir=",
        ],
        "mutates_state": True,
        "mutates_entity": "ProtectedSystemFiles",
    },
    "dism.exe": {
        "subsystem": "DiagnosticsHealth",
        "description": "Deployment Image Servicing and Management tool for servicing Windows images and component store (WinSxS).",
        "requires_privilege": "Administrator",
        "parameters": [
            "/Online", "/Image:", "/Cleanup-Image", "/CheckHealth", "/ScanHealth",
            "/RestoreHealth", "/StartComponentCleanup", "/ResetBase",
            "/Get-Packages", "/Get-Features", "/Enable-Feature", "/Disable-Feature",
            "/FeatureName:", "/All", "/Source:", "/LimitAccess",
        ],
        "mutates_state": True,
        "mutates_entity": "WindowsComponentStore",
    },
    "wevtutil.exe": {
        "subsystem": "DiagnosticsHealth",
        "description": "Enables retrieval of information about event logs and publishers, exporting, archiving, and clearing logs.",
        "requires_privilege": "StandardUser", # Clearing logs requires Administrator
        "parameters": [
            "qe", "gli", "sl", "cl", "ep", "gp", "al", "um",
            "/f:text", "/f:xml", "/c:", "/rd:true", "/q:", "/e:", "/r:",
        ],
        "mutates_state": True,
        "mutates_entity": "WindowsEventLog",
    },

    # --- LAYER 8: VIRTUALIZATION & PACKAGES ---
    "wsl.exe": {
        "subsystem": "VirtualizationPackages",
        "description": "Launches and manages Windows Subsystem for Linux distributions.",
        "requires_privilege": "StandardUser",
        "parameters": [
            "--list", "-l", "--verbose", "-v", "--running", "--all",
            "--status", "--help", "--shutdown", "--terminate", "-t",
            "--unregister", "--set-version", "--set-default-version",
            "--export", "--import", "--distribution", "-d", "--user", "-u",
        ],
        "mutates_state": True,
        "mutates_entity": "WslDistributionState",
    },
    "winget.exe": {
        "subsystem": "VirtualizationPackages",
        "description": "Windows Package Manager CLI client for installing, querying, and updating applications.",
        "requires_privilege": "StandardUser", # System packages require UAC
        "parameters": [
            "search", "install", "show", "upgrade", "uninstall", "list",
            "hash", "validate", "settings", "source",
            "--id", "--name", "-e", "--exact", "-m", "--manifest",
            "-v", "--version", "-s", "--source", "-h", "--silent",
            "--accept-package-agreements", "--accept-source-agreements",
            "--all", "--include-unknown",
        ],
        "mutates_state": True,
        "mutates_entity": "InstalledPackageCatalog",
    },
}
