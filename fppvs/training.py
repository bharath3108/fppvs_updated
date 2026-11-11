"""Actor-critic and federated training utilities for FPPVS (Section 4.3)."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from random import Random

import torch
from torch.distributions import Categorical

from .environment import PlacementEnvironment
from .neural import CNNActorCritic, fedavg


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    episodes: int = 100
    learning_rate: float = 5e-4
    gamma: float = 0.99
    temperature: float = 1.0
    epsilon_start: float = 0.25
    epsilon_min: float = 0.02
    epsilon_decay: float = 0.995
    logit_noise: float = 0.10
    entropy: float = 0.01
    device: str = "auto"


@dataclass(frozen=True, slots=True)
class TrainingHistory:
    episode_rewards: tuple[float, ...]
    accepted: tuple[bool, ...]
    epsilons: tuple[float, ...]
    device: str


@dataclass(frozen=True, slots=True)
class FederatedTrainingHistory:
    round_rewards: tuple[float, ...]
    round_acceptance: tuple[float, ...]
    local_histories: tuple[TrainingHistory, ...]
    device: str

    @property
    def episode_rewards(self) -> tuple[float, ...]:
        """All local episode rewards, not one thresholded value per round."""
        return tuple(reward for history in self.local_histories for reward in history.episode_rewards)

    @property
    def accepted(self) -> tuple[bool, ...]:
        """Acceptance of every local episode across all FedAvg rounds."""
        return tuple(value for history in self.local_histories for value in history.accepted)

    @property
    def acceptance_rate(self) -> float:
        return sum(self.accepted) / len(self.accepted) if self.accepted else 0.0


def resolve_device(requested: str = "auto") -> torch.device:
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(requested)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable. Install a CUDA-enabled PyTorch build or use --device cpu.")
    return device


def train(
    model: CNNActorCritic,
    environments: list[PlacementEnvironment],
    *,
    episodes: int = 100,
    learning_rate: float = 5e-4,
    seed: int = 7,
    config: TrainingConfig | None = None,
    checkpoint: str | Path | None = None,
    start_episode: int = 0,
) -> TrainingHistory:
    """Train one local FPPVS actor-critic agent with masked actions.

    ``start_episode`` lets repeated calls (federated rounds) continue through
    the request stream instead of replaying its first requests.
    """
    if not environments:
        raise ValueError("at least one placement environment is required")
    config = config or TrainingConfig(episodes=episodes, learning_rate=learning_rate)
    if config.episodes < 1:
        raise ValueError("episodes must be positive")
    device = resolve_device(config.device)
    torch.manual_seed(seed)
    rng = Random(seed)
    model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    rewards: list[float] = []
    accepted: list[bool] = []
    epsilons: list[float] = []
    epsilon = config.epsilon_start

    for episode in range(start_episode, start_episode + config.episodes):
        environment = environments[episode % len(environments)]
        state = environment.reset().to(device)
        log_probs: list[torch.Tensor] = []
        entropies: list[torch.Tensor] = []
        values: list[torch.Tensor] = []
        step_rewards: list[float] = []
        final = None
        model.train()
        if not environment.has_action():
            final = environment.reject("no feasible data center")
            rewards.append(final.reward); accepted.append(False); epsilons.append(epsilon)
            continue
        while not environment.done:
            logits, value = model(state)
            mask = environment.action_mask().to(device)
            masked_logits = logits.squeeze(0).masked_fill(~mask, float("-inf"))
            if config.logit_noise:
                masked_logits = masked_logits + torch.randn_like(masked_logits) * config.logit_noise
                masked_logits = masked_logits.masked_fill(~mask, float("-inf"))
            distribution = Categorical(logits=masked_logits / config.temperature)
            valid_actions = torch.nonzero(mask, as_tuple=False).squeeze(1).tolist()
            action = rng.choice(valid_actions) if rng.random() < epsilon else int(distribution.sample().item())
            log_probs.append(distribution.log_prob(torch.tensor(action, device=device)))
            entropies.append(distribution.entropy())
            values.append(value.squeeze())
            final = environment.step(action)
            step_rewards.append(final.reward)
            state = final.state.to(device)

        returns: list[float] = []
        running_return = 0.0
        for reward in reversed(step_rewards):
            running_return = reward + config.gamma * running_return
            returns.append(running_return)
        returns_tensor = torch.tensor(list(reversed(returns)), dtype=torch.float32, device=device)
        value_tensor = torch.stack(values)
        advantage = returns_tensor - value_tensor.detach()
        actor_loss = -(torch.stack(log_probs) * advantage).mean()
        critic_loss = torch.nn.functional.mse_loss(value_tensor, returns_tensor)
        entropy_bonus = torch.stack(entropies).nan_to_num(0.0).mean()
        optimizer.zero_grad()
        (actor_loss + 0.5 * critic_loss - config.entropy * entropy_bonus).backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        total_reward = float(sum(step_rewards))
        rewards.append(total_reward)
        was_accepted = bool(final and final.info.get("accepted"))
        accepted.append(was_accepted)
        epsilon = max(config.epsilon_min, epsilon * config.epsilon_decay) if was_accepted else min(config.epsilon_start, epsilon / config.epsilon_decay)
        epsilons.append(epsilon)

    history = TrainingHistory(tuple(rewards), tuple(accepted), tuple(epsilons), str(device))
    if checkpoint is not None:
        save_checkpoint(checkpoint, model, config, history)
    return history


def train_federated(
    global_model: CNNActorCritic,
    agent_environments: list[list[PlacementEnvironment]],
    *,
    rounds: int,
    local_episodes: int,
    seed: int = 7,
    config: TrainingConfig | None = None,
    checkpoint: str | Path | None = None,
) -> FederatedTrainingHistory:
    """Run local actor-critic training followed by FedAvg in each round."""
    if rounds < 1 or local_episodes < 1 or not agent_environments or any(not group for group in agent_environments):
        raise ValueError("rounds, local_episodes, and every agent environment group must be non-empty")
    config = config or TrainingConfig(episodes=local_episodes)
    local_models = [deepcopy(global_model) for _ in agent_environments]
    round_rewards: list[float] = []
    round_acceptance: list[float] = []
    histories: list[TrainingHistory] = []
    for round_index in range(rounds):
        round_histories = []
        for agent_index, (model, environments) in enumerate(zip(local_models, agent_environments, strict=True)):
            local_config = TrainingConfig(**(asdict(config) | {"episodes": local_episodes}))
            history = train(model, environments, seed=seed + round_index * len(local_models) + agent_index, config=local_config, start_episode=round_index * local_episodes)
            round_histories.append(history)
            histories.append(history)
        # Weight each agent by how much experience it gathered this round.
        fedavg(local_models, [len(history.accepted) for history in round_histories])
        global_model.load_state_dict(local_models[0].state_dict())
        round_rewards.append(sum(sum(history.episode_rewards) / len(history.episode_rewards) for history in round_histories) / len(round_histories))
        round_acceptance.append(sum(sum(history.accepted) / len(history.accepted) for history in round_histories) / len(round_histories))
    result = FederatedTrainingHistory(tuple(round_rewards), tuple(round_acceptance), tuple(histories), histories[-1].device)
    if checkpoint is not None:
        save_checkpoint(checkpoint, global_model, config, result)
    return result


def evaluate_policy(model: CNNActorCritic, environments: list[PlacementEnvironment], *, device: str = "auto") -> TrainingHistory:
    """Evaluate a trained policy deterministically on fresh environments.

    Unlike ``train``, this never injects epsilon exploration or logit noise.
    It is therefore suitable for comparison with deterministic baselines.
    """
    if not environments:
        raise ValueError("at least one placement environment is required")
    resolved = resolve_device(device)
    model.to(resolved)
    model.eval()
    rewards: list[float] = []
    accepted: list[bool] = []
    with torch.no_grad():
        for environment in environments:
            state = environment.reset().to(resolved)
            total_reward = 0.0
            final = None
            if not environment.has_action():
                final = environment.reject("no feasible data center")
                total_reward = final.reward
            while not environment.done:
                logits, _ = model(state)
                mask = environment.action_mask().to(resolved)
                action = int(logits.squeeze(0).masked_fill(~mask, float("-inf")).argmax().item())
                final = environment.step(action)
                total_reward += final.reward
                state = final.state.to(resolved)
            rewards.append(total_reward)
            accepted.append(bool(final and final.info.get("accepted")))
    return TrainingHistory(tuple(rewards), tuple(accepted), tuple(0.0 for _ in rewards), str(resolved))


def save_checkpoint(path: str | Path, model: CNNActorCritic, config: TrainingConfig, history: TrainingHistory | FederatedTrainingHistory) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state": model.state_dict(), "config": asdict(config), "history": asdict(history)}, path)
    return path


def load_checkpoint(path: str | Path, model: CNNActorCritic, *, device: str = "auto") -> dict[str, object]:
    payload = torch.load(Path(path), map_location=resolve_device(device), weights_only=False)
    model.load_state_dict(payload["model_state"])
    return payload
