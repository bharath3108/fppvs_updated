"""Draw the explanatory figures used in report/report.tex."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from fppvs import SFCRequest, VNF, VNFKind, parallelize_sfc

OUT = Path(__file__).resolve().parents[1] / "report" / "figures"
INK, MUTED, LINE = "#1f1f1f", "#52514e", "#9a9893"
BLUE, ORANGE, AQUA, GREY = "#dbe8f8", "#fbe1d6", "#d4f1e6", "#efeeea"
BLUE_EDGE, ORANGE_EDGE, AQUA_EDGE = "#2a78d6", "#eb6834", "#1baf7a"


def box(ax, x, y, w, h, text, face=GREY, edge=LINE, size=9, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", facecolor=face, edgecolor=edge, linewidth=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=INK, fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, start, end, text=None, style="-|>", color=MUTED, rad=0.0, offset=(0, 0.12)):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=12, color=color, linewidth=1.2, connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((start[0] + end[0]) / 2 + offset[0], (start[1] + end[1]) / 2 + offset[1], text, ha="center", va="bottom", fontsize=7.5, color=MUTED)


def architecture():
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.set_xlim(0, 11); ax.set_ylim(0, 6.2); ax.axis("off")
    # Cloud aggregator
    box(ax, 4.0, 5.25, 3.0, 0.7, "Cloud server\nFedAvg (experience-weighted)", BLUE, BLUE_EDGE, bold=True)
    # Local agents
    for i, x in enumerate((0.3, 3.0, 5.7, 8.4)):
        label = f"Local agent {i + 1}" if i < 3 else "Local agent 4"
        box(ax, x, 4.0, 2.3, 0.65, f"{label}\nCNN actor-critic", BLUE, BLUE_EDGE, size=8.5)
        arrow(ax, (x + 1.15, 4.65), (5.5 + (x - 4.35) * 0.25, 5.25), color=BLUE_EDGE)
    ax.text(5.5, 4.85, "model weights only", ha="center", fontsize=7.5, color=MUTED)
    # Pipeline for one request
    y = 2.35
    steps = [
        (0.2, "SFC request\n(source, VNFs, dest,\nrate, max latency, TTL)", GREY, LINE),
        (2.25, "Algorithm 1\ns-SFC → p-SFC\n(DAG)", ORANGE, ORANGE_EDGE),
        (4.3, "State builder\n9 features × DCs\n(+ SQN-LSTM forecast)", ORANGE, ORANGE_EDGE),
        (6.35, "Feasibility mask\ncompute · bandwidth\n· latency look-ahead", AQUA, AQUA_EDGE),
        (8.4, "Policy picks DC\n(+ placement prior)\nshare or start instance", AQUA, AQUA_EDGE),
    ]
    for x, text, face, edge in steps:
        box(ax, x, y, 1.85, 1.05, text, face, edge, size=8)
    for (x1, *_), (x2, *_) in zip(steps, steps[1:]):
        arrow(ax, (x1 + 1.85, y + 0.52), (x2, y + 0.52))
    arrow(ax, (9.3, 4.0), (9.3, y + 1.05), color=BLUE_EDGE)
    ax.text(9.4, 3.62, "policy", fontsize=7.5, color=MUTED)
    # Admission and ledger
    by = 0.6
    box(ax, 8.4, by, 1.85, 1.05, "Admission check\nall VNFs placed?\nfits ledger?", AQUA, AQUA_EDGE, size=8)
    box(ax, 6.35, by, 1.85, 1.05, "Resource ledger\ncompute, links,\nshared instances,\nTTL release", GREY, LINE, size=8)
    box(ax, 3.3, by, 2.5, 1.05, "Accept → commit, reward\n+ fairness bonus\nReject → retry other\nfirst DC, else −10", GREY, LINE, size=8)
    arrow(ax, (9.32, y), (9.32, by + 1.05))
    ax.text(9.42, 1.95, "last VNF", fontsize=7.5, color=MUTED)
    arrow(ax, (8.4, by + 0.52), (8.2, by + 0.52), style="<|-|>")
    arrow(ax, (7.27, by + 1.05), (7.27, y))
    ax.text(7.37, 1.95, "residual capacity", fontsize=7.5, color=MUTED)
    arrow(ax, (9.32, by), (4.55, by), rad=-0.18)
    ax.text(6.9, 0.05, "decision", fontsize=7.5, color=MUTED, ha="center")
    ax.text(0.2, 1.65, "Blue: original FPPVS idea kept\nOrange: original idea, re-implemented\nGreen: modified / added by our team",
            fontsize=8, color=MUTED, va="top")
    fig.tight_layout(); fig.savefig(OUT / "architecture.png", dpi=200); plt.close(fig)


def psfc_example():
    s, m = VNFKind.SHAPER, VNFKind.MONITOR
    vnfs = [VNF("FW", s), VNF("IDS", m), VNF("DPI", m), VNF("NAT", s), VNF("LB", s)]
    matrix = [[0] * 5 for _ in range(5)]
    matrix[3][1] = 1  # NAT waits for IDS
    request = SFCRequest("Src", vnfs, "Dst", matrix)
    result = parallelize_sfc(request)
    fig, axes = plt.subplots(2, 1, figsize=(9, 3.6))
    order = ["Src", "FW", "IDS", "DPI", "NAT", "LB", "Dst"]
    kinds = {v.id: v.kind for v in vnfs}
    for ax in axes:
        ax.set_xlim(-0.5, 6.5); ax.set_ylim(-1.3, 1.0); ax.axis("off")

    def node(ax, name, x, y):
        face, edge = (GREY, LINE) if name in ("Src", "Dst") else ((AQUA, AQUA_EDGE) if kinds[name] is m else (ORANGE, ORANGE_EDGE))
        ax.add_patch(FancyBboxPatch((x - 0.36, y - 0.22), 0.72, 0.44, boxstyle="round,pad=0.02,rounding_size=0.1", facecolor=face, edgecolor=edge))
        ax.text(x, y, name, ha="center", va="center", fontsize=9, color=INK)

    ax = axes[0]
    ax.set_title("(a) Sequential SFC as requested", loc="left", fontsize=9.5, color=INK)
    for i, name in enumerate(order):
        node(ax, name, i, 0)
        if i:
            arrow(ax, (i - 1 + 0.36, 0), (i - 0.36, 0))
    ax = axes[1]
    ax.set_title("(b) Parallel SFC from Algorithm 1 (main chain + monitor branches)", loc="left", fontsize=9.5, color=INK)
    pos = {"Src": (0, 0), "FW": (1.3, 0), "NAT": (3.2, 0), "LB": (4.6, 0), "Dst": (6, 0), "IDS": (2.25, -0.85), "DPI": (3.9, -0.85)}
    for name, (x, y) in pos.items():
        node(ax, name, x, y)
    for u, v in result.graph.edges:
        (x1, y1), (x2, y2) = pos[u], pos[v]
        dx = 0.36 if x2 > x1 else -0.36
        if y1 == y2:
            arrow(ax, (x1 + dx, y1), (x2 - dx, y2))
        else:
            arrow(ax, (x1 + 0.2, y1 - 0.22 if y1 > y2 else y1 + 0.22), (x2 - 0.2, y2 + 0.22 if y1 > y2 else y2 - 0.22), color=AQUA_EDGE)
    ax.text(6.4, -0.85, "orange = shaper\ngreen = monitor", fontsize=8, color=MUTED, ha="right", va="center")
    fig.tight_layout(); fig.savefig(OUT / "psfc-example.png", dpi=200); plt.close(fig)


def placement_flow():
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 3.4); ax.axis("off")
    items = [
        (0.1, "Next VNF in\ntopological order"),
        (2.1, "Route every edge it\ncompletes (incl. to\negress) per candidate DC"),
        (4.1, "Mask DC if compute,\nlink bandwidth or\nlatency bound fails"),
        (6.1, "Score = CNN logit\n+ w · prior"),
        (8.1, "Pick best DC;\nreuse live instance\nif one exists"),
    ]
    for x, text in items:
        box(ax, x, 1.9, 1.8, 1.1, text, AQUA if "Mask" in text or "prior" in text else GREY, AQUA_EDGE if "Mask" in text or "prior" in text else LINE, size=8)
    for (x1, _), (x2, _) in zip(items, items[1:]):
        arrow(ax, (x1 + 1.8, 2.45), (x2, 2.45))
    box(ax, 2.1, 0.2, 2.6, 0.9, "No DC feasible → roll back\n(nothing committed yet)", ORANGE, ORANGE_EDGE, size=8)
    box(ax, 5.3, 0.2, 2.6, 0.9, "Retry from up to 4 other\nfirst DCs, else reject", ORANGE, ORANGE_EDGE, size=8)
    arrow(ax, (5.0, 1.9), (3.4, 1.1))
    arrow(ax, (4.7, 0.65), (5.3, 0.65))
    arrow(ax, (9.0, 1.9), (9.0, 1.1))
    ax.text(9.0, 0.75, "last VNF → admission\ncheck and commit", ha="center", fontsize=8, color=MUTED)
    fig.tight_layout(); fig.savefig(OUT / "placement-flow.png", dpi=200); plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    architecture(); psfc_example(); placement_flow()
    print("figures written to", OUT)
