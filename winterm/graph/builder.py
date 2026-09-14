"""Knowledge Graph Builder: Compiles Windows administration datasets into a NetworkX MultiDiGraph."""

import re
from typing import Dict, Any, Optional
import networkx as nx

from winterm.graph.schema import NodeType, RelationType, GraphNode, GraphEdge
from winterm.graph.datasets.cmdlets_data import CMDLETS_DATA
from winterm.graph.datasets.native_binaries_data import NATIVE_BINARIES_DATA
from winterm.graph.datasets.services_dependency_data import SERVICES_DATA
from winterm.graph.datasets.errors_remedies_data import ERRORS_REMEDIES_DATA
from winterm.graph.hf_ingestor import HuggingFaceIngestor


WIN_COMMAND_SUBSYSTEM_MAP = {
    # StorageNTFS
    "chkdsk": "StorageNTFS", "chkntfs": "StorageNTFS", "compact": "StorageNTFS",
    "convert": "StorageNTFS", "diskcomp": "StorageNTFS", "diskcopy": "StorageNTFS",
    "diskpart": "StorageNTFS", "format": "StorageNTFS", "fsutil": "StorageNTFS",
    "mountvol": "StorageNTFS", "vssadmin": "StorageNTFS", "robocopy": "StorageNTFS",
    "icacls": "StorageNTFS", "takeown": "StorageNTFS", "cipher": "StorageNTFS",
    "bdehdcfg": "StorageNTFS", "manage-bde": "StorageNTFS", "repair-bde": "StorageNTFS",
    "wbadmin": "StorageNTFS", "assign": "StorageNTFS", "attach": "StorageNTFS",
    "attributes": "StorageNTFS", "automount": "StorageNTFS",
    # NetworkFirewall
    "arp": "NetworkFirewall", "atmadm": "NetworkFirewall", "ftp": "NetworkFirewall",
    "ipconfig": "NetworkFirewall", "nbtstat": "NetworkFirewall", "netcfg": "NetworkFirewall",
    "netsh": "NetworkFirewall", "netstat": "NetworkFirewall", "nslookup": "NetworkFirewall",
    "pathping": "NetworkFirewall", "ping": "NetworkFirewall", "route": "NetworkFirewall",
    "rpcping": "NetworkFirewall", "telnet": "NetworkFirewall", "tftp": "NetworkFirewall",
    "tracert": "NetworkFirewall", "winrm": "NetworkFirewall", "winrs": "NetworkFirewall",
    # ServicesTasks
    "sc": "ServicesTasks", "schtasks": "ServicesTasks", "shutdown": "ServicesTasks",
    "logman": "ServicesTasks", "mqsvc": "ServicesTasks", "at": "ServicesTasks",
    # RegistryPolicy
    "reg": "RegistryPolicy", "gpupdate": "RegistryPolicy", "gpresult": "RegistryPolicy",
    "auditpol": "RegistryPolicy",
    # SecurityCrypto
    "whoami": "SecurityCrypto", "certutil": "SecurityCrypto", "runas": "SecurityCrypto",
    "klist": "SecurityCrypto",
    # KernelBoot
    "bcdedit": "KernelBoot", "bootcfg": "KernelBoot", "powercfg": "KernelBoot",
    "pnputil": "KernelBoot", "driverquery": "KernelBoot", "w32tm": "KernelBoot",
    "tzutil": "KernelBoot",
    # DiagnosticsHealth
    "sfc": "DiagnosticsHealth", "dism": "DiagnosticsHealth", "wevtutil": "DiagnosticsHealth",
    "systeminfo": "DiagnosticsHealth", "typeperf": "DiagnosticsHealth", "tracerpt": "DiagnosticsHealth",
    "verifier": "DiagnosticsHealth", "sxstrace": "DiagnosticsHealth", "winsat": "DiagnosticsHealth",
    "winmgmt": "DiagnosticsHealth", "wmic": "DiagnosticsHealth", "openfiles": "DiagnosticsHealth",
    # ProcessMemory
    "tasklist": "ProcessMemory", "taskkill": "ProcessMemory", "qprocess": "ProcessMemory",
}


class KnowledgeGraphBuilder:
    """Compiles disparate Windows datasets into a unified, typed MultiDiGraph."""

    def __init__(self):
        self.graph = nx.MultiDiGraph()

    def build(self) -> nx.MultiDiGraph:
        """Constructs and returns the fully populated Windows Terminal Knowledge Graph."""
        self._add_subsystems()
        self._add_privileges()
        self._add_cmdlets()
        self._add_native_binaries()
        self._add_services()
        self._add_errors_and_remedies()
        self._add_command_alternatives()
        self._add_hf_corpus()
        return self.graph

    def _add_subsystems(self):
        subsystems = [
            ("KernelBoot", "Layer 0: Firmware, BCD, boot configuration, drivers, power management"),
            ("StorageNTFS", "Layer 1: Disks, volumes, BitLocker, VSS shadow copies, NTFS ACLs"),
            ("ProcessMemory", "Layer 2: Processes, threads, priority, memory trimming, handles"),
            ("ServicesTasks", "Layer 3: SCM services, recovery actions, Task Scheduler"),
            ("RegistryPolicy", "Layer 4: Registry hives, typed properties, Group Policy RSoP"),
            ("SecurityCrypto", "Layer 5: Privileges, local security, certificates, Defender"),
            ("NetworkFirewall", "Layer 6: Interfaces, IP routing, Windows Defender Firewall, DNS"),
            ("DiagnosticsHealth", "Layer 7: Event Log, DISM component store, SFC, PerfMon"),
            ("VirtualizationPackages", "Layer 8: WSL, Hyper-V virtualization, winget packages"),
        ]
        for sub_id, desc in subsystems:
            node_id = f"subsystem:{sub_id}"
            self.graph.add_node(
                node_id,
                node_type=NodeType.SUBSYSTEM.value,
                name=sub_id,
                description=desc,
            )

    def _add_privileges(self):
        privileges = [
            ("StandardUser", "Standard non-elevated user token"),
            ("Administrator", "Elevated Administrator token (UAC elevated)"),
            ("SYSTEM", "NT AUTHORITY\\SYSTEM account"),
            ("TrustedInstaller", "NT SERVICE\\TrustedInstaller account"),
        ]
        for priv_id, desc in privileges:
            node_id = f"privilege:{priv_id}"
            self.graph.add_node(
                node_id,
                node_type=NodeType.PRIVILEGE.value,
                name=priv_id,
                description=desc,
            )

    def _add_cmdlets(self):
        for cmdlet_name, meta in CMDLETS_DATA.items():
            cmd_node_id = f"cmdlet:{cmdlet_name.lower()}"
            self.graph.add_node(
                cmd_node_id,
                node_type=NodeType.COMMAND.value,
                name=cmdlet_name,
                description=meta.get("description", ""),
                subsystem=meta.get("subsystem", ""),
                outputs=meta.get("outputs", ""),
                mutates_state=meta.get("mutates_state", False),
                is_cmdlet=True,
            )

            # Link Subsystem
            subsystem = meta.get("subsystem")
            if subsystem:
                sub_node_id = f"subsystem:{subsystem}"
                self.graph.add_edge(cmd_node_id, sub_node_id, relation=RelationType.PART_OF_SUBSYSTEM.value)

            # Link Privilege
            privilege = meta.get("requires_privilege", "StandardUser")
            priv_node_id = f"privilege:{privilege}"
            self.graph.add_edge(cmd_node_id, priv_node_id, relation=RelationType.REQUIRES_PRIVILEGE.value)

            # Parameters
            for param in meta.get("parameters", []):
                clean_param = param.strip()
                param_node_id = f"param:{cmdlet_name.lower()}:{clean_param.lower()}"
                self.graph.add_node(
                    param_node_id,
                    node_type=NodeType.PARAMETER.value,
                    name=clean_param,
                    command=cmdlet_name,
                )
                self.graph.add_edge(cmd_node_id, param_node_id, relation=RelationType.HAS_PARAMETER.value)

            # State Mutation
            if meta.get("mutates_state"):
                entity = meta.get("mutates_entity", "SystemState")
                entity_node_id = f"state:{entity}"
                if not self.graph.has_node(entity_node_id):
                    self.graph.add_node(
                        entity_node_id,
                        node_type=NodeType.STATE_ENTITY.value,
                        name=entity,
                    )
                self.graph.add_edge(cmd_node_id, entity_node_id, relation=RelationType.MUTATES_STATE.value)

    def _add_native_binaries(self):
        for bin_name, meta in NATIVE_BINARIES_DATA.items():
            bin_node_id = f"binary:{bin_name.lower()}"
            self.graph.add_node(
                bin_node_id,
                node_type=NodeType.COMMAND.value,
                name=bin_name,
                description=meta.get("description", ""),
                subsystem=meta.get("subsystem", ""),
                mutates_state=meta.get("mutates_state", False),
                is_native_binary=True,
            )

            # Link Subsystem
            subsystem = meta.get("subsystem")
            if subsystem:
                sub_node_id = f"subsystem:{subsystem}"
                self.graph.add_edge(bin_node_id, sub_node_id, relation=RelationType.PART_OF_SUBSYSTEM.value)

            # Link Privilege
            privilege = meta.get("requires_privilege", "StandardUser")
            priv_node_id = f"privilege:{privilege}"
            self.graph.add_edge(bin_node_id, priv_node_id, relation=RelationType.REQUIRES_PRIVILEGE.value)

            # Parameters & Flags
            for param in meta.get("parameters", []):
                clean_param = param.strip()
                param_node_id = f"param:{bin_name.lower()}:{clean_param.lower()}"
                self.graph.add_node(
                    param_node_id,
                    node_type=NodeType.PARAMETER.value,
                    name=clean_param,
                    command=bin_name,
                )
                self.graph.add_edge(bin_node_id, param_node_id, relation=RelationType.HAS_PARAMETER.value)

            # State Mutation
            if meta.get("mutates_state"):
                entity = meta.get("mutates_entity", "SystemState")
                entity_node_id = f"state:{entity}"
                if not self.graph.has_node(entity_node_id):
                    self.graph.add_node(
                        entity_node_id,
                        node_type=NodeType.STATE_ENTITY.value,
                        name=entity,
                    )
                self.graph.add_edge(bin_node_id, entity_node_id, relation=RelationType.MUTATES_STATE.value)

    def _add_services(self):
        for svc_name, meta in SERVICES_DATA.items():
            svc_node_id = f"service:{svc_name.lower()}"
            self.graph.add_node(
                svc_node_id,
                node_type=NodeType.SERVICE_RESOURCE.value,
                name=svc_name,
                display_name=meta.get("display_name", svc_name),
                description=meta.get("description", ""),
                can_stop_safely=meta.get("can_stop_safely", True),
                default_startup=meta.get("default_startup", "Automatic"),
                risk_if_stopped=meta.get("risk_if_stopped", "LOW"),
                subsystem=meta.get("subsystem", "ServicesTasks"),
            )

            # Subsystem Link
            subsystem = meta.get("subsystem", "ServicesTasks")
            sub_node_id = f"subsystem:{subsystem}"
            self.graph.add_edge(svc_node_id, sub_node_id, relation=RelationType.PART_OF_SUBSYSTEM.value)

            # Explicit Dependencies (Service -> depends_on -> Dependency)
            for dep in meta.get("depends_on", []):
                dep_node_id = f"service:{dep.lower()}"
                if not self.graph.has_node(dep_node_id):
                    self.graph.add_node(
                        dep_node_id,
                        node_type=NodeType.SERVICE_RESOURCE.value,
                        name=dep,
                        display_name=dep,
                        risk_if_stopped="MEDIUM",
                    )
                # svc_node depends on dep_node
                self.graph.add_edge(svc_node_id, dep_node_id, relation=RelationType.DEPENDS_ON.value)
                # dep_node is dependency_of svc_node (blast radius edge)
                self.graph.add_edge(dep_node_id, svc_node_id, relation=RelationType.DEPENDENCY_OF.value)

            # Explicit Dependents
            for child in meta.get("dependents", []):
                child_node_id = f"service:{child.lower()}"
                if not self.graph.has_node(child_node_id):
                    self.graph.add_node(
                        child_node_id,
                        node_type=NodeType.SERVICE_RESOURCE.value,
                        name=child,
                        display_name=child,
                        risk_if_stopped="MEDIUM",
                    )
                # child depends on svc_node
                self.graph.add_edge(child_node_id, svc_node_id, relation=RelationType.DEPENDS_ON.value)
                # svc_node is dependency_of child
                self.graph.add_edge(svc_node_id, child_node_id, relation=RelationType.DEPENDENCY_OF.value)

    def _add_errors_and_remedies(self):
        for err_code, meta in ERRORS_REMEDIES_DATA.items():
            err_node_id = f"error:{err_code.lower()}"
            self.graph.add_node(
                err_node_id,
                node_type=NodeType.ERROR_CODE.value,
                name=meta.get("symbol", err_code),
                error_code=err_code,
                win32_code=meta.get("win32_code"),
                description=meta.get("description", ""),
                contributing_factors=meta.get("contributing_factors", []),
                remediation_chain=meta.get("remediation_chain", []),
                requires_privilege=meta.get("requires_privilege", "StandardUser"),
            )

            # Subsystem Link
            subsystem = meta.get("subsystem")
            if subsystem:
                sub_node_id = f"subsystem:{subsystem}"
                self.graph.add_edge(err_node_id, sub_node_id, relation=RelationType.PART_OF_SUBSYSTEM.value)

            # Privilege Link
            privilege = meta.get("requires_privilege", "StandardUser")
            priv_node_id = f"privilege:{privilege}"
            self.graph.add_edge(err_node_id, priv_node_id, relation=RelationType.REQUIRES_PRIVILEGE.value)

            # Connect remediation commands to error
            for step in meta.get("remediation_chain", []):
                cmd_str = step.get("command", "")
                # Detect core command token from the step
                matched_command = self._find_matching_command_node(cmd_str)
                if matched_command:
                    self.graph.add_edge(
                        matched_command,
                        err_node_id,
                        relation=RelationType.REMEDIATES_ERROR.value,
                        step_action=step.get("action", ""),
                        step_order=step.get("step", 1),
                    )

    def _find_matching_command_node(self, command_text: str) -> Optional[str]:
        """Matches a command text snippet against registered command nodes."""
        cmd_text_lower = command_text.lower()
        # Check cmdlets
        for cmdlet in CMDLETS_DATA:
            if re.search(r"\b" + re.escape(cmdlet.lower()) + r"\b", cmd_text_lower):
                return f"cmdlet:{cmdlet.lower()}"
        # Check binaries
        for binary in NATIVE_BINARIES_DATA:
            base_name = binary.lower().replace(".exe", "")
            if re.search(r"\b" + re.escape(base_name) + r"\b", cmd_text_lower):
                return f"binary:{binary.lower()}"
        return None

    def _add_command_alternatives(self):
        """Cross-links native binaries and PowerShell cmdlets that achieve equivalent outcomes."""
        alternatives = [
            ("cmdlet:get-process", "binary:tasklist.exe"),
            ("cmdlet:stop-process", "binary:taskkill.exe"),
            ("cmdlet:get-service", "binary:sc.exe"),
            ("cmdlet:start-service", "binary:sc.exe"),
            ("cmdlet:stop-service", "binary:sc.exe"),
            ("cmdlet:get-itemproperty", "binary:reg.exe"),
            ("cmdlet:set-itemproperty", "binary:reg.exe"),
            ("cmdlet:clear-dnsclientcache", "binary:ipconfig.exe"),
            ("cmdlet:get-netadapter", "binary:ipconfig.exe"),
            ("cmdlet:get-netroute", "binary:route.exe"),
            ("cmdlet:get-winevent", "binary:wevtutil.exe"),
            ("cmdlet:copy-item", "binary:robocopy.exe"),
        ]
        for src, tgt in alternatives:
            if self.graph.has_node(src) and self.graph.has_node(tgt):
                self.graph.add_edge(src, tgt, relation=RelationType.ALTERNATIVE_TO.value)
                self.graph.add_edge(tgt, src, relation=RelationType.ALTERNATIVE_TO.value)

    def _add_hf_corpus(self):
        """Ingests Windows commands, natural-language intents, and safety rules from HuggingFace corpora."""
        corpus = HuggingFaceIngestor.load_or_ingest()

        # 1. Ingest Windows Commands & Parameters from IAmSomeone/Windows_command
        for cmd_key, meta in corpus.get("commands", {}).items():
            bin_node_id = f"binary:{cmd_key}.exe"
            subsystem = WIN_COMMAND_SUBSYSTEM_MAP.get(cmd_key, "ServicesTasks")
            sub_node_id = f"subsystem:{subsystem}"

            if not self.graph.has_node(bin_node_id):
                self.graph.add_node(
                    bin_node_id,
                    node_type=NodeType.COMMAND.value,
                    name=f"{cmd_key}.exe",
                    description=meta.get("description", ""),
                    syntax=meta.get("syntax", []),
                    applies_to=meta.get("applies_to", ""),
                    subsystem=subsystem,
                    is_native_binary=True,
                    hf_source="IAmSomeone/Windows_command",
                )
                self.graph.add_edge(bin_node_id, sub_node_id, relation=RelationType.PART_OF_SUBSYSTEM.value)
                self.graph.add_edge(bin_node_id, "privilege:StandardUser", relation=RelationType.REQUIRES_PRIVILEGE.value)
            else:
                # Enrich existing binary node
                node_data = self.graph.nodes[bin_node_id]
                if not node_data.get("description") and meta.get("description"):
                    node_data["description"] = meta.get("description")
                if "syntax" not in node_data:
                    node_data["syntax"] = meta.get("syntax", [])
                if "applies_to" not in node_data:
                    node_data["applies_to"] = meta.get("applies_to", "")

            # Attach parameters
            for param_token, param_desc in meta.get("parameters", {}).items():
                clean_param = param_token.strip()
                param_node_id = f"param:{cmd_key}.exe:{clean_param.lower()}"
                if not self.graph.has_node(param_node_id):
                    self.graph.add_node(
                        param_node_id,
                        node_type=NodeType.PARAMETER.value,
                        name=clean_param,
                        description=param_desc,
                        command=f"{cmd_key}.exe",
                    )
                    self.graph.add_edge(bin_node_id, param_node_id, relation=RelationType.HAS_PARAMETER.value)

        # 2. Ingest Safety & Privilege Rules from mshojaei77/terminal-command-execution-sft
        for idx, rule in enumerate(corpus.get("safety_rules", [])):
            safety_node_id = f"safety:{idx}"
            self.graph.add_node(
                safety_node_id,
                node_type=NodeType.SAFETY_RULE.value,
                safety_label=rule.get("safety_label", "safe"),
                skill=rule.get("skill", "unknown"),
                warning=rule.get("warning", ""),
                intent_context=rule.get("intent_context", ""),
                command_sample=rule.get("command_sample", ""),
                shell_family=rule.get("shell_family", "powershell"),
            )

            matched_cmd = self._find_matching_command_node(rule.get("command_sample", "")) or self._find_matching_command_node(rule.get("intent_context", ""))
            if matched_cmd and self.graph.has_node(matched_cmd):
                self.graph.add_edge(matched_cmd, safety_node_id, relation=RelationType.HAS_SAFETY_RULE.value)

        # 3. Ingest Natural Language Intent Mappings from sumit-s-nair/command-dataset
        for idx, item in enumerate(corpus.get("intents", [])):
            intent_node_id = f"intent:{idx}"
            instruction = item.get("instruction", "")
            cmd_text = item.get("command", "")
            self.graph.add_node(
                intent_node_id,
                node_type=NodeType.INTENT.value,
                name=instruction[:60],
                instruction=instruction,
                command=cmd_text,
                shell=item.get("shell", "powershell"),
                intent_type=item.get("intent_type", "others"),
            )

            # Map intent to target command node if matched
            matched_cmd = self._find_matching_command_node(cmd_text)
            if matched_cmd and self.graph.has_node(matched_cmd):
                self.graph.add_edge(
                    intent_node_id,
                    matched_cmd,
                    relation=RelationType.MAPS_TO_COMMAND.value,
                    command_text=cmd_text,
                    shell=item.get("shell", "powershell"),
                )



def build_windows_knowledge_graph() -> nx.MultiDiGraph:
    """Factory helper that instantiates the builder and compiles the complete knowledge graph."""
    builder = KnowledgeGraphBuilder()
    return builder.build()
