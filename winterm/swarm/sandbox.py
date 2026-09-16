"""Layered Safety Sandbox & Circuit Breaker: Enforces capability scopes, prevents runaway loops,
and contains flukes and unexpected OS exceptions to prevent swarm-wide crash cascading.
"""

from __future__ import annotations

import re
import logging
import threading
import time
import traceback
from collections import deque
from typing import Dict, Any, Callable, Optional, Tuple
from pydantic import BaseModel, Field

from winterm.models.context import ShellType
from winterm.models.intent import ActionCategory
from winterm.knowledge.safety_guard import SafetyGuard
from winterm.knowledge.linux_safety import LinuxSafetyGuard
from winterm.swarm.models import AgentScope, AgentPrivilege, SwarmFaultRecord
from winterm.swarm.board import SwarmMessageBoard

logger = logging.getLogger("winterm.swarm.sandbox")

# Verbs/cmdlets that mutate the filesystem. Used to enforce ``allow_file_write``
# independently of the (untrusted) ``category`` reported by the caller.
_WINDOWS_WRITE_PATTERNS = [
    re.compile(r"\bout-file\b", re.IGNORECASE),
    re.compile(r"\bset-content\b", re.IGNORECASE),
    re.compile(r"\badd-content\b", re.IGNORECASE),
    re.compile(r"\bclear-content\b", re.IGNORECASE),
    re.compile(r"\bnew-item\b", re.IGNORECASE),
    re.compile(r"\bnew-itemproperty\b", re.IGNORECASE),
    re.compile(r"\bset-item\b", re.IGNORECASE),
    re.compile(r"\bset-itemproperty\b", re.IGNORECASE),
    re.compile(r"\bcopy-item\b", re.IGNORECASE),
    re.compile(r"\bmove-item\b", re.IGNORECASE),
    re.compile(r"\brename-item\b", re.IGNORECASE),
    re.compile(r"\bremove-item\b", re.IGNORECASE),
    re.compile(r"\bexport-csv\b", re.IGNORECASE),
    re.compile(r"\bexport-clixml\b", re.IGNORECASE),
    re.compile(r"\bset-acl\b", re.IGNORECASE),
    re.compile(r"\bicacls\b", re.IGNORECASE),
    re.compile(r"\btakeown\b", re.IGNORECASE),
    re.compile(r"\breg\s+(add|delete|import|copy|save|restore)\b", re.IGNORECASE),
    re.compile(r"\bmkdir\b", re.IGNORECASE),
    re.compile(r"\bmd\b", re.IGNORECASE),
    re.compile(r"\bcopy\b", re.IGNORECASE),
    re.compile(r"\bmove\b", re.IGNORECASE),
    re.compile(r"\bren\b", re.IGNORECASE),
    re.compile(r"\btypenul\b", re.IGNORECASE),
    # Redirection to a file (ignores benign fd duplications like 2>&1).
    re.compile(r"(?<![0-9&])>(?!&)\s*[^\s&]"),
]

_POSIX_WRITE_PATTERNS = [
    re.compile(r"\btee\b", re.IGNORECASE),
    re.compile(r"\b(?:cp|mv|mkdir|touch|rm|dd|install|ln|chmod|chown)\b"),
    re.compile(r"\bsed\s+-i\b"),
    re.compile(r"\btruncate\b"),
    re.compile(r"(?<![0-9&])>>?(?!&)\s*[^\s&]"),
]


class ScopeViolationError(PermissionError):
    """Raised when a sub-agent attempts an action outside its authorized privilege scope."""
    pass


class StepLimitExceededError(RuntimeError):
    """Raised when a sub-agent exceeds its maximum configured execution step quota."""
    pass


class CircuitBreakerTrippedError(RuntimeError):
    """Raised when an isolated sub-agent attempts execution while its circuit breaker is open."""
    pass


class RateLimitExceededError(RuntimeError):
    """Raised when a sub-agent exceeds its configured per-minute action rate limit."""
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
        self._lock = threading.Lock()

    def record_success(self) -> None:
        """Resets the consecutive failure counter upon a verified successful operation."""
        with self._lock:
            self.consecutive_failures = 0
            self.is_isolated = False

    def record_failure(self) -> bool:
        """Increments failure count and trips isolation if threshold is reached. Returns True if tripped."""
        with self._lock:
            self.consecutive_failures += 1
            self.last_failure_time = time.time()
            if self.consecutive_failures >= self.failure_threshold:
                self.is_isolated = True
                return True
            return False

    def check_state(self) -> None:
        """Verifies if the circuit breaker allows execution."""
        with self._lock:
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
        with self._lock:
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
        self._lock = threading.Lock()
        self._action_times: deque = deque()

    # =========================================================================
    # LAYER 1: PRE-EXECUTION SCOPE & PRIVILEGE ENFORCEMENT
    # =========================================================================

    @staticmethod
    def _is_file_write_command(command: str, shell: ShellType) -> bool:
        """Detects whether a command mutates filesystem/registry/disk state.

        This is enforced *independently* of the caller-supplied ``category`` so a
        READ_ONLY sub-agent cannot write files by mislabelling the action as a
        diagnostic.
        """
        patterns = _POSIX_WRITE_PATTERNS if shell in (ShellType.WSL_BASH, ShellType.BASH) else _WINDOWS_WRITE_PATTERNS
        return any(p.search(command) for p in patterns)

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

        # 4. Filesystem-write boundary (independent of the caller's category).
        if command and not self.scope.allow_file_write and self._is_file_write_command(command, shell):
            raise ScopeViolationError(
                f"Filesystem/registry write detected in command '{command[:80]}' but agent "
                f"'{self.agent_name}' (privilege '{self.scope.privilege.value}') is not authorized to mutate state."
            )

        # 5. Destructive command prevention
        if command:
            if shell in (ShellType.WSL_BASH, ShellType.BASH):
                verdict = self.linux_safety_guard.evaluate(command)
                if verdict and verdict.is_dangerous and not self.scope.allow_destructive:
                    lbl = getattr(verdict, "label", getattr(verdict, "risk_level", "destructive"))
                    raise ScopeViolationError(
                        f"Command '{command}' is classified as DESTRUCTIVE ({lbl}) and is forbidden under scope."
                    )
            else:
                v = self.safety_guard.classify(command)
                if v and v.is_dangerous and not self.scope.allow_destructive:
                    lbl = getattr(v, "label", getattr(v, "risk_level", "destructive"))
                    raise ScopeViolationError(
                        f"Command '{command}' is classified as DESTRUCTIVE ({lbl}) and is forbidden under scope."
                    )

    # =========================================================================
    # LAYER 2: STEP & RATE LIMIT BOUNDARIES
    # =========================================================================

    def increment_step(self) -> None:
        """Enforces upper step limit and per-minute rate fences to eliminate runaway loops."""
        with self._lock:
            self.steps_executed += 1
            executed = self.steps_executed
            now = time.time()
            # Drop timestamps older than 60 seconds
            while self._action_times and now - self._action_times[0] > 60.0:
                self._action_times.popleft()
            self._action_times.append(now)
            rate = len(self._action_times)

        if executed > self.scope.max_steps:
            raise StepLimitExceededError(
                f"Sub-agent '{self.agent_name}' exceeded maximum permitted execution quota ({self.scope.max_steps} steps)."
            )
        if self.scope.rate_limit_per_minute and rate > self.scope.rate_limit_per_minute:
            raise RateLimitExceededError(
                f"Sub-agent '{self.agent_name}' exceeded rate limit ({self.scope.rate_limit_per_minute} actions/minute)."
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

        except (ScopeViolationError, StepLimitExceededError, RateLimitExceededError) as sec_err:
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
            # Keep the raw traceback in the local log only; never expose it via
            # the message board / swarm status (information disclosure).
            logger.warning(
                "Sub-agent '%s' fluke during '%s': %s\n%s",
                self.agent_name, action_name, exc, traceback.format_exc(),
            )
            fault = None
            if self.board:
                fault = self.board.record_fault(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    exception_type=exc.__class__.__name__,
                    error_message=str(exc),
                    attempted_action=action_name,
                    was_isolated=tripped,
                    context={"exception_type": exc.__class__.__name__},
                )

            return SafeExecutionResult(
                success=False,
                error=f"FLUKE_CONTAINED: [{exc.__class__.__name__}] {str(exc)}",
                fluke_contained=True,
                duration_ms=duration_ms,
                fault_record=fault,
            )
