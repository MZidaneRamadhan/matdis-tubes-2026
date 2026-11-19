# Tutorial: Editor Graf Aliran Asia Afrika

Tutorial ini menjelaskan cara menjalankan aplikasi, mengubah jaringan jalan,
menghitung max-flow/min-cut, dan menyimpan data graf.

## 1. Menyiapkan dan menjalankan aplikasi

Pastikan Python 3.10 atau lebih baru tersedia. Dari PowerShell pada direktori
proyek:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run scripts/run_simulation.py
```

Peramban akan menampilkan editor peta. Koneksi internet diperlukan untuk
memuat tile peta OpenStreetMap; perhitungan graf berjalan di Python.

## 2. Mengedit node dan edge

### Menambah node

1. Klik lokasi tujuan pada peta.
2. Isi kode unik, nama, dan jenis node pada bagian **Tambah node dari peta**.
3. Periksa koordinat yang diambil dari klik peta, lalu pilih **Tambah node**.
4. Untuk kantong parkir, isi kapasitas kendaraan per jam.

Node yang sudah ada dapat dipilih pada bagian **Edit node** untuk mengubah
nama, jenis, koordinat, status titik macet, atau kapasitas parkir. Menghapus
node juga menghapus edge yang terhubung dengannya.

### Mengedit edge

Di bagian **Edit edge**, pilih ruas lalu ubah titik asal/tujuan, arah, jenis,
jumlah lajur, faktor lebar lajur, kapasitas manual, beban dasar, atau status
edge. Edge yang tidak ikut jaringan aliran tetap terlihat pada peta, tetapi
tidak masuk perhitungan.

Untuk menambah edge, pilih node asal dan tujuan serta arah. Edge dua arah
diwakili oleh dua busur terpisah pada jaringan aliran, masing-masing dengan
kapasitas yang sama.

### Mengatur parameter

Bagian **Parameter model** mengatur C0, FC model, smp per kendaraan, demand Q,
reduksi kapasitas konvoi, dan pengurangan beban dasar. Simpan perubahan
sebelum menghitung ulang aliran.

## 3. Menjalankan analisis

1. Pilih Dinic, Ford-Fulkerson (pencarian jalur BFS), atau Push-Relabel.
2. Klik **Hitung max-flow dan min-cut**.
3. Bandingkan nilai max-flow normal dan konvoi, demand yang belum tertampung,
   serta kapasitas parkir total.
4. Tabel min-cut mengikuti skenario peta yang dipilih. Ruas min-cut diberi
   warna merah; kapasitas parkir yang menjadi bottleneck ditandai ungu.

Sumber virtual menerima paling banyak demand Q. Setiap pintu masuk dihubungkan
ke sumber, dan setiap kantong parkir dihubungkan ke tujuan sesuai kapasitas
parkirnya. Dengan demikian, hasil min-cut dapat menunjukkan ruas jalan maupun
batas daya tampung parkir.

## 4. Impor dan ekspor

- **JSON graf** menyimpan node, edge, serta parameter. Unduh berkas untuk
  mempertahankan perubahan setelah sesi ditutup.
- **CSV node** berisi identitas, koordinat, jenis, status macet, dan kapasitas
  parkir.
- **CSV edge** berisi arah, lajur, parameter kapasitas, dan kapasitas normal
  maupun konvoi.
- **CSV jaringan aliran** berisi busur kapasitas normal dan konvoi, termasuk
  busur sumber, demand, dan parkir.
- Untuk memuat graf, pilih berkas JSON yang diekspor sebelumnya lalu klik
  **Muat graf JSON**.

Gunakan **Reset ke data awal** untuk mengembalikan graf dari
`cases/scenarios/asia_afrika.yaml`.

## 5. Menambah skenario dan algoritma

Skenario awal menggunakan YAML dengan bagian `case_id`, `title`,
`description`, `parameters`, `nodes`, dan `edges`. `cases/scenario_loader.py`
membaca YAML tersebut menjadi model graf bertipe di `core/graph_model.py`.
Validasi mencegah koordinat di luar rentang, kapasitas negatif, dan edge yang
merujuk node yang tidak tersedia.

Solver mengimplementasikan `BaseGraphAlgorithm` di
`core/base_algorithm.py`, kemudian didaftarkan melalui
`AlgorithmRegistry` pada `algorithms/__init__.py`. Runner pada
`core/simulation_runner.py` menggunakan registry untuk membandingkan solver
dengan input jaringan yang sama.

## 6. Menjalankan test dan benchmark

```powershell
python -m pytest
python -m pytest tests\test_flow_algorithms.py
python -m scripts.run_benchmark
```

Tes mencakup hasil max-flow/min-cut, kapasitas edge paralel, validasi
kapasitas, pemuatan skenario awal, dan ketiga implementasi algoritma.
