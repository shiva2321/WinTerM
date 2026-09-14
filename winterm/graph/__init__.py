"""Windows Terminal Knowledge Graph module: Ontology, datasets, builder, and reasoning engine."""

from winterm.graph.schema import (
    NodeType,
    RelationType,
    GraphNode,
    GraphEdge,
    BlastRadiusReport,
    RemediationPath,
    ParameterValidationResult,
)
from winterm.graph.builder import KnowledgeGraphBuilder, build_windows_knowledge_graph
from winterm.graph.engine import WindowsKnowledgeGraph

__all__ = [
    "NodeType",
    "RelationType",
    "GraphNode",
    "GraphEdge",
    "BlastRadiusReport",
    "RemediationPath",
    "ParameterValidationResult",
    "KnowledgeGraphBuilder",
    "build_windows_knowledge_graph",
    "WindowsKnowledgeGraph",
]
