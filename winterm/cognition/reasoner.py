"""Semantic Reasoner: Produces transparent rationale and alternative rejection traces (The WHY of 5W)."""

from typing import Optional, List, Dict
from winterm.models.intent import PlanStep, ActionCategory
from winterm.models.reasoning import WhyRationale, AlternativeRejected
from winterm.knowledge.commands_db import WindowsCommandDatabase
from winterm.graph.engine import WindowsKnowledgeGraph
import re



class SemanticReasoner:
    """Generates transparent, auditable rationales explaining why commands, switches, and shells were chosen."""

    def __init__(self, graph: Optional[WindowsKnowledgeGraph] = None):
        self.graph = graph or WindowsKnowledgeGraph()

    def explain_step(self, step: PlanStep) -> WhyRationale:
        """Constructs a comprehensive WhyRationale for a PlanStep."""
        cmd = step.command or step.raw_intent
        category = step.category

        # Check knowledge base catalog for predefined rationale
        matched_tpl = None
        for tpl in WindowsCommandDatabase.CATALOG.values():
            if tpl.category == category and (tpl.intent_key in step.step_id or tpl.intent_key in step.raw_intent):
                matched_tpl = tpl
                break

        intent_clar = f"Perform atomic Windows operation: {step.title}"
        justification = ""
        flags_just: Dict[str, str] = {}
        alternatives: List[AlternativeRejected] = []
        pitfalls: List[str] = [
            "Path quoting enforced to avoid whitespace truncation",
            "Non-interactive switches injected to avoid blocking on stdin prompts",
            "UTF-8 console encoding explicitly enforced",
        ]

        if matched_tpl:
            justification = matched_tpl.why
            flags_just.update(matched_tpl.flags_explained)
            if matched_tpl.modern_alternative_to:
                alternatives.append(
                    AlternativeRejected(
                        alternative=matched_tpl.modern_alternative_to,
                        reason=matched_tpl.rejection_reason or "Legacy or non-standard command"
                    )
                )

        # Dynamic reasoning heuristics
        if "Stop-Process" in cmd or "taskkill" in cmd:
            if not justification:
                justification = "Stop-Process terminates unresponsive or target processes cleanly by PID/Name."
            flags_just["-Force"] = "Bypasses confirmation prompts and forcefully halts stubborn or hung threads."
            if "taskkill" not in cmd:
                alternatives.append(
                    AlternativeRejected(
                        alternative="taskkill.exe /F /PID",
                        reason="PowerShell Stop-Process provides integrated error objects and pipeline support."
                    )
                )

        elif "Get-NetTCPConnection" in cmd:
            if not justification:
                justification = "Get-NetTCPConnection queries the TCP/IP stack directly, returning structured objects."
            alternatives.append(
                AlternativeRejected(
                    alternative="netstat -ano | findstr",
                    reason="Netstat output is unstructured text requiring brittle regex parsing and cannot directly inspect process metadata."
                )
            )

        elif "Get-CimInstance" in cmd:
            if not justification:
                justification = "Get-CimInstance uses WS-Management standards compatible across modern PowerShell."
            alternatives.append(
                AlternativeRejected(
                    alternative="Get-WmiObject",
                    reason="Get-WmiObject is legacy DCOM-based and completely removed in PowerShell 7+."
                )
            )

        elif "robocopy" in cmd:
            if not justification:
                justification = "Robocopy provides robust multi-threaded file replication with retry mechanisms for locked files."
            flags_just["/E"] = "Copies subdirectories, including empty ones."
            flags_just["/Z"] = "Copies files in restartable mode."
            alternatives.append(
                AlternativeRejected(
                    alternative="Copy-Item",
                    reason="Copy-Item fails on locked files and lacks built-in retry and verification loops for large hierarchies."
                )
            )

        # Knowledge Graph dynamic alternatives resolution
        tokens = cmd.split()
        first_tok = tokens[0] if tokens else ""
        graph_alts = self.graph.find_command_alternatives(first_tok)
        existing_alt_names = {a.alternative.lower() for a in alternatives}
        for alt in graph_alts:
            if alt.lower() not in existing_alt_names and alt.lower() != first_tok.lower():
                alternatives.append(
                    AlternativeRejected(
                        alternative=alt,
                        reason=f"Knowledge Graph registered alternative for {first_tok}; selected {first_tok} for native shell fidelity and object pipeline support.",
                    )
                )

        if not justification:
            justification = f"Synthesized canonical {step.target_shell.value} command tailored for {step.category.value} tasks."

        return WhyRationale(
            intent_clarification=intent_clar,
            command_justification=justification,
            flags_justification=flags_just,
            alternatives_rejected=alternatives,
            windows_pitfall_mitigations=pitfalls,
        )
