"""Old-workload check: new placement logic vs baselines on the original stream.

The original stream sends one request per time unit with ~1000-unit
lifetimes, so almost nothing is released in a 100-request run. This isolates
how much of the improvement comes from the algorithm rather than from the
Poisson workload used in the main experiments.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fppvs.baselines import greedy_choice, prior_choice, random_chooser, run_stream, shortest_choice
from fppvs.experiment import build_environments
from fppvs.workloads import make_synthetic_scenario


def main() -> None:
    seeds = [7, 8, 9, 10, 11]
    methods = {
        "prior-only (FPPVS placement, no DRL)": (prior_choice, True, 4),
        "shortest+sharing": (shortest_choice, True, 0),
        "shortest": (shortest_choice, False, 0),
        "greedy": (greedy_choice, False, 0),
        "random": (None, False, 0),
    }
    results: dict[str, list[float]] = {name: [] for name in methods}
    for seed in seeds:
        scenario = make_synthetic_scenario(requests=100, seed=seed + 100_000)
        for name, (chooser, sharing, retries) in methods.items():
            envs, ledger = build_environments(scenario.network, scenario.requests, sharing=sharing, fairness=False)
            chooser = chooser or random_chooser(seed)
            results[name].append(run_stream(envs, chooser, ledger, retries=retries).acceptance)
    summary = {name: {"mean": statistics.mean(v), "std": statistics.stdev(v), "per_seed": v} for name, v in results.items()}
    out = Path("output/scenarios/old-workload.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for name, s in summary.items():
        print(f"{name:40s} {100 * s['mean']:.1f} ± {100 * s['std']:.1f}")


if __name__ == "__main__":
    main()
