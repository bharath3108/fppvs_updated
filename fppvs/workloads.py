"""Seeded synthetic scenarios using the parameter ranges in Section 5.1.

They are deliberately named synthetic: they are not substitutes for the
unpublished USANet/Milan datasets or the authors' traffic traces.

Arrivals: the paper fixes a mean service lifetime of 1000 time units but
does not state the arrival rate. With ``arrival_rate=None`` requests arrive
one per time unit (the old behaviour), which keeps ~1000 SFCs alive at once
and exceeds the physical capacity of a 24-node network. Passing an
``arrival_rate`` instead draws a homogeneous Poisson process, so the offered
load is ``arrival_rate * 1000`` concurrently active SFCs on average.
"""
from __future__ import annotations

from dataclasses import dataclass
from random import Random

import networkx as nx

from .models import SFCRequest, VNF, VNFKind
from .substrate import DataCenter, MECNetwork, PhysicalLink

VNF_TYPES = ("ids", "dpi", "lb", "fw", "nat")
MEAN_LIFETIME = 1000.0

# Paper Section 5.2: USAnet backbone (24 nodes, 47 links) and an Italian
# metropolitan access network (17 nodes, 29 links). Exact graphs are not
# published, so random connected graphs of the same size are used.
TOPOLOGIES = {"backbone": (24, 47), "metro": (17, 29)}


@dataclass(frozen=True, slots=True)
class SyntheticScenario:
    network: MECNetwork
    requests: tuple[SFCRequest, ...]
    seed: int
    topology: str = "backbone"
    arrival_rate: float | None = None


def make_synthetic_scenario(
    *,
    nodes: int | None = None,
    links: int | None = None,
    requests: int = 100,
    seed: int = 7,
    topology: str = "backbone",
    arrival_rate: float | None = None,
) -> SyntheticScenario:
    """Create a connected, paper-range scenario with reproducible randomness.

    Resource units are normalized: 500--900 Mbps becomes 0.5--0.9 and
    data-center capacity 10--20 represents 10,000--20,000 normalized Mbps.
    The network depends only on ``seed`` and ``topology`` so that a training
    stream and a hold-out stream can share the same substrate.
    """
    default_nodes, default_links = TOPOLOGIES[topology]
    nodes = default_nodes if nodes is None else nodes
    links = default_links if links is None else links
    if links < nodes - 1:
        raise ValueError("a connected topology requires at least nodes - 1 links")
    network = make_network(nodes, links, seed)
    generated = make_requests(network, requests, seed + 1, arrival_rate=arrival_rate)
    return SyntheticScenario(network, generated, seed, topology, arrival_rate)


def make_network(nodes: int, links: int, seed: int) -> MECNetwork:
    rng = Random(seed)
    graph = nx.gnm_random_graph(nodes, links, seed=seed)
    while not nx.is_connected(graph):
        graph = nx.gnm_random_graph(nodes, links, seed=rng.randrange(1 << 30))
    data_centers = [DataCenter(f"dc-{i}", rng.uniform(10, 20), processing_cost=0.001) for i in graph.nodes]
    physical_links = [
        PhysicalLink(f"dc-{left}", f"dc-{right}", rng.uniform(5, 20), rng.choice(range(100, 201, 20)))
        for left, right in graph.edges
    ]
    return MECNetwork(data_centers, physical_links)


def make_requests(network: MECNetwork, count: int, seed: int, *, arrival_rate: float | None = None) -> tuple[SFCRequest, ...]:
    rng = Random(seed)
    time = 0.0
    generated = []
    for index in range(count):
        if arrival_rate is None:
            time = float(index)
        else:
            time += rng.expovariate(arrival_rate)
        generated.append(_request(network.data_centers, index, time, rng))
    return tuple(generated)


def _power_law(rng: Random, low: float, high: float, alpha: float = 1.5) -> float:
    """Bounded Pareto sample: most requests moderate, a few heavy."""
    u = rng.random()
    return low / (1 - u * (1 - (low / high) ** alpha)) ** (1 / alpha)


def _request(data_centers: tuple[str, ...], index: int, arrival_time: float, rng: Random) -> SFCRequest:
    size = rng.randint(4, 10)
    vnfs = []
    for position in range(size):
        name = rng.choice(VNF_TYPES)
        kind = VNFKind.MONITOR if name in {"ids", "dpi"} and rng.random() < 0.45 else VNFKind.SHAPER
        vnfs.append(VNF(f"{name}-{index}-{position}", kind, rng.uniform(0.5, 0.9), rng.uniform(.01, .2)))
    # Each monitor may be required by a later shaper; no monitor->monitor dependencies.
    matrix = [[0] * size for _ in range(size)]
    for monitor in range(size):
        if vnfs[monitor].kind is VNFKind.MONITOR:
            later = [j for j in range(monitor + 1, size) if vnfs[j].kind is VNFKind.SHAPER]
            if later and rng.random() < .5:
                matrix[rng.choice(later)][monitor] = 1
    source, destination = rng.sample(data_centers, 2)
    return SFCRequest(
        source, tuple(vnfs), destination, tuple(tuple(row) for row in matrix),
        arrival_time=arrival_time, ttl=max(1, round(rng.expovariate(1 / MEAN_LIFETIME))),
        data_rate=_power_law(rng, 5, 30), min_throughput=0.0, payment=1.0,
        max_latency=rng.uniform(100, 150),
    )
