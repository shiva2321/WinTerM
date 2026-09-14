"""Swarm Message Board: Thread-safe blackboard communication bus and suggestion ledger
for multi-agent coordination.
"""

from __future__ import annotations

import time
import threading
from typing import Dict, Any, List, Optional
from winterm.swarm.models import (
    SwarmMessage,
    MessageType,
    SwarmSuggestion,
    SuggestionStatus,
    SwarmFaultRecord,
)


class SwarmMessageBoard:
    """Centralized, thread-safe blackboard facilitating asynchronous multi-agent coordination."""

    MAX_MESSAGES_DEFAULT: int = 500
    MAX_SUGGESTIONS_DEFAULT: int = 100
    MAX_FAULTS_DEFAULT: int = 100

    def __init__(self, max_messages: int = MAX_MESSAGES_DEFAULT):
        self._lock = threading.RLock()
        self._max_messages = max_messages
        self._messages: List[SwarmMessage] = []
        self._suggestions: Dict[str, SwarmSuggestion] = {}
        self._faults: List[SwarmFaultRecord] = []

    # =========================================================================
    # 1. MESSAGE BUS
    # =========================================================================

    def post_message(
        self,
        sender_id: str,
        message_type: MessageType,
        content: str,
        sender_role: str = "sub_agent",
        recipient_id: str = "broadcast",
        payload: Optional[Dict[str, Any]] = None,
    ) -> SwarmMessage:
        """Posts a message to the shared coordination board."""
        msg = SwarmMessage(
            sender_id=sender_id,
            sender_role=sender_role,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content,
            payload=payload or {},
            timestamp=time.time(),
        )
        with self._lock:
            self._messages.append(msg)
            # Enforce message retention quota
            if len(self._messages) > self._max_messages:
                self._messages = self._messages[-self._max_messages:]
        return msg

    def get_messages(
        self,
        filter_type: Optional[MessageType] = None,
        recipient_id: Optional[str] = None,
        sender_id: Optional[str] = None,
        since_timestamp: Optional[float] = None,
        limit: int = 50,
    ) -> List[SwarmMessage]:
        """Retrieves filtered messages from the board in chronological order."""
        with self._lock:
            results = self._messages[:]

        if filter_type:
            results = [m for m in results if m.message_type == filter_type]
        if recipient_id:
            results = [m for m in results if m.recipient_id in (recipient_id, "broadcast")]
        if sender_id:
            results = [m for m in results if m.sender_id == sender_id]
        if since_timestamp is not None:
            results = [m for m in results if m.timestamp >= since_timestamp]

        return results[-limit:]

    # =========================================================================
    # 2. PROACTIVE SUGGESTIONS LEDGER
    # =========================================================================

    def submit_suggestion(
        self,
        proposing_agent_id: str,
        proposing_agent_name: str,
        title: str,
        reasoning: str,
        proposed_action: str,
        target_shell: Any,
        required_privilege: Any,
    ) -> SwarmSuggestion:
        """Records a proactive optimization or operational proposal from a sub-agent."""
        suggestion = SwarmSuggestion(
            proposing_agent_id=proposing_agent_id,
            proposing_agent_name=proposing_agent_name,
            title=title,
            reasoning=reasoning,
            proposed_action=proposed_action,
            target_shell=target_shell,
            required_privilege=required_privilege,
        )
        with self._lock:
            self._suggestions[suggestion.suggestion_id] = suggestion
            # Also notify board
            self.post_message(
                sender_id=proposing_agent_id,
                sender_role="sub_agent",
                recipient_id="broadcast",
                message_type=MessageType.SUGGESTION,
                content=f"Sub-agent '{proposing_agent_name}' proposed suggestion: '{title}'",
                payload={"suggestion_id": suggestion.suggestion_id, "proposed_action": proposed_action},
            )
        return suggestion

    def get_pending_suggestions(self) -> List[SwarmSuggestion]:
        """Returns all suggestions currently awaiting main agent review."""
        with self._lock:
            return [s for s in self._suggestions.values() if s.status == SuggestionStatus.PENDING]

    def get_suggestion(self, suggestion_id: str) -> Optional[SwarmSuggestion]:
        """Retrieves a specific suggestion by its ID."""
        with self._lock:
            return self._suggestions.get(suggestion_id)

    def list_suggestions(self, status: Optional[SuggestionStatus] = None) -> List[SwarmSuggestion]:
        """Returns all registered suggestions, optionally filtered by status."""
        with self._lock:
            if status:
                return [s for s in self._suggestions.values() if s.status == status]
            return list(self._suggestions.values())

    def update_suggestion_status(
        self,
        suggestion_id: str,
        status: SuggestionStatus,
        resolution_note: str = "",
    ) -> bool:
        """Updates the status of a suggestion (e.g. APPROVED, REJECTED, EXECUTED)."""
        with self._lock:
            if suggestion_id not in self._suggestions:
                return False
            sug = self._suggestions[suggestion_id]
            sug.status = status
            sug.resolution_note = resolution_note
            sug.resolved_at = time.time()
            return True

    # =========================================================================
    # 3. FAULT TELEMETRY & AUDITING
    # =========================================================================

    def record_fault(
        self,
        agent_id: str,
        agent_name: str,
        exception_type: str,
        error_message: str,
        attempted_action: str,
        was_isolated: bool = False,
        context: Optional[Dict[str, Any]] = None,
    ) -> SwarmFaultRecord:
        """Logs an isolated fault event to preserve diagnostic evidence without crashing."""
        fault = SwarmFaultRecord(
            agent_id=agent_id,
            agent_name=agent_name,
            exception_type=exception_type,
            error_message=error_message,
            attempted_action=attempted_action,
            was_isolated=was_isolated,
            context=context or {},
        )
        with self._lock:
            self._faults.append(fault)
            if len(self._faults) > self.MAX_FAULTS_DEFAULT:
                self._faults = self._faults[-self.MAX_FAULTS_DEFAULT:]

            # Post an ALERT to the board
            self.post_message(
                sender_id=agent_id,
                sender_role="system",
                recipient_id="broadcast",
                message_type=MessageType.ALERT,
                content=f"Fault captured for sub-agent '{agent_name}': {exception_type} - {error_message}",
                payload={"fault_id": fault.fault_id, "was_isolated": was_isolated},
            )
        return fault

    def get_fault_records(self, agent_id: Optional[str] = None) -> List[SwarmFaultRecord]:
        """Retrieves recorded fault events, optionally filtered by agent."""
        with self._lock:
            if agent_id:
                return [f for f in self._faults if f.agent_id == agent_id]
            return self._faults[:]

    # =========================================================================
    # 4. MAINTENANCE & RETENTION
    # =========================================================================

    def prune_board(self, max_messages: int = 100) -> int:
        """Purges old messages down to max_messages to conserve system memory."""
        with self._lock:
            if len(self._messages) <= max_messages:
                return 0
            purged = len(self._messages) - max_messages
            self._messages = self._messages[-max_messages:]
            return purged

    def clear(self) -> None:
        """Clears all board state (used during full swarm reset or testing)."""
        with self._lock:
            self._messages.clear()
            self._suggestions.clear()
            self._faults.clear()
