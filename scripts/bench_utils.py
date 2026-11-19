"""Utilitas pengukuran untuk benchmark Bagian 4.1 dan 4.2."""

import csv
from pathlib import Path
from statistics import median
from time import perf_counter
import tracemalloc
from typing import Any, Callable, Iterable

from config.settings import PROJECT_ROOT

RESULTS_DIR = PROJECT_ROOT / "results"


def median_ms(fn: Callable[[], Any], repeat: int = 200, warmup: int = 5) -> float:
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(repeat):
        started = perf_counter()
        fn()
        samples.append((perf_counter() - started) * 1000)
    return median(samples)


def peak_kib(fn: Callable[[], Any]) -> float:
    tracemalloc.start()
    try:
        fn()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return peak / 1024


def write_csv(name: str, rows: list[dict[str, Any]]) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / name
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def markdown_table(rows: Iterable[dict[str, Any]]) -> str:
    rows = list(rows)
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in rows:
        lines.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
    return "\n".join(lines)
