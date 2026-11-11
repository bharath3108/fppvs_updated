import pytest
import torch

from fppvs import DataCenter, MECNetwork, PhysicalLink, SFCRequest, VNF, VNFKind
from fppvs.admission import Admission, ResourceLedger
from fppvs.baselines import place, prior_choice, run_stream, shortest_choice
from fppvs.environment import FEATURES, ROW_PRIOR, PlacementEnvironment
from fppvs.experiment import arrival_rate_for_load
from fppvs.neural import CNNActorCritic, fedavg
from fppvs.workloads import make_network, make_requests

S = VNFKind.SHAPER


def line_network(bandwidth=100.0, capacity=10.0):
    return MECNetwork(
        [DataCenter("a", capacity), DataCenter("b", capacity), DataCenter("c", capacity)],
        [PhysicalLink("a", "b", 5, bandwidth), PhysicalLink("b", "c", 5, bandwidth)],
    )


def chain(index, *, demand=1.0, rate=10.0, arrival=0.0, ttl=10, source="a", destination="c", kinds=("fw", "nat")):
    vnfs = tuple(VNF(f"{kind}-{index}-{i}", S, demand, 0.1) for i, kind in enumerate(kinds))
    size = len(vnfs)
    return SFCRequest(source, vnfs, destination, tuple(tuple(0 for _ in range(size)) for _ in range(size)),
                      arrival_time=arrival, ttl=ttl, data_rate=rate, max_latency=100)


def test_ledger_releases_everything_and_integrates_resource_time():
    network = line_network()
    ledger = ResourceLedger(network, instance_overhead=0.5)
    ledger.advance(0)
    ledger.commit(Admission({"a": 2.0}, {("a", "b"): 10.0}, shared_instances=(("a", "fw"),)), expires_at=10)
    ledger.advance(4)
    assert ledger.compute["a"] == pytest.approx(2.5)  # demand + one instance overhead
    ledger.drain()
    assert sum(ledger.compute.values()) == pytest.approx(0)
    assert sum(ledger.links.values()) == pytest.approx(0)
    assert ledger.compute_time == pytest.approx(2.5 * 10)
    assert ledger.bandwidth_time == pytest.approx(10 * 10)
    assert ledger.active_time == pytest.approx(10)


def test_shared_instance_overhead_is_paid_once_and_released_with_last_user():
    ledger = ResourceLedger(line_network(), instance_overhead=0.5)
    ledger.advance(0)
    key = ("a", "fw")
    ledger.commit(Admission({"a": 1.0}, {}, shared_instances=(key,), new_instances=(key,)), expires_at=5)
    ledger.commit(Admission({"a": 1.0}, {}, shared_instances=(key,)), expires_at=10)
    assert ledger.compute["a"] == pytest.approx(2.5)
    ledger.advance(6)
    assert ledger.compute["a"] == pytest.approx(1.5)  # instance kept alive by second user
    ledger.advance(11)
    assert ledger.compute["a"] == pytest.approx(0)
    assert ledger.instances_created == 1


def test_sharing_reuses_live_instance_and_saves_compute():
    network = line_network()
    for sharing, expected in ((True, 2 * 1.0 + 0.25), (False, 2 * 1.25)):
        ledger = ResourceLedger(network)
        env = PlacementEnvironment(network, chain(0, kinds=("fw", "fw")), sharing=sharing, ledger=ledger)
        final = place(env, lambda e, c: 0)
        assert final.info["accepted"]
        assert final.info["compute"] == pytest.approx(expected)


def test_mask_prunes_data_centers_without_bandwidth():
    # Link a-b is full, so placing the first VNF on b or c (reached via a-b) is pruned;
    # 'a' stays feasible, but the chain can never reach egress 'b' and is rejected.
    network = line_network(bandwidth=10)
    ledger = ResourceLedger(network)
    ledger.advance(0)
    ledger.commit(Admission({}, {("a", "b"): 10.0}), expires_at=100)
    env = PlacementEnvironment(network, chain(1, source="a", destination="b", rate=5), ledger=ledger)
    assert env.action_mask().tolist() == [True, False, False]
    final = place(env, shortest_choice)
    assert final.info["accepted"] is False
    assert not ledger.reservations[1:]  # nothing new committed


def test_rejection_commits_nothing():
    network = line_network(capacity=1.5)
    ledger = ResourceLedger(network)
    env = PlacementEnvironment(network, chain(2, demand=1.0, kinds=("fw", "nat", "lb", "ids", "dpi")), ledger=ledger)
    final = place(env, prior_choice)
    assert final.info["accepted"] is False
    assert sum(ledger.compute.values()) == 0 and not ledger.reservations


def test_state_grid_shape_and_policy_logits_cover_every_dc():
    network = line_network()
    env = PlacementEnvironment(network, chain(3))
    state = env.reset()
    assert state.shape == (1, 1, FEATURES, 3)
    model = CNNActorCritic(prior_row=ROW_PRIOR)
    model.eval()
    logits, value = model(state)
    assert logits.shape == (1, 3) and value.shape == (1, 1)


def test_policy_is_permutation_equivariant_over_dcs():
    model = CNNActorCritic()
    model.eval()
    state = torch.randn(1, 1, FEATURES, 5)
    permutation = torch.tensor([4, 2, 0, 1, 3])
    logits, _ = model(state)
    permuted, _ = model(state[..., permutation])
    assert torch.allclose(logits[0, permutation], permuted[0], atol=1e-5)


def test_weighted_fedavg():
    one, two = CNNActorCritic(), CNNActorCritic()
    with torch.no_grad():
        one.prior_weight.fill_(0.0); two.prior_weight.fill_(4.0)
    fedavg([one, two], [3, 1])
    assert one.prior_weight.item() == pytest.approx(1.0) == two.prior_weight.item()


def test_poisson_arrivals_hit_requested_load():
    network = make_network(24, 47, 3)
    rate = arrival_rate_for_load(network, 1.0)
    requests = make_requests(network, 2000, 4, arrival_rate=rate)
    span = requests[-1].arrival_time - requests[0].arrival_time
    assert 0.9 < (len(requests) - 1) / span / rate < 1.1
    assert all(5 <= r.data_rate <= 30 for r in requests)


def test_stream_metrics_are_consistent():
    network = make_network(17, 29, 5)
    requests = make_requests(network, 80, 6, arrival_rate=arrival_rate_for_load(network, 0.5))
    ledger = ResourceLedger(network)
    envs = [PlacementEnvironment(network, r, ledger=ledger) for r in requests]
    summary = run_stream(envs, prior_choice, ledger, retries=2).summary()
    assert 0 <= summary["acceptance"] <= 1
    # Each running SFC holds at least four VNFs x 0.5 units of compute.
    assert summary["compute_per_active_sfc"] >= 2.0
