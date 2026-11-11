"""Runnable placement MDP for FDRL experiments (Section 4.3).

One SFC request per episode; its internal VNFs are placed one by one on
data centers (DCs). The VNF order is a topological order of the p-SFC, so
when a VNF is placed every virtual edge into it (and its edge to egress, if
any) can be routed immediately. That lets the action mask prune DCs that
would break compute, bandwidth or latency constraints *before* the agent
commits, as Section 4.3 describes ("prune nodes that cannot satisfy resource
or bandwidth constraints").
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import torch

from .admission import Admission, InstanceKey, Link, ResourceLedger
from .metrics import jains_fairness
from .models import SFCRequest, VNFKind
from .parallelization import parallelize_sfc
from .placement import evaluate_placement
from .sharing import vnf_type
from .sqn import SQNPrediction
from .substrate import MECNetwork

# Rows of the per-DC state grid (shape 1 x 1 x FEATURES x DCs).
FEATURES = 9
ROW_RESIDUAL, ROW_DEMAND, ROW_FROM_PREV, ROW_TO_DEST, ROW_BANDWIDTH, ROW_REUSE, ROW_FORECAST, ROW_PRIOR, ROW_MASK = range(FEATURES)
PAPER_FEATURES = 4  # original FPPVS state: residual, demand, distance, forecast
ORIGINAL_FEATURES = 6  # + node already hosts this VNF type, + candidate after pruning

REJECT_REWARD = -10.0


@dataclass(frozen=True, slots=True)
class StepResult:
    state: torch.Tensor
    reward: float
    terminated: bool
    info: dict[str, object]


@dataclass(frozen=True, slots=True)
class _Option:
    """Consequences of placing the current VNF on one DC."""

    feasible: bool
    compute_cost: float
    new_instance: bool
    links: dict[Link, float]
    hops: float          # bandwidth-weighted hops added, in units of data rate
    finish: float        # earliest finish time of this VNF on the critical path
    bandwidth_margin: float


class PlacementEnvironment:
    """Rewards follow Eq. (28): -10 invalid/rejected, +1 per valid placement,
    -1 for a new instance, and a final objective reward for accepted chains.
    """

    def __init__(
        self,
        network: MECNetwork,
        request: SFCRequest,
        *,
        sharing: bool | None = None,
        fairness_throughputs: list[float] | None = None,
        sqn_prediction: SQNPrediction | None = None,
        ledger: ResourceLedger | None = None,
        lookahead: bool = True,
        paper_mode: bool = False,
        zhang_mode: bool = False,
        original_mode: bool = False,
    ):
        """``paper_mode`` reproduces the original FPPVS specification: a 4-row
        state (residual capacity, demand, distance, forecast), compute-only
        pruning and the paper's Eq. (28) step rewards (+1 valid, +5 reuse,
        -1 new instance).

        ``zhang_mode`` is our adaptation of Zhang et al. (2022): the chain is
        placed as a plain sequential SFC (no parallelization), with the same
        4-row state and compute-only checks, reuse of live same-type
        instances, rollback on failure, and a long-term revenue-to-cost
        (LTCR) reward with a fixed failure penalty.

        ``original_mode`` is the original FPPVS read closely from Section 4.3
        of the paper: resource-aware pruning drops nodes without enough compute
        *or available bandwidth*; the next VNF is placed on the current node or
        a feasible neighbouring node; nodes that already host the same VNF type
        are marked in the state (the paper's history-based prioritisation); and
        the state is a fixed-length grid for the paper's CNN. It keeps the
        paper's Eq. (28) reward and has no latency look-ahead, placement prior
        or retries, which are our additions."""
        self.zhang_mode = zhang_mode
        self.original_mode = original_mode
        if original_mode:
            paper_mode = True
        if zhang_mode:
            # No network-function parallelism: every VNF stays on the main chain.
            request = replace(
                request,
                vnfs=tuple(replace(vnf, kind=VNFKind.SHAPER) for vnf in request.vnfs),
                dependency_matrix=tuple(tuple(0 for _ in request.vnfs) for _ in request.vnfs),
            )
            paper_mode = True
        self.network, self.request = network, request
        self.paper_mode = paper_mode
        if paper_mode:
            lookahead = False
        self.p_sfc = parallelize_sfc(request)
        self.dcs = network.data_centers
        # Sharing is on unless explicitly turned off.
        self.sharing = True if sharing is None else sharing
        self.fairness_throughputs = fairness_throughputs
        self.sqn_prediction = sqn_prediction
        self.ledger = ledger if ledger is not None else ResourceLedger(network)
        self.lookahead = lookahead
        self.max_latency = request.max_latency or float("inf")
        graph = self.p_sfc.graph
        self.vnf_by_id = {vnf.id: vnf for vnf in request.vnfs}
        # Edges completed when each VNF is placed: all in-edges plus edges to egress.
        self.completed_edges = {
            vnf.id: [(u, vnf.id) for u in graph.predecessors(vnf.id)]
            + ([(vnf.id, request.destination)] if graph.has_edge(vnf.id, request.destination) else [])
            for vnf in request.vnfs
        }
        self.reset()

    # -- episode ------------------------------------------------------------
    def reset(self) -> torch.Tensor:
        self.ledger.advance(self.request.arrival_time)
        self.index, self.done = 0, False
        self.assignment = {self.request.source: self.request.source, self.request.destination: self.request.destination}
        self.reserved = {dc: 0.0 for dc in self.dcs}      # per-flow demand + dedicated overhead
        self.flow_compute = {dc: 0.0 for dc in self.dcs}
        self.dedicated = {dc: 0.0 for dc in self.dcs}
        self.links: dict[Link, float] = {}
        self.finish = {self.request.source: 0.0}
        self.shared_keys: list[InstanceKey] = []
        self.new_keys: set[InstanceKey] = set()
        self.instances_started = 0
        self.reused_count = 0
        self._options: list[_Option] | None = None
        return self.state()

    @property
    def current_vnf(self):
        return self.request.vnfs[self.index]

    def _live(self, dc: str, type_name: str) -> bool:
        return self.ledger.has_instance(dc, type_name) or (dc, type_name) in self.new_keys

    def options(self) -> list[_Option]:
        if self._options is None:
            self._options = [self._option(dc) for dc in self.dcs]
        return self._options

    def _option(self, dc: str) -> _Option:
        vnf = self.current_vnf
        type_name = vnf_type(vnf)
        new_instance = not (self.sharing and self._live(dc, type_name))
        overhead = self.ledger.instance_overhead if new_instance else 0.0
        compute_cost = vnf.compute_demand + overhead
        compute_ok = self.ledger.residual_compute(dc) - self.reserved[dc] - compute_cost >= -1e-9

        links: dict[Link, float] = {}
        finish = 0.0
        node_cost = vnf.processing_latency + vnf.virtualization_latency
        for u, v in self.completed_edges[vnf.id]:
            left = self.assignment[u] if u != vnf.id else dc
            right = dc if v == vnf.id else self.assignment[v]
            demand = self.request.bandwidth_demand(u, v)
            for link in self.network.route_links(left, right):
                links[link] = links.get(link, 0.0) + demand
            if v == vnf.id:
                finish = max(finish, self.finish[u] + self.network.latency(left, dc))
        finish += node_cost
        margin = 1.0
        bandwidth_ok = True
        for link, amount in links.items():
            free = self.ledger.residual_bandwidth(link) - self.links.get(link, 0.0) - amount
            margin = min(margin, free / self.network.bandwidth_capacity(link))
            if free < -1e-9:
                bandwidth_ok = False
        latency_ok = finish + self.network.latency(dc, self.request.destination) <= self.max_latency + 1e-9
        if self.original_mode:
            # Paper: prune nodes lacking compute or bandwidth, and choose the
            # current node or a neighbouring node for the next VNF.
            previous = self.request.source if self.index == 0 else self.assignment[self.request.vnfs[self.index - 1].id]
            neighbour = dc == previous or self.network.graph.has_edge(previous, dc)
            feasible = compute_ok and bandwidth_ok and neighbour
        else:
            feasible = compute_ok and (not self.lookahead or (bandwidth_ok and latency_ok))
        rate = max(self.request.data_rate, 1e-9)
        hops = sum(links.values()) / rate
        return _Option(feasible, compute_cost, new_instance, links, hops, finish, margin)

    def action_mask(self) -> torch.Tensor:
        if self.done:
            return torch.zeros(len(self.dcs), dtype=torch.bool)
        return torch.tensor([option.feasible for option in self.options()])

    def has_action(self) -> bool:
        return not self.done and any(option.feasible for option in self.options())

    def heuristic_scores(self) -> list[float]:
        """Placement prior: keep the chain short and on few DCs, reuse live
        instances, and avoid nearly-full DCs and links."""
        if self.done:
            return [0.0] * len(self.dcs)
        scores = []
        destination = self.request.destination
        previous = self.request.source if self.index == 0 else self.assignment[self.request.vnfs[self.index - 1].id]
        scale = self.max_latency if self.max_latency != float("inf") else 150.0
        for dc, option in zip(self.dcs, self.options()):
            future_hops = len(self.network.shortest_path(dc, destination)) - 1
            residual = (self.ledger.residual_compute(dc) - self.reserved[dc] - option.compute_cost) / self.network.compute_capacity(dc)
            # Bandwidth now (hops x rate) and the minimum still to come to egress.
            score = -(option.hops + future_hops)
            # Latency of the critical path so far plus the shortest way to egress.
            score -= 2.0 * (option.finish + self.network.latency(dc, destination)) / scale
            score += 0.5 * (not option.new_instance)
            score += 0.3 * (dc == previous)
            score += 0.5 * residual
            score -= 3.0 * max(0.0, 0.25 - option.bandwidth_margin) / 0.25
            scores.append(score)
        return scores

    def state(self) -> torch.Tensor:
        n = len(self.dcs)
        rows_out = ORIGINAL_FEATURES if self.original_mode else (PAPER_FEATURES if self.paper_mode else FEATURES)
        if self.done:
            return torch.zeros(1, 1, rows_out, n)
        vnf = self.current_vnf
        caps = [self.network.compute_capacity(dc) for dc in self.dcs]
        previous = self.request.source if self.index == 0 else self.assignment[self.request.vnfs[self.index - 1].id]
        scale = self.max_latency if self.max_latency != float("inf") else 150.0
        forecast = 0.0 if self.sqn_prediction is None else self.sqn_prediction.for_vnf(vnf_type(vnf))
        if self.paper_mode:
            distance = [self.network.latency(previous, dc) for dc in self.dcs]
            rows = [
                [(self.ledger.residual_compute(dc) - self.reserved[dc]) / cap for dc, cap in zip(self.dcs, caps)],
                [vnf.compute_demand / cap for cap in caps],
                [d / max(1.0, max(distance)) for d in distance],
                [forecast / cap for cap in caps],
            ]
            if self.original_mode:
                options = self.options()
                type_name = vnf_type(vnf)
                rows += [
                    [float(self._live(dc, type_name)) for dc in self.dcs],  # node already hosts this VNF type
                    [float(option.feasible) for option in options],          # candidate nodes after pruning
                ]
            return torch.tensor(rows, dtype=torch.float32).view(1, 1, rows_out, n)
        options = self.options()
        rows = [
            [(self.ledger.residual_compute(dc) - self.reserved[dc]) / cap for dc, cap in zip(self.dcs, caps)],
            [vnf.compute_demand / cap for cap in caps],
            [self.network.latency(previous, dc) / scale for dc in self.dcs],
            [self.network.latency(dc, self.request.destination) / scale for dc in self.dcs],
            [max(-1.0, option.bandwidth_margin) for option in options],
            [float(not option.new_instance) for option in options],
            [forecast / cap for cap in caps],
            self.heuristic_scores(),
            [float(option.feasible) for option in options],
        ]
        return torch.tensor(rows, dtype=torch.float32).view(1, 1, FEATURES, n)

    def reject(self, reason: str) -> StepResult:
        """End the episode without placing the request (nothing is committed)."""
        self.done = True
        return StepResult(self.state(), REJECT_REWARD, True, {"accepted": False, "reason": reason})

    def step(self, action: int) -> StepResult:
        if self.done:
            raise RuntimeError("episode is already terminated")
        options = self.options()
        if action < 0 or action >= len(self.dcs) or not options[action].feasible:
            return self.reject("invalid action")
        vnf, dc, option = self.current_vnf, self.dcs[action], options[action]
        self.assignment[vnf.id] = dc
        self.finish[vnf.id] = option.finish
        self.flow_compute[dc] += vnf.compute_demand
        self.reserved[dc] += option.compute_cost
        for link, amount in option.links.items():
            self.links[link] = self.links.get(link, 0.0) + amount
        key = (dc, vnf_type(vnf))
        if self.sharing:
            self.shared_keys.append(key)
            if option.new_instance:
                self.new_keys.add(key)
        elif option.new_instance:
            self.dedicated[dc] += self.ledger.instance_overhead
        reused = not option.new_instance
        self.reused_count += reused
        self.instances_started += option.new_instance
        if self.zhang_mode:
            step_reward = 0.0  # LTCR reward is given once, at the end
        elif self.paper_mode:
            step_reward = 1.0 + (5.0 if reused else -1.0)  # paper Eq. (28)
        else:
            step_reward = 1.0 - (0.0 if reused else 1.0) - 0.2 * option.hops
        self.index += 1
        self._options = None
        if self.index < len(self.request.vnfs):
            if not self.has_action():
                result = self.reject("no feasible data center")
                return StepResult(result.state, step_reward + REJECT_REWARD, True, result.info)
            return StepResult(self.state(), step_reward, False, {"accepted": None, "reused": reused})
        return self._finish(step_reward, reused)

    def _finish(self, step_reward: float, reused: bool) -> StepResult:
        report = evaluate_placement(self.network, self.request, self.p_sfc, self.assignment)
        self.done = True
        admission = Admission(
            compute={dc: amount for dc, amount in self.flow_compute.items() if amount},
            links=dict(report.link_bandwidth_usage),
            shared_instances=tuple(self.shared_keys),
            new_instances=tuple(key for key in self.new_keys if not self.ledger.has_instance(*key)),
            dedicated_overhead={dc: amount for dc, amount in self.dedicated.items() if amount},
        )
        ledger_ok, ledger_violations = self.ledger.can_admit(admission)
        if not report.feasible or not ledger_ok:
            reason = "; ".join(report.violations + ledger_violations)
            return StepResult(self.state(), step_reward + REJECT_REWARD, True, {"accepted": False, "report": report, "reason": reason})
        self.ledger.commit(admission, expires_at=self.request.arrival_time + self.request.ttl)
        if self.zhang_mode:
            # LTCR: revenue (requested compute + bandwidth) over the cost actually used.
            revenue = sum(vnf.compute_demand for vnf in self.request.vnfs) + self.request.data_rate * self.p_sfc.graph.number_of_edges()
            cost = sum(admission.compute_need(self.ledger.instance_overhead).values()) + sum(admission.links.values())
            objective = 10.0 * min(2.0, revenue / max(cost, 1e-9))
        else:
            # Normalized objective: acceptance plus latency slack.
            objective = 5.0 * (1.0 + max(0.0, 1.0 - report.latency.end_to_end / (self.request.max_latency or 1.0)))
        fairness_bonus = 0.0
        if self.fairness_throughputs is not None:
            before = jains_fairness(self.fairness_throughputs)
            self.fairness_throughputs.append(self.request.data_rate)
            fairness_bonus = 5 * (jains_fairness(self.fairness_throughputs) - before)
        compute_used = sum(admission.compute_need(self.ledger.instance_overhead).values())
        return StepResult(
            self.state(),
            step_reward + objective + fairness_bonus,
            True,
            {
                "accepted": True,
                "report": report,
                "reused": reused,
                "fairness_bonus": fairness_bonus,
                "compute": compute_used,
                "bandwidth": sum(admission.links.values()),
                "reused_vnfs": self.reused_count,
                "new_instances": self.instances_started,
            },
        )
