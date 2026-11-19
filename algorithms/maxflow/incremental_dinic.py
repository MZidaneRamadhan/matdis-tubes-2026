"""Dinic dengan *warm start* untuk graf dinamis.

Algoritma klasik (Ford-Fulkerson/Edmonds-Karp) dan Dinic biasa harus
menghitung ulang dari aliran nol setiap kali kapasitas jalan berubah.
``IncrementalDinic`` menyimpan graf residual hasil langkah waktu sebelumnya
lalu hanya memperbaiki bagian yang terdampak:

1. Kapasitas arc naik / turun tetapi masih >= aliran lama
   -> cukup ubah sisa kapasitas residual (tidak ada aliran yang rusak).
2. Kapasitas arc turun di bawah aliran lama (``f > c'``)
   -> aliran dipangkas ke ``c'`` sehingga muncul kelebihan ``delta`` di
      ujung awal ``u`` dan kekurangan ``delta`` di ujung akhir ``v``.
   a. *Reroute*: coba kirim ``delta`` dari ``u`` ke ``v`` lewat jalan lain
      (fase Dinic terbatas ``limit = delta``).
   b. Sisa yang tidak bisa dialihkan dikembalikan: ``u -> S0`` dan
      ``T -> v`` (membatalkan aliran lewat arc balik residual).
3. Lanjutkan fase Dinic biasa ``S0 -> T`` pada graf residual yang sudah
   konsisten untuk mengisi kapasitas yang baru terbuka.

Karena hasil akhir adalah aliran layak tanpa *augmenting path*, menurut
teorema Max-Flow Min-Cut hasilnya tetap **optimum global**.
"""

from typing import Sequence

from algorithms.maxflow.dinic import dinic_augment, new_stats
from core.base_algorithm import BaseGraphAlgorithm, EPSILON, FlowResult
from core.flow_model import FlowArc


class IncrementalDinic(BaseGraphAlgorithm):
    def __init__(self, graph_model=None):
        super().__init__(graph_model)
        self.graph = None
        self.forward_edges: list[tuple[str, int]] = []
        self.arcs: list[FlowArc] = []
        self.source = ""
        self.sink = ""
        self.stats = new_stats()

    # ------------------------------------------------------------------ cold
    def run(self, source: str, sink: str, arcs: Sequence[FlowArc]) -> FlowResult:
        """Hitung dari nol (sama dengan Dinic biasa) dan simpan state."""
        self.source, self.sink = source, sink
        self.arcs = list(arcs)
        self.graph, self.forward_edges = self._initialize(self.arcs, source, sink)
        self.stats = new_stats()
        self.stats.update({"arcs_changed": 0, "overflow_arcs": 0, "rerouted": 0.0, "cancelled": 0.0})
        dinic_augment(self.graph, source, sink, stats=self.stats)
        return self._build_result()

    # ------------------------------------------------------------------ warm
    def update(self, arcs: Sequence[FlowArc]) -> FlowResult:
        """Terapkan kapasitas baru pada struktur arc yang sama secara inkremental."""
        new_arcs = list(arcs)
        if self.graph is None or not self._same_structure(new_arcs):
            return self.run(self.source or "S0", self.sink or "T", new_arcs)

        graph = self.graph
        self.stats = new_stats()
        self.stats.update({"arcs_changed": 0, "overflow_arcs": 0, "rerouted": 0.0, "cancelled": 0.0})
        overflows: list[tuple[str, str, float]] = []

        # Langkah 1-2: sesuaikan kapasitas residual arc yang berubah.
        for index, (old, new) in enumerate(zip(self.arcs, new_arcs)):
            if abs(old.capacity - new.capacity) <= EPSILON or old.capacity == new.capacity:
                continue
            self.stats["arcs_changed"] += 1
            start, edge_index = self.forward_edges[index]
            edge = graph[start][edge_index]
            reverse = graph[edge.target][edge.reverse_index]
            flow = reverse.capacity
            if new.capacity >= flow - EPSILON:
                edge.capacity = max(0.0, new.capacity - flow)
            else:
                overflow = flow - new.capacity
                edge.capacity = 0.0
                reverse.capacity = new.capacity
                overflows.append((new.start, new.end, overflow))
                self.stats["overflow_arcs"] += 1
        self.arcs = new_arcs

        # Langkah 2a-2b: perbaiki konservasi aliran di sekitar arc yang meluap.
        for u, v, overflow in overflows:
            rerouted = dinic_augment(graph, u, v, limit=overflow, stats=self.stats)
            self.stats["rerouted"] += rerouted
            remaining = overflow - rerouted
            if remaining <= EPSILON:
                continue
            self.stats["cancelled"] += remaining
            if u != self.source:
                back = dinic_augment(graph, u, self.source, limit=remaining, stats=self.stats)
                if back < remaining - 1e-6:
                    raise RuntimeError(f"Gagal mengembalikan kelebihan aliran dari {u!r}.")
            if v != self.sink:
                forward = dinic_augment(graph, self.sink, v, limit=remaining, stats=self.stats)
                if forward < remaining - 1e-6:
                    raise RuntimeError(f"Gagal menutup kekurangan aliran di {v!r}.")

        # Langkah 3: lanjutkan Dinic S0 -> T dari aliran yang tersisa.
        dinic_augment(graph, self.source, self.sink, stats=self.stats)
        return self._build_result()

    # --------------------------------------------------------------- helpers
    def _same_structure(self, new_arcs: list[FlowArc]) -> bool:
        return len(new_arcs) == len(self.arcs) and all(
            (a.start, a.end) == (b.start, b.end) for a, b in zip(self.arcs, new_arcs)
        )

    def _current_value(self) -> float:
        value = 0.0
        for arc, (start, index) in zip(self.arcs, self.forward_edges):
            edge = self.graph[start][index]
            flow = self.graph[edge.target][edge.reverse_index].capacity
            if arc.end == self.sink:
                value += flow
            elif arc.start == self.sink:
                value -= flow
        return value

    def _build_result(self) -> FlowResult:
        return self._result(
            self.graph,
            self.forward_edges,
            self.arcs,
            self.source,
            self._current_value(),
            self.stats["augmentations"],
        )
