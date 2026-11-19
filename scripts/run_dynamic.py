"""Simulasi graf dinamis Bagian 4.2.

Untuk setiap langkah waktu pada timeline gangguan dibandingkan:
  * Ford-Fulkerson (basic)  -> hitung ulang dari nol (re-computation)
  * Dinic (advance, cold)   -> hitung ulang dari nol
  * Dinic (advance, warm)   -> IncrementalDinic: perbaiki aliran lama saja
Serta dicek apakah aliran langkah sebelumnya masih LAYAK setelah gangguan.

Jalankan:
    python -m scripts.run_dynamic
    python -m scripts.run_dynamic cases/scenarios/asia_afrika_dynamic.yaml --repeat 300
"""

import argparse
import copy

from algorithms.maxflow import Dinic, FordFulkerson, IncrementalDinic
from config.settings import SCENARIO_DIR
from core.base_algorithm import EPSILON
from core.dynamic_events import build_step_arcs, load_dynamic_case
from core.flow_model import SINK, SOURCE
from scripts.bench_utils import markdown_table, median_ms, write_csv

DEFAULT_TIMELINE = SCENARIO_DIR / "asia_afrika_dynamic.yaml"


def stale_flow_check(prev_flows, arcs):
    """Berapa arc yang dilanggar jika aliran lama dipakai apa adanya."""
    violated, overflow = [], 0.0
    for flow, arc in zip(prev_flows, arcs):
        if flow > arc.capacity + EPSILON:
            violated.append(f"{arc.start}->{arc.end}")
            overflow += flow - arc.capacity
    return violated, overflow


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline", nargs="?", default=str(DEFAULT_TIMELINE))
    parser.add_argument("--repeat", type=int, default=300)
    args = parser.parse_args()

    case = load_dynamic_case(args.timeline)
    demand = case.base.parameters.Q
    incremental = IncrementalDinic()
    prev_flows = None
    rows, detail = [], []

    for step in case.steps:
        arcs = build_step_arcs(case, step)

        ff = FordFulkerson()
        ff_res = ff.run(SOURCE, SINK, arcs)
        dn = Dinic()
        dn_res = dn.run(SOURCE, SINK, arcs)

        snapshot = copy.deepcopy(incremental)
        if prev_flows is None:
            inc_res = incremental.run(SOURCE, SINK, arcs)
            inc_time = median_ms(lambda: IncrementalDinic().run(SOURCE, SINK, arcs), args.repeat)
        else:
            inc_res = incremental.update(arcs)
            copies = [copy.deepcopy(snapshot) for _ in range(args.repeat + 5)]
            it = iter(copies)
            inc_time = median_ms(lambda: next(it).update(arcs), args.repeat)
        inc_stats = dict(incremental.stats)

        ff_time = median_ms(lambda: FordFulkerson().run(SOURCE, SINK, arcs), args.repeat)
        dn_time = median_ms(lambda: Dinic().run(SOURCE, SINK, arcs), args.repeat)

        assert abs(ff_res.max_flow - dn_res.max_flow) < 1e-6
        assert abs(ff_res.max_flow - inc_res.max_flow) < 1e-6, (step.t, ff_res.max_flow, inc_res.max_flow)

        violated, overflow = ([], 0.0) if prev_flows is None else stale_flow_check(prev_flows, arcs)
        cut = [f"{arcs[i].start}->{arcs[i].end}" for i in dn_res.min_cut]

        rows.append(
            {
                "t": step.t,
                "jam": step.jam,
                "max_flow": f"{dn_res.max_flow:.0f}",
                "tak_terlayani": f"{max(0.0, demand - dn_res.max_flow):.0f}",
                "aliran_lama_layak": "-" if prev_flows is None else ("ya" if not violated else f"TIDAK ({len(violated)} arc, lebih {overflow:.0f})"),
                "FF_ms": f"{ff_time:.4f}",
                "FF_aug": ff.stats["augmentations"],
                "FF_scan": ff.stats["edge_scans"],
                "Dinic_ms": f"{dn_time:.4f}",
                "Dinic_fase": dn.stats["phases"],
                "Dinic_aug": dn.stats["augmentations"],
                "Dinic_scan": dn.stats["edge_scans"],
                "Inkr_ms": f"{inc_time:.4f}",
                "Inkr_aug": inc_stats["augmentations"],
                "Inkr_scan": inc_stats["edge_scans"],
            }
        )
        detail.append(
            {
                "t": step.t,
                "jam": step.jam,
                "kejadian": step.label,
                "perubahan": "; ".join(step.changes) or "-",
                "arc_berubah": inc_stats.get("arcs_changed", "-"),
                "arc_meluap": inc_stats.get("overflow_arcs", "-"),
                "dialihkan": f"{inc_stats.get('rerouted', 0):.0f}",
                "dibatalkan": f"{inc_stats.get('cancelled', 0):.0f}",
                "arc_dilanggar_aliran_lama": ", ".join(violated) or "-",
                "min_cut": ", ".join(cut),
            }
        )
        prev_flows = dn_res.arc_flows if prev_flows is None else inc_res.arc_flows

    print(f"\n=== 4.2 Timeline gangguan: {args.timeline} (demand Q = {demand:.0f}) ===")
    print(markdown_table(detail))
    print(f"\n=== 4.2 Respons algoritma per langkah waktu (median {args.repeat}x) ===")
    print(markdown_table(rows))
    print("Disimpan:", write_csv("dynamic_timeline.csv", rows), write_csv("dynamic_events.csv", detail))


if __name__ == "__main__":
    main()
