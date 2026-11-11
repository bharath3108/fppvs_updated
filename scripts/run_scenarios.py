"""Run every FPPVS scenario (topology x load x seed) and write a report.

Synthetic data only; this is not an exact paper reproduction.

Example (full run, ~30-60 min on 8 cores):
    python scripts/run_scenarios.py --seeds 7 8 9 10 11 --workers 8
Quick smoke test:
    python scripts/run_scenarios.py --seeds 7 --rounds 2 --local-episodes 10 --requests 200 --stress-loads
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

LABELS = {
    "fppvs": "Updated FPPVS (ours)",
    "no-sharing": "FPPVS w/o sharing",
    "no-fairness": "FPPVS w/o fairness",
    "single-agent": "FPPVS single agent",
    "no-retry": "FPPVS w/o retry",
    "prior-only": "Prior only (no DRL)",
    "original": "Original FPPVS",
    "zhang2022": "2022 adaptation",
    "shortest+sharing": "Shortest-path + sharing",
    "shortest": "Shortest-path first-fit",
    "greedy": "Greedy",
    "random": "Random",
}
# Methods compared in the headline charts, in fixed colour order.
COMPARED = ("fppvs", "original", "zhang2022", "greedy", "random")
COLORS = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4")
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
TARGET = 0.70


def _job(args):
    topology, load, seed, cfg_dict = args
    import torch
    torch.set_num_threads(1)
    from fppvs.experiment import ExperimentConfig, run_scenario
    outcome = run_scenario(topology, load, seed, ExperimentConfig(**cfg_dict))
    scores = ", ".join(f"{name} {result['acceptance']:.3f}" for name, result in outcome.methods.items())
    print(f"done {topology} load={load} seed={seed}: {scores}", flush=True)
    return asdict(outcome)


def _stats(values: list[float]) -> dict[str, float]:
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return {"mean": mean, "std": std, "ci95": 1.96 * std / len(values) ** 0.5, "min": min(values), "max": max(values)}


def aggregate(outcomes: list[dict]) -> dict:
    groups: dict[tuple[str, float], list[dict]] = {}
    for outcome in outcomes:
        groups.setdefault((outcome["topology"], outcome["load"]), []).append(outcome)
    summary = {}
    for (topology, load), items in sorted(groups.items()):
        methods = {}
        for method in items[0]["methods"]:
            metrics = items[0]["methods"][method].keys()
            methods[method] = {metric: _stats([item["methods"][method][metric] for item in items]) for metric in metrics}
        summary[f"{topology}@{load}"] = {
            "topology": topology, "load": load, "seeds": [item["seed"] for item in items],
            "arrival_rate": statistics.mean(item["arrival_rate"] for item in items),
            "methods": methods,
            "training": {k: _stats([item["training"][k] for item in items]) for k in items[0]["training"]},
        }
        if all(item.get("training_original") for item in items):
            summary[f"{topology}@{load}"]["training_original"] = {
                k: _stats([item["training_original"][k] for item in items]) for k in items[0]["training_original"]}
    return summary


def _style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _bars(ax, scenarios, summary, metric, *, scale=1.0, methods=COMPARED):
    width = 0.8 / len(methods)
    for m, (method, color) in enumerate(zip(methods, COLORS)):
        means = [summary[s]["methods"][method][metric]["mean"] * scale for s in scenarios]
        errors = [summary[s]["methods"][method][metric]["std"] * scale for s in scenarios]
        xs = [i + (m - (len(methods) - 1) / 2) * width for i in range(len(scenarios))]
        ax.bar(xs, means, width * 0.92, color=color, label=LABELS[method], yerr=errors,
               error_kw={"ecolor": MUTED, "elinewidth": 0.8, "capsize": 2}, edgecolor="white", linewidth=1)


def _scenario_label(key: str, summary: dict) -> str:
    item = summary[key]
    return f"{item['topology'].title()}\nload {item['load']:g}"


def plot(summary: dict, main_loads: list[float], out: Path) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "text.color": INK, "axes.labelcolor": MUTED})
    paths = []
    scenarios = [k for k, v in summary.items() if v["load"] in main_loads]
    labels = [_scenario_label(k, summary) for k in scenarios]

    fig, ax = plt.subplots(figsize=(11, 4.6))
    _bars(ax, scenarios, summary, "acceptance", scale=100)
    ax.axhline(TARGET * 100, color=INK, linewidth=1, linestyle=(0, (4, 3)), label="70% target")
    ax.set_xticks(range(len(scenarios)), labels)
    ax.set_ylabel("Service acceptance (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Hold-out service acceptance by scenario (mean ± std over seeds)", loc="left", fontsize=11, color=INK)
    _style(ax)
    ax.legend(ncol=6, frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    fig.tight_layout(); path = out / "scenario-acceptance.png"; fig.savefig(path, dpi=150); plt.close(fig); paths.append(path)

    # Resources held per running SFC: one chart per resource (no dual axis).
    short = [f"{'BB' if summary[k]['topology'] == 'backbone' else 'Metro'} {summary[k]['load']:g}" for k in scenarios]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax, metric, title in (
        (axes[0], "compute_per_active_sfc", "Compute held per running SFC (units)"),
        (axes[1], "bandwidth_per_active_sfc", "Bandwidth held per running SFC (units)"),
    ):
        _bars(ax, scenarios, summary, metric)
        ax.set_xticks(range(len(scenarios)), short, fontsize=8.5)
        ax.set_title(title + ", lower is better", loc="left", fontsize=10.5, color=INK)
        _style(ax)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, ncol=5, frameon=False, fontsize=8.5, loc="lower center")
    fig.tight_layout(rect=(0, 0.07, 1, 1)); path = out / "scenario-resources.png"; fig.savefig(path, dpi=150); plt.close(fig); paths.append(path)

    # Load sweep: acceptance vs offered load per topology.
    topologies = sorted({v["topology"] for v in summary.values()})
    fig, axes = plt.subplots(1, len(topologies), figsize=(6 * len(topologies), 4.2), squeeze=False)
    for ax, topology in zip(axes[0], topologies):
        keys = sorted((k for k, v in summary.items() if v["topology"] == topology), key=lambda k: summary[k]["load"])
        loads = [summary[k]["load"] for k in keys]
        for method, color in zip(COMPARED, COLORS):
            values = [summary[k]["methods"][method]["acceptance"]["mean"] * 100 for k in keys]
            ax.plot(loads, values, color=color, linewidth=2, marker="o", markersize=5, label=LABELS[method])
            if method == "fppvs":
                ax.annotate(f"{values[-1]:.0f}%", (loads[-1], values[-1]), textcoords="offset points", xytext=(6, 0), color=INK, fontsize=8.5, va="center")
        ax.axhline(TARGET * 100, color=INK, linewidth=1, linestyle=(0, (4, 3)))
        # Shade where average offered compute exceeds total capacity (load > 1).
        if max(loads) > 1.0:
            ax.axvspan(1.0, max(loads) + 0.1, color=GRID, alpha=0.5, linewidth=0)
            ax.text(1.03, 8, "demand > capacity", color=MUTED, fontsize=8.5)
        # Mark the main scenarios on the x-axis.
        ax.axvspan(min(main_loads) - 0.03, max(main_loads) + 0.03, ymin=0, ymax=0.03, color=COLORS[0], alpha=0.6, linewidth=0)
        ax.set_xlabel("Offered load (offered compute demand ÷ total DC capacity)")
        ax.set_ylabel("Service acceptance (%)")
        ax.set_ylim(0, 105)
        ax.set_title(f"{topology.title()} topology", loc="left", fontsize=11, color=INK)
        _style(ax)
    axes[0][0].legend(frameon=False, fontsize=8.5, loc="lower left")
    fig.tight_layout(); path = out / "load-sweep.png"; fig.savefig(path, dpi=150); plt.close(fig); paths.append(path)
    return paths


def write_report(summary: dict, main_loads: list[float], cfg: dict, out: Path) -> Path:
    def pct(s): return f"{100 * s['mean']:.1f} ± {100 * s['std']:.1f}"
    def num(s, d=1): return f"{s['mean']:.{d}f}"
    lines = ["# FPPVS scenario results (synthetic)", "",
             "Hold-out acceptance, mean ± std over seeds. Load = offered compute demand ÷ total DC capacity.",
             f"Training: {cfg['agents']} federated agents × {cfg['rounds']} rounds × {cfg['local_episodes']} episodes; "
             f"{cfg['train_requests']} training / {cfg['test_requests']} hold-out requests per stream.", ""]
    methods = list(next(iter(summary.values()))["methods"])
    lines += ["## Acceptance (%)", "", "| Scenario | " + " | ".join(LABELS[m] for m in methods) + " |",
              "|---|" + "---|" * len(methods)]
    for key, item in summary.items():
        tag = "" if item["load"] in main_loads else (" (overload)" if item["load"] > 1 else " (light load)")
        lines.append(f"| {item['topology'].title()} load {item['load']:g}{tag} | " + " | ".join(pct(item["methods"][m]["acceptance"]) if m in item["methods"] else "—" for m in methods) + " |")
    lines += ["", "## Resources per running SFC and per accepted SFC (lower is better)", "",
              "| Scenario | Method | Compute/SFC | Bandwidth/SFC | Compute·time per accepted | Bandwidth·time per accepted | Instances per accepted | Latency | Decision ms |",
              "|---|---|---|---|---|---|---|---|---|"]
    for key, item in summary.items():
        if item["load"] not in main_loads:
            continue
        for m in COMPARED:
            s = item["methods"][m]
            lines.append(f"| {item['topology'].title()} {item['load']:g} | {LABELS[m]} | {num(s['compute_per_active_sfc'], 2)} | {num(s['bandwidth_per_active_sfc'])} | "
                         f"{num(s['compute_time_per_accepted'], 0)} | {num(s['bandwidth_time_per_accepted'], 0)} | {num(s['instances_per_accepted'], 2)} | {num(s['mean_latency'])} | {num(s['decision_ms_per_request'])} |")
    path = out / "scenario-report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--topologies", nargs="+", default=["backbone", "metro"])
    parser.add_argument("--loads", nargs="+", type=float, default=[0.9, 1.0, 1.1])
    parser.add_argument("--stress-loads", nargs="*", type=float, default=[0.5, 1.25, 1.5], help="extra load levels for the load sweep (fewer variants)")
    parser.add_argument("--seeds", nargs="+", type=int, default=[7, 8, 9])
    parser.add_argument("--requests", type=int, default=600, help="requests per training and per hold-out stream")
    parser.add_argument("--agents", type=int, default=4)
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--local-episodes", type=int, default=50)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", default="output/scenarios")
    parser.add_argument("--replot", action="store_true", help="redraw report and charts from an existing scenario-results.json")
    parser.add_argument("--merge-variants", nargs="+", default=None,
                        help="run only these variants (no baselines) and merge them into an existing scenario-results.json")
    args = parser.parse_args()
    if args.merge_variants:
        out = Path(args.output)
        payload = json.loads((out / "scenario-results.json").read_text(encoding="utf-8"))
        cfg = payload["config"] | {"variants": tuple(args.merge_variants), "baselines": ()}
        jobs = [(run["topology"], run["load"], run["seed"], cfg) for run in payload["per_run"]]
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            new_runs = list(pool.map(_job, jobs))
        for run, new in zip(payload["per_run"], new_runs):
            run["methods"].update(new["methods"])
            run["reasons"].update(new["reasons"])
            if new.get("training_original"):
                run["training_original"] = new["training_original"]
            if new.get("training_zhang2022"):
                run["training_zhang2022"] = new["training_zhang2022"]
        payload["summary"] = aggregate(payload["per_run"])
        (out / "scenario-results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        write_report(payload["summary"], payload["main_loads"], payload["config"], out)
        print("plots:", *map(str, plot(payload["summary"], payload["main_loads"], out)))
        return
    if args.replot:
        out = Path(args.output)
        payload = json.loads((out / "scenario-results.json").read_text(encoding="utf-8"))
        write_report(payload["summary"], payload["main_loads"], payload["config"], out)
        print("plots:", *map(str, plot(payload["summary"], payload["main_loads"], out)))
        return

    cfg = {"train_requests": args.requests, "test_requests": args.requests, "agents": args.agents,
           "rounds": args.rounds, "local_episodes": args.local_episodes, "device": "cpu"}
    stress_cfg = cfg | {"variants": ("fppvs", "prior-only", "original", "zhang2022")}
    jobs = [(t, load, seed, cfg) for t in args.topologies for load in args.loads for seed in args.seeds]
    jobs += [(t, load, seed, stress_cfg) for t in args.topologies for load in args.stress_loads for seed in args.seeds]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        outcomes = list(pool.map(_job, jobs))

    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    summary = aggregate(outcomes)
    (out / "scenario-results.json").write_text(json.dumps({"config": cfg, "main_loads": args.loads, "summary": summary, "per_run": outcomes}, indent=2), encoding="utf-8")
    report = write_report(summary, args.loads, cfg, out)
    plots = plot(summary, args.loads, out)
    print(report.read_text(encoding="utf-8"))
    print("plots:", *map(str, plots))


if __name__ == "__main__":
    main()
