import torch
from fppvs import SFCQueueMemory, SFCRequest, VNF, VNFInstance, VNFInstancePool, VNFKind, jains_fairness
from fppvs.neural import CNNActorCritic, DemandLSTM, fedavg
from fppvs.sqn import SQNLSTMPredictor
from fppvs.training import FederatedTrainingHistory, TrainingHistory
from fppvs.training import evaluate_policy
from fppvs.environment import PlacementEnvironment
from fppvs.substrate import DataCenter, MECNetwork, PhysicalLink

def test_sharing_prefers_capacity_then_cost():
    v = VNF("dpi", VNFKind.SHAPER, compute_demand=2)
    pool = VNFInstancePool([VNFInstance("a", "dpi", "x", 10, 2), VNFInstance("b", "dpi", "y", 8, 0)])
    assert pool.choose(v, {"x": 1, "y": 10}).id == "a"

def test_sqn_and_neural_shapes_and_fedavg():
    memory = SFCQueueMemory(["dpi", "nat"], 5); memory.observe([VNF("dpi", VNFKind.SHAPER, 3)])
    assert DemandLSTM(2)(memory.tensor()).shape == (1, 2)
    one, two = CNNActorCritic(4), CNNActorCritic(4)
    logits, value = one(torch.zeros(2, 1, 3, 4))
    assert logits.shape == (2, 4) and value.shape == (2, 1)
    fedavg([one, two]); assert jains_fairness([1, 1]) == 1


def test_sqn_lstm_predictor_keeps_bounded_request_history():
    predictor = SQNLSTMPredictor(time_depth=2)
    request = SFCRequest("a", (VNF("dpi-1", VNFKind.SHAPER, 3),), "b", ((0,),))
    predictor.update(request)
    predictor.update(request)
    predictor.update(request)
    assert len(predictor.memory.layers) == 2
    assert predictor.prediction().for_vnf("dpi") >= 0


def test_federated_history_uses_every_local_episode_for_acceptance():
    first = TrainingHistory((1.0, -1.0), (True, False), (0.2, 0.2), "cpu")
    second = TrainingHistory((1.0, 1.0), (True, True), (0.2, 0.2), "cpu")
    history = FederatedTrainingHistory((0.5,), (0.75,), (first, second), "cpu")
    assert len(history.accepted) == 4
    assert history.acceptance_rate == 0.75


def test_policy_evaluation_is_deterministic_on_a_fresh_environment():
    network = MECNetwork([DataCenter("a", 10), DataCenter("b", 10)], [PhysicalLink("a", "b", 10, 1)])
    request = SFCRequest("a", (VNF("dpi-1", VNFKind.SHAPER, 1),), "b", ((0,),), max_latency=20)
    model = CNNActorCritic(2)
    first = evaluate_policy(model, [PlacementEnvironment(network, request)])
    second = evaluate_policy(model, [PlacementEnvironment(network, request)])
    assert first.accepted == second.accepted
