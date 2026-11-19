import csv
from dataclasses import asdict
import io
import json

import streamlit as st
from streamlit_folium import st_folium

from algorithms import AlgorithmRegistry
from cases.scenario_loader import load_scenario
from config.settings import DEFAULT_SCENARIO
from core.flow_model import build_flow_arcs, edge_capacity
from core.graph_model import (
    EDGE_TYPES,
    FlowParameters,
    GraphEdge,
    GraphModel,
    GraphNode,
    NODE_TYPES,
)
from core.simulation_runner import (
    ScenarioResult,
    compare_algorithms,
    solve_both_scenarios,
)
from core.visualizer import build_map


def _clear_results() -> None:
    st.session_state.results = None
    st.session_state.comparison = None


def _initialize_state() -> None:
    if "graph" not in st.session_state:
        scenario = load_scenario(DEFAULT_SCENARIO)
        st.session_state.graph = scenario.graph
        st.session_state.parameters = scenario.parameters
        st.session_state.results = None
        st.session_state.comparison = None
        st.session_state.map_click = None
        st.session_state.map_location_version = 0
        st.session_state.algorithm = "dinic"


def _add_node(
    graph: GraphModel,
    key: str,
    name: str,
    kind: str,
    lat: float,
    lon: float,
    congested: bool,
    parking_capacity: float,
) -> None:
    key = key.strip().upper()
    if not key or key in graph.nodes:
        raise ValueError("Kode node wajib diisi dan harus unik.")
    node_data = {
        "lat": lat,
        "lon": lon,
        "nama": name.strip() or key,
        "jenis": kind,
        "macet": congested,
        "pcap": parking_capacity if kind == "Kantong parkir" else None,
    }
    graph.nodes[key] = GraphNode.from_dict(node_data)
    graph.validate()


def _export_json(graph: GraphModel, parameters: FlowParameters) -> str:
    graph_data = graph.to_dict()
    return json.dumps(
        {
            "nodes": graph_data["nodes"],
            "edges": graph_data["edges"],
            "p": asdict(parameters),
        },
        ensure_ascii=False,
        indent=2,
    )


def _export_csv(
    graph: GraphModel,
    parameters: FlowParameters,
    export_type: str,
) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    if export_type == "nodes":
        writer.writerow(
            ["Kode", "Nama", "Latitude", "Longitude", "Jenis", "Titik_Macet",
             "Laju_Masuk_Parkir"]
        )
        for key, node in graph.nodes.items():
            writer.writerow(
                [key, node.nama, node.lat, node.lon, node.jenis, node.macet, node.pcap]
            )
    elif export_type == "edges":
        writer.writerow(
            ["From", "To", "Jenis", "Arah", "Lajur_per_arah", "Lebar_m", "FCLJ",
             "Kapasitas_manual", "Beban_dasar", "Terdampak", "Ikut_aliran",
             "Kap_normal", "Kap_konvoi"]
        )
        for edge in graph.edges:
            writer.writerow(
                [
                    edge.u,
                    edge.v,
                    edge.type,
                    edge.dir,
                    edge.lanes,
                    edge.w,
                    edge.fc,
                    edge.man,
                    edge.bg,
                    edge.hit,
                    edge.flow,
                    edge_capacity(edge, parameters, "normal"),
                    edge_capacity(edge, parameters, "konvoi"),
                ]
            )
    elif export_type == "arcs":
        writer.writerow(["Skenario", "From", "To", "Kapasitas", "Jenis"])
        for scenario in ("normal", "konvoi"):
            for arc in build_flow_arcs(graph, parameters, scenario):
                writer.writerow(
                    [
                        scenario,
                        arc.start,
                        arc.end,
                        "INF" if arc.capacity == float("inf") else arc.capacity,
                        arc.kind,
                    ]
                )
    else:
        raise ValueError(f"Jenis ekspor CSV tidak dikenal: {export_type}")
    return output.getvalue()


def _render_results(
    results: dict[str, ScenarioResult],
    selected: str,
    comparison: dict[str, dict[str, ScenarioResult]] | None = None,
) -> None:
    st.subheader("Hasil max-flow")
    columns = st.columns(2)
    for column, scenario in zip(columns, ("normal", "konvoi")):
        result = results[scenario]
        with column:
            st.metric(
                f"Max-flow — {scenario.capitalize()}",
                f"{result.flow_result.max_flow:,.0f} kendaraan/jam",
                help=f"Demand yang belum tertampung: {result.unserved:,.0f} kendaraan/jam",
            )
            st.caption(
                f"Belum tertampung: {result.unserved:,.0f} · "
                f"Kapasitas parkir: {result.parking_capacity:,.0f}"
            )

    if not comparison:
        return

    st.markdown(f"**Perbandingan algoritma max-flow (skenario: {selected})**")
    comp_rows = []
    for label, algo_key in (
        ("Ford-Fulkerson (Basic)", "Ford-Fulkerson"),
        ("Dinic's Algorithm (Advance)", "Dinic"),
    ):
        res_norm = comparison[algo_key]["normal"]
        res_konv = comparison[algo_key]["konvoi"]
        res_sel = comparison[algo_key][selected]
        stats = res_sel.stats
        comp_rows.append(
            {
                "Algoritma": label,
                "Max-Flow Normal (kend/jam)": f"{res_norm.flow_result.max_flow:,.0f}",
                "Max-Flow Konvoi (kend/jam)": f"{res_konv.flow_result.max_flow:,.0f}",
                "Belum Tertampung (kend/jam)": f"{res_sel.unserved:,.0f}",
                "Fase BFS": stats.get("phases", "-"),
                "Augmenting Path": stats.get(
                    "augmentations", res_sel.flow_result.augmentations
                ),
                "Edge Scan": stats.get("edge_scans", "-"),
                "Waktu Eksekusi (ms)": f"{res_sel.elapsed_ms:.4f}",
            }
        )
    st.dataframe(comp_rows, width="stretch", hide_index=True)

    ff_sel = comparison["Ford-Fulkerson"][selected]
    dn_sel = comparison["Dinic"][selected]
    edge_rows = []
    for index, edge in enumerate(st.session_state.graph.edges):
        if not edge.flow:
            continue
        ff_flow = ff_sel.edge_results.get(index, {}).get("flow", 0.0)
        dn_flow = dn_sel.edge_results.get(index, {}).get("flow", 0.0)
        cap = dn_sel.edge_results.get(index, {}).get("capacity", 0.0)
        if ff_flow <= 0 and dn_flow <= 0:
            continue
        edge_rows.append(
            {
                "Ruas Jalan": f"{edge.u} → {edge.v}",
                "Kapasitas (kend/jam)": f"{cap:,.0f}",
                "Aliran Ford-Fulkerson": f"{ff_flow:,.0f}",
                "Aliran Dinic's": f"{dn_flow:,.0f}",
                "Utilisasi (%)": f"{(dn_flow / cap * 100) if cap > 0 else 0:.1f}%",
            }
        )
    if edge_rows:
        with st.expander(
            f"Detail perbandingan aliran per ruas jalan ({selected})",
            expanded=False,
        ):
            st.dataframe(edge_rows, width="stretch", hide_index=True)


def _render_node_editor(graph: GraphModel) -> None:
    st.subheader("Edit node")
    keys = sorted(graph.nodes)
    selected = st.selectbox(
        "Pilih node",
        keys,
        format_func=lambda key: f"{key} — {graph.nodes[key].nama}",
        key="selected_node",
    )
    node = graph.nodes[selected]
    with st.form(f"edit_node_{selected}"):
        name = st.text_input("Nama lokasi", value=node.nama, key=f"node_name_{selected}")
        kind = st.selectbox(
            "Jenis node",
            NODE_TYPES,
            index=NODE_TYPES.index(node.jenis),
            key=f"node_type_{selected}",
        )
        latitude = st.number_input(
            "Latitude",
            value=node.lat,
            format="%.7f",
            key=f"node_lat_{selected}",
        )
        longitude = st.number_input(
            "Longitude",
            value=node.lon,
            format="%.7f",
            key=f"node_lon_{selected}",
        )
        congested = st.checkbox(
            "Titik macet dilaporkan",
            value=node.macet,
            key=f"node_congested_{selected}",
        )
        parking_capacity = st.number_input(
            "Kapasitas parkir (kendaraan/jam)",
            min_value=0.0,
            value=float(node.pcap if node.pcap is not None else 300),
            key=f"node_pcap_{selected}",
            disabled=kind != "Kantong parkir",
        )
        if st.form_submit_button("Simpan node"):
            try:
                updated = GraphNode.from_dict(
                    {
                        "lat": latitude,
                        "lon": longitude,
                        "nama": name,
                        "jenis": kind,
                        "macet": congested,
                        "pcap": parking_capacity if kind == "Kantong parkir" else None,
                    }
                )
                graph.nodes[selected] = updated
                graph.validate()
                _clear_results()
                st.success(f"Node {selected} berhasil diperbarui.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    if len(graph.nodes) == 1:
        st.info("Graf harus memiliki setidaknya satu node.")
    elif st.button("Hapus node dan edge terkait", key=f"delete_node_{selected}"):
        del graph.nodes[selected]
        graph.edges = [
            edge for edge in graph.edges if edge.u != selected and edge.v != selected
        ]
        _clear_results()
        st.rerun()


def _render_add_node(graph: GraphModel) -> None:
    st.subheader("Tambah node dari peta")
    location = st.session_state.map_click
    if location:
        st.caption(f"Lokasi peta: {location[0]:.6f}, {location[1]:.6f}")
    else:
        st.caption("Klik peta untuk memilih koordinat node baru.")

    version = st.session_state.map_location_version
    with st.form("add_node"):
        key = st.text_input("Kode unik", placeholder="Contoh: J11").strip().upper()
        name = st.text_input("Nama lokasi", placeholder="Nama tempat")
        kind = st.selectbox("Jenis node baru", NODE_TYPES, index=0)
        default_lat, default_lon = location or (-6.9195, 107.6095)
        lat = st.number_input(
            "Latitude baru", value=float(default_lat), format="%.7f",
            key=f"new_lat_{version}",
        )
        lon = st.number_input(
            "Longitude baru", value=float(default_lon), format="%.7f",
            key=f"new_lon_{version}",
        )
        congested = st.checkbox("Titik macet", key=f"new_congested_{version}")
        pcap = st.number_input(
            "Kapasitas parkir (kendaraan/jam)",
            min_value=0.0,
            value=300.0,
            disabled=kind != "Kantong parkir",
            key=f"new_pcap_{version}",
        )
        if st.form_submit_button("Tambah node"):
            try:
                _add_node(graph, key, name, kind, lat, lon, congested, pcap)
                st.session_state.map_click = None
                st.session_state.map_location_version += 1
                _clear_results()
                st.success(f"Node {key} berhasil ditambahkan.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def _render_edge_editors(graph: GraphModel) -> None:
    st.subheader("Edit edge")
    if graph.edges:
        edge_labels = {
            index: f"{index + 1}. {edge.u} → {edge.v} ({edge.type})"
            for index, edge in enumerate(graph.edges)
        }
        selected = st.selectbox(
            "Pilih edge",
            list(edge_labels),
            format_func=edge_labels.get,
            key="selected_edge",
        )
        edge = graph.edges[selected]
        node_keys = sorted(graph.nodes)
        with st.form(f"edit_edge_{selected}"):
            col1, col2 = st.columns(2)
            start = col1.selectbox(
                "Dari",
                node_keys,
                index=node_keys.index(edge.u),
                key=f"edge_start_{selected}",
            )
            end = col2.selectbox(
                "Ke",
                node_keys,
                index=node_keys.index(edge.v),
                key=f"edge_end_{selected}",
            )
            direction = st.selectbox(
                "Arah lalu lintas",
                ("one", "two"),
                index=("one", "two").index(edge.dir),
                format_func=lambda value: "Satu arah" if value == "one" else "Dua arah",
                key=f"edge_direction_{selected}",
            )
            edge_type = st.selectbox(
                "Jenis edge",
                EDGE_TYPES,
                index=EDGE_TYPES.index(edge.type),
                key=f"edge_type_{selected}",
            )
            col1, col2 = st.columns(2)
            lanes = col1.number_input(
                "Lajur per arah", min_value=0.0, value=edge.lanes,
                key=f"edge_lanes_{selected}",
            )
            width = col2.number_input(
                "Lebar jalur (m)", min_value=0.0, value=float(edge.w or 0),
                key=f"edge_width_{selected}",
            )
            col1, col2 = st.columns(2)
            lane_factor = col1.number_input(
                "FC lebar lajur", min_value=0.0, value=edge.fc,
                key=f"edge_fc_{selected}",
            )
            manual_capacity_enabled = st.checkbox(
                "Gunakan kapasitas manual",
                value=edge.man is not None,
                key=f"edge_manual_enabled_{selected}",
            )
            manual_capacity = col2.number_input(
                "Kapasitas manual",
                min_value=0.0,
                value=float(edge.man or 0),
                key=f"edge_manual_{selected}",
                disabled=not manual_capacity_enabled,
            )
            base_flow = st.number_input(
                "Beban dasar (kendaraan/jam)",
                min_value=0.0,
                value=edge.bg,
                key=f"edge_bg_{selected}",
            )
            affected = st.checkbox(
                "Terdampak parkir liar atau konvoi",
                value=edge.hit,
                key=f"edge_hit_{selected}",
            )
            included = st.checkbox(
                "Ikut jaringan aliran",
                value=edge.flow,
                key=f"edge_flow_{selected}",
            )
            save_col, del_col = st.columns(2)
            save_edge = save_col.form_submit_button("Simpan edge")
            delete_edge = del_col.form_submit_button("Hapus edge")
        if save_edge:
            try:
                updated = GraphEdge.from_dict(
                    {
                        "u": start,
                        "v": end,
                        "type": edge_type,
                        "dir": direction,
                        "lanes": lanes,
                        "w": width or None,
                        "fc": lane_factor,
                        "man": manual_capacity if manual_capacity_enabled else None,
                        "bg": base_flow,
                        "hit": affected,
                        "flow": included,
                    }
                )
                graph.edges[selected] = updated
                graph.validate()
                _clear_results()
                st.success("Edge berhasil diperbarui.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        elif delete_edge:
            graph.edges.pop(selected)
            _clear_results()
            st.rerun()


def _render_add_edge(graph: GraphModel) -> None:
    st.subheader("Tambah edge")
    node_keys = sorted(graph.nodes)
    if len(node_keys) < 2:
        st.info("Tambahkan setidaknya dua node untuk membuat edge.")
        return
    with st.form("add_edge"):
        col1, col2 = st.columns(2)
        start = col1.selectbox("Dari node", node_keys, key="new_edge_start")
        end = col2.selectbox(
            "Ke node", node_keys, index=min(1, len(node_keys) - 1), key="new_edge_end"
        )
        col1, col2 = st.columns(2)
        direction = col1.selectbox(
            "Arah edge baru",
            ("two", "one"),
            format_func=lambda value: "Dua arah" if value == "two" else "Satu arah",
            key="new_edge_direction",
        )
        edge_type = col2.selectbox("Jenis edge baru", EDGE_TYPES, key="new_edge_type")
        lanes = st.number_input("Lajur per arah baru", min_value=0.0, value=2.0)
        if st.form_submit_button("Tambah edge"):
            try:
                edge = GraphEdge.from_dict(
                    {
                        "u": start,
                        "v": end,
                        "type": edge_type,
                        "dir": direction,
                        "lanes": lanes,
                        "hit": graph.nodes[start].macet or graph.nodes[end].macet,
                    }
                )
                graph.edges.append(edge)
                graph.validate()
                _clear_results()
                st.success(f"Edge {start} → {end} berhasil ditambahkan.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def _render_parameter_editor(parameters: FlowParameters) -> None:
    st.subheader("Parameter model")
    with st.form("model_parameters"):
        col1, col2 = st.columns(2)
        c0 = col1.number_input("C0 per lajur (smp/jam)", min_value=0.01, value=parameters.c0)
        fc = col2.number_input("FC lain", min_value=0.01, value=parameters.fc, step=0.01)
        col1, col2 = st.columns(2)
        smp = col1.number_input("smp per kendaraan", min_value=0.01, value=parameters.smp, step=0.01)
        demand = col2.number_input("Demand Q (kend/jam)", min_value=0.0, value=parameters.Q)
        col1, col2 = st.columns(2)
        reduction = col1.number_input(
            "Reduksi kapasitas konvoi", min_value=0.0, max_value=1.0,
            value=parameters.red, step=0.05,
        )
        scenario = col2.selectbox(
            "Skenario peta",
            ("normal", "konvoi"),
            index=("normal", "konvoi").index(parameters.scen),
        )
        deduct_base = st.checkbox(
            "Kurangi beban dasar lalu lintas", value=parameters.bg
        )
        if st.form_submit_button("Simpan parameter"):
            try:
                updated = FlowParameters.from_dict(
                    {
                        "c0": c0,
                        "fc": fc,
                        "smp": smp,
                        "Q": demand,
                        "red": reduction,
                        "bg": deduct_base,
                        "scen": scenario,
                    }
                )
                st.session_state.parameters = updated
                _clear_results()
                st.success("Parameter berhasil diperbarui.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def main() -> None:
    st.set_page_config(
        page_title="Editor Graf Aliran Asia Afrika",
        page_icon="🗺️",
        layout="wide",
    )
    _initialize_state()
    st.title("Editor graf aliran koridor Asia Afrika")
    st.caption(
        "Aplikasi Python untuk mengedit jaringan jalan dan membandingkan "
        "algoritma max-flow (Ford-Fulkerson vs Dinic's)."
    )
    if st.button("Reset ke data awal"):
        scenario = load_scenario(DEFAULT_SCENARIO)
        st.session_state.graph = scenario.graph
        st.session_state.parameters = scenario.parameters
        st.session_state.results = None
        st.session_state.comparison = None
        st.session_state.map_click = None
        st.session_state.map_location_version += 1
        st.rerun()

    graph: GraphModel = st.session_state.graph
    parameters: FlowParameters = st.session_state.parameters
    algorithm = st.selectbox(
        "Algoritma max-flow (untuk visualisasi peta)",
        ["dinic", "ford_fulkerson"],
        format_func={
            "dinic": "Dinic's Algorithm (Advance)",
            "ford_fulkerson": "Ford-Fulkerson (Basic)",
        }.get,
        key="algorithm",
        on_change=_clear_results,
        help="Pilih algoritma yang ditampilkan pada peta; tombol hitung akan membandingkan keduanya.",
    )
    if st.button("Hitung & bandingkan max-flow", type="primary"):
        try:
            graph.validate()
            comparison = compare_algorithms(
                graph,
                parameters,
                ("Ford-Fulkerson", "Dinic"),
            )
            st.session_state.comparison = comparison
            st.session_state.results = comparison[
                {
                    "dinic": "Dinic",
                    "ford_fulkerson": "Ford-Fulkerson",
                }[algorithm]
            ]
        except (ValueError, RuntimeError) as error:
            st.error(f"Perhitungan gagal: {error}")
            st.session_state.results = None
            st.session_state.comparison = None

    results = st.session_state.results
    if results:
        _render_results(results, parameters.scen, st.session_state.get("comparison"))

    left, right = st.columns([1.55, 1])
    with left:
        st.subheader("Peta jaringan")
        result = results.get(parameters.scen) if results else None
        map_data = st_folium(
            build_map(graph, parameters, result),
            height=540,
            use_container_width=True,
            returned_objects=["last_clicked"],
            key="network_map",
        )
        clicked = map_data.get("last_clicked") if map_data else None
        if clicked:
            location = (float(clicked["lat"]), float(clicked["lng"]))
            if location != st.session_state.map_click:
                st.session_state.map_click = location
                st.session_state.map_location_version += 1
        st.caption("Klik peta untuk memilih lokasi node baru.")
        if result is None:
            st.markdown(
                """
                <div style="display:flex;flex-wrap:wrap;gap:14px;align-items:center;font-size:0.88rem;padding:8px 12px;border-radius:8px;background:rgba(148,163,184,0.12);">
                    <b>Keterangan Garis (Sebelum Dihitung):</b>
                    <span><span style="display:inline-block;width:18px;height:4px;background:#555555;vertical-align:middle;margin-right:6px;"></span>Koridor Asia Afrika</span>
                    <span><span style="display:inline-block;width:18px;height:4px;background:#2563eb;vertical-align:middle;margin-right:6px;"></span>Jaringan jalan penghubung</span>
                    <span><span style="display:inline-block;width:18px;height:0;border-top:3px dashed #d9481e;vertical-align:middle;margin-right:6px;"></span>Jalur rute konvoi</span>
                    <span><span style="display:inline-block;width:18px;height:0;border-top:2px dashed #94a3b8;vertical-align:middle;margin-right:6px;"></span>Tidak ikut jaringan aliran</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="display:flex;flex-wrap:wrap;gap:14px;align-items:center;font-size:0.88rem;padding:8px 12px;border-radius:8px;background:rgba(148,163,184,0.12);">
                    <b>Keterangan Warna Garis (Utilisasi Aliran):</b>
                    <span><span style="display:inline-block;width:18px;height:4px;background:#16a34a;vertical-align:middle;margin-right:6px;"></span><b>Hijau</b>: Lancar (&lt; 50% kapasitas)</span>
                    <span><span style="display:inline-block;width:18px;height:4px;background:#f59e0b;vertical-align:middle;margin-right:6px;"></span><b>Oranye</b>: Padat (50% – 98% kapasitas)</span>
                    <span><span style="display:inline-block;width:18px;height:4px;background:#dc2626;vertical-align:middle;margin-right:6px;"></span><b>Merah</b>: Jenuh / Penuh (≥ 99% kapasitas)</span>
                    <span><span style="display:inline-block;width:18px;height:4px;background:#94a3b8;vertical-align:middle;margin-right:6px;"></span><b>Abu-abu</b>: Tidak dilewati aliran (0 kend/jam)</span>
                    <span><span style="display:inline-block;width:18px;height:0;border-top:3px dashed #64748b;vertical-align:middle;margin-right:6px;"></span><b>Putus-putus</b>: Jalur konvoi / non-aliran</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with right:
        _render_parameter_editor(parameters)

    st.divider()
    row1_left, row1_right = st.columns(2)
    with row1_left:
        _render_node_editor(graph)
    with row1_right:
        _render_add_node(graph)

    row2_left, row2_right = st.columns(2)
    with row2_left:
        _render_edge_editors(graph)
    with row2_right:
        _render_add_edge(graph)

    st.subheader("Impor dan ekspor")
    export_columns = st.columns(4)
    export_columns[0].download_button(
        "JSON graf",
        _export_json(graph, parameters),
        file_name="graf_asia_afrika.json",
        mime="application/json",
    )
    for column, export_type, label, filename in (
        (export_columns[1], "nodes", "CSV node", "node_graf_asia_afrika.csv"),
        (export_columns[2], "edges", "CSV edge", "edge_graf_asia_afrika.csv"),
        (export_columns[3], "arcs", "CSV jaringan aliran", "jaringan_aliran.csv"),
    ):
        column.download_button(
            label,
            _export_csv(graph, parameters, export_type),
            file_name=filename,
            mime="text/csv",
        )

    uploaded = st.file_uploader("Impor JSON graf", type=["json"])
    if uploaded and st.button("Muat graf JSON", key="load_json"):
        try:
            data = json.loads(uploaded.getvalue())
            if not isinstance(data, dict):
                raise ValueError("Isi file JSON harus berupa objek.")
            imported_graph = GraphModel.from_dict(data)
            imported_parameters = FlowParameters.from_dict(data.get("p") or {})
            st.session_state.graph = imported_graph
            st.session_state.parameters = imported_parameters
            st.session_state.results = None
            st.session_state.map_click = None
            st.session_state.map_location_version += 1
            st.success("Graf JSON berhasil dimuat.")
            st.rerun()
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as error:
            st.error(f"File JSON tidak valid: {error}")


if __name__ == "__main__":
    main()
