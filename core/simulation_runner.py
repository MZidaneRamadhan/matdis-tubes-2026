from dataclasses import dataclass, field
from statistics import median
from time import perf_counter

from algorithms import AlgorithmRegistry
from core.base_algorithm import FlowResult
from core.flow_model import SINK, SOURCE, FlowArc, build_flow_arcs
from core.graph_model import FlowParameters, GraphModel


ALGORITHMS = {
    "Dinic": "dinic",
    "Ford-Fulkerson": "ford_fulkerson",
    "Push-Relabel": "push_relabel",
}


@dataclass(frozen=True)
class ScenarioResult:
    scenario: str
    algorithm: str
    flow_result: FlowResult
    arcs: tuple[FlowArc, ...]
    edge_results: dict[int, dict[str, float]]
    parking_capacity: float
    demand: float
    elapsed_ms: float = 0.0
    stats: dict[str, int | float] = field(default_factory=dict)

    @property
    def unserved(self) -> float:
        return max(0.0, self.demand - self.flow_result.max_flow)


def solve_scenario(
    graph: GraphModel,
    parameters: FlowParameters,
    scenario: str,
    algorithm: str = "Dinic",
    repeats: int = 25,
) -> ScenarioResult:
    graph.validate()
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Algoritma tidak dikenal: {algorithm!r}.")

    arcs = build_flow_arcs(graph, parameters, scenario)
    key = ALGORITHMS[algorithm]
    samples = []
    solver = None
    result = None
    for _ in range(max(1, repeats)):
        solver = AlgorithmRegistry.create(key, graph)
        started = perf_counter()
        result = solver.run(SOURCE, SINK, arcs)
        samples.append((perf_counter() - started) * 1000)

    edge_results: dict[int, dict[str, float]] = {}
    for index, arc in enumerate(arcs):
        if arc.edge_id is None:
            continue
        totals = edge_results.setdefault(arc.edge_id, {"flow": 0.0, "capacity": 0.0})
        totals["flow"] += result.arc_flows[index]
        totals["capacity"] += arc.capacity

    return ScenarioResult(
        scenario=scenario,
        algorithm=algorithm,
        flow_result=result,
        arcs=tuple(arcs),
        edge_results=edge_results,
        parking_capacity=sum(
            arc.capacity for arc in arcs if arc.kind == "park"
        ),
        demand=parameters.Q,
        elapsed_ms=median(samples),
        stats=dict(getattr(solver, "stats", {}) or {}),
    )


def solve_both_scenarios(
    graph: GraphModel,
    parameters: FlowParameters,
    algorithm: str = "Dinic",
) -> dict[str, ScenarioResult]:
    return {
        scenario: solve_scenario(graph, parameters, scenario, algorithm)
        for scenario in ("normal", "konvoi")
    }


def compare_algorithms(
    graph: GraphModel,
    parameters: FlowParameters,
    algorithms: tuple[str, ...] = ("Ford-Fulkerson", "Dinic"),
) -> dict[str, dict[str, ScenarioResult]]:
    """Hitung max-flow untuk setiap algoritma pada skenario normal dan konvoi."""
    return {
        algo: solve_both_scenarios(graph, parameters, algo)
        for algo in algorithms
    }
