"""MEC substrate-network models from Section 3 of the paper."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx


@dataclass(frozen=True, slots=True)
class DataCenter:
    """A substrate node with computational capacity ``C_i``."""

    id: str
    compute_capacity: float
    resource_cost: float = 0.0
    processing_cost: float = 0.0


@dataclass(frozen=True, slots=True)
class PhysicalLink:
    """An undirected substrate link with latency ``L_i,j`` and bandwidth ``B_i,j``."""

    source: str
    destination: str
    latency: float
    bandwidth_capacity: float


class MECNetwork:
    """Undirected MEC substrate graph ``G_s = (V_s, E_s)``.

    Shortest routes are selected by communication latency, as required for
    virtual-link mapping in the system model.
    """

    def __init__(self, data_centers: list[DataCenter], links: list[PhysicalLink]) -> None:
        self.graph = nx.Graph()
        for dc in data_centers:
            if dc.compute_capacity < 0:
                raise ValueError("data-center compute capacity cannot be negative")
            if dc.id in self.graph:
                raise ValueError(f"duplicate data-center id: {dc.id}")
            self.graph.add_node(dc.id, data_center=dc)

        for link in links:
            if link.source == link.destination:
                raise ValueError("physical links must connect distinct data centers")
            if link.source not in self.graph or link.destination not in self.graph:
                raise ValueError("physical link endpoint is not a data center")
            if link.latency < 0 or link.bandwidth_capacity < 0:
                raise ValueError("link latency and capacity cannot be negative")
            if self.graph.has_edge(link.source, link.destination):
                raise ValueError("duplicate physical link")
            self.graph.add_edge(
                link.source,
                link.destination,
                latency=link.latency,
                bandwidth_capacity=link.bandwidth_capacity,
            )

        self._data_centers = tuple(self.graph.nodes)
        # The topology is static, so latency-shortest routes are cached.
        self._paths: dict[tuple[str, str], tuple[str, ...]] = {}
        self._latency: dict[tuple[str, str], float] = {}
        self._links: dict[tuple[str, str], tuple[tuple[str, str], ...]] = {}

    @property
    def data_centers(self) -> tuple[str, ...]:
        return self._data_centers

    def shortest_path(self, source: str, destination: str) -> tuple[str, ...]:
        key = (source, destination)
        cached = self._paths.get(key)
        if cached is not None:
            return cached
        if source not in self.graph or destination not in self.graph:
            raise ValueError("route endpoint is not a data center")
        if source == destination:
            path = (source,)
        else:
            try:
                path = tuple(nx.shortest_path(self.graph, source, destination, weight="latency"))
            except nx.NetworkXNoPath as exc:
                raise ValueError(f"no route between {source!r} and {destination!r}") from exc
        self._paths[key] = path
        return path

    def path_latency(self, path: tuple[str, ...]) -> float:
        return sum(self.graph[left][right]["latency"] for left, right in zip(path, path[1:]))

    def latency(self, source: str, destination: str) -> float:
        """Latency of the cached shortest route between two data centers."""
        key = (source, destination)
        value = self._latency.get(key)
        if value is None:
            value = self.path_latency(self.shortest_path(source, destination))
            self._latency[key] = value
        return value

    def route_links(self, source: str, destination: str) -> tuple[tuple[str, str], ...]:
        """Canonical link keys traversed by the shortest route."""
        key = (source, destination)
        links = self._links.get(key)
        if links is None:
            path = self.shortest_path(source, destination)
            links = tuple(self.link_key(left, right) for left, right in zip(path, path[1:]))
            self._links[key] = links
        return links

    def compute_capacity(self, dc: str) -> float:
        return self.graph.nodes[dc]["data_center"].compute_capacity

    def bandwidth_capacity(self, link: tuple[str, str]) -> float:
        return self.graph[link[0]][link[1]]["bandwidth_capacity"]

    @staticmethod
    def link_key(source: str, destination: str) -> tuple[str, str]:
        """Canonical key for an undirected substrate link."""

        return tuple(sorted((source, destination)))
