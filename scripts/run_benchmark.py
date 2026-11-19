import argparse
from time import perf_counter

from cases.scenario_loader import load_scenario
from scripts.cli_utils import resolve_scenario_path
from core.simulation_runner import ALGORITHMS, solve_both_scenarios


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bandingkan waktu eksekusi algoritma max-flow."
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        help="Path file YAML skenario (default: Asia Afrika).",
    )
    args = parser.parse_args()
    scenario = load_scenario(resolve_scenario_path(args.scenario))
    print(f"Benchmark: {scenario.title}")
    print(f"{'Algoritma':<20} {'Normal':>12} {'Konvoi':>12} {'Waktu (ms)':>14}")

    for name in ALGORITHMS:
        started = perf_counter()
        results = solve_both_scenarios(
            scenario.graph, scenario.parameters, algorithm=name
        )
        elapsed_ms = (perf_counter() - started) * 1000
        print(
            f"{name:<20} "
            f"{results['normal'].flow_result.max_flow:>12,.0f} "
            f"{results['konvoi'].flow_result.max_flow:>12,.0f} "
            f"{elapsed_ms:>14.3f}"
        )


if __name__ == "__main__":
    main()
