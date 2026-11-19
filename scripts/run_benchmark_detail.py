"""Benchmark detail Bagian 4.1: Ford-Fulkerson (basic) vs Dinic (advance).

Jalankan:
    python -m scripts.run_benchmark_detail
    python -m scripts.run_benchmark_detail --repeat 500 --sizes 5 10 20 40

Output: tabel di konsol + results/benchmark_asia_afrika.csv dan
results/benchmark_scaling.csv (untuk slide/grafik video).
"""

import argparse
import random

from algorithms.maxflow import Dinic, FordFulkerson
from cases.scenario_loader import load_scenario
from core.flow_model import SINK, SOURCE, FlowArc, build_flow_arcs
from scripts.bench_utils import markdown_table, median_ms, peak_kib, write_csv
from scripts.cli_utils import resolve_scenario_path

SOLVERS = {
    "Ford-Fulkerson (basic)": FordFulkerson,
    "Dinic (advance)": Dinic,
}


def grid_network(k: int, seed: int = 2026) -> list[FlowArc]:
    """Graf grid k x k sintetis (meniru jaringan jalan) dengan kapasitas acak."""
    rng = random.Random(seed)
    arcs: list[FlowArc] = []
    name = lambda r, c: f"g{r}_{c}"  # noqa: E731
    for r in range(k):
        arcs.append(FlowArc(SOURCE, name(r, 0), float("inf")))
        arcs.append(FlowArc(name(r, k - 1), SINK, float("inf")))
        for c in range(k):
            if c + 1 < k:
                arcs.append(FlowArc(name(r, c), name(r, c + 1), rng.randint(100, 2000)))
                arcs.append(FlowArc(name(r, c + 1), name(r, c), rng.randint(100, 2000)))
            if r + 1 < k:
                arcs.append(FlowArc(name(r, c), name(r + 1, c), rng.randint(100, 2000)))
                arcs.append(FlowArc(name(r + 1, c), name(r, c), rng.randint(100, 2000)))
    return arcs


def measure(solver_cls, arcs, repeat: int) -> dict:
    solver = solver_cls()
    result = solver.run(SOURCE, SINK, arcs)
    stats = getattr(solver, "stats", {})
    return {
        "max_flow": result.max_flow,
        "time_ms": median_ms(lambda: solver_cls().run(SOURCE, SINK, arcs), repeat),
        "memory_kib": peak_kib(lambda: solver_cls().run(SOURCE, SINK, arcs)),
        "phases_bfs": stats.get("phases", "-"),
        "augmentations": stats.get("augmentations", result.augmentations or "-"),
        "edge_scans": stats.get("edge_scans", "-"),
        "min_cut": result.min_cut,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", nargs="?")
    parser.add_argument("--repeat", type=int, default=300)
    parser.add_argument("--sizes", type=int, nargs="*", default=[5, 10, 20, 40])
    args = parser.parse_args()

    scenario = load_scenario(resolve_scenario_path(args.scenario))
    graph, params = scenario.graph, scenario.parameters
    rows = []
    for scen in ("normal", "konvoi"):
        arcs = build_flow_arcs(graph, params, scen)
        nodes = {a.start for a in arcs} | {a.end for a in arcs}
        for label, cls in SOLVERS.items():
            m = measure(cls, arcs, args.repeat)
            rows.append(
                {
                    "skenario": scen,
                    "algoritma": label,
                    "V": len(nodes),
                    "E_arc": len(arcs),
                    "max_flow": f"{m['max_flow']:.0f}",
                    "waktu_ms_median": f"{m['time_ms']:.4f}",
                    "memori_puncak_KiB": f"{m['memory_kib']:.1f}",
                    "fase_BFS": m["phases_bfs"],
                    "augmenting_path": m["augmentations"],
                    "edge_scan": m["edge_scans"],
                }
            )
    print(f"\n=== 4.1 Benchmark: {scenario.title} (median {args.repeat}x) ===")
    print(markdown_table(rows))
    path = write_csv("benchmark_asia_afrika.csv", rows)
    print(f"Disimpan: {path}")

    scaling = []
    for k in args.sizes:
        arcs = grid_network(k)
        repeat = max(3, args.repeat // (k * k // 25 or 1))
        for label, cls in SOLVERS.items():
            m = measure(cls, arcs, repeat)
            scaling.append(
                {
                    "grid": f"{k}x{k}",
                    "V": k * k + 2,
                    "E_arc": len(arcs),
                    "algoritma": label,
                    "max_flow": f"{m['max_flow']:.0f}",
                    "waktu_ms_median": f"{m['time_ms']:.3f}",
                    "memori_puncak_KiB": f"{m['memory_kib']:.1f}",
                    "fase_BFS": m["phases_bfs"],
                    "augmenting_path": m["augmentations"],
                    "edge_scan": m["edge_scans"],
                }
            )
    print("\n=== 4.1 Uji skalabilitas (graf grid sintetis) ===")
    print(markdown_table(scaling))
    path = write_csv("benchmark_scaling.csv", scaling)
    print(f"Disimpan: {path}")


if __name__ == "__main__":
    main()
