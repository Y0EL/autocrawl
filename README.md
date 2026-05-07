# AutoCrawler

Crawler otonom yang jalan 24 jam non stop. Fungsinya menemukan expo bidang security dan defense, mengambil daftar exhibitor dari situs aggregator (10times.com, Wikipedia, eventbrite, dan sejenisnya), lalu menentukan domain vendor asli (bukan domain aggregator), dan terakhir memperkaya data vendor pakai sumber publik gratis. Data text vendor otomatis diterjemahkan ke Bahasa Indonesia memakai NLLB-200. Hasil disimpan ke Postgres dan dipresentasikan di admin console berbasis Vue.

> **Baru pertama kali pakai?** Lihat [TUTORIAL.md](TUTORIAL.md) untuk panduan langkah demi langkah dari nol (15 section, lengkap dengan troubleshooting).

Stack inti backend. LangGraph, LangChain (langchain-ollama dan langchain-openai), Playwright, **Crawl4AI** (Apache-2.0 OSS, ganti Firecrawl), **OCR via Ollama vision model** (`gemma4:e4b`, ganti Surya — gak perlu PyTorch / weight download), **Ollama dengan IBM Granite 4.1** (LLM lokal default, gratis, Apache-2.0), **OpenSERP** (SERP self-hosted multi engine, mendukung Google, Bing, Yandex, Baidu), FastAPI, SQLAlchemy async, Postgres, Redis Streams.

Stack frontend. Vue 3, TypeScript, Tailwind CSS, Apache ECharts, **Vue Flow** (canvas LangGraph viz), **MapLibre GL dengan @antv/l7** (world map 2.5D globe projection plus drilldown panel interaktif), TanStack Query, Pinia, FontAwesome 6. Semua self host, dijalankan via Docker Compose. Default tanpa cloud dependency, OpenAI cuma escape hatch opsional.

## Struktur Repo

```
crawl/
  backend/    Python service (LangGraph crawler, FastAPI, OCR, scraper, enrichment)
    src/crawler/
      agents/        discovery, extractor, resolver, name_resolver, enricher, reporter
      api/           FastAPI app, routes (incl orchestrator + settings + health expanded)
      db/            SQLAlchemy models, engine (with idempotent column patches), repositories
      orchestrator/  events.py emitter to Redis Streams `autocrawl:events`
      tools/
        scrapers/    10times, wikipedia, generic, pdf_extractor
        crawl4ai_client/  Crawl4AIClient singleton (scrape, extract, find_pdfs, scrape_many)
        firecrawl/   Legacy Firecrawl client (off by default, ENABLE_FIRECRAWL flag)
        search/      wikipedia (full WikiClient REST direct), ddg, baidu, naver, multi
        browsers/    httpx, Playwright pool, Crawl4AI ladder, FlareSolverr
        parsers/     html_parser, pdf_parser (PyMuPDF + pdfplumber + Ollama VLM)
        llm/         openai_client, translator (NLLB-200 int8)
        proxies/     rate_limit, flaresolverr
      store/         json_reporter, db_reporter, pdf_store, vector_store
      observability/ structlog, prometheus metrics (incl crawl4ai_*), langfuse tracer
    tests/unit/      unit test
  frontend/   Vue 3 admin console (TypeScript, Tailwind, ECharts, Vue Flow, FontAwesome)
    src/
      api/           axios client, TypeScript types (incl OrchestratorState/CrawlEvent)
      components/    HudPanel, HudKpiTile, HudFlowNode, HudHeartbeat, HudUptime,
                     HudStatusPill, HudDataTable, HudActivityFeed, charts/
      composables/   useTheme, useApiHealth, useUptime, useCsvExport
      views/         OverviewPage (Pusat Komando), VendorsListPage, VendorDetailPage,
                     ExposListPage, ExpoDetailPage, PdfsListPage, RunsListPage,
                     DiagnosticsPage, OrchestratorBoardPage
      mocks/         MSW handlers (opsional, fallback dev tanpa backend)
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

Lalu isi `.env`. Default semua provider sudah lokal jadi `.env` boleh kosong total saat first boot. Yang opsional, kalau mau switch ke OpenAI cloud sebagai escape hatch:

```
OPENAI_API_KEY=sk_xxx          # opsional, kosongkan untuk full lokal Ollama
LLM_PROVIDER=openai            # opsional, default ollama
EMBEDDING_PROVIDER=openai      # opsional, default ollama
FIRECRAWL_API_KEY=              # opsional, default ENABLE_FIRECRAWL=false
```

Crawl4AI dipakai sebagai default scraper (Apache-2.0 OSS, gratis). LLM default Ollama dengan IBM Granite 4.1 yang otomatis di pull saat container ollama pertama kali boot (sekitar 3 GB total untuk chat plus embedding). Firecrawl legacy tetep ada di codebase tapi off by default. Lihat section `Crawl4AI Integration` dan `.env.example` untuk semua flag.

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
| Ollama | http://localhost:11434 | Tanpa login. Daemon LLM lokal. Cek model dengan `docker compose exec ollama ollama list` |
| OpenSERP | http://localhost:7000 | Tanpa login. Cek health di `/health`. Endpoint per engine misal `/google/search?text=...` |
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
Admin console tactical / military-grade berbasis Vue 3 plus Apache ECharts plus Vue Flow. Sembilan halaman (Pusat Komando, Vendor list + detail, Ekspo list + detail, Brosur PDF, Riwayat Operasi, Diagnostik, Orkestrator), IBM Plex Sans + Mono fonts, palette amber HUD, sidebar icon-only collapsible. Light dan dark mode toggle. Filter, search, CSV export. Hit API real time dengan TanStack Query. Heartbeat strip di topbar (API/DB), uptime live counter, ENGAGE button trigger run dengan dropdown mode (dev/normal/agresif).

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
| GET | `/api/health` | Status per komponen, db, redis, chroma, llm, disk, plus uptime_seconds |
| GET | `/api/settings` | Konfigurasi runtime read only (LLM provider, translation, mode, dll) |
| GET | `/api/overview` | Counter total, latest run, industry breakdown |
| GET | `/api/vendors` | Daftar vendor paginated, filter industry, country, search |
| GET | `/api/vendors/{domain}` | Profil vendor lengkap |
| GET | `/api/expos` | Daftar expo paginated |
| GET | `/api/expos/{expo_id}` | Detail expo plus vendor_domains |
| GET | `/api/pdfs` | Daftar PDF brosur |
| GET | `/api/runs` | Riwayat run |
| GET | `/api/runs/active` | Status run yang lagi jalan plus flag `stop_requested` |
| POST | `/api/runs/trigger` | Luncurkan run baru, body `{mode: dev | normal | aggressive}` |
| POST | `/api/runs/stop` | Stop run aktif. Body `{force: bool}`. Default graceful drain |
| GET | `/api/stats/industries` | Untuk pie chart industri |
| GET | `/api/stats/countries` | Untuk bar chart top negara vendor |
| GET | `/api/stats/source-types` | PDF vs aggregator vs search |
| GET | `/api/stats/timeline` | Akumulasi vendor per hari |
| GET | `/api/stats/runs-mode` | Distribusi mode run |
| GET | `/api/stats/expo-countries` | Per negara, hitung expo dan vendor untuk world map |
| GET | `/api/stats/expo-countries/{country}` | Detail per negara untuk panel drilldown world map |
| GET | `/api/orchestrator/state` | Snapshot graph nodes plus per node counters (active, completed, failed) |
| GET | `/api/orchestrator/events` | Tail event stream `autocrawl:events` (long poll friendly) |
| GET | `/api/orchestrator/throughput` | Rolling window throughput dengan adaptive fallback (60s, 5m, 30m, 1h, 24h) |
| GET | `/api/exhibitor-refs/stats` | Bucket counts per status dan failure category |
| GET | `/api/exhibitor-refs` | List ref dengan filter status atau failure category |
| GET | `/api/config/scope` | List scope rules user editable (kata kunci, domain, topik) |
| POST | `/api/config/scope` | Tambah rule baru |
| PATCH | `/api/config/scope/{id}` | Toggle enabled atau edit notes |
| DELETE | `/api/config/scope/{id}` | Hapus rule (block untuk source `yaml_default`) |
| GET | `/api/config/scope/prompt` | Prompt AI scope classifier saat ini |
| PUT | `/api/config/scope/prompt` | Set prompt custom |
| DELETE | `/api/config/scope/prompt` | Reset prompt ke default |
| POST | `/api/config/scope/suggest` | LLM saran rule kandidat berdasarkan hint user |

OpenAPI Swagger UI: http://localhost:8081/api/docs

## Frontend Admin Console

Vue 3 dengan TypeScript, Tailwind, ECharts, MapLibre GL, @antv/l7, TanStack Query, Pinia, FontAwesome 6. Light dan dark mode otomatis ikut preferensi sistem, bisa di toggle manual, tersimpan di localStorage.

Sepuluh halaman utama:

1. Pusat Komando (Overview) dengan world map 2.5D interaktif di paling atas
2. Daftar Vendor (filter industri, negara, status, plus banner filter dari klik map)
3. Detail Vendor (timeline source provenance per vendor)
4. Daftar Expo (filter negara dari klik map)
5. Detail Expo
6. Brosur PDF
7. Riwayat Operasi (run history dengan polling 5 detik)
8. Diagnostik (status per komponen)
9. Orkestrator (Vue Flow canvas LangGraph workflow real time)
10. Konfigurasi (4 tab edit kata kunci scope, blacklist domain, seed topik, prompt AI dengan toggle realtime via Redis version counter)

Topbar punya tombol ENGAGE untuk trigger run plus dropdown mode (dev, normal, agresif). Saat run aktif, muncul tombol STOP merah yang default graceful drain (klik biasa) dan force kill (shift plus klik dengan modal konfirm).

### Charts industrial (Apache ECharts)

* **IndustryBarChart**. Horizontal bar top 12 + Lainnya bucket. Toggle "Top 12" vs "Semua" dengan dataZoom virtual scroll. Replace pie chart yang overflow waktu kategori >30.
* **CountryBarChart**. Top 10 negara berdasarkan registrar domain vendor.
* **SourceTypePieChart**. Donut PDF vs aggregator vs search vs manual (4 kategori, pas untuk pie).
* **VendorTimelineChart**. Combo bar plus line area, akumulasi vendor 30 hari.
* **Phase2GaugeChart**. Gauge tactical (amber needle) progress menuju target 100 vendor.
* **RunsModeBarChart**. Distribusi run mode dev, normal, aggressive.

Semua chart auto swap palette saat user toggle dark mode. Theme tactical: IBM Plex Mono labels, amber accent, sharp corners, low-saturation borders.

### Filter, Search, Export

Halaman Vendor punya filter industri (dropdown), filter negara (dropdown dinamis dari endpoint), full text search nama atau domain, plus tombol Export CSV satu klik.

Halaman Expo punya filter negara dan search nama expo.

### Dev Lokal

Frontend selalu hit backend real. Tidak ada mock layer. Pastikan stack docker udah jalan sebelum `npm run dev`.

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # bundle production ke dist/
npm run preview      # cek build di port 8090
npm run test         # vitest
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
docker compose exec api crawl backfill-pdfs              # walk data/pdfs/ dan insert ke DB

docker compose exec api crawl db migrate                 # buat tabel Postgres
docker compose exec api crawl db import-json             # impor JSON lama ke DB
docker compose exec api crawl api-serve --port 8081      # serve API manual (default sudah jalan)
docker compose exec api crawl reset-state                # bersihin lock Redis + runs gantung + ref mid-pipeline
```

> Detail `reset-state` (kapan perlu, flag `--clear-pdfs`/`--clear-logs`, manual fallback) ada di [TUTORIAL.md section 13x](TUTORIAL.md).

Mode tersedia:

| Mode | Jumlah Worker | Untuk Apa |
|---|---|---|
| dev | 5 worker | debug lokal, hemat resource |
| normal | 15 worker enrichment | run harian biasa, default |
| aggressive | 50 worker enrichment | catch up burst di akhir minggu |

## Provider LLM (Ollama default, OpenAI opsional)

Default semua LLM call masuk ke **Ollama lokal** dengan model **IBM Granite 4.1** (Apache-2.0, gratis, fully offline). Container `ollama` di compose otomatis pull dua model saat first boot.

* `granite4.1:3b` untuk chat (sekitar 2.1 GB Q4_K_M)
* `granite-embedding:278m` untuk embedding 768 dim multilingual (sekitar 950 MB)

Cek model setelah container ollama healthy:

```bash
docker compose exec ollama ollama list
```

Tuning otomatis untuk single GPU lewat env di compose:

```
OLLAMA_KEEP_ALIVE=-1               # model tetap resident, no cold start
OLLAMA_NUM_PARALLEL=2              # max 2 concurrent request
OLLAMA_MAX_LOADED_MODELS=2         # chat plus embedding sama sama resident
```

Concurrency di crawler otomatis di throttle saat detect Ollama provider (lihat `config.py:for_provider`). Discovery di cap 2, enrichment di cap 8.

### GPU NVIDIA

Edit `docker-compose.yml`, uncomment block `deploy.resources.reservations.devices` di service `ollama`. Pastikan host udah install `nvidia-container-toolkit`. Throughput naik 5 sampai 10x dibanding CPU only.

### Escape hatch ke OpenAI cloud

Kalau Ollama lokal terlalu lambat dan lo punya OpenAI key, override env di `.env`:

```
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk_xxx
OPENAI_MODEL_HEAVY=gpt-4o
OPENAI_MODEL_LIGHT=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Lalu restart container crawler dan api:

```bash
docker compose restart crawler api
```

Chroma vector store auto detect dimensi mismatch (768 ke 1536 atau sebaliknya). Saat embedding provider switch, koleksi vendor lama otomatis di wipe dan dibangun ulang. Tidak perlu intervensi manual.

### Reliabilitas structured output di model kecil

Granite 3B kadang miss field optional di Pydantic schema saat enrichment besar. Wrapper `chat()` punya retry loop 3 attempt. Setiap retry pakai `with_structured_output(method="json_schema")` yang constrain decoding dengan JSON schema, jauh lebih reliable dari free form JSON. Failure case di log dengan event `llm.structured_validation_retry`.

## Crawl4AI Integration

Crawl4AI by [unclecode](https://github.com/unclecode/crawl4ai) adalah scraper Apache-2.0 OSS berbasis Playwright. Mengganti Firecrawl yang berbayar. Tiga peran:

1. **Scrape URL → markdown clean** (`c4ai_scrape`). Pakai `result.markdown.raw_markdown` bawaan, tanpa LLM cost.
2. **Structured extract dengan Pydantic schema** (`c4ai_extract`). Pakai `LLMExtractionStrategy` BYOK OpenAI — lo bayar token aja.
3. **Find PDF links di sebuah page** (`c4ai_find_pdfs`). Filter `result.links` untuk href `.pdf`.

Singleton client di `tools/crawl4ai_client/client.py` reuse satu `AsyncWebCrawler` antar request supaya gak kena cold-start Chromium tiap call (~3 detik saving). Browser auto-recycle setelah `CRAWL4AI_RECYCLE_AFTER` page (default 500) untuk hindari memory leak Chromium long-lived.

Dua mode browser:
* `chromium` — fast path default
* `undetected` — anti-bot via undetected-chromedriver Playwright fork. Dipanggil otomatis dari ladder fetcher kalau scrape biasa kena Cloudflare wall

Ladder fetcher lengkap (`tools/browsers/fetcher.py`):
1. httpx (cepat, static page)
2. Playwright pool internal (JS render)
3. Crawl4AI chromium (clean markdown + JS)
4. Crawl4AI undetected + stealth (anti-bot)
5. FlareSolverr (Cloudflare bypass via service)
6. Firecrawl `/scrape` (cuma kalau `ENABLE_FIRECRAWL=true` AND budget OK)

Env vars di `.env`:

```
ENABLE_FIRECRAWL=false                    # legacy Firecrawl, off by default
ENABLE_CRAWL4AI=true                      # primary scraper
CRAWL4AI_BROWSER=chromium                 # chromium | undetected
CRAWL4AI_RECYCLE_AFTER=500                # restart browser tiap N page
CRAWL4AI_MAX_CONCURRENT=8                 # batch concurrency cap
CRAWL4AI_EXTRACTION_MODEL=gpt-4o-mini     # model untuk LLMExtractionStrategy
```

Metric Prometheus relevant:
* `crawl_crawl4ai_requests_total{operation,status}` — counter per operasi (scrape/extract/find_pdfs/scrape_stealth)
* `crawl_crawl4ai_browser_recycles_total{mode}` — counter restart browser per mode
* `crawl_external_search_total{provider,status}` — distribusi search provider (wikipedia/ddg/firecrawl)

Build image: `crawl4ai-setup` post-install di Dockerfile (idempotent, warm browser bridge cache).

## Wikipedia Direct REST API

`tools/search/wikipedia.py` punya `WikiClient` lengkap pakai `httpx.AsyncClient` ke MediaWiki Action API. Tier 1 discovery. Surface:

| Method | Endpoint | Use case |
|---|---|---|
| `opensearch(query, limit)` | `action=opensearch` | Type-ahead, query pendek, hasil canonical title |
| `fulltext_search(query, limit)` | `action=query&list=search` | Fallback OpenSearch kalau hits < 3 |
| `category_members(category, limit)` | `action=query&list=categorymembers` | Enumeration eksaustif (e.g. `Category:Defence_exhibitions`) |
| `extracts(titles)` | `prop=extracts&exintro&explaintext` | Batch intro paragraph (50 titles per call) |
| `page_categories(titles)` | `prop=categories` | Batch klasifikasi |
| `extlinks(title)` | `prop=extlinks` | External URLs cited oleh artikel — direct vendor candidates |
| `outbound_links(title)` | `prop=links&plnamespace=0` | Internal /wiki/ link |

ToS-compliant: User-Agent mandatory (`AutoCrawler/0.2 ...`), `maxlag=5`, `Accept-Encoding: gzip`, concurrency `Semaphore(2)`. Auto exponential backoff on `ratelimited` / 429.

Multi search reweight (`tools/search/multi.py`).

* **Tier 1**. Wikipedia direct (opensearch plus category_members)
* **Tier 2**. DuckDuckGo via `ddgs` plus Google News RSS
* **Tier 3**. **OpenSERP** multi engine (Google, Bing, Yandex, Baidu) via headless Chromium lokal, default ON saat `ENABLE_OPENSERP=true`
* **Tier 4**. Region specific (baidu, naver, yahoo_japan kalau query hint China, Korea, Japan)
* **Tier 5**. Firecrawl (cuma kalau `ENABLE_FIRECRAWL=true`)

Wikipedia article scraper (`tools/scrapers/wikipedia.py`) sekarang gabungkan dua jalur:
1. **Internal `/wiki/` links** (existing) — classify via category heuristic, emit `company` + `organisation`
2. **External links via `extlinks` API** (NEW) — direct vendor URL cited oleh artikel, confidence 0.90

Verify dengan:
```bash
docker compose exec api crawl wiki-test https://en.wikipedia.org/wiki/Eurosatory
```

## Orkestrator Board

Halaman `/orkestrator` di frontend tampilkan canvas LangGraph workflow real-time pakai Vue Flow. Enam node (discover → worker_extract / worker_pdf_extract → worker_resolve → worker_enrich → finalize), edge animated saat upstream node aktif, side panel scroll event ticker live.

Backend pipeline:
* `orchestrator/events.py` emitter ke Redis Stream `autocrawl:events` (MAXLEN 10000)
* Tiap LangGraph node panggil `await emit_event(node, event, run_id, payload)` di `started` / `completed` / `failed`
* `GET /api/orchestrator/state` aggregate counters per node dari window 1000 event terakhir
* `GET /api/orchestrator/events?since=<id>&limit=<n>` tail XRANGE untuk frontend

Frontend `OrchestratorBoardPage.vue` poll state tiap 2 detik dan events tiap 1.5 detik. `HudFlowNode.vue` custom Vue Flow node dengan tactical chrome (LED pulse, code, label, mini grid AKTIF/OK/GAGAL counter).

Pure cosmetic — gak drive backend behavior, cuma observability. Best buat presentasi ke management atau debug saat satu stage stuck.

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
OCR_VLM_MODEL=gemma4:e4b   # vision model untuk OCR fallback (lewat Ollama)
OCR_RENDER_DPI=200
OCR_PAGE_TIMEOUT=60
MAX_PDFS_PER_EXPO=10
PDF_MAX_SIZE_MB=50
```

OCR sekarang dilayani Ollama (vision model `gemma4:e4b`) — tidak perlu PyTorch, tidak perlu download bobot Surya. Cukup pastikan model sudah ke-pull di Ollama:

```bash
docker compose exec ollama ollama pull gemma4:e4b
docker compose build crawler
docker compose up -d
```

Untuk passthrough GPU ke Ollama (butuh NVIDIA Container Toolkit di host):

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
      "extraction_method": "vlm_ocr",
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

## OpenSERP (Multi Engine SERP Self Hosted)

Container `openserp` (image `karust/openserp:latest`, MIT, port 7000) adalah scraper SERP yang fronting Google, Bing, Yandex, Baidu, dan DuckDuckGo via headless Chromium. Default `ENABLE_OPENSERP=true` dan engine list `google,bing,yandex,baidu`.

Provider Python di `tools/search/openserp.py` paralel ke semua engine yang di set, dedupe by URL, plus backoff exponential pada HTTP 503 (captcha Google) dengan max 2 retry per query. Hasil di merge ke `multi.py` aggregator bareng Wikipedia, DuckDuckGo, dan Google News RSS.

Override engines via env:

```
ENABLE_OPENSERP=true
OPENSERP_URL=http://openserp:7000
OPENSERP_ENGINES=google,bing,yandex,baidu
OPENSERP_TIMEOUT_SECONDS=30
OPENSERP_MAX_RETRIES=2
```

Cek health:

```bash
curl http://localhost:7000/health
docker compose logs openserp --tail 30
```

Saat ada captcha, log crawler nunjukin `openserp.captcha` dengan engine name. Worst case lo cabut Google saja, sisanya tetep jalan.

## Konfigurasi Scope (UI editable)

Halaman `/konfigurasi` di frontend kasih kontrol live atas behavior pipeline tanpa restart container. Empat tab.

1. **Kata Kunci Cakupan** (in scope dan out of scope) untuk classifier
2. **Blacklist Domain** (plus whitelist override)
3. **Seed Topik** (topic name plus anchor expo untuk LLM expansion)
4. **Prompt AI** (system prompt scope classifier yang bisa di edit langsung)

Tabel `scope_rules` di Postgres jadi source of truth, otomatis di seed dari `config/aggregator_blacklist.yaml` dan `config/seed_topics.yaml` saat container api first boot. Setiap mutation lewat UI bump counter `scope:version` di Redis. Crawler dan api proses punya in memory snapshot yang re fetch dari DB tiap kali version berubah, polling 1 detik. Realtime, tidak ada TTL delay.

Tombol "Saran AI" di tiap tab manggil `POST /api/config/scope/suggest`. LLM (granite4.1:3b atau gpt-4o-mini) keluarkan kandidat rule dengan confidence score, user approve manual sebelum masuk DB. Source label ada tiga, `yaml_default` (read only, cuma boleh toggle off), `user` (manual), `ai_suggested` (AI generated, approved user).

## World Map 2.5D Tactical (Overview)

Halaman Pusat Komando paling atas tampilkan world map 2.5D dengan **MapLibre GL** sebagai base map plus **@antv/l7** untuk data layer. Style basemap pakai **CartoDB Dark Matter** (free, no API key). Border negara di recolor cyan setelah style load supaya match HUD theme.

Visual layer.

* **Globe projection** (MapLibre 5.24 plus). Bumi melengkung saat zoom out, fade ke flat mercator saat zoom in. Infinite world copy aktif jadi pan ke samping tidak kelihatan ujung Antartika patah.
* **Cylinder bar** per negara dengan height proporsional vendor count. Color tier dari cyan (1 sampai 4 vendor) sampai merah (50 plus).
* **Glow halo** dual layer cyan di bawah cylinder.
* **Pulse circle** animated.
* **Fly arc 3D** dari top 3 hub country ke seluruh negara lain (cyan ke magenta, animated trail).
* **Country code label** plus vendor count.

Interaksi.

* **Drag** pan, **scroll** zoom, **right click drag** tilt plus rotate, **double click** zoom in.
* **Hover** cylinder, tooltip muncul dengan flag emoji plus stat. Cylinder yang di hover flash putih.
* **Klik kiri** cylinder, side panel slide in dari kanan dengan top 5 expo plus top 3 vendor di negara itu, plus tombol drilldown ke `/expos?country=X` dan `/vendors?country=X`.
* **Klik kanan** cylinder, context menu (Filter Ekspo, Filter Vendor, Copy ISO).
* **ESC** tutup panel atau context menu.

Data world map polling 5 detik ke `/api/stats/expo-countries`. Begitu crawler enrich vendor baru dengan country valid, marker baru muncul tanpa refresh. Indicator hijau pulsing **LIVE 5s** di header map konfirmasi polling jalan.

## Stop Run Graceful atau Force

Tombol STOP merah muncul di topbar saat ada run aktif.

* **Klik biasa** kirim graceful drain. Backend set flag asyncio Event, worker check di boundary tiap stage, in flight request natural complete, drain selesai sekitar 30 sampai 60 detik. Vendor yang sudah enriched tetep ke commit. `runs.notes='aborted_graceful'`.
* **Shift plus klik** munculkan modal konfirmasi STOP PAKSA. Backend cancel asyncio task langsung, kill Chromium subprocess via `_release_run_resources()`, abort LLM call mid flight, reset `exhibitor_refs.status` yang stuck. Selesai dalam 5 detik. Token in flight kebakar.

Endpoint `POST /api/runs/stop` body `{force: bool}`. Lock Redis `autocrawl:active_run` otomatis di clear setelah stop. Trigger run baru langsung available.

## Cara Kerja Singkat

1. **Discovery**. LLM expand topic dari `config/seed_topics.yaml` jadi 8 sampai 15 query variasi (juga dalam bahasa lokal kalau region China, Jepang, Korea, atau Russia). Multi sumber search tiered. Wikipedia REST direct (OpenSearch plus CategoryMembers), DuckDuckGo via `ddgs`, Google News RSS, plus regional engine (Baidu, Naver, Yahoo Japan) kalau region cocok, plus **OpenSERP** (Google, Bing, Yandex, Baidu via headless Chromium lokal) saat `ENABLE_OPENSERP=true`, plus Firecrawl cuma kalau `ENABLE_FIRECRAWL=true`.
2. **Extraction**. Scraper khusus per situs aggregator (10times, Wikipedia article, generic fallback) hasilkan daftar exhibitor. Wikipedia path gabungkan internal `/wiki/` link classification + external links dari `extlinks` API. Bersamaan, PDF Finder cari brosur PDF expo (lewat Crawl4AI `c4ai_find_pdfs`) dan PDF Extractor parsing pakai PyMuPDF, pdfplumber, atau Ollama vision OCR (`gemma4:e4b`). PDF metadata (filename, sha256, size, page_count, vendors_found, downloaded_at) auto-persisted ke tabel `pdfs` setelah extraction selesai.
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

Karena default LLM lokal Ollama, concurrency otomatis dikecilkan supaya GPU tidak overload. Auto throttle ke 2 untuk discovery dan 8 untuk enrichment via `for_provider("ollama")` di `config.py`.

Per domain rate limit (1 request per detik via Redis token bucket) tetap dihormati. Walaupun 50 worker jalan, satu domain tidak akan dipukul lebih cepat dari setting itu.

## Roadmap Fase

**Fase 1 (sekarang).** Hanya tier gratis. Target 100 vendor terenrich. Pakai whois, dns, sitemap, schema.org, vendor self crawl. **Crawl4AI** (Apache-2.0 OSS) sebagai primary scraper, **Ollama plus Granite 4.1** sebagai LLM lokal default (gratis, Apache-2.0), **OpenSERP** multi engine self hosted untuk SERP coverage Google plus Bing plus Yandex plus Baidu, Wikipedia REST direct sebagai tier 1 discovery, DDGS plus Google News RSS sebagai tier 2. **Zero cloud cost by default**. Counter `vendors_enriched_total >= 100` jadi gerbang exit.

**Fase 2 (nanti).** Setelah milestone Fase 1 tercapai, tambah Hunter berbayar, Apollo, Crunchbase API, proxycurl LinkedIn, residential proxy. Optional re aktivasi Firecrawl (`ENABLE_FIRECRAWL=true`) atau switch LLM ke OpenAI gpt-4o (`LLM_PROVIDER=openai`) untuk quality boost di enrichment yang Granite kena hallucinate. Brave Search API untuk SERP reliability. Pertimbangkan SearXNG self-hosted kalau OpenSERP captcha rate jadi masalah. Re enrich vendor lama yang `enrichment_gap` nya panjang.

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

Cakupan saat ini: backend unit test (URL canonicalization, aggregator blacklist, schema validation, vendor URL resolver, region detection multilingual, atomic JSON writer, PDF parser, PDF dedup SHA256, name resolver scoring, email verifier, API endpoint smoke test). Frontend test legacy sudah dibersihkan saat redesign tactical (component tests yang lama refer ke komponen yang udah dihapus). Test coverage frontend bisa ditambah ulang nanti untuk komponen Hud* yang baru.

## File Penting

| File | Fungsi |
|---|---|
| `backend/src/crawler/agents/resolver.py` | Penentu URL vendor asli, komponen paling kritikal |
| `backend/src/crawler/agents/name_resolver.py` | Resolver vendor PDF (cuma punya nama, cari domain pakai search plus LLM) |
| `backend/src/crawler/agents/pdf_finder.py` | Discovery URL PDF dari aggregator, situs resmi expo, dan search engine |
| `backend/src/crawler/tools/scrapers/pdf_extractor.py` | Parsing PDF jadi daftar vendor dengan provenance halaman |
| `backend/src/crawler/tools/parsers/pdf_parser.py` | PyMuPDF plus pdfplumber plus Ollama-VLM OCR fallback (gemma4:e4b) |
| `backend/src/crawler/store/pdf_store.py` | Atomic download PDF, dedup SHA256, sidecar metadata |
| `backend/src/crawler/store/db_reporter.py` | Tulis Vendor / Expo / Run ke Postgres dual-write dengan JSON |
| `backend/src/crawler/db/models.py` | SQLAlchemy ORM Vendor, Expo, ExpoVendor, Pdf, Run |
| `backend/src/crawler/db/repositories/` | Repository CRUD plus query stats per entitas |
| `backend/src/crawler/api/app.py` | FastAPI factory plus lifespan plus CORS plus Crawl4AI close hook |
| `backend/src/crawler/api/routes/` | 17 endpoint termasuk stats, settings, orchestrator |
| `backend/src/crawler/api/routes/runs.py` | Trigger run dengan Redis SETNX active-run lock + persist RunSummary ke DB |
| `backend/src/crawler/api/routes/health.py` | Health expanded (db, redis, chroma, llm, disk, uptime) |
| `backend/src/crawler/api/routes/orchestrator.py` | Snapshot state + events tail untuk Orkestrator Board |
| `backend/src/crawler/orchestrator/events.py` | Redis Stream emitter `autocrawl:events` |
| `backend/src/crawler/graph.py` | LangGraph state machine plus parallel fan out plus emit_event instrumentation |
| `backend/src/crawler/db/engine.py` | init_db dengan idempotent ALTER TABLE patches untuk Postgres |
| `backend/src/crawler/tools/crawl4ai_client/client.py` | Crawl4AIClient singleton (scrape, extract, find_pdfs, scrape_many) |
| `backend/src/crawler/tools/search/wikipedia.py` | WikiClient REST direct (opensearch, search, category_members, extracts, extlinks) |
| `backend/src/crawler/tools/scrapers/wikipedia.py` | Article scraper internal links + extlinks dual path |
| `backend/src/crawler/tools/scrapers/pdf_extractor.py` | PDF parsing + auto pdf_repo.upsert ke DB setelah extraction |
| `backend/src/crawler/agents/discovery.py` | Dynamic seed generation plus multi sumber search tiered |
| `backend/src/crawler/agents/enricher.py` | Free tools enrichment plus LLM merge |
| `backend/src/crawler/store/vector_store.py` | Chroma vendor dedup |
| `frontend/src/views/OverviewPage.vue` | Pusat Komando dengan 6 KPI tile + 12-col grid charts |
| `frontend/src/views/DiagnosticsPage.vue` | System diagnostics (per-component health, Phase 2 gauge, runtime config) |
| `frontend/src/views/OrchestratorBoardPage.vue` | Vue Flow canvas LangGraph workflow real-time |
| `frontend/src/components/HudFlowNode.vue` | Custom Vue Flow node dengan tactical chrome + LED |
| `frontend/src/components/HudHeartbeat.vue` | API/DB heartbeat strip di topbar |
| `frontend/src/components/HudUptime.vue` | Live uptime counter dari /api/health uptime_seconds |
| `frontend/src/components/charts/` | IndustryBarChart (replace pie), country bar, source type pie, timeline, gauge phase 2, runs mode bar |
| `frontend/src/api/client.ts` | Axios client plus typed endpoints (incl orchestrator) |
| `frontend/src/composables/useTheme.ts` | Light dan dark mode toggle |
| `frontend/src/composables/useApiHealth.ts` | Live ping status backend |
| `frontend/src/composables/useUptime.ts` | Uptime counter dengan reference dari API |
| `frontend/src/composables/useCsvExport.ts` | Helper export CSV |
| `config/aggregator_blacklist.yaml` | Domain yang tidak boleh dianggap vendor (auto seed ke `scope_rules` saat first boot) |
| `config/seed_topics.yaml` | Topic dan anchor expo untuk LLM seed expansion (auto seed ke `scope_rules`) |
| `backend/src/crawler/tools/search/openserp.py` | Provider SERP multi engine self hosted |
| `backend/src/crawler/tools/scope_cache.py` | In memory snapshot scope rule plus prompt, di refresh realtime via Redis version counter |
| `backend/src/crawler/db/scope_seed.py` | Auto import YAML default ke tabel `scope_rules` saat init |
| `backend/src/crawler/api/routes/config_scope.py` | Endpoint UI Konfigurasi (CRUD rule, prompt, suggest) |
| `backend/ops/ollama_init.sh` | Bootstrap script container ollama, idempotent pull granite4.1:3b plus granite-embedding:278m |
| `frontend/src/components/HudWorldMap.vue` | World map 2.5D MapLibre plus L7 plus globe projection plus interactivity |
| `frontend/src/components/HudCountryDetailPanel.vue` | Slide in detail panel side world map |
| `frontend/src/views/ConfigurationPage.vue` | UI Konfigurasi 4 tab (scope keyword, blacklist, seed topik, prompt AI) |
| `frontend/src/data/country_resolver.ts` | Resolve free text country ke ISO plus centroid lat lon (via world-countries) |
| `docker-compose.yml` | Stack lengkap self host (12 service termasuk ollama plus openserp) |
| `docker-compose.gpu.yml` | Overlay opsional untuk passthrough GPU NVIDIA |
