import pytest

from algorithms.maxflow import Dinic, FordFulkerson, PushRelabel
from core.flow_model import FlowArc
from core.graph_model import FlowParameters, GraphModel
from core.simulation_runner import solve_both_scenarios


ALGORITHMS = [Dinic, FordFulkerson, PushRelabel]


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_max_flow_and_min_cut_capacity_match(algorithm):
    arcs = [
        FlowArc("s", "a", 10),
        FlowArc("s", "b", 5),
        FlowArc("a", "b", 15),
        FlowArc("a", "t", 10),
        FlowArc("b", "t", 10),
    ]

    result = algorithm().run("s", "t", arcs)

    assert result.max_flow == pytest.approx(15)
    assert sum(arcs[index].capacity for index in result.min_cut) == pytest.approx(15)
    balance = {node: 0.0 for arc in arcs for node in (arc.start, arc.end)}
    for arc, flow in zip(arcs, result.arc_flows):
        assert 0 <= flow <= arc.capacity
        balance[arc.start] -= flow
        balance[arc.end] += flow
    assert balance["s"] == pytest.approx(-15)
    assert balance["t"] == pytest.approx(15)
    assert balance["a"] == pytest.approx(0)
    assert balance["b"] == pytest.approx(0)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_parallel_arcs_and_reverse_edges_are_supported(algorithm):
    arcs = [
        FlowArc("s", "a", 2),
        FlowArc("s", "a", 3),
        FlowArc("a", "s", 8),
        FlowArc("a", "t", 4),
        FlowArc("a", "t", 1),
    ]

    result = algorithm().run("s", "t", arcs)

    assert result.max_flow == pytest.approx(5)
    assert len(result.arc_flows) == len(arcs)
    assert all(0 <= flow <= arc.capacity for flow, arc in zip(result.arc_flows, arcs))


@pytest.mark.parametrize(
    ("algorithm", "algorithm_name"),
    [
        (Dinic, "Dinic"),
        (FordFulkerson, "Ford-Fulkerson"),
        (PushRelabel, "Push-Relabel"),
    ],
)
def test_bundled_asia_afrika_scenario_uses_all_parking_capacity(
    algorithm, algorithm_name
):
    from cases.scenario_loader import load_scenario

    scenario = load_scenario()
    results = solve_both_scenarios(
        scenario.graph, scenario.parameters, algorithm_name
    )

    assert len(scenario.graph.nodes) == 23
    assert len(scenario.graph.edges) == 27
    assert results["normal"].flow_result.max_flow == pytest.approx(2700)
    assert results["konvoi"].flow_result.max_flow == pytest.approx(2700)
    assert results["normal"].unserved == pytest.approx(2300)


def test_negative_capacity_is_rejected():
    with pytest.raises(ValueError, match="non-negatif"):
        Dinic().run("s", "t", [FlowArc("s", "t", -1)])


def test_zero_demand_has_zero_flow():
    graph = GraphModel.from_dict(
        {
            "nodes": {
                "E": {
                    "lat": 0,
                    "lon": 0,
                    "nama": "Pintu",
                    "jenis": "Pintu masuk",
                },
                "P": {
                    "lat": 1,
                    "lon": 1,
                    "nama": "Parkir",
                    "jenis": "Kantong parkir",
                    "pcap": 10,
                },
            },
            "edges": [{"u": "E", "v": "P", "lanes": 1}],
        }
    )

    result = solve_both_scenarios(
        graph, FlowParameters.from_dict({"Q": 0})
    )["normal"]

    assert result.flow_result.max_flow == 0
