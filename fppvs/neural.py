"""Actor-critic networks for updated FPPVS, original FPPVS and the 2022 adaptation, plus FedAvg."""
import torch
from torch import nn


class CNNActorCritic(nn.Module):
    """Three 64-filter CNN layers with batch norm; 256-unit FC + dropout 0.3 critic.

    Input is a ``(batch, 1, features, DCs)`` grid with one column per DC.
    Convolutions run along the feature axis only (kernel 3x1), because
    neighbouring columns are unrelated DCs. The actor scores every column
    with the same weights, so the policy is DC-permutation-equivariant and
    works for any number of DCs. If ``prior_row`` is set, that state row
    (a placement-heuristic score) is added to the logits with a learnable
    weight, i.e. the network learns a residual on top of a sensible prior.
    """

    def __init__(self, actions: int | None = None, *, prior_row: int | None = None, prior_weight: float = 2.0):
        super().__init__()
        layers = []; channels = 1
        for _ in range(3):
            layers += [nn.Conv2d(channels, 64, (3, 1), padding=(1, 0)), nn.BatchNorm2d(64), nn.ReLU()]
            channels = 64
        self.encoder = nn.Sequential(*layers)
        self.actor = nn.Sequential(nn.Conv2d(64, 64, 1), nn.ReLU(), nn.Conv2d(64, 1, 1))
        self.critic = nn.Sequential(nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(64, 256), nn.ReLU(), nn.Dropout(.3), nn.Linear(256, 1))
        self.prior_row = prior_row
        self.prior_weight = nn.Parameter(torch.tensor(float(prior_weight)))

    def forward(self, state):
        features = self.encoder(state)
        logits = self.actor(features).mean(dim=2).flatten(1)
        if self.prior_row is not None and state.shape[2] > self.prior_row:
            logits = logits + self.prior_weight * state[:, 0, self.prior_row, :]
        return logits, self.critic(features)


class OriginalCNNActorCritic(nn.Module):
    """Original FPPVS network following the paper's description closely.

    Three 3x3 conv layers with 64 filters, batch norm and ReLU, then the
    feature map as a fixed-length vector into a 256-unit FC layer with
    dropout 0.3, then one actor output per DC and one critic output.
    There is no global pooling, so each DC keeps its own position in the input.
    """

    def __init__(self, features: int, actions: int):
        super().__init__(); layers = []; channels = 1
        for _ in range(3):
            layers += [nn.Conv2d(channels, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU()]; channels = 64
        self.encoder = nn.Sequential(*layers, nn.Flatten(), nn.Linear(64 * features * actions, 256), nn.ReLU(), nn.Dropout(.3))
        self.actor, self.critic = nn.Linear(256, actions), nn.Linear(256, 1)

    def forward(self, state):
        x = self.encoder(state); return self.actor(x), self.critic(x)


class MLPActorCritic(nn.Module):
    """Fully connected actor-critic used for our Zhang et al. (2022) adaptation.

    The state grid is flattened, so each DC keeps a fixed input position.
    """

    def __init__(self, features: int, actions: int, hidden: int = 128):
        super().__init__()
        self.body = nn.Sequential(nn.Flatten(), nn.Linear(features * actions, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU())
        self.actor, self.critic = nn.Linear(hidden, actions), nn.Linear(hidden, 1)

    def forward(self, state):
        x = self.body(state); return self.actor(x), self.critic(x)


def fedavg(models: list[nn.Module], weights: list[float] | None = None) -> None:
    """Federated-average local model parameters and broadcast the result."""
    if not models: return
    weights = weights or [1.0] * len(models)
    total = sum(weights)
    state = models[0].state_dict()
    averaged = {}
    for key, value in state.items():
        stacked = torch.stack([m.state_dict()[key].float() * (w / total) for m, w in zip(models, weights)]).sum(0)
        averaged[key] = stacked.to(value.dtype)
    for model in models: model.load_state_dict(averaged)
