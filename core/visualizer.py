from html import escape

import folium

from core.flow_model import edge_capacity
from core.graph_model import FlowParameters, GraphModel
from core.simulation_runner import ScenarioResult


BASE_EDGE_COLORS = {
    "konvoi": "#d9481e",
    "asia_afrika": "#555555",
    "jaringan": "#2563eb",
}
NODE_COLORS = {
    "Pintu masuk": "darkred",
    "Kantong parkir": "green",
    "Gmaps": "blue",
    "Simpul koridor": "cadetblue",
}


def _format(value: float) -> str:
    return f"{value:,.0f}"


def _edge_color(index: int, edge_type: str, result: ScenarioResult | None) -> str:
    if result is None:
        return BASE_EDGE_COLORS[edge_type]
    flow = result.edge_results.get(index, {}).get("flow", 0.0)
    capacity = result.edge_results.get(index, {}).get("capacity", 0.0)
    if capacity <= 0 or flow <= 0:
        return "#94a3b8"
    utilization = flow / capacity
    if utilization >= 0.99:
        return "#dc2626"
    if utilization >= 0.5:
        return "#f59e0b"
    return "#16a34a"


def build_map(
    graph: GraphModel,
    parameters: FlowParameters,
    result: ScenarioResult | None = None,
) -> folium.Map:
    graph.validate()
    center = [-6.9195, 107.6095]
    if graph.nodes:
        center = [
            sum(node.lat for node in graph.nodes.values()) / len(graph.nodes),
            sum(node.lon for node in graph.nodes.values()) / len(graph.nodes),
        ]
    map_view = folium.Map(location=center, zoom_start=14, control_scale=True)

    for index, edge in enumerate(graph.edges):
        start = graph.nodes[edge.u]
        end = graph.nodes[edge.v]
        safe_start = escape(edge.u)
        safe_end = escape(edge.v)
        capacity = (
            result.edge_results.get(index, {}).get("capacity", 0.0)
            if result
            else edge_capacity(edge, parameters, parameters.scen)
        )
        flow = result.edge_results.get(index, {}).get("flow", 0.0) if result else 0.0
        popup = (
            f"<b>{safe_start} → {safe_end}</b><br>"
            f"{edge.type}, {'satu arah' if edge.dir == 'one' else 'dua arah'}<br>"
            f"Kapasitas ({result.scenario if result else 'pilih skenario'}): "
            f"{_format(capacity)} kendaraan/jam"
        )
        if result:
            popup += f"<br>Aliran: {_format(flow)} kendaraan/jam"
        if edge.flow:
            folium.PolyLine(
                locations=[(start.lat, start.lon), (end.lat, end.lon)],
                color=_edge_color(index, edge.type, result),
                weight=5 if edge.type == "asia_afrika" else 3,
                opacity=0.9,
                dash_array="10, 8" if edge.type == "konvoi" else None,
                tooltip=f"{safe_start} → {safe_end}",
                popup=folium.Popup(popup, max_width=320),
            ).add_to(map_view)
        else:
            folium.PolyLine(
                locations=[(start.lat, start.lon), (end.lat, end.lon)],
                color="#94a3b8",
                weight=2,
                opacity=0.5,
                dash_array="3, 8",
                tooltip=f"{safe_start} → {safe_end} (tidak dihitung)",
                popup=folium.Popup(popup, max_width=320),
            ).add_to(map_view)

    for key, node in graph.nodes.items():
        safe_key = escape(key)
        safe_name = escape(node.nama)
        details = (
            f"<b>{safe_key} — {safe_name}</b><br>{node.jenis}"
            f"<br>Koordinat: {node.lat:.6f}, {node.lon:.6f}"
        )
        if node.pcap is not None:
            details += f"<br>Kapasitas parkir: {_format(node.pcap)} kendaraan/jam"
        if node.macet:
            details += "<br>Titik macet dilaporkan"
        folium.Marker(
            location=(node.lat, node.lon),
            tooltip=f"{safe_key}: {safe_name}",
            popup=folium.Popup(details, max_width=320),
            icon=folium.Icon(
                color=NODE_COLORS[node.jenis],
                icon="info-sign",
            ),
        ).add_to(map_view)

    folium.LayerControl().add_to(map_view)
    return map_view
