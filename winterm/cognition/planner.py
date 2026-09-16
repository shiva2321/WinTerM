"""Terminal Task Planner: Decomposes natural language goals into staged atomic execution plans (The WHAT of 5W)."""

import re
import uuid
from typing import List, Dict, Any, Optional
from winterm.models.intent import ExecutionPlan, PlanStep, ActionCategory, StepStatus
from winterm.models.context import ShellType, ElevationLevel, SystemContext
from winterm.knowledge.commands_db import WindowsCommandDatabase
from winterm.knowledge.shell_matrix import ShellMatrix
from winterm.engine.environment import WindowsEnvironment
from winterm.subsystems import (
    KernelBootSubsystem,
    StorageNTFSSubsystem,
    ProcessMemorySubsystem,
    ServicesTasksSubsystem,
    RegistryPolicySubsystem,
    SecurityCryptoSubsystem,
    NetworkFirewallSubsystem,
    DiagnosticsHealthSubsystem,
    VirtualizationPackagesSubsystem,
    DesktopGuiSubsystem,
)


class TerminalPlanner:
    """Decomposes goals into a staged DAG plan of atomic Windows terminal actions."""

    def __init__(self, context: Optional[SystemContext] = None):
        self.context = context or WindowsEnvironment.probe()

    def plan_goal(self, goal: str) -> ExecutionPlan:
        """Parses a natural language goal and produces a structured ExecutionPlan."""
        plan_id = f"plan-{uuid.uuid4().hex[:8]}"
        steps: List[PlanStep] = []
        requires_admin = False

        goal_clean = goal.strip()
        lower_goal = goal_clean.lower()

        # Rule-based intent decomposition
        # 1. Port conflict resolution: e.g. "free port 8080 and run server" or "kill process on port 3000"
        port_match = re.search(r'\b(?:port|on port)\s+(\d{2,5})\b', lower_goal)
        if port_match and any(w in lower_goal for w in ["kill", "free", "stop", "terminate", "clear"]):
            port = int(port_match.group(1))
            steps.append(
                PlanStep(
                    step_id="step-1",
                    title=f"Identify process listening on port {port}",
                    category=ActionCategory.PROCESS,
                    raw_intent=f"find process on port {port}",
                    target_shell=ShellType.POWERSHELL_51,
                    command=WindowsCommandDatabase.CATALOG["find_process_by_port"].powershell_template.format(port=port),
                    metadata={"port": port},
                )
            )
            steps.append(
                PlanStep(
                    step_id="step-2",
                    title=f"Terminate process occupying port {port}",
                    category=ActionCategory.PROCESS,
                    raw_intent=f"kill process on port {port}",
                    target_shell=ShellType.POWERSHELL_51,
                    command=(
                        f"$conns = Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue; "
                        f"if ($conns) {{ $conns | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }} }}"
                    ),
                    depends_on=["step-1"],
                    metadata={"port": port},
                )
            )

        # 2. Kill process by name: e.g. "kill chrome" or "stop process node"
        elif re.match(r'^(?:kill|stop|terminate)\s+(?:process\s+)?[a-zA-Z0-9_\-\.]+\s*$', lower_goal) and "service" not in lower_goal:
            proc_name = re.sub(r'\.exe$', '', re.sub(r'^(?:kill|stop|terminate)\s+(?:process\s+)?', '', goal_clean, flags=re.IGNORECASE)).strip()
            steps.append(
                PlanStep(
                    step_id="step-1",
                    title=f"Terminate process '{proc_name}'",
                    category=ActionCategory.PROCESS,
                    raw_intent=f"kill process {proc_name}",
                    target_shell=ShellType.POWERSHELL_51,
                    command=WindowsCommandDatabase.CATALOG["kill_process_by_name"].powershell_template.format(name=proc_name),
                    metadata={"process_name": proc_name},
                )
            )

        # 3. List high memory processes: e.g. "show top memory processes"
        elif ("top" in lower_goal and "memory" in lower_goal) or "high memory" in lower_goal:
            count = 10
            count_match = re.search(r'top\s+(\d+)', lower_goal)
            if count_match:
                count = int(count_match.group(1))
            steps.append(
                PlanStep(
                    step_id="step-1",
                    title=f"Query top {count} memory-consuming processes",
                    category=ActionCategory.PROCESS,
                    raw_intent="list top memory processes",
                    target_shell=ShellType.POWERSHELL_51,
                    command=WindowsCommandDatabase.CATALOG["list_top_memory_processes"].powershell_template.format(count=count),
                    metadata={"count": count},
                )
            )

        # 4. Windows Service restart: e.g. "restart service spooler"
        elif "restart service" in lower_goal:
            service_name = re.sub(r'^.*?restart\s+service\s+', '', goal_clean, flags=re.IGNORECASE).strip()
            requires_admin = True
            steps.append(
                PlanStep(
                    step_id="step-1",
                    title=f"Restart Windows service '{service_name}'",
                    category=ActionCategory.SERVICE,
                    raw_intent=f"restart service {service_name}",
                    target_shell=ShellType.POWERSHELL_51,
                    required_elevation=ElevationLevel.ADMIN,
                    command=WindowsCommandDatabase.CATALOG["restart_service"].powershell_template.format(service_name=service_name),
                    metadata={"service_name": service_name},
                )
            )

        # 5. Port connectivity test: e.g. "test port 443 on github.com"
        elif "test port" in lower_goal or "check port" in lower_goal:
            host = "localhost"
            port = 80
            port_m = re.search(r'port\s+(\d+)', lower_goal)
            if port_m:
                port = int(port_m.group(1))
            host_m = re.search(r'(?:on|to|for)\s+([a-zA-Z0-9.\-]+)', lower_goal)
            if host_m:
                host = host_m.group(1)
            steps.append(
                PlanStep(
                    step_id="step-1",
                    title=f"Test TCP port connectivity to {host}:{port}",
                    category=ActionCategory.NETWORK,
                    raw_intent=f"test connection {host} {port}",
                    target_shell=ShellType.POWERSHELL_51,
                    command=WindowsCommandDatabase.CATALOG["test_port_connectivity"].powershell_template.format(host=host, port=port),
                    metadata={"host": host, "port": port},
                )
            )

        # 6. Hardware / System diagnostic query
        elif any(w in lower_goal for w in ["system info", "hardware", "cpu info", "system hardware"]):
            steps.append(
                PlanStep(
                    step_id="step-1",
                    title="Query system hardware specifications via CIM",
                    category=ActionCategory.DIAGNOSTIC,
                    raw_intent="query system hardware",
                    target_shell=ShellType.POWERSHELL_51,
                    command=WindowsCommandDatabase.CATALOG["query_system_hardware"].powershell_template,
                )
            )

        # --- LAYER 0: KERNEL & BOOT ---
        elif re.search(r'\bbcd\b', lower_goal) or "boot config" in lower_goal or "bootloader" in lower_goal:
            requires_admin = True
            steps.append(KernelBootSubsystem.query_boot_configuration())
        elif any(w in lower_goal for w in ["power schemes", "power plans", "powercfg"]):
            steps.append(KernelBootSubsystem.query_power_schemes())
        elif any(w in lower_goal for w in ["tpm", "trusted platform module"]):
            requires_admin = True
            steps.append(KernelBootSubsystem.query_tpm_status())
        elif any(w in lower_goal for w in ["firmware mode", "uefi", "bios mode"]):
            steps.append(KernelBootSubsystem.query_uefi_firmware_type())

        # --- LAYER 1: STORAGE & NTFS ---
        elif any(w in lower_goal for w in ["list disks", "physical disks", "disk health"]):
            requires_admin = True
            steps.append(StorageNTFSSubsystem.list_physical_disks())
        elif any(w in lower_goal for w in ["list volumes", "free space", "drive space"]):
            steps.append(StorageNTFSSubsystem.list_volumes())
        elif "bitlocker" in lower_goal:
            requires_admin = True
            steps.append(StorageNTFSSubsystem.query_bitlocker_status())
        elif any(w in lower_goal for w in ["shadow copies", "vss"]):
            requires_admin = True
            steps.append(StorageNTFSSubsystem.list_shadow_copies())
        elif any(w in lower_goal for w in ["acl", "ntfs permissions", "permissions on"]):
            path_m = re.search(r"(?:for|on|path)\s+['\"]?([a-zA-Z0-9_:\\\-\.]+)['\"]?", goal_clean)
            target_p = path_m.group(1) if path_m else "."
            steps.append(StorageNTFSSubsystem.inspect_acls(target_p))

        # --- LAYER 2: PROCESS & MEMORY ---
        elif "cpu affinity" in lower_goal or "affinity" in lower_goal:
            pid_m = re.search(r'pid\s+(\d+)', lower_goal)
            pid = int(pid_m.group(1)) if pid_m else 1000
            steps.append(ProcessMemorySubsystem.set_cpu_affinity(pid, 3))
        elif "loaded modules" in lower_goal or "dlls" in lower_goal:
            pid_m = re.search(r'pid\s+(\d+)', lower_goal)
            pid = int(pid_m.group(1)) if pid_m else 1000
            steps.append(ProcessMemorySubsystem.inspect_loaded_modules(pid))

        # --- LAYER 3: SERVICES & TASKS ---
        elif any(w in lower_goal for w in ["scheduled tasks", "list tasks"]):
            steps.append(
                PlanStep(
                    step_id="step-tasks-list",
                    title="Enumerate Windows Scheduled Tasks",
                    category=ActionCategory.SYSTEM,
                    raw_intent="list scheduled tasks",
                    target_shell=ShellType.POWERSHELL_51,
                    command=WindowsCommandDatabase.CATALOG["list_scheduled_tasks"].powershell_template,
                )
            )

        # --- LAYER 4: REGISTRY & POLICIES ---
        elif "gpupdate" in lower_goal or "group policy" in lower_goal:
            steps.append(RegistryPolicySubsystem.force_group_policy_update())
        elif "registry" in lower_goal:
            if "long path" in lower_goal:
                steps.append(RegistryPolicySubsystem.query_registry_tree(r"HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem"))
            else:
                path_m = re.search(r"(?:path|in|key)\s+['\"]?([a-zA-Z0-9_:\\\-\.]+)['\"]?", goal_clean)
                reg_p = path_m.group(1) if path_m else r"HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion"
                steps.append(RegistryPolicySubsystem.query_registry_tree(reg_p))

        # --- LAYER 5: SECURITY & CRYPTO ---
        elif any(w in lower_goal for w in ["privileges", "whoami /priv", "user privileges"]):
            steps.append(SecurityCryptoSubsystem.audit_user_privileges())
        elif any(w in lower_goal for w in ["local users", "list users"]):
            requires_admin = True
            steps.append(SecurityCryptoSubsystem.list_local_users())
        elif any(w in lower_goal for w in ["certificates", "cert store", "certs"]):
            steps.append(SecurityCryptoSubsystem.list_certificates_in_store())
        elif any(w in lower_goal for w in ["defender status", "antivirus status"]):
            requires_admin = True
            steps.append(SecurityCryptoSubsystem.query_defender_status())
        elif any(w in lower_goal for w in ["saved credentials", "credential manager", "cmdkey"]):
            steps.append(SecurityCryptoSubsystem.list_saved_credentials())

        # --- LAYER 6: NETWORK & FIREWALL ---
        elif any(w in lower_goal for w in ["network adapters", "list adapters", "nic"]):
            steps.append(NetworkFirewallSubsystem.list_network_adapters())
        elif any(w in lower_goal for w in ["flush dns", "clear dns"]):
            steps.append(NetworkFirewallSubsystem.flush_dns_cache())
        elif any(w in lower_goal for w in ["winhttp", "proxy"]):
            steps.append(NetworkFirewallSubsystem.query_winhttp_proxy())
        elif any(w in lower_goal for w in ["routing table", "routes"]):
            steps.append(NetworkFirewallSubsystem.inspect_ip_routing_table())

        # --- LAYER 7: DIAGNOSTICS & HEALTH ---
        elif any(w in lower_goal for w in ["audio", "sound problem", "no sound", "sound issue", "audio problem", "troubleshoot audio"]):
            steps.append(DiagnosticsHealthSubsystem.audit_audio_services())
            steps.append(DiagnosticsHealthSubsystem.probe_sound_hardware())
            steps.append(DiagnosticsHealthSubsystem.audit_pnp_media_devices())
            steps.append(DiagnosticsHealthSubsystem.query_audio_event_logs(max_events=10))
        elif any(w in lower_goal for w in ["system errors", "event log", "event viewer"]):
            steps.append(DiagnosticsHealthSubsystem.query_recent_system_errors())
        elif any(w in lower_goal for w in ["performance counters", "cpu usage counter", "memory counter"]):
            steps.append(DiagnosticsHealthSubsystem.query_live_performance_metrics())
        elif any(w in lower_goal for w in ["sfc", "system file checker", "scan system files"]):
            requires_admin = True
            steps.append(DiagnosticsHealthSubsystem.scan_system_file_integrity())
        elif any(w in lower_goal for w in ["dism", "component store"]):
            requires_admin = True
            steps.append(DiagnosticsHealthSubsystem.dism_health_check())
        elif any(w in lower_goal for w in ["reliability", "stability records"]):
            steps.append(DiagnosticsHealthSubsystem.query_reliability_history())

        # --- LAYER 8: VIRTUALIZATION & PACKAGES ---
        elif any(w in lower_goal for w in ["wsl", "wsl distros", "wsl list"]):
            steps.append(VirtualizationPackagesSubsystem.list_wsl_distributions())
        elif any(w in lower_goal for w in ["hyperv", "vms", "virtual machines"]):
            requires_admin = True
            steps.append(VirtualizationPackagesSubsystem.list_hyperv_vms())
        elif any(w in lower_goal for w in ["winget upgrade", "update apps"]):
            steps.append(VirtualizationPackagesSubsystem.winget_upgrade_all())
        elif "winget install" in lower_goal:
            pkg_m = re.search(r'winget install\s+([a-zA-Z0-9_\-\.]+)', lower_goal)
            pkg_id = pkg_m.group(1) if pkg_m else "Git.Git"
            steps.append(VirtualizationPackagesSubsystem.winget_install(pkg_id))

        # --- LAYER 9: DESKTOP GUI & INPUT AUTOMATION ---
        elif any(w in lower_goal for w in ["find app", "search app", "find application", "list apps"]):
            app_q_m = re.search(r'(?:find|search|list)\s+(?:app|apps|application|applications)\s*(.*)', goal_clean, re.IGNORECASE)
            app_q = app_q_m.group(1).strip() if app_q_m and app_q_m.group(1).strip() else None
            steps.append(DesktopGuiSubsystem.find_applications(query=app_q))
        elif any(lower_goal.startswith(w) for w in ["launch app", "open app", "start app", "launch application", "open application"]):
            app_t_m = re.search(r'(?:launch|open|start)\s+(?:app|application)\s+([^\s]+)', goal_clean, re.IGNORECASE)
            target = app_t_m.group(1).strip() if app_t_m else "notepad.exe"
            steps.append(DesktopGuiSubsystem.launch_application(target=target))
        elif any(lower_goal.startswith(w) for w in ["close app", "kill app", "stop app", "close application"]):
            app_c_m = re.search(r'(?:close|kill|stop)\s+(?:app|application)\s+([^\s]+)', goal_clean, re.IGNORECASE)
            target = app_c_m.group(1).strip() if app_c_m else "notepad"
            steps.append(DesktopGuiSubsystem.close_application(target=target))
        elif any(w in lower_goal for w in ["list windows", "show windows", "get windows"]):
            steps.append(DesktopGuiSubsystem.list_windows())
        elif any(w in lower_goal for w in ["focus window", "foreground window", "activate window"]):
            proc_m = re.search(r'(?:focus|foreground|activate)\s+(?:window\s+)?([a-zA-Z0-9_\-\.\s]+)', goal_clean, re.IGNORECASE)
            p_name = proc_m.group(1).strip() if proc_m else "notepad"
            steps.append(DesktopGuiSubsystem.focus_window(p_name))
        elif any(w in lower_goal for w in ["resize window", "move window"]):
            res_m = re.search(r'(?:resize|move)\s+(?:window\s+)?([a-zA-Z0-9_\-\.]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', goal_clean, re.IGNORECASE)
            if res_m:
                steps.append(DesktopGuiSubsystem.resize_move_window(res_m.group(1), int(res_m.group(2)), int(res_m.group(3)), int(res_m.group(4)), int(res_m.group(5))))
            else:
                steps.append(DesktopGuiSubsystem.resize_move_window("Notepad", 100, 100, 800, 600))
        elif any(w in lower_goal for w in ["inspect ui", "inspect elements", "inspect window"]):
            insp_m = re.search(r'(?:inspect\s+(?:ui|elements|controls|window)\s+(?:in\s+)?)([a-zA-Z0-9_\-\.\s]+)', goal_clean, re.IGNORECASE)
            w_name = insp_m.group(1).strip() if insp_m else "Notepad"
            steps.append(DesktopGuiSubsystem.inspect_ui_elements(w_name))
        elif any(w in lower_goal for w in ["click element", "click button", "click control"]):
            clk_m = re.search(r'click\s+(?:element|button|control)\s+([^\s]+)\s+(?:in\s+)?([^\s]+)', goal_clean, re.IGNORECASE)
            if clk_m:
                steps.append(DesktopGuiSubsystem.click_ui_element(window_identifier=clk_m.group(2), element_query=clk_m.group(1)))
            else:
                steps.append(DesktopGuiSubsystem.click_ui_element(window_identifier="Notepad", element_query="Submit"))
        elif any(w in lower_goal for w in ["type text", "type into", "type string"]):
            txt_m = re.search(r'type\s+(?:text|into|string)\s*(.*)', goal_clean, re.IGNORECASE)
            txt_val = txt_m.group(1).strip() if txt_m and txt_m.group(1).strip() else "Hello Windows"
            steps.append(DesktopGuiSubsystem.type_text(txt_val))
        elif any(w in lower_goal for w in ["press hotkey", "send hotkey", "keyboard shortcut", "press windows", "press win", "press key", "press keys", "show desktop", "minimize all windows"]):
            if "show desktop" in lower_goal or "minimize all" in lower_goal:
                parsed_keys = ["win", "d"]
            else:
                hk_m = re.search(r'(?:hotkey|shortcut|press|send)\s+(?:the\s+)?([a-zA-Z0-9_\-\+\s]+?)(?:\s+key|\s+keys)?$', goal_clean, re.IGNORECASE)
                raw_keys = hk_m.group(1).strip() if hk_m else "ctrl+c"
                parsed_keys = [k.strip() for k in re.split(r'[\+\s]+', raw_keys) if k.strip()]
            steps.append(DesktopGuiSubsystem.press_hotkey(parsed_keys))
        elif any(w in lower_goal for w in ["click mouse", "mouse click"]):
            m_clk = re.search(r'click\s+(?:mouse\s+)?(?:at\s+)?(\d+)\s+(\d+)', lower_goal)
            cx = int(m_clk.group(1)) if m_clk else 500
            cy = int(m_clk.group(2)) if m_clk else 500
            steps.append(DesktopGuiSubsystem.mouse_click(cx, cy))
        elif any(w in lower_goal for w in ["paint", "pain application", "draw circle", "draw a circle", "draw in paint"]):
            # Stage 1: Probe interactive desktop environment
            steps.append(DesktopGuiSubsystem.probe_desktop_session())
            # Stage 2: Programmatically render high-resolution anti-aliased circle via GDI+
            steps.append(DesktopGuiSubsystem.generate_circle_graphic(radius=160, center_x=300, center_y=300, color="RoyalBlue", fill=True))
            # Stage 3: Launch Paint application with the synthesized graphic
            steps.append(DesktopGuiSubsystem.open_in_paint())
            # Stage 4: If interactive session, attempt live Win32 canvas mouse drag
            steps.append(DesktopGuiSubsystem.live_draw_circle_in_paint(radius=120, center_x=500, center_y=400))

        # Fallback: Generic atomic command execution
        else:
            rec_shell = ShellMatrix.recommend_shell("custom", goal_clean, self.context.pwsh_available)
            steps.append(
                PlanStep(
                    step_id="step-1",
                    title=f"Execute: {goal_clean[:50]}",
                    category=ActionCategory.CUSTOM,
                    raw_intent=goal_clean,
                    target_shell=rec_shell,
                    command=goal_clean,
                )
            )

        total_est = sum(s.timeout_seconds for s in steps)
        return ExecutionPlan(
            plan_id=plan_id,
            goal=goal,
            summary=f"Staged plan with {len(steps)} step(s) to achieve: {goal}",
            steps=steps,
            total_estimated_seconds=total_est,
            requires_admin=requires_admin,
        )
