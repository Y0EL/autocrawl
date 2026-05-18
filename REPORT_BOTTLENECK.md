# Laporan Bottleneck Pipeline Autocrawl

**Tanggal investigasi:** 16 Mei 2026, 10.30 sampai 11.15 UTC
**Penyusun:** Diagnosa mendalam dari log container, database Postgres, Redis state, file lessons, dan summary harian
**Status pipeline saat laporan ditulis:** BERHENTI TOTAL. Tidak ada vendor baru sejak 15 Mei 08.25 UTC (lebih dari 26 jam). Tidak ada enriched vendor sejak 15 Mei 04.20 UTC (lebih dari 30 jam).

---

## Ringkasan Eksekutif

Pipeline berhenti total karena empat lapis kegagalan saling memperparah. Lapis pertama adalah backend Ollama di host `10.83.81.246:11434` yang mati dari jaringan sejak 13 Mei 03.27 UTC dengan pola intermittent. Lapis kedua membuat browser_use Agent terus throw `ModelProviderError`, memaksa container agentic restart 11 kali dalam tiga hari. Lapis ketiga melumpuhkan resolution stage yang LLM-dependent, sehingga 74 persen vendor stuck di status `unresolved` dan vendor noise off-scope masuk database tanpa di-filter. Lapis keempat adalah instrumentasi yang patah. Tabel `runs` kosong total padahal scheduler jalan, knowledge tracking kehilangan seen_domains dan completed_seeds, lesson system tidak mencegah retry URL yang sudah 404 belasan kali, dan industry tags pecah jadi varian capitalization plus campuran bahasa Indonesia dan Inggris.

Plan rekoveri `velvet-stirring-truffle.md` yang sudah disetujui menutup sebagian besar lapis ini. Dua isu tambahan yang harus dimasukkan ke roadmap adalah perbaikan persistence run record ke Postgres dan feedback loop dari lesson archive ke seed generator supaya URL 404 chronic tidak dicoba ulang.

---

## A. Akar Penyebab Berhenti Total

### A.1. Ollama Backend Mati Dari Jaringan

Probe dari container agentic dan dari WSL host menunjukkan host `10.83.81.246` tidak bisa di-ping (100 persen packet loss dalam tiga paket berturut). HTTP request ke `http://10.83.81.246:11434/` return status `000` dengan waktu 6.0 detik (timeout penuh, tidak ada respons TCP).

Pertama kali pesan `LLM error (ModelProviderError: Failed to connect to Ollama. Please check that Ollama is downloaded, running and accessible)` muncul di log:
- `autocrawl-agentic-a` pertama kali: **13 Mei 2026 03.27.29 UTC**
- `autocrawl-agentic-b` pertama kali: **13 Mei 2026 03.27.29 UTC**

Itu berarti gangguan Ollama backend sudah berjalan tiga hari intermittent, bukan insiden mendadak hari ini. User sempat restart Ollama 14 Mei dan pipeline pulih beberapa jam, tapi backend mati lagi setelahnya dan tetap mati sampai investigasi ini ditulis.

### A.2. Konfigurasi LLM Tanpa Fallback

Container agentic punya env `AGENTIC_LLM_BASE_URL=http://10.83.81.246:11434` dan model utama `OPENAI_MODEL_LIGHT=qwen3.6:27b`. Setiap LLM error muncul dengan suffix `but no fallback_llm configured`. Tidak ada cadangan provider, tidak ada model fallback lokal yang lebih kecil, tidak ada cooldown buat seed yang baru terkena LLM error.

### A.3. Restart Loop Container Agentic

Inspeksi Docker terhadap dua worker:

| Container | Jumlah restart | Exit code terakhir | OOMKilled | Started terakhir |
|-----------|----------------|--------------------|-----------| ----------------|
| autocrawl-agentic-a | 11 | 0 | false | 16 Mei 10.10.12 UTC |
| autocrawl-agentic-b | 11 | 0 | false | 16 Mei 09.37.38 UTC |

Exit code 0 berarti shutdown graceful, bukan OOM atau crash. Pola ini konsisten dengan healthcheck atau internal supervisor yang mendeteksi LLM tidak responsif lalu memutuskan exit. Docker restart-policy `unless-stopped` mengangkat container kembali, lalu siklus berulang. Ini bukan recovery, ini loop yang menghabiskan boot time tanpa progress.

---

## B. Bottleneck Utama

### B.1. Resolution Stage Adalah Pinch Point Terbesar

Distribusi status vendor di tabel `vendors`:

| Status | Jumlah | Persentase |
|--------|--------|------------|
| **unresolved** | **3026** | **74,2%** |
| scope_rejected | 677 | 16,6% |
| **enriched** | **373** | **9,2%** |
| **Total** | 4076 | 100% |

Hanya 9,2 persen vendor yang berhasil sampai status enriched. Sisanya stuck di unresolved (3026 vendor) atau ditolak scope classifier (677 vendor). Sample lima vendor terbaru yang unresolved, semua dengan kolom `domain` kosong:

- Henkel Adhesive Technologies (created 15 Mei 08.25 UTC)
- Concentric AI (15 Mei 08.19 UTC)
- Bosch Rexroth (15 Mei 08.19 UTC)
- ThreatLocker (15 Mei 08.11 UTC)
- SAP (15 Mei 08.01 UTC)

Tiga di antaranya (Henkel, Bosch Rexroth, SAP) adalah vendor industri umum, bukan defense atau security. Discovery stage mengekstrak nama dari halaman exhibitor listing termasuk sidebar sponsor dan footer logo, lalu mengkomit ke DB sebagai vendor kandidat. Karena resolution dan scope classifier bergantung LLM yang sedang mati, vendor noise ini tidak pernah lolos screening jadi scope_rejected. Mereka menumpuk di DB tanpa value.

### B.2. Vendor Add Rate Turun Drastis

Daily count vendor masuk DB dari query langsung Postgres:

| Tanggal | Total masuk DB |
|---------|----------------|
| 9 Mei | 86 |
| 10 Mei | **691 (puncak)** |
| 11 Mei | 344 |
| 12 Mei | 331 |
| 13 Mei | 181 |
| 14 Mei | 288 |
| 15 Mei | **78** |
| 16 Mei | **0** (sampai 10.30 UTC) |

Daily count enriched (lolos sampai akhir pipeline):

| Tanggal | Enriched |
|---------|----------|
| 11 Mei | 27 |
| 12 Mei | 39 (puncak) |
| 13 Mei | 7 |
| 14 Mei | 15 |
| 15 Mei | **1** |
| 16 Mei | **0** |

Enriched turun 97 persen dalam empat hari (39 ke 1). Vendor terakhir yang berhasil enriched adalah Claroty di 15 Mei 04.20 UTC, sekarang sudah lebih dari 30 jam tanpa enriched baru. Pattern ini coinciding dengan onset gangguan Ollama 13 Mei 03.27 UTC.

---

## C. Temuan Menarik Dari Deep Dive

### C.1. Lesson Failure Didominasi Empty Result

Folder `data/agentic_lessons/`:
- Failure lessons: **2857**
- Success lessons: **205**
- Failure rate: **93 persen**

Breakdown kategori failure:

| Kategori | Jumlah | Persentase failure |
|----------|--------|---------------------|
| **empty_result** | **1976** | **69%** |
| timeout | 427 | 15% |
| empty_page | 340 | 12% |
| no_selector_match | 14 | 0,5% |
| image_only | 4 | 0,1% |

`empty_result` mendominasi. Itu kategori ketika agent **jalan sampai akhir, parsing halaman**, lalu emit `{"exhibitors": []}`. Bukan timeout, bukan website kosong (`empty_page` kategori terpisah), bukan dead domain. Pattern ini muncul ketika **LLM gagal mengekstrak entity dari konten yang sebenarnya ada di DOM**. Itu signature LLM-degraded behavior. Pipeline mengeluarkan resource Chromium dan network full untuk navigate plus render, lalu LLM call gagal di tengah jalan, lalu agent bail dengan list kosong.

Lessons by day:

| Tanggal | Failures |
|---------|----------|
| 9 Mei | 318 |
| 10 Mei | 287 |
| 11 Mei | 277 |
| 12 Mei | 270 |
| 13 Mei | 248 |
| 14 Mei | **354 (puncak)** |
| 15 Mei | 275 |
| 16 Mei | 90 (sampai 10.30 UTC) |

Pace failure relatif stabil 250 sampai 350 per hari. Container terus mencoba, tapi hampir semuanya berakhir di archive failure.

### C.2. Lesson System Tidak Mencegah Retry URL 404

Domain valid tapi URL path-nya 404 atau 403, di-coba ulang puluhan kali walaupun lesson sudah ter-archive:

| Domain | URL path | Jumlah 404 | Rentang tanggal |
|--------|----------|-------------|-----------------|
| aprescyber.com | Apres Cyber Slopes Summit 2026 | 14 | 7 sampai 12 Mei |
| messefrankfurt.com | Intersec 2026 | 10+ | 8 sampai 15 Mei |
| dimdex.com | DIMDEX 2026 | 8 plus 2x 403 | 8 sampai 15 Mei |
| iwceexpo.com | International Wireless | 10 | 8 sampai 9 Mei |
| ofcconference.org | Optical Fiber Communications | 5 | 8 sampai 9 Mei |
| generativeaiexpo.com | Generative AI Expo 2026 | 8 | 8 sampai 15 Mei |
| sans.org | SANS 2026 Training | 4 | 8 sampai 9 Mei |
| enterpriseconnect.com | Enterprise Connect | 1 | 9 Mei |

Tiap pass, seed yang sama di-launch ulang, agent navigate ke URL yang sama, dapat 404, lesson di-archive, lalu pass berikutnya melakukan hal yang sama. Tidak ada feedback dari archive failure ke seed generator untuk membuang URL path yang sudah 404 chronic.

### C.3. Tabel Runs Di Postgres Kosong Total

`SELECT COUNT(*) FROM runs;` returns **0**.

Schema tabel lengkap dengan 17 kolom termasuk `run_id`, `started_at`, `finished_at`, `mode`, `exhibitors_extracted`, `vendors_resolved`, `vendors_enriched`, `failures`, `firecrawl_credits_used`, `openai_tokens_used`. Tapi tidak satu run pun yang pernah persisted ke DB selama lifetime pipeline.

Konsekuensi:
- Endpoint `/api/overview` return `latest_run: null`
- Endpoint `/api/runs` return `{"items":[], "total":0, "limit":8, "offset":0}`
- Frontend "RUN TERAKHIR" card yang sempat kita ganti menjadi UPTIME (di pass redesign tanggal 13 Mei) menggambar dari source lain, kemungkinan Redis ephemeral state atau in-memory accumulator yang hilang saat container restart

Code path yang seharusnya insert run record ke tabel `runs` belum di-audit. Itu masuk daftar dependency untuk plan recovery.

### C.4. Expo Discovery Mati Lima Hari

Tabel `expos`: 44 records. **Semua memiliki `created_at = 2026-05-11 10:05:10` timestamp identik**. Itu satu bulk insert dari seed file YAML, bukan discovery progresif.

Source breakdown:
- `unknown` (legacy import): 10
- `agentic` (agentic crawler): 14
- `conferenceindex` (adapter conferenceindex.com): 20

Total cuma 44 di DB, padahal `expo_files: 84` di summary harian. Mismatch 40 file antara file storage (`/app/data/...`) dengan DB. Itu indikasi insert path file_to_db rusak atau ada filter yang aggressive di insert side.

Tidak ada expo baru ditambahkan ke DB dalam lima hari penuh.

### C.5. Industry Tags Pecah Inkonsisten

Top 14 industry tags dari endpoint `/api/overview`:

```
cybersecurity        163
defense              119
Pendidikan            47
surveillance          40
Kesehatan             28
Pertanian             28
law_enforcement       24
Teknologi             22
Cybersecurity         21    duplikasi capitalization
critical_infra        21
Pertahanan            16    duplikasi bahasa
Kecerdasan Buatan     16
Healthcare            15
Bioteknologi          15
```

Tiga masalah sekaligus:

1. **Capitalization variants**: `cybersecurity` (163) terpisah dari `Cybersecurity` (21). Normalisasi case tidak dilakukan sebelum count atau insert. Ini bug di stage classification atau storage.

2. **Bilingual drift**: `defense` (119) terpisah dari `Pertahanan` (16). LLM scope classifier kadang return tag bahasa Inggris kadang bahasa Indonesia tanpa kontrol. Kemungkinan prompt tidak menetapkan locale output.

3. **Off-scope tags**: `Kesehatan` 28, `Pertanian` 28, `Pendidikan` 47, `Bioteknologi` 15. Crawler ini target defense dan security expo. Munculnya tag healthcare, agriculture, education, biotech adalah bukti vendor noise yang seharusnya scope_rejected tapi tidak ter-filter karena classifier mati.

### C.6. Knowledge Tracking Patah

File `agentic_knowledge.json` ukuran 2898 baris di disk, tapi setelah di-parse:

```
blacklist: 7
seen_domains: 0
completed_seeds: 0
```

`seen_domains` dan `completed_seeds` keduanya **nol** padahal pipeline sudah discover 4000 lebih vendor. Itu artinya tracking yang seharusnya jadi memory long-term (apa yang sudah dilihat, seed apa yang sudah selesai diproses) tidak ter-populate atau hilang setelah restart. Konsekuensinya, ya itu yang dilihat di temuan C.2: lesson archive ada tapi knowledge tidak menyerap signal-nya kembali ke seed loader.

Blacklist cuma punya 7 entry juga aneh. Setelah 14 lessons 404 untuk aprescyber.com saja, mestinya minimal domain itu sudah masuk blacklist.

### C.7. Active Run Lock Asimetris

Redis key yang ada saat probe:

```
autocrawl:agentic_active_run:agentic-b   -- ada, started_at = 2026-05-16T10:23:11
autocrawl:agent_traces
autocrawl:events
```

**Tidak ada `autocrawl:agentic_active_run:agentic-a`.** Twin worker A dan B mestinya simetris pegang lock saat pass aktif. Kemungkinan agentic-a stuck di startup retry loop sehingga belum sempat acquire lock untuk pass pertama setelah restart paling baru di 10.10.12 UTC.

DBSIZE Redis hanya 20 key total. Pipeline yang seharusnya intensif state cross-process punya footprint Redis sangat minimal. Itu tanda bahwa banyak instrumentasi yang dirancang untuk Redis (cross-worker counters, pass history, dedup state) tidak digunakan atau key TTL terlalu pendek.

### C.8. Summary Vendor Total Mismatch Dengan Realitas DB

Daily summary file di `data/reports/runs/summary_*.json` punya field `vendors_total`:

- 13 Mei: 415
- 14 Mei: 432
- 15 Mei: 435

DB real:
- Total vendors: **4076**
- Enriched only: **373**

Tidak ada formula yang langsung match. Kemungkinan `vendors_total` di summary adalah count vendor dengan `industries IS NOT NULL` plus filter lain, atau cuma scope yang aktif. User report angka `3710` saat awal investigasi, itu juga tidak match dengan DB (4076) maupun summary (435). Ada tiga metric berbeda untuk konsep yang sama: file storage, DB query, dan apa yang dilihat frontend. Itu fragmentasi observability yang membingungkan.

---

## D. Resource Anomali

Snapshot `docker stats` saat probe:

| Container | CPU | Memori |
|-----------|-----|--------|
| autocrawl-frontend | 0,24% | 18 MiB |
| autocrawl-api | 1,24% | 183 MiB |
| autocrawl-agentic-a | 0,92% | 241 MiB |
| autocrawl-agentic-b | 0,65% | 669 MiB |
| **autocrawl-crawler** | **2,08%** | **6,1 GiB** |
| autocrawl-grafana | 1,00% | 212 MiB |
| autocrawl-prometheus | 0% | 50 MiB |
| autocrawl-db | 0,26% | 80 MiB |
| autocrawl-redis | 0,74% | 16 MiB |
| autocrawl-flaresolverr | 0,01% | 320 MiB |
| autocrawl-chroma | 0,13% | 151 MiB |
| autocrawl-openserp | 0,02% | 122 MiB |

`autocrawl-crawler` (scheduler service) makan **6,1 GiB RAM** dengan CPU 2 persen. Itu sangat tinggi untuk service yang fungsinya cuma run APScheduler dan trigger pass. Kemungkinan ada memory leak atau working set yang tidak ter-release setelah pass selesai. Worth audit terpisah, tapi bukan blocker akut saat ini.

Container `autocrawl-openserp` dibatasi 1 GiB sementara semua container lain bisa pakai 30,9 GiB host. Itu konfigurasi yang sah tapi worth dicatat.

---

## E. Empat Lapis Kegagalan

Untuk pembaca yang skim, urutan cascade kegagalan adalah sebagai berikut.

**Lapis 1 (akar masalah, faktor eksternal)**

Ollama backend `10.83.81.246:11434` mati intermittent sejak 13 Mei 03.27 UTC. Network unreachable, ping fail, HTTP timeout. Pipeline 100 persen bergantung pada LLM ini tanpa fallback model dan tanpa secondary provider.

**Lapis 2 (efek langsung di container)**

Browser_use Agent throw `ModelProviderError` di setiap step. Agentic-a dan agentic-b masing-masing restart 11 kali dalam tiga hari. Container exit 0 (graceful via internal logic), Docker restart loop. Pass terisi 69 persen `empty_result` failure karena LLM tidak bisa parse halaman.

**Lapis 3 (kerusakan kaskade ke stage hilir)**

Resolution stage yang LLM-dependent hampir mati. 74 persen vendor stuck di status `unresolved`. Scope classifier juga mati, sehingga vendor noise off-scope (SAP, Bosch Rexroth, Henkel, Pertanian, Kesehatan, Pendidikan) menumpuk di DB tanpa di-filter.

**Lapis 4 (instrumentasi rusak, baru ketahuan saat investigasi)**

Tabel `runs` di Postgres kosong total padahal scheduler jalan. Knowledge `seen_domains` dan `completed_seeds` nol padahal 4000+ vendor sudah discover. Lesson archive tidak feedback ke seed generator, URL 404 di-retry belasan kali. Industry tags pecah jadi variants capitalization dan campuran bahasa. Active run lock cuma untuk agentic-b, tidak untuk agentic-a. Summary metric, DB query, dan frontend tampilkan angka berbeda untuk konsep yang sama.

---

## F. Mapping Ke Plan Recovery `velvet-stirring-truffle.md`

Plan recovery yang sudah disetujui menutup sebagian besar lapis kegagalan di atas.

| Fitur Plan | Lapis yang Ditutup | Catatan |
|------------|---------------------|---------|
| F1: Force-release watchdog di crawler scheduler | Lapis 2 (cegah lock stuck) | Mitigasi 12+ jam skip_overlap loop |
| F2: Pre-flight DNS hard-fail | Lapis 2 (cegah buang 20 menit per dead domain) | Belum cover URL 404 chronic, lihat catatan di F-extra |
| F3: LLM fallback chain | Lapis 1 dan Lapis 2 (akar masalah) | Critical fitur. Tanpa ini insiden akan terulang |
| F4: Endpoint `/api/health/agentic` | Lapis 4 (instrumentasi) | Expose state baru cross-process via Redis |
| F5: Self-restart trigger Windows watchdog | Lapis 2 (auto-recovery) | Bergantung F4 |

### F.X. Dua Item Baru Yang Belum Ada Di Plan

Investigasi ini menemukan dua issue yang harus ditambahkan ke roadmap recovery.

**F-extra-1: Audit dan perbaiki path insert `runs` ke Postgres**

Tabel `runs` kosong total adalah problem instrumentasi mendasar. Frontend dan analytics bergantung pada record ini. Audit code path dari `crawler/scheduler.py` ke `runs` insert. Periksa apakah ada try-except yang swallow exception, transaction yang tidak commit, atau path yang hanya menulis ke summary file alih-alih DB. Effort estimasi: M (2 sampai 3 jam audit plus fix).

**F-extra-2: Feedback loop dari lesson archive ke seed generator**

URL 404 chronic seperti `aprescyber.com/Apres Cyber Slopes Summit 2026 path` di-retry 14 kali dalam 5 hari. Lesson sudah ter-archive, tapi seed generator masih mengeluarkan URL yang sama tiap pass. Tambahkan post-processor yang baca `data/agentic_lessons/failure/` dengan kategori `404` atau `403` dan rate retry di atas threshold, lalu tambahkan URL path tersebut ke skip list. Effort estimasi: S (1 sampai 2 jam).

---

## G. Tindakan Yang Direkomendasikan Segera

1. **Cek host Ollama `10.83.81.246`**. SSH ke sana, jalankan `nvidia-smi` plus `systemctl status ollama` plus `journalctl -u ollama -n 200`. Kalau GPU device hilang dari driver, restart service. Kalau host benar-benar down, reboot atau cek hardware.

2. **Sementara Ollama belum pulih**, sebelum F3 di-implement, lakukan workaround sementara: edit `docker-compose.yml` env `OPENAI_MODEL_LIGHT` dari `qwen3.6:27b` ke model kecil yang fit di CPU (`granite4.1:8b` atau `qwen3-vl:8b`), restart container agentic. Itu memberi waktu sampai F3 fallback chain ter-deploy.

3. **Bersihkan vendor noise off-scope**. Setelah Ollama pulih dan scope classifier berfungsi, jalankan one-off script untuk reclassify 3026 vendor unresolved. Yang off-scope masuk `scope_rejected`. Itu turunkan beban DB dan bersihkan industry tag distribution.

4. **Mulai implementasi plan F1 dan F3 paralel** karena keduanya independen dan critical.

5. **Audit `runs` table insert path** sebagai F-extra-1 segera sebelum F4 di-implement, karena F4 dan watchdog F5 bergantung pada visibility yang akurat.

6. **Mulai fitur F-extra-2 (URL 404 skip list)** sebagai quick win. Implementasi pendek, dampak besar untuk turunkan failure rate dari sisi pipeline yang masih jalan.

---

## H. Daftar Berkas Yang Di-investigasi

- Logs container `autocrawl-agentic-a` (full history sejak boot pertama)
- Logs container `autocrawl-agentic-b` (full history)
- Logs container `autocrawl-crawler` (24 jam terakhir)
- Postgres database `autocrawl`, tabel `vendors`, `expos`, `runs`
- Redis keys via `--scan` dan `DBSIZE`
- File `data/agentic_knowledge.json`
- Folder `data/agentic_lessons/failure/` dan `data/agentic_lessons/success/`
- Folder `data/reports/runs/summary_*.json` untuk tanggal 7 sampai 15 Mei 2026
- Endpoint `/api/overview`, `/api/runs`, `/api/health` via container `autocrawl-api`
- Probe network ke `10.83.81.246` via ping dan curl
- Snapshot `docker stats --no-stream`
- Docker inspect untuk RestartCount, ExitCode, OOMKilled

Laporan ini menyajikan data faktual dari sumber tersebut. Semua nomor, tanggal, dan persentase dihitung langsung dari hasil query atau parsing file, bukan estimasi.
