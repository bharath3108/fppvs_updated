from collections import deque
from dataclasses import dataclass
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

@dataclass
class VNFInstance:
    id: str; vnf_type: str; data_center: str; capacity: float; used: float = 0.0
    @property
    def remaining(self): return self.capacity - self.used

class VNFInstancePool:
    def __init__(self, instances: Iterable[VNFInstance] = (), dc_capacities: dict[str, float] = None):
        self.instances = {i.id: i for i in instances}
        
        # Track dynamic DC capacities and their current usage
        self.dc_capacities = dc_capacities or {}
        self.dc_used = {dc: 0.0 for dc in self.dc_capacities}
        
        # Initialize DC usage based on pre-existing instances
        for i in self.instances.values():
            self.dc_used[i.data_center] = self.dc_used.get(i.data_center, 0.0) + i.capacity

    def set_dc_capacity(self, data_center: str, new_capacity: float):
        """Dynamically update the total resource limit of a server/DC."""
        self.dc_capacities[data_center] = new_capacity
        if data_center not in self.dc_used:
            self.dc_used[data_center] = 0.0

    def get_dc_remaining(self, data_center: str) -> float:
        """Check how much physical server capacity is left."""
        return self.dc_capacities.get(data_center, 0.0) - self.dc_used.get(data_center, 0.0)

    def add_instance(self, instance: VNFInstance):
        """Create a new instance ONLY if the DC has enough dynamic capacity."""
        if self.get_dc_remaining(instance.data_center) < instance.capacity:
            raise ValueError(f"Insufficient total capacity in Data Center {instance.data_center}")
        
        self.instances[instance.id] = instance
        self.dc_used[instance.data_center] += instance.capacity

    def choose(self, vnf: VNF, cost: dict[str, float]) -> VNFInstance | None:
        """Share an existing instance (does not consume extra DC capacity)."""
        candidates = [i for i in self.instances.values() if i.vnf_type == vnf_type(vnf) and i.remaining >= vnf.compute_demand]
        return min(candidates, key=lambda i: (-i.remaining, cost.get(i.data_center, float('inf')), i.id)) if candidates else None

    def allocate(self, instance: VNFInstance, demand: float):
        """Allocate demand to an instance."""
        if instance.remaining < demand: 
            raise ValueError("insufficient instance capacity")
        instance.used += demand