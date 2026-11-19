from collections import deque
from typing import Sequence

from core.base_algorithm import BaseGraphAlgorithm, EPSILON, FlowResult, ResidualEdge
from core.flow_model import FlowArc


def new_stats() -> dict[str, int]:
    """Counter kerja algoritma (tidak bergantung kecepatan mesin)."""
    return {"phases": 0, "augmentations": 0, "edge_scans": 0}


def dinic_augment(
    graph: dict[str, list[ResidualEdge]],
    source: str,
    sink: str,
    limit: float = float("inf"),
    stats: dict[str, int] | None = None,
) -> float:
    """Jalankan fase-fase Dinic pada graf residual yang sudah ada.

    Setiap fase: (1) BFS membangun *level graph* dari ``source``;
    (2) DFS dengan pointer ``next_edge`` mengirim *blocking flow* hanya
    lewat edge level[v] == level[u] + 1. Berhenti jika ``sink`` tidak lagi
    terjangkau atau total aliran mencapai ``limit``. Graf residual diubah
    di tempat sehingga fungsi ini juga dapat dipakai untuk *warm start*.
    """
    if stats is None:
        stats = new_stats()
    pushed = 0.0
    while pushed < limit - EPSILON:
        level = {node: -1 for node in graph}
        level[source] = 0
        queue = deque([source])
        while queue:
            node = queue.popleft()
            for edge in graph[node]:
                stats["edge_scans"] += 1
                if edge.capacity > EPSILON and level[edge.target] < 0:
                    level[edge.target] = level[node] + 1
                    queue.append(edge.target)
        if level[sink] < 0:
            break
        stats["phases"] += 1

        next_edge = {node: 0 for node in graph}

        def send(node: str, available: float) -> float:
            if node == sink:
                return available
            while next_edge[node] < len(graph[node]):
                index = next_edge[node]
                edge = graph[node][index]
                stats["edge_scans"] += 1
                if edge.capacity > EPSILON and level[edge.target] == level[node] + 1:
                    sent = send(edge.target, min(available, edge.capacity))
                    if sent > EPSILON:
                        BaseGraphAlgorithm._augment(graph, node, index, sent)
                        return sent
                next_edge[node] += 1
            return 0.0

        while pushed < limit - EPSILON:
            amount = send(source, limit - pushed)
            if amount <= EPSILON:
                break
            pushed += amount
            stats["augmentations"] += 1
    return pushed


class Dinic(BaseGraphAlgorithm):
    def run(
        self, source: str, sink: str, arcs: Sequence[FlowArc]
    ) -> FlowResult:
        graph, forward_edges = self._initialize(arcs, source, sink)
        self.stats = new_stats()
        max_flow = dinic_augment(graph, source, sink, stats=self.stats)
        return self._result(
            graph, forward_edges, arcs, source, max_flow, self.stats["augmentations"]
        )
