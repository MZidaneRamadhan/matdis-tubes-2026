from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
import math
from typing import Sequence

from core.flow_model import FlowArc


EPSILON = 1e-9


@dataclass
class ResidualEdge:
    target: str
    reverse_index: int
    capacity: float


@dataclass(frozen=True)
class FlowResult:
    max_flow: float
    arc_flows: tuple[float, ...]
    source_partition: frozenset[str]
    min_cut: tuple[int, ...]
    augmentations: int


class BaseGraphAlgorithm(ABC):
    def __init__(self, graph_model=None):
        self.graph_model = graph_model

    @staticmethod
    def _initialize(
        arcs: Sequence[FlowArc], source: str, sink: str
    ) -> tuple[dict[str, list[ResidualEdge]], list[tuple[str, int]]]:
        if source == sink:
            raise ValueError("Sumber dan tujuan aliran harus berbeda.")

        adjacency: dict[str, list[ResidualEdge]] = {}
        forward_edges: list[tuple[str, int]] = []
        for arc in arcs:
            if math.isnan(arc.capacity) or arc.capacity < 0:
                raise ValueError("Kapasitas edge harus berupa angka non-negatif.")
            adjacency.setdefault(arc.start, [])
            adjacency.setdefault(arc.end, [])
            forward_index = len(adjacency[arc.start])
            reverse_index = len(adjacency[arc.end])
            adjacency[arc.start].append(
                ResidualEdge(arc.end, reverse_index, arc.capacity)
            )
            adjacency[arc.end].append(
                ResidualEdge(arc.start, forward_index, 0.0)
            )
            forward_edges.append((arc.start, forward_index))

        adjacency.setdefault(source, [])
        adjacency.setdefault(sink, [])
        return adjacency, forward_edges

    @staticmethod
    def _augment(
        adjacency: dict[str, list[ResidualEdge]],
        start: str,
        edge_index: int,
        amount: float,
    ) -> None:
        edge = adjacency[start][edge_index]
        edge.capacity -= amount
        adjacency[edge.target][edge.reverse_index].capacity += amount

    @staticmethod
    def _result(
        adjacency: dict[str, list[ResidualEdge]],
        forward_edges: list[tuple[str, int]],
        arcs: Sequence[FlowArc],
        source: str,
        max_flow: float,
        augmentations: int,
    ) -> FlowResult:
        reachable = {source}
        queue = deque([source])
        while queue:
            current = queue.popleft()
            for edge in adjacency[current]:
                if edge.capacity > EPSILON and edge.target not in reachable:
                    reachable.add(edge.target)
                    queue.append(edge.target)

        flows = tuple(
            adjacency[adjacency[start][index].target][
                adjacency[start][index].reverse_index
            ].capacity
            for start, index in forward_edges
        )
        min_cut = tuple(
            index
            for index, arc in enumerate(arcs)
            if arc.capacity > EPSILON
            and arc.start in reachable
            and arc.end not in reachable
        )
        return FlowResult(
            max_flow=max_flow,
            arc_flows=flows,
            source_partition=frozenset(reachable),
            min_cut=min_cut,
            augmentations=augmentations,
        )

    @abstractmethod
    def run(
        self, source: str, sink: str, arcs: Sequence[FlowArc]
    ) -> FlowResult:
        """Compute a maximum flow and return the corresponding residual cut."""
