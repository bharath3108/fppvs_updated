"""VNF type helper and the bounded SQN queue used by the SQN-LSTM forecaster."""
from collections import deque
from typing import Iterable
from .models import VNF

def vnf_type(vnf: VNF) -> str:
    return vnf.id.split("-", 1)[0]


class SFCQueueMemory:
    """Bounded SQN queue: one per-type compute-demand vector per observed SFC."""

    def __init__(self, types: list[str], time_depth: int):
        self.types = list(types)
        self.index = {name: i for i, name in enumerate(self.types)}
        self.layers: deque[list[float]] = deque(maxlen=time_depth)

    def observe(self, vnfs: Iterable[VNF]) -> None:
        row = [0.0] * len(self.types)
        for vnf in vnfs:
            position = self.index.get(vnf_type(vnf))
            if position is not None:
                row[position] += vnf.compute_demand
        self.layers.append(row)

    def tensor(self):
        """Return shape (1, depth, types); a single zero row when empty."""
        import torch
        rows = list(self.layers) or [[0.0] * len(self.types)]
        return torch.tensor(rows, dtype=torch.float32).unsqueeze(0)
