from collections import deque
from typing import Sequence

from core.base_algorithm import BaseGraphAlgorithm, EPSILON, FlowResult
from core.flow_model import FlowArc


class Dinic(BaseGraphAlgorithm):
    def run(
        self, source: str, sink: str, arcs: Sequence[FlowArc]
    ) -> FlowResult:
        graph, forward_edges = self._initialize(arcs, source, sink)
        max_flow = 0.0
        augmentations = 0

        while True:
            level = {node: -1 for node in graph}
            level[source] = 0
            queue = deque([source])
            while queue:
                node = queue.popleft()
                for edge in graph[node]:
                    if edge.capacity > EPSILON and level[edge.target] < 0:
                        level[edge.target] = level[node] + 1
                        queue.append(edge.target)
            if level[sink] < 0:
                break

            next_edge = {node: 0 for node in graph}

            def send(node: str, available: float) -> float:
                if node == sink:
                    return available
                while next_edge[node] < len(graph[node]):
                    index = next_edge[node]
                    edge = graph[node][index]
                    if edge.capacity > EPSILON and level[edge.target] == level[node] + 1:
                        sent = send(edge.target, min(available, edge.capacity))
                        if sent > EPSILON:
                            self._augment(graph, node, index, sent)
                            return sent
                    next_edge[node] += 1
                return 0.0

            while True:
                amount = send(source, float("inf"))
                if amount <= EPSILON:
                    break
                max_flow += amount
                augmentations += 1

        return self._result(
            graph, forward_edges, arcs, source, max_flow, augmentations
        )
