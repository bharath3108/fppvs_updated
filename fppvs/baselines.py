"""Transparent reference baselines and a common stream runner.

All methods run in the identical environment (same substrate, request
stream, feasibility mask, sharing model and ledger); only the DC choice
differs. These are simple stand-ins for the strategy families the paper
discusses, not re-implementations of RVNF, DRL-SFCP, PVFP or DPC:

* random - any feasible DC;
* greedy - load balancing: most residual compute first.

It also holds the choosers used for the learned policies and the placement
prior, the rollback-and-retry admission, and the stream runner that collects
every metric in the report.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from random import Random
from typing import Callable

import torch

from .admission import ResourceLedger
from .environment import PlacementEnvironment

Chooser = Callable[[PlacementEnvironment, list[int]], int]


def _previous_dc(environment: PlacementEnvironment) -> str:
    request = environment.request
    return request.source if environment.index == 0 else environment.assignment[request.vnfs[environment.index - 1].id]


def greedy_choice(environment: PlacementEnvironment, candidates: list[int]) -> int:
    previous = _previous_dc(environment)
    def key(i: int):
        dc = environment.dcs[i]
        residual = (environment.ledger.residual_compute(dc) - environment.reserved[dc]) / environment.network.compute_capacity(dc)
        return (residual, -environment.network.latency(previous, dc))
    return max(candidates, key=key)


def prior_choice(environment: PlacementEnvironment, candidates: list[int]) -> int:
    scores = environment.heuristic_scores()
    return max(candidates, key=lambda i: scores[i])


def random_chooser(seed: int) -> Chooser:
    rng = Random(seed)
    return lambda environment, candidates: rng.choice(candidates)


def model_chooser(model: torch.nn.Module, device: str | torch.device = "cpu") -> Chooser:
    model.eval()
    def choose(environment: PlacementEnvironment, candidates: list[int]) -> int:
        with torch.no_grad():
            logits, _ = model(environment.state().to(device))
        mask = environment.action_mask().to(device)
        return int(logits.squeeze(0).masked_fill(~mask, float("-inf")).argmax().item())
    return choose


def place(environment: PlacementEnvironment, chooser: Chooser):
    """Run one episode; return the final StepResult."""
    environment.reset()
    if not environment.has_action():
        return environment.reject("no feasible data center")
    final = None
    while not environment.done:
        candidates = [i for i, valid in enumerate(environment.action_mask().tolist()) if valid]
        final = environment.step(chooser(environment, candidates))
    return final


def place_with_retry(environment: PlacementEnvironment, chooser: Chooser, retries: int):
    """Rollback-and-retry admission: if the policy's placement is rejected,
    nothing was committed, so retry with the next-best first DCs (ranked by
    the placement prior) before rejecting the request."""
    final = place(environment, chooser)
    if final.info.get("accepted") or retries <= 0:
        return final
    environment.reset()
    if not environment.has_action():
        return final
    scores = environment.heuristic_scores()
    mask = environment.action_mask().tolist()
    first = chooser(environment, [i for i, ok in enumerate(mask) if ok])
    alternatives = sorted((i for i, ok in enumerate(mask) if ok and i != first), key=lambda i: -scores[i])[:retries]
    for action in alternatives:
        environment.reset()
        attempt = environment.step(action)
        while not environment.done:
            candidates = [i for i, ok in enumerate(environment.action_mask().tolist()) if ok]
            attempt = environment.step(chooser(environment, candidates))
        if attempt.info.get("accepted"):
            return attempt
    return final


@dataclass
class StreamResult:
    """Outcome of one method on one request stream."""

    accepted: list[bool] = field(default_factory=list)
    latencies: list[float] = field(default_factory=list)
    hops: list[float] = field(default_factory=list)
    reasons: dict[str, int] = field(default_factory=dict)
    compute_time: float = 0.0
    bandwidth_time: float = 0.0
    active_time: float = 0.0
    duration: float = 0.0
    instances_created: int = 0
    reused_vnfs: int = 0
    placed_vnfs: int = 0
    decision_seconds: float = 0.0
    capacity_compute: float = 0.0
    capacity_bandwidth: float = 0.0
    window_compute_time: float = 0.0
    window_bandwidth_time: float = 0.0

    @property
    def acceptance(self) -> float:
        return sum(self.accepted) / len(self.accepted) if self.accepted else 0.0

    def summary(self) -> dict[str, float]:
        n_acc = max(1, sum(self.accepted))
        duration = max(self.duration, 1e-9)
        return {
            "acceptance": self.acceptance,
            "mean_latency": sum(self.latencies) / len(self.latencies) if self.latencies else 0.0,
            "mean_hops": sum(self.hops) / len(self.hops) if self.hops else 0.0,
            # Resource-time per accepted SFC (lower = fewer resources held for the same service).
            "compute_time_per_accepted": self.compute_time / n_acc,
            "bandwidth_time_per_accepted": self.bandwidth_time / n_acc,
            # Average resources held per running SFC at any moment.
            "compute_per_active_sfc": self.compute_time / max(self.active_time, 1e-9),
            "bandwidth_per_active_sfc": self.bandwidth_time / max(self.active_time, 1e-9),
            # Time-averaged utilization of total physical capacity.
            "compute_utilization": self.window_compute_time / duration / self.capacity_compute,
            "bandwidth_utilization": self.window_bandwidth_time / duration / self.capacity_bandwidth,
            "instances_per_accepted": self.instances_created / n_acc,
            "reuse_ratio": self.reused_vnfs / max(1, self.placed_vnfs),
            "decision_ms_per_request": 1000 * self.decision_seconds / max(1, len(self.accepted)),
        }


def run_stream(environments: list[PlacementEnvironment], chooser: Chooser, ledger: ResourceLedger, *, retries: int = 0) -> StreamResult:
    """Place a whole request stream with one method and collect metrics."""
    result = StreamResult()
    network = ledger.network
    result.capacity_compute = sum(network.compute_capacity(dc) for dc in network.data_centers)
    result.capacity_bandwidth = sum(network.bandwidth_capacity(network.link_key(*e)) for e in network.graph.edges)
    started = time.perf_counter()
    for environment in environments:
        final = place_with_retry(environment, chooser, retries)
        result.accepted.append(bool(final.info.get("accepted")))
        if final.info.get("accepted"):
            report = final.info["report"]
            result.latencies.append(report.latency.end_to_end)
            result.hops.append(sum(len(route) - 1 for route in report.routes.values()))
            result.reused_vnfs += final.info["reused_vnfs"]
            result.placed_vnfs += len(environment.request.vnfs)
        else:
            reason = str(final.info.get("reason", "rejected")).split(" at ")[0].split(":")[0]
            result.reasons[reason] = result.reasons.get(reason, 0) + 1
    result.decision_seconds = time.perf_counter() - started
    end_time = ledger.time
    result.duration = end_time - (ledger.start_time or 0.0)
    result.window_compute_time = ledger.compute_time
    result.window_bandwidth_time = ledger.bandwidth_time
    # Resource-time per accepted SFC must include each SFC's full lifetime.
    ledger.drain()
    result.compute_time = ledger.compute_time
    result.bandwidth_time = ledger.bandwidth_time
    result.active_time = ledger.active_time
    result.instances_created = ledger.instances_created
    return result
