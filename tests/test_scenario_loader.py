from cases.scenario_loader import load_scenario
from core.flow_model import edge_capacity


def test_scenario_loads_the_original_map_parameters_and_nodes():
    scenario = load_scenario()

    assert scenario.case_id == "asia_afrika"
    assert scenario.parameters.Q == 5000
    assert scenario.graph.nodes["GS"].nama.startswith("Gedung Sate")
    assert scenario.graph.nodes["P1"].pcap == 500
    assert scenario.graph.nodes["J5"].macet


def test_convoy_reduction_is_applied_only_to_affected_edges():
    scenario = load_scenario()
    edge = next(edge for edge in scenario.graph.edges if edge.u == "E1")

    assert edge_capacity(edge, scenario.parameters, "normal") == 3400
    assert edge_capacity(edge, scenario.parameters, "konvoi") == 2040


def test_background_traffic_cannot_make_capacity_negative():
    scenario = load_scenario()
    edge = next(edge for edge in scenario.graph.edges if edge.type == "asia_afrika")
    edge.bg = 100_000

    assert edge_capacity(edge, scenario.parameters, "normal") == 0
