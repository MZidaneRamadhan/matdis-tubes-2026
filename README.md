# Editor Graf Aliran Asia Afrika

Aplikasi Python interaktif untuk mengedit jaringan jalan koridor Asia Afrika
Bandung dan menganalisis **maximum flow** serta **minimum cut** kendaraan.
Data awal peta berasal dari editor HTML yang menjadi sumber proyek; data
tersebut sekarang tersimpan sebagai skenario YAML dan diproses oleh modul
Python terpisah.

## Menjalankan aplikasi

Gunakan Python 3.10 atau lebih baru. Dari PowerShell pada direktori proyek:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run scripts/run_simulation.py
```

Aplikasi terbuka di browser. Peta menggunakan tile OpenStreetMap melalui
Folium, jadi koneksi internet diperlukan untuk menampilkan latar peta.

## Fitur

- Peta interaktif dengan node dan edge jaringan Asia Afrika.
- Tambah node dengan memilih lokasi melalui klik peta; edit atau hapus node.
- Tambah, edit arah, dan hapus edge; pilih edge satu arah atau dua arah.
- Atur kapasitas parkir, parameter model, dan faktor pengurangan kapasitas
  konvoi.
- Hitung max-flow dan min-cut untuk kondisi normal dan konvoi. Algoritma yang
  tersedia: Dinic, Ford-Fulkerson (BFS), dan Push-Relabel.
- Tampilkan kapasitas/aliran pada ruas serta node parkir yang termasuk
  min-cut.
- Impor/ekspor graf JSON dan ekspor node, edge, atau jaringan aliran ke CSV.
- Kembalikan graf ke data awal melalui tombol **Reset ke data awal**.

Perubahan graf tersimpan pada sesi aplikasi. Unduh JSON untuk menyimpan
perubahan dan impor kembali berkas tersebut pada sesi berikutnya.

## Parameter dan asumsi kapasitas

Kapasitas edge dihitung dengan rumus:

```text
kapasitas = jumlah lajur × C0 × FC edge × FC model / smp per kendaraan
```

Kapasitas manual pada edge menggantikan hasil rumus. Untuk skenario konvoi,
kapasitas edge yang terdampak dikalikan `(1 - reduksi konvoi)`. Jika pilihan
pengurangan beban dasar aktif, beban dasar dikurangi dari kapasitas. Nilai
akhir dibatasi minimum nol.

Kapasitas dan faktor pada skenario awal merupakan nilai asumsi/placeholder
dari editor HTML, bukan rekomendasi resmi PKJI. Sesuaikan dengan data survei
dan tabel PKJI sebelum menggunakan hasil sebagai analisis lalu lintas nyata.

## Struktur proyek

```text
matdis-tubes-2026/
├── README.md
├── TUTORIAL.md
├── CASESS.md
├── GLOSSARY.md
├── requirements.txt
├── config/
│   └── settings.py
├── core/
│   ├── base_algorithm.py
│   ├── flow_model.py
│   ├── graph_model.py
│   ├── simulation_runner.py
│   └── visualizer.py
├── cases/
│   ├── scenario_loader.py
│   └── scenarios/
│       └── asia_afrika.yaml
├── algorithms/
│   ├── registry.py
│   └── maxflow/
│       ├── dinic.py
│       ├── ford_fulkerson.py
│       └── push_relabel.py
├── tests/
│   ├── test_flow_algorithms.py
│   └── test_scenario_loader.py
└── scripts/
    ├── cli_utils.py
    ├── run_benchmark.py
    └── run_simulation.py
```

## Pengujian dan benchmark

```powershell
python -m pytest
python -m scripts.run_benchmark
python -m scripts.run_benchmark cases\scenarios\asia_afrika.yaml
```

Benchmark membandingkan waktu ketiga algoritma pada kondisi normal dan
konvoi. `CASESS.md` tetap disimpan sebagai referensi daftar kasus tugas besar;
editor ini saat ini memuat skenario peta Asia Afrika saja.
