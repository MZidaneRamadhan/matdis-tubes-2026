from dataclasses import dataclass

from core.graph_model import FlowParameters, GraphEdge, GraphModel


SOURCE = "S0"
SOURCE_GATE = "S"
SINK = "T"
INF_CAPACITY = float("inf")


@dataclass(frozen=True)
class FlowArc:
    start: str
    end: str
    capacity: float
    edge_id: int | None = None
    kind: str = "jalan"
    node: str | None = None


def edge_capacity(edge: GraphEdge, parameters: FlowParameters, scenario: str) -> float:
    if edge.man is not None:
        capacity = edge.man
    else:
        capacity = edge.lanes * parameters.c0 * edge.fc * parameters.fc / parameters.smp
    if scenario == "konvoi" and edge.hit:
        capacity *= 1 - parameters.red
    if parameters.bg:
        capacity -= edge.bg
    return max(0.0, capacity)


def build_flow_arcs(
    graph: GraphModel, parameters: FlowParameters, scenario: str
) -> list[FlowArc]:
    if scenario not in ("normal", "konvoi"):
        raise ValueError(f"Skenario aliran tidak dikenal: {scenario!r}.")

    arcs: list[FlowArc] = []
    for index, edge in enumerate(graph.edges):
        if not edge.flow:
            continue
        capacity = edge_capacity(edge, parameters, scenario)
        arcs.append(FlowArc(edge.u, edge.v, capacity, edge_id=index))
        if edge.dir == "two":
            arcs.append(FlowArc(edge.v, edge.u, capacity, edge_id=index))

    arcs.append(FlowArc(SOURCE, SOURCE_GATE, parameters.Q, kind="demand"))
    for key, node in graph.nodes.items():
        if node.jenis == "Pintu masuk":
            arcs.append(FlowArc(SOURCE_GATE, key, INF_CAPACITY, kind="source"))
        elif node.jenis == "Kantong parkir":
            arcs.append(FlowArc(key, SINK, node.pcap or 0, kind="park", node=key))
    return arcs
