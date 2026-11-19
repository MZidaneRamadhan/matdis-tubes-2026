from collections import deque
from typing import Sequence

from core.base_algorithm import BaseGraphAlgorithm, EPSILON, FlowResult
from core.flow_model import FlowArc


class PushRelabel(BaseGraphAlgorithm):
    def run(
        self, source: str, sink: str, arcs: Sequence[FlowArc]
    ) -> FlowResult:
        graph, forward_edges = self._initialize(arcs, source, sink)
        height = {node: 0 for node in graph}
        excess = {node: 0.0 for node in graph}
        height[source] = len(graph)

        active = deque()
        queued: set[str] = set()
        for index, edge in enumerate(graph[source]):
            if edge.capacity <= EPSILON:
                continue
            amount = edge.capacity
            self._augment(graph, source, index, amount)
            excess[edge.target] += amount
            excess[source] -= amount
            if edge.target not in (source, sink) and edge.target not in queued:
                active.append(edge.target)
                queued.add(edge.target)

        while active:
            node = active.popleft()
            queued.discard(node)
            while excess[node] > EPSILON:
                admissible = next(
                    (
                        index
                        for index, edge in enumerate(graph[node])
                        if edge.capacity > EPSILON
                        and height[node] == height[edge.target] + 1
                    ),
                    None,
                )
                if admissible is None:
                    reachable_heights = [
                        height[edge.target]
                        for edge in graph[node]
                        if edge.capacity > EPSILON
                    ]
                    if not reachable_heights:
                        raise RuntimeError(
                            f"Aliran berlebih di node {node!r} tidak dapat dikembalikan."
                        )
                    height[node] = min(reachable_heights) + 1
                    continue

                edge = graph[node][admissible]
                amount = min(excess[node], edge.capacity)
                was_inactive = excess[edge.target] <= EPSILON
                self._augment(graph, node, admissible, amount)
                excess[node] -= amount
                excess[edge.target] += amount
                if (
                    was_inactive
                    and edge.target not in (source, sink)
                    and edge.target not in queued
                ):
                    active.append(edge.target)
                    queued.add(edge.target)

            if excess[node] > EPSILON and node not in queued:
                active.append(node)
                queued.add(node)

        return self._result(
            graph, forward_edges, arcs, source, excess[sink], 0
        )