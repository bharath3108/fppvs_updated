import networkx as nx
import pytest

from fppvs import SFCRequest, VNF, VNFKind, parallelize_sfc
from fppvs import DataCenter, MECNetwork, PhysicalLink, evaluate_placement


S = VNFKind.SHAPER
M = VNFKind.MONITOR


def request(vnfs, matrix):
    return SFCRequest("ingress", vnfs, "egress", matrix)


def test_mixed_chain_connects_dependent_monitor_to_shaper():
    result = parallelize_sfc(
        request(
            [VNF("firewall", S), VNF("ids", M), VNF("nat", S)],
            [[0, 0, 0], [0, 0, 0], [0, 1, 0]],
        )
    )

    assert result.main_chain == ("ingress", "firewall", "nat", "egress")
    assert result.branch_paths == {"ids": ("firewall", "ids", "nat")}
    assert set(result.graph.edges) == {
        ("ingress", "firewall"),
        ("firewall", "nat"),
        ("nat", "egress"),
        ("firewall", "ids"),
        ("ids", "nat"),
    }
    assert nx.is_directed_acyclic_graph(result.graph)


def test_outstanding_monitors_rejoin_at_egress():
    result = parallelize_sfc(
        request(
            [VNF("dpi", S), VNF("logger", M), VNF("meter", M)],
            [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
        )
    )

    assert result.main_chain == ("ingress", "dpi", "egress")
    assert result.branch_paths == {
        "logger": ("dpi", "logger", "egress"),
        "meter": ("dpi", "meter", "egress"),
    }


def test_only_shapers_remain_a_single_main_chain():
    result = parallelize_sfc(
        request(
            [VNF("firewall", S), VNF("nat", S)],
            [[0, 0], [0, 0]],
        )
    )

    assert result.main_chain == ("ingress", "firewall", "nat", "egress")
    assert result.branch_paths == {}


def test_only_monitors_form_branches_from_ingress_to_egress():
    result = parallelize_sfc(
        request(
            [VNF("logger", M), VNF("meter", M)],
            [[0, 0], [0, 0]],
        )
    )

    assert result.main_chain == ("ingress", "egress")
    assert result.branch_paths == {
        "logger": ("ingress", "logger", "egress"),
        "meter": ("ingress", "meter", "egress"),
    }


def test_rejects_non_square_dependency_matrix():
    with pytest.raises(ValueError, match="square"):
        parallelize_sfc(request([VNF("logger", M)], [[0, 0]]))


def test_rejects_monitor_dependency_row():
    with pytest.raises(ValueError, match="monitor rows"):
        parallelize_sfc(
            request(
                [VNF("logger", M), VNF("nat", S)],
                [[0, 1], [0, 0]],
            )
        )


def network(link_bandwidth=5):
    return MECNetwork(
        [DataCenter("a", 10), DataCenter("b", 10), DataCenter("c", 10)],
        [
            PhysicalLink("a", "b", latency=1, bandwidth_capacity=link_bandwidth),
            PhysicalLink("b", "c", latency=1, bandwidth_capacity=link_bandwidth),
            PhysicalLink("a", "c", latency=3, bandwidth_capacity=link_bandwidth),
        ],
    )


def test_evaluator_uses_shortest_routes_and_reports_latency():
    sfc = request(
        [VNF("dpi", S, compute_demand=4, processing_latency=1, virtualization_latency=0.5)],
        [[0]],
    )
    result = evaluate_placement(
        network(),
        sfc,
        parallelize_sfc(sfc),
        {"ingress": "a", "dpi": "b", "egress": "c"},
    )

    assert result.feasible
    assert result.routes == {("ingress", "dpi"): ("a", "b"), ("dpi", "egress"): ("b", "c")}
    assert result.compute_usage["b"] == 4
    assert result.latency.network == 2
    assert result.latency.virtualization == 0.5
    assert result.latency.processing == 1
    assert result.latency.end_to_end == 3.5


def test_evaluator_rejects_compute_and_bandwidth_overcommitment():
    sfc = request([VNF("dpi", S, compute_demand=11)], [[0]])
    sfc = SFCRequest(
        sfc.source,
        sfc.vnfs,
        sfc.destination,
        sfc.dependency_matrix,
        data_rate=2,
    )
    result = evaluate_placement(
        network(link_bandwidth=1),
        sfc,
        parallelize_sfc(sfc),
        {"ingress": "a", "dpi": "b", "egress": "c"},
    )

    assert not result.feasible
    assert any("compute capacity" in message for message in result.violations)
    assert any("bandwidth capacity" in message for message in result.violations)


def test_parallel_sfc_latency_uses_the_critical_branch():
    substrate = MECNetwork(
        [DataCenter("a", 10), DataCenter("b", 10)],
        [PhysicalLink("a", "b", latency=2, bandwidth_capacity=10)],
    )
    sfc = request(
        [
            VNF("monitor", M, processing_latency=1),
            VNF("shape", S, processing_latency=0.5),
        ],
        [[0, 0], [0, 0]],
    )
    result = evaluate_placement(
        substrate,
        sfc,
        parallelize_sfc(sfc),
        {"ingress": "a", "shape": "a", "monitor": "b", "egress": "a"},
    )

    assert result.feasible
    assert result.latency.critical_path == ("ingress", "monitor", "egress")
    assert result.latency.end_to_end == 5
