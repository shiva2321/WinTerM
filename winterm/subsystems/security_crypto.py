"""Layer 5: Security, Accounts, Privileges, Certificates & Windows Defender Subsystem."""

from typing import Dict, Any, List, Optional
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import PlanStep, ActionCategory


class SecurityCryptoSubsystem:
    """Manages local users, groups, privileges, certificates, credentials, and Windows Defender."""

    @classmethod
    def audit_user_privileges(cls) -> PlanStep:
        """Audits active user token security privileges (SeDebugPrivilege, SeShutdownPrivilege, etc.)."""
        return PlanStep(
            step_id="sec-whoami-priv",
            title="Audit Security Token Privileges (whoami /priv)",
            category=ActionCategory.SECURITY,
            raw_intent="audit privileges",
            target_shell=ShellType.CMD,
            command="whoami /priv",
            metadata={"subsystem": "security_crypto", "action": "whoami_priv"},
        )

    @classmethod
    def list_local_users(cls) -> PlanStep:
        """Enumerates local user accounts with enabled state and password requirements."""
        return PlanStep(
            step_id="sec-localusers-list",
            title="Enumerate Local User Accounts",
            category=ActionCategory.SECURITY,
            raw_intent="list local users",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=(
                "Get-LocalUser | Select-Object -Property Name,Enabled,PasswordRequired,"
                "UserMayChangePassword,LastLogon | ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "security_crypto", "action": "list_users"},
        )

    @classmethod
    def list_certificates_in_store(cls, store_location: str = "LocalMachine", store_name: str = "My") -> PlanStep:
        """Lists installed X.509 certificates from the Windows Certificate Store."""
        return PlanStep(
            step_id=f"sec-cert-list-{store_location}-{store_name}",
            title=f"Inspect Windows Certificate Store: Cert:\\{store_location}\\{store_name}",
            category=ActionCategory.SECURITY,
            raw_intent=f"list certificates {store_location} {store_name}",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                f"Get-ChildItem -Path 'Cert:\\{store_location}\\{store_name}' -ErrorAction SilentlyContinue | "
                f"Select-Object -Property Subject,Thumbprint,NotAfter,NotBefore,HasPrivateKey | "
                f"ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "security_crypto", "store": f"{store_location}\\{store_name}"},
        )

    @classmethod
    def query_defender_status(cls) -> PlanStep:
        """Inspects Windows Defender antivirus status, real-time protection, and signature versions."""
        return PlanStep(
            step_id="sec-defender-status",
            title="Query Windows Defender Antivirus Protection Status",
            category=ActionCategory.SECURITY,
            raw_intent="query defender status",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=(
                "Get-MpComputerStatus | "
                "Select-Object -Property AntivirusEnabled,RealTimeProtectionEnabled,"
                "AntivirusSignatureLastUpdated,AMServiceEnabled | ConvertTo-Json"
            ),
            metadata={"subsystem": "security_crypto", "action": "defender_status"},
        )

    @classmethod
    def add_defender_exclusion(cls, folder_path: str) -> PlanStep:
        """Adds a trusted directory exclusion to Windows Defender real-time scanning."""
        return PlanStep(
            step_id="sec-defender-add-exclusion",
            title=f"Add Defender Exclusion: {folder_path}",
            category=ActionCategory.SECURITY,
            raw_intent=f"add defender exclusion {folder_path}",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=f"Add-MpPreference -ExclusionPath '{folder_path}'",
            metadata={"subsystem": "security_crypto", "path": folder_path},
        )

    @classmethod
    def list_saved_credentials(cls) -> PlanStep:
        """Lists generic and domain credentials stored in Windows Credential Manager."""
        return PlanStep(
            step_id="sec-cmdkey-list",
            title="Enumerate Windows Credential Manager Targets",
            category=ActionCategory.SECURITY,
            raw_intent="list saved credentials",
            target_shell=ShellType.CMD,
            command="cmdkey /list",
            metadata={"subsystem": "security_crypto", "action": "cmdkey_list"},
        )
