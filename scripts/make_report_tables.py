"""Turn output/scenarios/*.json into LaTeX tables for report/report.tex."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "output" / "scenarios"
OUT = ROOT / "report" / "tables"

COMPARED = [("fppvs", "Updated (ours)"), ("original", "Original FPPVS"), ("zhang2022", "2022 adaptation"), ("greedy", "Greedy"), ("random", "Random")]
ABLATIONS = [("fppvs", "Full"), ("no-sharing", "w/o sharing"), ("no-fairness", "w/o fairness"), ("single-agent", "1 agent"), ("no-retry", "w/o retry"), ("prior-only", "Prior only")]


def pct(stat):
    return f"{100 * stat['mean']:.1f} $\\pm$ {100 * stat['std']:.1f}"


def scenario_name(item):
    return f"{item['topology'].title()} {item['load']:g}"


def best_row(item, methods, metric, lower=False):
    values = {m: item["methods"][m][metric]["mean"] for m, _ in methods if m in item["methods"]}
    return (min if lower else max)(values, key=values.get)


def acceptance_table(summary, main_loads):
    lines = [r"\begin{tabular}{l" + "c" * len(COMPARED) + "}", r"\toprule",
             "Scenario (topology, load) & " + " & ".join(label for _, label in COMPARED) + r" \\", r"\midrule"]
    stress_started = False
    # Main scenarios first, then overload stress tests.
    ordered = sorted(summary.values(), key=lambda item: (item["load"] not in main_loads, item["topology"], item["load"]))
    for item in ordered:
        if item["load"] not in main_loads and not stress_started:
            lines.append(r"\midrule \multicolumn{" + str(len(COMPARED) + 1) + r"}{l}{\emph{Other load levels (light load and overload)}} \\")
            stress_started = True
        best = best_row(item, COMPARED, "acceptance")
        cells = [(r"\textbf{" + pct(item["methods"][m]["acceptance"]) + "}") if m == best else pct(item["methods"][m]["acceptance"]) for m, _ in COMPARED]
        lines.append(scenario_name(item) + " & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def ablation_table(summary, main_loads):
    lines = [r"\begin{tabular}{l" + "c" * len(ABLATIONS) + "}", r"\toprule",
             "Scenario & " + " & ".join(label for _, label in ABLATIONS) + r" \\", r"\midrule"]
    for item in summary.values():
        if item["load"] not in main_loads:
            continue
        lines.append(scenario_name(item) + " & " + " & ".join(pct(item["methods"][m]["acceptance"]) for m, _ in ABLATIONS) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def resource_table(summary, main_loads):
    metrics = [
        ("compute_per_active_sfc", "{:.2f}", 1, True),
        ("bandwidth_per_active_sfc", "{:.1f}", 1, True),
        ("compute_time_per_accepted", "{:.2f}", 1e-3, True),
        ("bandwidth_time_per_accepted", "{:.1f}", 1e-3, True),
        ("instances_per_accepted", "{:.2f}", 1, True),
        ("mean_latency", "{:.1f}", 1, True),
    ]
    lines = [r"\begin{tabular}{llcccccc}", r"\toprule",
             r"Scenario & Method & Compute & Bandwidth & Compute$\cdot$time & BW$\cdot$time & Instances & Latency \\",
             r" & & per SFC & per SFC & per acc. ($10^3$) & per acc. ($10^3$) & per acc. & (ms) \\", r"\midrule"]
    first = True
    for item in summary.values():
        if item["load"] not in main_loads:
            continue
        if not first:
            lines.append(r"\midrule")
        first = False
        bests = {metric: best_row(item, COMPARED, metric, lower=lower) for metric, _, _, lower in metrics}
        for index, (method, label) in enumerate(COMPARED):
            cells = []
            for metric, fmt, scale, _ in metrics:
                text = fmt.format(item["methods"][method][metric]["mean"] * scale)
                cells.append(r"\textbf{" + text + "}" if bests[metric] == method else text)
            name = scenario_name(item) if index == 0 else ""
            lines.append(f"{name} & {label} & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def savings_table(summary, main_loads):
    """Percentage reduction in resources held per running SFC vs each baseline."""
    lines = [r"\begin{tabular}{lcccc}", r"\toprule",
             r"Reduction vs. & Compute & Bandwidth & BW$\cdot$time & Instances \\",
             r" & per SFC & per SFC & per accepted & per accepted \\", r"\midrule"]
    for method, label in COMPARED[1:]:
        cells = []
        for metric in ("compute_per_active_sfc", "bandwidth_per_active_sfc", "bandwidth_time_per_accepted", "instances_per_accepted"):
            reductions = []
            for item in summary.values():
                if item["load"] in main_loads:
                    ours = item["methods"]["fppvs"][metric]["mean"]
                    theirs = item["methods"][method][metric]["mean"]
                    reductions.append(100 * (theirs - ours) / theirs)
            cells.append(f"{sum(reductions) / len(reductions):+.1f}\\%")
        lines.append(label + " & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def old_workload_table(old):
    names = [("prior-only (FPPVS placement, no DRL)", "Updated FPPVS placement"), ("greedy", "Greedy"), ("random", "Random")]
    lines = [r"\begin{tabular}{lc}", r"\toprule", r"Method (original workload, 100 requests) & Acceptance (\%) \\", r"\midrule",
             r"Original implementation, trained FDRL (5 seeds) & 10.4 $\pm$ 5.1 \\",
             r"Original implementation, greedy & 15.8 $\pm$ 3.1 \\",
             r"Original implementation, random & 11.6 $\pm$ 3.0 \\", r"\midrule"]
    for key, label in names:
        lines.append(f"{label} & {pct(old[key])}" + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


# Published results of the paper (Tables 6 and 7 of Zhu et al.), for reference.
PAPER = {
    "backbone": {"FPPVS": (88.1, 134.4, 75.35)},
    "metro": {"FPPVS": (75.9, 160.1, 72.36)},
}


def original_table(summary, main_loads):
    """Original FPPVS, 2022 adaptation and updated FPPVS on identical streams."""
    lines = [r"\begin{tabular}{lccccccc}", r"\toprule",
             r" & \multicolumn{4}{c}{Acceptance (\%)} & \multicolumn{3}{c}{Bandwidth per running SFC} \\",
             r"\cmidrule(lr){2-5}\cmidrule(lr){6-8}",
             r"Scenario & Original & 2022 & Updated & Gain$^\ast$ & Original & 2022 & Updated \\", r"\midrule"]
    ordered = sorted(summary.values(), key=lambda item: (item["load"] not in main_loads, item["topology"], item["load"]))
    stress_started = False
    for item in ordered:
        if item["load"] not in main_loads and not stress_started:
            lines.append(r"\midrule \multicolumn{8}{l}{\emph{Other load levels}} \\")
            stress_started = True
        o, z, u = (item["methods"][m] for m in ("original", "zhang2022", "fppvs"))
        gain = 100 * (u["acceptance"]["mean"] - max(o["acceptance"]["mean"], z["acceptance"]["mean"]))
        cells = [
            f"{100 * o['acceptance']['mean']:.1f}",
            f"{100 * z['acceptance']['mean']:.1f}",
            r"\textbf{" + f"{100 * u['acceptance']['mean']:.1f}" + "}",
            f"{gain:+.1f}",
            f"{o['bandwidth_per_active_sfc']['mean']:.1f}",
            f"{z['bandwidth_per_active_sfc']['mean']:.1f}",
            r"\textbf{" + f"{u['bandwidth_per_active_sfc']['mean']:.1f}" + "}",
        ]
        lines.append(scenario_name(item) + " & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def paper_table(summary):
    """Paper's published FPPVS numbers next to our three runs at full load (rho = 1)."""
    lines = [r"\begin{tabular}{llcccc}", r"\toprule",
             r" & & Published & \multicolumn{3}{c}{Our runs, load 1.0} \\",
             r"\cmidrule(lr){4-6}",
             r"Topology & Metric & FPPVS (paper) & Original & 2022 & Updated \\", r"\midrule"]
    for topology in ("backbone", "metro"):
        item = summary.get(f"{topology}@1.0")
        if item is None:
            continue
        runs = [item["methods"][m] for m in ("original", "zhang2022", "fppvs")]
        paper = PAPER[topology]["FPPVS"]
        rows = [
            (r"Acceptance (\%)", paper[0], [f"{100 * r['acceptance']['mean']:.1f}" for r in runs]),
            ("Latency (ms)", paper[1], [f"{r['mean_latency']['mean']:.1f}" for r in runs]),
            (r"Resource utilization (\%)", paper[2], [f"{100 * r['compute_utilization']['mean']:.1f}" for r in runs]),
        ]
        for index, (metric, published, ours) in enumerate(rows):
            name = topology.title() if index == 0 else ""
            lines.append(f"{name} & {metric} & {published:g} & " + " & ".join(ours) + r" \\")
        if topology == "backbone":
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def macros(summary, main_loads, payload):
    main = [item for item in summary.values() if item["load"] in main_loads]
    fppvs = [item["methods"]["fppvs"]["acceptance"]["mean"] for item in main]
    worst = min(main, key=lambda item: item["methods"]["fppvs"]["acceptance"]["mean"])
    lowest_run = min(run["methods"]["fppvs"]["acceptance"] for run in payload["per_run"] if run["load"] in main_loads)
    train = [item["training"]["training_seconds"]["mean"] for item in main]
    defs = {
        "fppvsMinAcc": f"{100 * min(fppvs):.1f}",
        "fppvsMaxAcc": f"{100 * max(fppvs):.1f}",
        "fppvsMeanAcc": f"{100 * sum(fppvs) / len(fppvs):.1f}",
        "fppvsWorstScenario": scenario_name(worst),
        "fppvsLowestRun": f"{100 * lowest_run:.1f}",
        "trainSeconds": f"{sum(train) / len(train):.0f}",
        "numSeeds": str(len(next(iter(summary.values()))["seeds"])),
    }
    if all("original" in item["methods"] for item in main):
        original = [item["methods"]["original"]["acceptance"]["mean"] for item in main]
        gains = [100 * (a - b) for a, b in zip(fppvs, original)]
        defs |= {
            "origMinAcc": f"{100 * min(original):.1f}",
            "origMaxAcc": f"{100 * max(original):.1f}",
            "origMeanAcc": f"{100 * sum(original) / len(original):.1f}",
            "origGainMin": f"{min(gains):.1f}",
            "origGainMax": f"{max(gains):.1f}",
            "origGainMean": f"{sum(gains) / len(gains):.1f}",
        }
    if all("zhang2022" in item["methods"] for item in main):
        zhang = [item["methods"]["zhang2022"]["acceptance"]["mean"] for item in main]
        zgains = [100 * (a - b) for a, b in zip(fppvs, zhang)]
        defs |= {
            "zhangMinAcc": f"{100 * min(zhang):.1f}",
            "zhangMaxAcc": f"{100 * max(zhang):.1f}",
            "zhangMeanAcc": f"{100 * sum(zhang) / len(zhang):.1f}",
            "zhangGainMean": f"{sum(zgains) / len(zgains):.1f}",
        }
    return "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in defs.items())


def main() -> None:
    payload = json.loads((SRC / "scenario-results.json").read_text(encoding="utf-8"))
    summary, main_loads = payload["summary"], payload["main_loads"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "acceptance.tex").write_text(acceptance_table(summary, main_loads), encoding="utf-8")
    (OUT / "ablation.tex").write_text(ablation_table(summary, main_loads), encoding="utf-8")
    (OUT / "resources.tex").write_text(resource_table(summary, main_loads), encoding="utf-8")
    (OUT / "savings.tex").write_text(savings_table(summary, main_loads), encoding="utf-8")
    (OUT / "macros.tex").write_text(macros(summary, main_loads, payload), encoding="utf-8")
    if all("original" in item["methods"] and "zhang2022" in item["methods"] for item in summary.values()):
        (OUT / "original.tex").write_text(original_table(summary, main_loads), encoding="utf-8")
        (OUT / "paper.tex").write_text(paper_table(summary), encoding="utf-8")
    old = SRC / "old-workload.json"
    if old.exists():
        (OUT / "old-workload.tex").write_text(old_workload_table(json.loads(old.read_text(encoding="utf-8"))), encoding="utf-8")
    # Copy result charts next to the report so it compiles on its own (e.g. Overleaf).
    figures = ROOT / "report" / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    for name in ("scenario-acceptance.png", "scenario-resources.png", "load-sweep.png"):
        if (SRC / name).exists():
            (figures / name).write_bytes((SRC / name).read_bytes())
    print("tables written to", OUT)


if __name__ == "__main__":
    main()
