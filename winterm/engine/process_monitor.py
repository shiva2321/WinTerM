"""Windows Process and Resource Monitor: Live introspection of ports, processes, and services."""

import json
from typing import Optional, Dict, Any, List
from winterm.engine.executor import WindowsShellExecutor
from winterm.models.context import ShellType


class WindowsProcessMonitor:
    """Provides structured queries into active Windows processes, network ports, and services."""

    def __init__(self, executor: Optional[WindowsShellExecutor] = None):
        self.executor = executor or WindowsShellExecutor(default_shell=ShellType.POWERSHELL_51)

    def find_process_on_port(self, port: int) -> Optional[Dict[str, Any]]:
        """Identifies the process PID and name actively listening or established on a local TCP port."""
        safe_port = int(port)
        script = (
            f"Get-NetTCPConnection -LocalPort {safe_port} -ErrorAction SilentlyContinue | "
            f"Select-Object -First 1 -Property LocalPort,OwningProcess,State | "
            f"ForEach-Object {{ "
            f"$p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
            f"[PSCustomObject]@{{ Port = $_.LocalPort; PID = $_.OwningProcess; Name = $p.ProcessName; Path = $p.Path; State = $_.State.ToString() }} "
            f"}} | ConvertTo-Json"
        )
        res = self.executor.execute(script, shell=ShellType.POWERSHELL_51)
        if res.success and res.stdout:
            try:
                return json.loads(res.stdout)
            except Exception:
                pass
        return None

    def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """Retrieves process details by PID."""
        safe_pid = int(pid)
        script = (
            f"Get-Process -Id {safe_pid} -ErrorAction SilentlyContinue | "
            f"Select-Object -Property Id,ProcessName,Path,WorkingSet64,StartTime,Responding | "
            f"ConvertTo-Json"
        )
        res = self.executor.execute(script, shell=ShellType.POWERSHELL_51)
        if res.success and res.stdout:
            try:
                return json.loads(res.stdout)
            except Exception:
                pass
        return None

    def get_service_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves Windows service status and configuration."""
        safe_name = str(service_name).replace("'", "''")
        script = (
            f"Get-Service -Name '{safe_name}' -ErrorAction SilentlyContinue | "
            f"Select-Object -Property Name,DisplayName,Status,StartType | "
            f"ConvertTo-Json"
        )
        res = self.executor.execute(script, shell=ShellType.POWERSHELL_51)
        if res.success and res.stdout:
            try:
                data = json.loads(res.stdout)
                # Normalize Status int/string
                return data
            except Exception:
                pass
        return None

    def is_port_in_use(self, port: int) -> bool:
        """Checks if a TCP port is currently in use."""
        info = self.find_process_on_port(port)
        return info is not None
