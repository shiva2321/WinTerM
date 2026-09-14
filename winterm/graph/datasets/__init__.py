"""Knowledge Graph Datasets: Consolidated factual catalogs for Windows Terminal."""

from winterm.graph.datasets.cmdlets_data import CMDLETS_DATA
from winterm.graph.datasets.native_binaries_data import NATIVE_BINARIES_DATA
from winterm.graph.datasets.services_dependency_data import SERVICES_DATA
from winterm.graph.datasets.errors_remedies_data import ERRORS_REMEDIES_DATA

__all__ = [
    "CMDLETS_DATA",
    "NATIVE_BINARIES_DATA",
    "SERVICES_DATA",
    "ERRORS_REMEDIES_DATA",
]
