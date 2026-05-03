# AutoCrawler

Crawler otonom yang jalan 24 jam non stop. Fungsinya menemukan expo bidang security dan defense, mengambil daftar exhibitor dari situs aggregator (10times.com, Wikipedia, eventbrite, dan sejenisnya), lalu menentukan domain vendor asli (bukan domain aggregator), dan terakhir memperkaya data vendor pakai sumber publik gratis. Data text vendor otomatis diterjemahkan ke Bahasa Indonesia memakai NLLB-200. Hasil disimpan ke Postgres dan dipresentasikan di admin console berbasis Vue.

> **Baru pertama kali pakai?** Lihat [TUTORIAL.md](TUTORIAL.md) untuk panduan langkah demi langkah dari nol (15 section, lengkap dengan troubleshooting).

Stack inti backend: LangGraph, LangChain, Playwright, Surya OCR, Firecrawl, OpenAI atau Ollama, FastAPI, SQLAlchemy async, Postgres. Stack frontend: Vue 3, TypeScript, Tailwind CSS, Apache ECharts, TanStack Query, Pinia, FontAwesome 6. Semua self host, dijalankan via Docker Compose.

## Struktur Repo

```
crawl/
  backend/    Python service (LangGraph crawler, FastAPI, OCR, scraper, enrichment)
    src/crawler/
      agents/        discovery, extractor, resolver, name_resolver, enricher, reporter
      api/           FastAPI app, routes, dependency
      db/            SQLAlchemy models, engine, repositories
      tools/         scrapers, parsers, browsers, search, enrichment, llm
      store/         json_reporter, db_reporter, pdf_store, vector_store
      observability/ structlog logger, prometheus metrics, langfuse tracer
    tests/unit/      152 unit test
  frontend/   Vue 3 admin console (TypeScript, Tailwind, ECharts, FontAwesome)
    src/
      api/           axios client, TypeScript types
      components/    StatCard, DataTable, ProvenanceTimeline, charts/
      composables/   useTheme, useApiHealth, useCsvExport
      views/         OverviewPage, VendorsListPage, VendorDetailPage, ExposListPage, ExpoDetailPage, PdfsListPage, RunsListPage
      mocks/         MSW handlers (opsional, fallback dev tanpa backend)
    tests/          26 vitest test
  config/     YAML konfigurasi yang di share ke backend
  data/       Output JSON, PDF brosur, Chroma vector (gitignored)
  logs/       Log harian terstruktur (gitignored)
  docker-compose.yml          Stack lengkap (10 service)
  docker-compose.gpu.yml      Overlay opsional GPU NVIDIA
  .env.example                Template environment
```

## Cara Boot Pertama Kali

```bash
cp .env.example .env
```

Lalu isi `.env`. Minimum yang perlu diisi:

```
OPENAI_API_KEY=sk_xxx          # boleh kosong kalau pakai Ollama
FIRECRAWL_API_KEY=fc_xxx       # boleh kosong, fitur firecrawl auto skip
```

Build dan jalankan:

```bash
docker compose up -d --build
docker compose logs -f api
```

Tunggu sampai semua container `Healthy` atau `Started`, kira kira 30 detik. Postgres dan API butuh waktu lebih lama (init schema otomatis di lifespan startup).

Kalau lo punya data JSON dari run sebelumnya di `data/reports/`, impor ke Postgres:

```bash
docker compose exec api crawl db import-json
```

Buka dashboard di http://localhost:8090.

## Login dan Akses Layanan

| Layanan | URL | Cara Login |
|---|---|---|
| Frontend dashboard | http://localhost:8090 | Tanpa login. Konsumsi `/api/*` lewat nginx proxy |
| API FastAPI | http://localhost:8081/api/docs | Tanpa login. OpenAPI Swagger UI tersedia |
| Postgres autocrawl | localhost:5432 | User `postgres`, password `123`, database `autocrawl`. Internal antar container |
| Metrik Crawler | http://localhost:8080/metrics | Tanpa login. Endpoint Prometheus untuk di scrape |
| Grafana | http://localhost:3000 | User `admin`, password `admin`. Dashboard `AutoCrawl Overview` sudah pre loaded |
| Prometheus | http://localhost:9090 | Tanpa login. Buka langsung |
| Langfuse | http://localhost:3001 | **Buat akun pertama kali**. Klik "Sign up", isi email, password, dan organization name. Setelah masuk, buat project baru, copy `Public Key` dan `Secret Key` ke `.env` lalu restart container crawler |
| Chroma | http://localhost:8000 | Tanpa login. Hanya API, dipakai internal oleh crawler |
| FlareSolverr | http://localhost:8191 | Tanpa login. Hanya layanan, dipakai internal saat hadapi Cloudflare |
| Redis | localhost:6379 | Tanpa login. Hanya internal |
| Postgres Langfuse | internal | Hanya internal, user dan password sudah otomatis di compose |

### Setup Langfuse Pertama Kali (penting kalau mau lihat trace LLM)

1. Buka http://localhost:3001
2. Klik tombol Sign up
3. Isi email apa saja (misal `admin@local`), password bebas, nama organization bebas
4. Setelah login, klik Settings, lalu API Keys
5. Klik Create new API keys, copy yang muncul
6. Edit `.env`:
   ```
   LANGFUSE_PUBLIC_KEY=pk_xxx
   LANGFUSE_SECRET_KEY=sk_xxx
   ```
7. Restart container crawler:
   ```bash
   docker compose restart crawler
   ```

Setelah itu setiap LLM call yang crawler kerjakan akan muncul di dashboard Langfuse, lengkap dengan prompt, response, latency, dan token usage.

## Manfaat Tiap Layanan

**Crawler**
Inti aplikasi. Menjalankan LangGraph state machine, fan out ke 15 sampai 50 worker paralel, simpan hasil ke Postgres dan JSON, plus log harian. Lo bisa pakai CLI di sini.

**API (FastAPI)**
Endpoint `/api/*` yang melayani frontend. Baca dari Postgres. CORS enabled untuk localhost dan origin lain di env. OpenAPI docs di `/api/docs`.

**Postgres autocrawl**
Source of truth untuk vendor, expo, run, PDF metadata. Schema otomatis dibuat saat API container start. Data lama JSON bisa diimpor lewat `crawl db import-json`.

**Frontend dashboard**
Admin console berbasis Vue 3 plus Apache ECharts. Tujuh halaman, light dan dark mode otomatis. Filter, search, CSV export. Hit API real time. Status indicator backend di topbar (refresh tiap 30 detik).

**Grafana**
Dashboard visual real time. Lihat berapa vendor sudah dikoleksi, error rate per stage, OpenAI token usage, Firecrawl credit usage, latency request per tool, dan progress menuju target Phase 2 (100 vendor). Cocok buat presentasi ke management.

**Prometheus**
Backend metrik. Grafana baca dari sini. Lo juga bisa buka UI Prometheus untuk query manual atau debug saat ada metrik anomali.

**Langfuse**
Tracing LLM. Tiap kali crawler tanya OpenAI atau Ollama, prompt dan response masuk ke Langfuse. Berguna untuk debug kalau hasil ekstraksi LLM aneh, audit cost, atau lihat reasoning chain qwen.

**Chroma**
Database vektor. Simpan embedding tiap vendor agar dedup vendor jalan otomatis. Misal kalau "XL Defense Inc" dan "XL Defense Systems" muncul di expo berbeda, Chroma kasih tahu mereka kemungkinan vendor yang sama.

**FlareSolverr**
Pengelabuh Cloudflare. Banyak situs aggregator dan vendor pakai Cloudflare anti bot. FlareSolverr buka headless browser, lewati challenge, lalu balikin HTML asli ke crawler.

**Redis**
Antrian kerja dan pembatas request. Tiap domain dibatasi 1 request per detik (default), worker yang dapat domain sibuk parkir di queue dan ambil kerjaan lain. Plus dedup task ID supaya satu vendor tidak diproses dua kali per hari.

**Postgres Langfuse**
Database internal Langfuse menyimpan trace LLM. Tidak perlu disentuh manual.

## Storage Postgres

Seluruh data vendor, expo, PDF, dan run summary disimpan di Postgres (container `autocrawl-db`) sebagai source of truth. JSON di `data/reports/` tetap ditulis sebagai audit trail dan backward compatibility.

Kredensial default (override via `.env`):

```
DATABASE_URL=postgresql+asyncpg://postgres:123@autocrawl-db:5432/autocrawl
SQLALCHEMY_ECHO=false
API_CORS_ORIGINS=http://localhost:5173,http://localhost:8090
```

Schema otomatis dibuat saat API container startup lewat `Base.metadata.create_all()`. Tabel utama:

* `vendors` (PK domain, JSONB untuk address, contacts, source_trail, raw_extracts)
* `expos` (PK expo_id)
* `expo_vendors` (join table)
* `pdfs` (PK auto, UNIQUE sha256)
* `runs` (PK run_id)

Akses Postgres dari host pakai psql atau client GUI:

```bash
psql -h localhost -p 5432 -U postgres -d autocrawl
# password: 123
```

## API Endpoint

Container `autocrawl-api` jalan di port 8081, baca dari Postgres. Endpoint utama:

| Method | Path | Deskripsi |
|---|---|---|
| GET | `/api/health` | Status API plus DB ping |
| GET | `/api/overview` | Counter total, latest run, industry breakdown |
| GET | `/api/vendors` | Daftar vendor paginated, filter industry, country, search |
| GET | `/api/vendors/{domain}` | Profil vendor lengkap |
| GET | `/api/expos` | Daftar expo paginated |
| GET | `/api/expos/{expo_id}` | Detail expo plus vendor_domains |
| GET | `/api/pdfs` | Daftar PDF brosur |
| GET | `/api/runs` | Riwayat run |
| GET | `/api/stats/industries` | Untuk pie chart industri |
| GET | `/api/stats/countries` | Untuk bar chart top negara |
| GET | `/api/stats/source-types` | PDF vs aggregator vs search |
| GET | `/api/stats/timeline` | Akumulasi vendor per hari |
| GET | `/api/stats/runs-mode` | Distribusi mode run |

OpenAPI Swagger UI: http://localhost:8081/api/docs

## Frontend Admin Console

Vue 3 plus TypeScript plus Tailwind plus ECharts plus TanStack Query plus Pinia plus FontAwesome 6. Light dan dark mode otomatis ikut preferensi sistem, bisa di toggle manual, tersimpan di localStorage. Tujuh halaman: Ringkasan, Daftar Vendor, Detail Vendor (timeline source provenance), Daftar Expo, Detail Expo, Brosur PDF, Riwayat Run.

### Charts industrial (Apache ECharts)

* **IndustryPieChart**. Distribusi vendor per industri tag.
* **CountryBarChart**. Top 10 negara berdasarkan registrar domain vendor.
* **SourceTypePieChart**. Donut PDF vs aggregator vs search.
* **VendorTimelineChart**. Combo bar plus line area, akumulasi vendor 30 hari.
* **Phase2GaugeChart**. Gauge progress menuju target 100 vendor.
* **RunsModeBarChart**. Distribusi run mode dev, normal, aggressive.

Semua chart auto swap palette saat user toggle dark mode.

### Filter, Search, Export

Halaman Vendor punya filter industri (dropdown), filter negara (dropdown dinamis dari endpoint), full text search nama atau domain, plus tombol Export CSV satu klik.

Halaman Expo punya filter negara dan search nama expo.

### Mode Dev tanpa Backend (opsional)

Default frontend hit backend real (`VITE_USE_MOCKS=false`). Kalau backend tidak jalan dan lo cuma mau cek UI:

```bash
cd frontend
echo "VITE_USE_MOCKS=true" > .env.local
npm run dev
```

MSW intercept semua request `/api/*` dengan mock data realistis (3 vendor sample, 2 expo, 2 PDF, 3 run).

### Dev Lokal

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # bundle production ke dist/
npm run preview      # cek build di port 8090
npm run test         # 26 vitest test
npm run typecheck    # vue-tsc strict
```

## Perintah CLI

Semua perintah dijalankan dari host pakai `docker compose exec`:

```bash
docker compose exec crawler crawl run                    # satu run end to end
docker compose exec crawler crawl run --mode aggressive  # 50 worker paralel
docker compose exec crawler crawl schedule               # mode 24 jam (default di container)
docker compose exec crawler crawl report                 # status koleksi vendor sejauh ini
docker compose exec crawler crawl health                 # cek koneksi ke semua dependency
docker compose exec crawler crawl pdf-test <url>         # uji ekstraksi satu PDF
docker compose exec api crawl wiki-test <url>            # uji scraper Wikipedia
docker compose exec api crawl translate-vendors          # backfill translasi vendor lama

docker compose exec api crawl db migrate                 # buat tabel Postgres
docker compose exec api crawl db import-json             # impor JSON lama ke DB
docker compose exec api crawl api-serve --port 8081      # serve API manual (default sudah jalan)
```

Mode tersedia:

| Mode | Jumlah Worker | Untuk Apa |
|---|---|---|
| dev | 5 worker | debug lokal, hemat resource |
| normal | 15 worker enrichment | run harian biasa, default |
| aggressive | 50 worker enrichment | catch up burst di akhir minggu |

## Ganti Provider LLM (OpenAI atau Ollama)

Kalau OpenAI tier kena rate limit, ganti ke Ollama lokal. Sama sekali tidak perlu ubah kode, cuma tukar env.

Edit `.env`:

```
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
OPENAI_MODEL_HEAVY=qwen3.5:4b
OPENAI_MODEL_LIGHT=qwen3.5:4b
OPENAI_EMBEDDING_MODEL=qwen3_embedding:4b
```

Di host (sekali saja) pull model:

```bash
ollama pull qwen3.5:4b
ollama pull qwen3_embedding:4b
```

Container akses Ollama via `host.docker.internal:11434/v1` (sudah default). Restart:

```bash
docker compose restart crawler
```

Catatan tuning Ollama supaya tidak timeout saat banyak request bareng:

```bash
[Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "4", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "30m", "User")
```

Lalu restart layanan Ollama.

## Translation Bahasa Indonesia (NLLB-200)

Data text vendor (description, tagline, products, industries) otomatis diterjemahkan ke Bahasa Indonesia saat enrichment selesai. Engine translasi: NLLB-200 distilled 600M dari Meta, dijalankan via CTranslate2 dengan int8 quantization (~1.2GB di disk, jalan di CPU). Versi English asli tetap disimpan di kolom `*_original` untuk audit dan toggle EN/ID di dashboard.

Aktif default. Build image akan download dan convert model otomatis. Untuk skip (lebih ringan, akan fallback ke OpenAI gpt-4o-mini saat ada panggilan translasi):

```bash
docker compose build --build-arg INSTALL_NLLB=false
```

Backfill semua vendor lama yang masih `language_code=en`:

```bash
docker compose exec api crawl translate-vendors
docker compose exec api crawl translate-vendors --force          # paksa re translate semua
docker compose exec api crawl translate-vendors --limit 10       # batasi 10 vendor saja
docker compose exec api crawl translate-vendors --dry-run        # preview tanpa simpan
```

Env yang relevan di `.env`:

```
TRANSLATION_ENABLED=true
TRANSLATION_PROVIDER=nllb          # nllb | openai | none
NLLB_MODEL_PATH=/app/data/nllb_ct2
NLLB_TOKENIZER_PATH=/app/data/nllb_hf/snapshot
TARGET_LANGUAGE=id
TRANSLATION_BATCH_SIZE=8
TRANSLATION_MAX_CHARS=2000
```

Detail lebih lanjut termasuk troubleshooting dan cara verify model load: [TUTORIAL.md section 9](TUTORIAL.md).

## Wikipedia Scraper

Selain 10times.com, AutoCrawl bisa ekstrak organisasi dari artikel Wikipedia. Aggregator domain `wikipedia.org` punya scraper khusus yang:

1. Fetch HTML artikel
2. Pull semua `/wiki/<title>` link dari main content
3. Skip namespace infrastruktur (`Category:`, `File:`, `Talk:`, dll)
4. Batch query Wikipedia REST API untuk klasifikasi via category
5. Emit `ExhibitorRef` hanya untuk yang tergolong `company` atau `organisation` (skip person dan place)

Vendor URL resolver tetap reject `wikipedia.org` sebagai domain vendor (Wikipedia bukan vendor), jadi resolusi domain final pakai name resolver: search by name plus LLM tiebreak.

Test scraper Wikipedia tanpa run penuh:

```bash
docker compose exec api crawl wiki-test https://en.wikipedia.org/wiki/2026_Bilderberg_Conference
```

Output tabel berisi nama, URL Wikipedia tujuan, metode ekstraksi, dan confidence. Person akan diskip otomatis. Lihat juga [TUTORIAL.md section 12](TUTORIAL.md).

## Ekstraksi Brosur PDF

Crawler bisa download PDF brosur expo, ekstrak daftar vendor, dan track presisi tiap vendor dapet dari PDF mana, halaman berapa, posisi keberapa.

Aktifin lewat `.env`:

```
PDF_DISCOVERY_ENABLED=true
OCR_ENABLED=true
SURYA_DEVICE=auto      # auto | cpu | cuda | mps
MAX_PDFS_PER_EXPO=10
PDF_MAX_SIZE_MB=50
```

Build image dengan Surya OCR (default `INSTALL_SURYA=true`):

```bash
docker compose build crawler
docker compose up -d
```

Untuk passthrough GPU (butuh NVIDIA Container Toolkit di host):

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

Uji ekstraksi satu PDF tanpa run penuh:

```bash
docker compose exec crawler crawl pdf-test https://expo.com/2026/exhibitors.pdf
```

Output di `data/pdfs/<expo_id>/`:

* `<file>.pdf` PDF mentah untuk audit trail
* `<file>.meta.json` SHA256, source URL, timestamp download
* `<file>.pages.jsonl` per halaman, metode ekstraksi, vendor yang ditemukan

Tiap vendor JSON yang ditemukan dari PDF punya `source_trail` lengkap:

```json
{
  "domain": "guangzhouinstitutedefense.com",
  "company_name": "Guangzhou Institute Defense",
  "source_trail": [
    {
      "type": "pdf",
      "url": "https://malaysiadefence.com/2026/list.pdf",
      "pdf_filename": "MDE2026_Exhibitor_List.pdf",
      "pdf_sha256": "abc123...",
      "page": 7,
      "position": 3,
      "extraction_method": "surya_ocr",
      "confidence": 0.92,
      "context_snippet": "AS#312 Guangzhou Institute Defense Hall B"
    },
    {
      "type": "search",
      "url": "https://duckduckgo.com/?q=Guangzhou+Institute+Defense",
      "extraction_method": "name_resolver_llm_tiebreak"
    }
  ]
}
```

## Output Hasil

Postgres adalah source of truth (akses lewat `/api/*` atau psql). JSON tetap ditulis sebagai audit:

```
data/
  reports/
    master_manifest.json     index semua expo dan vendor (legacy)
    expos/<expo_id>.json     tiap expo, daftar vendor di dalamnya
    vendors/<domain>.json    tiap vendor, profil lengkap
    runs/<run_id>.json       ringkasan tiap run
  pdfs/<expo_id>/            PDF brosur mentah, metadata sidecar, audit per halaman
  vector_db/                 Chroma vector store untuk dedup vendor

logs/
  YYYY MM DD/
    run.jsonl                semua event JSON terstruktur
    errors.jsonl             hanya event level ERROR
```

## Cara Kerja Singkat

1. **Discovery**. LLM expand topic dari `config/seed_topics.yaml` jadi 8 sampai 15 query variasi (juga dalam bahasa lokal kalau region China, Jepang, Korea, atau Russia). Multi sumber search (Firecrawl, DuckDuckGo, Google News RSS, Wikipedia, plus Baidu, Naver, Yahoo Japan kalau region cocok).
2. **Extraction**. Scraper khusus per situs aggregator (10times, generic fallback) hasilkan daftar exhibitor. Bersamaan, PDF Finder cari brosur PDF expo dan PDF Extractor parsing pakai PyMuPDF, pdfplumber, atau Surya OCR.
3. **Resolution**. Komponen paling penting. Tiap exhibitor dihadapkan ke ladder schema.org json ld, anchor "Visit Website", analisa outbound link, lalu LLM tie break. Aggregator dan social media pasti ditolak via blacklist di `config/aggregator_blacklist.yaml`. Untuk vendor dari PDF yang cuma punya nama, name resolver pakai search plus LLM untuk nemuin domain aslinya.
4. **Dedup**. Chroma cosine similarity. Vendor yang mirip cuma di update expo list nya, tidak di enrich ulang.
5. **Enrichment**. Gabungan whois, dns, sitemap, schema.org organization, Open Graph, regex email, Wayback. LLM merge semua jadi profil Vendor sesuai schema Pydantic. Field yang tidak bisa diisi free tier ditandai `enrichment_gap`.
6. **Persistence**. Tulis ke Postgres (primary) plus JSON (audit). Atomic write. Vector store upsert. Event Phase 2 unlock muncul di log saat counter `vendors_enriched_total` mencapai 100.

## Pembagian Paralel

LangGraph `Send` API membagi pekerjaan ke worker subgraph identik. asyncio Semaphore membatasi maksimum worker per stage. Default override via `.env`:

```
EXPO_DISCOVERY_CONCURRENCY=10
EXHIBITOR_EXTRACTION_CONCURRENCY=15
VENDOR_RESOLUTION_CONCURRENCY=30
ENRICHMENT_CONCURRENCY=50
PDF_EXTRACTION_CONCURRENCY=4
```

Kalau pakai Ollama dengan satu GPU, concurrency otomatis dikecilkan supaya GPU tidak overload (auto throttle ke 2 untuk discovery dan 8 untuk enrichment).

Per domain rate limit (1 request per detik via Redis token bucket) tetap dihormati. Walaupun 50 worker jalan, satu domain tidak akan dipukul lebih cepat dari setting itu.

## Roadmap Fase

**Fase 1 (sekarang).** Hanya tier gratis. Target 100 vendor terenrich. Pakai whois, dns, sitemap, schema.org, vendor self crawl. Counter `vendors_enriched_total` jadi gerbang exit.

**Fase 2 (nanti).** Setelah milestone Fase 1 tercapai, tambah Hunter berbayar, Apollo, Crunchbase API, proxycurl LinkedIn, residential proxy. Re enrich vendor lama yang `enrichment_gap` nya panjang.

## Jalankan Tes

Backend:

```bash
cd backend
pip install -e ".[dev]"
pytest tests/unit
```

Frontend:

```bash
cd frontend
npm install
npm run test
npm run typecheck
```

Cakupan saat ini: 152 backend test plus 26 frontend test (total 178 hijau). Backend cover URL canonicalization, aggregator blacklist, schema validation, vendor URL resolver pakai fixture HTML 10times, region detection multilingual, atomic JSON writer, ekstraksi PDF parser, dedup SHA256 PDF store, table parser PDF extractor, name resolver scoring, email verifier (syntax, MX, disposable, role-based, domain match), 7 endpoint API dengan TestClient plus SQLite in-memory. Frontend cover komponen StatCard, DataTable, CompletenessBar, IndustryBadge, ProvenanceTimeline.

## File Penting

| File | Fungsi |
|---|---|
| `backend/src/crawler/agents/resolver.py` | Penentu URL vendor asli, komponen paling kritikal |
| `backend/src/crawler/agents/name_resolver.py` | Resolver vendor PDF (cuma punya nama, cari domain pakai search plus LLM) |
| `backend/src/crawler/agents/pdf_finder.py` | Discovery URL PDF dari aggregator, situs resmi expo, dan search engine |
| `backend/src/crawler/tools/scrapers/pdf_extractor.py` | Parsing PDF jadi daftar vendor dengan provenance halaman |
| `backend/src/crawler/tools/parsers/pdf_parser.py` | PyMuPDF plus pdfplumber plus Surya OCR fallback |
| `backend/src/crawler/store/pdf_store.py` | Atomic download PDF, dedup SHA256, sidecar metadata |
| `backend/src/crawler/store/db_reporter.py` | Tulis Vendor / Expo / Run ke Postgres dual-write dengan JSON |
| `backend/src/crawler/db/models.py` | SQLAlchemy ORM Vendor, Expo, ExpoVendor, Pdf, Run |
| `backend/src/crawler/db/repositories/` | Repository CRUD plus query stats per entitas |
| `backend/src/crawler/api/app.py` | FastAPI factory plus lifespan plus CORS |
| `backend/src/crawler/api/routes/` | 13 endpoint termasuk stats untuk charts |
| `backend/src/crawler/graph.py` | LangGraph state machine plus parallel fan out |
| `backend/src/crawler/agents/discovery.py` | Dynamic seed generation plus multi sumber search |
| `backend/src/crawler/agents/enricher.py` | Free tools enrichment plus LLM merge |
| `backend/src/crawler/store/vector_store.py` | Chroma vendor dedup |
| `frontend/src/views/OverviewPage.vue` | Dashboard utama dengan 6 chart industrial |
| `frontend/src/components/charts/` | Industri pie, country bar, source type pie, timeline, gauge phase 2, runs mode bar |
| `frontend/src/api/client.ts` | Axios client plus typed endpoints |
| `frontend/src/composables/useTheme.ts` | Light dan dark mode toggle |
| `frontend/src/composables/useApiHealth.ts` | Live ping status backend |
| `frontend/src/composables/useCsvExport.ts` | Helper export CSV |
| `config/aggregator_blacklist.yaml` | Domain yang tidak boleh dianggap vendor |
| `config/seed_topics.yaml` | Topic dan anchor expo untuk LLM seed expansion |
| `docker-compose.yml` | Stack lengkap self host (10 service) |
| `docker-compose.gpu.yml` | Overlay opsional untuk passthrough GPU NVIDIA |
