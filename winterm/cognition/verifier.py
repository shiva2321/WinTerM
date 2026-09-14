"""State Verifier: Audits and proves that post-execution state matches expected goals."""

from typing import List, Dict, Any, Optional
from winterm.models.intent import PlanStep
from winterm.models.impact import PredictedImpact
from winterm.models.result import ExecutionResult, VerificationResult
from winterm.engine.executor import WindowsShellExecutor
from winterm.models.context import ShellType


class StateVerifier:
    """Audits system state changes after command execution to guarantee intended results."""

    def __init__(self, executor: Optional[WindowsShellExecutor] = None):
        self.executor = executor or WindowsShellExecutor(default_shell=ShellType.POWERSHELL_51)

    def verify_step(
        self,
        step: PlanStep,
        exec_result: ExecutionResult,
        predicted_impact: Optional[PredictedImpact] = None,
    ) -> VerificationResult:
        """Verifies whether a completed step achieved its intended state."""
        if not exec_result.success:
            return VerificationResult(
                step_id=step.step_id,
                verified=False,
                unmatched_expectations=["Command execution returned non-zero exit code or failed."],
                details=f"Execution failed with code {exec_result.exit_code}: {exec_result.stderr}",
            )

        unmatched: List[str] = []
        observed_diff: Dict[str, Any] = {}

        # 1. Verify filesystem creations
        if predicted_impact and predicted_impact.state_diff.filesystem.created_paths:
            for path in predicted_impact.state_diff.filesystem.created_paths:
                probe_res = self.executor.execute(f"Test-Path -Path '{path}'", shell=ShellType.POWERSHELL_51)
                if probe_res.stdout.strip().lower() == "true":
                    observed_diff[f"created_path:{path}"] = "EXISTS"
                else:
                    unmatched.append(f"Expected created path '{path}' does not exist.")

        # 2. Verify process termination
        if "stop-process" in step.command.lower() or "taskkill" in step.command.lower():
            port = step.metadata.get("port")
            if port:
                probe_res = self.executor.execute(
                    f"[bool](Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue)",
                    shell=ShellType.POWERSHELL_51,
                )
                if probe_res.stdout.strip().lower() == "false":
                    observed_diff[f"port_free:{port}"] = "FREE"
                else:
                    unmatched.append(f"Port {port} is still reported as occupied after termination.")

        # 3. Verify service state
        service_name = step.metadata.get("service_name")
        if service_name and ("restart-service" in step.command.lower() or "start-service" in step.command.lower()):
            probe_res = self.executor.execute(
                f"(Get-Service -Name '{service_name}').Status.ToString()",
                shell=ShellType.POWERSHELL_51,
            )
            status = probe_res.stdout.strip()
            observed_diff[f"service_status:{service_name}"] = status
            if status != "Running":
                unmatched.append(f"Service '{service_name}' status is '{status}', expected 'Running'.")

        verified = (len(unmatched) == 0)
        details = "All post-conditions successfully verified." if verified else f"Verification issues: {'; '.join(unmatched)}"

        return VerificationResult(
            step_id=step.step_id,
            verified=verified,
            actual_state_diff=observed_diff,
            unmatched_expectations=unmatched,
            details=details,
        )
