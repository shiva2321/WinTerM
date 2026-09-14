"""Live Windows environment inspection and context resolution."""

import os
import sys
import shutil
import platform
import subprocess
from typing import List, Dict, Optional
from winterm.models.context import SystemContext, ElevationLevel
from winterm.knowledge.elevation_rules import ElevationRules


class WindowsEnvironment:
    """Probes the live Windows operating system to build an accurate SystemContext snapshot."""

    _cached_context: Optional[SystemContext] = None

    @classmethod
    def probe(cls, force_refresh: bool = False) -> SystemContext:
        """Inspects the local Windows system and returns a populated SystemContext."""
        if cls._cached_context and not force_refresh:
            return cls._cached_context

        # OS Details
        os_name = platform.system()
        os_release = platform.release()
        os_version = platform.version()
        arch = platform.machine()

        # Elevation
        elevation = ElevationRules.detect_elevation_level()

        # PowerShell version check
        ps_version = "5.1"
        pwsh_available = shutil.which("pwsh") is not None
        wsl_available = shutil.which("wsl") is not None

        # Detect package managers
        package_managers = []
        for pm in ["winget", "choco", "scoop"]:
            if shutil.which(pm) is not None:
                package_managers.append(pm)

        # Detect LongPathsEnabled via registry or default
        long_paths = False
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\FileSystem",
                0,
                winreg.KEY_READ,
            ) as key:
                val, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
                long_paths = (val == 1)
        except Exception:
            pass

        # Code page
        code_page = 65001
        try:
            import ctypes
            code_page = ctypes.windll.kernel32.GetConsoleOutputCP()
        except Exception:
            pass

        context = SystemContext(
            os_name=os_name,
            os_release=os_release,
            os_build=os_version,
            architecture=arch,
            powershell_version=ps_version,
            pwsh_available=pwsh_available,
            wsl_available=wsl_available,
            current_elevation=elevation,
            current_directory=os.getcwd(),
            active_code_page=code_page,
            long_paths_enabled=long_paths,
            installed_package_managers=package_managers,
            environment_variables={
                "PATH": os.environ.get("PATH", ""),
                "TEMP": os.environ.get("TEMP", ""),
                "USERPROFILE": os.environ.get("USERPROFILE", ""),
                "PROCESSOR_ARCHITECTURE": os.environ.get("PROCESSOR_ARCHITECTURE", arch),
            },
        )

        cls._cached_context = context
        return context
