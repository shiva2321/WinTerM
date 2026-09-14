"""Unit tests for Multi-Agent Session Coordination, Concurrency Locks, and Framework Isolation."""

import time
import pytest
from winterm.agent.session import AgentSession, AgentSessionCoordinator, ResourceLock


def test_agent_session_framework_tagging():
    """Validates session framework tagging for different agent runtimes."""
    s_claude = AgentSession(session_id="claude-1", agent_framework="claude-code")
    s_gemini = AgentSession(session_id="gemini-1", agent_framework="gemini")
    s_deepseek = AgentSession(session_id="deepseek-1", agent_framework="deepseek")
    s_opencode = AgentSession(session_id="opencode-1", agent_framework="opencode")

    assert s_claude.agent_framework == "claude-code"
    assert s_gemini.agent_framework == "gemini"
    assert s_deepseek.agent_framework == "deepseek"
    assert s_opencode.agent_framework == "opencode"


def test_agent_session_coordinator_registration():
    """Validates registering concurrent agent sessions and querying active sessions."""
    s1 = AgentSession(session_id="coord-gemini-1", agent_framework="gemini")
    s2 = AgentSession(session_id="coord-deepseek-1", agent_framework="deepseek")

    AgentSessionCoordinator.register_session(s1)
    AgentSessionCoordinator.register_session(s2)

    active = AgentSessionCoordinator.get_active_sessions()
    session_ids = [s["session_id"] for s in active]
    assert "coord-gemini-1" in session_ids
    assert "coord-deepseek-1" in session_ids


def test_agent_session_coordinator_resource_locking():
    """Validates mutual exclusion and resource lock leasing between simultaneous agents."""
    port_resource = "tcp:8080"

    # Gemini acquires lock on port 8080
    acquired = AgentSessionCoordinator.acquire_resource_lock(
        resource_id=port_resource,
        session_id="sess-gemini",
        framework="gemini",
        ttl_seconds=10.0,
    )
    assert acquired is True

    # Same session re-enters successfully
    reenter = AgentSessionCoordinator.acquire_resource_lock(
        resource_id=port_resource,
        session_id="sess-gemini",
        framework="gemini",
        ttl_seconds=10.0,
    )
    assert reenter is True

    # DeepSeek attempts to acquire same locked port -> must be rejected
    rejected = AgentSessionCoordinator.acquire_resource_lock(
        resource_id=port_resource,
        session_id="sess-deepseek",
        framework="deepseek",
        ttl_seconds=10.0,
    )
    assert rejected is False

    # Check lock inspector
    lock_info = AgentSessionCoordinator.is_resource_locked(port_resource)
    assert lock_info is not None
    assert lock_info.owner_session_id == "sess-gemini"
    assert lock_info.owner_framework == "gemini"

    # Gemini releases lock
    released = AgentSessionCoordinator.release_resource_lock(
        resource_id=port_resource,
        session_id="sess-gemini",
    )
    assert released is True

    # Now DeepSeek can acquire it
    acquired_deepseek = AgentSessionCoordinator.acquire_resource_lock(
        resource_id=port_resource,
        session_id="sess-deepseek",
        framework="deepseek",
        ttl_seconds=10.0,
    )
    assert acquired_deepseek is True

    # Clean up
    AgentSessionCoordinator.release_resource_lock(port_resource, "sess-deepseek")
