"""Time-aware substrate reservations for sequential online SFC admission.

Compute model (all of it counts against physical DC capacity, so nothing is
overbooked):

* every VNF a request uses consumes its own ``compute_demand``;
* every live VNF instance also costs a fixed ``instance_overhead`` (the
  VM/container footprint). With sharing, a same-type instance already live
  in a DC is reused and the overhead is paid once; it is released when its
  last user expires. Without sharing each VNF pays its own overhead.

The ledger integrates held compute and bandwidth over time, which gives the
resource-time metrics used in the experiments.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .substrate import MECNetwork

INSTANCE_OVERHEAD = 0.25
Link = tuple[str, str]
InstanceKey = tuple[str, str]  # (data center, VNF type)


@dataclass(frozen=True, slots=True)
class Reservation:
    expires_at: float
    compute: dict[str, float]
    links: dict[Link, float]
    shared_instances: tuple[InstanceKey, ...] = ()
    dedicated_overhead: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Admission:
    """What one request needs on top of the current ledger state."""

    compute: dict[str, float]            # per-flow VNF demand by DC
    links: dict[Link, float]             # bandwidth by substrate link
    shared_instances: tuple[InstanceKey, ...] = ()   # instances used under sharing
    new_instances: tuple[InstanceKey, ...] = ()      # shared instances this request starts
    dedicated_overhead: dict[str, float] = field(default_factory=dict)

    def compute_need(self, overhead: float) -> dict[str, float]:
        need = dict(self.compute)
        for dc, _ in self.new_instances:
            need[dc] = need.get(dc, 0.0) + overhead
        for dc, amount in self.dedicated_overhead.items():
            need[dc] = need.get(dc, 0.0) + amount
        return need


class ResourceLedger:
    """Tracks active SFC reservations and releases them at request expiry."""

    def __init__(self, network: MECNetwork, *, instance_overhead: float = INSTANCE_OVERHEAD) -> None:
        self.network = network
        self.instance_overhead = instance_overhead
        self.clear()

    def clear(self) -> None:
        self.compute = {dc: 0.0 for dc in self.network.data_centers}
        self.links = {MECNetwork.link_key(left, right): 0.0 for left, right in self.network.graph.edges}
        self.instances: dict[InstanceKey, int] = {}
        self.reservations: list[Reservation] = []
        self.time = -1.0
        self.start_time: float | None = None
        self.compute_time = 0.0
        self.bandwidth_time = 0.0
        self.active_time = 0.0
        self.instances_created = 0

    # -- time ---------------------------------------------------------------
    def _integrate(self, until: float, *, extra_active: int = 0) -> None:
        if self.start_time is None or until <= self.time:
            return
        dt = until - self.time
        self.compute_time += sum(self.compute.values()) * dt
        self.bandwidth_time += sum(self.links.values()) * dt
        self.active_time += (len(self.reservations) + extra_active) * dt
        self.time = until

    def advance(self, arrival_time: float) -> None:
        # A training epoch restarts the synthetic arrival stream.
        if arrival_time < self.time:
            self.clear()
        if self.start_time is None:
            self.start_time = arrival_time
            self.time = arrival_time
        expiring = sorted((r for r in self.reservations if r.expires_at <= arrival_time), key=lambda r: r.expires_at)
        if expiring:
            ids = {id(r) for r in expiring}
            self.reservations = [r for r in self.reservations if id(r) not in ids]
        # Integrate piecewise: the active count drops at each expiry instant.
        for position, reservation in enumerate(expiring):
            self._integrate(reservation.expires_at, extra_active=len(expiring) - position)
            self._release(reservation)
        self._integrate(arrival_time)

    def drain(self) -> None:
        """Run until every active reservation expired (for final integrals)."""
        if self.reservations:
            self.advance(max(r.expires_at for r in self.reservations))

    def _release(self, reservation: Reservation) -> None:
        for dc, amount in reservation.compute.items():
            self.compute[dc] -= amount
        for dc, amount in reservation.dedicated_overhead.items():
            self.compute[dc] -= amount
        for link, amount in reservation.links.items():
            self.links[link] -= amount
        for key in reservation.shared_instances:
            self.instances[key] -= 1
            if self.instances[key] == 0:
                del self.instances[key]
                self.compute[key[0]] -= self.instance_overhead

    # -- queries ------------------------------------------------------------
    def residual_compute(self, dc: str) -> float:
        return self.network.compute_capacity(dc) - self.compute[dc]

    def residual_bandwidth(self, link: Link) -> float:
        return self.network.bandwidth_capacity(link) - self.links[link]

    def has_instance(self, dc: str, vnf_type: str) -> bool:
        return self.instances.get((dc, vnf_type), 0) > 0

    def can_admit(self, admission: Admission) -> tuple[bool, tuple[str, ...]]:
        violations: list[str] = []
        for dc, amount in admission.compute_need(self.instance_overhead).items():
            if self.compute[dc] + amount > self.network.compute_capacity(dc) + 1e-9:
                violations.append(f"active compute capacity exceeded at {dc}")
        for link, amount in admission.links.items():
            if amount and self.links[link] + amount > self.network.bandwidth_capacity(link) + 1e-9:
                violations.append(f"active link bandwidth exceeded at {link}")
        return not violations, tuple(violations)

    def commit(self, admission: Admission, *, expires_at: float) -> None:
        for dc, amount in admission.compute.items():
            self.compute[dc] += amount
        for dc, amount in admission.dedicated_overhead.items():
            self.compute[dc] += amount
        links = {link: amount for link, amount in admission.links.items() if amount}
        for link, amount in links.items():
            self.links[link] += amount
        for key in admission.shared_instances:
            if key not in self.instances:
                self.instances[key] = 0
                self.compute[key[0]] += self.instance_overhead
                self.instances_created += 1
            self.instances[key] += 1
        if self.instance_overhead > 0:
            self.instances_created += round(sum(admission.dedicated_overhead.values()) / self.instance_overhead)
        self.reservations.append(Reservation(expires_at, dict(admission.compute), links, tuple(admission.shared_instances), dict(admission.dedicated_overhead)))
