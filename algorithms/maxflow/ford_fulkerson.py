from collections import deque
from typing import Sequence

from core.base_algorithm import BaseGraphAlgorithm, EPSILON, FlowResult
from core.flow_model import FlowArc


class FordFulkerson(BaseGraphAlgorithm):
    """Ford-Fulkerson dengan pencarian augmenting path menggunakan BFS."""

    def run(
        self, source: str, sink: str, arcs: Sequence[FlowArc]
    ) -> FlowResult:
        graph, forward_edges = self._initialize(arcs, source, sink)
        max_flow = 0.0
        augmentations = 0
        # phases = jumlah BFS (satu BFS untuk setiap augmenting path + 1 BFS terakhir)
        self.stats = {"phases": 0, "augmentations": 0, "edge_scans": 0}

        while True:
            self.stats["phases"] += 1
            parent: dict[str, tuple[str, int]] = {}
            visited = {source}
            queue = deque([source])
            while queue and sink not in visited:
                node = queue.popleft()
                for index, edge in enumerate(graph[node]):
                    self.stats["edge_scans"] += 1
                    if edge.capacity > EPSILON and edge.target not in visited:
                        visited.add(edge.target)
                        parent[edge.target] = (node, index)
                        queue.append(edge.target)
                        if edge.target == sink:
                            break
            if sink not in visited:
                break

            path: list[tuple[str, int]] = []
            node = sink
            amount = float("inf")
            while node != source:
                previous, index = parent[node]
                path.append((previous, index))
                amount = min(amount, graph[previous][index].capacity)
                node = previous

            for previous, index in path:
                self._augment(graph, previous, index, amount)
            max_flow += amount
            augmentations += 1

        self.stats["augmentations"] = augmentations
        return self._result(
            graph, forward_edges, arcs, source, max_flow, augmentations
        )
