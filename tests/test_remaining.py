import torch

from fppvs import SFCQueueMemory, SFCRequest, VNF, VNFKind, jains_fairness
from fppvs.baselines import model_chooser, place
from fppvs.environment import ORIGINAL_FEATURES, PAPER_FEATURES, PlacementEnvironment
from fppvs.neural import CNNActorCritic, MLPActorCritic, OriginalCNNActorCritic, fedavg
from fppvs.sqn import SQNLSTMPredictor
from fppvs.substrate import DataCenter, MECNetwork, PhysicalLink
from fppvs.training import FederatedTrainingHistory, TrainingHistory


def test_sqn_queue_and_network_shapes_and_fedavg():
    memory = SFCQueueMemory(["dpi", "nat"], 5)
    memory.observe([VNF("dpi-1", VNFKind.SHAPER, 3)])
    assert memory.tensor().shape == (1, 1, 2)
    one, two = CNNActorCritic(), CNNActorCritic()
    logits, value = one(torch.zeros(2, 1, 3, 4))
    assert logits.shape == (2, 4) and value.shape == (2, 1)
    fedavg([one, two])
    assert jains_fairness([1, 1]) == 1


def test_original_and_2022_networks_output_one_logit_per_dc():
    original = OriginalCNNActorCritic(ORIGINAL_FEATURES, 5).eval()
    logits, value = original(torch.zeros(1, 1, ORIGINAL_FEATURES, 5))
    assert logits.shape == (1, 5) and value.shape == (1, 1)
    zhang = MLPActorCritic(PAPER_FEATURES, 5)
    logits, value = zhang(torch.zeros(1, 1, PAPER_FEATURES, 5))
    assert logits.shape == (1, 5) and value.shape == (1, 1)


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


def test_learned_policy_choice_is_deterministic():
    network = MECNetwork([DataCenter("a", 10), DataCenter("b", 10)], [PhysicalLink("a", "b", 10, 100)])
    request = SFCRequest("a", (VNF("dpi-1", VNFKind.SHAPER, 1),), "b", ((0,),), max_latency=20)
    chooser = model_chooser(CNNActorCritic())
    first = place(PlacementEnvironment(network, request), chooser)
    second = place(PlacementEnvironment(network, request), chooser)
    assert first.info["accepted"] == second.info["accepted"]


def test_original_mode_only_offers_current_or_neighbouring_nodes():
    # Line a - b - c: from source 'a', the first VNF may go on 'a' or 'b', not 'c'.
    network = MECNetwork(
        [DataCenter("a", 10), DataCenter("b", 10), DataCenter("c", 10)],
        [PhysicalLink("a", "b", 5, 100), PhysicalLink("b", "c", 5, 100)],
    )
    request = SFCRequest("a", (VNF("fw-1-0", VNFKind.SHAPER, 1, 0.1),), "c", ((0,),), data_rate=5, max_latency=100)
    env = PlacementEnvironment(network, request, original_mode=True)
    assert env.action_mask().tolist() == [True, True, False]
    assert env.state().shape == (1, 1, ORIGINAL_FEATURES, 3)
