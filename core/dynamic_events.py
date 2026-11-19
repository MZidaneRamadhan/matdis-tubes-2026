"""Timeline gangguan (graf dinamis) untuk simulasi Bagian 4.2.

Format YAML::

    base_scenario: asia_afrika.yaml
    timeline:
      - t: 0
        jam: "07.00"
        label: Kondisi normal
        scenario: normal            # normal | konvoi
        edges:                      # faktor pengali kapasitas (kumulatif)
          - {u: J5, v: J10, factor: 0}
        parking:
          - {node: P1, factor: 0}

Modifier bersifat kumulatif: faktor yang sudah diset tetap berlaku pada
langkah waktu berikutnya sampai diset ulang (``factor: 1`` = pulih).
"""

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from cases.scenario_loader import Scenario, load_scenario
from core.flow_model import FlowArc, build_flow_arcs


@dataclass(frozen=True)
class TimelineStep:
    t: int
    jam: str
    label: str
    scenario: str
    edge_factors: dict[int, float] = field(default_factory=dict)
    park_factors: dict[str, float] = field(default_factory=dict)
    changes: tuple[str, ...] = ()


@dataclass(frozen=True)
class DynamicCase:
    base: Scenario
    steps: tuple[TimelineStep, ...]


def _find_edge(scenario: Scenario, u: str, v: str) -> int:
    for index, edge in enumerate(scenario.graph.edges):
        if (edge.u, edge.v) == (u, v) or (edge.dir == "two" and (edge.v, edge.u) == (u, v)):
            return index
    raise ValueError(f"Edge {u}->{v} tidak ditemukan pada skenario dasar.")


def load_dynamic_case(path: str | Path) -> DynamicCase:
    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        data: Any = yaml.safe_load(handle)
    base = load_scenario(path.parent / data["base_scenario"])

    edge_factors: dict[int, float] = {}
    park_factors: dict[str, float] = {}
    steps: list[TimelineStep] = []
    for raw in data["timeline"]:
        changes: list[str] = []
        for item in raw.get("edges") or []:
            index = _find_edge(base, str(item["u"]), str(item["v"]))
            factor = float(item["factor"])
            edge_factors[index] = factor
            changes.append(f"{item['u']}->{item['v']} x{factor:g}")
        for item in raw.get("parking") or []:
            node = str(item["node"])
            if node not in base.graph.nodes:
                raise ValueError(f"Node parkir {node!r} tidak ditemukan.")
            factor = float(item["factor"])
            park_factors[node] = factor
            changes.append(f"parkir {node} x{factor:g}")
        steps.append(
            TimelineStep(
                t=int(raw["t"]),
                jam=str(raw.get("jam", raw["t"])),
                label=str(raw.get("label", "")),
                scenario=str(raw.get("scenario", "normal")),
                edge_factors=dict(edge_factors),
                park_factors=dict(park_factors),
                changes=tuple(changes),
            )
        )
    return DynamicCase(base=base, steps=tuple(steps))


def build_step_arcs(case: DynamicCase, step: TimelineStep) -> list[FlowArc]:
    """Bangun jaringan aliran untuk satu langkah waktu (struktur arc tetap)."""
    arcs = build_flow_arcs(case.base.graph, case.base.parameters, step.scenario)
    result = []
    for arc in arcs:
        factor = 1.0
        if arc.edge_id is not None:
            factor = step.edge_factors.get(arc.edge_id, 1.0)
        elif arc.kind == "park" and arc.node is not None:
            factor = step.park_factors.get(arc.node, 1.0)
        result.append(replace(arc, capacity=arc.capacity * factor) if factor != 1.0 else arc)
    return result
