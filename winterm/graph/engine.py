"""Windows Terminal Knowledge Graph Engine: Reasoning, blast radius, validation, and remediation."""

import difflib
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

    def __init__(self, graph: Optional[nx.MultiDiGraph] = None):
        self.graph = graph if graph is not None else build_windows_knowledge_graph()

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
        cmd_node_id = self._resolve_command_node(command)

        if not cmd_node_id or not self.graph.has_node(cmd_node_id):
            # Command itself is unknown - find closest suggestions
            all_cmds = [
                d.get("name")
                for _, d in self.graph.nodes(data=True)
                if d.get("node_type") == NodeType.COMMAND.value
            ]
            matches = difflib.get_close_matches(command, all_cmds, n=3, cutoff=0.5)
            suggestions = {command: matches[0]} if matches else {}
            return ParameterValidationResult(
                command=command,
                is_valid=False,
                unknown_parameters=parameters,
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

        for p in parameters:
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
        """Retrieves all commands registered to a specific subsystem layer."""
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
                cmd_name = self.graph.nodes[source].get("name", "")
                if cmd_name:
                    commands.append(cmd_name)

        return sorted(commands)

    # =========================================================================
    # 6. INTENT SEARCH & GROUNDING (from sumit-s-nair/command-dataset)
    # =========================================================================

    def resolve_intent_to_commands(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Finds closest matching natural-language Windows intents and returns their concrete commands."""
        import re
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
        verdict = SafetyGuard().classify(command_string)
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

        cmd_lower = command_string.lower()
        matched_rules = []

        for node_id, data in self.graph.nodes(data=True):
            if data.get("node_type") == NodeType.SAFETY_RULE.value:
                ctx = data.get("intent_context", "").lower()
                samp = data.get("command_sample", "").lower()
                if samp and (samp in cmd_lower or cmd_lower in samp):
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
        cmd_lower = command.lower().strip()
        # Direct check
        candidates = [
            f"cmdlet:{cmd_lower}",
            f"binary:{cmd_lower}",
            f"binary:{cmd_lower}.exe",
        ]
        for c in candidates:
            if self.graph.has_node(c):
                return c

        # Scan nodes
        for node_id, data in self.graph.nodes(data=True):
            if data.get("node_type") == NodeType.COMMAND.value:
                if data.get("name", "").lower() == cmd_lower:
                    return node_id
        return None

    def _resolve_resource_node(self, resource: str) -> Optional[str]:
        res_lower = resource.lower().strip()
        candidates = [
            f"service:{res_lower}",
            f"state:{res_lower}",
        ]
        for c in candidates:
            if self.graph.has_node(c):
                return c

        for node_id, data in self.graph.nodes(data=True):
            if data.get("node_type") in (NodeType.SERVICE_RESOURCE.value, NodeType.STATE_ENTITY.value):
                if data.get("name", "").lower() == res_lower:
                    return node_id
        return None

    def _resolve_error_node(self, error_sig: str) -> Optional[str]:
        err_lower = error_sig.lower().strip()
        # Check direct ID
        candidate = f"error:{err_lower}"
        if self.graph.has_node(candidate):
            return candidate

        # Check by symbol, code, or win32 code
        for node_id, data in self.graph.nodes(data=True):
            if data.get("node_type") == NodeType.ERROR_CODE.value:
                if (
                    data.get("name", "").lower() == err_lower
                    or data.get("error_code", "").lower() == err_lower
                    or str(data.get("win32_code", "")).lower() == err_lower
                ):
                    return node_id
        return None
