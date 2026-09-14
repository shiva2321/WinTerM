"""Layered Safety Sandbox & Circuit Breaker: Enforces capability scopes, prevents runaway loops,
and contains flukes and unexpected OS exceptions to prevent swarm-wide crash cascading.
"""

from __future__ import annotations

import time
import traceback
from typing import Dict, Any, Callable, Optional, Tuple
from pydantic import BaseModel, Field

from winterm.models.context import ShellType
from winterm.models.intent import ActionCategory
from winterm.knowledge.safety_guard import SafetyGuard
from winterm.knowledge.linux_safety import LinuxSafetyGuard
from winterm.swarm.models import AgentScope, AgentPrivilege, SwarmFaultRecord
from winterm.swarm.board import SwarmMessageBoard


class ScopeViolationError(PermissionError):
    """Raised when a sub-agent attempts an action outside its authorized privilege scope."""
    pass


class StepLimitExceededError(RuntimeError):
    """Raised when a sub-agent exceeds its maximum configured execution step quota."""
    pass


class CircuitBreakerTrippedError(RuntimeError):
    """Raised when an isolated sub-agent attempts execution while its circuit breaker is open."""
    pass


class SafeExecutionResult(BaseModel):
    """Encapsulates the outcome of an operation executed inside the fault-tolerant sandbox."""
    success: bool
    result: Any = None
    error: Optional[str] = None
    fluke_contained: bool = False
    duration_ms: int = 0
    fault_record: Optional[SwarmFaultRecord] = None


class CircuitBreaker:
    """Tracks consecutive faults per sub-agent and trips into an isolated state if threshold is met."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.consecutive_failures: int = 0
        self.is_isolated: bool = False
        self.last_failure_time: float = 0.0

    def record_success(self) -> None:
        """Resets the consecutive failure counter upon a verified successful operation."""
        self.consecutive_failures = 0
        self.is_isolated = False

    def record_failure(self) -> bool:
        """Increments failure count and trips isolation if threshold is reached. Returns True if tripped."""
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        if self.consecutive_failures >= self.failure_threshold:
            self.is_isolated = True
            return True
        return False

    def check_state(self) -> None:
        """Verifies if the circuit breaker allows execution."""
        if self.is_isolated:
            # Check if cooldown has elapsed
            if time.time() - self.last_failure_time > self.cooldown_seconds:
                self.is_isolated = False
                self.consecutive_failures = 0
            else:
                raise CircuitBreakerTrippedError(
                    f"Circuit breaker is TRIPPED. Sub-agent is isolated due to {self.consecutive_failures} consecutive faults."
                )

    def reset(self) -> None:
        """Manually resets the circuit breaker."""
        self.consecutive_failures = 0
        self.is_isolated = False


class SubAgentSandbox:
    """Multi-layered security gatekeeper and exception boundary for sub-agent execution."""

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        scope: AgentScope,
        board: Optional[SwarmMessageBoard] = None,
        safety_guard: Optional[SafetyGuard] = None,
        linux_safety_guard: Optional[LinuxSafetyGuard] = None,
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.scope = scope
        self.board = board
        self.safety_guard = safety_guard or SafetyGuard()
        self.linux_safety_guard = linux_safety_guard or LinuxSafetyGuard()
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)
        self.steps_executed: int = 0

    # =========================================================================
    # LAYER 1: PRE-EXECUTION SCOPE & PRIVILEGE ENFORCEMENT
    # =========================================================================

    def validate_action_scope(
        self,
        category: ActionCategory,
        shell: ShellType = ShellType.POWERSHELL_51,
        command: Optional[str] = None,
        is_desktop_interaction: bool = False,
    ) -> None:
        """Validates that the proposed operation strictly conforms to the agent's privilege scope."""
        # 1. Action Category verification
        if category not in self.scope.allowed_action_categories:
            raise ScopeViolationError(
                f"Action category '{category.value}' is NOT permitted under privilege tier '{self.scope.privilege.value}'. "
                f"Allowed categories: {[c.value for c in self.scope.allowed_action_categories]}"
            )

        # 2. Target Shell verification
        if shell not in self.scope.allowed_shells:
            raise ScopeViolationError(
                f"Target shell '{shell.value}' is NOT authorized for agent '{self.agent_name}'. "
                f"Authorized shells: {[s.value for s in self.scope.allowed_shells]}"
            )

        # 3. Desktop / GUI Automation boundary
        if is_desktop_interaction and not self.scope.allow_desktop_interaction:
            raise ScopeViolationError(
                f"Desktop GUI interaction is denied for agent '{self.agent_name}' with privilege '{self.scope.privilege.value}'."
            )

        # 4. Destructive command prevention
        if command:
            if shell in (ShellType.WSL_BASH, ShellType.BASH):
                verdict = self.linux_safety_guard.classify(command)
                if verdict and verdict.is_dangerous and not self.scope.allow_destructive:
                    raise ScopeViolationError(
                        f"Command '{command}' is classified as DESTRUCTIVE ({verdict.risk_level}) and is forbidden under scope."
                    )
            else:
                v = self.safety_guard.classify(command)
                if v and v.is_dangerous and not self.scope.allow_destructive:
                    raise ScopeViolationError(
                        f"Command '{command}' is classified as DESTRUCTIVE ({v.risk_level}) and is forbidden under scope."
                    )

    # =========================================================================
    # LAYER 2: STEP & RATE LIMIT BOUNDARIES
    # =========================================================================

    def increment_step(self) -> None:
        """Enforces upper step limit fences to eliminate runaway loops."""
        self.steps_executed += 1
        if self.steps_executed > self.scope.max_steps:
            raise StepLimitExceededError(
                f"Sub-agent '{self.agent_name}' exceeded maximum permitted execution quota ({self.scope.max_steps} steps)."
            )

    # =========================================================================
    # LAYER 3: FLUKE & EXCEPTION ISOLATION (ZERO SWARM CRASH CASCADE)
    # =========================================================================

    def execute_guarded(
        self,
        action_name: str,
        func: Callable[..., Any],
        *args: Any,
        category: ActionCategory = ActionCategory.DIAGNOSTIC,
        shell: ShellType = ShellType.POWERSHELL_51,
        command: Optional[str] = None,
        is_desktop_interaction: bool = False,
        **kwargs: Any,
    ) -> SafeExecutionResult:
        """Executes an action within the layered safety sandbox, catching any fluke or OS crash."""
        start_time = time.time()
        try:
            # Check circuit breaker
            self.circuit_breaker.check_state()

            # Layer 1: Scope Validation
            self.validate_action_scope(
                category=category,
                shell=shell,
                command=command,
                is_desktop_interaction=is_desktop_interaction,
            )

            # Layer 2: Step Increment
            self.increment_step()

            # Execute the payload
            result = func(*args, **kwargs)

            # Record success
            self.circuit_breaker.record_success()
            duration_ms = int((time.time() - start_time) * 1000)

            return SafeExecutionResult(
                success=True,
                result=result,
                duration_ms=duration_ms,
            )

        except (ScopeViolationError, StepLimitExceededError) as sec_err:
            # Security violations trigger immediate fault logging without crashing caller
            duration_ms = int((time.time() - start_time) * 1000)
            fault = None
            if self.board:
                fault = self.board.record_fault(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    exception_type=sec_err.__class__.__name__,
                    error_message=str(sec_err),
                    attempted_action=action_name,
                    was_isolated=False,
                )

            return SafeExecutionResult(
                success=False,
                error=f"SECURITY_VIOLATION: {str(sec_err)}",
                fluke_contained=True,
                duration_ms=duration_ms,
                fault_record=fault,
            )

        except Exception as exc:
            # Traps any unforeseen OS error, driver fault, or crash fluke
            duration_ms = int((time.time() - start_time) * 1000)
            tripped = self.circuit_breaker.record_failure()
            fault = None
            if self.board:
                fault = self.board.record_fault(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    exception_type=exc.__class__.__name__,
                    error_message=str(exc),
                    attempted_action=action_name,
                    was_isolated=tripped,
                    context={"traceback": traceback.format_exc()},
                )

            return SafeExecutionResult(
                success=False,
                error=f"FLUKE_CONTAINED: [{exc.__class__.__name__}] {str(exc)}",
                fluke_contained=True,
                duration_ms=duration_ms,
                fault_record=fault,
            )
