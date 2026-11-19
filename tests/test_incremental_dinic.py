import random

import pytest

from algorithms.maxflow import Dinic, IncrementalDinic
from core.dynamic_events import build_step_arcs, load_dynamic_case
from core.flow_model import FlowArc, SINK, SOURCE
from config.settings import SCENARIO_DIR


def _random_arcs(rng: random.Random, n: int = 12, m: int = 40) -> list[FlowArc]:
    nodes = [SOURCE, SINK] + [f"v{i}" for i in range(n)]
    arcs = []
    for _ in range(m):
        u, v = rng.sample(nodes, 2)
        arcs.append(FlowArc(u, v, float(rng.randint(0, 20))))
    return arcs


def _assert_feasible(arcs, result):
    balance = {}
    for arc, flow in zip(arcs, result.arc_flows):
        assert -1e-9 <= flow <= arc.capacity + 1e-9
        balance[arc.start] = balance.get(arc.start, 0) - flow
        balance[arc.end] = balance.get(arc.end, 0) + flow
    for node, value in balance.items():
        if node not in (SOURCE, SINK):
            assert value == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize("seed", range(40))
def test_incremental_matches_recomputation(seed):
    rng = random.Random(seed)
    arcs = _random_arcs(rng)
    solver = IncrementalDinic()
    solver.run(SOURCE, SINK, arcs)
    for _ in range(6):
        arcs = [
            FlowArc(a.start, a.end, float(rng.randint(0, 20)) if rng.random() < 0.3 else a.capacity)
            for a in arcs
        ]
        warm = solver.update(arcs)
        cold = Dinic().run(SOURCE, SINK, arcs)
        assert warm.max_flow == pytest.approx(cold.max_flow)
        _assert_feasible(arcs, warm)


def test_dynamic_timeline_asia_afrika():
    case = load_dynamic_case(SCENARIO_DIR / "asia_afrika_dynamic.yaml")
    solver = IncrementalDinic()
    for i, step in enumerate(case.steps):
        arcs = build_step_arcs(case, step)
        result = solver.run(SOURCE, SINK, arcs) if i == 0 else solver.update(arcs)
        assert result.max_flow == pytest.approx(Dinic().run(SOURCE, SINK, arcs).max_flow)
        _assert_feasible(arcs, result)
