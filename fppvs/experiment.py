"""Scenario experiments: train FPPVS, evaluate it and baselines on a hold-out stream."""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace

import torch

from .admission import ResourceLedger
from .baselines import (
    Chooser, StreamResult, greedy_choice, model_chooser, prior_choice, random_chooser,
    run_stream,
)
from .environment import ORIGINAL_FEATURES, PAPER_FEATURES, ROW_PRIOR, PlacementEnvironment
from .neural import CNNActorCritic, MLPActorCritic, OriginalCNNActorCritic
from .sqn import SQNLSTMPredictor
from .substrate import MECNetwork
from .training import TrainingConfig, resolve_device, train, train_federated
from .workloads import MEAN_LIFETIME, TOPOLOGIES, make_network, make_requests

MEAN_FLOW_COMPUTE_PER_SFC = 7 * 0.7  # 4--10 VNFs x U(0.5, 0.9)


def arrival_rate_for_load(network: MECNetwork, load: float) -> float:
    """Poisson rate whose offered compute demand is ``load`` x total DC capacity."""
    capacity = sum(network.compute_capacity(dc) for dc in network.data_centers)
    return load * capacity / (MEAN_FLOW_COMPUTE_PER_SFC * MEAN_LIFETIME)


def build_environments(network, requests, *, sharing: bool, fairness: bool, device: str = "cpu", lookahead: bool = True, paper_mode: bool = False, zhang_mode: bool = False, original_mode: bool = False):
    ledger = ResourceLedger(network)
    throughputs = [] if fairness else None
    # The 2022 adaptation keeps a longer SQN queue (TD = 20).
    predictor = SQNLSTMPredictor(time_depth=20 if zhang_mode else 5, device=device)
    environments = []
    # Predict before observing each SFC so the forecast stays causal.
    for request in requests:
        prediction = predictor.prediction()
        predictor.update(request)
        environments.append(PlacementEnvironment(
            network, request, sharing=sharing, fairness_throughputs=throughputs,
            sqn_prediction=prediction, ledger=ledger, lookahead=lookahead, paper_mode=paper_mode, zhang_mode=zhang_mode, original_mode=original_mode,
        ))
    return environments, ledger


@dataclass
class ScenarioOutcome:
    topology: str
    load: float
    seed: int
    arrival_rate: float
    methods: dict[str, dict[str, float]] = field(default_factory=dict)
    reasons: dict[str, dict[str, int]] = field(default_factory=dict)
    training: dict[str, float] = field(default_factory=dict)
    training_original: dict[str, float] = field(default_factory=dict)
    training_zhang2022: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ExperimentConfig:
    train_requests: int = 600
    test_requests: int = 600
    agents: int = 4
    rounds: int = 10
    local_episodes: int = 60
    retries: int = 4
    device: str = "cpu"
    variants: tuple[str, ...] = ("fppvs", "no-sharing", "no-fairness", "single-agent", "no-retry", "prior-only", "original", "zhang2022")
    # Plain placement heuristics run without VNF sharing, as in the original repository.
    baselines: tuple[str, ...] = ("greedy", "random")


def _train_model(network, seed: int, rate: float, cfg: ExperimentConfig, *, sharing: bool, fairness: bool, federated: bool, paper: bool = False, zhang: bool = False):
    torch.manual_seed(seed)
    n = len(network.data_centers)
    if zhang:
        model = MLPActorCritic(PAPER_FEATURES, n)
    elif paper:
        # Original FPPVS, following the paper's Section 4.3 closely.
        model = OriginalCNNActorCritic(ORIGINAL_FEATURES, n)
    else:
        model = CNNActorCritic(n, prior_row=ROW_PRIOR)
    config = TrainingConfig(episodes=cfg.local_episodes, device=cfg.device, epsilon_start=0.15)
    started = time.perf_counter()
    if federated:
        # Each agent is a local edge region with its own request stream and ledger.
        groups = [
            build_environments(network, make_requests(network, cfg.train_requests, seed * 1000 + agent, arrival_rate=rate), sharing=sharing, fairness=fairness, device=cfg.device, original_mode=paper, zhang_mode=zhang)[0]
            for agent in range(cfg.agents)
        ]
        history = train_federated(model, groups, rounds=cfg.rounds, local_episodes=cfg.local_episodes, seed=seed, config=config)
        acceptance, episodes = history.acceptance_rate, len(history.accepted)
    else:
        envs, _ = build_environments(network, make_requests(network, cfg.train_requests, seed * 1000, arrival_rate=rate), sharing=sharing, fairness=fairness, device=cfg.device, original_mode=paper, zhang_mode=zhang)
        total = cfg.rounds * cfg.local_episodes * cfg.agents
        history = train(model, envs, seed=seed, config=replace(config, episodes=total))
        acceptance, episodes = sum(history.accepted) / len(history.accepted), len(history.accepted)
    return model, {"training_acceptance": acceptance, "training_episodes": episodes, "training_seconds": time.perf_counter() - started}


def _evaluate(network, test_requests, chooser: Chooser, *, sharing: bool, retries: int, device: str, paper: bool = False, zhang: bool = False) -> StreamResult:
    envs, ledger = build_environments(network, test_requests, sharing=sharing, fairness=False, device=device, original_mode=paper, zhang_mode=zhang)
    return run_stream(envs, chooser, ledger, retries=retries)


def run_scenario(topology: str, load: float, seed: int, cfg: ExperimentConfig) -> ScenarioOutcome:
    nodes, links = TOPOLOGIES[topology]
    network = make_network(nodes, links, seed)
    rate = arrival_rate_for_load(network, load)
    outcome = ScenarioOutcome(topology, load, seed, rate)
    test_requests = make_requests(network, cfg.test_requests, seed * 1000 + 999, arrival_rate=rate)
    device = str(resolve_device(cfg.device))

    def record(name: str, result: StreamResult) -> None:
        outcome.methods[name] = result.summary()
        outcome.reasons[name] = dict(result.reasons)

    trained: dict[tuple, tuple[torch.nn.Module, dict]] = {}
    def model_for(sharing: bool, fairness: bool, federated: bool, paper: bool = False, zhang: bool = False):
        key = (sharing, fairness, federated, paper, zhang)
        if key not in trained:
            trained[key] = _train_model(network, seed, rate, cfg, sharing=sharing, fairness=fairness, federated=federated, paper=paper, zhang=zhang)
        return trained[key]

    variant_specs = {
        "fppvs": dict(sharing=True, fairness=True, federated=True, retries=cfg.retries),
        "no-sharing": dict(sharing=False, fairness=True, federated=True, retries=cfg.retries),
        "no-fairness": dict(sharing=True, fairness=False, federated=True, retries=cfg.retries),
        "single-agent": dict(sharing=True, fairness=True, federated=False, retries=cfg.retries),
        "no-retry": dict(sharing=True, fairness=True, federated=True, retries=0),
        # Original FPPVS as specified in the paper, same training budget.
        "original": dict(sharing=True, fairness=True, federated=True, retries=0, paper=True),
        # Our adaptation of Zhang et al. (2022): single synchronous agent, same episode budget.
        "zhang2022": dict(sharing=True, fairness=False, federated=False, retries=0, zhang=True),
    }
    for name in cfg.variants:
        if name == "prior-only":
            record(name, _evaluate(network, test_requests, prior_choice, sharing=True, retries=cfg.retries, device=device))
            continue
        spec = variant_specs[name]
        model, info = model_for(spec["sharing"], spec["fairness"], spec["federated"], spec.get("paper", False), spec.get("zhang", False))
        if name == "fppvs":
            outcome.training = info
        if name == "original":
            outcome.training_original = info
        if name == "zhang2022":
            outcome.training_zhang2022 = info
        model.to(device)
        record(name, _evaluate(network, test_requests, model_chooser(model, device), sharing=spec["sharing"], retries=spec["retries"], device=device, paper=spec.get("paper", False), zhang=spec.get("zhang", False)))
    baseline_choosers = {"greedy": greedy_choice, "random": random_chooser(seed)}
    for name in cfg.baselines:
        record(name, _evaluate(network, test_requests, baseline_choosers[name], sharing=False, retries=0, device=device))
    return outcome
