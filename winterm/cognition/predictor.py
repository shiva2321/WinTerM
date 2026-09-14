"""Impact Predictor: State diff simulation, risk assessment, and rollback synthesis (The WHAT HAPPENS AFTER of 5W)."""

import re
from typing import Optional, List, Dict
from winterm.models.intent import PlanStep, ActionCategory
from winterm.models.impact import (
    PredictedImpact,
    RiskLevel,
    StateDiff,
    FileDiff,
    RegDiff,
    ServiceDiff,
    ProcessDiff,
    NetworkDiff,
    RollbackAction,
)
from winterm.models.context import ShellType, ElevationLevel
from winterm.knowledge.elevation_rules import ElevationRules
from winterm.graph.engine import WindowsKnowledgeGraph


class ImpactPredictor:
    """Simulates and forecasts state diffs across Windows subsystems before commands execute."""

    _default_graph: Optional[WindowsKnowledgeGraph] = None

    def __init__(self, graph: Optional[WindowsKnowledgeGraph] = None):
        self.graph = graph or self._get_default_graph()

    @classmethod
    def _get_default_graph(cls) -> WindowsKnowledgeGraph:
        if cls._default_graph is None:
            cls._default_graph = WindowsKnowledgeGraph()
        return cls._default_graph

    @classmethod
    def predict_step_impact(cls, step: PlanStep, graph: Optional[WindowsKnowledgeGraph] = None) -> PredictedImpact:
        """Analyzes a PlanStep and produces a granular impact prediction and rollback plan."""
        kg = graph or (cls._get_default_graph() if isinstance(cls, type) else getattr(cls, "graph", cls._get_default_graph()))
        cmd = step.command or step.raw_intent
        cmd_lower = cmd.lower()
        category = step.category

        risk = RiskLevel.SAFE
        side_effects: List[str] = []
        warnings: List[str] = []
        is_reversible = True
        rollback: Optional[RollbackAction] = None

        state_diff = StateDiff()

        # Check for elevation requirement
        if step.required_elevation == ElevationLevel.ADMIN or ElevationRules.requires_elevation(cmd):
            risk = RiskLevel.ELEVATION_REQUIRED
            warnings.append("Requires Administrative privileges. Will prompt UAC or require elevated shell.")

        # HuggingFace SFT Safety Guard evaluation (early risk escalation only;
        # the final safety classification + warning is applied once at the end).
        safety_info = kg.get_safety_classification(cmd)
        if safety_info.get("is_dangerous"):
            if safety_info.get("safety_label") == "destructive" and risk != RiskLevel.HIGH_DESTRUCTIVE:
                risk = RiskLevel.HIGH_DESTRUCTIVE

        # 1. Process termination
        if "stop-process" in cmd_lower or "taskkill" in cmd_lower:
            risk = RiskLevel.MEDIUM
            proc_id_m = re.search(r'-id\s+(\d+)', cmd_lower)
            pid_str = proc_id_m.group(1) if proc_id_m else "target"
            proc_name = step.metadata.get("process_name") or step.metadata.get("target") or "target"
            state_diff.processes.terminated_processes.append(f"{proc_name} (PID: {pid_str})")
            side_effects.append("Terminating process will discard any unsaved in-memory state or active transactions.")
            is_reversible = False  # Killed process state cannot be magically revived
            warnings.append("Process termination is abrupt (-Force).")

        # 2. Port conflict / Network
        port = step.metadata.get("port")
        if port and "stop-process" in cmd_lower:
            state_diff.network.ports_opened.clear()
            side_effects.append(f"Port {port} will be released and become available for binding.")

        # 3. Service operations
        blast_report = None
        if any(w in cmd_lower for w in ["restart-service", "stop-service", "net stop", "sc stop"]):
            svc_name = step.metadata.get("service_name")
            if not svc_name:
                svc_m = re.search(r'(?:-name\s+|stop\s+)([\w\-]+)', cmd_lower)
                svc_name = svc_m.group(1).strip() if svc_m else "target_service"

            state_diff.services.services_stopped.append(svc_name)
            if "restart-service" in cmd_lower:
                state_diff.services.services_started.append(svc_name)
                side_effects.append(f"Windows service '{svc_name}' will briefly disconnect active client connections.")
            else:
                side_effects.append(f"Windows service '{svc_name}' will be stopped.")

            # Query Knowledge Graph for cascade blast radius
            blast_report = kg.calculate_blast_radius(svc_name, depth=2)
            if blast_report.risk_score in ("CRITICAL", "HIGH"):
                risk = RiskLevel.HIGH_DESTRUCTIVE if blast_report.risk_score == "CRITICAL" else RiskLevel.MEDIUM
                warnings.append(f"Knowledge Graph Alert: {blast_report.impact_summary}")
            elif blast_report.direct_dependents:
                warnings.append(f"Dependent services affected: {', '.join(blast_report.direct_dependents)}")

            rollback = RollbackAction(
                step_id=step.step_id,
                description=f"Restart service {svc_name} if needed",
                command=f"Start-Service -Name '{svc_name}'",
                shell=ShellType.POWERSHELL_51,
                required_elevation=ElevationLevel.ADMIN,
            )

        # 4. Filesystem: Directory / File creation
        elif "new-item" in cmd_lower and "-itemtype directory" in cmd_lower:
            path_m = re.search(r"-path\s+['\"]?([^'\"]+)['\"]?", cmd, re.IGNORECASE)
            created_dir = path_m.group(1).strip() if path_m else "new_directory"
            state_diff.filesystem.created_paths.append(created_dir)
            risk = RiskLevel.SAFE
            rollback = RollbackAction(
                step_id=step.step_id,
                description=f"Remove created directory {created_dir}",
                command=f"if (Test-Path '{created_dir}') {{ Remove-Item -Path '{created_dir}' -Recurse -Force -Confirm:$false }}",
                shell=ShellType.POWERSHELL_51,
            )

        # 5. Filesystem: Deletion / Removal
        elif any(w in cmd_lower for w in ["remove-item", "del /", "rmdir /", "rd /"]):
            path_m = re.search(r"(?:-path\s+['\"]?|del\s+|rd\s+)([^'\"\s]+)", cmd, re.IGNORECASE)
            target_del = path_m.group(1).strip() if path_m else "target_path"
            state_diff.filesystem.deleted_paths.append(target_del)
            risk = RiskLevel.HIGH_DESTRUCTIVE
            side_effects.append(f"Permanent deletion of files/directories under '{target_del}'. Cannot be recovered from Recycle Bin with -Force.")
            warnings.append("Destructive filesystem operation.")
            is_reversible = False

        # 8. Firewall rule creation / modification
        elif "new-netfirewallrule" in cmd_lower:
            risk = RiskLevel.LOW
            rule_name = step.metadata.get("rule_name") or "Firewall_Rule"
            state_diff.network.firewall_rules_altered.append(rule_name)
            side_effects.append(f"Alters Windows Firewall policy to allow or block traffic for rule '{rule_name}'.")
            rollback = RollbackAction(
                step_id=step.step_id,
                description=f"Remove firewall rule '{rule_name}'",
                command=f"Remove-NetFirewallRule -DisplayName '{rule_name}' -ErrorAction SilentlyContinue",
                shell=ShellType.POWERSHELL_51,
                required_elevation=ElevationLevel.ADMIN,
            )

        # 9. Registry modification
        elif any(w in cmd_lower for w in ["set-itemproperty", "new-itemproperty", "reg add"]):
            risk = RiskLevel.MEDIUM
            reg_path = step.metadata.get("path") or "RegistryKey"
            reg_name = step.metadata.get("name") or "Value"
            state_diff.registry.values_modified[f"{reg_path}\\{reg_name}"] = "modified"
            side_effects.append(f"Mutates Windows Registry hive at '{reg_path}'. System behavior or policy may immediately alter.")

        # 10. ACL / File Permission change
        elif any(w in cmd_lower for w in ["icacls", "set-acl", "takeown"]):
            risk = RiskLevel.MEDIUM
            target_p = step.metadata.get("path") or "Path"
            side_effects.append(f"Modifies NTFS Security Descriptors (DACLs) or ownership for '{target_p}'.")
            warnings.append("Changing ACLs can expose sensitive data or break process execution if restricted too far.")

        # 11. Scheduled Task registration
        elif any(w in cmd_lower for w in ["schtasks /create", "register-scheduledtask"]):
            risk = RiskLevel.LOW
            task_n = step.metadata.get("task_name") or "ScheduledTask"
            side_effects.append(f"Registers a background execution trigger in Task Scheduler: '{task_n}'.")
            rollback = RollbackAction(
                step_id=step.step_id,
                description=f"Unregister scheduled task '{task_n}'",
                command=f'schtasks /delete /tn "{task_n}" /f',
                shell=ShellType.CMD,
                required_elevation=ElevationLevel.ADMIN,
            )

        # 12. BitLocker operations
        elif "enable-bitlocker" in cmd_lower or "manage-bde -on" in cmd_lower:
            risk = RiskLevel.HIGH_DESTRUCTIVE
            side_effects.append("Initiates full-disk encryption. CPU I/O will increase during background encryption.")
            warnings.append("Ensure recovery keys are safely backed up before encrypting drive.")

        # 13. Package installation
        elif any(w in cmd_lower for w in ["winget install", "choco install", "scoop install"]):
            risk = RiskLevel.LOW
            side_effects.append("New binaries and PATH entries will be registered in the system.")
            warnings.append("Requires active internet connection and package repository access.")

        # 14. Read-Only queries
        elif any(cmd_lower.startswith(w) for w in ["get-", "select-", "test-", "where-", "findstr", "dir", "type", "powercfg /list", "vssadmin list", "bcdedit"]):
            risk = RiskLevel.READ_ONLY
            side_effects.append("No system state modification. Read-only diagnostic query.")

        # Final safety classification from the deterministic guard / SFT graph
        # (single authoritative pass — runs last so it cannot be overwritten by
        # the heuristic elif chain above).
        safety_info = kg.get_safety_classification(cmd)
        if safety_info.get("is_dangerous"):
            if safety_info.get("safety_label") == "destructive":
                risk = RiskLevel.HIGH_DESTRUCTIVE
            elif risk in (RiskLevel.SAFE, RiskLevel.READ_ONLY):
                risk = RiskLevel.MEDIUM
            if safety_info.get("warning"):
                warnings.append(f"Safety Guard Alert: {safety_info.get('warning')}")
            else:
                warnings.append(f"Safety Guard Alert: Classified as '{safety_info.get('safety_label')}' (skill: {safety_info.get('skill')}).")

        return PredictedImpact(
            step_id=step.step_id,
            risk_level=risk,
            state_diff=state_diff,
            side_effects=side_effects,
            warnings=warnings,
            is_reversible=is_reversible,
            rollback=rollback,
            blast_radius=blast_report.model_dump() if blast_report else None,
        )
