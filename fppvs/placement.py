"""Resource, routing, and latency evaluation for the Section 3 system model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import networkx as nx

from .models import SFCRequest
from .parallelization import ParallelSFC
from .substrate import MECNetwork


@dataclass(frozen=True, slots=True)
class LatencyBreakdown:
    """Critical-path form of Equation (16): network + virtualization + processing."""

    network: float
    virtualization: float
    processing: float
    critical_path: tuple[str, ...]

    @property
    def end_to_end(self) -> float:
        return self.network + self.virtualization + self.processing


@dataclass(frozen=True, slots=True)
class PlacementReport:
    """Outcome of evaluating one complete SFC placement."""

    feasible: bool
    violations: tuple[str, ...]
    compute_usage: Mapping[str, float]
    link_bandwidth_usage: Mapping[tuple[str, str], float]
    routes: Mapping[tuple[str, str], tuple[str, ...]]
    latency: LatencyBreakdown


def evaluate_placement(
    network: MECNetwork,
    request: SFCRequest,
    parallel_sfc: ParallelSFC,
    assignment: Mapping[str, str],
) -> PlacementReport:
    """Evaluate an inter-DC mapping against Section 3 constraints.

    The input assignment maps every graph node (including the ingress and
    egress auxiliary VNFs) to one data center.  Each virtual edge follows the
    latency-shortest substrate path.  Same-DC virtual edges consume neither
    substrate bandwidth nor network latency.  For a p-SFC, latency is measured
    on the longest source-to-egress DAG path, as specified after Equation (19).
    """

    graph = parallel_sfc.graph
    expected_nodes = set(graph.nodes)
    if set(assignment) != expected_nodes:
        missing = sorted(expected_nodes - set(assignment))
        extra = sorted(set(assignment) - expected_nodes)
        raise ValueError(f"assignment must cover exactly the p-SFC nodes; missing={missing}, extra={extra}")
    unknown_dcs = sorted(set(assignment.values()) - set(network.data_centers))
    if unknown_dcs:
        raise ValueError(f"assignment uses unknown data centers: {unknown_dcs}")

    vnf_by_id = {vnf.id: vnf for vnf in request.vnfs}
    compute_usage = {dc: 0.0 for dc in network.data_centers}
    for vnf in request.vnfs:
        if vnf.compute_demand < 0 or vnf.processing_latency < 0 or vnf.virtualization_latency < 0:
            raise ValueError("VNF resource demands and latencies cannot be negative")
        compute_usage[assignment[vnf.id]] += vnf.compute_demand

    routes: dict[tuple[str, str], tuple[str, ...]] = {}
    link_usage: dict[tuple[str, str], float] = {
        MECNetwork.link_key(left, right): 0.0 for left, right in network.graph.edges
    }
    edge_latency: dict[tuple[str, str], float] = {}
    for source, destination in graph.edges:
        path = network.shortest_path(assignment[source], assignment[destination])
        routes[(source, destination)] = path
        edge_latency[(source, destination)] = network.path_latency(path)
        demand = request.bandwidth_demand(source, destination)
        if demand < 0:
            raise ValueError("virtual-link bandwidth demand cannot be negative")
        for left, right in zip(path, path[1:]):
            link_usage[MECNetwork.link_key(left, right)] += demand

    latency = _critical_path_latency(graph, request, edge_latency, vnf_by_id)
    violations: list[str] = []
    for dc, used in compute_usage.items():
        capacity = network.graph.nodes[dc]["data_center"].compute_capacity
        if used > capacity:
            violations.append(f"compute capacity exceeded at {dc}: {used} > {capacity}")
    for left, right in network.graph.edges:
        key = MECNetwork.link_key(left, right)
        capacity = network.graph[left][right]["bandwidth_capacity"]
        if link_usage[key] > capacity:
            violations.append(f"bandwidth capacity exceeded at {key}: {link_usage[key]} > {capacity}")
    if request.max_latency is not None and latency.end_to_end > request.max_latency:
        violations.append(f"latency constraint exceeded: {latency.end_to_end} > {request.max_latency}")

    return PlacementReport(
        feasible=not violations,
        violations=tuple(violations),
        compute_usage=compute_usage,
        link_bandwidth_usage=link_usage,
        routes=routes,
        latency=latency,
    )


def _critical_path_latency(
    graph: nx.DiGraph,
    request: SFCRequest,
    edge_latency: Mapping[tuple[str, str], float],
    vnf_by_id: Mapping[str, object],
) -> LatencyBreakdown:
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError("p-SFC graph must be a DAG")

    node_cost = {
        node: (
            getattr(vnf_by_id.get(node), "processing_latency", 0.0)
            + getattr(vnf_by_id.get(node), "virtualization_latency", 0.0)
        )
        for node in graph.nodes
    }
    distance = {node: float("-inf") for node in graph.nodes}
    predecessor: dict[str, str] = {}
    distance[request.source] = node_cost[request.source]
    for node in nx.topological_sort(graph):
        if distance[node] == float("-inf"):
            continue
        for child in graph.successors(node):
            candidate = distance[node] + edge_latency[(node, child)] + node_cost[child]
            if candidate > distance[child]:
                distance[child] = candidate
                predecessor[child] = node

    if distance[request.destination] == float("-inf"):
        raise ValueError("p-SFC has no ingress-to-egress path")
    path = [request.destination]
    while path[-1] != request.source:
        path.append(predecessor[path[-1]])
    path.reverse()

    return LatencyBreakdown(
        network=sum(edge_latency[(left, right)] for left, right in zip(path, path[1:])),
        virtualization=sum(getattr(vnf_by_id.get(node), "virtualization_latency", 0.0) for node in path),
        processing=sum(getattr(vnf_by_id.get(node), "processing_latency", 0.0) for node in path),
        critical_path=tuple(path),
    )
