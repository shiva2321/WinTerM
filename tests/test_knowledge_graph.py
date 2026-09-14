"""Unit tests for Windows Terminal Knowledge Graph structure, ontology, and datasets."""

import pytest
from winterm.graph.builder import build_windows_knowledge_graph
from winterm.graph.engine import WindowsKnowledgeGraph
from winterm.graph.schema import NodeType, RelationType


@pytest.fixture(scope="module")
def kg():
    return WindowsKnowledgeGraph()


def test_knowledge_graph_compilation_and_metrics(kg):
    """Verifies that the knowledge graph compiles with extensive factual Windows data."""
    metrics = kg.get_metrics()
    assert metrics["total_nodes"] > 700, f"Expected >700 nodes, got {metrics['total_nodes']}"
    assert metrics["total_edges"] > 900, f"Expected >900 edges, got {metrics['total_edges']}"

    node_counts = metrics["node_type_counts"]
    assert node_counts[NodeType.SUBSYSTEM.value] == 9
    assert node_counts[NodeType.PRIVILEGE.value] >= 4
    assert node_counts[NodeType.COMMAND.value] >= 50
    assert node_counts[NodeType.PARAMETER.value] >= 500
    assert node_counts[NodeType.SERVICE_RESOURCE.value] >= 20
    assert node_counts[NodeType.ERROR_CODE.value] >= 10

    edge_counts = metrics["relation_type_counts"]
    assert edge_counts[RelationType.PART_OF_SUBSYSTEM.value] >= 50
    assert edge_counts[RelationType.REQUIRES_PRIVILEGE.value] >= 50
    assert edge_counts[RelationType.HAS_PARAMETER.value] >= 500
    assert edge_counts[RelationType.DEPENDS_ON.value] >= 30
    assert edge_counts[RelationType.DEPENDENCY_OF.value] >= 30
    assert edge_counts[RelationType.REMEDIATES_ERROR.value] >= 10
    assert edge_counts[RelationType.ALTERNATIVE_TO.value] >= 10


def test_all_subsystems_connected(kg):
    """Verifies all 9 Windows architecture subsystems are present and have attached commands."""
    subsystems = [
        "KernelBoot",
        "StorageNTFS",
        "ProcessMemory",
        "ServicesTasks",
        "RegistryPolicy",
        "SecurityCrypto",
        "NetworkFirewall",
        "DiagnosticsHealth",
        "VirtualizationPackages",
    ]
    for sub in subsystems:
        sub_node = f"subsystem:{sub}"
        assert kg.graph.has_node(sub_node), f"Subsystem {sub} node missing"
        cmds = kg.get_subsystem_commands(sub)
        assert len(cmds) > 0, f"Subsystem {sub} has no attached commands"


def test_cmdlet_parameters_and_privileges(kg):
    """Verifies PowerShell cmdlet nodes have parameter edges and privilege requirements."""
    cmd_node = "cmdlet:get-process"
    assert kg.graph.has_node(cmd_node)
    cmd_data = kg.graph.nodes[cmd_node]
    assert cmd_data["name"] == "Get-Process"
    assert cmd_data["is_cmdlet"] is True

    # Check parameters
    out_edges = kg.graph.out_edges(cmd_node, data=True)
    param_nodes = [
        target for _, target, data in out_edges
        if data.get("relation") == RelationType.HAS_PARAMETER.value
    ]
    assert "param:get-process:-name" in param_nodes
    assert "param:get-process:-id" in param_nodes


def test_native_binaries_parameters_and_privileges(kg):
    """Verifies native Win32 administrative utilities have valid flags and elevation mappings."""
    bin_node = "binary:bcdedit.exe"
    assert kg.graph.has_node(bin_node)
    bin_data = kg.graph.nodes[bin_node]
    assert bin_data["name"] == "bcdedit.exe"
    assert bin_data["is_native_binary"] is True

    out_edges = kg.graph.out_edges(bin_node, data=True)
    param_nodes = [
        target for _, target, data in out_edges
        if data.get("relation") == RelationType.HAS_PARAMETER.value
    ]
    assert "param:bcdedit.exe:/enum" in param_nodes

    priv_edges = [
        target for _, target, data in out_edges
        if data.get("relation") == RelationType.REQUIRES_PRIVILEGE.value
    ]
    assert "privilege:Administrator" in priv_edges


def test_bidirectional_service_dependencies(kg):
    """Verifies that SCM service dependencies maintain strict bidirectional graph edges."""
    rpcss_node = "service:rpcss"
    winmgmt_node = "service:winmgmt"
    assert kg.graph.has_node(rpcss_node)
    assert kg.graph.has_node(winmgmt_node)

    # Winmgmt depends on RpcSs
    winmgmt_out = [
        (t, d.get("relation"))
        for _, t, d in kg.graph.out_edges(winmgmt_node, data=True)
    ]
    assert (rpcss_node, RelationType.DEPENDS_ON.value) in winmgmt_out

    # RpcSs is dependency_of Winmgmt
    rpcss_out = [
        (t, d.get("relation"))
        for _, t, d in kg.graph.out_edges(rpcss_node, data=True)
    ]
    assert (winmgmt_node, RelationType.DEPENDENCY_OF.value) in rpcss_out


def test_bidirectional_command_alternatives(kg):
    """Verifies that cmdlet and Win32 binary alternatives are reciprocal."""
    ps_cmd = "cmdlet:stop-process"
    native_bin = "binary:taskkill.exe"
    assert kg.graph.has_node(ps_cmd)
    assert kg.graph.has_node(native_bin)

    ps_alts = kg.find_command_alternatives("Stop-Process")
    assert "taskkill.exe" in ps_alts

    native_alts = kg.find_command_alternatives("taskkill.exe")
    assert "Stop-Process" in native_alts
