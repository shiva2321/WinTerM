"""System context models for Windows environment and shell state."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ShellType(str, Enum):
    """Supported Windows shell environments."""
    POWERSHELL_51 = "powershell_51"  # Windows PowerShell 5.1 Desktop (default on Win 10/11)
    POWERSHELL_7 = "pwsh"            # PowerShell 7+ Core (cross-platform / modern)
    CMD = "cmd"                      # Classic Windows Command Prompt (cmd.exe)
    WSL_BASH = "wsl_bash"            # Windows Subsystem for Linux (bash)
    AUTO = "auto"                    # Automatically pick the most appropriate shell


class ElevationLevel(str, Enum):
    """Execution privilege levels."""
    STANDARD = "standard"            # Normal standard user privileges
    ADMIN = "admin"                  # Elevated Administrator (UAC token)
    SYSTEM = "system"                # NT AUTHORITY\SYSTEM service account


class SystemContext(BaseModel):
    """Snapshot of the host Windows environment."""
    os_name: str = Field(default="Windows", description="Operating system name")
    os_release: str = Field(default="", description="Windows release (e.g. 10, 11)")
    os_build: str = Field(default="", description="Windows build number (e.g. 26100)")
    architecture: str = Field(default="x64", description="CPU Architecture (x64, ARM64, x86)")
    powershell_version: str = Field(default="5.1", description="Installed PowerShell version")
    pwsh_available: bool = Field(default=False, description="Whether PowerShell 7 (pwsh) is installed")
    wsl_available: bool = Field(default=False, description="Whether WSL is installed and enabled")
    current_elevation: ElevationLevel = Field(
        default=ElevationLevel.STANDARD,
        description="Current user elevation level"
    )
    current_directory: str = Field(default="", description="Current working directory")
    active_code_page: int = Field(default=65001, description="Active console code page (e.g. 65001 for UTF-8)")
    long_paths_enabled: bool = Field(
        default=False,
        description="Whether Win32 LongPathsEnabled (>260 chars) is enabled in registry"
    )
    installed_package_managers: List[str] = Field(
        default_factory=list,
        description="Detected package managers (winget, choco, scoop)"
    )
    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Selected environment variables (PATH, TEMP, etc.)"
    )
