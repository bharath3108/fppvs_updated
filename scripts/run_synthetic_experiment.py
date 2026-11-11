"""Run FPPVS on synthetic data; this is not an exact paper reproduction.

Example: python scripts/run_synthetic_experiment.py --requests 100 --episodes 500
Federated: python scripts/run_synthetic_experiment.py --requests 100 --agents 4 --rounds 20 --local-episodes 10
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch

from fppvs.baselines import greedy_choice, random_chooser, run_stream
from fppvs.environment import ROW_PRIOR
from fppvs.experiment import arrival_rate_for_load, build_environments
from fppvs.neural import CNNActorCritic
from fppvs.reporting import save_learning_plot
from fppvs.training import TrainingConfig, TrainingHistory, evaluate_policy, resolve_device, train, train_federated
from fppvs.workloads import TOPOLOGIES, make_network, make_requests


def _mean_std_ci95(values: list[float]) -> dict[str, float]:
    mean = statistics.mean(values)
    if len(values) == 1:
        return {"mean": mean, "std": 0.0, "ci95_half_width": 0.0}
    return {"mean": mean, "std": statistics.stdev(values), "ci95_half_width": 1.96 * statistics.stdev(values) / (len(values) ** 0.5)}


def run_once(requests: int, episodes: int, seed: int, *, sharing: bool, fairness: bool, device: str, agents: int = 1, rounds: int | None = None, local_episodes: int | None = None, checkpoint: str | None = None, topology: str = "backbone", load: float = 1.0):
    network = make_network(*TOPOLOGIES[topology], seed)
    rate = arrival_rate_for_load(network, load)
    torch.manual_seed(seed)
    model = CNNActorCritic(len(network.data_centers), prior_row=ROW_PRIOR)
    config = TrainingConfig(episodes=episodes, device=device)
    if agents == 1:
        environments, _ = build_environments(network, make_requests(network, requests, seed * 1000, arrival_rate=rate), sharing=sharing, fairness=fairness, device=device)
        history = train(model, environments, seed=seed, config=config, checkpoint=checkpoint)
        training_episodes = len(history.accepted)
        training_acceptance = sum(history.accepted) / len(history.accepted)
        mean_training_reward = sum(history.episode_rewards) / len(history.episode_rewards)
    else:
        if rounds is None or local_episodes is None:
            raise ValueError("federated training requires rounds and local_episodes")
        # Each agent is a local region with its own request stream and ledger.
        groups = [build_environments(network, make_requests(network, requests, seed * 1000 + agent, arrival_rate=rate), sharing=sharing, fairness=fairness, device=device)[0] for agent in range(agents)]
        federated = train_federated(model, groups, rounds=rounds, local_episodes=local_episodes, seed=seed, config=config, checkpoint=checkpoint)
        history = TrainingHistory(federated.round_rewards, tuple(), tuple(), federated.device)
        training_episodes = len(federated.accepted)
        training_acceptance = federated.acceptance_rate
        mean_training_reward = sum(federated.episode_rewards) / len(federated.episode_rewards)
    # Hold-out stream on the same substrate, never seen during training.
    test_requests = make_requests(network, requests, seed * 1000 + 999, arrival_rate=rate)
    evaluation_envs, _ = build_environments(network, test_requests, sharing=sharing, fairness=fairness, device=device)
    evaluation = evaluate_policy(model, evaluation_envs, device=device)
    fdrl_acceptance = sum(evaluation.accepted) / len(evaluation.accepted)
    mean_reward = sum(evaluation.episode_rewards) / len(evaluation.episode_rewards)
    greedy_envs, greedy_ledger = build_environments(network, test_requests, sharing=False, fairness=False, device=device)
    greedy = run_stream(greedy_envs, greedy_choice, greedy_ledger).acceptance
    random_envs, random_ledger = build_environments(network, test_requests, sharing=False, fairness=False, device=device)
    random = run_stream(random_envs, random_chooser(seed), random_ledger).acceptance
    return history, {
        "seed": seed,
        "fdrl_acceptance": fdrl_acceptance,
        "greedy_acceptance": greedy,
        "random_acceptance": random,
        "mean_reward": mean_reward,
        "training_acceptance": training_acceptance,
        "mean_training_reward": mean_training_reward,
        "fdrl_training_episodes": training_episodes,
        "arrival_rate": rate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic FPPVS experiment; not a paper-result reproduction.")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--episodes", type=int, default=100, help="episodes for one non-federated agent")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--agents", type=int, default=1, help="use >1 to enable FedAvg across local agents")
    parser.add_argument("--rounds", type=int, default=20, help="FedAvg rounds when --agents > 1")
    parser.add_argument("--local-episodes", type=int, default=10, help="episodes each agent performs per FedAvg round")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--checkpoint", default=None, help="model checkpoint path; add {seed} for one checkpoint per run")
    parser.add_argument("--topology", choices=sorted(TOPOLOGIES), default="backbone")
    parser.add_argument("--load", type=float, default=1.0, help="offered compute demand / total DC capacity")
    parser.add_argument("--no-sharing", action="store_true")
    parser.add_argument("--no-fairness", action="store_true")
    parser.add_argument("--output", default="output/synthetic-results.json")
    parser.add_argument("--plot", default="output/synthetic-learning.png")
    args = parser.parse_args()
    if args.requests < 1 or args.episodes < 1 or args.runs < 1 or args.agents < 1 or args.rounds < 1 or args.local_episodes < 1:
        parser.error("request, episode, run, agent, round, and local-episode counts must be positive")
    resolved_device = str(resolve_device(args.device))
    outcomes = []
    first_history = None
    for run in range(args.runs):
        seed = args.seed + run
        checkpoint = args.checkpoint.format(seed=seed) if args.checkpoint else None
        history, outcome = run_once(args.requests, args.episodes, seed, sharing=not args.no_sharing, fairness=not args.no_fairness, device=resolved_device, agents=args.agents, rounds=args.rounds, local_episodes=args.local_episodes, checkpoint=checkpoint, topology=args.topology, load=args.load)
        outcomes.append(outcome)
        first_history = first_history or history
    result = {
        "scenario": "synthetic; not exact paper datasets",
        "modules": {"parallelization": True, "sqn_lstm": True, "sharing": not args.no_sharing, "fairness": not args.no_fairness, "federated": args.agents > 1},
        "device": resolved_device,
        "seed": args.seed,
        "runs": args.runs,
        "requests": args.requests,
        "topology": args.topology,
        "load": args.load,
        "training": {"agents": args.agents, "rounds": args.rounds if args.agents > 1 else None, "local_episodes": args.local_episodes if args.agents > 1 else None, "episodes": args.episodes if args.agents == 1 else None},
        "statistics": {key: _mean_std_ci95([outcome[key] for outcome in outcomes]) for key in outcomes[0] if key != "seed"},
        "per_run": outcomes,
    }
    plot = save_learning_plot(first_history, args.plot)
    result["learning_plot"] = str(plot)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
