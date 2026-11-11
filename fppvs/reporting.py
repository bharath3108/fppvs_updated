"""Repeated synthetic runs and plot generation."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .training import TrainingHistory


def moving_average(values: Iterable[float], window: int = 25) -> list[float]:
    values = list(values)
    return [sum(values[max(0, i - window + 1): i + 1]) / min(i + 1, window) for i in range(len(values))]


def save_learning_plot(history: TrainingHistory, destination: str | Path) -> Path:
    """Save a reward-learning plot for a synthetic run."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    destination = Path(destination); destination.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 4)); plt.plot(moving_average(history.episode_rewards), label="FDRL reward (moving average)")
    plt.xlabel("Episode"); plt.ylabel("Reward"); plt.title("Synthetic FPPVS training"); plt.legend(); plt.tight_layout(); plt.savefig(destination, dpi=150); plt.close()
    return destination
