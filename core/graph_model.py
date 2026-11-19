from dataclasses import asdict, dataclass, field
import math
from typing import Any


NODE_TYPES = ("Simpul koridor", "Pintu masuk", "Kantong parkir", "Gmaps")
EDGE_TYPES = ("konvoi", "asia_afrika", "jaringan")
EDGE_DIRECTIONS = ("one", "two")


@dataclass
class GraphNode:
    lat: float
    lon: float
    nama: str
    jenis: str
    macet: bool = False
    pcap: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphNode":
        if not isinstance(data, dict):
            raise ValueError("Data node harus berupa objek.")
        node = cls(
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            nama=str(data["nama"]),
            jenis=str(data["jenis"]),
            macet=bool(data.get("macet", False)),
            pcap=None if data.get("pcap") in (None, "") else float(data["pcap"]),
        )
        if not math.isfinite(node.lat) or not -90 <= node.lat <= 90:
            raise ValueError("Latitude node harus berada di antara -90 dan 90.")
        if not math.isfinite(node.lon) or not -180 <= node.lon <= 180:
            raise ValueError("Longitude node harus berada di antara -180 dan 180.")
        if node.jenis not in NODE_TYPES:
            raise ValueError(f"Jenis node tidak dikenal: {node.jenis!r}.")
        if node.pcap is not None and (not math.isfinite(node.pcap) or node.pcap < 0):
            raise ValueError("Kapasitas parkir harus berupa angka non-negatif.")
        return node


@dataclass
class GraphEdge:
    u: str
    v: str
    type: str = "jaringan"
    dir: str = "two"
    lanes: float = 2
    w: float | None = None
    fc: float = 1
    man: float | None = None
    bg: float = 0
    hit: bool = False
    flow: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphEdge":
        if not isinstance(data, dict):
            raise ValueError("Data edge harus berupa objek.")
        edge = cls(
            u=str(data["u"]),
            v=str(data["v"]),
            type=str(data.get("type", "jaringan")),
            dir=str(data.get("dir", "two")),
            lanes=float(data.get("lanes", 2)),
            w=None if data.get("w") in (None, "") else float(data["w"]),
            fc=float(data.get("fc", 1)),
            man=None if data.get("man") in (None, "") else float(data["man"]),
            bg=float(data.get("bg", 0)),
            hit=bool(data.get("hit", False)),
            flow=bool(data.get("flow", True)),
        )
        if edge.u == edge.v:
            raise ValueError("Sebuah edge tidak dapat menghubungkan node ke dirinya sendiri.")
        if edge.type not in EDGE_TYPES:
            raise ValueError(f"Jenis edge tidak dikenal: {edge.type!r}.")
        if edge.dir not in EDGE_DIRECTIONS:
            raise ValueError("Arah edge harus 'one' atau 'two'.")
        for name, value in (
            ("jumlah lajur", edge.lanes),
            ("faktor lajur", edge.fc),
            ("beban dasar", edge.bg),
        ):
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name.capitalize()} harus berupa angka non-negatif.")
        for name, value in (("lebar jalan", edge.w), ("kapasitas manual", edge.man)):
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError(f"{name.capitalize()} harus berupa angka non-negatif.")
        return edge


@dataclass
class FlowParameters:
    c0: float = 1700
    fc: float = 1
    smp: float = 1
    Q: float = 5000
    red: float = 0.4
    bg: bool = True
    scen: str = "konvoi"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FlowParameters":
        if not isinstance(data, dict):
            raise ValueError("Parameter model harus berupa objek.")
        result = cls(
            c0=float(data.get("c0", 1700)),
            fc=float(data.get("fc", 1)),
            smp=float(data.get("smp", 1)),
            Q=float(data.get("Q", 5000)),
            red=float(data.get("red", 0.4)),
            bg=bool(data.get("bg", True)),
            scen=str(data.get("scen", "konvoi")),
        )
        for name, value in (("c0", result.c0), ("fc", result.fc), ("smp", result.smp)):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"Parameter {name} harus berupa angka lebih besar dari 0.")
        if not math.isfinite(result.Q) or result.Q < 0:
            raise ValueError("Demand Q harus berupa angka non-negatif.")
        if not 0 <= result.red <= 1:
            raise ValueError("Reduksi kapasitas harus berada di antara 0 dan 1.")
        if result.scen not in ("normal", "konvoi"):
            raise ValueError("Skenario harus 'normal' atau 'konvoi'.")
        return result


@dataclass
class GraphModel:
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    def validate(self) -> None:
        if not self.nodes:
            raise ValueError("Graf harus memiliki setidaknya satu node.")
        for edge in self.edges:
            if edge.u not in self.nodes or edge.v not in self.nodes:
                raise ValueError(f"Edge {edge.u!r} -> {edge.v!r} merujuk node yang tidak ada.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": {key: asdict(node) for key, node in self.nodes.items()},
            "edges": [asdict(edge) for edge in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphModel":
        if not isinstance(data, dict):
            raise ValueError("Data graf harus berupa objek.")
        raw_nodes = data.get("nodes")
        if isinstance(raw_nodes, list):
            nodes = {}
            for item in raw_nodes:
                if not isinstance(item, dict) or "id" not in item:
                    raise ValueError("Setiap node pada daftar harus memiliki kode 'id'.")
                key = str(item["id"])
                if key in nodes:
                    raise ValueError(f"Kode node duplikat: {key!r}.")
                nodes[key] = GraphNode.from_dict(item)
        elif isinstance(raw_nodes, dict):
            nodes = {}
            for raw_key, item in raw_nodes.items():
                key = str(raw_key)
                if key in nodes:
                    raise ValueError(f"Kode node duplikat: {key!r}.")
                nodes[key] = GraphNode.from_dict(item)
        else:
            raise ValueError("Data graf harus memiliki objek atau daftar 'nodes'.")
        for key, node in nodes.items():
            if node.jenis == "Kantong parkir" and node.pcap is None:
                node.pcap = 300
        raw_edges = data.get("edges")
        if not isinstance(raw_edges, list):
            raise ValueError("Data graf harus memiliki daftar 'edges'.")
        edges = []
        for item in raw_edges:
            if not isinstance(item, dict):
                raise ValueError("Setiap edge pada daftar harus berupa objek.")
            edge_data = item.copy()
            if "hit" not in edge_data:
                start_node = nodes.get(str(edge_data.get("u")))
                end_node = nodes.get(str(edge_data.get("v")))
                edge_data["hit"] = bool(
                    (start_node and start_node.macet)
                    or (end_node and end_node.macet)
                )
            edges.append(GraphEdge.from_dict(edge_data))
        graph = cls(nodes=nodes, edges=edges)
        graph.validate()
        return graph
