"""Unit tests for Windows Terminal Knowledge Graph reasoning and agent integration."""

import pytest
from winterm.agent.winterm_agent import WinTermAgent
from winterm.graph.engine import WindowsKnowledgeGraph
from winterm.models.intent import PlanStep, ActionCategory
from winterm.models.context import ShellType, ElevationLevel
from winterm.cognition.predictor import ImpactPredictor
from winterm.cognition.reasoner import SemanticReasoner
from winterm.cognition.healer import ErrorHealer
from winterm.models.result import ExecutionResult


@pytest.fixture(scope="module")
def agent():
    return WinTermAgent()


@pytest.fixture(scope="module")
def kg():
    return WindowsKnowledgeGraph()


# =============================================================================
# 1. BLAST RADIUS REASONING
# =============================================================================

def test_blast_radius_critical_service(kg):
    """Halting RpcSs must compute critical risk and cascade to dependent services."""
    report = kg.calculate_blast_radius("RpcSs", depth=2)
    assert report.root_node_id == "RpcSs"
    assert report.risk_score == "CRITICAL"
    assert len(report.direct_dependents) >= 10
    assert "Winmgmt" in report.direct_dependents
    assert "CryptSvc" in report.direct_dependents
    assert "Schedule" in report.direct_dependents

    # Cascading transitive dependents
    assert len(report.cascading_dependents) >= 1
    assert "LanmanServer" in report.cascading_dependents or "iphlpsvc" in report.cascading_dependents
    assert report.blast_radius_depth >= 2
    assert "CRITICAL" in report.impact_summary


def test_blast_radius_safe_service(kg):
    """Stopping Spooler or TermService must not cascade critical failure."""
    report = kg.calculate_blast_radius("Spooler", depth=2)
    assert report.root_node_id == "Spooler"
    assert report.risk_score in ("LOW", "MEDIUM")
    assert len(report.direct_dependents) == 0


def test_blast_radius_unindexed_resource(kg):
    """Unregistered or custom resources return graceful low risk report."""
    report = kg.calculate_blast_radius("NonExistentService_XYZ", depth=2)
    assert report.risk_score == "LOW"
    assert len(report.direct_dependents) == 0


# =============================================================================
# 2. PARAMETER HALLUCINATION VALIDATION
# =============================================================================

def test_parameter_validation_valid_cmdlet(kg):
    """Legitimate cmdlet and valid flags pass validation."""
    res = kg.validate_command_parameters("Get-Process", ["-Name", "-Id", "-FileVersionInfo"])
    assert res.is_valid is True
    assert len(res.unknown_parameters) == 0
    assert len(res.valid_parameters) == 3


def test_parameter_validation_detects_hallucinations(kg):
    """Invented or hallucinated switches are flagged with unknown_parameters."""
    res = kg.validate_command_parameters("Get-Process", ["-Name", "-FakeParamInvented", "-WrongSwitch"])
    assert res.is_valid is False
    assert "-Name" in res.valid_parameters
    assert "-FakeParamInvented" in res.unknown_parameters
    assert "-WrongSwitch" in res.unknown_parameters


def test_parameter_validation_typo_suggestions(kg):
    """Minor typos in cmdlet flags receive close suggestions from graph."""
    res = kg.validate_command_parameters("Get-Process", ["-Nam"])
    assert res.is_valid is False
    assert "-Nam" in res.suggestions
    assert res.suggestions["-Nam"] == "-Name"


def test_parameter_validation_native_binary(kg):
    """Native Win32 binaries and slash flags are validated against the graph."""
    res = kg.validate_command_parameters("bcdedit.exe", ["/enum", "/v"])
    assert res.is_valid is True
    assert "/enum" in res.valid_parameters
    assert "/v" in res.valid_parameters


# =============================================================================
# 3. ERROR REMEDIATION PATHS
# =============================================================================

def test_remediation_access_denied_hresult(kg):
    """HRESULT 0x80070005 resolves to a multi-step administrative recovery chain."""
    path = kg.find_remediation_chains("0x80070005")
    assert path is not None
    assert path.error_code == "0x80070005"
    assert "Administrator" in path.required_privileges
    assert len(path.remediation_steps) >= 3
    # First step checks admin role
    assert "WindowsPrincipal" in path.remediation_steps[0]["command"]


def test_remediation_port_in_use_win32(kg):
    """Win32 error 10048 (WSAEADDRINUSE) resolves to PID resolution and termination."""
    path = kg.find_remediation_chains("10048")
    assert path is not None
    assert len(path.remediation_steps) >= 2
    assert "Get-NetTCPConnection" in path.remediation_steps[0]["command"]
    assert "Stop-Process" in path.remediation_steps[1]["command"]


def test_remediation_service_disabled(kg):
    """HRESULT 0x80070422 (service disabled) resolves to Set-Service + Start-Service."""
    path = kg.find_remediation_chains("0x80070422")
    assert path is not None
    assert "Set-Service" in path.remediation_steps[0]["command"]
    assert "Start-Service" in path.remediation_steps[1]["command"]


# =============================================================================
# 4. AGENT & COGNITIVE INTEGRATION
# =============================================================================

def test_agent_graph_convenience_methods(agent):
    """WinTermAgent directly exposes and utilizes the Knowledge Graph."""
    # Blast radius
    blast = agent.calculate_blast_radius("RpcSs")
    assert blast.risk_score == "CRITICAL"

    # Parameter validation
    val = agent.validate_command("Stop-Process -Id 1234 -Force")
    assert val.is_valid is True

    # Remedy
    remedy = agent.find_error_remedy("0x80070005")
    assert remedy is not None

    # Alternatives
    alts = agent.find_alternatives("Stop-Process")
    assert "taskkill.exe" in alts


def test_impact_predictor_enriches_with_graph_blast_radius(agent):
    """ImpactPredictor queries graph for service blast radius and enriches PredictedImpact."""
    step = PlanStep(
        step_id="stop-rpc",
        title="Stop critical RPC service",
        category=ActionCategory.SERVICE,
        raw_intent="stop rpcss",
        command="Stop-Service -Name RpcSs",
        target_shell=ShellType.POWERSHELL_51,
        metadata={"service_name": "RpcSs"},
    )
    impact = agent.predictor.predict_step_impact(step)
    assert impact.blast_radius is not None
    assert impact.blast_radius["risk_score"] == "CRITICAL"
    assert len(impact.blast_radius["direct_dependents"]) >= 10
    # Blast radius alert added to warnings
    assert any("Knowledge Graph Alert" in w for w in impact.warnings)


def test_semantic_reasoner_discovers_graph_alternatives(agent):
    """SemanticReasoner automatically extracts alternatives from the Knowledge Graph."""
    step = PlanStep(
        step_id="stop-proc",
        title="Stop hung process",
        category=ActionCategory.PROCESS,
        raw_intent="kill process",
        command="Stop-Process -Id 9999 -Force",
        target_shell=ShellType.POWERSHELL_51,
    )
    rationale = agent.reasoner.explain_step(step)
    alt_names = [a.alternative for a in rationale.alternatives_rejected]
    assert "taskkill.exe" in alt_names


def test_error_healer_graph_backed_diagnosis(agent):
    """ErrorHealer generates self-healing proposal when stderr contains graph-indexed HRESULT."""
    mock_failed_result = ExecutionResult(
        step_id="test-fail",
        command="Set-ItemProperty -Path HKLM:\\SYSTEM -Name Test -Value 1",
        shell=ShellType.POWERSHELL_51,
        success=False,
        exit_code=1,
        stderr="Set-ItemProperty : Requested registry access is not allowed. Error: 0x80070005 (Access is denied)",
    )
    proposal = agent.healer.diagnose_failure(mock_failed_result)
    assert proposal is not None
    assert "0x80070005" in proposal.error_signature
    assert proposal.healing_command != ""
    assert proposal.requires_elevation is True


# =============================================================================
# 5. HUGGING FACE DATASET GRAPH CAPABILITIES
# =============================================================================

def test_intent_search_corpus(kg):
    """Natural language intents resolve to real PowerShell and CMD commands."""
    matches = kg.resolve_intent_to_commands("find text in files", top_k=5)
    assert len(matches) > 0
    assert any("command" in m and len(m["command"]) > 0 for m in matches)
    assert any("instruction" in m for m in matches)
    # Check structure
    top_match = matches[0]
    assert "relevance_score" in top_match
    assert top_match["relevance_score"] > 0.0


def test_command_documentation_lookup(kg):
    """Official Microsoft documentation and syntax are retrievable for Windows commands."""
    # Test Hugging Face indexed Windows command (arp)
    arp_docs = kg.get_command_documentation("arp")
    assert arp_docs is not None
    assert "arp" in arp_docs["name"].lower()
    assert len(arp_docs["syntax"]) > 0
    assert len(arp_docs["applies_to"]) > 0
    assert "Address Resolution Protocol" in arp_docs["description"]

    # Test Native Win32 binary documentation (robocopy)
    robo_docs = kg.get_command_documentation("robocopy")
    assert robo_docs is not None
    assert "robocopy" in robo_docs["name"].lower()
    assert len(robo_docs["parameters"]) > 10
    assert "NTFS" in robo_docs["description"]


def test_safety_classification_evaluation(kg):
    """Safety corpus classifies commands into safety tiers with warnings."""
    # Destructive command
    destructive_safety = kg.get_safety_classification("Format-Volume -DriveLetter D -FileSystem NTFS")
    assert destructive_safety["is_dangerous"] is True
    assert destructive_safety["safety_label"] in ("destructive", "credential_sensitive", "privileged")

    # Safe read-only command
    safe_safety = kg.get_safety_classification("Get-Process")
    assert safe_safety["safety_label"] == "safe"
    assert safe_safety["is_dangerous"] is False


def test_agent_hf_convenience_methods(agent):
    """Agent methods for search_intent, get_command_docs, and check_command_safety work."""
    # Search intent
    intents = agent.search_intent("list directory contents", top_k=3)
    assert len(intents) > 0
    assert "command" in intents[0]

    # Command docs
    docs = agent.get_command_docs("robocopy")
    assert docs is not None
    assert "parameters" in docs

    # Safety check
    safety = agent.check_command_safety("reg delete HKLM\\Software\\Test /f")
    assert safety is not None
    assert "safety_label" in safety


def test_impact_predictor_safety_enrichment(agent):
    """ImpactPredictor upgrades risk and attaches warnings when command is dangerous in safety corpus."""
    step = PlanStep(
        step_id="format-disk",
        title="Format volume",
        category=ActionCategory.CUSTOM,
        raw_intent="format volume",
        command="Format-Volume -DriveLetter D -FileSystem NTFS",
        target_shell=ShellType.POWERSHELL_51,
    )
    impact = agent.predictor.predict_step_impact(step)
    assert impact.risk_level.value in ("high_destructive", "medium")
    assert any("Knowledge Graph Safety Alert" in w for w in impact.warnings)


def test_mcp_server_hf_tools():
    """WinTermMCPServer handles calls for new Hugging Face graph tools."""
    import json
    from winterm.tools.mcp_server import WinTermMCPServer

    server = WinTermMCPServer()

    # 1. winterm_graph_search_intent
    req_intent = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "winterm_graph_search_intent",
            "arguments": {"query": "find files", "top_k": 3},
        },
    }
    resp = server.handle_request(req_intent)
    assert "result" in resp
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["query"] == "find files"
    assert content["count"] > 0

    # 2. winterm_graph_command_docs
    req_docs = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "winterm_graph_command_docs",
            "arguments": {"command": "robocopy"},
        },
    }
    resp_docs = server.handle_request(req_docs)
    assert "result" in resp_docs
    content_docs = json.loads(resp_docs["result"]["content"][0]["text"])
    assert content_docs["matched"] is True

    # 3. winterm_graph_safety_check
    req_safety = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "winterm_graph_safety_check",
            "arguments": {"command": "Get-Process"},
        },
    }
    resp_safety = server.handle_request(req_safety)
    assert "result" in resp_safety
    content_safety = json.loads(resp_safety["result"]["content"][0]["text"])
    assert content_safety["safety_label"] == "safe"

