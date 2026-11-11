"""Algorithm 1: sequential-SFC to parallel-SFC conversion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import networkx as nx

from .models import SFCRequest, VNFKind


@dataclass(frozen=True, slots=True)
class ParallelSFC:
    """The parallelized SFC produced by Algorithm 1.

    ``graph`` is a DAG.  ``main_chain`` contains ingress, all shapers in
    original order, and egress.  Each branch path starts at the then-current
    main-chain node, passes through one monitor, and rejoins a shaper or the
    egress.
    """

    graph: nx.DiGraph
    main_chain: tuple[str, ...]
    branch_paths: Mapping[str, tuple[str, ...]]


def parallelize_sfc(request: SFCRequest) -> ParallelSFC:
    """Convert an s-SFC into the dependency-preserving p-SFC of Algorithm 1.

    A monitor immediately opens a branch from the latest main-chain VNF and
    becomes outstanding.  The first later shaper for which the dependency
    matrix is non-zero closes that monitor's branch.  Any still-outstanding
    monitor branches close at egress.
    """

    vnfs = tuple(request.vnfs)
    _validate_request(request, vnfs)

    graph = nx.DiGraph()
    graph.add_node(request.source, kind="endpoint")
    graph.add_node(request.destination, kind="endpoint")
    for vnf in vnfs:
        graph.add_node(vnf.id, kind=vnf.kind.value)

    main_chain = [request.source]
    outstanding: dict[int, tuple[str, str]] = {}
    # monitor index -> (branch start, monitor id)
    branch_paths: dict[str, tuple[str, ...]] = {}

    for index, vnf in enumerate(vnfs):
        if vnf.kind is VNFKind.MONITOR:
            branch_start = main_chain[-1]
            graph.add_edge(branch_start, vnf.id, edge_type="branch")
            outstanding[index] = (branch_start, vnf.id)
            continue

        previous_main = main_chain[-1]
        graph.add_edge(previous_main, vnf.id, edge_type="main")
        main_chain.append(vnf.id)

        # Algorithm 1 scans the outstanding monitor set Theta for the
        # current shaper. A closed monitor is removed and is not reused.
        for monitor_index, (branch_start, monitor_id) in list(outstanding.items()):
            if request.dependency_matrix[index][monitor_index] != 0:
                graph.add_edge(monitor_id, vnf.id, edge_type="branch")
                branch_paths[monitor_id] = (branch_start, monitor_id, vnf.id)
                del outstanding[monitor_index]

    graph.add_edge(main_chain[-1], request.destination, edge_type="main")
    main_chain.append(request.destination)

    # Section 4.1 states that a branch ultimately rejoins the main chain at
    # a shaper or at egress. Outstanding monitors therefore close at egress.
    for branch_start, monitor_id in outstanding.values():
        graph.add_edge(monitor_id, request.destination, edge_type="branch")
        branch_paths[monitor_id] = (branch_start, monitor_id, request.destination)

    if not nx.is_directed_acyclic_graph(graph):  # Defensive invariant check.
        raise ValueError("Algorithm 1 produced a cyclic p-SFC")

    return ParallelSFC(graph, tuple(main_chain), branch_paths)


def _validate_request(request: SFCRequest, vnfs: tuple) -> None:
    ids = [vnf.id for vnf in vnfs]
    if not request.source or not request.destination:
        raise ValueError("source and destination must be non-empty")
    if request.source == request.destination:
        raise ValueError("source and destination must be distinct")
    if request.source in ids or request.destination in ids:
        raise ValueError("source and destination cannot also be internal VNFs")
    if len(ids) != len(set(ids)):
        raise ValueError("internal VNF ids must be unique")

    size = len(vnfs)
    if len(request.dependency_matrix) != size or any(
        len(row) != size for row in request.dependency_matrix
    ):
        raise ValueError("dependency_matrix must be square with one row per internal VNF")

    # Under the agreed convention, only a shaper can depend on a monitor.
    # Shaper-to-shaper dependencies are preserved by their main-chain order.
    for row_index, vnf in enumerate(vnfs):
        if vnf.kind is VNFKind.MONITOR and any(request.dependency_matrix[row_index]):
            raise ValueError("monitor rows in dependency_matrix must be all zero")

