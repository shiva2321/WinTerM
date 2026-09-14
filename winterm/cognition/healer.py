"""Error Healer: Autonomous diagnosis, remedy proposal, and self-healing execution."""

import re
from typing import Optional, Tuple
from winterm.models.result import ExecutionResult, SelfHealingProposal
from winterm.knowledge.error_catalog import WindowsErrorCatalog
from winterm.engine.executor import WindowsShellExecutor
from winterm.models.context import ShellType
from winterm.graph.engine import WindowsKnowledgeGraph


class ErrorHealer:
    """Diagnoses Windows terminal execution failures and coordinates self-healing recovery."""

    def __init__(
        self,
        executor: Optional[WindowsShellExecutor] = None,
        graph: Optional[WindowsKnowledgeGraph] = None,
    ):
        self.executor = executor or WindowsShellExecutor(default_shell=ShellType.POWERSHELL_51)
        self.graph = graph or WindowsKnowledgeGraph()

    def diagnose_failure(self, exec_result: ExecutionResult) -> Optional[SelfHealingProposal]:
        """Analyzes an ExecutionResult and produces a SelfHealingProposal if a known root cause is detected."""
        if exec_result.success:
            return None

        proposal = WindowsErrorCatalog.diagnose(
            stderr=exec_result.stderr,
            stdout=exec_result.stdout,
            exit_code=exec_result.exit_code,
            failed_command=exec_result.command,
        )

        # Search knowledge graph for HRESULT / Win32 codes in stderr
        combined_text = f"{exec_result.stderr} {exec_result.stdout}"
        hresult_match = re.search(r"\b(0x[0-9a-fA-F]{8})\b", combined_text)
        error_code = hresult_match.group(1) if hresult_match else None

        if error_code:
            remediation = self.graph.find_remediation_chains(error_code)
            if remediation:
                first_step_cmd = remediation.remediation_steps[0].get("command", "") if remediation.remediation_steps else ""
                if not proposal:
                    proposal = SelfHealingProposal(
                        error_signature=remediation.error_code,
                        root_cause=remediation.root_cause,
                        remedy_explanation="Execute Knowledge Graph multi-step remediation",
                        healing_command=first_step_cmd,
                        healing_shell=ShellType.POWERSHELL_51,
                        requires_elevation=remediation.required_privileges == ["Administrator"],
                    )
                elif not proposal.healing_command and first_step_cmd:
                    proposal.healing_command = first_step_cmd

        return proposal

    def attempt_auto_heal(self, proposal: SelfHealingProposal) -> ExecutionResult:
        """Executes the proposed self-healing remedy."""
        if not proposal.healing_command:
            return ExecutionResult(
                step_id="heal-attempt",
                command="",
                shell=proposal.healing_shell,
                success=False,
                stderr="No executable healing command provided in proposal.",
            )

        return self.executor.execute(
            proposal.healing_command,
            shell=proposal.healing_shell,
            step_id="heal-attempt",
            timeout_seconds=30,
            auto_diagnose=False,
        )
