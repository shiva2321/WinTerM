"""Windows Terminal Knowledge Graph Engine: Reasoning, blast radius, validation, and remediation."""

import difflib
import threading
from typing import Dict, Any, List, Optional, Set, Tuple
import networkx as nx

from winterm.graph.schema import (
    NodeType,
    RelationType,
    BlastRadiusReport,
    RemediationPath,
    ParameterValidationResult,
)
from winterm.graph.builder import build_windows_knowledge_graph


class WindowsKnowledgeGraph:
    """Deterministic, graph-theoretic reasoning engine for Windows terminal operations."""

    _SHARED_GRAPH: Optional[nx.MultiDiGraph] = None
    _SHARED_CMD_INDEX: Optional[Dict[str, str]] = None
    _SHARED_RES_INDEX: Optional[Dict[str, str]] = None
    _SHARED_ERR_INDEX: Optional[Dict[str, str]] = None
    _SHARED_LOCK: threading.Lock = threading.Lock()

    @staticmethod
    def _build_indices(graph: nx.MultiDiGraph) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
        cmd_index: Dict[str, str] = {}
        res_index: Dict[str, str] = {}
        err_index: Dict[str, str] = {}
        for node_id, data in graph.nodes(data=True):
            nt = data.get("node_type")
            name = str(data.get("name") or "").lower()
            if nt == NodeType.COMMAND.value:
                if name:
                    cmd_index[name] = node_id
                if name.endswith(".exe"):
                    cmd_index[name[:-4]] = node_id
            elif nt in (NodeType.SERVICE_RESOURCE.value, NodeType.STATE_ENTITY.value):
                if name:
                    res_index[name] = node_id
            elif nt == NodeType.ERROR_CODE.value:
                if name:
                    err_index[name] = node_id
                ec = data.get("error_code")
                if ec:
                    err_index[str(ec).lower()] = node_id
                wc = data.get("win32_code")
                # Only index real numeric win32 codes -- ``str(None) == "None"``
                # previously polluted the index with a bogus "none" key.
                if isinstance(wc, int) and not isinstance(wc, bool):
                    err_index[str(wc)] = node_id
        return cmd_index, res_index, err_index

    def __init__(self, graph: Optional[nx.MultiDiGraph] = None):
        if graph is None:
            # Double-checked locking so concurrent agent sessions never build the
            # shared graph twice or observe a partially initialised index set.
            if WindowsKnowledgeGraph._SHARED_GRAPH is None:
                with WindowsKnowledgeGraph._SHARED_LOCK:
                    if WindowsKnowledgeGraph._SHARED_GRAPH is None:
                        built = build_windows_knowledge_graph()
                        c_idx, r_idx, e_idx = self._build_indices(built)
                        WindowsKnowledgeGraph._SHARED_CMD_INDEX = c_idx
                        WindowsKnowledgeGraph._SHARED_RES_INDEX = r_idx
                        WindowsKnowledgeGraph._SHARED_ERR_INDEX = e_idx
                        WindowsKnowledgeGraph._SHARED_GRAPH = built
            self.graph = WindowsKnowledgeGraph._SHARED_GRAPH
            self._cmd_index = WindowsKnowledgeGraph._SHARED_CMD_INDEX or {}
            self._res_index = WindowsKnowledgeGraph._SHARED_RES_INDEX or {}
            self._err_index = WindowsKnowledgeGraph._SHARED_ERR_INDEX or {}
        else:
            self.graph = graph
            c_idx, r_idx, e_idx = self._build_indices(graph)
            self._cmd_index = c_idx
            self._res_index = r_idx
            self._err_index = e_idx

    @staticmethod
    def _as_str(value: Any) -> str:
        """Coerces arbitrary input to a safe string (None/bool/int -> str)."""
        if isinstance(value, str):
            return value
        if value is None:
            return ""
        return str(value)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns node and edge topological counts across the graph."""
        node_types: Dict[str, int] = {}
        for _, data in self.graph.nodes(data=True):
            nt = data.get("node_type", "unknown")
            node_types[nt] = node_types.get(nt, 0) + 1

        relation_types: Dict[str, int] = {}
        for _, _, data in self.graph.edges(data=True):
            rel = data.get("relation", "unknown")
            relation_types[rel] = relation_types.get(rel, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_type_counts": node_types,
            "relation_type_counts": relation_types,
        }

    # =========================================================================
    # 1. BLAST RADIUS CASCADE ANALYSIS
    # =========================================================================

    def calculate_blast_radius(self, resource_name: str, depth: int = 2) -> BlastRadiusReport:
        """Calculates direct and cascading downstream entities affected if a service/resource is stopped or altered."""
        resource_name = self._as_str(resource_name)
        if not resource_name.strip():
            return BlastRadiusReport(
                root_node_id="",
                risk_score="LOW",
                impact_summary="No resource name supplied.",
            )
        # Normalize resource node ID
        node_id = self._resolve_resource_node(resource_name)
        if not node_id or not self.graph.has_node(node_id):
            return BlastRadiusReport(
                root_node_id=resource_name,
                risk_score="LOW",
                impact_summary=f"Resource '{resource_name}' is unindexed or has zero registered system dependencies.",
            )

        root_data = self.graph.nodes[node_id]
        direct_dependents: Set[str] = set()
        cascading_dependents: Set[str] = set()
        visited: Set[str] = {node_id}

        # Step 1: Direct dependents (immediate children whose functioning depends on this resource)
        for _, target, data in self.graph.out_edges(node_id, data=True):
            if data.get("relation") == RelationType.DEPENDENCY_OF.value:
                dep_name = self.graph.nodes[target].get("name", target)
                direct_dependents.add(dep_name)
                visited.add(target)

        # Also check incoming DEPENDS_ON edges
        for source, _, data in self.graph.in_edges(node_id, data=True):
            if data.get("relation") == RelationType.DEPENDS_ON.value:
                dep_name = self.graph.nodes[source].get("name", source)
                direct_dependents.add(dep_name)
                visited.add(source)

        # Step 2: Multi-hop cascading traversal (depth >= 2)
        current_layer = [self._resolve_resource_node(d) for d in direct_dependents if self._resolve_resource_node(d)]
        max_traversed_depth = 1 if direct_dependents else 0

        for current_depth in range(2, depth + 1):
            next_layer = []
            for curr_node in current_layer:
                if not curr_node:
                    continue
                # Traverse DEPENDENCY_OF outgoing
                for _, target, data in self.graph.out_edges(curr_node, data=True):
                    if data.get("relation") == RelationType.DEPENDENCY_OF.value and target not in visited:
                        dep_name = self.graph.nodes[target].get("name", target)
                        cascading_dependents.add(dep_name)
                        visited.add(target)
                        next_layer.append(target)
                # Traverse DEPENDS_ON incoming
                for source, _, data in self.graph.in_edges(curr_node, data=True):
                    if data.get("relation") == RelationType.DEPENDS_ON.value and source not in visited:
                        dep_name = self.graph.nodes[source].get("name", source)
                        cascading_dependents.add(dep_name)
                        visited.add(source)
                        next_layer.append(source)

            if next_layer:
                max_traversed_depth = current_depth
                current_layer = next_layer
            else:
                break

        # Step 3: Mutated states
        mutated_states = []
        for _, target, data in self.graph.out_edges(node_id, data=True):
            if data.get("relation") == RelationType.MUTATES_STATE.value:
                mutated_states.append(self.graph.nodes[target].get("name", target))

        # Step 4: Risk scoring
        risk_score = root_data.get("risk_if_stopped", "LOW")
        can_stop = root_data.get("can_stop_safely", True)
        total_affected = len(direct_dependents) + len(cascading_dependents)

        if not can_stop or risk_score == "CRITICAL" or total_affected >= 5:
            risk = "CRITICAL"
        elif risk_score == "HIGH" or total_affected >= 2:
            risk = "HIGH"
        elif total_affected >= 1:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        summary = (
            f"Halting or altering '{root_data.get('name', resource_name)}' directly impacts "
            f"{len(direct_dependents)} services ({', '.join(sorted(direct_dependents)) or 'none'}), "
            f"and induces cascading failures in {len(cascading_dependents)} downstream components "
            f"({', '.join(sorted(cascading_dependents)) or 'none'}). "
            f"Overall blast radius risk: {risk}."
        )

        return BlastRadiusReport(
            root_node_id=root_data.get("name", resource_name),
            direct_dependents=sorted(list(direct_dependents)),
            cascading_dependents=sorted(list(cascading_dependents)),
            mutated_states=mutated_states,
            risk_score=risk,
            blast_radius_depth=max_traversed_depth,
            impact_summary=summary,
        )

    # =========================================================================
    # 2. PARAMETER HALLUCINATION CHECK & VALIDATION
    # =========================================================================

    def validate_command_parameters(self, command: str, parameters: List[str]) -> ParameterValidationResult:
        """Validates that a cmdlet or native binary and all supplied parameters exist in the Knowledge Graph."""
        command = self._as_str(command)
        clean_parameters = [self._as_str(p) for p in (parameters or []) if p is not None]
        if not command.strip():
            return ParameterValidationResult(
                command="",
                is_valid=False,
                unknown_parameters=clean_parameters,
            )
        cmd_node_id = self._resolve_command_node(command)

        if not cmd_node_id or not self.graph.has_node(cmd_node_id):
            # Command itself is unknown - find closest suggestions
            all_cmds = [
                d.get("name")
                for _, d in self.graph.nodes(data=True)
                if d.get("node_type") == NodeType.COMMAND.value and d.get("name")
            ]
            matches = difflib.get_close_matches(command, all_cmds, n=3, cutoff=0.5)
            suggestions = {command: matches[0]} if matches else {}
            return ParameterValidationResult(
                command=command,
                is_valid=False,
                unknown_parameters=clean_parameters,
                suggestions=suggestions,
            )

        # Retrieve all valid parameter names for this command
        valid_param_nodes = [
            self.graph.nodes[target].get("name", "")
            for _, target, data in self.graph.out_edges(cmd_node_id, data=True)
            if data.get("relation") == RelationType.HAS_PARAMETER.value
        ]
        valid_param_lookup = {p.lower(): p for p in valid_param_nodes}

        valid_params: List[str] = []
        unknown_params: List[str] = []
        suggestions: Dict[str, str] = {}

        for p in clean_parameters:
            p_clean = p.strip().lower()
            # In Windows PowerShell, flags often begin with '-', in CMD with '/'
            # Check direct match
            if p_clean in valid_param_lookup:
                valid_params.append(valid_param_lookup[p_clean])
            # Check with leading dash / slash
            elif f"-{p_clean}" in valid_param_lookup:
                valid_params.append(valid_param_lookup[f"-{p_clean}"])
            elif f"/{p_clean}" in valid_param_lookup:
                valid_params.append(valid_param_lookup[f"/{p_clean}"])
            else:
                unknown_params.append(p)
                # Find closest parameter match
                matches = difflib.get_close_matches(p, valid_param_nodes, n=1, cutoff=0.5)
                if matches:
                    suggestions[p] = matches[0]

        is_valid = len(unknown_params) == 0

        return ParameterValidationResult(
            command=self.graph.nodes[cmd_node_id].get("name", command),
            is_valid=is_valid,
            valid_parameters=valid_params,
            unknown_parameters=unknown_params,
            suggestions=suggestions,
        )

    # =========================================================================
    # 3. ERROR REMEDIATION PATHFINDING
    # =========================================================================

    def find_remediation_chains(self, error_signature: str) -> Optional[RemediationPath]:
        """Resolves an error signature (HRESULT, Win32 code, or Exception name) to a graph remediation path."""
        error_signature = self._as_str(error_signature)
        if not error_signature.strip():
            return None
        err_node_id = self._resolve_error_node(error_signature)
        if not err_node_id or not self.graph.has_node(err_node_id):
            return None

        node_data = self.graph.nodes[err_node_id]
        remediation_chain = node_data.get("remediation_chain", [])
        required_priv = node_data.get("requires_privilege", "StandardUser")

        return RemediationPath(
            error_code=node_data.get("error_code", error_signature),
            root_cause=node_data.get("description", ""),
            remediation_steps=remediation_chain,
            required_privileges=[required_priv],
        )

    # =========================================================================
    # 4. COMMAND ALTERNATIVES
    # =========================================================================

    def find_command_alternatives(self, command: str) -> List[str]:
        """Discovers equivalent native binaries for PowerShell cmdlets or vice-versa."""
        command = self._as_str(command)
        if not command.strip():
            return []
        cmd_node_id = self._resolve_command_node(command)
        if not cmd_node_id or not self.graph.has_node(cmd_node_id):
            return []

        alternatives = []
        for _, target, data in self.graph.out_edges(cmd_node_id, data=True):
            if data.get("relation") == RelationType.ALTERNATIVE_TO.value:
                alt_name = self.graph.nodes[target].get("name", "")
                if alt_name:
                    alternatives.append(alt_name)

        return sorted(alternatives)

    # =========================================================================
    # 5. SUBSYSTEM QUERYING
    # =========================================================================

    def get_subsystem_commands(self, subsystem_name: str) -> List[str]:
        """Retrieves all *command* nodes registered to a specific subsystem layer."""
        subsystem_name = self._as_str(subsystem_name)
        if not subsystem_name.strip():
            return []
        sub_node_id = f"subsystem:{subsystem_name}"
        if not self.graph.has_node(sub_node_id):
            # Try case-insensitive lookup
            for n in self.graph.nodes:
                if n.lower() == sub_node_id.lower():
                    sub_node_id = n
                    break

        commands = []
        for source, _, data in self.graph.in_edges(sub_node_id, data=True):
            if data.get("relation") == RelationType.PART_OF_SUBSYSTEM.value:
                if self.graph.nodes[source].get("node_type") != NodeType.COMMAND.value:
                    continue
                cmd_name = self.graph.nodes[source].get("name", "")
                if cmd_name:
                    commands.append(cmd_name)

        return sorted(set(commands))

    # =========================================================================
    # 6. INTENT SEARCH & GROUNDING (from sumit-s-nair/command-dataset)
    # =========================================================================

    def resolve_intent_to_commands(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Finds closest matching natural-language Windows intents and returns their concrete commands."""
        import re
        query = self._as_str(query)
        query_words = set(re.findall(r"\w+", query.lower()))
        if not query_words:
            return []

        scored_matches = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get("node_type") == NodeType.INTENT.value:
                instr = data.get("instruction", "")
                instr_words = set(re.findall(r"\w+", instr.lower()))
                if not instr_words:
                    continue
                intersection = query_words.intersection(instr_words)
                if not intersection:
                    continue
                score = len(intersection) / float(len(query_words.union(instr_words)))
                if query.lower() in instr.lower():
                    score += 0.5
                scored_matches.append((score, data))

        scored_matches.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, item in scored_matches[:top_k]:
            results.append({
                "instruction": item.get("instruction"),
                "command": item.get("command"),
                "shell": item.get("shell"),
                "intent_type": item.get("intent_type"),
                "relevance_score": round(score, 3),
            })
        return results

    # =========================================================================
    # 7. COMMAND DOCUMENTATION & SYNTAX (from IAmSomeone/Windows_command)
    # =========================================================================

    def get_command_documentation(self, command: str) -> Optional[Dict[str, Any]]:
        """Retrieves official Microsoft syntax, parameter dictionary, and usage docs."""
        command = self._as_str(command)
        if not command.strip():
            return None
        cmd_node_id = self._resolve_command_node(command)
        if not cmd_node_id or not self.graph.has_node(cmd_node_id):
            return None

        node_data = self.graph.nodes[cmd_node_id]
        params = {}
        for _, target, data in self.graph.out_edges(cmd_node_id, data=True):
            if data.get("relation") == RelationType.HAS_PARAMETER.value:
                p_data = self.graph.nodes[target]
                params[p_data.get("name", target)] = p_data.get("description", "")

        return {
            "name": node_data.get("name", command),
            "description": node_data.get("description", ""),
            "syntax": node_data.get("syntax", []),
            "applies_to": node_data.get("applies_to", ""),
            "subsystem": node_data.get("subsystem", ""),
            "parameters": params,
        }

    # =========================================================================
    # 8. SAFETY & PRIVILEGE CLASSIFICATION (from mshojaei77/terminal-command-execution-sft)
    # =========================================================================

    def get_safety_classification(self, command_string: str) -> Dict[str, Any]:
        """Classifies safety level, detected warnings, and operational risk tiers.

        A deterministic :class:`SafetyGuard` runs first so destructive commands
        (deletion of protected paths, power control, registry surgery) can never
        fall through to ``safe`` when the SFT graph rules are too sparse to
        match. Graph rules enrich the result only when the guard is neutral.
        """
        from winterm.knowledge.safety_guard import SafetyGuard

        # Deterministic first pass — never fail-open on destructive commands.
        verdict = SafetyGuard().classify(self._as_str(command_string))
        if verdict is not None and verdict.label in ("destructive", "privileged"):
            return {
                "safety_label": verdict.label,
                "skill": verdict.skill,
                "warning": verdict.warning,
                "is_dangerous": verdict.is_dangerous,
            }
        # A read-only query is authoritatively safe — the sparse SFT graph rules
        # must not downgrade it to network_sensitive or privileged.
        if verdict is not None and verdict.label == "safe":
            return {
                "safety_label": "safe",
                "skill": verdict.skill,
                "warning": verdict.warning,
                "is_dangerous": False,
            }

        cmd_lower = self._as_str(command_string).lower()
        matched_rules = []

        for node_id, data in self.graph.nodes(data=True):
            if data.get("node_type") == NodeType.SAFETY_RULE.value:
                ctx = str(data.get("intent_context") or "").lower()
                samp = str(data.get("command_sample") or "").lower()
                # Containment must be *forward* (sample inside command) and
                # non-trivial; the previous bidirectional test made an empty
                # command match every rule and thus classify as destructive.
                if samp and len(samp) >= 6 and len(cmd_lower) >= 4 and samp in cmd_lower:
                    matched_rules.append(data)
                elif ctx and any(w in cmd_lower for w in ctx.split() if len(w) > 4):
                    matched_rules.append(data)

        if matched_rules:
            severity_order = {"destructive": 4, "credential_sensitive": 3, "privileged": 2, "network_sensitive": 1, "safe": 0}
            matched_rules.sort(key=lambda r: severity_order.get(r.get("safety_label", "safe"), 0), reverse=True)
            top_rule = matched_rules[0]
            # Prefer the deterministic guard's network-sensitive verdict if the
            # graph only produced a weaker classification.
            if verdict is not None and severity_order.get(verdict.label, 0) > severity_order.get(top_rule.get("safety_label", "safe"), 0):
                return {
                    "safety_label": verdict.label,
                    "skill": verdict.skill,
                    "warning": verdict.warning,
                    "is_dangerous": verdict.is_dangerous,
                }
            return {
                "safety_label": top_rule.get("safety_label", "safe"),
                "skill": top_rule.get("skill", "unknown"),
                "warning": top_rule.get("warning", ""),
                "is_dangerous": top_rule.get("safety_label") in ("destructive", "credential_sensitive", "privileged"),
            }

        # Network-sensitive verdict from the deterministic guard is still useful
        # even though the graph found no rule.
        if verdict is not None:
            return {
                "safety_label": verdict.label,
                "skill": verdict.skill,
                "warning": verdict.warning,
                "is_dangerous": verdict.is_dangerous,
            }

        return {
            "safety_label": "safe",
            "skill": "general",
            "warning": "",
            "is_dangerous": False,
        }


    # =========================================================================
    # INTERNAL RESOLUTION HELPERS
    # =========================================================================

    def _resolve_command_node(self, command: str) -> Optional[str]:
        cmd_lower = self._as_str(command).lower().strip()
        if not cmd_lower:
            return None
        candidates = [
            f"cmdlet:{cmd_lower}",
            f"binary:{cmd_lower}",
            f"binary:{cmd_lower}.exe",
        ]
        for c in candidates:
            if self.graph.has_node(c):
                return c
        return self._cmd_index.get(cmd_lower)

    def _resolve_resource_node(self, resource: str) -> Optional[str]:
        res_lower = self._as_str(resource).lower().strip()
        if not res_lower:
            return None
        candidates = [
            f"service:{res_lower}",
            f"state:{res_lower}",
        ]
        for c in candidates:
            if self.graph.has_node(c):
                return c
        return self._res_index.get(res_lower)

    def _resolve_error_node(self, error_sig: str) -> Optional[str]:
        err_lower = self._as_str(error_sig).lower().strip()
        if not err_lower:
            return None
        candidate = f"error:{err_lower}"
        if self.graph.has_node(candidate):
            return candidate
        return self._err_index.get(err_lower)
