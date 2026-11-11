"""Input models for sequential Service Function Chains."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, Sequence


class VNFKind(StrEnum):
    """A VNF either modifies packets or only observes them."""

    SHAPER = "shaper"
    MONITOR = "monitor"


@dataclass(frozen=True, slots=True)
class VNF:
    """An internal VNF in the ordered, sequential SFC.

    The three numeric fields implement the per-VNF quantities ``D_j`` and
    ``L_j`` used in the paper's system model.  Virtualization latency is kept
    separate from processing latency so that the end-to-end decomposition in
    Equation (16) remains observable.
    """

    id: str
    kind: VNFKind
    compute_demand: float = 0.0
    processing_latency: float = 0.0
    virtualization_latency: float = 0.0


@dataclass(frozen=True, slots=True)
class SFCRequest:
    """Inputs required by Algorithm 1 in Section 4.1.

    ``vnfs`` contains only internal VNFs.  ``source`` and ``destination``
    are deliberately separate endpoints.  In ``dependency_matrix``, a
    non-zero value at ``[shaper_index][monitor_index]`` means that the
    monitor must finish before that shaper, yielding a ``monitor -> shaper``
    branch edge.
    """

    source: str
    vnfs: Sequence[VNF]
    destination: str
    dependency_matrix: Sequence[Sequence[int | float]]
    arrival_time: int = 0
    ttl: int = 1
    data_rate: float = 0.0
    min_throughput: float = 0.0
    payment: float = 0.0
    max_latency: float | None = None
    edge_bandwidth_demands: Mapping[tuple[str, str], float] = field(default_factory=dict)

    def bandwidth_demand(self, source: str, destination: str) -> float:
        """Return ``B_e`` for a virtual edge, defaulting to request data rate."""

        return self.edge_bandwidth_demands.get((source, destination), self.data_rate)

