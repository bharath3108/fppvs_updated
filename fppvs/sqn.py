"""SQN-LSTM demand forecasting used by FPPVS placement (Section 4.2)."""
from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from .models import SFCRequest
from .sharing import SFCQueueMemory, vnf_type
from .workloads import VNF_TYPES


@dataclass(frozen=True, slots=True)
class SQNPrediction:
    """Predicted normalized demand for each known VNF type."""

    values: dict[str, float]

    def for_vnf(self, type_name: str) -> float:
        return self.values.get(type_name, 0.0)


class SQNLSTMPredictor(nn.Module):
    """Bounded SQN memory plus a next-request LSTM forecaster.

    The queue holds one five-value resource-demand vector per accepted SFC.
    This is the trace-free equivalent of the paper's SQN input; exact traffic
    traces can later be supplied through the same ``observe`` interface.
    """

    def __init__(self, *, time_depth: int = 5, hidden: int = 64, device: str | torch.device = "cpu"):
        super().__init__()
        if time_depth < 1:
            raise ValueError("time_depth must be positive")
        self.time_depth = time_depth
        self.types = VNF_TYPES
        self.memory = SFCQueueMemory(list(self.types), time_depth)
        self.lstm = nn.LSTM(len(self.types), hidden, batch_first=True)
        self.head = nn.Linear(hidden, len(self.types))
        self.to(device)

    def encode(self, request: SFCRequest) -> torch.Tensor:
        totals = {name: 0.0 for name in self.types}
        for vnf in request.vnfs:
            totals[vnf_type(vnf)] = totals.get(vnf_type(vnf), 0.0) + vnf.compute_demand
        return torch.tensor([totals[name] for name in self.types], dtype=torch.float32)

    def observe(self, request: SFCRequest) -> None:
        self.memory.observe(request.vnfs)

    def prediction(self) -> SQNPrediction:
        sequence = self.memory.tensor().to(next(self.parameters()).device)
        if not self.memory.layers:
            return SQNPrediction({name: 0.0 for name in self.types})
        with torch.no_grad():
            output, _ = self.lstm(sequence)
            values = torch.relu(self.head(output[:, -1])).squeeze(0).cpu().tolist()
        return SQNPrediction(dict(zip(self.types, values, strict=True)))

    def update(self, request: SFCRequest, *, learning_rate: float = 1e-3) -> float | None:
        """Fit the next request from current SQN memory, then append it."""
        target = self.encode(request).to(next(self.parameters()).device)
        sequence = self.memory.tensor().to(target.device)
        loss_value: float | None = None
        if self.memory.layers:
            optimizer = torch.optim.Adam(self.parameters(), lr=learning_rate)
            prediction, _ = self.lstm(sequence)
            loss = nn.functional.mse_loss(self.head(prediction[:, -1]).squeeze(0), target)
            optimizer.zero_grad(); loss.backward(); optimizer.step()
            loss_value = float(loss.detach().cpu())
        self.memory.observe(request.vnfs)
        return loss_value
