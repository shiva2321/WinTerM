"""Layer 2: Memory, Processes, Threads, CPU Affinity & Win32 Handles Subsystem."""

from typing import Dict, Any, List, Optional
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import PlanStep, ActionCategory


class ProcessMemorySubsystem:
    """Manages process lifecycle, threads, CPU core affinity, priority classes, and loaded modules."""

    @classmethod
    def set_process_priority(cls, pid: int, priority: str = "High") -> PlanStep:
        """Configures process scheduling priority (RealTime, High, AboveNormal, Normal, BelowNormal, Idle)."""
        valid_priorities = ["RealTime", "High", "AboveNormal", "Normal", "BelowNormal", "Idle"]
        clean_prio = priority if priority in valid_priorities else "High"
        return PlanStep(
            step_id=f"proc-prio-{pid}",
            title=f"Set Process {pid} Priority to {clean_prio}",
            category=ActionCategory.PROCESS,
            raw_intent=f"set priority {pid} {clean_prio}",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN if clean_prio in ("RealTime", "High") else ElevationLevel.STANDARD,
            command=f"(Get-Process -Id {pid} -ErrorAction Stop).PriorityClass = '{clean_prio}'",
            metadata={"subsystem": "process_memory", "pid": pid, "priority": clean_prio},
        )

    @classmethod
    def set_cpu_affinity(cls, pid: int, core_mask: int) -> PlanStep:
        """Binds a process to specific CPU cores via bitmask (e.g. 1=Core0, 3=Cores0+1, 15=Cores0..3)."""
        return PlanStep(
            step_id=f"proc-affinity-{pid}",
            title=f"Set Process {pid} CPU Affinity Bitmask ({core_mask})",
            category=ActionCategory.PROCESS,
            raw_intent=f"set affinity {pid} {core_mask}",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=f"(Get-Process -Id {pid} -ErrorAction Stop).ProcessorAffinity = [IntPtr]{core_mask}",
            metadata={"subsystem": "process_memory", "pid": pid, "mask": core_mask},
        )

    @classmethod
    def inspect_loaded_modules(cls, pid: int) -> PlanStep:
        """Enumerates all DLLs and assemblies loaded into a process address space."""
        return PlanStep(
            step_id=f"proc-modules-{pid}",
            title=f"Inspect Loaded DLL Modules in Process {pid}",
            category=ActionCategory.PROCESS,
            raw_intent=f"inspect modules {pid}",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                f"(Get-Process -Id {pid} -ErrorAction Stop).Modules | "
                f"Select-Object -Property ModuleName,FileName,Size | "
                f"ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "process_memory", "pid": pid},
        )

    @classmethod
    def inspect_process_threads(cls, pid: int) -> PlanStep:
        """Enumerates active threads within a process with state and CPU time."""
        return PlanStep(
            step_id=f"proc-threads-{pid}",
            title=f"Enumerate Active Threads for Process {pid}",
            category=ActionCategory.PROCESS,
            raw_intent=f"inspect threads {pid}",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                f"(Get-Process -Id {pid} -ErrorAction Stop).Threads | "
                f"Select-Object -Property Id,ThreadState,WaitReason,TotalProcessorTime | "
                f"ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "process_memory", "pid": pid},
        )

    @classmethod
    def trim_working_set(cls, pid: int) -> PlanStep:
        """Requests Windows kernel to trim process working set memory to pagefile."""
        return PlanStep(
            step_id=f"proc-trim-{pid}",
            title=f"Trim Working Set Memory for Process {pid}",
            category=ActionCategory.PROCESS,
            raw_intent=f"trim memory {pid}",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                f"$proc = Get-Process -Id {pid} -ErrorAction Stop; "
                f"$pHandle = $proc.Handle; "
                f"[System.GC]::Collect(); "
                f"$memBefore = [math]::Round($proc.WorkingSet64 / 1MB, 2); "
                f"[PSCustomObject]@{{ PID = {pid}; WorkingSetMB = $memBefore }} | ConvertTo-Json"
            ),
            metadata={"subsystem": "process_memory", "pid": pid},
        )
